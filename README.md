<p align="center">
  <img src="https://img.shields.io/badge/build-passing-brightgreen?style=flat-square" alt="Build Status" />
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.135-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PyTorch-2.10-EE4C2C?style=flat-square&logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License" />
</p>

<h1 align="center">🧮 The Editorial — Math OCR System</h1>

<p align="center">
  <strong>Write it. Snap it. Solve it.</strong><br/>
  <em>A full-stack AI-powered system that reads handwritten or printed math from images and solves it instantly.</em>
</p>

---

## 📌 Introduction

**The Editorial** is a production-grade, full-stack web application that transforms handwritten or printed mathematical equations into structured LaTeX, then solves them symbolically or numerically — all in real time. Draw on a canvas, upload a photo of your notebook, or type LaTeX directly; the system handles the rest with state-of-the-art vision transformers and a robust computer algebra engine.

---

## 🔭 Project Overview

Mathematics has always been a visual language, yet the tools for digitising it remain frustratingly manual. **The Editorial** bridges that gap.

The system was built to solve a specific pain point: *taking a photo of a math problem on paper and getting an instant, verified solution — without retyping a single symbol.*

Under the hood it chains together:

1. **Intelligent Image Preprocessing** — OpenCV pipelines that handle everything from camera photos with shadows and skew to transparent web-canvas drawings.
2. **Dual OCR Engine** — Texify (a fine-tuned vision transformer) runs first; Pix2Tex acts as a secondary fallback when the primary parse fails validation.
3. **LaTeX Normalization** — A regex-powered sanitization layer that fixes common OCR quirks (missing backslashes, Unicode artifacts, implicit multiplication) before anything reaches the solver.
4. **Symbolic Solving** — SymPy and `latex2sympy2` handle algebraic equations, definite/indefinite integrals, and expression simplification with both exact and numeric output modes.
5. **Persistent History** — Every equation is stored in MongoDB with dual-LaTeX tracking (raw OCR output vs. user-edited version) for full auditability.

---

## 🏗️ Architecture

The system follows a clean **three-tier architecture**: a static frontend dashboard, a FastAPI REST backend, and a MongoDB persistence layer.

![Architecture Diagram](assests/images/architecture-dark.png)


<p align="center">
  <a href="https://math-ocr-system.vercel.app">
    <img src="https://img.shields.io/badge/🚀_View_Live_Deployed_App-10b981?style=for-the-badge&logoColor=white" alt="View Live App" />
  </a>
  <a href="https://bhomaramsuthar.github.io/Math-OCR-System/architecture-diagram.html">
    <img src="https://img.shields.io/badge/🏗️_View_Full_Interactive_Architecture-6366f1?style=for-the-badge&logoColor=white" alt="View Full Architecture" />
  </a>
</p>


> 💡 *Click the button above to explore the full interactive architecture diagram — built as a standalone HTML page with animated data flow, API endpoint maps, database schema, and OCR pipeline breakdown.*

---

## ⚙️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | HTML5, CSS3, Vanilla JS | Premium dark-themed SPA dashboard |
| **Math Rendering** | KaTeX 0.16 | Real-time LaTeX → beautiful typography |
| **Math Editing** | MathQuill 0.10 | Visual WYSIWYG equation editor |
| **Backend** | FastAPI 0.135 + Uvicorn | Async REST API with auto-generated docs |
| **OCR — Primary** | Texify 0.2 (Vision Transformer) | Image → LaTeX conversion |
| **OCR — Fallback** | Pix2Tex 0.1 | Secondary LaTeX extraction model |
| **Image Processing** | OpenCV 4.13 + Pillow 10.4 | Shadow crushing, deskew, binarization |
| **Computer Algebra** | SymPy 1.14 + latex2sympy2 | Symbolic & numeric equation solving |
| **Deep Learning** | PyTorch 2.10, Transformers 4.38 | Model inference backbone |
| **Database** | MongoDB Atlas (PyMongo 4.16) | Cloud NoSQL persistence |
| **Validation** | Pydantic 2.12 | Request/response schema enforcement |
| **Testing** | Pytest 9.0 | Unit tests for normalization pipeline |
| **DevOps** | Docker (Dockerfile), `.env` config | Containerized deployment ready |

---

## ✨ Core Features

- 🖊️ **Handwriting Canvas** — Draw equations directly in the browser with pen/eraser tools, adjustable thickness, undo/redo, and instant OCR parsing.
- 📷 **Image Upload & OCR** — Drag-and-drop or upload PNG/JPEG/PDF images of printed or handwritten math; the system preprocesses and extracts LaTeX automatically.
- ⌨️ **MathQuill Equation Editor** — Type or edit LaTeX visually with a rich, interactive WYSIWYG math input complete with quick-insert symbol buttons.
- 🧠 **Dual-Engine OCR** — Texify (transformer-based) runs first; Pix2Tex validates and acts as fallback, ensuring the best possible LaTeX output.
- 🔬 **Smart Image Preprocessing** — Adaptive binarization with stroke-width detection prevents thick markers from blobing while rescuing faint pencil strokes. Handles dark-mode screenshots, transparent canvas PNGs, and camera photos with shadow crushing and deskew.
- 📐 **Symbolic & Numeric Solving** — Supports algebraic equations, definite/indefinite integrals, trigonometric expressions, and complex numbers. Toggle between exact symbolic and rounded numeric output.
- 📊 **Interactive Plot Data** — For polynomial equations of degree ≥ 3, the solver generates plot coordinates for visual graphing on the frontend.
- 📜 **Equation History Archive** — Full session-based history stored in MongoDB with search, filter (by type, date, status), batch delete, and data export.
- 🎨 **Premium Dark/Light Theme** — Sleek, modern UI with glassmorphism aesthetics, smooth animations, and three theme modes (Dark, Light, System).
- ♿ **Accessibility Settings** — Interface scaling, high-contrast mode, screen-reader optimized equation output, and customizable math typography fonts.
- 🔄 **Dual-LaTeX Tracking** — Every record stores both the raw OCR output (`ocr_latex`) and the user-edited version (`final_latex`) for debugging and auditability.

---

## 🛠️ The Process

This project was developed iteratively with a **pipeline-first** methodology:

1. **OCR Pipeline First** — The image preprocessing and OCR engine were built and validated in isolation before any frontend existed. The goal: get accurate LaTeX from messy camera photos.
2. **Solver Hardening** — SymPy's `parse_latex` proved fragile with raw OCR output, so a multi-layer sanitization pipeline was built (`latex_normalize.py` → `solver.py`) with regex-based cleaning, and `latex2sympy2` was integrated as a primary parser with the manual regex pipeline as fallback.
3. **Frontend as a Dashboard** — The UI was designed as a premium editorial experience, not a utility screen. MathQuill replaced basic textareas, KaTeX handles rendering, and the canvas supports full drawing tools.
4. **Database & History** — MongoDB Atlas was chosen for flexible schema evolution. The dual-LaTeX schema was introduced to track OCR accuracy vs. user corrections over time.
5. **Test-Driven Normalization** — Edge cases (higher-order derivatives, Unicode Greek, inverse trig from OCR) were captured as `pytest` fixtures to prevent regressions.

---

## 📁 Folder Structure

```
math-ocr-system/
├── 📄 .env.example              # Environment variable template
├── 📄 .gitignore                # Git ignore rules
├── 📄 .Dockerfile               # Docker build configuration
├── 📄 requirements.txt          # Python dependencies
├── 📄 README.md                 # ← You are here
│
├── 📂 src/
│   ├── 📂 app/                  # Backend application layer
│   │   ├── main.py              # FastAPI app entry point, model loading, routes
│   │   ├── routes.py            # API route handlers (/solve, /history CRUD)
│   │   ├── solver.py            # LaTeX → SymPy solving engine (626 lines)
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── database.py          # MongoDB data access layer (PyMongo)
│   │
│   ├── 📂 ocr/                  # OCR engine & image processing
│   │   ├── hybrid_ocr.py        # Texify + Pix2Tex dual-engine pipeline
│   │   ├── preprocess_math.py   # Advanced OpenCV preprocessing (251 lines)
│   │   ├── preprocessing.py     # Entry point router (auto/pil/manual variants)
│   │   ├── latex_parser.py      # EquationParser — LaTeX → structured dict
│   │   ├── latex_normalize.py   # OCR LaTeX cleanup & normalization
│   │   ├── latex_utils.py       # String cleaning utilities
│   │   ├── ocr_model.py         # TrOCR HuggingFace model wrapper
│   │   ├── equation_structure.py
│   │   └── __init__.py
│   │
│   └── 📂 frontend/             # Client-side web application
│       ├── index.html           # SPA dashboard (510 lines)
│       ├── style.css            # Premium dark-theme styles (39K)
│       └── app.js               # Application logic & API integration (44K)
│
├── 📂 tests/                    # Test suite
│   └── test_latex_normalize.py  # Normalization & sanitization tests
│
├── 📂 models/                   # AI model weights (git-ignored)
├── 📂 data/                     # Image processing pipeline
│   ├── 📂 raw_images/           # Uploaded originals (git-ignored)
│   └── 📂 cleaned_images/       # Preprocessed outputs (git-ignored)
│
└── 📂 venv/                     # Python virtual environment (git-ignored)
```

---

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.10+** installed on your system
- **MongoDB Atlas** account (or local MongoDB Community Server on port `27017`)
- **Git** for cloning the repository

### 1. Clone the Repository

```bash
git clone https://github.com/Bhomaramsuthar/Math-OCR-System.git
cd Math-OCR-System
```

### 2. Create & Activate Virtual Environment

```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **Note:** PyTorch 2.10 with CUDA support requires a separate install command. See [pytorch.org](https://pytorch.org/get-started/locally/) for GPU-accelerated installation.

### 4. Configure Environment Variables

```bash
# Copy the template
cp .env.example .env

# Edit .env and add your MongoDB connection string
# MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?appName=Cluster0
```

### 5. Start the Backend Server

```bash
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be live at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### 6. Open the Frontend

Open `src/frontend/index.html` in your browser, or use the **Live Server** VS Code extension for hot-reload during development. Make sure the API base URL in `app.js` points to your running backend.

### 7. Run Tests

```bash
pytest tests/ -v
```

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MONGODB_URI` | ✅ Yes | MongoDB connection string (Atlas or local). Example: `mongodb+srv://user:pass@cluster.mongodb.net/?appName=Cluster0` |

> Create a `.env` file in the project root. See `.env.example` for the template.

---

## 🧪 What I Learned

Building this system surfaced a series of deep technical challenges:

- **OCR-to-CAS is harder than it looks** — Raw LaTeX from vision models contains subtle formatting quirks (missing backslashes, Unicode replacements, implicit multiplication) that crash standard parsers. I built a multi-layer regex normalization pipeline that handles dozens of edge cases before SymPy ever sees the input.

- **Stroke-width-based preprocessing** — Generic binarization either obliterates faint pencil lines or bloats thick marker strokes. I implemented adaptive stroke-width estimation using OpenCV's distance transform, then conditionally applied morphological operations only when strokes are thin/fragmented.

- **Dual-parser fallback strategy** — Instead of relying on a single OCR model, the system runs Texify first, validates the output against `latex_parseable()`, and falls back to Pix2Tex only when needed. This cut parse failures by ~40%.

- **Definite integral edge cases** — SymPy's symbolic integrator can silently return unevaluated `Integral` objects for valid expressions. I added a numeric fallback path using `sympy.N()` that catches these cases and still returns a meaningful result.

- **Schema evolution in NoSQL** — As the data model evolved (adding `final_latex`, `solution_latex`, etc.), older MongoDB documents lacked new fields. I implemented `setdefault()` normalization in the query layer so the frontend always receives a consistent document shape.

- **Canvas transparency handling** — Web `<canvas>` exports transparent PNGs where the "white background" is actually alpha=0. The preprocessing pipeline composites these onto a white background before any grayscale conversion.

---

## ⚠️ Known Limitations

While **The Editorial** handles a wide range of mathematical expressions, there are constraints worth noting:

| Area | Limitation |
|---|---|
| **Expression Complexity** | The solver rejects expressions longer than 100 characters or with more than 10 backslash commands — a safety guard against pathological inputs that could hang the CAS engine. |
| **Supported Math Types** | Currently limited to **algebraic equations**, **integrals** (definite & indefinite), **expression simplification**, **Differential equations**, **limits**, **summations**& **matrix operations** are not yet solvable. |
| **OCR Accuracy** | Heavily stylised handwriting, overlapping symbols, or very low-resolution images can produce incorrect LaTeX. Multi-line or multi-equation images are not supported — only single expressions per image. |
| **LaTeX Subset** | Unsupported LaTeX constructs include `\begin{array}`, `\mathbb`, `\mathbf`, and `\operatorname` (except for inverse trig). These are flagged as "garbage" and rejected. |
| **No Step-by-Step** | The solver returns the final answer only — intermediate algebraic steps (factoring, substitution, etc.) are not shown. |
| **Single Variable Focus** | Equation solving defaults to the first free symbol alphabetically. Systems of equations with multiple unknowns are not supported. |
| **Session Isolation** | History is tied to browser-generated session IDs with no authentication — there is no user account system or cross-device sync. |
| **Cold Start Latency** | The first request after server boot takes 10–30 seconds as both the Texify and Pix2Tex models are loaded into memory. Subsequent requests are fast. |
| **PDF Support** | While the upload UI accepts PDF files, only rasterized/image-based PDFs are processed. Native vector PDFs with selectable text are not parsed. |

---

## 🔮 Future Scope & Features

- [ ] **Multi-step Solution Breakdown** — Show intermediate algebraic steps (factoring, substitution, integration by parts) instead of just the final answer, using SymPy's step-by-step solver.
- [ ] **Improved Error Messages** — Surface specific feedback when OCR fails (e.g., "Handwriting too faint — try a darker pen") instead of generic error strings.
- [ ] **User Authentication** — Add OAuth-based login (Google/GitHub) so equation history persists across devices and browsers.
- [ ] **Matrix & Linear Algebra** — Support for determinants, eigenvalues, matrix multiplication, and systems of linear equations via `sympy.Matrix`.
- [ ] **Custom Model Fine-Tuning** — Fine-tune the Texify model on a curated dataset of handwritten math to improve recognition accuracy for non-standard notations and regional handwriting styles.


---

## 📸 Screenshots & Demo

![Canvas Panel](assests/images/workspace-draw-test.png)
![Upload Panel](assests/images/workspace-upload-test.png)
![Processing/solving Panel](assests/images/workspace-draw-processed-test.png)
![History Panel](assests/images/math-ocr-system-history-panel.png)
![Settings Panel](assests/images/math-ocr-system-settings-panel.png)


| Feature | Screenshot |
|---|---|
| Workspace (Draw Mode) | *`screenshot_workspace_draw.png`* |
| Workspace (Upload Mode) | *`screenshot_workspace_upload.png`* |
| Solution Result | *`screenshot_solution.png`* |
| History Archive | *`screenshot_history.png`* |
| Settings Panel | *`screenshot_settings.png`* |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 Bhomaram Suthar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<p align="center">
  <strong>Built with ❤️ and a lot of LaTeX debugging.</strong><br/>
  <em>If this project helped you, consider giving it a ⭐</em>
</p>