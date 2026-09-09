"""Takeoffpoint QC layer, relocated verbatim from app.py:721-764 (run_takeoff_qc).

Registers TP2, TP3, TP4 and TP5 at import time — all four identifiers are frozen by D-04 and
unchanged by this relocation. Preserves the early return that yields an empty check list and an
empty detail frame when the takeoff frame is empty or has no columns; that early return is why
the Takeoffpoint layer can contribute zero checks, which is the condition Phase 3's VERDICT-02
will have to score as not-applicable.
"""

import pandas as pd

from .predicates import pct, vec_is_uuid
from .results import register

register("TP2", "Takeoffpoint", "Name matches MLoS takeoffpoint",
         "name in Takeoffpoint must match takeoffpoint column in MLoS")
register("TP3", "Takeoffpoint", "Code matches MLoS takeoffpoint_code",
         "code in Takeoffpoint must match takeoffpoint_code in MLoS")
register("TP4", "Takeoffpoint", "wardcode matches MLoS ward_code",
         "wardcode in Takeoffpoint must match ward_code in MLoS")
register("TP5", "Takeoffpoint", "globalid is UUID", "globalid must be a valid UUID")


def run_takeoff_qc(takeoff: pd.DataFrame, mlos: pd.DataFrame):
    if takeoff.empty or len(takeoff.columns) == 0:
        return [], pd.DataFrame()
    checks, details = [], []
    total  = len(takeoff)
    id_col = "ogc_fid" if "ogc_fid" in takeoff.columns else takeoff.columns[0]
    BASE   = [c for c in [id_col,"name","wardcode","code"] if c in takeoff.columns]

    def add(num, rule, desc, mask, extra=None):
        n    = int(mask.sum())
        cols = BASE + [c for c in (extra or []) if c in takeoff.columns and c not in BASE]
        checks.append({"Rule#": num, "QC Check": rule, "Description": desc,
                       "Failing Rows": n, "Total Rows": total,
                       "Fail %": pct(n, total),
                       "Status": "❌ FAIL" if n else "✅ PASS"})
        if n:
            sub = takeoff[mask][cols].copy()
            sub.insert(0, "Rule#", num)
            sub.insert(1, "Rule", rule)
            details.append(sub)

    if "name" in takeoff.columns and "takeoffpoint" in mlos.columns:
        add("TP2","Name matches MLoS takeoffpoint",
            "name in Takeoffpoint must match takeoffpoint column in MLoS",
            ~takeoff["name"].astype(str).str.strip().isin(set(mlos["takeoffpoint"].dropna().str.strip())),
            ["name"])

    if "code" in takeoff.columns and "takeoffpoint_code" in mlos.columns:
        add("TP3","Code matches MLoS takeoffpoint_code",
            "code in Takeoffpoint must match takeoffpoint_code in MLoS",
            ~takeoff["code"].astype(str).str.strip().isin(set(mlos["takeoffpoint_code"].dropna().str.strip())),
            ["code"])

    if "wardcode" in takeoff.columns and "ward_code" in mlos.columns:
        add("TP4","wardcode matches MLoS ward_code",
            "wardcode in Takeoffpoint must match ward_code in MLoS",
            ~takeoff["wardcode"].astype(str).str.strip().isin(set(mlos["ward_code"].dropna().str.strip())),
            ["wardcode"])

    if "globalid" in takeoff.columns:
        add("TP5","globalid is UUID","globalid must be a valid UUID",
            ~vec_is_uuid(takeoff["globalid"]), ["globalid"])

    return checks, pd.concat(details, ignore_index=True) if details else pd.DataFrame()
