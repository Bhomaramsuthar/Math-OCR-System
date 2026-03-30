from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from PIL import Image

# Hugging Face Bypass
from transformers import AutoImageProcessor
_original_register = AutoImageProcessor.register
@classmethod
def safe_register(cls, config_class, **kwargs):
    if 'slow_image_processor_class' in kwargs:
        kwargs['image_processor_class'] = kwargs.pop('slow_image_processor_class')
    return _original_register(config_class, **kwargs)
AutoImageProcessor.register = safe_register

# Models & Custom Modules
from texify.inference import batch_inference
from texify.model.model import load_model
from texify.model.processor import load_processor
from src.ocr_engine.preprocessing import preprocess_image
from src.ocr_engine.latex_parser import EquationParser
from src.backend.database import save_equation, get_equations_by_session
from src.backend.routes import router as api_router

app = FastAPI(title="Math OCR App", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading SOTA AI model...")
model = load_model()
processor = load_processor()
parser = EquationParser()
print("SOTA Vision Model loaded successfully!")

# Attach the external routes (like /solve)
app.include_router(api_router)

@app.post("/upload-equation")
async def process_equation(
    file: UploadFile = File(...),
    session_id: str = Form(...) 
):
    try:
        temp_path = f"data/raw_images/{file.filename}"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Preprocess & Predict
        cleaned_image_path = preprocess_image(temp_path) 
        img = Image.open(cleaned_image_path).convert('RGB')
        results = batch_inference([img], model, processor)
        
        raw_latex = results[0]

        # Strip strings
        clean_latex = raw_latex.strip()
        if clean_latex.endswith('.'):
            clean_latex = clean_latex[:-1].strip()
        if clean_latex.startswith('$$') and clean_latex.endswith('$$'):
            clean_latex = clean_latex[2:-2].strip()
        elif clean_latex.startswith('$') and clean_latex.endswith('$'):
            clean_latex = clean_latex[1:-1].strip()
            
        # Parse & Save
        parsed_data = parser.parse_to_dict(clean_latex)
        db_data = parsed_data.copy()
        db_data["session_id"] = session_id 
        
        raw_db_id = save_equation(db_data)

        return {
            "status": "success",
            "database_id": str(raw_db_id),
            "data": {k: v for k, v in parsed_data.items() if k != "_id"}
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/history/{session_id}")
async def fetch_history(session_id: str):
    try:
        user_history = get_equations_by_session(session_id)
        return {"status": "success", "history": user_history}
    except Exception as e:
        return {"status": "error", "message": str(e)}