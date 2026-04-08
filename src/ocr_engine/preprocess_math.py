"""
The Ultimate Preprocessor for Hybrid Math OCR.
Features:
- Canvas PNG Transparency Handler
- Digital Screenshot Bypass (Sensor Noise Detection)
- Smart Stroke-Width Calculation (Prevents blobs)
- Extreme Shadow-Crushing Contrast (For faint pencil)
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
    "pad": 60,
    "deskew_angle": 45.0,
    "stroke_threshold": 5.0 # Boundary between "broken ink" and "thick marker"
}

# -------------------------
# CORE IMAGE OPERATIONS
# -------------------------

def invert_if_dark(gray: np.ndarray) -> np.ndarray:
    """
    Calculates average brightness. If the image is mostly dark 
    (e.g., dark mode screenshot, chalkboard), it inverts the colors.
    """
    mean_brightness = np.mean(gray)
    
    # 127 is exactly halfway between 0 (pure black) and 255 (pure white)
    if mean_brightness < 127:
        print(f"Dark background detected (Brightness: {mean_brightness:.1f}). Inverting colors...")
        return cv2.bitwise_not(gray)
        
    return gray

def load_image_safely(image_path: str) -> np.ndarray:
    """Loads an image and safely handles transparent PNGs from web canvases."""
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
        
    # If the image has 4 channels (BGRA - transparent canvas image)
    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha = img[:, :, 3] / 255.0
        bgr = img[:, :, :3]
        white_bg = np.ones_like(bgr, dtype=np.uint8) * 255
        blended = (bgr * alpha[:, :, np.newaxis]) + (white_bg * (1.0 - alpha[:, :, np.newaxis]))
        return blended.astype(np.uint8)
        
    return img

def is_digital_screenshot(img_bgr: np.ndarray) -> bool:
    """Detects if an image is a digital screenshot by checking for sensor noise."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    patch = min(30, h // 4, w // 4)
    corners = [
        gray[0:patch, 0:patch],
        gray[0:patch, w-patch:w],
        gray[h-patch:h, 0:patch],
        gray[h-patch:h, w-patch:w]
    ]
    # A perfectly flat background has a standard deviation near 0.
    flat_corners = sum(1 for c in corners if np.std(c) < 1.5)
    return flat_corners >= 2

def apply_editor_adjustments(img_bgr: np.ndarray, settings: dict) -> np.ndarray:
    """Crushes shadows and maximizes ink visibility."""
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
    """Scales up small images so Texify has enough pixels to read."""
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
    """Straightens tilted handwriting."""
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(bw < 255))
    if coords.shape[0] < 10: return gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45: angle = -(90 + angle)
    else: angle = -angle
    if abs(angle) < 0.5 or abs(angle) > DEFAULTS["deskew_angle"]: return gray
    (h, w) = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)

def estimate_stroke_width(bw: np.ndarray) -> float:
    """Calculates the median thickness of the black lines in the image."""
    ink = (bw == 0).astype(np.uint8)
    if ink.sum() == 0: return 999.0
    dist = cv2.distanceTransform(255 - bw, cv2.DIST_L2, 5)
    d_vals = dist[ink.astype(bool)]
    if d_vals.size == 0: return 999.0
    return float(2.0 * np.median(d_vals))

def smart_binarize(gray: np.ndarray, block_size: int) -> np.ndarray:
    """Uses stroke width to decide if the image needs morphological closing."""
    gray_blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Pass 1: Standard clean threshold (Safe for thick markers)
    bw_standard = cv2.adaptiveThreshold(
        gray_blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, 10
    )
    
    # Measure the strokes!
    stroke_width = estimate_stroke_width(bw_standard)
    print(f"Smart-Tuner: Measured Stroke Width = {stroke_width:.2f}px")

    # If strokes are thin/fragmented, apply the heavy fix. Otherwise, leave it alone.
    if stroke_width < DEFAULTS["stroke_threshold"]:
        print("Smart-Tuner: Fragmented ink detected. Applying Kernel 3 fix...")
        bw_aggro = cv2.adaptiveThreshold(
            gray_blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, 3
        )
        ink = cv2.bitwise_not(bw_aggro)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel)
        bw_final = cv2.bitwise_not(ink)
    else:
        print("Smart-Tuner: Solid ink detected. Skipping morphological distortion.")
        bw_final = bw_standard
        
    return cv2.medianBlur(bw_final, 3)

# -------------------------
# MAIN COMPATIBLE PIPELINE
# -------------------------
def preprocess_image_auto(
    image_path: str,
    out_path: str | None = None,
    variant_hint: str | None = None,
    params: dict | None = None,
) -> str:
    print(f"Processing math image: {image_path}")
    global LAST_VARIANT_CHOICE
    LAST_VARIANT_CHOICE = "handwriting" 
    
    # 1. Load image safely (preserves web canvas drawings)
    img_bgr = load_image_safely(image_path)

    # 2. DIGITAL BYPASS LAYER
    if is_digital_screenshot(img_bgr):
        print("Bypass Layer: Digital screenshot/canvas detected! Bypassing heavy preprocessing.")
        img_bgr = ensure_scale_and_pad(img_bgr, image_path)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        #Dark mode
        gray = invert_if_dark(gray)

        # Gentle OTSU threshold for digital text
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
    # 3. HANDWRITTEN PAPER PIPELINE
    else:
        print("Bypass Layer: Physical photo detected. Applying shadow-crushing pipeline...")
        img_bgr = ensure_scale_and_pad(img_bgr, image_path)
        editor_adjusted = apply_editor_adjustments(img_bgr, LATEX_OPTIMIZED_SETTINGS)
        gray = cv2.cvtColor(editor_adjusted, cv2.COLOR_BGR2GRAY)
        
        #Dark mode
        gray = invert_if_dark(gray)
        
        gray = deskew(gray)
        bw = smart_binarize(gray, DEFAULTS["adaptive_block"])

    # 4. FINAL PADDING (Crucial for Transformer models)
    pad = DEFAULTS["pad"]
    final_img = cv2.copyMakeBorder(bw, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)

    if out_path is None:
        base, ext = os.path.splitext(image_path)
        out_path = f"{base}_latex_ready.png"
        
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    cv2.imwrite(out_path, final_img)
    
    return out_path