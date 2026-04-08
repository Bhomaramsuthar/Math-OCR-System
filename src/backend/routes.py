"""
API route handlers (mounted on the main FastAPI app via ``include_router``).
"""

from fastapi import APIRouter, HTTPException

from src.backend.schemas import (
    HistoryCreateRequest,
    HistoryCreateResponse,
    SolveRequest,
    DeleteHistoryRequest,
)
from src.backend.database import (
    save_history_entry,
    update_equation_solution,
    update_final_latex,
)
from src.backend.solver import solve_latex

router = APIRouter()


# ------------------------------------------------------------------
# POST /solve  — Solve an equation by its DB id + LaTeX
# ------------------------------------------------------------------


@router.post("/solve")
async def solve_equation(request: SolveRequest):
    try:
        print(f"\n--- SOLVING EQUATION ---")
        print(f"Target DB ID: {request.database_id}")

        # 1. Run the solver
        result = solve_latex(request.latex)

        # 2. CHECK IF THE SOLVER ACTUALLY FAILED
        if result["status"] == "error":
            print(f"SOLVER FAILED: {result['solution_latex']}")
            # Send the error status back to the frontend so it triggers the red UI warning
            return {"status": "error", "message": result["solution_latex"]}

        # 3. If success, save and return
        solution_latex = result["solution_latex"]
        update_equation_solution(request.database_id, solution_latex)
        update_final_latex(request.database_id, request.latex)

        return {
            "status": "success",
            "original_latex": request.latex,
            "solution_latex": solution_latex,
        }

    except Exception as e:
        print(f"SOLVE ERROR: {str(e)}")
        return {"status": "error", "message": str(e)}

        
# ------------------------------------------------------------------
# POST /history  — Save a new history entry (dual-latex)
# ------------------------------------------------------------------


@router.post("/history", response_model=HistoryCreateResponse)
async def create_history_entry(payload: HistoryCreateRequest):
    """
    Accept both ``ocr_latex`` and ``final_latex`` from the client.

    *  ``final_latex`` is the "source of truth" — the LaTeX the user
       actually intended.
    *  ``ocr_latex`` is kept for reference / debugging.
    *  If ``final_latex`` is omitted the Pydantic model automatically
       falls back to ``ocr_latex``.

    **Example request body**::

        {
            "session_id": "abc-123",
            "ocr_latex": "\\\\frac{1}{2}+x",
            "final_latex": "\\\\frac{1}{2}+y",
            "image_url": null,
            "solution": null
        }
    """
    doc = save_history_entry(payload.model_dump())

    if doc is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to save history entry to database.",
        )

    return HistoryCreateResponse(
        id=doc["_id"],
        session_id=doc["session_id"],
        ocr_latex=doc["ocr_latex"],
        final_latex=doc["final_latex"],
        solution=doc.get("solution"),
        created_at=doc["created_at"],
    )

# ------------------------------------------------------------------
# DELETE /history  — Delete history items (Issue #4)
# ------------------------------------------------------------------

@router.delete("/history/{item_id}")
async def delete_history_item(item_id: str):
    from src.backend.database import delete_history_item as db_delete_item
    success = db_delete_item(item_id)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to delete"}

@router.delete("/history")
async def delete_history_items(payload: DeleteHistoryRequest):
    from src.backend.database import delete_history_items as db_delete_items
    success = db_delete_items(payload.ids)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to delete"}