"""Shared predicate helpers relocated verbatim from app.py, per D-07.

Imports ``UUID_RE``/``EDITOR_RE`` from the sibling ``domain`` module by relative import — never
through the package's own ``__init__`` (per Pitfall 5, that is the circular-import shape that
produces partially-initialised-module errors sensitive to import order).
"""

import pandas as pd

from .domain import UUID_RE, EDITOR_RE


def pct(v, t): return f"{v/t*100:.1f}%" if t else "0%"

# Vectorized regex checks — avoid per-row Python function calls
def vec_is_uuid(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(UUID_RE.pattern, na=False)

def vec_is_editor(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(EDITOR_RE.pattern, na=False)
