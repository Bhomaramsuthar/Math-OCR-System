"""
solve_latex(latex_str) -> dict

LaTeX -> SymPy solving pipeline using ``sympy.parsing.latex.parse_latex``.

``sanitize_latex`` normalises OCR output (via ``normalize_ocr_latex``) and
applies structural fixes so SymPy's parser is less likely to mis-read
derivatives, limits, and integrals.
"""

import re
import sympy
from sympy.parsing.latex import parse_latex

from src.ocr_engine.latex_normalize import normalize_ocr_latex


# =====================================================================
#  LaTeX Sanitization Pipeline
# =====================================================================

def sanitize_latex(raw: str) -> str:
    """
    Clean OCR-generated LaTeX so SymPy's ``parse_latex`` can handle it.

    Fixes applied (in order):
        0. ``normalize_ocr_latex`` — trig names, higher derivatives, limits,
           implicit ``*``, Greek letters, etc.
        1. Strip leading/trailing whitespace.
        2. Remove ``\\left`` / ``\\right`` sizing commands (turns
           ``\\left|...\\right|`` into ``|...|``, which SymPy parses as ``Abs``).
        3. Remove empty subscripts ``_{}`` and superscripts ``^{}``.
        4. Remove stray spaces between ``\\int`` and ``_`` or ``^``.
        5. Ensure a space exists between ``}`` and ``\\frac`` so SymPy
           doesn't merge the closing brace with the next command.
        6. Ensure differentials like ``dx``, ``dy``, ``dt`` are preceded
           by a thin-space ``\\,`` so SymPy recognises them.
        7. Collapse runs of whitespace into single spaces.

    Parameters
    ----------
    raw : str
        Raw LaTeX string (e.g. straight from Texify / MathQuill).

    Returns
    -------
    str
        Sanitised LaTeX ready for ``parse_latex``.
    """
    s = normalize_ocr_latex(raw)
    if not s:
        return s

    # 1.  Remove \left and \right sizing tags
    s = s.replace(r'\left', '').replace(r'\right', '')

    # 2.  Remove empty subscripts / superscripts  _{} or ^{}
    #     (may contain only whitespace inside the braces)
    s = re.sub(r'_\{\s*\}', '', s)
    s = re.sub(r'\^\{\s*\}', '', s)

    # 3.  Remove spaces between \int and its limits (_ or ^)
    #     e.g.  "\int _8"  ->  "\int_8"
    #           "\int   ^{13}"  ->  "\int^{13}"
    s = re.sub(r'\\int\s+(_)', r'\\int\1', s)
    s = re.sub(r'\\int\s+(\^)', r'\\int\1', s)

    # 4.  Ensure a space between a closing brace and \frac
    #     e.g.  "}\frac"  ->  "} \frac"
    s = re.sub(r'\}\\frac', r'} \\frac', s)

    # 5.  Ensure differentials have a thin-space before them
    #     Matches d followed by a single variable letter (x, y, z, t, u, v, w, r, s)
    #     but NOT when preceded by a backslash (to avoid clobbering \delta, etc.)
    #     and NOT when the 'd' is part of a longer word.
    s = re.sub(r'(?<!\\)(?<![a-zA-Z])d([xyztuvrws])(?![a-zA-Z])', r' \\,d\1', s)

    # 6.  Collapse multiple spaces into one
    s = re.sub(r' {2,}', ' ', s)

    return s.strip()


def latex_parseable(latex_str: str) -> bool:
    """Return True if ``sanitize_latex`` + ``parse_latex`` succeeds (equation or expression)."""
    s = sanitize_latex(latex_str)
    if not s:
        return False
    try:
        if "=" in s:
            lhs, rhs = s.split("=", 1)
            parse_latex(lhs.strip())
            parse_latex(rhs.strip())
        else:
            parse_latex(s)
        return True
    except Exception:
        return False


# =====================================================================
#  Public API
# =====================================================================

def solve_latex(latex_str: str) -> dict:
    """
    Accepts raw LaTeX, returns::

        {"status": "success", "solution_latex": "..."}
        {"status": "error",   "solution_latex": "\\text{...}"}
    """
    latex_input = sanitize_latex(latex_str)
    if not latex_input:
        return _fail("Empty input")

    print(f"\n[SOLVER] Cleaned Input for SymPy: {latex_input}")

    # -- 1. Equation  (contains '=') --
    if "=" in latex_input:
        return _solve_equation(latex_input)

    # -- 2. Expression (no '=') --
    return _solve_expression(latex_input)


# =====================================================================
#  EQUATIONS   (LHS = RHS  ->  sympy.solve)
# =====================================================================

def _solve_equation(latex_input: str) -> dict:
    parts = latex_input.split("=", 1)
    try:
        lhs = parse_latex(parts[0].strip())
        rhs = parse_latex(parts[1].strip())
    except Exception as e:
        print(f"[SOLVER] Equation parse error: {e}")
        return _fail("Invalid or unsupported equation")

    expr = lhs - rhs
    var = _pick_variable(expr)

    try:
        solutions = sympy.solve(expr, var)
        print(f"[SOLVER] solve() -> {solutions}")
    except Exception as e:
        print(f"[SOLVER] solve() crashed: {e}")
        return _fail("Could not solve this equation")

    if not solutions:
        return _fail("No solution found")

    # Format output
    if isinstance(solutions, list):
        parts_fmt = [sympy.latex(s) for s in solutions]
        solution_latex = f"{sympy.latex(var)} = " + ",\\;".join(parts_fmt)
    elif isinstance(solutions, dict):
        parts_fmt = [f"{sympy.latex(k)} = {sympy.latex(v)}"
                     for k, v in solutions.items()]
        solution_latex = ",\\;".join(parts_fmt)
    else:
        solution_latex = sympy.latex(solutions)

    return _ok(solution_latex)


# =====================================================================
#  EXPRESSIONS  (integrals, derivatives, simplify, trig)
# =====================================================================

def _solve_expression(latex_input: str) -> dict:
    try:
        expr = parse_latex(latex_input)
    except Exception as e:
        print(f"[SOLVER] parse_latex error: {e}")
        return _fail("Invalid or unsupported equation")

    print(f"[SOLVER] Parsed: {expr}  (type={type(expr).__name__})")

    var = _pick_variable(expr)
    result = None

    # Strategy 1 -- .doit()  (evaluates Integral, Derivative, Sum, etc.)
    result = _try(lambda: expr.doit(), expr, "doit")

    # Strategy 2 -- explicit integration for unevaluated Integral
    if result is None and isinstance(expr, sympy.Integral):
        result = _try(
            lambda: sympy.integrate(expr.function, *expr.limits),
            expr, "integrate(Integral)",
        )
        # Reject if still unevaluated
        if result is not None and result.has(sympy.Integral):
            result = None

    # Strategy 2.5 -- numerical evaluation for definite integrals
    #   If symbolic integration failed but the integral has numeric limits,
    #   fall back to .evalf() which uses numerical quadrature.
    if result is None and isinstance(expr, sympy.Integral):
        result = _try_numerical(expr, "evalf(definite integral)")

    # Strategy 3 -- explicit integration for bare integrand
    if result is None and not expr.has(sympy.Integral, sympy.Derivative):
        def _integrate_bare():
            r = sympy.integrate(expr, var)
            return r if not r.has(sympy.Integral) else None
        result = _try(_integrate_bare, expr, "integrate(bare)")

    # Strategy 4 -- explicit differentiation
    if result is None and isinstance(expr, sympy.Derivative):
        result = _try(
            lambda: sympy.diff(expr.args[0], var),
            expr, "diff",
        )

    # Strategy 5 -- simplify
    if result is None:
        result = _try(lambda: sympy.simplify(expr), expr, "simplify")

    # Strategy 6 -- trigsimp
    if result is None:
        result = _try(lambda: sympy.trigsimp(expr), expr, "trigsimp")

    # Strategy 7 -- expand
    if result is None:
        result = _try(lambda: sympy.expand(expr), expr, "expand")

    # -- Final output --
    if result is None:
        return _fail("Could not simplify or solve further")

    if result.has(sympy.Integral):
        # Last resort: try numerical evaluation for any remaining integral
        numerical = _try_numerical(result, "evalf(residual integral)")
        if numerical is not None:
            return _ok(sympy.latex(numerical))
        return _fail("Unable to solve this integral")

    return _ok(sympy.latex(result))


# =====================================================================
#  Helpers
# =====================================================================

def _pick_variable(expr) -> sympy.Symbol:
    """One free symbol -> use it.  Otherwise default to x."""
    free = expr.free_symbols
    if len(free) == 1:
        return list(free)[0]
    return sympy.Symbol("x")


def _try(fn, original_expr, label: str):
    """
    Run *fn()*.  Return the result only if it differs from *original_expr*.
    Return None on failure or if the result is identical to the input.
    """
    try:
        out = fn()
        if out is None:
            return None
        if out == original_expr:
            return None
        print(f"[SOLVER] OK {label} => {out}")
        return out
    except Exception:
        return None


def _try_numerical(expr, label: str):
    """
    Attempt numerical evaluation via ``.evalf()``.

    Returns a SymPy ``Float`` (or ``Integer``) if the result is a clean
    number.  Returns ``None`` if evaluation fails or yields a complex /
    symbolic leftover.
    """
    try:
        val = expr.evalf()
        # Reject if the result still contains free symbols or is complex
        if val.is_number and val.is_real:
            # Round to remove floating-point noise (e.g. 2.49999999 -> 2.5)
            rounded = sympy.nsimplify(val, rational=False, tolerance=1e-10)
            print(f"[SOLVER] OK {label} => {rounded}")
            return rounded
        return None
    except Exception:
        return None


def _ok(solution_latex: str) -> dict:
    return {"status": "success", "solution_latex": solution_latex}


def _fail(message: str) -> dict:
    return {
        "status": "error",
        "solution_latex": r"\text{" + message + "}",
    }


# =====================================================================
#  Integration Test
# =====================================================================

if __name__ == "__main__":
    # The exact OCR-output string from the user's failing test case
    test_latex = r"\int _8^{13}\frac{\sqrt{21-x}}{\sqrt{x}+\sqrt{21-x}}dx"

    print("=" * 60)
    print("  Math-OCR Solver -- Integration Test")
    print("=" * 60)
    print(f"\n[TEST] Raw OCR input : {test_latex}")
    print(f"[TEST] Sanitised     : {sanitize_latex(test_latex)}")

    result = solve_latex(test_latex)
    print(f"\n[TEST] solve_latex result: {result}")

    # Also evaluate via .doit() directly to print the numerical value
    cleaned = sanitize_latex(test_latex)
    expr = parse_latex(cleaned)
    print(f"\n[TEST] Parsed SymPy expr : {expr}")

    evaluated = expr.doit()
    print(f"[TEST] .doit() result    : {evaluated}")

    # Attempt numerical evaluation
    try:
        numerical = float(evaluated.evalf())
        print(f"[TEST] Numerical value   : {numerical}")
    except Exception:
        print(f"[TEST] Numerical evalf   : {evaluated.evalf()}")

    print("\n" + "=" * 60)
