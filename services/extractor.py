"""
extractor.py — pulls text out of a PDF file.
Tries normal text extraction first (fast, works for digital PDFs).
Falls back to OCR only if that gives us almost nothing (scanned PDFs).
"""

import pdfplumber
import pytesseract
from pdf2image import convert_from_path


def extract_text(pdf_path):
    """
    Returns (text, used_ocr) — the extracted text, and whether OCR was needed.
    """
    text = _extract_with_pdfplumber(pdf_path)

    # If we got barely any text, this is probably a scanned image PDF.
    # 50 characters is a rough "basically empty" threshold.
    if len(text.strip()) < 50:
        text = _extract_with_ocr(pdf_path)
        return text, True

    return text, False


def _extract_with_pdfplumber(pdf_path):
    """Extracts text directly from a digital (non-scanned) PDF."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_with_ocr(pdf_path):
    """
    Converts each PDF page to an image, then reads text from the image.
    Used for scanned resumes where there's no real text layer.
    """
    text_parts = []
    pages = convert_from_path(pdf_path)  # returns a list of images, one per page
    for page_image in pages:
        page_text = pytesseract.image_to_string(page_image)
        text_parts.append(page_text)
    return "\n".join(text_parts)