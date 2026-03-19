import cv2
import numpy as np

def preprocess_image(image_path, output_path=None):
    """
    Crops, resizes to a standardized AI-friendly scale, thickens, and pads.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    # 1. Invert and Threshold (Pure black and white)
    inverted = cv2.bitwise_not(img)
    _, thresh = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 2. Crop tightly around the ink
    coords = cv2.findNonZero(thresh)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        cropped = thresh[y:y+h, x:x+w]
    else:
        cropped = thresh

    # 3. RESIZE: Force the height to be 96 pixels (AI textbook scale)
    target_height = 96
    aspect_ratio = cropped.shape[1] / cropped.shape[0]
    target_width = int(target_height * aspect_ratio)
    
    # INTER_AREA is best for shrinking images
    resized = cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_AREA)

    # 4. Dilate slightly to make strokes bold at the new smaller scale
    #kernel = np.ones((2, 2), np.uint8)
    #thickened = cv2.dilate(resized, kernel, iterations=1)

    # 5. Add a uniform white border
    pad = 32
    padded = cv2.copyMakeBorder(cropped, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)

    # 6. Invert back (White background, black text)
    final_img = cv2.bitwise_not(padded)

    if output_path:
        cv2.imwrite(output_path, final_img)

    return final_img