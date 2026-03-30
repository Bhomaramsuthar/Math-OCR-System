from pydantic import BaseModel

class SolveRequest(BaseModel):
    database_id: str
    latex: str