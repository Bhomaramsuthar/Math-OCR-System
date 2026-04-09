"""Shared helpers for LaTeX strings coming from OCR or the UI."""

import re


def clean_ocr_latex_string(s: str) -> str:
    """Strip wrappers, trailing period, and common Texify bibliography hallucinations."""
    t = s.strip()
    if t.endswith("."):
        t = t[:-1].strip()
    if t.startswith("$$") and t.endswith("$$"):
        t = t[2:-2].strip()
    elif t.startswith("$") and t.endswith("$"):
        t = t[1:-1].strip()
    cut = re.search(r",\s*\[\d{1,3}\]\s*[A-Za-z]", t)
    if cut:
        t = t[: cut.start()].rstrip()
    return t
