// ==========================================
// 1. SESSION MANAGEMENT
// ==========================================
function getSessionId() {
    let sessionId = localStorage.getItem("session_id");
    if (!sessionId) {
        sessionId = crypto.randomUUID(); 
        localStorage.setItem("session_id", sessionId);
    }
    return sessionId;
}
const currentSessionId = getSessionId();

// ==========================================
// 2. DOM ELEMENTS & INITIALIZATION
// ==========================================
const API_URL = 'http://127.0.0.1:8000';

// Tabs
const tabDraw = document.getElementById('tabDraw');
const tabUpload = document.getElementById('tabUpload');
const drawSection = document.getElementById('drawSection');
const uploadSection = document.getElementById('uploadSection');

// Canvas
const canvas = document.getElementById('drawingCanvas');
const ctx = canvas.getContext('2d');
const clearBtn = document.getElementById('clearBtn');
let isDrawing = false;

// Editor & Results
const imageInput = document.getElementById('imageInput');
const processBtn = document.getElementById('processBtn');
const resultBox = document.getElementById('resultBox');
const solveBtn = document.getElementById('solveBtn');
const solutionContainer = document.getElementById('solutionContainer');
const solutionDisplay = document.getElementById('solutionDisplay');
const dbId = document.getElementById('dbId');
const historyList = document.getElementById('historyList');

// Initialize MathQuill
const MQ = MathQuill.getInterface(2);
const visualMathField = MQ.MathField(document.getElementById('visualMathEditor'), {
    spaceBehavesLikeTab: true
});

const mathErrorMsg = document.getElementById('mathErrorMsg');
const mathErrorText = document.getElementById('mathErrorText');


// ==========================================
// 3. CANVAS DRAWING LOGIC (Smooth Calligraphy & Accurate Pointer)
// ==========================================
function initCanvas() {
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}
initCanvas();

let lastPos = null;

// The vital math to fix the misaligned pointer
function getPointerPos(e) {
    const rect = canvas.getBoundingClientRect();
    // Handle both mouse and touch seamlessly
    const clientX = e.clientX || (e.touches && e.touches[0].clientX);
    const clientY = e.clientY || (e.touches && e.touches[0].clientY);

    // Map the CSS screen pixels to the internal Canvas pixels perfectly
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
        x: (clientX - rect.left) * scaleX,
        y: (clientY - rect.top) * scaleY
    };
}

canvas.addEventListener('mousedown', startPosition);
canvas.addEventListener('mouseup', endPosition);
canvas.addEventListener('mousemove', draw);
// Touch support for mobile/tablets
canvas.addEventListener('touchstart', (e) => { e.preventDefault(); startPosition(e); });
canvas.addEventListener('touchend', (e) => { e.preventDefault(); endPosition(); });
canvas.addEventListener('touchmove', (e) => { e.preventDefault(); draw(e); });

function startPosition(e) {
    isDrawing = true;
    lastPos = getPointerPos(e);
    
    // Setup Calligraphy Ink Settings
    ctx.lineWidth = 5;          // Thicker, bolder ink
    ctx.lineCap = 'round';      // Rounded ends
    ctx.lineJoin = 'round';     // Smooth corners
    ctx.strokeStyle = '#000000';// Pure black
    
    // Optional: Add a microscopic shadow to mimic ink bleeding into the paper
    ctx.shadowBlur = 1;
    ctx.shadowColor = 'rgba(0,0,0,0.5)';
    
    ctx.beginPath();
    ctx.moveTo(lastPos.x, lastPos.y);
}

function endPosition() {
    isDrawing = false;
    lastPos = null;
}

function draw(e) {
    if (!isDrawing) return;
    
    const currentPos = getPointerPos(e);
    
    // Calculate the midpoint between the last recorded position and current position
    const midPoint = {
        x: lastPos.x + (currentPos.x - lastPos.x) / 2,
        y: lastPos.y + (currentPos.y - lastPos.y) / 2
    };
    
    // Draw a smooth Bezier curve through the midpoint
    ctx.quadraticCurveTo(lastPos.x, lastPos.y, midPoint.x, midPoint.y);
    ctx.stroke();
    
    // Update the last position to the current one
    lastPos = currentPos;
}

clearBtn.addEventListener('click', initCanvas);

// Tab Switching (Keep your existing tab switching logic here!)
tabDraw.addEventListener('click', () => {
    drawSection.classList.remove('hidden');
    uploadSection.classList.add('hidden');
    tabDraw.classList.add('text-blue-600', 'border-b-2', 'border-blue-600');
    tabDraw.classList.remove('text-gray-500');
    tabUpload.classList.add('text-gray-500');
    tabUpload.classList.remove('text-blue-600', 'border-b-2', 'border-blue-600');
});

tabUpload.addEventListener('click', () => {
    uploadSection.classList.remove('hidden');
    drawSection.classList.add('hidden');
    tabUpload.classList.add('text-blue-600', 'border-b-2', 'border-blue-600');
    tabUpload.classList.remove('text-gray-500');
    tabDraw.classList.add('text-gray-500');
    tabDraw.classList.remove('text-blue-600', 'border-b-2', 'border-blue-600');
});


// ==========================================
// 4. API COMMUNICATION (Process & Solve)
// ==========================================
processBtn.addEventListener('click', async () => {
    const formData = new FormData();
    formData.append('session_id', currentSessionId);

    // Determine if we are sending the drawn canvas OR the uploaded file
    if (!drawSection.classList.contains('hidden')) {
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        formData.append('file', blob, 'canvas.png');
    } else {
        const file = imageInput.files[0];
        if (!file) return alert("Please select an image file.");
        formData.append('file', file);
    }

    const originalText = processBtn.innerText;
    processBtn.innerText = "Processing via AI...";
    processBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/upload-equation`, { method: 'POST', body: formData });
        const data = await response.json();

        if (data.status === 'success') {
            resultBox.classList.remove('hidden');
            solutionContainer.classList.add('hidden');
            dbId.innerText = data.database_id;
            
            // Load LaTeX into visual editor
            const latexStr = data.data.latex || data.data.raw_latex || "";
            visualMathField.latex(latexStr);
            loadHistory();
        } else {
            alert("Error: " + data.message);
        }
    } catch (error) {
        alert("Server connection failed.");
    } finally {
        processBtn.innerText = originalText;
        processBtn.disabled = false;
    }
});

solveBtn.addEventListener('click', async () => {
    const currentLatex = visualMathField.latex(); 
    const currentDbId = dbId.innerText;

    // 1. Reset the error message UI every time they click solve
    mathErrorMsg.classList.add('hidden');
    mathErrorText.innerText = "";
    solutionContainer.classList.add('hidden');

    // 2. FORM VALIDATION
    if (!currentLatex || currentLatex.trim() === '') {
        mathErrorText.innerText = "The equation is empty. Please process an image or draw one first.";
        mathErrorMsg.classList.remove('hidden');
        return; 
    }

    if (currentLatex.includes('{}')) {
        mathErrorText.innerText = "Your equation has empty blanks. Please fill in all required values.";
        mathErrorMsg.classList.remove('hidden');
        return; 
    }

    // 3. Process the backend request
    const originalText = solveBtn.innerText;
    solveBtn.innerText = "Solving...";
    solveBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/solve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ database_id: currentDbId, latex: currentLatex })
        });
        const data = await response.json();

        if (data.status === 'success') {
            solutionContainer.classList.remove('hidden');
            katex.render(data.solution_latex, solutionDisplay, { throwOnError: false, displayMode: true });
            loadHistory(); 
        } else {
            // Display backend parsing errors gracefully in the UI instead of an alert
            mathErrorText.innerText = "SymPy could not understand this format. Ensure the math is valid and all the blanks are filled.";
            mathErrorMsg.classList.remove('hidden');
        }
    } catch (error) {
        mathErrorText.innerText = "Server connection failed. Is FastAPI running?";
        mathErrorMsg.classList.remove('hidden');
    } finally {
        solveBtn.innerText = originalText;
        solveBtn.disabled = false;
    }
});


// ==========================================
// 5. LOAD SESSION HISTORY (Using MathQuill StaticMath)
// ==========================================
async function loadHistory() {
    try {
        const response = await fetch(`${API_URL}/history/${currentSessionId}`);
        const data = await response.json();

        if (data.status === 'success') {
            historyList.innerHTML = ''; 
            
            if (data.history.length === 0) {
                historyList.innerHTML = '<li class="text-sm text-gray-500 italic p-4 text-center bg-gray-50 rounded border border-dashed">No equations yet. Draw or upload one!</li>';
                return;
            }

            data.history.forEach(item => {
                const li = document.createElement('li');
                li.className = "p-4 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow";
                
                const eqStr = item.latex || item.raw_latex || "Unknown";
                
                // Build the HTML with specific classes for MathQuill to target
                let htmlContent = `
                    <div class="flex justify-between items-center mb-2 border-b pb-1">
                        <span class="text-xs font-bold text-gray-400 uppercase tracking-wider">ID: ${item._id.slice(-4)}</span>
                    </div>
                    <div class="text-lg overflow-x-auto pb-2 text-gray-800 mq-static-math">${eqStr}</div>
                `;
                
                // If it has a solution, add it in green below
                if (item.solution_latex) {
                    htmlContent += `
                        <div class="mt-2 pt-2 border-t border-gray-100 bg-green-50/50 -mx-4 px-4 pb-2 rounded-b-lg">
                            <span class="text-xs font-bold text-green-600 uppercase tracking-wider block mb-1">Answer:</span>
                            <div class="text-xl overflow-x-auto text-green-800 mq-static-math">${item.solution_latex}</div>
                        </div>
                    `;
                }
                
                li.innerHTML = htmlContent;
                historyList.appendChild(li);
            });

            // Tell MathQuill to loop through those new divs and render them beautifully
            document.querySelectorAll('.mq-static-math').forEach(el => {
                MQ.StaticMath(el);
            });
        }
    } catch (error) {
        console.error("Failed to load history.", error);
        historyList.innerHTML = '<li class="text-sm text-red-500 p-2">Failed to load history from server.</li>';
    }
}

// Call it once when the page loads
loadHistory();