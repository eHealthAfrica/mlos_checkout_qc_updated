"""Schema alignment QC layer, relocated verbatim from app.py:232-278.

``build_schema_report_xlsx`` (app.py's report builder, immediately below ``run_schema_qc`` in
the original file) stays in app.py per D-06 — it is a report builder, not a QC engine.

S3 "Column Name Collision" registers immediately after S2 (INTEG-03/D-10): a header-name
collision, detected upstream by ``qc.columns.normalize_columns`` before any rename is applied,
is reported here as a named failing check rather than silently producing a duplicate column
label. S3 reads its collision groups from an optional ``collisions`` argument, defaulting to
an empty tuple so every existing two-argument call in the test suite keeps working, with S3
emitting PASS for them.

S1 and S2 now compare against the frame's columns exactly as given, not a lower-cased
projection. With normalisation performed once at load (``qc.columns.normalize_columns``), that
defensive re-normalisation inside this check was the second, diverging view of the column set
F7 names — comparing against ``mlos.columns.str.strip().str.lower()`` here while every rule
tests the raw frame is exactly the divergence INTEG-03 removes. This is a de-duplication, not a
behaviour change: the shared fixture's headers are already canonical snake_case, so S1 and S2
report identical values before and after this change.
"""

import pandas as pd

from .domain import MLOS_REQUIRED_COLS, TAKEOFF_REQUIRED_COLS
from .predicates import pct
from .results import register

register("S1", "Schema", "MLoS Schema Alignment", "All required MLoS columns present")
register("S2", "Schema", "Takeoffpoint Schema Alignment", "All required Takeoffpoint columns present")
register("S3", "Schema", "Column Name Collision", "No two original headers normalise to the same column name")


def run_schema_qc(mlos: pd.DataFrame, takeoff: pd.DataFrame, collisions=()):
    """
    Schema alignment QC — checks required columns are present, plus (S3) that no two
    original headers collided during column-name normalisation (INTEG-03/D-10).

    ``collisions`` is the third value ``qc.columns.normalize_columns`` returns: a list of
    dicts, each shaped ``{"normalized": str, "originals": list[str]}``, one per colliding
    group. Defaults to an empty tuple, so every existing two-argument caller keeps working
    and S3 emits PASS for them.

    Returns check entries (same format as run_mlos_qc) and a detail DataFrame.
    Does NOT stop the QC process.
    """
    checks, details = [], []

    mlos_cols    = set(mlos.columns)
    missing_mlos = sorted(MLOS_REQUIRED_COLS - mlos_cols)
    n_mlos_total = len(MLOS_REQUIRED_COLS)
    n_mlos_miss  = len(missing_mlos)
    checks.append({
        "Rule#": "S1", "QC Check": "MLoS Schema Alignment",
        "Description": f"{n_mlos_total - n_mlos_miss}/{n_mlos_total} required MLoS columns present",
        "Failing Rows": n_mlos_miss, "Total Rows": n_mlos_total,
        "Fail %": pct(n_mlos_miss, n_mlos_total),
        "Status": "❌ FAIL" if n_mlos_miss else "✅ PASS",
    })
    if missing_mlos:
        details.append(pd.DataFrame([{
            "Rule#": "S1", "Rule": "MLoS Schema Alignment",
            "Table": "MLoS", "Missing Column": col,
            "Impact": "QC rule(s) referencing this column will be skipped or may return incorrect results",
        } for col in missing_mlos]))

    if not takeoff.empty and len(takeoff.columns) > 0:
        tp_cols    = set(takeoff.columns)
        missing_tp = sorted(TAKEOFF_REQUIRED_COLS - tp_cols)
        n_tp_total = len(TAKEOFF_REQUIRED_COLS)
        n_tp_miss  = len(missing_tp)
        checks.append({
            "Rule#": "S2", "QC Check": "Takeoffpoint Schema Alignment",
            "Description": f"{n_tp_total - n_tp_miss}/{n_tp_total} required Takeoffpoint columns present",
            "Failing Rows": n_tp_miss, "Total Rows": n_tp_total,
            "Fail %": pct(n_tp_miss, n_tp_total),
            "Status": "❌ FAIL" if n_tp_miss else "✅ PASS",
        })
        if missing_tp:
            details.append(pd.DataFrame([{
                "Rule#": "S2", "Rule": "Takeoffpoint Schema Alignment",
                "Table": "Takeoffpoint", "Missing Column": col,
                "Impact": "QC rule(s) referencing this column will be skipped or may return incorrect results",
            } for col in missing_tp]))

    n_collisions = len(collisions)
    n_cols_total = len(mlos.columns)
    if n_collisions:
        description = "; ".join(
            f"{', '.join(group['originals'])} all normalise to {group['normalized']!r}"
            for group in collisions
        )
    else:
        description = "No column headers collided after normalisation"
    checks.append({
        "Rule#": "S3", "QC Check": "Column Name Collision",
        "Description": description,
        "Failing Rows": n_collisions, "Total Rows": n_cols_total,
        "Fail %": pct(n_collisions, n_cols_total),
        "Status": "❌ FAIL" if n_collisions else "✅ PASS",
    })
    if n_collisions:
        details.append(pd.DataFrame([{
            "Rule#": "S3", "Rule": "Column Name Collision",
            "Table": "MLoS", "Colliding Headers": ", ".join(group["originals"]),
            "Normalised Form": group["normalized"],
            "Impact": "QC rule(s) referencing this column may be skipped because it could not be safely renamed",
        } for group in collisions]))

    schema_detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return checks, schema_detail
