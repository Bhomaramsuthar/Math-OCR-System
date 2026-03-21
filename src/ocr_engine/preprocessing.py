import cv2
import numpy as np

def preprocess_image(image_path, output_path=None):
    """
    Advanced preprocessing pipeline that dynamically adjusts stroke thickness
    based on the input image (handles both Paint doodles and clean textbooks).
    """
    # 1. Read Image
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    # 2. Invert (Ink becomes white, background black for CV math)
    inverted = cv2.bitwise_not(img)

    # 3. Clean up noise and Threshold
    _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 4. Smart Cropping (tightest bounding box around the ink)
    coords = cv2.findNonZero(thresh)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        cropped = thresh[y:y+h, x:x+w]
    else:
        cropped = thresh

    # 5. Scale Normalization (Force height to 96px, preserve aspect ratio)
    target_height = 96
    aspect_ratio = cropped.shape[1] / cropped.shape[0]
    target_width = int(target_height * aspect_ratio)

    # Use INTER_AREA for shrinking, INTER_CUBIC for enlarging
    if cropped.shape[0] > target_height:
        resized = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_AREA)
    else:
        resized = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_CUBIC)

    # 6. THE SMART VISION: Calculate average ink thickness
    dist = cv2.distanceTransform(resized, cv2.DIST_L2, 3)
    max_thickness = np.max(dist)
    
    # Dynamically adjust the stroke width
    processed_ink = resized.copy()
    
    if max_thickness < 2.5:
        # Ink is too thin (e.g., MS Paint). Thicken it.
        kernel = np.ones((2, 2), np.uint8)
        processed_ink = cv2.dilate(resized, kernel, iterations=1)
        print(f"Smart Vision: Detected thin lines (Thickness: {max_thickness:.2f}). Thickening applied.")
        
    elif max_thickness > 6.0:
        # Ink is too thick (e.g., heavy marker). Thin it.
        kernel = np.ones((2, 2), np.uint8)
        processed_ink = cv2.erode(resized, kernel, iterations=1)
        print(f"Smart Vision: Detected thick lines (Thickness: {max_thickness:.2f}). Thinning applied.")
        
    else:
        print(f"Smart Vision: Detected normal lines (Thickness: {max_thickness:.2f}). No adjustment needed.")

    # 7. Add Standardized Padding (Pix2Tex needs breathing room)
    pad = 32
    padded = cv2.copyMakeBorder(processed_ink, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)

    # 8. Re-invert to black text on white background
    final_img = cv2.bitwise_not(padded)

    if output_path:
        cv2.imwrite(output_path, final_img)

    return final_img