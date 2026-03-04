"""Structure-aware document parser using docling.

Docling is used only for parsing (PDF, DOCX, DOC, MD → clean plain text).
Chunking is handled downstream by HybridChunker so paragraph boundaries are
always respected and chunk sizes are controlled by settings.

Text extraction strategy:
- Iterate docling's document model item by item (TextItem, SectionHeaderItem, etc.)
- Pull the raw .text from each item — no markdown formatting applied
- Join items with double newlines → compatible with HybridChunker's paragraph splitter
- Adjacent duplicate items are dropped (guards against the docling DOCX table
  iteration bug introduced in v2.54.0)
"""
import os
import tempfile
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".md"}

# Module-level singleton — loaded once, reused across requests.
_converter = None


def _get_converter():
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter
        _converter = DocumentConverter()
    return _converter


def _extract_clean_text(doc) -> str:
    """Iterate docling document items and return clean plain text.

    SectionHeaderItems are prefixed with '#' (scaled to their heading level)
    so that HybridChunker's heading detection can split the document at section
    boundaries rather than relying on character count alone.

    Each item's raw .text is extracted (no markdown symbols), joined with
    double newlines so the result is directly compatible with HybridChunker.
    Consecutive identical items are deduplicated to handle the DOCX table bug.
    """
    parts = []
    prev = None
    for item, _ in doc.iterate_items():
        text = getattr(item, "text", None)
        if not text or not text.strip():
            continue
        cleaned = text.strip()
        if cleaned == prev:
            continue  # drop adjacent duplicates (DOCX table bug guard)

        # Prefix section headers so HybridChunker recognises them as headings
        if type(item).__name__ == "SectionHeaderItem":
            level = max(1, min(getattr(item, "level", 1), 3))
            cleaned = "#" * level + " " + cleaned

        parts.append(cleaned)
        prev = cleaned
    return "\n\n".join(parts)


class DoclingChunker:
    @staticmethod
    def is_supported(filename: str) -> bool:
        return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS

    @staticmethod
    def extract_text(file_content: bytes, filename: str) -> str | None:
        """Parse a document with docling and return clean plain text.

        Returns extracted text on success, None if unsupported or failed.
        Chunking is intentionally not done here — callers use HybridChunker on the result.
        """
        if not DoclingChunker.is_supported(filename):
            return None

        suffix = Path(filename).suffix.lower()
        tmp_path = None
        try:
            converter = _get_converter()

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            doc = converter.convert(tmp_path).document
            text = _extract_clean_text(doc)
            return text if text.strip() else None
        except Exception:
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
