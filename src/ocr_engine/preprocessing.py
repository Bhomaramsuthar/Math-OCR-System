"""
Entry point for math image cleaning. Delegates to ``preprocess_math`` by default;
use ``variant=\"pil\"`` for the legacy PIL contrast-only path.
"""

from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from src.ocr_engine.preprocess_math import (
    DEFAULTS,
    LAST_VARIANT_CHOICE,
    preprocess_image_auto,
)

# Backwards-compatible name (synced from preprocess_math after auto run).
LAST_PREPROCESS_ROUTE: str = "printed"


def _preprocess_pil_only(image_path: str, clean_path: str) -> str:
    """Original PIL pipeline: grayscale, dark invert, contrast 2.5 (+ same scale rule)."""
    from src.ocr_engine.preprocess_math import ensure_scale_and_pad, load_bgr

    print("Preprocessing image (pil):", image_path)
    img_bgr = load_bgr(image_path)
    cfg = DEFAULTS.copy()
    img_bgr = ensure_scale_and_pad(img_bgr, image_path, cfg)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    img = Image.fromarray(gray)

    mean_brightness = float(np.mean(gray))
    print(f"Mean Brightness: {mean_brightness:.2f}")
    if mean_brightness < 128:
        print("PIL: dark mode — inverting.")
        img = ImageOps.invert(img)

    clean_img = ImageEnhance.Contrast(img).enhance(2.5)
    os.makedirs(os.path.dirname(clean_path) or ".", exist_ok=True)
    clean_img.save(clean_path)
    print(f"PIL cleaned image saved to: {clean_path}")
    return clean_path


def preprocess_image(
    image_path: str,
    variant: str = "auto",
    params: dict | None = None,
) -> str:
    """
    Parameters
    ----------
    variant
        ``auto`` — ``preprocess_image_auto`` (stroke-based printed/handwriting/outline).
        ``pil`` — PIL invert + contrast only.
        ``printed`` / ``handwriting`` / ``outline`` — force that branch in
        ``preprocess_image_auto``.
    params
        Overrides merged into ``DEFAULTS`` for the OpenCV pipeline.
    """
    global LAST_PREPROCESS_ROUTE

    clean_path = image_path.replace("raw_images", "cleaned_images")
    v = (variant or "auto").lower().strip()

    if v == "pil":
        LAST_PREPROCESS_ROUTE = "pil"
        return _preprocess_pil_only(image_path, clean_path)

    hint = None
    if v in ("printed", "handwriting", "outline"):
        hint = v
    elif v in ("opencv_printed",):
        hint = "printed"
    elif v in ("opencv_handwriting",):
        hint = "handwriting"
    elif v in ("opencv_outline",):
        hint = "outline"
    # "auto" / "opencv" → hint None

    print(f"Preprocessing image ({v}): {image_path}")
    out = preprocess_image_auto(
        image_path,
        out_path=clean_path,
        variant_hint=hint,
        params=params,
    )
    LAST_PREPROCESS_ROUTE = LAST_VARIANT_CHOICE
    return out
