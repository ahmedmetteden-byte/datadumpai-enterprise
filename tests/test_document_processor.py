"""
PDF text extraction tests.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from services.document_processor import DocumentProcessor


def _sample_pdf_bytes(text: str = "Annual market revenue increased 12 percent.") -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.drawString(72, 720, text)
    pdf.save()
    return buffer.getvalue()


def test_extract_pdf_text_from_bytes():
    data = _sample_pdf_bytes()
    text = DocumentProcessor._extract_pdf_text(data)

    assert "revenue" in text.lower()


def test_extract_pdf_from_upload_object():
    buffer = BytesIO(_sample_pdf_bytes("Board report summary for Q4."))
    buffer.name = "report.pdf"

    text = DocumentProcessor.extract_text(buffer)

    assert "board report" in text.lower()


def test_pdf_ocr_fallback_used_when_text_layer_empty(monkeypatch):
    data = _sample_pdf_bytes("ignored")

    monkeypatch.setattr(
        DocumentProcessor,
        "_extract_pdf_with_pypdf2",
        staticmethod(lambda *_args, **_kwargs: ""),
    )
    monkeypatch.setattr(
        DocumentProcessor,
        "_extract_pdf_with_pymupdf",
        staticmethod(lambda *_args, **_kwargs: ""),
    )
    monkeypatch.setattr(
        DocumentProcessor,
        "_extract_pdf_with_pdfplumber",
        staticmethod(lambda *_args, **_kwargs: ""),
    )
    monkeypatch.setattr(
        DocumentProcessor,
        "_extract_pdf_with_ocr",
        staticmethod(lambda *_args, **_kwargs: "OCR market revenue increased 12 percent."),
    )

    text = DocumentProcessor._extract_pdf_text(data)

    assert "OCR market revenue" in text
