"""
Normalize OCR / user LaTeX before SymPy's ``parse_latex``.

Covers common failure modes: plain-text trig names, higher-order derivative
fractions (parsed as multipliers by the ANTLR grammar), limit arrows, stray
pipes, and implicit multiplication between closing parens and factors.
"""

from __future__ import annotations

import re


def clean_latex_for_sympy(latex: str) -> str:
    """Apply minimal cleanup so OCR LaTeX is safer to route into SymPy."""
    if not latex:
        return ""

    cleaned = latex.replace("*", "")
    cleaned = cleaned.replace(r"\,", " ")
    cleaned = re.sub(r"(?<![A-Za-z\\])d\s*([A-Za-z])", r" d \1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_ocr_latex(s: str) -> str:
    if not s:
        return s

    t = s.strip()

    # Unicode and punctuation often seen in OCR / editors
    t = (
        t.replace("\u2212", "-")
        .replace("\u00d7", r" \cdot ")
        .replace("\u22c5", r" \cdot ")
        .replace("\u03c0", r"\pi")
        .replace("\u221e", r"\infty")
    )

    # \mathrm{ln} / \text{ln} → \ln
    t = re.sub(
        r"\\(?:mathrm|text|textrm|mbox)\{\s*ln\s*\}",
        r"\\ln",
        t,
        flags=re.IGNORECASE,
    )

    # Plain "ln(" from OCR (no backslash)
    t = re.sub(r"(?<!\\)\bln\s*\(", r"\\ln(", t, flags=re.IGNORECASE)

    # Inverse trig written like operatorname
    t = re.sub(
        r"\\operatorname\{\s*sin\s*\}\s*\^\s*\{\s*-\s*1\s*\}",
        r"\\arcsin",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\\operatorname\{\s*cos\s*\}\s*\^\s*\{\s*-\s*1\s*\}",
        r"\\arccos",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\\operatorname\{\s*tan\s*\}\s*\^\s*\{\s*-\s*1\s*\}",
        r"\\arctan",
        t,
        flags=re.IGNORECASE,
    )

    # atan / asin / acos (OCR) → LaTeX commands SymPy understands
    t = re.sub(r"(?<!\\)\batan\s*\(", r"\\arctan(", t, flags=re.IGNORECASE)
    t = re.sub(r"(?<!\\)\basin\s*\(", r"\\arcsin(", t, flags=re.IGNORECASE)
    t = re.sub(r"(?<!\\)\bacos\s*\(", r"\\arccos(", t, flags=re.IGNORECASE)

    # exp(x) without backslash
    t = re.sub(r"(?<!\\)\bexp\s*\(", r"\\exp(", t, flags=re.IGNORECASE)

    t = _expand_higher_derivative_fractions(t)

    # Limits: \rightarrow / \Rightarrow → \to
    t = re.sub(r"\\rightarrow", r"\\to", t)
    t = re.sub(r"\\Rightarrow", r"\\to", t)
    t = re.sub(r"\\longrightarrow", r"\\to", t)

    # Standalone Greek names from OCR (word boundaries)
    _GREEK = (
        ("alpha", r"\alpha"),
        ("beta", r"\beta"),
        ("gamma", r"\gamma"),
        ("delta", r"\delta"),
        ("theta", r"\theta"),
        ("lambda", r"\lambda"),
        ("mu", r"\mu"),
        ("sigma", r"\sigma"),
        ("omega", r"\omega"),
        ("phi", r"\phi"),
        ("psi", r"\psi"),
        ("rho", r"\rho"),
        ("tau", r"\tau"),
    )
    for name, cmd in _GREEK:
        t = re.sub(
            rf"(?<!\\)\b{name}\b",
            lambda _m, c=cmd: c,
            t,
            flags=re.IGNORECASE,
        )

    # pi / Pi → \pi when not already a command
    t = re.sub(
        r"(?<!\\)\bpi\b",
        lambda _m: r"\pi",
        t,
        flags=re.IGNORECASE,
    )

    t = _insert_implicit_multiplication(t)

    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def _expand_higher_derivative_fractions(s: str) -> str:
    """
    SymPy parses ``\\frac{d^2}{dx^2} f`` as ``f * (d^2 / dx^2)``.
    Rewrite as nested ``\\frac{d}{dx}`` which becomes ``Derivative(..., (x, n))``.
    """

    def build_replacement(n: int) -> str:
        # Avoid r"\f..." — that is a form-feed escape even in raw strings.
        frag = "\\frac{d}{dx}"
        return frag * n

    out = s
    for n in range(9, 1, -1):
        ns = str(n)
        patterns = [
            rf"\\frac\s*{{\s*d\s*\^\s*{ns}\s*}}\s*{{\s*dx\s*\^\s*{ns}\s*}}",
            rf"\\frac\s*{{\s*d\s*\^\s*\{{\s*{ns}\s*\}}\s*}}\s*{{\s*dx\s*\^\s*\{{\s*{ns}\s*\}}\s*}}",
            rf"\\frac\s*{{\s*d\s*\^\s*{ns}\s*}}\s*{{\s*d\s+x\s*\^\s*{ns}\s*}}",
            rf"\\frac\s*{{\s*d\s*\^\s*\{{\s*{ns}\s*\}}\s*}}\s*{{\s*d\s+x\s*\^\s*\{{\s*{ns}\s*\}}\s*}}",
        ]
        rep = build_replacement(n)
        for pat in patterns:
            # str replacements are interpreted as templates: "\\frac" would see "\\f" → form feed.
            out = re.sub(pat, lambda _m, r=rep: r, out, flags=re.IGNORECASE)
    return out


def _insert_implicit_multiplication(s: str) -> str:
    # 2\pi, 3\sin(x), …
    s = re.sub(r"(?<=\d)(?=\\[a-zA-Z])", "*", s)

    # ) followed by (  →  )*(
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == ")" and i + 1 < n and s[i + 1] == "(":
            out.append(")*(")
            i += 2
            continue
        out.append(s[i])
        i += 1
    t = "".join(out)

    # ) followed by letter, digit, or backslash-command
    t = re.sub(r"\)(?=[a-zA-Z0-9\\])", r")*", t)
    return t
