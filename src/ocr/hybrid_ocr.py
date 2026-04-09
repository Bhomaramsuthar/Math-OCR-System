"""
Texify with optional Pix2Tex fallback. Input image is preprocessed with PIL
(``preprocess_image``) then sent as RGB to the vision model.
"""

from __future__ import annotations

from typing import Any

from PIL import Image
from texify.inference import batch_inference

from src.app.solver import latex_parseable
from src.ocr.latex_utils import clean_ocr_latex_string
from src.ocr.preprocessing import preprocess_image

_pix2tex_model: Any = None
_pix2tex_failed: bool = False


def _get_pix2tex():
    global _pix2tex_model, _pix2tex_failed
    if _pix2tex_failed:
        return None
    if _pix2tex_model is not None:
        return _pix2tex_model
    try:
        from pix2tex.cli import LatexOCR

        _pix2tex_model = LatexOCR()
    except Exception:
        _pix2tex_failed = True
        _pix2tex_model = None
    return _pix2tex_model


def run_math_ocr(pil_image: Image.Image, texify_model, texify_processor) -> str:
    raw = batch_inference([pil_image], texify_model, texify_processor)[0]
    primary = clean_ocr_latex_string(raw)
    if latex_parseable(primary):
        return primary

    ocr = _get_pix2tex()
    if ocr is None:
        return primary

    try:
        alt = clean_ocr_latex_string(ocr(pil_image))
    except Exception:
        return primary

    if latex_parseable(alt):
        return alt

    return alt if len(alt) > len(primary) else primary


def run_math_ocr_from_file(image_path: str, texify_model, texify_processor) -> str:
    """PIL vs OpenCV preprocess (default ``auto``), then Texify (+ optional Pix2Tex)."""
    cleaned_path = preprocess_image(image_path, variant="auto")
    pil = Image.open(cleaned_path).convert("RGB")
    return clean_ocr_latex_string(run_math_ocr(pil, texify_model, texify_processor))
