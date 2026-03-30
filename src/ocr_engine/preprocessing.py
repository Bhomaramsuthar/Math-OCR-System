import os
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

def preprocess_image(image_path: str) -> str:
    """
    Detects dark-mode images, inverts them to white, and gently boosts contrast
    without destroying the smooth edges of the handwriting.
    """
    print(f"Preprocessing image: {image_path}")
    
    # 1. Open the image and convert to Grayscale ('L')
    img = Image.open(image_path).convert('L')
    
    # 2. THE DARK MODE FIX
    # Convert image data to a numpy array to calculate average brightness
    img_array = np.array(img)
    mean_brightness = np.mean(img_array)
    print(f"Mean Brightness: {mean_brightness:.2f}")

    # Threshold for deciding if image is dark (0=black, 255=white). 
    # 128 is middle gray. If below this, it's a dark background.
    if mean_brightness < 128:
        print("Detected Dark Mode image. Inverting colors.")
        # Turns dark background white, white text black. Perfect for Texify!
        img = ImageOps.invert(img)
    
    # 3. Boost the Contrast (Gently)
    # This washes out shadows but keeps the pen strokes smooth
    enhancer = ImageEnhance.Contrast(img)
    clean_img = enhancer.enhance(2.5)

    # 4. Save the cleaned image to pass to the AI
    clean_path = image_path.replace("raw_images", "cleaned_images")
    
    # Ensure the cleaned_images directory exists
    os.makedirs(os.path.dirname(clean_path), exist_ok=True)
    
    clean_img.save(clean_path)
    print(f"Cleaned image saved to: {clean_path}")
    
    return clean_path