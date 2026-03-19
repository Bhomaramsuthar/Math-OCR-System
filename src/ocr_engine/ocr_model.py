from PIL import Image
from pix2tex.cli import LatexOCR
import cv2
import numpy as np

class MathOCR:
    def __init__(self):
        """Initializes the Pix2Tex model once."""
        print("Initializing MathOCR Model...")
        self.model = LatexOCR()

    def predict(self, image_input):
        """
        Takes an image (either a file path or an OpenCV numpy array)
        and returns the predicted LaTeX string.
        """
        # If the input is an OpenCV image (numpy array), convert it to a PIL Image
        if isinstance(image_input, np.ndarray):
            # Convert grayscale OpenCV image to PIL Image format
            if len(image_input.shape) == 2: 
                image_input = cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
            else: 
                image_input = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            
            img = Image.fromarray(image_input)
            
        elif isinstance(image_input, str):
            # If a file path is passed directly
            img = Image.open(image_input)
        else:
            raise TypeError("Input must be a file path or an OpenCV image array.")

        # Run inference
        return self.model(img)