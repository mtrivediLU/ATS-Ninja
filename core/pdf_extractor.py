from __future__ import annotations

import logging
import re
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
            page_text = [
                _clean_extracted_text(
                    page.extract_text(x_tolerance=1, y_tolerance=3) or page.extract_text() or ""
                )
                for page in pdf.pages
            ]

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


def _clean_extracted_text(text: str) -> str:
    """Normalize text extracted from tightly formatted resume PDFs."""
    if not text:
        return ""

    cleaned = text.replace("\x00", "")
    cleaned = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return _merge_wrapped_lines(cleaned.strip())


def _merge_wrapped_lines(text: str) -> str:
    """Rejoin sentences that the PDF layout hard-wrapped across visual lines.

    Resume bullets routinely span two or three PDF lines. Downstream
    parsing treats each line as a unit, so an unmerged continuation line
    ("time from 5 hours to minutes...") gets misread as a new entry or
    employer. A continuation is detected conservatively: the current line
    starts with a lowercase letter (or digit) and the previous line has
    content and does not end with terminal punctuation typical of a
    completed heading or field.
    """
    merged: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            merged.append("")
            continue
        previous = merged[-1] if merged else ""
        is_continuation = (
            previous
            and not previous.endswith((":", ";", "|"))
            and line[0].islower()
            and not re.match(r"^[\-*•]", line)
        )
        if is_continuation:
            merged[-1] = f"{previous} {line}"
        else:
            merged.append(line)
    return "\n".join(merged)
