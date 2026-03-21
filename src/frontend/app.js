// DOM Elements
const imageInput = document.getElementById('imageInput');
const uploadBtn = document.getElementById('uploadBtn');
const resultBox = document.getElementById('resultBox');
const mathDisplay = document.getElementById('mathDisplay');
const rawLatex = document.getElementById('rawLatex');
const dbId = document.getElementById('dbId');

// API Endpoint (Make sure your FastAPI server is running on port 8000!)
const API_URL = 'http://127.00.1:8000/upload-equation';

uploadBtn.addEventListener('click', async () => {
    // 1. Check if a file was selected
    const file = imageInput.files[0];
    if (!file) {
        alert("Please select an image file first.");
        return;
    }

    // 2. Change button state to show loading
    const originalText = uploadBtn.innerText;
    uploadBtn.innerText = "Processing Image...";
    uploadBtn.disabled = true;

    // 3. Prepare the data for FastAPI
    const formData = new FormData();
    formData.append('file', file);

   try {
        console.log("1. Sending request...");
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });

        console.log("2. Request finished. Status:", response.status);
        const data = await response.json();
        console.log("3. Raw Data from Server:", data);

        if (data.status === 'success') {
            console.log("4. Status is success. Unhiding box...");
            resultBox.classList.remove('hidden');

            console.log("5. Updating text fields...");
            dbId.innerText = data.database_id;
            
            // Safety check: Does data.data.latex actually exist?
            const latexString = data.data.latex || data.data.raw_latex || "NO LATEX FOUND";
            rawLatex.innerText = latexString;

            console.log("6. Rendering KaTeX...");
            try {
                katex.render(latexString, mathDisplay, {
                    throwOnError: false,
                    displayMode: true 
                });
                console.log("7. KaTeX rendered successfully!");
            } catch (katexErr) {
                console.error("KATEX CRASHED:", katexErr);
            }
            
        } else {
            console.error("Server returned an error status:", data);
            alert("Error from server: " + data.message);
        }

    } catch (error) {
        console.error("CRITICAL FETCH ERROR:", error);
        alert("Fetch failed. Check the F12 console.");
    } finally {
        uploadBtn.innerText = originalText;
        uploadBtn.disabled = false;
        console.log("8. Button reset.");
    }
});