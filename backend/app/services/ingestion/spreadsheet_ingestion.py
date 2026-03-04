"""Spreadsheet ingestion: parses Excel/CSV into JSON (for LLM) and markdown table chunks (for embedding)."""
import io
import json
import re
from pathlib import Path

import pandas as pd

_AUTO_COL = re.compile(r"^Unnamed: \d+$")

SPREADSHEET_EXTENSIONS = {".xlsx", ".xls", ".csv"}


class SpreadsheetIngestionService:

    @staticmethod
    def is_supported(filename: str) -> bool:
        return Path(filename).suffix.lower() in SPREADSHEET_EXTENSIONS

    @staticmethod
    def parse(file_content: bytes, filename: str) -> tuple[str | None, list[dict], str | None]:
        """Parse a spreadsheet file.

        Returns:
            (json_content, chunks, error)
            - json_content: JSON string stored as content_text (LLM input in Phase 2b)
            - chunks: list[{"text": str, "token_count": int}] — markdown table chunks for embedding
            - error: None on success, error message on failure
        """
        ext = Path(filename).suffix.lower()
        try:
            buf = io.BytesIO(file_content)
            if ext == ".csv":
                df_dict = {"Sheet1": pd.read_csv(buf)}
            elif ext == ".xls":
                xf = pd.ExcelFile(buf, engine="xlrd")
                df_dict = {s: xf.parse(s) for s in xf.sheet_names}
            else:  # .xlsx
                xf = pd.ExcelFile(io.BytesIO(file_content), engine="openpyxl")
                df_dict = {s: xf.parse(s) for s in xf.sheet_names}

            sheets_data = []
            chunks: list[dict] = []

            for sheet_name, df in df_dict.items():
                df = _promote_header_row(df)
                df = df.dropna(how="all").fillna("")
                # Flatten whitespace (including embedded \n from merged/formatted cells)
                # so column names and values don't break the markdown table line format.
                columns = [" ".join(str(c).split()) for c in df.columns.tolist()]
                rows = [
                    {" ".join(str(k).split()): " ".join(str(v).split()) for k, v in row.items()}
                    for row in df.to_dict("records")
                ]
                sheets_data.append({"name": sheet_name, "columns": columns, "rows": rows})
                chunks.extend(_make_table_chunks(sheet_name, columns, rows))

            json_content = json.dumps(
                {"filename": filename, "sheets": sheets_data},
                ensure_ascii=False,
                indent=2,
            )
            return json_content, chunks, None

        except Exception as exc:
            return None, [], str(exc)


def _promote_header_row(df: "pd.DataFrame") -> "pd.DataFrame":
    """Detect Excel files where a title/branding row was mistakenly read as the header.

    If >50% of column names are auto-assigned by pandas ("Unnamed: N" or bare integers),
    and the first data row consists entirely of non-empty strings, promote that row to
    be the column headers and drop it from the data.

    This handles the common pattern where Excel workbooks have a decorative merged-cell
    title row above the real column headers.
    """
    if len(df) == 0:
        return df
    auto_count = sum(
        1 for c in df.columns
        if _AUTO_COL.match(str(c)) or isinstance(c, (int, float))
    )
    if auto_count <= len(df.columns) / 2:
        return df  # columns look real already
    first_row = df.iloc[0].tolist()
    if all(isinstance(v, str) and v.strip() for v in first_row):
        df = df.copy()
        df.columns = [" ".join(str(v).split()) for v in first_row]
        df = df.iloc[1:].reset_index(drop=True)
    return df


def _make_table_chunks(
    sheet_name: str, columns: list[str], rows: list[dict], rows_per_chunk: int = 20
) -> list[dict]:
    """Convert sheet rows into markdown table chunks (~20 rows each)."""
    if not rows:
        return []
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    chunks = []
    for i in range(0, len(rows), rows_per_chunk):
        batch = rows[i : i + rows_per_chunk]
        table_rows = [
            "| " + " | ".join(str(row.get(col, "")) for col in columns) + " |"
            for row in batch
        ]
        text = f"{sheet_name}\n\n{header}\n{separator}\n" + "\n".join(table_rows)
        chunks.append({"text": text, "token_count": max(1, len(text) // 4)})
    return chunks
