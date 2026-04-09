"""
Pydantic schemas for the Math OCR API.

All request/response models live here to keep routes thin and type-safe.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ------------------------------------------------------------------
# Solve endpoint
# ------------------------------------------------------------------


class SolveRequest(BaseModel):
    """Body for POST /solve."""

    database_id: str
    latex: str
    exact: bool = False
    decimals: int = 3

class DeleteHistoryRequest(BaseModel):
    """Body for DELETE /history."""
    ids: list[str]


# ------------------------------------------------------------------
# History endpoint
# ------------------------------------------------------------------


class HistoryCreateRequest(BaseModel):
    """
    Body for POST /history.

    • ``ocr_latex``  – raw LaTeX produced by the OCR engine (required).
    • ``final_latex`` – user-edited LaTeX sent to the solver.
      Falls back to ``ocr_latex`` when not supplied (backward compat).
    """

    session_id: str
    image_url: Optional[str] = None
    ocr_latex: str
    final_latex: Optional[str] = None
    solution: Optional[str] = None

    @model_validator(mode="after")
    def _default_final_latex(self) -> "HistoryCreateRequest":
        """If the client omits *final_latex*, fall back to *ocr_latex*."""
        if self.final_latex is None:
            self.final_latex = self.ocr_latex
        return self


class HistoryCreateResponse(BaseModel):
    """Returned after a successful POST /history."""

    status: str = "success"
    id: str
    session_id: str
    ocr_latex: str
    final_latex: str
    solution: Optional[str] = None
    created_at: str


class HistoryItemResponse(BaseModel):
    """Single item inside the GET /history/{session_id} list."""

    id: str
    session_id: str
    image_url: Optional[str] = None
    ocr_latex: str
    final_latex: str
    solution: Optional[str] = None
    solution_latex: Optional[str] = None
    created_at: Optional[str] = None
