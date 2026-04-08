"""Unit tests for OCR LaTeX normalization."""

import pytest

from src.ocr_engine.latex_normalize import normalize_ocr_latex
from src.backend.solver import sanitize_latex
from sympy.parsing.latex import parse_latex


def test_second_derivative_fraction_expands():
    raw = r"\frac{d^2}{dx^2} x^3"
    n = normalize_ocr_latex(raw)
    assert n.count(r"\frac{d}{dx}") == 2
    expr = parse_latex(sanitize_latex(raw))
    assert expr.func.__name__ == "Derivative"


def test_limit_arrow_normalized():
    raw = r"\lim_{h \rightarrow 0} h"
    n = normalize_ocr_latex(raw)
    assert r"\to" in n
    assert r"\rightarrow" not in n


def test_plain_atan_becomes_arctan():
    raw = r"atan(x)+1"
    n = normalize_ocr_latex(raw)
    assert r"\arctan" in n


def test_implicit_mult_before_paren():
    raw = r")x"
    n = normalize_ocr_latex(raw)
    assert ")*x" in n or n == ")*x"


def test_left_right_stripped_for_abs():
    raw = r"\left|x\right|"
    s = sanitize_latex(raw)
    assert "|" in s
    expr = parse_latex(s)
    assert expr.func.__name__ == "Abs"
