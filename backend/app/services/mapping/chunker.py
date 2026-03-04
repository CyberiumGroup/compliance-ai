"""Hybrid document chunker for semantic relevance scoring.

Strategy:
  1. Scan the document for section headings using regex patterns.
  2. If >= chunk_min_sections headings are found → semantic mode:
       - Split the document at heading boundaries.
       - If a section fits within chunk_size_chars, emit it as one chunk.
       - If a section is too large, sub-chunk its body with the fixed-size
         paragraph accumulator and prepend the heading to every sub-chunk
         so each chunk retains its section context.
  3. Otherwise → fixed-size mode (original behaviour):
       - Accumulate paragraphs until chunk_size_chars, then emit with overlap.

chunk() returns (chunks, strategy) where strategy is 'semantic' or 'fixed',
allowing the caller to persist this label on the Policy record.
"""

import re
from typing import Literal

ChunkStrategy = Literal["semantic", "fixed"]

# ── Heading detection patterns ────────────────────────────────────────────────

_HEADING_PATTERNS = [
    re.compile(r"^#{1,3}\s+\S"),                    # Markdown: ## Title
    re.compile(r"^\d+(\.\d+)*[\s\.\)]\s*\S"),       # Numbered: "3.2 " / "4.1.1."
    re.compile(r"^[A-Z][A-Z0-9 \-–/]{4,}$"),        # ALLCAPS:  "ACCESS CONTROL"
]


def _is_heading(line: str) -> bool:
    """Return True if the line looks like a section heading."""
    stripped = line.strip()
    # Headings are non-empty and not excessively long (avoids catching body sentences)
    if not stripped or len(stripped) > 120:
        return False
    return any(p.match(stripped) for p in _HEADING_PATTERNS)


# ── Chunker ───────────────────────────────────────────────────────────────────

class HybridChunker:
    """Chunk policy documents using structure-aware or fixed-size strategies."""

    def __init__(
        self,
        chunk_size_chars: int,
        chunk_overlap_chars: int,
        chunk_min_sections: int,
    ) -> None:
        self.chunk_size = chunk_size_chars
        self.overlap = chunk_overlap_chars
        self.min_sections = chunk_min_sections

    def chunk(self, text: str) -> tuple[list[dict], ChunkStrategy]:
        """Chunk text and return (chunks, strategy).

        strategy is 'semantic' if heading detection succeeded, 'fixed' otherwise.
        Each chunk dict has keys: 'text', 'token_count'.
        """
        lines = text.splitlines()
        heading_indices = [i for i, line in enumerate(lines) if _is_heading(line)]

        if len(heading_indices) >= self.min_sections:
            chunks = self._semantic_chunks(lines, heading_indices)
            return chunks, "semantic"
        else:
            chunks = self._fixed_size_chunks(text)
            return chunks, "fixed"

    # ── Semantic mode ──────────────────────────────────────────────────────────

    def _semantic_chunks(
        self,
        lines: list[str],
        heading_indices: list[int],
    ) -> list[dict]:
        """Split at detected headings; sub-chunk large sections.

        Heading display text has leading '#' stripped (they were only added for
        detection). Sections with no body are merged into the following section
        to avoid emitting standalone heading-only chunks.
        """
        raw_sections: list[tuple[str, str]] = []

        # Preamble: text before the first heading
        if heading_indices[0] > 0:
            preamble = "\n".join(lines[: heading_indices[0]]).strip()
            if preamble:
                raw_sections.append(("", preamble))

        # Each heading + its body until the next heading
        for idx, hi in enumerate(heading_indices):
            # Strip '#' markers — only needed for detection, not for display
            heading = lines[hi].strip().lstrip("#").strip()
            start = hi + 1
            end = heading_indices[idx + 1] if idx + 1 < len(heading_indices) else len(lines)
            body = "\n".join(lines[start:end]).strip()
            raw_sections.append((heading, body))

        # Merge empty-body sections into the following section so headings
        # without content don't become tiny standalone chunks.
        sections: list[tuple[str, str]] = []
        pending = ""  # accumulated orphan heading text
        for heading, body in raw_sections:
            if not body:
                pending = f"{pending}\n\n{heading}".strip() if pending else heading
                continue
            if pending:
                body = f"{pending}\n\n{body}"
                pending = ""
            sections.append((heading, body))
        # Trailing orphan headings — append to last section's body
        if pending:
            if sections:
                h, b = sections[-1]
                sections[-1] = (h, f"{b}\n\n{pending}")
            else:
                sections.append(("", pending))

        chunks: list[dict] = []
        for heading, body in sections:
            prefix = f"{heading}\n\n" if heading else ""
            full_text = f"{prefix}{body}".strip()
            if not full_text:
                continue

            if len(full_text) <= self.chunk_size:
                chunks.append(self._make_chunk(full_text))
            else:
                # Sub-chunk the body; prepend the heading to every sub-chunk
                sub_chunks = self._fixed_size_chunks(body)
                for i, sc in enumerate(sub_chunks):
                    if heading:
                        label = f"{heading} (cont.)" if i > 0 else heading
                        sub_text = f"{label}\n\n{sc['text']}"
                    else:
                        sub_text = sc["text"]
                    chunks.append(self._make_chunk(sub_text))

        # Safety: if semantic produced nothing, fall back to fixed-size
        return chunks if chunks else self._fixed_size_chunks(
            "\n\n".join(
                (f"{h}\n\n" if h else "") + b for h, b in sections if b
            )
        )

    # ── Fixed-size mode ────────────────────────────────────────────────────────

    def _fixed_size_chunks(self, text: str) -> list[dict]:
        """Paragraph-accumulating fixed-size chunker with overlap."""
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        chunks: list[dict] = []
        current_paras: list[str] = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if current_size + para_size > self.chunk_size and current_paras:
                chunks.append(self._make_chunk("\n\n".join(current_paras)))

                # Build overlap from trailing paragraphs
                overlap_paras: list[str] = []
                overlap_size = 0
                for p in reversed(current_paras):
                    if overlap_size + len(p) <= self.overlap:
                        overlap_paras.insert(0, p)
                        overlap_size += len(p)
                    else:
                        break

                current_paras = overlap_paras
                current_size = overlap_size

            current_paras.append(para)
            current_size += para_size

        if current_paras:
            chunks.append(self._make_chunk("\n\n".join(current_paras)))

        return chunks

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _make_chunk(text: str) -> dict:
        return {"text": text, "token_count": max(1, len(text) // 4)}
