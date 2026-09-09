"""Auto-correction layer, relocated verbatim from app.py (auto_correct_mlos, formerly app.py's
"# ─── Auto Correction ───" section).

Per D-09 (01-CONTEXT.md), ``auto_correct_mlos`` moves in this phase even though its two known
defects — the corrected frame diverging from what the cache holds, and a fresh ``eha_guid``
generated on every rerun rather than deterministically — are Phase 2 work (ENGINE-03/ENGINE-04
respectively). The user chose this deliberately so that all pure code lands on the correct side
of the seam in one move rather than leaving one pure function stranded; Phase 2 editing this file
next is expected, not a sign this move was premature. Moving code and changing its behaviour are
different changes, and this relocation does neither of the latter — the five corrections below
are unchanged from app.py, including the local ``uuid`` import and the defensive copy of the
input frame.

This module registers no rule identifiers: auto_correct_mlos is a data transform applied to the
uploaded frame before any QC layer runs, not a check the registry needs to know about.
"""

import pandas as pd

from .domain import FLAG_COLS
from .predicates import vec_is_uuid


def auto_correct_mlos(mlos: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Apply auto-corrections to the MLoS DataFrame.
    Returns a corrected copy and a log of changes made.
    """
    import uuid as _uuid
    df  = mlos.copy()
    log = []   # list of {Column, Correction, Rows Fixed}

    # ── Correction 1: Flag columns NULL → "NA" ───────────────────────────────
    for col in FLAG_COLS:
        if col not in df.columns:
            continue
        mask = df[col].isna() | df[col].astype(str).str.strip().eq("")
        n = int(mask.sum())
        if n:
            df.loc[mask, col] = "NA"
            log.append({"Column": col,
                        "Correction": "NULL → NA",
                        "Rows Fixed": n})

    # ── Correction 1b: scattered NULL or "NA" → "N" ─────────────────────────
    if "scattered" in df.columns:
        mask = (
            df["scattered"].isna() |
            df["scattered"].astype(str).str.strip().eq("") |
            df["scattered"].astype(str).str.strip().eq("NA")
        )
        n = int(mask.sum())
        if n:
            df.loc[mask, "scattered"] = "N"
            log.append({"Column": "scattered",
                        "Correction": "NULL / NA → N",
                        "Rows Fixed": n})

    # ── Correction 2: Fully Accessible + NULL reason → "NA" ──────────────────
    if "accessibility_status" in df.columns and "reasons_for_inaccessibility" in df.columns:
        mask = (
            df["accessibility_status"].astype(str).str.strip().eq("Fully Accessible") &
            (df["reasons_for_inaccessibility"].isna() |
             df["reasons_for_inaccessibility"].astype(str).str.strip().eq(""))
        )
        n = int(mask.sum())
        if n:
            df.loc[mask, "reasons_for_inaccessibility"] = "NA"
            log.append({"Column": "reasons_for_inaccessibility",
                        "Correction": "NULL → NA (Fully Accessible rows)",
                        "Rows Fixed": n})

    # ── Correction 3: source NULL / empty → "IE" ─────────────────────────────
    if "source" in df.columns:
        mask = df["source"].isna() | df["source"].astype(str).str.strip().eq("")
        n = int(mask.sum())
        if n:
            df.loc[mask, "source"] = "IE"
            log.append({"Column": "source",
                        "Correction": "NULL / empty → IE",
                        "Rows Fixed": n})

    # ── Correction 4: eha_guid — strip braces then regenerate invalid UUIDs ──
    if "eha_guid" in df.columns:
        # Step 1: strip any { } characters
        has_braces = df["eha_guid"].astype(str).str.contains(r"[\{\}]", na=False)
        n_brace = int(has_braces.sum())
        if n_brace:
            df.loc[has_braces, "eha_guid"] = (
                df.loc[has_braces, "eha_guid"]
                  .astype(str).str.replace(r"[\{\}]", "", regex=True).str.strip()
            )

        # Step 2: generate a fresh UUID for any value still not a valid UUID
        invalid_mask = ~vec_is_uuid(df["eha_guid"])
        n_gen = int(invalid_mask.sum())
        if n_gen:
            df.loc[invalid_mask, "eha_guid"] = [
                str(_uuid.uuid4()) for _ in range(n_gen)
            ]

        total_fixed = n_brace + n_gen
        if total_fixed:
            log.append({"Column": "eha_guid",
                        "Correction": f"Braces removed ({n_brace} rows); UUID regenerated ({n_gen} rows)",
                        "Rows Fixed": total_fixed})

    return df, log
