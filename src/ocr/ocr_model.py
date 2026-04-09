from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
import io

class MathOCR:
    def __init__(self):
        print("Initializing Custom Hugging Face OCR Model...")
        
        # We check if you have a GPU available; otherwise, we use CPU
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Loading model onto: {self.device}")

        # TrOCR outputs plain text, not LaTeX. The HTTP API uses Texify (+ optional
        # Pix2Tex) in ``main.py`` for math. This class remains useful for
        # experiments / non-math handwriting.
        model_name = "microsoft/trocr-base-handwritten"

        try:
            # The Processor handles the image resizing and normalization
            self.processor = TrOCRProcessor.from_pretrained(model_name)
            # The Model is the actual neural network
            self.model = VisionEncoderDecoderModel.from_pretrained(model_name).to(self.device)
            print("Hugging Face Model loaded successfully!")
        except Exception as e:
            print(f"CRITICAL ERROR loading model: {e}")

    def predict(self, image_array):
        """
        Takes an OpenCV image array, converts it for Hugging Face,
        runs a forward pass, and returns the predicted string.
        """
        try:
            # 1. Convert OpenCV image (NumPy array) to a PIL Image (which Hugging Face expects)
            # Assuming the image coming from preprocessing is grayscale, we convert to RGB
            pil_image = Image.fromarray(image_array).convert("RGB")

            # 2. Preprocess the image into PyTorch tensors
            pixel_values = self.processor(images=pil_image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)

            # 3. Run Inference (Generate the text)
            generated_ids = self.model.generate(pixel_values)

            # 4. Decode the tensor output back into a human-readable string
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            print(f"AI Prediction: {generated_text}")
            return generated_text

        except Exception as e:
            print(f"Error during model inference: {e}")
            return "ERROR_INFERENCE"