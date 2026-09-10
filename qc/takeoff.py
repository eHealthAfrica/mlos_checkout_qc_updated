"""Takeoffpoint QC layer, relocated verbatim from app.py:721-764 (run_takeoff_qc).

Registers TP2, TP3, TP4 and TP5 at import time — all four identifiers are frozen by D-04 and
unchanged by this relocation. Preserves the early return that yields an empty check list and an
empty detail frame when the takeoff frame is empty or has no columns; that early return is why
the Takeoffpoint layer can contribute zero checks, which is the condition Phase 3's VERDICT-02
will have to score as not-applicable.
"""

import pandas as pd

from .predicates import pct, vec_is_uuid, vec_is_absent
from .results import register

register("TP2", "Takeoffpoint", "Name matches MLoS takeoffpoint",
         "name in Takeoffpoint must match takeoffpoint column in MLoS")
register("TP2.missing", "Takeoffpoint", "Name Missing", "name in Takeoffpoint must not be blank")
register("TP3", "Takeoffpoint", "Code matches MLoS takeoffpoint_code",
         "code in Takeoffpoint must match takeoffpoint_code in MLoS")
register("TP3.missing", "Takeoffpoint", "Code Missing", "code in Takeoffpoint must not be blank")
register("TP4", "Takeoffpoint", "wardcode matches MLoS ward_code",
         "wardcode in Takeoffpoint must match ward_code in MLoS")
register("TP4.missing", "Takeoffpoint", "Wardcode Missing", "wardcode in Takeoffpoint must not be blank")
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

    # TP2 / TP2.missing — mirrors qc/mlos.py's R2/2.missing: guard on the Takeoffpoint-side
    # column, compute its absence mask, and only inside a nested guard on the MLoS-side column
    # build the valid-target set from non-absent MLoS values and emit TP2 with the
    # not-absent-and-not-matched conjunction. TP2.missing fires on the bare absence mask inside
    # the outer guard only — the Takeoffpoint-side trio stays silent with no table (D-07).
    if "name" in takeoff.columns:
        _absentTP2 = vec_is_absent(takeoff["name"])
        if "takeoffpoint" in mlos.columns:
            _validTP2 = set(
                mlos.loc[~vec_is_absent(mlos["takeoffpoint"]), "takeoffpoint"].astype(str).str.strip()
            )
            _not_matchedTP2 = ~takeoff["name"].astype(str).str.strip().isin(_validTP2)
            add("TP2", "Name matches MLoS takeoffpoint",
                "name in Takeoffpoint must match takeoffpoint column in MLoS",
                ~_absentTP2 & _not_matchedTP2, ["name"])
        add("TP2.missing", "Name Missing", "name in Takeoffpoint must not be blank",
            _absentTP2, ["name"])

    # TP3 / TP3.missing (mirrors TP2/TP2.missing above)
    if "code" in takeoff.columns:
        _absentTP3 = vec_is_absent(takeoff["code"])
        if "takeoffpoint_code" in mlos.columns:
            _validTP3 = set(
                mlos.loc[~vec_is_absent(mlos["takeoffpoint_code"]), "takeoffpoint_code"]
                .astype(str).str.strip()
            )
            _not_matchedTP3 = ~takeoff["code"].astype(str).str.strip().isin(_validTP3)
            add("TP3", "Code matches MLoS takeoffpoint_code",
                "code in Takeoffpoint must match takeoffpoint_code in MLoS",
                ~_absentTP3 & _not_matchedTP3, ["code"])
        add("TP3.missing", "Code Missing", "code in Takeoffpoint must not be blank",
            _absentTP3, ["code"])

    # TP4 / TP4.missing (mirrors TP2/TP2.missing above)
    if "wardcode" in takeoff.columns:
        _absentTP4 = vec_is_absent(takeoff["wardcode"])
        if "ward_code" in mlos.columns:
            _validTP4 = set(
                mlos.loc[~vec_is_absent(mlos["ward_code"]), "ward_code"].astype(str).str.strip()
            )
            _not_matchedTP4 = ~takeoff["wardcode"].astype(str).str.strip().isin(_validTP4)
            add("TP4", "wardcode matches MLoS ward_code",
                "wardcode in Takeoffpoint must match ward_code in MLoS",
                ~_absentTP4 & _not_matchedTP4, ["wardcode"])
        add("TP4.missing", "Wardcode Missing", "wardcode in Takeoffpoint must not be blank",
            _absentTP4, ["wardcode"])

    if "globalid" in takeoff.columns:
        add("TP5","globalid is UUID","globalid must be a valid UUID",
            ~vec_is_uuid(takeoff["globalid"]), ["globalid"])

    return checks, pd.concat(details, ignore_index=True) if details else pd.DataFrame()
