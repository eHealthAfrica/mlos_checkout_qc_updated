"""Shared predicate helpers relocated verbatim from app.py, per D-07.

Imports ``UUID_RE``/``EDITOR_RE`` from the sibling ``domain`` module by relative import — never
through the package's own ``__init__`` (per Pitfall 5, that is the circular-import shape that
produces partially-initialised-module errors sensitive to import order).
"""

import pandas as pd

from .domain import UUID_RE, EDITOR_RE, ABSENCE_SENTINELS


def pct(v, t): return f"{v/t*100:.1f}%" if t else "0%"

# Vectorized regex checks — avoid per-row Python function calls
def vec_is_uuid(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(UUID_RE.pattern, na=False)

def vec_is_editor(series: "pd.Series") -> "pd.Series":
    s = series.astype(str).str.strip()
    return s.str.match(EDITOR_RE.pattern, na=False)

def vec_is_absent(series: "pd.Series") -> "pd.Series":
    """D-04's absence predicate, vectorised: a cell is absent when it is pandas NA/None/NaN, the
    empty string, whitespace-only, or one of the case-insensitive ABSENCE_SENTINELS tokens —
    except the exact literal "NA", matched case-sensitively, which D-05 exempts because it is
    simultaneously a valid flag value in every FLAG_COLS column and Nasarawa's state_code.

    Built from three disjunctive parts over a stripped string projection, never ``.apply`` or a
    per-row loop: the Series' own ``isna()`` (catches real ``None``/NaN/``pd.NA`` even where
    ``str()`` would otherwise obscure them, e.g. ``pd.NA`` stringifies to ``"<NA>"``), the
    stripped projection equal to the empty string, and its lower-cased form's membership in
    ``ABSENCE_SENTINELS`` conjoined with the stripped projection not equal to the exempt literal.
    An empty input Series returns an empty boolean Series and raises nothing.
    """
    stripped = series.astype(str).str.strip()
    lowered = stripped.str.lower()
    return (
        series.isna()
        | stripped.eq("")
        | (lowered.isin(ABSENCE_SENTINELS) & stripped.ne("NA"))
    )
