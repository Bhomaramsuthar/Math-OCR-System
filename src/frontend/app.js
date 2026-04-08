// ═══════════════════════════════════════════════════════════════════
// THE EDITORIAL — Application Logic
// Math OCR Dashboard — Full SPA with API Integration
// ═══════════════════════════════════════════════════════════════════

(() => {
    'use strict';

    // ════════════════════════════════════════════════════════════════
    // 1. CONFIGURATION & SESSION
    // ════════════════════════════════════════════════════════════════
    const API_URL = 'http://127.0.0.1:8000';

    function getSessionId() {
        let sid = localStorage.getItem('session_id');
        if (!sid) {
            sid = crypto.randomUUID();
            localStorage.setItem('session_id', sid);
        }
        return sid;
    }
    const sessionId = getSessionId();

    // ════════════════════════════════════════════════════════════════
    // 2. SPA NAVIGATION
    // ════════════════════════════════════════════════════════════════
    const pages = {
        workspace: document.getElementById('page-workspace'),
        history: document.getElementById('page-history'),
        settings: document.getElementById('page-settings'),
    };

    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const topnavLinks = document.querySelectorAll('.topnav-link');

    const pageTitles = {
        workspace: 'The Editorial — Workspace',
        history: 'The Editorial — Equation Archive',
        settings: 'The Editorial — Settings',
    };

    function navigateTo(page) {
        // Hide all pages, show target
        Object.values(pages).forEach(p => p.classList.remove('active'));
        if (pages[page]) pages[page].classList.add('active');

        // Update sidebar active
        sidebarLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.page === page);
        });

        // Update topnav active
        topnavLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.page === page);
        });

        // Update document title
        document.title = pageTitles[page] || 'The Editorial';

        // Load history data when navigating to history page
        if (page === 'history') {
            loadHistory();
        }
    }

    // Bind nav clicks
    sidebarLinks.forEach(link => {
        link.addEventListener('click', () => navigateTo(link.dataset.page));
    });
    topnavLinks.forEach(link => {
        link.addEventListener('click', () => navigateTo(link.dataset.page));
    });

    // ════════════════════════════════════════════════════════════════
    // 3. WORKSPACE — MODE TOGGLE (Draw / Upload)
    // ════════════════════════════════════════════════════════════════
    const modeDraw = document.getElementById('modeDraw');
    const modeUpload = document.getElementById('modeUpload');
    const drawSection = document.getElementById('drawSection');
    const uploadSection = document.getElementById('uploadSection');

    let currentMode = 'draw';

    function setMode(mode) {
        currentMode = mode;
        if (mode === 'draw') {
            drawSection.classList.remove('hidden');
            uploadSection.classList.add('hidden');
            modeDraw.classList.add('active');
            modeUpload.classList.remove('active');
        } else {
            drawSection.classList.add('hidden');
            uploadSection.classList.remove('hidden');
            modeDraw.classList.remove('active');
            modeUpload.classList.add('active');
        }
    }

    modeDraw.addEventListener('click', () => setMode('draw'));
    modeUpload.addEventListener('click', () => setMode('upload'));

    // ════════════════════════════════════════════════════════════════
    // 4. CANVAS DRAWING ENGINE
    // ════════════════════════════════════════════════════════════════
    const canvas = document.getElementById('drawingCanvas');
    const ctx = canvas.getContext('2d');

    let isDrawing = false;
    let lastPos = null;
    let isErasing = false;
    let brushSize = 5;

    // Undo/Redo stacks
    let undoStack = [];
    let redoStack = [];
    const MAX_UNDO = 30;

    function initCanvas() {
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
    initCanvas();

    function saveCanvasState() {
        undoStack.push(canvas.toDataURL());
        if (undoStack.length > MAX_UNDO) undoStack.shift();
        redoStack = []; // Clear redo on new action
    }

    // Save initial blank state
    saveCanvasState();

    function getPointerPos(e) {
        const rect = canvas.getBoundingClientRect();
        const clientX = e.clientX ?? (e.touches && e.touches[0]?.clientX);
        const clientY = e.clientY ?? (e.touches && e.touches[0]?.clientY);
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        return {
            x: (clientX - rect.left) * scaleX,
            y: (clientY - rect.top) * scaleY,
        };
    }

    function startDraw(e) {
        isDrawing = true;
        lastPos = getPointerPos(e);

        ctx.lineWidth = brushSize;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        if (isErasing) {
            ctx.globalCompositeOperation = 'destination-out';
            ctx.strokeStyle = 'rgba(0,0,0,1)';
            ctx.shadowBlur = 0;
        } else {
            ctx.globalCompositeOperation = 'source-over';
            ctx.strokeStyle = '#000000';
            ctx.shadowBlur = 1;
            ctx.shadowColor = 'rgba(0,0,0,0.5)';
        }

        ctx.beginPath();
        ctx.moveTo(lastPos.x, lastPos.y);
    }

    function drawing(e) {
        if (!isDrawing) return;
        const currentPos = getPointerPos(e);
        const midPoint = {
            x: lastPos.x + (currentPos.x - lastPos.x) / 2,
            y: lastPos.y + (currentPos.y - lastPos.y) / 2,
        };
        ctx.quadraticCurveTo(lastPos.x, lastPos.y, midPoint.x, midPoint.y);
        ctx.stroke();
        lastPos = currentPos;
    }

    function endDraw() {
        if (isDrawing) {
            isDrawing = false;
            lastPos = null;
            ctx.shadowBlur = 0;
            saveCanvasState();
        }
    }

    // Mouse events
    canvas.addEventListener('mousedown', startDraw);
    canvas.addEventListener('mousemove', drawing);
    canvas.addEventListener('mouseup', endDraw);
    canvas.addEventListener('mouseleave', endDraw);

    // Touch events
    canvas.addEventListener('touchstart', e => { e.preventDefault(); startDraw(e); });
    canvas.addEventListener('touchmove', e => { e.preventDefault(); drawing(e); });
    canvas.addEventListener('touchend', e => { e.preventDefault(); endDraw(); });

    // ── Canvas Toolbar ────────────────────────────────────────────
    const toolPen = document.getElementById('toolPen');
    const toolEraser = document.getElementById('toolEraser');
    const toolUndo = document.getElementById('toolUndo');
    const toolRedo = document.getElementById('toolRedo');
    const toolClear = document.getElementById('toolClear');
    const thicknessSlider = document.getElementById('thicknessSlider');
    const dotSizes = document.querySelectorAll('.dot-size');

    // Pen / Eraser toggle
    toolPen.addEventListener('click', () => {
        isErasing = false;
        toolPen.classList.add('active');
        toolEraser.classList.remove('active');
        canvas.style.cursor = 'crosshair';
    });

    toolEraser.addEventListener('click', () => {
        isErasing = true;
        toolEraser.classList.add('active');
        toolPen.classList.remove('active');
        canvas.style.cursor = 'cell';
    });

    // Dot size presets
    dotSizes.forEach(dot => {
        dot.addEventListener('click', () => {
            brushSize = parseInt(dot.dataset.size, 10);
            thicknessSlider.value = brushSize;
            dotSizes.forEach(d => d.classList.remove('active'));
            dot.classList.add('active');
        });
    });

    // Thickness slider
    thicknessSlider.addEventListener('input', e => {
        brushSize = parseInt(e.target.value, 10);
        // Update dot-size active state
        dotSizes.forEach(d => {
            const sz = parseInt(d.dataset.size, 10);
            d.classList.toggle('active', sz === brushSize);
        });
    });

    // Undo
    toolUndo.addEventListener('click', () => {
        if (undoStack.length > 1) {
            redoStack.push(undoStack.pop());
            const img = new Image();
            img.onload = () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
            };
            img.src = undoStack[undoStack.length - 1];
        }
    });

    // Redo
    toolRedo.addEventListener('click', () => {
        if (redoStack.length > 0) {
            const state = redoStack.pop();
            undoStack.push(state);
            const img = new Image();
            img.onload = () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
            };
            img.src = state;
        }
    });

    // Clear
    toolClear.addEventListener('click', () => {
        initCanvas();
        saveCanvasState();
    });

    // ════════════════════════════════════════════════════════════════
    // 5. WORKSPACE — FILE UPLOAD & DRAG-AND-DROP
    // ════════════════════════════════════════════════════════════════
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const uploadDocBtn = document.getElementById('uploadDocBtn');
    const uploadPreview = document.getElementById('uploadPreview');
    const uploadFileName = document.getElementById('uploadFileName');
    const removeFileBtn = document.getElementById('removeFile');

    let selectedFile = null;

    uploadDocBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            selectFile(e.target.files[0]);
        }
    });

    // Drag-and-drop
    dropzone.addEventListener('dragover', e => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', e => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
    });
    dropzone.addEventListener('drop', e => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files[0]) {
            selectFile(e.dataTransfer.files[0]);
        }
    });

    function selectFile(file) {
        selectedFile = file;
        uploadFileName.textContent = file.name;
        uploadPreview.classList.add('visible');
    }

    removeFileBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        uploadFileName.textContent = 'No file selected';
        uploadPreview.classList.remove('visible');
    });

    // ════════════════════════════════════════════════════════════════
    // 6. WORKSPACE — MATHQUILL EDITOR INITIALIZATION
    // ════════════════════════════════════════════════════════════════
    const MQ = MathQuill.getInterface(2);
    const mathEditorEl = document.getElementById('mathEditor');
    const visualMathField = MQ.MathField(mathEditorEl, {
        spaceBehavesLikeTab: true,
    });

    const parseInputBtn = document.getElementById('parseInputBtn');
    const dbIdSpan = document.getElementById('dbId');
    const mathErrorMsg = document.getElementById('mathErrorMsg');
    const mathErrorText = document.getElementById('mathErrorText');

    parseInputBtn.addEventListener('click', async () => {
        const formData = new FormData();
        formData.append('session_id', sessionId);

        if (currentMode === 'draw') {
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
            formData.append('file', blob, 'canvas.png');
        } else {
            if (!selectedFile) {
                showError('Please select a file to upload.');
                return;
            }
            formData.append('file', selectedFile);
        }

        // Loading state
        const originalText = parseInputBtn.innerHTML;
        parseInputBtn.innerHTML = '<span class="spinner"></span> Processing via AI...';
        parseInputBtn.disabled = true;
        hideError();

        try {
            const response = await fetch(`${API_URL}/upload-equation`, {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();

            if (data.status === 'success') {
                // Populate MathQuill editor with recognized LaTeX
                const latexStr = data.data.final_latex || data.data.ocr_latex || '';
                visualMathField.latex(latexStr);
                dbIdSpan.textContent = data.database_id;

                // Focus the MathQuill editor
                visualMathField.focus();
            } else {
                showError('Error: ' + (data.message || 'Unknown error'));
            }
        } catch (err) {
            showError('Server connection failed. Is the backend running?');
        } finally {
            parseInputBtn.innerHTML = originalText;
            parseInputBtn.disabled = false;
        }
    });

    // ════════════════════════════════════════════════════════════════
    // 7. WORKSPACE — QUICK SYMBOLS (MathQuill API)
    // ════════════════════════════════════════════════════════════════
    const symbolBtns = document.querySelectorAll('.symbol-btn');

    // Map symbols to MathQuill commands
    const mqCommands = {
        '\\pi': 'pi',
        '\\sum': 'sum',
        '\\sqrt{}': 'sqrt',
        '\\infty': 'infty',
        '\\theta': 'theta',
        '\\log': 'log',
        '\\sin': 'sin',
        '\\cos': 'cos',
    };

    symbolBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const latex = btn.dataset.latex;
            const cmd = mqCommands[latex];

            if (cmd) {
                // Use cmd() for LaTeX commands (renders properly in MathQuill)
                visualMathField.cmd('\\' + cmd);
            } else {
                // Fallback: write raw LaTeX
                visualMathField.write(latex);
            }
            visualMathField.focus();
        });
    });

    // ════════════════════════════════════════════════════════════════
    // 8. WORKSPACE — SOLVE EQUATION
    // ════════════════════════════════════════════════════════════════
    const solveBtn = document.getElementById('solveBtn');
    const solutionPanel = document.getElementById('solutionPanel');
    const solutionDisplay = document.getElementById('solutionDisplay');

    solveBtn.addEventListener('click', async () => {
        const latex = visualMathField.latex().trim();
        const currentDbId = dbIdSpan.textContent;

        hideError();
        hideMathError();
        solutionPanel.classList.remove('visible');

        if (!latex) {
            showMathError('The equation is empty. Please enter an equation or parse an input first.');
            return;
        }

        // If no DB ID (manual entry), create one first
        let dbId = currentDbId;
        if (!dbId) {
            try {
                const createRes = await fetch(`${API_URL}/history`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionId,
                        ocr_latex: latex,
                        final_latex: latex,
                    }),
                });
                const createData = await createRes.json();
                if (createData.status === 'success' || createData.id) {
                    dbId = createData.id;
                    dbIdSpan.textContent = dbId;
                }
            } catch (e) {
                // Continue without DB ID if history creation fails
            }
        }

        // Loading state
        const originalHTML = solveBtn.innerHTML;
        solveBtn.innerHTML = '<span class="spinner"></span> Solving...';
        solveBtn.disabled = true;

        try {
            const response = await fetch(`${API_URL}/solve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ database_id: dbId || '', latex }),
            });
            const data = await response.json();

            if (data.status === 'success') {
                solutionPanel.classList.add('visible');
                try {
                    katex.render(data.solution_latex, solutionDisplay, {
                        throwOnError: false,
                        displayMode: true,
                    });
                } catch (renderErr) {
                    solutionDisplay.textContent = data.solution_latex;
                }
            } else {
                showError(data.message || 'SymPy could not understand this format. Ensure the math is valid.');
            }
        } catch (err) {
            showError('Server connection failed. Is FastAPI running?');
        } finally {
            solveBtn.innerHTML = originalHTML;
            solveBtn.disabled = false;
        }
    });

    // ── Error Display ─────────────────────────────────────────────
    const errorMsg = document.getElementById('errorMsg');
    const errorText = document.getElementById('errorText');

    function showError(msg) {
        errorText.textContent = msg;
        errorMsg.classList.add('visible');
    }

    function hideError() {
        errorMsg.classList.remove('visible');
        errorText.textContent = '';
    }

    // MathQuill-specific error (shown below the editor)
    function showMathError(msg) {
        mathErrorText.textContent = msg;
        mathErrorMsg.style.display = 'flex';
    }

    function hideMathError() {
        mathErrorMsg.style.display = 'none';
        mathErrorText.textContent = '';
    }

    // ════════════════════════════════════════════════════════════════
    // 9. HISTORY PAGE — DATA LOADING & RENDERING
    // ════════════════════════════════════════════════════════════════
    const historyGrid = document.getElementById('historyGrid');
    const historyCount = document.getElementById('historyCount');
    const loadMoreBtn = document.getElementById('loadMoreBtn');

    let allHistory = [];
    let displayedCount = 6;
    let batchMode = false;

    async function loadHistory() {
        try {
            const response = await fetch(`${API_URL}/history/${sessionId}`);
            const data = await response.json();

            if (data.status === 'success') {
                allHistory = data.history || [];
                displayedCount = 6;
                renderHistory();
            } else {
                historyGrid.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1; text-align:center; padding: 40px;">Failed to load history.</p>';
            }
        } catch (err) {
            historyGrid.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1; text-align:center; padding: 40px;">Cannot connect to server.</p>';
        }
    }

    function renderHistory() {
        const filtered = applyFilters(allHistory);
        const toShow = filtered.slice(0, displayedCount);

        historyGrid.innerHTML = '';

        if (filtered.length === 0) {
            historyGrid.innerHTML = `
                <div class="add-new-card" id="solveNewCard" style="grid-column: 1/-1; min-height: 160px;">
                    <div class="add-new-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    </div>
                    <span class="add-new-text">SOLVE NEW</span>
                </div>
            `;
            attachSolveNewHandler();
            historyCount.textContent = 'No equations found';
            loadMoreBtn.style.display = 'none';
            return;
        }

        toShow.forEach(item => {
            const card = createHistoryCard(item);
            historyGrid.appendChild(card);
        });

        // Add "Solve New" card
        const addNewCard = document.createElement('div');
        addNewCard.className = 'add-new-card';
        addNewCard.id = 'solveNewCard';
        addNewCard.innerHTML = `
            <div class="add-new-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </div>
            <span class="add-new-text">SOLVE NEW</span>
        `;
        historyGrid.appendChild(addNewCard);
        attachSolveNewHandler();

        // Tell MathQuill to render equations beautifully in history cards
        document.querySelectorAll('.mq-static-math').forEach(el => {
            try { MQ.StaticMath(el); } catch (e) { /* graceful fallback */ }
        });

        // Update count
        historyCount.textContent = `Showing ${toShow.length} of ${filtered.length} equations`;

        // Load more button
        if (toShow.length < filtered.length) {
            loadMoreBtn.style.display = 'inline-flex';
        } else {
            loadMoreBtn.style.display = 'none';
        }
    }

    function createHistoryCard(item) {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.dataset.id = item._id;

        // Determine type
        const hasImage = item.image_url;
        const type = hasImage ? 'IMAGE SCAN' : 'HANDWRITTEN';
        const typeIcon = hasImage ? getCameraIcon() : getPenIcon();

        // Determine status
        const hasSolution = item.solution_latex && item.solution_latex.trim();
        const isFailed = !hasSolution && item.solution !== null && item.solution !== undefined;
        const statusBadge = hasSolution
            ? '<span class="badge badge-solved">SOLVED</span>'
            : (isFailed ? '<span class="badge badge-failed">FAILED</span>' : '');

        // Equation text
        const eqStr = item.final_latex || item.ocr_latex || item.latex || item.raw_latex || '(empty)';
        const resultStr = item.solution_latex || item.solution || '—';

        // Timestamp
        const timeStr = formatTimestamp(item.created_at);

        // Checkbox (for batch delete)
        const checkboxClass = batchMode ? 'history-card-checkbox visible' : 'history-card-checkbox';

        card.innerHTML = `
            <div class="history-card-header">
                <div class="history-type-icon ${isFailed ? 'failed' : ''}">
                    ${typeIcon}
                </div>
                <div class="history-card-meta">
                    <div class="history-type-label">${type}</div>
                    <div class="history-timestamp">${timeStr}</div>
                </div>
                <input type="checkbox" class="${checkboxClass}" data-id="${item._id}">
            </div>
            <div class="history-input-block mq-static-math">${eqStr}</div>
            <div class="history-result-row">
                <div>
                    <div class="history-result-label">RESULT</div>
                    <div class="history-result-value mq-static-math">${resultStr}</div>
                </div>
                ${statusBadge}
            </div>
        `;

        return card;
    }

    function attachSolveNewHandler() {
        const solveNewCard = document.getElementById('solveNewCard');
        if (solveNewCard) {
            solveNewCard.addEventListener('click', () => navigateTo('workspace'));
        }
    }

    // Load more button
    loadMoreBtn.addEventListener('click', () => {
        displayedCount += 6;
        renderHistory();
    });

    // ════════════════════════════════════════════════════════════════
    // 10. HISTORY — SEARCH & FILTERS (CLIENT-SIDE)
    // ════════════════════════════════════════════════════════════════
    const searchInput = document.getElementById('searchInput');
    const filterType = document.getElementById('filterType');
    const filterDate = document.getElementById('filterDate');
    const filterStatus = document.getElementById('filterStatus');

    function applyFilters(history) {
        let items = [...history];
        const searchTerm = searchInput.value.toLowerCase().trim();
        const typeFilter = filterType.value;
        const dateFilter = filterDate.value;
        const statusFilter = filterStatus.value;

        // Search
        if (searchTerm) {
            items = items.filter(item => {
                const eq = (item.final_latex || item.ocr_latex || '').toLowerCase();
                const sol = (item.solution_latex || item.solution || '').toLowerCase();
                return eq.includes(searchTerm) || sol.includes(searchTerm);
            });
        }

        // Type filter
        if (typeFilter !== 'all') {
            items = items.filter(item => {
                if (typeFilter === 'image') return item.image_url;
                if (typeFilter === 'handwritten') return !item.image_url;
                if (typeFilter === 'manual') return false; // Placeholder
                return true;
            });
        }

        // Date filter
        if (dateFilter !== 'all') {
            const days = parseInt(dateFilter, 10);
            const cutoff = new Date();
            cutoff.setDate(cutoff.getDate() - days);
            items = items.filter(item => {
                if (!item.created_at) return true;
                return new Date(item.created_at) >= cutoff;
            });
        }

        // Status filter
        if (statusFilter !== 'all') {
            items = items.filter(item => {
                const hasSolution = item.solution_latex && item.solution_latex.trim();
                if (statusFilter === 'solved') return hasSolution;
                if (statusFilter === 'failed') return !hasSolution;
                return true;
            });
        }

        return items;
    }

    // Re-render on filter/search change
    searchInput.addEventListener('input', () => { displayedCount = 6; renderHistory(); });
    filterType.addEventListener('change', () => { displayedCount = 6; renderHistory(); });
    filterDate.addEventListener('change', () => { displayedCount = 6; renderHistory(); });
    filterStatus.addEventListener('change', () => { displayedCount = 6; renderHistory(); });

    // ════════════════════════════════════════════════════════════════
    // 11. HISTORY — EXPORT
    // ════════════════════════════════════════════════════════════════
    const exportBtn = document.getElementById('exportBtn');

    exportBtn.addEventListener('click', () => {
        if (allHistory.length === 0) {
            alert('No equations to export.');
            return;
        }

        const exportData = allHistory.map(item => ({
            id: item._id,
            input_latex: item.final_latex || item.ocr_latex || '',
            solution: item.solution_latex || item.solution || '',
            created_at: item.created_at || '',
        }));

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `editorial-equations-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
    });

    // ════════════════════════════════════════════════════════════════
    // 12. HISTORY — BATCH DELETE
    // ════════════════════════════════════════════════════════════════
    const batchDeleteBtn = document.getElementById('batchDeleteBtn');

    batchDeleteBtn.addEventListener('click', async () => {
        if (!batchMode) {
            // Enter batch mode
            batchMode = true;
            batchDeleteBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                Confirm Delete
            `;
            renderHistory();
            return;
        }

        // Confirm and delete selected
        const checked = Array.from(document.querySelectorAll('.history-card-checkbox:checked'));
        const ids = checked.map(cb => cb.dataset.id);

        if (ids.length === 0) {
            // Exit batch mode
            batchMode = false;
            batchDeleteBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                Batch Delete
            `;
            renderHistory();
            return;
        }

        if (!confirm(`Delete ${ids.length} selected equation(s)?`)) return;

        try {
            await fetch(`${API_URL}/history`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids }),
            });

            batchMode = false;
            batchDeleteBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                Batch Delete
            `;
            await loadHistory();
        } catch (err) {
            showError('Failed to delete equations.');
        }
    });

    // ════════════════════════════════════════════════════════════════
    // 13. SETTINGS — VISUAL THEME
    // ════════════════════════════════════════════════════════════════
    const themeToggle = document.getElementById('themeToggle');
    const themeBtns = themeToggle.querySelectorAll('.segment-btn');

    function setTheme(theme) {
        localStorage.setItem('editorial-theme', theme);

        document.documentElement.classList.remove('theme-light', 'theme-dark');

        if (theme === 'light') {
            document.documentElement.classList.add('theme-light');
        } else if (theme === 'dark') {
            document.documentElement.classList.add('theme-dark');
        } else {
            // System
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.documentElement.classList.add(prefersDark ? 'theme-dark' : 'theme-light');
        }

        themeBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.theme === theme));
    }

    themeBtns.forEach(btn => {
        btn.addEventListener('click', () => setTheme(btn.dataset.theme));
    });

    // Load saved theme
    const savedTheme = localStorage.getItem('editorial-theme') || 'dark';
    setTheme(savedTheme);

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (localStorage.getItem('editorial-theme') === 'system') setTheme('system');
    });

    // ════════════════════════════════════════════════════════════════
    // 14. SETTINGS — MATH TYPOGRAPHY
    // ════════════════════════════════════════════════════════════════
    const mathFontSelect = document.getElementById('mathFontSelect');
    const fontPreview = document.getElementById('fontPreview');

    const fontFamilies = {
        'default': '"STIX Two Math", "STIX Two Text", serif',
        'latin-modern': '"Latin Modern Math", "Latin Modern Roman", serif',
        'computer-modern': '"Computer Modern", "CMU Serif", serif',
        'serif': 'Georgia, "Times New Roman", serif',
    };

    function setMathFont(font) {
        localStorage.setItem('editorial-math-font', font);
        fontPreview.style.fontFamily = fontFamilies[font] || fontFamilies['default'];

        // Render preview with KaTeX if available
        if (typeof katex !== 'undefined') {
            try {
                katex.render('f(x) = \\int_{a}^{b} \\phi(t)\\, dt', fontPreview, {
                    throwOnError: false,
                    displayMode: false,
                });
            } catch (e) {
                fontPreview.textContent = 'f(x) = ∫ₐᵇ φ(t) dt';
            }
        }
    }

    mathFontSelect.addEventListener('change', () => setMathFont(mathFontSelect.value));

    // Load saved font
    const savedFont = localStorage.getItem('editorial-math-font') || 'default';
    mathFontSelect.value = savedFont;

    // Render preview after KaTeX loads
    function initFontPreview() {
        if (typeof katex !== 'undefined') {
            setMathFont(savedFont);
        } else {
            setTimeout(initFontPreview, 200);
        }
    }
    initFontPreview();

    // ════════════════════════════════════════════════════════════════
    // 15. SETTINGS — ACCESSIBILITY
    // ════════════════════════════════════════════════════════════════

    // Interface Scale
    const scaleSlider = document.getElementById('scaleSlider');

    function setScale(val) {
        const scale = parseInt(val, 10) / 100;
        document.documentElement.style.setProperty('--font-scale', scale);
        localStorage.setItem('editorial-scale', val);
    }

    scaleSlider.addEventListener('input', e => setScale(e.target.value));

    const savedScale = localStorage.getItem('editorial-scale') || '100';
    scaleSlider.value = savedScale;
    setScale(savedScale);

    // High Contrast Mode
    const highContrastToggle = document.getElementById('highContrastToggle');

    function setHighContrast(enabled) {
        document.documentElement.classList.toggle('high-contrast', enabled);
        localStorage.setItem('editorial-high-contrast', enabled);
    }

    highContrastToggle.addEventListener('change', () => setHighContrast(highContrastToggle.checked));

    const savedContrast = localStorage.getItem('editorial-high-contrast') === 'true';
    highContrastToggle.checked = savedContrast;
    setHighContrast(savedContrast);

    // Screen Reader Support
    const screenReaderToggle = document.getElementById('screenReaderToggle');

    function setScreenReader(enabled) {
        localStorage.setItem('editorial-screen-reader', enabled);

        if (enabled) {
            // Add aria-labels to key interactive elements
            document.querySelectorAll('.btn-primary').forEach(btn => {
                if (!btn.getAttribute('aria-label')) {
                    btn.setAttribute('aria-label', btn.textContent.trim());
                }
            });
            document.querySelectorAll('.symbol-btn').forEach(btn => {
                btn.setAttribute('aria-label', `Insert ${btn.title || btn.textContent}`);
            });
        }
    }

    screenReaderToggle.addEventListener('change', () => setScreenReader(screenReaderToggle.checked));

    const savedScreenReader = localStorage.getItem('editorial-screen-reader');
    if (savedScreenReader !== null) {
        screenReaderToggle.checked = savedScreenReader === 'true';
    }
    setScreenReader(screenReaderToggle.checked);

    // ════════════════════════════════════════════════════════════════
    // 16. UTILITY FUNCTIONS
    // ════════════════════════════════════════════════════════════════

    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatTimestamp(isoStr) {
        if (!isoStr) return '';
        const date = new Date(isoStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;

        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
        });
    }

    function getPenIcon() {
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
        </svg>`;
    }

    function getCameraIcon() {
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
        </svg>`;
    }

    // ════════════════════════════════════════════════════════════════
    // 17. INITIAL LOAD
    // ════════════════════════════════════════════════════════════════

    // Load history on initial page load (in background)
    loadHistory();

})();