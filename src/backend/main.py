from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

#Initialize the fastapi app
app = FastAPI(title="Maath OCR API",version="1.0")

#Setup CORS (Crucial for allowing our frontend HTML to talk to this API )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production , you'd restrict this to your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A simple route to test if the server is awake 
@app.get("/")
def read_root():
    return {"status":"online","message":"Math OCR API is running!"}