"""
API route handlers (mounted on the main FastAPI app via ``include_router``).
"""

import logging

from fastapi import APIRouter, HTTPException

from src.app.schemas import (
    HistoryCreateRequest,
    HistoryCreateResponse,
    SolveRequest,
    DeleteHistoryRequest,
)
from src.app.database import (
    save_history_entry,
    update_equation_solution,
    update_final_latex,
)
from src.app.solver import safe_solve

router = APIRouter()
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# POST /solve  — Solve an equation by its DB id + LaTeX
# ------------------------------------------------------------------


@router.post("/solve")
async def solve_equation(request: SolveRequest):
    try:
        logger.info("Solving request for DB id: %s", request.database_id)
        result = safe_solve(
            request.latex,
            exact=request.exact,
            decimals=request.decimals,
        )

        if result["status"] == "error":
            logger.warning("Solver rejected input: %s", result["message"])
            return {
                "status": "error",
                "original_latex": request.latex,
                "solution_latex": None,
                "message": result["message"],
                "cleaned_latex": result.get("cleaned_latex", ""),
                "display_text": result.get("display_text"),
                "plot_data": result.get("plot_data"),
                "mode": result.get("mode", "numeric"),
            }

        solution_latex = result["result"]
        update_equation_solution(request.database_id, solution_latex)
        update_final_latex(request.database_id, request.latex)

        return {
            "status": "success",
            "original_latex": request.latex,
            "solution_latex": solution_latex,
            "message": result["message"],
            "cleaned_latex": result.get("cleaned_latex", ""),
            "expression_type": result.get("expression_type"),
            "display_text": result.get("display_text"),
            "plot_data": result.get("plot_data"),
            "mode": result.get("mode", "numeric"),
        }

    except Exception as e:
        logger.exception("Unhandled solve route error: %s", e)
        return {
            "status": "error",
            "original_latex": request.latex,
            "solution_latex": None,
            "message": "Internal solver error",
        }

        
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
    from src.app.database import delete_history_item as db_delete_item
    success = db_delete_item(item_id)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to delete"}

@router.delete("/history")
async def delete_history_items(payload: DeleteHistoryRequest):
    from src.app.database import delete_history_items as db_delete_items
    success = db_delete_items(payload.ids)
    if success:
        return {"status": "success"}
    return {"status": "error", "message": "Failed to delete"}
