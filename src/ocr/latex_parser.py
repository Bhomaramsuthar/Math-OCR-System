from latex2sympy2 import latex2sympy

# Re-use the same sanitisation pipeline that the solver uses,
# so any raw OCR string is cleaned before SymPy ever sees it.
from src.app.solver import sanitize_latex


class EquationParser:
    def parse_to_dict(self, latex_str):
        """
        Converts a LaTeX string into a structured dictionary (ready for JSON/MongoDB).

        The raw input is first run through ``sanitize_latex`` to fix common
        OCR-generated formatting quirks that would otherwise crash parsing.
        """
        try:
            cleaned = sanitize_latex(latex_str)

            # 1. Parse LaTeX into a SymPy expression object
            expr = latex2sympy(cleaned)

            # 2. Build the basic structured representation
            structured_data = {
                "latex": latex_str,           # keep the original for reference
                "cleaned_latex": cleaned,     # what was actually parsed
                "sympy_format": str(expr),
                "type": "equation" if "=" in latex_str else "expression",
            }

            return structured_data

        except Exception as e:
            print(f"SymPy Parsing Error: {e}")
            return {
                "latex": latex_str,
                "error": str(e),
            }