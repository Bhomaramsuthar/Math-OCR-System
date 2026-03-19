from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os

# Import our custom ML and Database pipeline
from src.ocr_engine.preprocessing import preprocess_image
from src.ocr_engine.ocr_model import MathOCR
from src.ocr_engine.latex_parser import EquationParser
from src.backend.database import save_equation

app = FastAPI(title="Math OCR API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Booting up server and loading AI models into memory...")
ocr_system = MathOCR()
parser = EquationParser()
print("Models loaded successfully!")

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
        cleaned_image = preprocess_image(temp_path)
        latex_str = ocr_system.predict(cleaned_image)
        parsed_data = parser.parse_to_dict(latex_str)

        # 3. Save to DB using a strict copy
        db_data = parsed_data.copy()
        raw_db_id = save_equation(db_data)

        # 4. THE NUCLEAR FIX: 
        # Force the database ID into a standard Python string
        safe_db_id = str(raw_db_id) 

        # Forcefully rebuild the dictionary without the _id key (just in case)
        clean_data = {k: v for k, v in parsed_data.items() if k != "_id"}

        # 5. Return Success
        return {
            "status": "success",
            "database_id": safe_db_id,
            "data": clean_data
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}