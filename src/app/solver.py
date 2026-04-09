"""Robust OCR LaTeX -> SymPy solving helpers for simple production-safe cases."""

from __future__ import annotations

import logging
import re
from typing import Optional

import sympy
from sympy import Eq, N, integrate, symbols
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

# Primary LaTeX parser — handles raw LaTeX strings directly
try:
    from latex2sympy2 import latex2sympy
    _HAS_LATEX2SYMPY = True
except ImportError:
    _HAS_LATEX2SYMPY = False

from src.ocr.latex_normalize import clean_latex_for_sympy, normalize_ocr_latex

logger = logging.getLogger(__name__)

_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)
_ALLOWED_LOCALS = {
    "sin": sympy.sin,
    "cos": sympy.cos,
    "tan": sympy.tan,
    "sqrt": sympy.sqrt,
    "log": sympy.log,
    "ln": sympy.log,
    "exp": sympy.exp,
    "pi": sympy.pi,
    "E": sympy.E,
    "x": symbols("x"),
    "y": symbols("y"),
    "z": symbols("z"),
    "t": symbols("t"),
}
_GARBAGE_PATTERNS = (r"\begin", "array", r"\mathbb", r"\mathbf", r"\operatorname")


def clean_latex_for_solver(latex: str) -> str:
    """Normalize OCR noise and apply the final lightweight cleanup pass."""
    if not latex:
        return ""

    cleaned = normalize_ocr_latex(latex)
    cleaned = cleaned.replace(r"\left", "").replace(r"\right", "")
    cleaned = re.sub(r'_\{\s*\}', '', cleaned)
    cleaned = re.sub(r'\^\{\s*\}', '', cleaned)
    cleaned = re.sub(r'\\int\s+([_^])', r'\\int\1', cleaned)
    cleaned = re.sub(r'\}\\frac', r'} \\frac', cleaned)
    cleaned = clean_latex_for_sympy(cleaned)
    return cleaned.strip()


def sanitize_latex(raw: str) -> str:
    """Backward-compatible sanitizer used by OCR helpers and parser utilities."""
    return clean_latex_for_solver(raw)


def clean_latex_for_sympy_pipeline(latex: str) -> str:
    """Alias kept for explicit pipeline naming inside the solver."""
    return clean_latex_for_solver(latex)


def reject_garbage(latex: str) -> bool:
    return any(token in latex for token in _GARBAGE_PATTERNS)


def is_simple_expression(latex: str) -> bool:
    return len(latex) < 100 and latex.count("\\") < 10


def classify_expression(latex: str) -> str:
    if r"\int" in latex:
        return "integral"
    if "=" in latex:
        return "equation"
    return "unknown"


def latex_parseable(latex_str: str) -> bool:
    cleaned = clean_latex_for_sympy_pipeline(latex_str)
    if not cleaned or reject_garbage(cleaned) or not is_simple_expression(cleaned):
        return False

    expr_type = classify_expression(cleaned)
    try:
        if expr_type == "equation":
            lhs, rhs = cleaned.split("=", 1)
            _parse_simple_expr(lhs)
            _parse_simple_expr(rhs)
            return True
        if expr_type == "integral":
            parsed = _extract_integral_parts(cleaned)
            if parsed is None:
                return False
            _parse_simple_expr(parsed["integrand"])
            if parsed["lower"] is not None:
                _parse_simple_expr(parsed["lower"])
            if parsed["upper"] is not None:
                _parse_simple_expr(parsed["upper"])
            return True
        _parse_simple_expr(cleaned)
        return True
    except Exception:
        return False


def _try_latex2sympy(raw_latex: str):
    """Attempt to parse raw LaTeX with latex2sympy2; return SymPy expr or None."""
    if not _HAS_LATEX2SYMPY:
        return None
    try:
        expr = latex2sympy(raw_latex)
        return expr
    except Exception as exc:
        logger.debug("latex2sympy2 could not parse '%s': %s", raw_latex, exc)
        return None


def safe_solve(latex: str, exact: bool = False, decimals: int = 3):
    logger.info("Raw OCR output: %s", latex)
    cleaned = clean_latex_for_sympy_pipeline(latex)
    logger.info("Cleaned LaTeX: %s", cleaned)
    decimals = max(2, min(int(decimals), 6))

    if not cleaned:
        return _error("Empty input", cleaned)

    if reject_garbage(cleaned):
        logger.warning("Rejected garbage LaTeX: %s", cleaned)
        return _error("Rejected unsupported LaTeX content", cleaned)

    if not is_simple_expression(cleaned):
        logger.warning("Rejected complex LaTeX: %s", cleaned)
        return _error("Expression too complex for safe solving", cleaned)

    expr_type = classify_expression(cleaned)

    # ── Try latex2sympy2 first (handles raw LaTeX directly) ──────
    l2s_expr = _try_latex2sympy(latex)
    if l2s_expr is not None:
        try:
            result = _solve_from_sympy_expr(l2s_expr, expr_type, exact, decimals)
            if result is not None:
                return {
                    "status": "success",
                    "result": result["result"],
                    "message": result["message"],
                    "display_text": result.get("display_text"),
                    "plot_data": result.get("plot_data"),
                    "cleaned_latex": cleaned,
                    "expression_type": expr_type,
                    "mode": "exact" if exact else "numeric",
                }
        except Exception as exc:
            logger.debug("latex2sympy2 solve path failed, falling back: %s", exc)

    # ── Fallback: manual regex-based parser ───────────────────────
    try:
        if expr_type == "integral":
            result = solve_integral(cleaned, exact=exact, decimals=decimals)
        elif expr_type == "equation":
            result = solve_equation(cleaned, exact=exact, decimals=decimals)
        else:
            return _error("Unsupported expression type", cleaned)

        return {
            "status": "success",
            "result": result["result"],
            "message": result["message"],
            "display_text": result.get("display_text"),
            "plot_data": result.get("plot_data"),
            "cleaned_latex": cleaned,
            "expression_type": expr_type,
            "mode": "exact" if exact else "numeric",
        }
    except Exception as exc:
        logger.exception("Solver error for LaTeX '%s': %s", cleaned, exc)
        return _error("Solver failed to process expression", cleaned)


def solve_latex(latex_str: str) -> dict:
    """Compatibility wrapper for older callers that expect `solution_latex`."""
    result = safe_solve(latex_str)
    if result["status"] == "success":
        return {"status": "success", "solution_latex": result["result"]}
    return {
        "status": "error",
        "solution_latex": r"\text{" + result["message"] + "}",
    }


def solve_equation(latex: str, exact: bool = False, decimals: int = 3) -> dict:
    lhs_text, rhs_text = [part.strip() for part in latex.split("=", 1)]
    lhs = _parse_simple_expr(lhs_text)
    rhs = _parse_simple_expr(rhs_text)
    standard_expr = sympy.simplify(lhs - rhs)
    variable = _pick_variable(standard_expr)
    equation = Eq(standard_expr, 0)
    solutions = sympy.solve(equation, variable)
    if not solutions:
        raise ValueError("No solution found")

    if isinstance(solutions, dict):
        ordered_solutions = [solutions[key] for key in sorted(solutions, key=lambda item: item.name)]
    else:
        ordered_solutions = list(solutions)

    if exact:
        rendered_values = [sympy.latex(value) for value in ordered_solutions]
        rendered = f"{sympy.latex(variable)} = " + ",\\;".join(rendered_values)
        display_text = f"Solutions: {variable} = " + ", ".join(str(value) for value in ordered_solutions)
    else:
        rendered, display_text = _format_numeric_solutions(variable, ordered_solutions, decimals)

    plot_data = _build_plot_data(standard_expr, variable, ordered_solutions, decimals)
    return {
        "result": rendered,
        "message": "Equation solved",
        "display_text": display_text,
        "plot_data": plot_data,
    }


def solve_integral(latex: str, exact: bool = False, decimals: int = 3) -> dict:
    parts = _extract_integral_parts(latex)
    if parts is None:
        raise ValueError("Could not extract integral components")

    variable = symbols(parts["variable"])
    integrand = _parse_simple_expr(parts["integrand"], variable_hint=variable)

    if parts["lower"] is not None and parts["upper"] is not None:
        lower = _parse_simple_expr(parts["lower"], variable_hint=variable)
        upper = _parse_simple_expr(parts["upper"], variable_hint=variable)
        integral_expr = sympy.Integral(integrand, (variable, lower, upper))
        symbolic = integrate(integrand, (variable, lower, upper))
        if symbolic.has(sympy.Integral):
            symbolic = None
        numeric = N(integral_expr)
        if symbolic is not None:
            if exact:
                exact_text = sympy.latex(symbolic)
                return {
                    "result": exact_text,
                    "message": f"Integral solved (numeric fallback: {_format_number_text(numeric, decimals)})",
                    "display_text": f"Result: {symbolic}",
                }
            rounded_value = _format_number_text(numeric, decimals)
            return {
                "result": rounded_value,
                "message": "Integral solved numerically",
                "display_text": f"Result: ≈ {rounded_value}",
            }
        rounded_value = _format_number_text(numeric, decimals)
        return {
            "result": rounded_value,
            "message": "Integral solved numerically",
            "display_text": f"Result: ≈ {rounded_value}",
        }

    symbolic = integrate(integrand, variable)
    if symbolic.has(sympy.Integral):
        numeric = N(integrand.subs(variable, 1))
        return {
            "result": _format_number_text(numeric, decimals),
            "message": "Indefinite integral unsupported symbolically; returning sample numeric fallback",
            "display_text": f"Sample value at {variable}=1: ≈ {_format_number_text(numeric, decimals)}",
        }

    if exact or symbolic.free_symbols:
        return {
            "result": sympy.latex(symbolic),
            "message": "Integral solved symbolically",
            "display_text": f"Result: {symbolic}",
        }

    numeric = N(symbolic)
    return {
        "result": _format_number_text(numeric, decimals),
        "message": "Integral solved numerically",
        "display_text": f"Result: ≈ {_format_number_text(numeric, decimals)}",
    }


def _solve_from_sympy_expr(expr, expr_type: str, exact: bool, decimals: int):
    """Solve a SymPy expression produced by latex2sympy2.

    Returns a result dict on success, or *None* to signal the caller
    should fall through to the legacy regex-based pipeline.
    """
    # ── Integral (latex2sympy2 returns sympy.Integral) ────────────
    if isinstance(expr, sympy.Integral):
        symbolic = expr.doit()
        if symbolic.has(sympy.Integral):
            # Could not evaluate symbolically — try numeric
            numeric = N(expr)
            return {
                "result": _format_number_text(numeric, decimals),
                "message": "Integral solved numerically",
                "display_text": f"Result: ≈ {_format_number_text(numeric, decimals)}",
            }
        if exact or symbolic.free_symbols:
            return {
                "result": sympy.latex(symbolic),
                "message": "Integral solved symbolically",
                "display_text": f"Result: {symbolic}",
            }
        numeric = N(symbolic)
        return {
            "result": _format_number_text(numeric, decimals),
            "message": "Integral solved numerically",
            "display_text": f"Result: ≈ {_format_number_text(numeric, decimals)}",
        }

    # ── Equality (latex2sympy2 returns sympy.Eq) ──────────────────
    if isinstance(expr, sympy.Eq):
        standard_expr = sympy.simplify(expr.lhs - expr.rhs)
        variable = _pick_variable(standard_expr)
        solutions = sympy.solve(expr, variable)
        if not solutions:
            return None  # fall through
        if isinstance(solutions, dict):
            ordered = [solutions[k] for k in sorted(solutions, key=lambda s: s.name)]
        else:
            ordered = list(solutions)
        if exact:
            rendered_values = [sympy.latex(v) for v in ordered]
            rendered = f"{sympy.latex(variable)} = " + ",\\;".join(rendered_values)
            display_text = f"Solutions: {variable} = " + ", ".join(str(v) for v in ordered)
        else:
            rendered, display_text = _format_numeric_solutions(variable, ordered, decimals)
        plot_data = _build_plot_data(standard_expr, variable, ordered, decimals)
        return {
            "result": rendered,
            "message": "Equation solved",
            "display_text": display_text,
            "plot_data": plot_data,
        }

    # ── Plain expression — simplify it ────────────────────────────
    simplified = sympy.simplify(expr)
    if simplified == expr and not expr.free_symbols:
        numeric = N(expr)
        return {
            "result": _format_number_text(numeric, decimals),
            "message": "Expression evaluated",
            "display_text": f"Result: ≈ {_format_number_text(numeric, decimals)}",
        }
    result_latex = sympy.latex(simplified)
    return {
        "result": result_latex,
        "message": "Expression simplified",
        "display_text": f"Result: {simplified}",
    }


def _pick_variable(expr) -> sympy.Symbol:
    free = sorted(expr.free_symbols, key=lambda symbol: symbol.name)
    if free:
        return free[0]
    return symbols("x")


def _parse_simple_expr(expr_text: str, variable_hint: Optional[sympy.Symbol] = None):
    prepared = _latex_to_sympy_expr(expr_text)
    locals_map = dict(_ALLOWED_LOCALS)
    if variable_hint is not None:
        locals_map[variable_hint.name] = variable_hint
    return parse_expr(
        prepared,
        local_dict=locals_map,
        transformations=_TRANSFORMATIONS,
        evaluate=True,
    )


def _latex_to_sympy_expr(expr_text: str) -> str:
    text = expr_text.strip()
    if not text:
        raise ValueError("Empty expression")

    text = _convert_frac(text)
    text = _convert_sqrt(text)
    text = text.replace("{", "(").replace("}", ")")
    text = _convert_exponents(text)
    text = re.sub(r"\\(sin|cos|tan|log|ln|exp)\b", r"\1", text)
    text = re.sub(r"\\pi\b", "pi", text)
    text = re.sub(r"\\cdot", "*", text)
    text = re.sub(r"\\times", "*", text)
    text = re.sub(r"\\,", " ", text)
    text = re.sub(r"\\([a-zA-Z]+)", r"\1", text)
    text = _normalize_function_calls(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _convert_frac(text: str) -> str:
    while r"\frac" in text:
        start = text.find(r"\frac")
        num_start = start + len(r"\frac")
        numerator, next_index = _read_braced(text, num_start)
        denominator, end_index = _read_braced(text, next_index)
        replacement = f"(({_convert_frac(numerator)})/({_convert_frac(denominator)}))"
        text = text[:start] + replacement + text[end_index:]
    return text


def _convert_sqrt(text: str) -> str:
    while r"\sqrt" in text:
        start = text.find(r"\sqrt")
        inner, end_index = _read_braced(text, start + len(r"\sqrt"))
        replacement = f"sqrt({_convert_frac(inner)})"
        text = text[:start] + replacement + text[end_index:]
    return text


def _convert_exponents(text: str) -> str:
    text = re.sub(r"\^\{([^{}]+)\}", r"**(\1)", text)
    text = re.sub(r"\^([A-Za-z0-9])", r"**(\1)", text)
    return text


def _extract_integral_parts(latex: str) -> Optional[dict]:
    text = latex.strip()
    if not text.startswith(r"\int"):
        return None

    index = len(r"\int")
    lower = None
    upper = None

    while index < len(text) and text[index].isspace():
        index += 1

    if index < len(text) and text[index] == "_":
        lower, index = _read_latex_token(text, index + 1)

    while index < len(text) and text[index].isspace():
        index += 1

    if index < len(text) and text[index] == "^":
        upper, index = _read_latex_token(text, index + 1)

    remainder = text[index:].strip()
    diff_match = re.search(r"\s+d\s*([A-Za-z])\s*$", remainder)
    if not diff_match:
        return None

    body = remainder[:diff_match.start()].strip()
    if not body:
        return None

    return {
        "integrand": body,
        "lower": _strip_outer_braces(lower),
        "upper": _strip_outer_braces(upper),
        "variable": diff_match.group(1),
    }


def _strip_outer_braces(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.strip().strip("{}").strip()


def _read_latex_token(text: str, start_index: int) -> tuple[str, int]:
    while start_index < len(text) and text[start_index].isspace():
        start_index += 1

    if start_index >= len(text):
        raise ValueError("Expected LaTeX token")

    if text[start_index] == "{":
        return _read_braced(text, start_index)

    end_index = start_index
    while end_index < len(text):
        char = text[end_index]
        if char.isspace() or char in "_^":
            break
        if end_index > start_index and char == "\\":
            break
        end_index += 1
    return text[start_index:end_index], end_index


def _normalize_function_calls(text: str) -> str:
    pattern = re.compile(r"\b(sin|cos|tan|log|ln|exp)\s+([A-Za-z0-9]+|\([^()]+\))")
    previous = None
    current = text
    while current != previous:
        previous = current
        current = pattern.sub(r"\1(\2)", current)
    return current


def _read_braced(text: str, start_index: int) -> tuple[str, int]:
    while start_index < len(text) and text[start_index].isspace():
        start_index += 1
    if start_index >= len(text) or text[start_index] != "{":
        raise ValueError("Expected braced LaTeX group")

    depth = 0
    for index in range(start_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start_index + 1:index], index + 1
    raise ValueError("Unbalanced LaTeX braces")


def _error(message: str, cleaned_latex: str = "") -> dict:
    return {
        "status": "error",
        "result": None,
        "message": message,
        "cleaned_latex": cleaned_latex,
    }


def _format_numeric_solutions(variable: sympy.Symbol, solutions: list, decimals: int) -> tuple[str, str]:
    values = [_format_solution_value(solution, decimals) for solution in solutions]
    latex_values = [item["latex"] for item in values]
    text_values = [item["text"] for item in values]
    latex_result = f"{sympy.latex(variable)} \\approx " + ",\\;".join(latex_values)
    text_result = f"Solutions: {variable} ≈ " + ", ".join(text_values)
    return latex_result, text_result


def _format_solution_value(value, decimals: int) -> dict:
    numeric = N(value, decimals + 3)
    if getattr(numeric, "is_real", False):
        text = _format_number_text(numeric, decimals)
        return {"text": text, "latex": text}

    real_part = sympy.re(numeric)
    imag_part = sympy.im(numeric)
    real_text = _format_number_text(real_part, decimals)
    imag_text = _format_number_text(abs(imag_part), decimals)
    sign = "+" if imag_part >= 0 else "-"
    text = f"{real_text} {sign} {imag_text}i"
    latex = f"{real_text} {sign} {imag_text}i"
    return {"text": text, "latex": latex}


def _format_number_text(value, decimals: int) -> str:
    try:
        rounded = round(float(N(value)), decimals)
    except Exception:
        return str(value)
    return f"{rounded:.{decimals}f}"


def _build_plot_data(expr, variable: sympy.Symbol, solutions: list, decimals: int) -> Optional[dict]:
    try:
        poly = sympy.Poly(sympy.expand(expr), variable)
    except Exception:
        return None

    if poly.degree() < 1:
        return None

    numeric_roots = []
    has_complex_root = False
    for solution in solutions:
        numeric = N(solution)
        if getattr(numeric, "is_real", False):
            numeric_roots.append(float(numeric))
        else:
            has_complex_root = True

    if not has_complex_root and poly.degree() <= 2:
        return None

    if numeric_roots:
        xmin = min(numeric_roots) - 2.0
        xmax = max(numeric_roots) + 2.0
    else:
        xmin, xmax = -10.0, 10.0

    if xmin == xmax:
        xmin -= 1.0
        xmax += 1.0

    step = (xmax - xmin) / 40.0
    fn = sympy.lambdify(variable, expr, "math")
    xs = []
    ys = []
    for index in range(41):
        x_value = xmin + (step * index)
        try:
            y_value = fn(x_value)
        except Exception:
            continue
        if isinstance(y_value, complex):
            continue
        xs.append(round(x_value, decimals))
        ys.append(round(float(y_value), decimals))

    if not xs:
        return None

    return {
        "variable": variable.name,
        "x": xs,
        "y": ys,
        "standard_form_latex": sympy.latex(Eq(sympy.expand(expr), 0)),
    }
