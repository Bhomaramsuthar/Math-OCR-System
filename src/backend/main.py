from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os

# 1. THE AI IMPORTS
from PIL import Image
from pix2tex.cli import LatexOCR
import pix2tex  # <--- Added to locate the package directory
from munch import Munch

# Import our custom Database and Parser pipeline
from src.ocr_engine.preprocessing import preprocess_image
from src.ocr_engine.latex_parser import EquationParser
from src.backend.database import save_equation

app = FastAPI(title="Math OCR API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Booting up server and loading AI models into memory...")

# 2. THE BLUEPRINT FIX
# Dynamically locate the default architecture blueprint inside your virtual environment
pix2tex_dir = os.path.dirname(pix2tex.__file__)
default_config_path = os.path.join(pix2tex_dir, 'model', 'settings', 'config.yaml')

# THE NEW FIX: The Absolute Path to the Brain
# This mathematically calculates the root folder (math-ocr-system) no matter where the server runs
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# VERY IMPORTANT: Ensure your extracted file is actually named EXACTLY "weights.pth". 
# If it is named something like "bhomaram_custom_model.pth", change the string below to match!
custom_brain_path = os.path.join(ROOT_DIR, 'bhomaram_custom_math_model_e03_step250.pth') 

args = Munch({
    'checkpoint': custom_brain_path, # <--- We pass the absolute path here
    'config': default_config_path,   
    'no_cuda': False,            
    'no_resize': False
})

ocr_system = LatexOCR()

parser = EquationParser()
print("Models loaded successfully!")

# ... (Keep all your @app.get and @app.post routes exactly the same below here) ...
@app.get("/")
def read_root():
    return {"status": "online", "message": "Math OCR API is running!"}

@app.post("/upload-equation")
async def process_equation(file: UploadFile = File(...)):
    """
    Receives an image, runs the ML pipeline, saves to DB, and returns JSON.
    """
    try:
        # 1. Save uploaded file temporarily
        temp_path = f"data/raw_images/{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Run Pipeline
        # (Optional: You can still run your custom preprocess_image here if it overwrites the temp_path)
        cleaned_image_path = preprocess_image(temp_path) 
        
        # 3. THE PREDICTION UPDATE
        # Pix2Tex requires the image to be opened as a PIL RGB object before predicting
        img = Image.open(temp_path).convert('RGB')
        latex_str = ocr_system(img)
        
        # Pass the newly generated LaTeX string into your existing parser
        parsed_data = parser.parse_to_dict(latex_str)

        # 4. Save to DB using a strict copy
        db_data = parsed_data.copy()
        raw_db_id = save_equation(db_data)

        # 5. THE NUCLEAR FIX: 
        # Force the database ID into a standard Python string
        safe_db_id = str(raw_db_id) 

        # Forcefully rebuild the dictionary without the _id key (just in case)
        clean_data = {k: v for k, v in parsed_data.items() if k != "_id"}

        # 6. Return Success
        return {
            "status": "success",
            "database_id": safe_db_id,
            "data": clean_data
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}