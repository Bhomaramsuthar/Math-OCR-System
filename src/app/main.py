from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
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
from texify.model.model import load_model
from texify.model.processor import load_processor
from src.ocr.hybrid_ocr import run_math_ocr_from_file
from src.ocr.latex_parser import EquationParser
from src.app.database import save_equation, save_history_entry, get_equations_by_session
from src.app.routes import router as api_router

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
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # PIL preprocess (invert + contrast) → cleaned_images → Texify
        clean_latex = run_math_ocr_from_file(temp_path, model, processor)

        # Parse for extra metadata (sympy_format, type, etc.)
        parsed_data = parser.parse_to_dict(clean_latex)

        # Save with dual-latex design:
        #   ocr_latex  = raw OCR output (clean_latex)
        #   final_latex = same initially; updated when user edits
        history_doc = save_history_entry({
            "session_id": session_id,
            "ocr_latex": clean_latex,
            "final_latex": clean_latex
        })

        db_id = history_doc["_id"] if history_doc else None

        return {
            "status": "success",
            "database_id": str(db_id),
            "data": {
                **{k: v for k, v in parsed_data.items() if k != "_id"},
                "ocr_latex": clean_latex,
                "final_latex": clean_latex,
            },
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