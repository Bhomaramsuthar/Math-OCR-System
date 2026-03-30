import os
from pymongo import MongoClient
from datetime import datetime, timezone
from dotenv import load_dotenv
from bson.objectid import ObjectId


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
    
def get_equations_by_session(session_id:str):
    """Fetches all equations belonging to a specific session, newest first."""
    try:
        # Assuming your MongoDB equations_collection variable is named `collection`
        # We sort by _id -1 to get the most recently added items first
        cursor = equations_collection.find({"session_id": session_id}).sort("_id", -1)
        history = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            history.append(doc)

        return history
    except Exception as e:
        print(f"Database FetchError: {e}")
        return []            

from bson.objectid import ObjectId # Ensure this is imported at the top

# Add this to the bottom of the file
def update_equation_solution(db_id: str, solution_latex: str):
    """Updates an existing database record with its calculated solution."""
    try:
        equations_collection.update_one(
            {"_id": ObjectId(db_id)},
            {"$set": {"solution_latex": solution_latex}}
        )
        return True
    except Exception as e:
        print(f"Database Update Error: {e}")
        return False
