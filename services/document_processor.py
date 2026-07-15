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
            truncated = False

            if max_tabular_rows is not None and len(df) > max_tabular_rows:
                df = df.head(max_tabular_rows)
                truncated = True

            text = df.to_string(index=False)

            if truncated:
                text += (
                    f"\n\n[… first {max_tabular_rows} rows only; "
                    "remaining rows omitted for faster processing …]"
                )

            return text

        if suffix == ".xlsx":
            df = pd.read_excel(uploaded_file)
            truncated = False

            if max_tabular_rows is not None and len(df) > max_tabular_rows:
                df = df.head(max_tabular_rows)
                truncated = True

            text = df.to_string(index=False)

            if truncated:
                text += (
                    f"\n\n[… first {max_tabular_rows} rows only; "
                    "remaining rows omitted for faster processing …]"
                )

            return text

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
