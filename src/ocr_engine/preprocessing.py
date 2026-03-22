import cv2
import numpy as np
import os

def preprocess_image(image_path: str) -> str:
    """
    Takes a raw smartphone photo, resizes it, and applies adaptive thresholding
    to create a perfect black-and-white scan for the AI.
    """
    print(f"Preprocessing raw image: {image_path}")
    
    # 1. Read the image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    # 2. THE RESIZE FIX
    # The AI hates massive phone photos. We shrink it to a max height of 384px
    # while maintaining the exact aspect ratio.
    max_height = 384
    h, w = img.shape[:2]
    if h > max_height:
        scaling_factor = max_height / float(h)
        new_size = (int(w * scaling_factor), max_height)
        img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

    # 3. Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 4. THE SHADOW FIX (Adaptive Thresholding)
    # This ignores overall lighting and looks at local areas to separate ink from paper.
    # It forces the background to pure white (255) and the ink to pure black (0).
    binary_img = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        blockSize=21, 
        C=11
    )

    # 5. Denoise (Wipes away tiny specks of dust or rogue pixels)
    clean_img = cv2.fastNlMeansDenoising(binary_img, h=15)

    # 6. Save the cleaned image to pass to the AI
    clean_path = image_path.replace("raw_images", "cleaned_images")
    
    # Ensure the cleaned_images directory exists
    os.makedirs(os.path.dirname(clean_path), exist_ok=True)
    
    cv2.imwrite(clean_path, clean_img)
    print(f"Cleaned image saved to: {clean_path}")
    
    return clean_path