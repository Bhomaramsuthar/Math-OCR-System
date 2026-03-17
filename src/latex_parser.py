from sympy.parsing.latex import parse_latex

class EquationParser:
    def parse_to_dict(self, latex_str):
        """
        Converts a LaTeX string into a structured dictionary (ready for JSON/MongoDB).
        """
        try:
            # 1. Parse LaTeX into a SymPy expression object
            expr = parse_latex(latex_str)
            
            # 2. Build the basic structured representation
            structured_data = {
                "latex": latex_str,
                "sympy_format": str(expr),
                "type": "equation" if "=" in latex_str else "expression"
            }
            
            return structured_data
            
        except Exception as e:
            print(f"SymPy Parsing Error: {e}")
            return {
                "latex": latex_str,
                "error": str(e)
            }