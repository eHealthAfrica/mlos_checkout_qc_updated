"""MLoS QC layer, relocated from app.py:720-880, with the R11/R12 identifier fix (D-01/D-02).

Rule 11's field-presence loop and rule 12's profile-flag loop used to pass the bare literal
identifier ("11" or "12") to every iteration, so three checks all reported "11" and eight checks
all reported "12" — the F3 defect this phase closes. The fix touches exactly two call sites: the
identifier argument each loop passes to ``add()`` is now built from the column name being
checked (``f"11.{col}"`` / ``f"12.{col}"``), field-named per D-01/D-02 because the letter suffixes
``11a``/``11b`` are already taken by the two conflict rules. Every other identifier in this file
(1-10, 11a, 11b, 13, 14) is frozen per D-04 and unchanged.

``YN_NA_COLS`` is now an ordered tuple (qc/domain.py, plan 03's D-10/D-11 fix), so the eight
rule-12 checks emit in the same fixed order on every process — the other half of the F10 defect
this phase closes, with the registry's import-time ``register()`` order as the structural
backstop (D-12).
"""

import pandas as pd

from .domain import VALID_ACC, VALID_HAB, VALID_YN, VALID_YN_NA, YN_NA_COLS
from .predicates import pct, vec_is_uuid, vec_is_editor, vec_is_absent
from .results import register

register("1", "MLoS", "Required Fields — Not Null", "All schema NOT NULL fields must not be empty")
register("2", "MLoS", "Takeoffpoint Name Match", "takeoffpoint in MLoS must match name in Takeoffpoint table")
register("2.missing", "MLoS", "Takeoffpoint Name Missing", "takeoffpoint in MLoS must not be blank")
register("3", "MLoS", "Takeoffpoint Code Match", "takeoffpoint_code in MLoS must match code in Takeoffpoint table")
register("3.missing", "MLoS", "Takeoffpoint Code Missing", "takeoffpoint_code in MLoS must not be blank")
register("4", "MLoS", "Ward Code Match", "ward_code in MLoS must match wardcode in Takeoffpoint table")
register("4.missing", "MLoS", "Ward Code Missing", "ward_code in MLoS must not be blank")
register("5", "MLoS", "Security Compromised Y/N", "security_compromised must be Y or N")
register("6", "MLoS", "Accessibility Status Valid",
         "accessibility_status must be: Fully Accessible, Partially Accessible, or Inaccessible")
register("7", "MLoS", "Reason for Inaccessibility Required",
         "Partially Accessible & Inaccessible settlements must have reasons_for_inaccessibility")
register("8", "MLoS", "Habitational Status Valid",
         "habitational_status must be: Abandoned, Migrated, Inhabited, or Partially Inhabited")
register("9", "MLoS", "set_target ≤ set_population", "set_target must not exceed set_population")
register("10", "MLoS", "number_of_household ≤ set_population",
         "number_of_household must not exceed set_population")
register("11.urban", "MLoS", "urban is Y or N", "urban must be Y or N and must not be null")
register("11.rural", "MLoS", "rural is Y or N", "rural must be Y or N and must not be null")
register("11.scattered", "MLoS", "scattered is Y or N", "scattered must be Y or N and must not be null")
register("11a", "MLoS", "Cannot be both Urban and Rural",
         "A settlement cannot be both urban=Y and rural=Y")
register("11b", "MLoS", "Urban cannot be Scattered",
         "Urban settlements cannot be categorised as scattered")
register("12.highrisk", "MLoS", "highrisk = Y/N/NA", "highrisk must be Y, N, or NA")
register("12.slums", "MLoS", "slums = Y/N/NA", "slums must be Y, N, or NA")
register("12.densely_populated", "MLoS", "densely_populated = Y/N/NA", "densely_populated must be Y, N, or NA")
register("12.hard2reach", "MLoS", "hard2reach = Y/N/NA", "hard2reach must be Y, N, or NA")
register("12.border", "MLoS", "border = Y/N/NA", "border must be Y, N, or NA")
register("12.nomadic", "MLoS", "nomadic = Y/N/NA", "nomadic must be Y, N, or NA")
register("12.riverine", "MLoS", "riverine = Y/N/NA", "riverine must be Y, N, or NA")
register("12.fulani", "MLoS", "fulani = Y/N/NA", "fulani must be Y, N, or NA")
register("13", "MLoS", "Editor Format (firstname.surname)",
         "editor must be in format: firstname.surname (all lowercase)")
register("14", "MLoS", "eha_guid is UUID",
         "eha_guid must be a valid UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)")


def run_mlos_qc(mlos: pd.DataFrame, takeoff: pd.DataFrame):
    checks, details = [], []
    total  = len(mlos)
    id_col = "ogc_fid" if "ogc_fid" in mlos.columns else mlos.columns[0]
    BASE   = [c for c in [id_col,"state_name","lga_name","ward_code",
                           "settlement_name","takeoffpoint","takeoffpoint_code"]
              if c in mlos.columns]

    def add(num, rule, desc, mask, extra=None):
        n    = int(mask.sum())
        cols = BASE + [c for c in (extra or []) if c in mlos.columns and c not in BASE]
        checks.append({"Rule#": num, "QC Check": rule, "Description": desc,
                       "Failing Rows": n, "Total Rows": total,
                       "Fail %": pct(n, total),
                       "Status": "❌ FAIL" if n else "✅ PASS"})
        if n:
            sub = mlos[mask][cols].copy()
            sub.insert(0, "Rule#", num)
            sub.insert(1, "Rule", rule)
            details.append(sub)

    # R1 — All schema NOT NULL fields must not be null
    # Full list of 28 NOT NULL columns from the PostgreSQL schema.
    _NOT_NULL_COLS = [c for c in [
        "state_code", "state_name", "lga_code", "lga_name", "ward_name", "ward_code",
        "settlement_name", "latitude", "longitude",
        "security_compromised", "accessibility_status",
        "set_population", "set_target", "number_of_household",
        "urban", "rural", "scattered",
        "highrisk", "slums", "densely_populated", "hard2reach",
        "border", "nomadic", "riverine", "fulani",
        "timestamp", "eha_guid", "settlementarea_globalid",
    ] if c in mlos.columns]
    if _NOT_NULL_COLS:
        # D-04/D-05: absence, not just SQL NULL — vec_is_absent also catches the empty-string and
        # whitespace-only cells CSV/XLSX blanks arrive as under keep_default_na=False, which
        # .isnull() alone missed (F2/INTEG-01). One boolean frame, keyed by column name, built
        # once and reused for both the failing-row mask and the "Null Fields" detail column below
        # — never re-derived per row, so the two can never disagree with each other.
        _absent_frame = pd.concat(
            [vec_is_absent(mlos[c]) for c in _NOT_NULL_COLS], axis=1, keys=_NOT_NULL_COLS,
        )
        _null_mask = _absent_frame.any(axis=1)
        _n1 = int(_null_mask.sum())
        checks.append({
            "Rule#": "1", "QC Check": "Required Fields — Not Null",
            "Description": "All schema NOT NULL fields must not be empty: " + ", ".join(_NOT_NULL_COLS),
            "Failing Rows": _n1, "Total Rows": total,
            "Fail %": pct(_n1, total),
            "Status": "❌ FAIL" if _n1 else "✅ PASS",
        })
        if _n1:
            _cols1 = BASE + [c for c in _NOT_NULL_COLS if c not in BASE]
            _sub1 = mlos[_null_mask][_cols1].copy()
            _sub1.insert(0, "Rule#", "1")
            _sub1.insert(1, "Rule", "Required Fields — Not Null")
            _sub1["Null Fields"] = _absent_frame[_null_mask].apply(
                lambda row: ", ".join(col for col in _NOT_NULL_COLS if row[col]),
                axis=1,
            )
            details.append(_sub1)

    # R2 / 2.missing — Takeoffpoint Name Match
    # D-01/D-03/D-07 (INTEG-02): a blank `takeoffpoint` cell must not silently match a blank
    # `name` cell in the Takeoffpoint table (F9). The valid-target set is built from
    # non-absent Takeoffpoint names only (vec_is_absent, not .dropna(), because a CSV/XLSX
    # blank arrives as "" under keep_default_na=False and .dropna() cannot remove it), AND the
    # match mask itself excludes rows whose MLoS-side source cell is absent — both halves are
    # required, or a blank source would fail both "2" and "2.missing" (four checks instead of
    # D-03's three). "2.missing" fires unconditionally whenever the MLoS-side column exists,
    # even with no Takeoffpoint table supplied at all (D-07).
    if "takeoffpoint" in mlos.columns:
        _absent2 = vec_is_absent(mlos["takeoffpoint"])
        if "name" in takeoff.columns:
            _valid2 = set(
                takeoff.loc[~vec_is_absent(takeoff["name"]), "name"].astype(str).str.strip()
            )
            _not_matched2 = ~mlos["takeoffpoint"].astype(str).str.strip().isin(_valid2)
            add("2", "Takeoffpoint Name Match",
                "takeoffpoint in MLoS must match name in Takeoffpoint table",
                ~_absent2 & _not_matched2, ["takeoffpoint"])
        add("2.missing", "Takeoffpoint Name Missing",
            "takeoffpoint in MLoS must not be blank",
            _absent2, ["takeoffpoint"])

    # R3 / 3.missing — Takeoffpoint Code Match (mirrors R2/2.missing; see comment above)
    if "takeoffpoint_code" in mlos.columns:
        _absent3 = vec_is_absent(mlos["takeoffpoint_code"])
        if "code" in takeoff.columns:
            _valid3 = set(
                takeoff.loc[~vec_is_absent(takeoff["code"]), "code"].astype(str).str.strip()
            )
            _not_matched3 = ~mlos["takeoffpoint_code"].astype(str).str.strip().isin(_valid3)
            add("3", "Takeoffpoint Code Match",
                "takeoffpoint_code in MLoS must match code in Takeoffpoint table",
                ~_absent3 & _not_matched3, ["takeoffpoint_code"])
        add("3.missing", "Takeoffpoint Code Missing",
            "takeoffpoint_code in MLoS must not be blank",
            _absent3, ["takeoffpoint_code"])

    # R4 / 4.missing — Ward Code Match (mirrors R2/2.missing; see comment above)
    if "ward_code" in mlos.columns:
        _absent4 = vec_is_absent(mlos["ward_code"])
        if "wardcode" in takeoff.columns:
            _valid4 = set(
                takeoff.loc[~vec_is_absent(takeoff["wardcode"]), "wardcode"].astype(str).str.strip()
            )
            _not_matched4 = ~mlos["ward_code"].astype(str).str.strip().isin(_valid4)
            add("4", "Ward Code Match",
                "ward_code in MLoS must match wardcode in Takeoffpoint table",
                ~_absent4 & _not_matched4, ["ward_code"])
        add("4.missing", "Ward Code Missing",
            "ward_code in MLoS must not be blank",
            _absent4, ["ward_code"])

    # R5 — Security Compromised Y/N
    if "security_compromised" in mlos.columns:
        add("5", "Security Compromised Y/N",
            "security_compromised must be Y or N",
            ~mlos["security_compromised"].astype(str).str.strip().isin({"Y", "N"}),
            ["security_compromised"])

    # R6 — Accessibility Status Valid
    if "accessibility_status" in mlos.columns:
        add("6", "Accessibility Status Valid",
            "accessibility_status must be: Fully Accessible, Partially Accessible, or Inaccessible",
            ~mlos["accessibility_status"].astype(str).str.strip().isin(VALID_ACC),
            ["accessibility_status"])

    # R7 — Reason for Inaccessibility Required
    if "accessibility_status" in mlos.columns and "reasons_for_inaccessibility" in mlos.columns:
        needs     = mlos["accessibility_status"].isin(["Partially Accessible", "Inaccessible"])
        no_reason = (mlos["reasons_for_inaccessibility"].isna() |
                     mlos["reasons_for_inaccessibility"].astype(str).str.strip().eq(""))
        add("7", "Reason for Inaccessibility Required",
            "Partially Accessible & Inaccessible settlements must have reasons_for_inaccessibility",
            needs & no_reason, ["accessibility_status", "reasons_for_inaccessibility"])

    # R8 — Habitational Status Valid
    if "habitational_status" in mlos.columns:
        add("8", "Habitational Status Valid",
            "habitational_status must be: Abandoned, Migrated, Inhabited, or Partially Inhabited",
            ~mlos["habitational_status"].astype(str).str.strip().isin(VALID_HAB),
            ["habitational_status"])

    # R9 — set_target must not exceed set_population
    if "set_target" in mlos.columns and "set_population" in mlos.columns:
        mask = (pd.to_numeric(mlos["set_target"], errors="coerce") >
                pd.to_numeric(mlos["set_population"], errors="coerce")).fillna(False)
        add("9", "set_target ≤ set_population",
            "set_target must not exceed set_population",
            mask, ["set_target", "set_population"])

    # R10 — number_of_household must not exceed set_population
    if "number_of_household" in mlos.columns and "set_population" in mlos.columns:
        mask = (pd.to_numeric(mlos["number_of_household"], errors="coerce") >
                pd.to_numeric(mlos["set_population"], errors="coerce")).fillna(False)
        add("10", "number_of_household ≤ set_population",
            "number_of_household must not exceed set_population",
            mask, ["number_of_household", "set_population"])

    # R11 — Urban / Rural / Scattered must be Y or N
    if "urban" in mlos.columns:
        add("11.urban", "urban is Y or N",
            "urban must be Y or N and must not be null",
            ~mlos["urban"].astype(str).str.strip().isin(VALID_YN), ["urban"])
    if "rural" in mlos.columns:
        add("11.rural", "rural is Y or N",
            "rural must be Y or N and must not be null",
            ~mlos["rural"].astype(str).str.strip().isin(VALID_YN), ["rural"])
    if "scattered" in mlos.columns:
        add("11.scattered", "scattered is Y or N",
            "scattered must be Y or N and must not be null",
            ~mlos["scattered"].astype(str).str.strip().isin(VALID_YN), ["scattered"])

    if "urban" in mlos.columns and "rural" in mlos.columns:
        mask = ((mlos["urban"].astype(str).str.strip() == "Y") &
                (mlos["rural"].astype(str).str.strip() == "Y"))
        add("11a", "Cannot be both Urban and Rural",
            "A settlement cannot be both urban=Y and rural=Y", mask, ["urban", "rural"])

    if "urban" in mlos.columns and "scattered" in mlos.columns:
        mask = ((mlos["urban"].astype(str).str.strip() == "Y") &
                (mlos["scattered"].astype(str).str.strip() == "Y"))
        add("11b", "Urban cannot be Scattered",
            "Urban settlements cannot be categorised as scattered", mask, ["urban", "scattered"])

    # R12 — Profile Flags must be Y / N / NA
    for col in YN_NA_COLS:
        if col in mlos.columns:
            add(f"12.{col}", f"{col} = Y/N/NA",
                f"{col} must be Y, N, or NA",
                ~mlos[col].astype(str).str.strip().isin(VALID_YN_NA), [col])

    # R13 — Editor must follow firstname.surname format
    if "editor" in mlos.columns:
        add("13", "Editor Format (firstname.surname)",
            "editor must be in format: firstname.surname (all lowercase)",
            ~vec_is_editor(mlos["editor"]), ["editor"])

    # R14 — eha_guid must be a valid UUID
    if "eha_guid" in mlos.columns:
        add("14", "eha_guid is UUID",
            "eha_guid must be a valid UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)",
            ~vec_is_uuid(mlos["eha_guid"]), ["eha_guid"])

    # Keep original mlos_df indices so make_longitudinal_df can match failing rows correctly
    return checks, pd.concat(details) if details else pd.DataFrame()
