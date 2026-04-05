"""
A unified, highly aggressive preprocessor for handwritten math equations.
Forces optimal thresholding and morphological closing to bridge fragmented ink.
(Wrapped for compatibility with preprocessing.py)
"""
from __future__ import annotations

import os
import cv2
import numpy as np

# -------------------------
# COMPATIBILITY VARIABLES
# -------------------------
LAST_VARIANT_CHOICE = "handwriting"

# -------------------------
# THE GOLDEN OCR SETTINGS
# -------------------------
# Gentle contrast enhancement to avoid blowing out faint pencil marks
LATEX_OPTIMIZED_SETTINGS = {
    "brightness": 20.0,   
    "exposure": 15.0,     
    "contrast": 40.0,     
    "highlights": 20.0,
    "saturation": -100.0, 
    "sharpness": 100.0
}

DEFAULTS = {
    "min_width": 400,
    "min_height": 150,
    "scale_min": 2.0,
    "scale_max": 4.0,
    "small_file_bytes": 35_000,
    "adaptive_block": 41, 
    "adaptive_C": 3,      # Forced low C to extract faint ink
    "morph_kernel": 3,    # Forced Kernel 3 to bridge gaps (without smudging thick text)
    "pad": 60,            # High padding for Transformer attention
    "deskew_angle": 45.0
}

# -------------------------
# CORE IMAGE OPERATIONS
# -------------------------
def apply_editor_adjustments(img_bgr: np.ndarray, settings: dict) -> np.ndarray:
    img = img_bgr.astype(np.float32) / 255.0

    exp_gain = max(0.2, min(3.0, 1.0 + (settings["exposure"] / 100.0)))
    img = np.clip(img * exp_gain, 0.0, 1.0)

    lab = cv2.cvtColor((img * 255.0).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = cv2.split(lab)

    L = L + (settings["brightness"] / 100.0) * 50.0
    contrast_scale = max(0.3, min(3.0, 1.0 + (settings["contrast"] / 100.0)))
    L = (L - 50.0) * contrast_scale + 50.0

    if abs(settings["highlights"]) > 1e-6:
        h = settings["highlights"] / 100.0
        L = L + h * ((L / 100.0) ** 2) * 100.0

    L = np.clip(L, 0.0, 255.0)
    lab = cv2.merge((L, A, B)).astype(np.uint8)
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR).astype(np.float32) / 255.0

    hsv = cv2.cvtColor((img * 255.0).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    H, S, V = cv2.split(hsv)
    S = S * max(0.0, min(3.0, 1.0 + (settings["saturation"] / 100.0)))
    hsv = cv2.merge((H, np.clip(S, 0.0, 255.0), V)).astype(np.uint8)
    img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR).astype(np.float32) / 255.0

    if settings["sharpness"] > 0.0:
        amount = max(0.0, min(2.0, settings["sharpness"] / 100.0))
        sigma = max(0.5, min(2.0, max(img.shape[:2]) / 1200.0))
        blurred = cv2.GaussianBlur((img * 255.0).astype(np.uint8), (0, 0), sigma).astype(np.float32) / 255.0
        img = np.clip((1.0 + amount) * img - amount * blurred, 0.0, 1.0)

    return (img * 255.0).astype(np.uint8)

def ensure_scale_and_pad(img_bgr: np.ndarray, file_path: str) -> np.ndarray:
    h, w = img_bgr.shape[:2]
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

    scale = 1.0
    if w < DEFAULTS["min_width"] or h < DEFAULTS["min_height"] or file_size < DEFAULTS["small_file_bytes"]:
        scale_w = max(DEFAULTS["min_width"] / w, 1.0)
        scale_h = max(DEFAULTS["min_height"] / h, 1.0)
        scale = max(scale_w, scale_h, DEFAULTS["scale_min"])
        if file_size < DEFAULTS["small_file_bytes"]:
            scale = max(scale, 2.5)
        scale = min(scale, DEFAULTS["scale_max"])

    if scale > 1.0:
        img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    
    return img_bgr

def deskew(gray: np.ndarray) -> np.ndarray:
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(bw < 255))
    if coords.shape[0] < 10:
        return gray
    
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    if abs(angle) < 0.5 or abs(angle) > DEFAULTS["deskew_angle"]:
        return gray
        
    (h, w) = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)

def binarize_equation(gray: np.ndarray, block_size: int, c_val: int, k_size: int) -> np.ndarray:
    """Forces aggressive extraction and morphological closing to bridge gaps."""
    # Pre-blur spreads faint ink slightly
    gray_blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Adaptive threshold grabs the ink
    bw = cv2.adaptiveThreshold(
        gray_blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c_val
    )
    
    # MORPH_CLOSE joins broken pixels together without over-thickening existing heavy lines
    ink = cv2.bitwise_not(bw)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel)
    bw = cv2.bitwise_not(ink)
        
    # Remove single-pixel pepper noise
    bw = cv2.medianBlur(bw, 3)
    return bw

def load_image_safely(image_path: str) -> np.ndarray:
    """Loads an image and safely handles transparent PNGs from web canvases."""
    # Load UNCHANGED to preserve the alpha transparency channel
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
        
    # If the image has 4 channels (BGRA - transparent canvas image)
    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3] / 255.0
        bgr = img[:, :, :3]
        
        # Create a pure white background
        white_bg = np.ones_like(bgr, dtype=np.uint8) * 255
        
        # Blend the digital ink over the white background
        blended = (bgr * alpha[:, :, np.newaxis]) + (white_bg * (1.0 - alpha[:, :, np.newaxis]))
        return blended.astype(np.uint8)
        
    # If it's a standard 3-channel image (like a JPG from a phone camera)
    return img

# -------------------------
# MAIN COMPATIBLE PIPELINE
# -------------------------
def preprocess_image_auto(
    image_path: str,
    out_path: str | None = None,
    variant_hint: str | None = None,
    params: dict | None = None,
) -> str:
    print(f"Processing handwritten math: {image_path}")
    global LAST_VARIANT_CHOICE
    LAST_VARIANT_CHOICE = "handwriting" 
    
    img_bgr = load_image_safely(image_path)

    # Scale, adjust colors, and straighten
    img_bgr = ensure_scale_and_pad(img_bgr, image_path)
    editor_adjusted = apply_editor_adjustments(img_bgr, LATEX_OPTIMIZED_SETTINGS)
    gray = cv2.cvtColor(editor_adjusted, cv2.COLOR_BGR2GRAY)
    gray = deskew(gray)

    # Force the binarization with Kernel 3 (No guessing!)
    bw = binarize_equation(
        gray, 
        DEFAULTS["adaptive_block"], 
        DEFAULTS["adaptive_C"], 
        DEFAULTS["morph_kernel"]
    )

    # Add heavy padding
    pad = DEFAULTS["pad"]
    final_img = cv2.copyMakeBorder(bw, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)

    if out_path is None:
        base, ext = os.path.splitext(image_path)
        out_path = f"{base}_latex_ready.png"
        
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    cv2.imwrite(out_path, final_img)
    
    return out_path