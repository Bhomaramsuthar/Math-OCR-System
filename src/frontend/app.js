// DOM Elements
const imageInput = document.getElementById('imageInput');
const uploadBtn = document.getElementById('uploadBtn');
const resultBox = document.getElementById('resultBox');
const mathDisplay = document.getElementById('mathDisplay');
const rawLatex = document.getElementById('rawLatex');
const dbId = document.getElementById('dbId');

// API Endpoint (Make sure your FastAPI server is running on port 8000!)
const API_URL = 'http://localhost:8000/upload-equation';

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
        // 4. Send the POST request to our backend
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        console.log("Server Response:", data);

        if (data.status === 'success') {
            // 5. Unhide the result box
            resultBox.classList.remove('hidden');

            // 6. Populate the raw data
            dbId.innerText = data.database_id;
            rawLatex.innerText = data.data.latex;

            // 7. Render the Math using KaTeX!
            // We use displayMode: true to make it big and centered
            katex.render(data.data.latex, mathDisplay, {
                throwOnError: false,
                displayMode: true 
            });
        } else {
            alert("Error from server: " + data.message);
        }

    } catch (error) {
        console.error("Fetch error:", error);
        alert("Could not connect to the server. Is FastAPI running?");
    } finally {
        // 8. Reset the button
        uploadBtn.innerText = originalText;
        uploadBtn.disabled = false;
    }
});