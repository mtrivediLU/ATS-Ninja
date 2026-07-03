from __future__ import annotations

import logging
from typing import Any

import pdfplumber


logger = logging.getLogger(__name__)


def extract_text_from_pdf(uploaded_file: Any) -> str:
    """Extract text from all pages of an uploaded PDF file."""
    if uploaded_file is None:
        return ""

    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        with pdfplumber.open(uploaded_file) as pdf:
            page_text = [page.extract_text() or "" for page in pdf.pages]

        return "\n\n".join(text.strip() for text in page_text if text.strip()).strip()
    except Exception:
        logger.exception("Failed to extract text from PDF.")
        return ""
    finally:
        try:
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
        except Exception:
            logger.debug("Unable to reset uploaded PDF pointer.", exc_info=True)
