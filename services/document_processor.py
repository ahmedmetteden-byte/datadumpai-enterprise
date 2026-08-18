"""
DataDumpAI Enterprise
Document Processing Service
"""

from __future__ import annotations

import logging
import time
from io import BytesIO
from pathlib import Path
from typing import Callable

import pandas as pd
from PyPDF2 import PdfReader
from docx import Document

import config

logger = logging.getLogger(__name__)


class DocumentProcessor:
    @staticmethod
    def extract_text(
        uploaded_file,
        *,
        max_pdf_pages: int | None = None,
        max_tabular_rows: int | None = None,
    ) -> str:
        suffix = Path(uploaded_file.name).suffix.lower()

        if suffix == ".pdf":
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            data = uploaded_file.read()
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            return DocumentProcessor._extract_pdf_text(
                data,
                max_pdf_pages=max_pdf_pages,
            )

        if suffix == ".docx":
            doc = Document(uploaded_file)
            return "\n".join(p.text for p in doc.paragraphs)

        if suffix == ".txt":
            return uploaded_file.read().decode("utf-8")

        if suffix == ".csv":
            df = pd.read_csv(uploaded_file)
            return DocumentProcessor._render_tabular_block(
                df, heading=None, max_tabular_rows=max_tabular_rows
            )

        if suffix == ".xlsx":
            # sheet_name=None returns every sheet as {name: DataFrame} —
            # pd.read_excel's default keeps only the first sheet, silently
            # discarding the rest of the workbook.
            sheets = pd.read_excel(uploaded_file, sheet_name=None)
            non_empty_sheets = {
                name: sheet_df for name, sheet_df in sheets.items() if len(sheet_df.columns) > 0
            }

            if not non_empty_sheets:
                return ""

            blocks: list[str] = []
            multi_sheet = len(non_empty_sheets) > 1

            if multi_sheet:
                blocks.append(
                    f"Workbook contains {len(non_empty_sheets)} sheets: "
                    f"{', '.join(non_empty_sheets)}."
                )

            for name, sheet_df in non_empty_sheets.items():
                blocks.append(
                    DocumentProcessor._render_tabular_block(
                        sheet_df,
                        heading=f"Sheet: {name}" if multi_sheet else None,
                        max_tabular_rows=max_tabular_rows,
                    )
                )

            return "\n\n".join(blocks)

        return ""

    @staticmethod
    def extract_text_from_path(
        file_path: Path | str,
        *,
        max_pdf_pages: int | None = None,
        max_tabular_rows: int | None = None,
    ) -> str:
        """Extract text from a file on disk."""

        path = Path(file_path)
        suffix = path.suffix.lower()
        try:
            file_size = path.stat().st_size
        except OSError:
            file_size = None

        logger.info(
            "extract_text_from_path start path=%s suffix=%s file_size=%s "
            "max_pdf_pages=%s max_tabular_rows=%s",
            path,
            suffix,
            file_size,
            max_pdf_pages,
            max_tabular_rows,
        )

        try:
            if suffix == ".pdf":
                text = DocumentProcessor._extract_pdf_text(
                    path.read_bytes(),
                    max_pdf_pages=max_pdf_pages,
                )
            else:
                buffer = BytesIO(path.read_bytes())
                buffer.name = path.name
                text = DocumentProcessor.extract_text(
                    buffer,
                    max_pdf_pages=max_pdf_pages,
                    max_tabular_rows=max_tabular_rows,
                )

            logger.info(
                "extract_text_from_path finished success=True chars=%d",
                len(text or ""),
            )
            return text
        except Exception:
            logger.exception("Document extraction crashed")
            raise

    @staticmethod
    def _truncate_dataframe(
        df: pd.DataFrame, max_tabular_rows: int | None
    ) -> tuple[pd.DataFrame, bool]:
        if max_tabular_rows is not None and len(df) > max_tabular_rows:
            return df.head(max_tabular_rows), True
        return df, False

    @staticmethod
    def _format_cell_value(value) -> str:
        """Render one cell for both the stats block and the markdown table.
        Numeric values are comma-formatted (never scientific notation, so
        an LLM can read them reliably); NaN/NaT become an empty string
        rather than a literal "nan"; a literal "|" is substituted (not
        escaped) since report_markdown_renderer.py's table parser splits
        on "|" without any escape handling."""

        if value is None:
            return ""
        try:
            if pd.isna(value):
                return ""
        except (TypeError, ValueError):
            pass

        if isinstance(value, bool):
            return "True" if value else "False"

        try:
            number = float(value)
        except (TypeError, ValueError):
            number = None

        if number is not None:
            if number == int(number) and abs(number) < 1e15:
                return f"{int(number):,}"
            return f"{number:,.4f}".rstrip("0").rstrip(".")

        text = str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        return text.replace("|", "/").strip()

    @staticmethod
    def _dataframe_stats_block(df: pd.DataFrame) -> str:
        """Verified, computed-by-pandas summary statistics per numeric
        column — the primary numeric payload for the LLM to cite, since it
        should never be left to eyeball totals/averages off a rendered
        table itself."""

        numeric_columns = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]

        if not numeric_columns:
            return "No numeric columns detected in this data."

        lines = ["Summary statistics (computed across all rows):"]
        for column in numeric_columns:
            series = df[column].dropna()
            if series.empty:
                lines.append(f"- {column}: no non-null values.")
                continue
            lines.append(
                f"- {column}: count={len(series)}, "
                f"sum={DocumentProcessor._format_cell_value(series.sum())}, "
                f"mean={DocumentProcessor._format_cell_value(series.mean())}, "
                f"min={DocumentProcessor._format_cell_value(series.min())}, "
                f"max={DocumentProcessor._format_cell_value(series.max())}"
            )
        return "\n".join(lines)

    @staticmethod
    def _dataframe_markdown_table(df: pd.DataFrame) -> str:
        """GFM pipe table — survives a hard chunk-boundary cut far better
        than a fixed-width df.to_string() table (pipes stay distinguishable
        even once whitespace gets collapsed downstream; column alignment
        does not), and parses directly via
        report_markdown_renderer.py's existing table block support."""

        headers = [DocumentProcessor._format_cell_value(column) for column in df.columns]
        header_row = "| " + " | ".join(headers) + " |"
        separator_row = "| " + " | ".join("---" for _ in headers) + " |"

        if df.empty:
            return f"{header_row}\n{separator_row}\n(no data rows)"

        data_rows = [
            "| " + " | ".join(DocumentProcessor._format_cell_value(value) for value in row) + " |"
            for row in df.itertuples(index=False, name=None)
        ]
        return "\n".join([header_row, separator_row, *data_rows])

    @staticmethod
    def _render_tabular_block(
        df: pd.DataFrame,
        *,
        heading: str | None,
        max_tabular_rows: int | None,
    ) -> str:
        """Stats block first, then the table — every clip/budget mechanism
        downstream (SpaReportGenerationService._clip,
        report_retrieval_service.py's per-document/total budgets) truncates
        from the tail, so putting verified numbers first maximizes the odds
        they survive intact even when the full table gets cut."""

        stats = DocumentProcessor._dataframe_stats_block(df)
        truncated_df, truncated = DocumentProcessor._truncate_dataframe(df, max_tabular_rows)
        table = DocumentProcessor._dataframe_markdown_table(truncated_df)

        parts: list[str] = []
        if heading:
            parts.append(f"### {heading}")
        parts.append(stats)
        if truncated:
            parts.append(
                f"(stats computed across all {len(df)} rows; "
                f"table below shows first {max_tabular_rows})"
            )
        parts.append(table)
        return "\n\n".join(parts)

    @staticmethod
    def _call_pdf_extractor(
        name: str,
        extractor: Callable[..., str],
        data: bytes,
        *,
        max_pdf_pages: int | None = None,
    ) -> str:
        """Run one PDF backend with before/after timing logs."""

        logger.info(
            "PDF extractor %s starting data_size=%s max_pdf_pages=%s",
            name,
            len(data),
            max_pdf_pages,
        )
        started = time.perf_counter()
        try:
            text = extractor(data, max_pdf_pages=max_pdf_pages) or ""
        except Exception:
            elapsed = time.perf_counter() - started
            logger.exception(
                "PDF extractor %s crashed after %.3fs data_size=%s max_pdf_pages=%s",
                name,
                elapsed,
                len(data),
                max_pdf_pages,
            )
            raise

        elapsed = time.perf_counter() - started
        logger.info(
            "PDF extractor %s returned chars=%d elapsed=%.3fs",
            name,
            len(text),
            elapsed,
        )
        return text

    @staticmethod
    def _extract_pdf_text(
        data: bytes,
        *,
        max_pdf_pages: int | None = None,
    ) -> str:
        """Try text-layer engines, then OCR for scanned PDFs."""

        extractors = (
            ("pypdf2", DocumentProcessor._extract_pdf_with_pypdf2),
            ("pymupdf", DocumentProcessor._extract_pdf_with_pymupdf),
            ("pdfplumber", DocumentProcessor._extract_pdf_with_pdfplumber),
        )

        best_text = ""
        for name, extractor in extractors:
            try:
                text = DocumentProcessor._call_pdf_extractor(
                    name,
                    extractor,
                    data,
                    max_pdf_pages=max_pdf_pages,
                )
            except Exception:
                # Already logged with traceback inside _call_pdf_extractor.
                # Continue to the next backend so one broken engine does not
                # abort extraction entirely.
                continue

            if len(text.strip()) > len(best_text.strip()):
                best_text = text

            if len(best_text.strip()) >= 200:
                break

        if len(best_text.strip()) < config.PDF_OCR_MIN_TEXT_CHARS:
            logger.info(
                "PDF text layer below OCR threshold (%s); attempting OCR data_size=%s "
                "best_stripped=%s",
                config.PDF_OCR_MIN_TEXT_CHARS,
                len(data),
                len(best_text.strip()),
            )
            ocr_text = DocumentProcessor._call_pdf_extractor(
                "ocr",
                DocumentProcessor._extract_pdf_with_ocr,
                data,
                max_pdf_pages=max_pdf_pages,
            )
            if len(ocr_text.strip()) > len(best_text.strip()):
                best_text = ocr_text

        if best_text.strip():
            return DocumentProcessor._append_pdf_truncation_note(
                best_text,
                data=data,
                max_pdf_pages=max_pdf_pages,
            )

        logger.warning(
            "All PDF extractors returned empty text data_size=%s max_pdf_pages=%s",
            len(data),
            max_pdf_pages,
        )
        return best_text

    @staticmethod
    def _append_pdf_truncation_note(
        text: str,
        *,
        data: bytes,
        max_pdf_pages: int | None,
    ) -> str:
        if max_pdf_pages is None:
            return text

        try:
            total_pages = DocumentProcessor._pdf_page_count(data)
        except Exception:
            return text

        if total_pages > max_pdf_pages:
            return (
                text
                + f"\n\n[… first {max_pdf_pages} PDF pages only; "
                "remaining pages omitted for faster processing …]"
            )

        return text

    @staticmethod
    def _pdf_page_count(data: bytes) -> int:
        try:
            import fitz

            with fitz.open(stream=data, filetype="pdf") as document:
                return len(document)
        except Exception:
            reader = PdfReader(BytesIO(data), strict=False)
            return len(reader.pages)

    @staticmethod
    def _extract_pdf_with_pypdf2(
        data: bytes,
        *,
        max_pdf_pages: int | None = None,
    ) -> str:
        reader = PdfReader(BytesIO(data), strict=False)
        pages = reader.pages
        truncated = max_pdf_pages is not None and len(pages) > max_pdf_pages

        if truncated:
            pages = pages[:max_pdf_pages]

        return "\n".join(page.extract_text() or "" for page in pages)

    @staticmethod
    def _extract_pdf_with_pymupdf(
        data: bytes,
        *,
        max_pdf_pages: int | None = None,
    ) -> str:
        try:
            import fitz
        except ImportError:
            return ""

        best = ""
        with fitz.open(stream=data, filetype="pdf") as document:
            if document.is_encrypted and not document.authenticate(""):
                return ""

            page_count = len(document)
            limit = page_count if max_pdf_pages is None else min(page_count, max_pdf_pages)

            for index in range(limit):
                page = document[index]
                candidates = [
                    page.get_text("text", sort=True) or "",
                    DocumentProcessor._pymupdf_blocks_text(page),
                    page.get_text() or "",
                ]
                page_text = max(candidates, key=lambda value: len(value.strip()))
                if page_text.strip():
                    best = f"{best}\n{page_text}" if best else page_text

        return best

    @staticmethod
    def _pymupdf_blocks_text(page) -> str:
        try:
            blocks = page.get_text("blocks") or []
        except Exception:
            return ""

        parts: list[str] = []
        for block in blocks:
            if len(block) >= 5 and isinstance(block[4], str) and block[4].strip():
                parts.append(block[4].strip())
        return "\n".join(parts)

    @staticmethod
    def _ocr_page_limit(max_pdf_pages: int | None, page_count: int) -> int:
        if max_pdf_pages is not None:
            return min(page_count, max_pdf_pages, config.PDF_OCR_MAX_PAGES)
        return min(page_count, config.PDF_OCR_MAX_PAGES)

    @staticmethod
    def _extract_pdf_with_ocr(
        data: bytes,
        *,
        max_pdf_pages: int | None = None,
    ) -> str:
        if not config.PDF_OCR_ENABLED:
            return ""

        text = DocumentProcessor._call_pdf_extractor(
            "tesseract_ocr",
            DocumentProcessor._extract_pdf_with_tesseract_ocr,
            data,
            max_pdf_pages=max_pdf_pages,
        )
        if text.strip():
            return text

        return DocumentProcessor._call_pdf_extractor(
            "rapidocr",
            DocumentProcessor._extract_pdf_with_rapidocr,
            data,
            max_pdf_pages=max_pdf_pages,
        )

    @staticmethod
    def _extract_pdf_with_tesseract_ocr(
        data: bytes,
        *,
        max_pdf_pages: int | None = None,
    ) -> str:
        try:
            import fitz
        except ImportError:
            return ""

        parts: list[str] = []
        with fitz.open(stream=data, filetype="pdf") as document:
            if document.is_encrypted and not document.authenticate(""):
                return ""

            limit = DocumentProcessor._ocr_page_limit(max_pdf_pages, len(document))
            for index in range(limit):
                page = document[index]
                try:
                    text_page = page.get_textpage_ocr(dpi=200, full=True)
                    page_text = page.get_text(textpage=text_page) or ""
                except Exception:
                    page_text = ""
                if page_text.strip():
                    parts.append(page_text.strip())

        if not parts:
            return ""

        joined = "\n\n".join(parts)
        return joined + "\n\n[… text extracted with OCR …]"

    @staticmethod
    def _extract_pdf_with_rapidocr(
        data: bytes,
        *,
        max_pdf_pages: int | None = None,
    ) -> str:
        try:
            import fitz
            import numpy as np
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            return ""

        engine = RapidOCR()
        parts: list[str] = []

        with fitz.open(stream=data, filetype="pdf") as document:
            if document.is_encrypted and not document.authenticate(""):
                return ""

            limit = DocumentProcessor._ocr_page_limit(max_pdf_pages, len(document))
            for index in range(limit):
                page = document[index]
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                channels = pixmap.n
                image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                    pixmap.height,
                    pixmap.width,
                    channels,
                )
                if channels == 4:
                    image = image[:, :, :3]

                result, _ = engine(image)
                if not result:
                    continue

                page_lines = [str(item[1]).strip() for item in result if item[1]]
                if page_lines:
                    parts.append("\n".join(page_lines))

        if not parts:
            return ""

        joined = "\n\n".join(parts)
        return joined + "\n\n[… text extracted with OCR …]"

    @staticmethod
    def _extract_pdf_with_pdfplumber(
        data: bytes,
        *,
        max_pdf_pages: int | None = None,
    ) -> str:
        try:
            import pdfplumber
        except ImportError:
            return ""

        parts: list[str] = []

        with pdfplumber.open(BytesIO(data)) as document:
            pages = document.pages
            if max_pdf_pages is not None:
                pages = pages[:max_pdf_pages]

            for page in pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text)
                    continue

                for table in page.extract_tables() or []:
                    for row in table:
                        cells = [str(cell or "").strip() for cell in row]
                        if any(cells):
                            parts.append(" | ".join(cells))

        return "\n".join(parts)
