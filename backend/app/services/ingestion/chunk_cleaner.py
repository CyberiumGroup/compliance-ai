"""Chunk cleaning stage: removes boilerplate sections and merges small chunks.

Three operations, applied in order by clean_chunks():

1. Text sanitisation — strip non-printable control characters and collapse
   visual separator runs (e.g. "------", "......") from every chunk's text.

2. Exclusion filter — chunks whose leading heading matches EXCLUDED_HEADINGS are
   discarded. Leading numbers are stripped before matching, so "3.2 History" and
   "1. Approval" are both caught.

3. Small-chunk merger — chunks with <= MERGE_MIN_TOKENS tokens are merged into
   the following chunk with a double-newline separator. If a small chunk is the
   last in the list it is merged into the preceding chunk instead. Accumulation
   continues until the merged result exceeds the threshold.
"""

import re

# ── Exclusion list ─────────────────────────────────────────────────────────────

# Case-insensitive exact matches against the chunk's leading heading (after
# stripping any leading numbering sequence). Add new entries here.
EXCLUDED_HEADINGS: frozenset[str] = frozenset({
    "approval",
    "approvals",
    "history",
    "related documents",
    "contacts"
})

# Matches leading numbering prefixes: "1.", "3.2 ", "4.1.1)", "2) ", etc.
_NUMBERED_PREFIX = re.compile(r"^\d+(\.\d+)*[\s\.\)]+")

MERGE_MIN_TOKENS: int = 50


# ── Helpers ────────────────────────────────────────────────────────────────────

# Non-printable control characters excluding tab (\x09), newline (\x0a), carriage return (\x0d)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Visual separator runs: 4+ repetitions of the same non-word, non-space character
_SEPARATOR_RUNS = re.compile(r"([^\w\s])\1{3,}")


def _sanitise_text(text: str) -> str:
    """Remove junk characters that embedding models gain nothing from."""
    text = _CONTROL_CHARS.sub("", text)
    text = _SEPARATOR_RUNS.sub("", text)
    return text.strip()


def _leading_heading(chunk_text: str) -> str | None:
    """Return the leading heading of a chunk, or None if not detectable.

    A heading is the first line when it is a single short string (no embedded
    newline, <= 120 chars) followed by a blank line — the format produced by
    HybridChunker's semantic mode.
    """
    parts = chunk_text.split("\n\n", 1)
    if len(parts) != 2:
        return None
    candidate = parts[0].strip()
    if "\n" in candidate or len(candidate) > 120:
        return None
    return candidate


def _normalize_heading(heading: str) -> str:
    """Strip leading numbering and lowercase for exclusion comparison.

    Examples:
        "3.2 History"        → "history"
        "1. Approval"        → "approval"
        "4.1) Related Documents" → "related documents"
        "Approvals"          → "approvals"
    """
    return _NUMBERED_PREFIX.sub("", heading).strip().lower()


def _make_chunk(text: str) -> dict:
    return {"text": text, "token_count": max(1, len(text) // 4)}


# ── Public API ─────────────────────────────────────────────────────────────────

def filter_chunks(chunks: list[dict]) -> list[dict]:
    """Discard chunks whose leading heading (after stripping numbering) is excluded."""
    result = []
    for chunk in chunks:
        heading = _leading_heading(chunk["text"])
        if heading and _normalize_heading(heading) in EXCLUDED_HEADINGS:
            continue
        result.append(chunk)
    return result


def merge_small_chunks(chunks: list[dict], min_tokens: int = MERGE_MIN_TOKENS) -> list[dict]:
    """Merge chunks with <= min_tokens tokens into the following chunk.

    Accumulation continues until the combined result exceeds min_tokens.
    A trailing small chunk (no following chunk) is merged into the last
    emitted chunk instead of being stored alone.
    """
    if not chunks:
        return chunks

    result: list[dict] = []
    carry: str | None = None  # text accumulated from small chunk(s)

    for chunk in chunks:
        if carry is not None:
            merged_text = carry + "\n\n" + chunk["text"]
            merged = _make_chunk(merged_text)
            if merged["token_count"] > min_tokens:
                result.append(merged)
                carry = None
            else:
                carry = merged_text  # still small — keep accumulating
        elif chunk["token_count"] <= min_tokens:
            carry = chunk["text"]
        else:
            result.append(chunk)

    # Flush any remaining carry into the last emitted chunk, or emit alone
    if carry is not None:
        if result:
            merged_text = result[-1]["text"] + "\n\n" + carry
            result[-1] = _make_chunk(merged_text)
        else:
            result.append(_make_chunk(carry))

    return result


def sanitise_chunks(chunks: list[dict]) -> list[dict]:
    """Apply text sanitisation to every chunk in place (returns new list)."""
    result = []
    for chunk in chunks:
        cleaned = _sanitise_text(chunk["text"])
        if cleaned:
            result.append(_make_chunk(cleaned))
    return result


def clean_chunks(chunks: list[dict]) -> list[dict]:
    """Run all cleaning stages in order: sanitise → exclude → merge small."""
    chunks = sanitise_chunks(chunks)
    chunks = filter_chunks(chunks)
    chunks = merge_small_chunks(chunks)
    return chunks
