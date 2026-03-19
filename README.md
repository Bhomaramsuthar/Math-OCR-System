# Full-Stack Math OCR System

An end-to-end machine learning web application that extracts mathematical equations from images, parses them into structured data, stores them in a NoSQL database, and renders them beautifully on a web interface.

## System Architecture

* **Frontend:** Vanilla JS, HTML, CSS, KaTeX (for mathematical rendering).
* **Backend API:** FastAPI (Python) for handling asynchronous image uploads.
* **Computer Vision:** OpenCV for image normalization, scaling, and noise reduction.
* **OCR Engine:** Pix2Tex (LaTeX extraction).
* **Data Parsing:** SymPy (for converting raw LaTeX into structured equation formats).
* **Database:** MongoDB (for persistent storage of equation histories).

## How to Run Locally

1. **Clone and Setup Environment:**
   ```bash
   git clone <your-repo-link>
   cd math-ocr-system
   python -m venv venv
   source venv/Scripts/activate  # On Windows
   pip install -r requirements.txt

2. **Start the Database:** Ensure MongoDB Community Server is running locally on port 27017.

3. **Run the Backend Server:**
    ```bash
    uvicorn ocr_engine.main:app --reload

4. **Open the Frontend:** Open frontend/index.html in your web browser or use a Live Server extension.