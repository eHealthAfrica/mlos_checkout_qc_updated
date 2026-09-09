"""Schema alignment QC layer, relocated verbatim from app.py:232-278.

``build_schema_report_xlsx`` (app.py's report builder, immediately below ``run_schema_qc`` in
the original file) stays in app.py per D-06 — it is a report builder, not a QC engine.
"""

import pandas as pd

from .domain import MLOS_REQUIRED_COLS, TAKEOFF_REQUIRED_COLS
from .predicates import pct
from .results import register

register("S1", "Schema", "MLoS Schema Alignment", "All required MLoS columns present")
register("S2", "Schema", "Takeoffpoint Schema Alignment", "All required Takeoffpoint columns present")


def run_schema_qc(mlos: pd.DataFrame, takeoff: pd.DataFrame):
    """
    Schema alignment QC — checks required columns are present.
    Returns check entries (same format as run_mlos_qc) and a detail DataFrame.
    Does NOT stop the QC process.
    """
    checks, details = [], []

    mlos_cols    = set(mlos.columns.str.strip().str.lower())
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
        tp_cols    = set(takeoff.columns.str.strip().str.lower())
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

    schema_detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return checks, schema_detail
