"""
Database access layer for the Math OCR application.

All MongoDB reads/writes are encapsulated here so that routes and
business logic never touch the driver directly.
"""

import os
from datetime import datetime, timezone

from bson.objectid import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

# ── Connection ───────────────────────────────────────────────────────

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)

db = client["math_ocr_db"]
equations_collection = db["equation"]


# ── Legacy helpers (used by /upload-equation) ─────────────────────────


def save_equation(parsed_data: dict) -> str | None:
    """
    Insert the structured dict produced by ``EquationParser`` into MongoDB.
    Returns the string representation of the inserted ``_id``, or *None* on
    failure.
    """
    try:
        parsed_data["created_at"] = datetime.now(timezone.utc).isoformat()
        result = equations_collection.insert_one(parsed_data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Database Error: {e}")
        return None


def update_equation_solution(db_id: str, solution_latex: str) -> bool:
    """Update an existing record with its calculated solution."""
    try:
        equations_collection.update_one(
            {"_id": ObjectId(db_id)},
            {"$set": {"solution_latex": solution_latex}},
        )
        return True
    except Exception as e:
        print(f"Database Update Error: {e}")
        return False


# ── History helpers (new dual-latex design) ──────────────────────────


def save_history_entry(data: dict) -> dict | None:
    """
    Persist a history entry that carries **both** ``ocr_latex`` (raw OCR
    output) and ``final_latex`` (user-edited version).

    Parameters
    ----------
    data : dict
        Must contain at least ``session_id``, ``ocr_latex``, and
        ``final_latex``.  Optional keys: ``image_url``, ``solution``.

    Returns
    -------
    dict | None
        The complete document (with ``_id`` as a string) on success,
        *None* on failure.
    """
    try:
        doc = {
            "session_id": data["session_id"],
            "image_url": data.get("image_url"),
            "ocr_latex": data["ocr_latex"],
            "final_latex": data["final_latex"],
            "solution": data.get("solution"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = equations_collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc
    except Exception as e:
        print(f"Database Error (save_history_entry): {e}")
        return None


def get_equations_by_session(session_id: str) -> list[dict]:
    """Fetch **all** equations for a session, newest first (by created_at)."""
    try:
        cursor = (
            equations_collection
            .find({"session_id": session_id})
            .sort("created_at", -1)
        )
        history = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            # Normalise fields so every record has a consistent shape
            # for the frontend, even if older records are missing keys.
            doc.setdefault("ocr_latex", doc.get("latex", ""))
            doc.setdefault("final_latex", doc.get("ocr_latex", ""))
            doc.setdefault("solution", None)
            doc.setdefault("solution_latex", None)
            doc.setdefault("image_url", None)
            doc.setdefault("created_at", None)
            history.append(doc)
        return history
    except Exception as e:
        print(f"Database FetchError: {e}")
        return []


def update_final_latex(db_id: str, final_latex: str) -> bool:
    """
    Update only the ``final_latex`` field of an existing record.
    Useful when the user edits the LaTeX *after* the initial OCR save.
    """
    try:
        equations_collection.update_one(
            {"_id": ObjectId(db_id)},
            {"$set": {"final_latex": final_latex}},
        )
        return True
    except Exception as e:
        print(f"Database Update Error (final_latex): {e}")
        return False

def delete_history_item(db_id: str) -> bool:
    """Deletes a single history item by its ID."""
    try:
        result = equations_collection.delete_one({"_id": ObjectId(db_id)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Database Delete Error: {e}")
        return False

def delete_history_items(db_ids: list[str]) -> bool:
    """Deletes multiple history items by their IDs."""
    try:
        object_ids = [ObjectId(i) for i in db_ids]
        result = equations_collection.delete_many({"_id": {"$in": object_ids}})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Database Delete Many Error: {e}")
        return False
