from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from PIL import Image

# 1. THE HUGGING FACE SURGICAL BYPASS
from transformers import AutoImageProcessor

_original_register = AutoImageProcessor.register

@classmethod
def safe_register(cls, config_class, **kwargs):
    if 'slow_image_processor_class' in kwargs:
        kwargs['image_processor_class'] = kwargs.pop('slow_image_processor_class')
    return _original_register(config_class, **kwargs)

AutoImageProcessor.register = safe_register

# 2. THE MODERN MATH MODEL IMPORTS
from texify.inference import batch_inference
from texify.model.model import load_model
from texify.model.processor import load_processor

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

print("Booting up server and loading SOTA AI model...")

# 3. LOAD THE TEXIFY MODEL
model = load_model()
processor = load_processor()

parser = EquationParser()
print("SOTA Vision Model loaded successfully!")

@app.get("/")
def read_root():
    return {"status": "online", "message": "Math OCR API is running!"}

@app.post("/upload-equation")
async def process_equation(file: UploadFile = File(...)):
    try:
        # 1. Save uploaded file temporarily
        temp_path = f"data/raw_images/{file.filename}"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Run the gentle PIL preprocessor
        cleaned_image_path = preprocess_image(temp_path) 
        
        # 3. THE PREDICTION
        img = Image.open(cleaned_image_path).convert('RGB')
        results = batch_inference([img], model, processor)
        
        # Grab the raw LaTeX from the array
        raw_latex = results[0]
        print(f"\nRaw AI Prediction: {raw_latex}")

        # 3.5 THE STRING STRIPPER
        # Remove whitespace and newlines
        clean_latex = raw_latex.strip()
        
        # First, remove stray trailing periods if the VLM treated it like a sentence
        if clean_latex.endswith('.'):
            clean_latex = clean_latex[:-1].strip()

        # Next, remove $$ or $ wrappers that crash SymPy
        if clean_latex.startswith('$$') and clean_latex.endswith('$$'):
            clean_latex = clean_latex[2:-2].strip()
        elif clean_latex.startswith('$') and clean_latex.endswith('$'):
            clean_latex = clean_latex[1:-1].strip()
            
        print(f"Cleaned LaTeX for Parser: {clean_latex}\n")
        
        # 4. Parse and Save
        parsed_data = parser.parse_to_dict(clean_latex)
        db_data = parsed_data.copy()
        raw_db_id = save_equation(db_data)

        # 5. Return Clean JSON
        return {
            "status": "success",
            "database_id": str(raw_db_id),
            "data": {k: v for k, v in parsed_data.items() if k != "_id"}
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}