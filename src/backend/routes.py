from fastapi import APIRouter
import sympy
from src.backend.schemas import SolveRequest
from src.backend.database import update_equation_solution
from src.ocr_engine.latex_parser import EquationParser

router= APIRouter()
parser = EquationParser()
@router.post("/solve")
async def solve_equation(request: SolveRequest):
    try:
        print(f"\n--- SOLVING EQUATION ---")
        print(f"Target DB ID: {request.database_id}")

        parsed_data = parser.parse_to_dict(request.latex)
        sympy_str = parsed_data.get("sympy_format")

        if not sympy_str:
            raise ValueError("Parser could not genrae a SymPy format from this Latex")
        
        math_obj = sympy.sympify(sympy_str)

        solution_obj = math_obj.doit()

        solution_latex = sympy.latex(solution_obj)
        print(f"Calculated Solution: {solution_latex}")

        update_equation_solution(request.database_id,solution_latex)

        return{
            "status":"success",
            "original_latex" : request.latex,
            "solution_latex" : solution_latex
        }

    except Exception as e:
        print(f"SOLVE ERROR: {str(e)}")
        return {"status":"error","message":str(e)} 