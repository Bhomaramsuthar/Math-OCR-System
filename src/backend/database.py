import os
from pymongo import MongoClient
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load the environment variable from the .env file
load_dotenv()

#Safely fetch the URI . if not found it default sto the localhost 
MONGO_URI = os.getenv("MONGODB_URI","mongodb://localhost:27017/")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)

db = client["math_ocr_db"]
equations_collection = db["equation"]

def save_equation(parsed_data):
    """
    takes the structured dictionary from ouur parser , adds a timestamp, and saves it to MongoDB.
    """
    try:
        parsed_data["created_at"] = datetime.now(timezone.utc).isoformat()

        result = equations_collection.insert_one(parsed_data)

        return str(result.inserted_id)
    
    except Exception as e:
        print(f"Database Error: {e}")
        return None