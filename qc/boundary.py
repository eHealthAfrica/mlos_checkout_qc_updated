"""Boundary QC layer, relocated verbatim from app.py:303-456 (run_ward_boundary_qc).

Registers B0, B1, B2 and B3 at import time, last among the five layers so they read at the end
of canonical_order() — that order is load-bearing beyond this phase, since Phase 3's VERDICT-06
requires boundary checks to read B0, B1, B2, B3 in every summary table and export.

The two reference frames (``ref_df``, ``bbox_df``) stay function parameters. Nothing under
``qc/`` knows where the bundled ward reference CSVs live: the path constants and the Streamlit-
cached loader that reads them both stay in app.py, which loads the two DataFrames and passes
them in here — that loader is decorated for Streamlit caching and resolves paths relative to
app.py, so it belongs on the UI side of the seam.

Preserves both B0 emission paths: when the ward code column is absent, the function appends a
single failing check and returns immediately with an empty detail frame; when the column is
present, the same identifier is emitted through the ``add()`` closure alongside B1-B3. Those two
paths are mutually exclusive and both survive the move, because the early-return path is what
keeps a file missing that column from crashing the run.
"""

import pandas as pd

from .predicates import pct, vec_is_absent
from .results import register

register("B0", "Boundary", "Ward Code — Not Available on Data",
         "ward_code is null or empty on the uploaded data")
register("B1", "Boundary", "Ward Code — Boundary Reference",
         "ward_code must exist in the admin ward boundary reference for the file's state(s)")
register("B2", "Boundary", "Coordinates — Ward Boundary Intersection",
         "latitude/longitude must fall within the bounding box of the declared ward_code "
         "(ward_code of the intersecting boundary must equal the declared ward_code)")
register("B3", "Boundary", "State Name — Boundary Reference Match",
         "state_name in MLoS must match the state_name assigned to the ward_code in the boundary reference")
register("B4", "Boundary", "Boundary Reference Fallback",
         "reports whether B1 and B2 validated against the file's own state(s) or, on a "
         "fallback, against the full national reference because state-name filtering "
         "matched no ward (INTEG-04, D-16/D-17)")
register("B5", "Boundary", "Boundary Reference Unavailable",
         "reports when no boundary reference was found at all, so B1, B2, B3 and B4 could "
         "not run (INTEG-04, D-18)")


def run_ward_boundary_qc(mlos: pd.DataFrame, ref_df: pd.DataFrame, bbox_df: pd.DataFrame):
    checks, details = [], []
    total = len(mlos)

    if "ward_code" not in mlos.columns:
        checks.append({
            "Rule#": "B0", "QC Check": "Ward Code — Not Available on Data",
            "Description": "ward_code column is missing from the uploaded data — all boundary checks skipped",
            "Failing Rows": total, "Total Rows": total,
            "Fail %": "100.0%",
            "Status": "❌ FAIL",
        })
        return checks, pd.DataFrame()

    id_col = "ogc_fid" if "ogc_fid" in mlos.columns else mlos.columns[0]
    BASE   = [c for c in [id_col,"state_name","lga_name","ward_code","settlement_name"] if c in mlos.columns]

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

    # ── Filter boundary reference by state_name (case-insensitive).
    # state_name ("Nasarawa", "Kano", etc.) is a plain readable string shared
    # by both the MLoS data and the boundary reference — no format ambiguity.
    # This replaces state_code filtering which caused false positives because
    # "NA" (Nasarawa's code) is silently converted to NaN by pandas.
    filtered_ref  = ref_df.copy()  if not ref_df.empty  else ref_df
    filtered_bbox = bbox_df.copy() if not bbox_df.empty else bbox_df

    if (not ref_df.empty
            and "state_name" in mlos.columns
            and "state_name" in ref_df.columns):
        mlos_state_names = set(
            mlos["state_name"].dropna().astype(str).str.strip().str.lower()
        )
        ref_sn_norm  = ref_df["state_name"].astype(str).str.strip().str.lower()
        filtered_ref = filtered_ref[ref_sn_norm.isin(mlos_state_names)]

        if not filtered_ref.empty and not filtered_bbox.empty and "ward_code" in filtered_bbox.columns:
            state_ward_set = set(filtered_ref["ward_code"].dropna().astype(str).str.strip())
            filtered_bbox  = filtered_bbox[
                filtered_bbox["ward_code"].astype(str).str.strip().isin(state_ward_set)
            ]

    # B4 (INTEG-04, D-16/D-17): capture the fallback as a boolean, and the state-filtered
    # ward count, at this site — before the reassignment below destroys both. The trigger is
    # emptiness of the state-filtered result, not a size comparison against the national set.
    fallback_fired = filtered_ref.empty and not ref_df.empty
    pre_fallback_ward_count = (
        int(filtered_ref["ward_code"].dropna().astype(str).str.strip().nunique())
        if not filtered_ref.empty and "ward_code" in filtered_ref.columns
        else 0
    )

    # Fallback to full reference if state_name filtering yields nothing
    if filtered_ref.empty and not ref_df.empty:
        filtered_ref  = ref_df.copy()
        filtered_bbox = bbox_df.copy()

    # B0 — ward_code must not be null or empty in the uploaded data. Uses the shared D-04
    # absence predicate (vec_is_absent) rather than a hand-rolled null-or-empty disjunction,
    # so a sentinel ward_code (e.g. "n/a") fails B0 exactly as it fails Rule 1 and 4.missing
    # elsewhere (D-03's exactly-three-checks invariant).
    null_wc_mask = vec_is_absent(mlos["ward_code"])
    add("B0", "Ward Code — Not Available on Data",
        "ward_code is null or empty on the uploaded data",
        null_wc_mask, ["ward_code"])

    # B5 (INTEG-04, D-18): the reference is unavailable entirely. Emitted as an early return,
    # after B0 so the ward-code-on-data finding still reaches the officer, and before B1/B2/B3
    # so the emitted set is exactly the two checks D-18 specifies. Mirrors the early-return
    # precedent at the top of this function for a missing ward_code column.
    if ref_df.empty:
        checks.append({
            "Rule#": "B5", "QC Check": "Boundary Reference Unavailable",
            "Description": "No boundary reference was found — B1, B2, B3 and B4 could not run",
            "Failing Rows": 1, "Total Rows": 1,
            "Fail %": pct(1, 1),
            "Status": "❌ FAIL",
        })
        return checks, pd.DataFrame()

    # B1 — non-null ward_codes must exist in the state-name-filtered boundary reference
    if not filtered_ref.empty and "ward_code" in filtered_ref.columns:
        valid_wards   = set(filtered_ref["ward_code"].dropna().astype(str).str.strip())
        has_wc        = ~null_wc_mask   # only check rows that actually have a ward_code
        not_in_ref    = ~mlos["ward_code"].astype(str).str.strip().isin(valid_wards)
        add("B1", "Ward Code — Boundary Reference",
            "ward_code must exist in the admin ward boundary reference for the file's state(s)",
            has_wc & not_in_ref,
            ["ward_code"])

    # B3 — state_name in MLoS must match the state_name the boundary reference
    # assigns to the same ward_code (catches ward codes registered to a different state)
    if (not ref_df.empty
            and "ward_code" in ref_df.columns
            and "state_name" in ref_df.columns
            and "state_name" in mlos.columns
            and "ward_code" in mlos.columns):
        ref_sn_map = (
            ref_df[["ward_code", "state_name"]]
            .drop_duplicates("ward_code")
            .rename(columns={"state_name": "_ref_state_name"})
        )
        chk_sn = pd.DataFrame({
            "ward_code":  mlos["ward_code"].astype(str).str.strip().values,
            "_mlos_sn":   mlos["state_name"].astype(str).str.strip().str.lower().values,
        }, index=mlos.index)
        merged_sn = chk_sn.merge(ref_sn_map, on="ward_code", how="left")
        merged_sn.index = mlos.index
        merged_sn["_ref_sn_lower"] = merged_sn["_ref_state_name"].astype(str).str.strip().str.lower()
        # Only flag rows where the ward_code IS found in the reference but the state_name differs
        ward_found  = merged_sn["_ref_state_name"].notna()
        sn_mismatch = merged_sn["_mlos_sn"] != merged_sn["_ref_sn_lower"]
        mask_b3 = ward_found & sn_mismatch
        add("B3", "State Name — Boundary Reference Match",
            "state_name in MLoS must match the state_name assigned to the ward_code in the boundary reference",
            mask_b3, ["ward_code", "state_name"])

    # B2 — lat/lon must fall within the state-filtered bounding box
    if (not filtered_bbox.empty and "ward_code" in filtered_bbox.columns
            and "latitude" in mlos.columns and "longitude" in mlos.columns):
        chk = pd.DataFrame({
            "ward_code": mlos["ward_code"].astype(str).str.strip().values,
            "lat":       pd.to_numeric(mlos["latitude"],  errors="coerce").values,
            "lon":       pd.to_numeric(mlos["longitude"], errors="coerce").values,
        }, index=mlos.index)

        bbox_ref = filtered_bbox[["ward_code","min_lon","min_lat","max_lon","max_lat"]].copy()
        for col in ["min_lon","min_lat","max_lon","max_lat"]:
            bbox_ref[col] = pd.to_numeric(bbox_ref[col], errors="coerce")

        merged = chk.merge(bbox_ref, on="ward_code", how="left")
        merged.index = mlos.index

        has_coords   = merged["lat"].notna() & merged["lon"].notna() & (merged["lat"] != 0) & (merged["lon"] != 0)
        in_reference = merged["min_lon"].notna()
        out_of_box   = (
            (merged["lon"] < merged["min_lon"]) |
            (merged["lon"] > merged["max_lon"]) |
            (merged["lat"] < merged["min_lat"]) |
            (merged["lat"] > merged["max_lat"])
        )
        mask_b2 = has_coords & in_reference & out_of_box
        add("B2", "Coordinates — Ward Boundary Intersection",
            "latitude/longitude must fall within the bounding box of the declared ward_code "
            "(ward_code of the intersecting boundary must equal the declared ward_code)",
            mask_b2, ["ward_code","latitude","longitude"])

        # Enrich B2 detail with reverse-lookup: which ward bbox contains the failing coordinate
        if mask_b2.any() and details:
            _b2_detail = details[-1]
            _bbox_lkp = filtered_bbox[["ward_code","min_lon","min_lat","max_lon","max_lat"]].copy()
            for _c in ["min_lon","min_lat","max_lon","max_lat"]:
                _bbox_lkp[_c] = pd.to_numeric(_bbox_lkp[_c], errors="coerce")
            _bbox_lkp = _bbox_lkp.dropna()
            _matched = []
            for _idx in mask_b2[mask_b2].index:
                _lv = pd.to_numeric(mlos.at[_idx, "latitude"],  errors="coerce")
                _lnv = pd.to_numeric(mlos.at[_idx, "longitude"], errors="coerce")
                if pd.isna(_lv) or pd.isna(_lnv):
                    _matched.append("N/A")
                    continue
                _hits = _bbox_lkp[
                    (_bbox_lkp["min_lon"] <= _lnv) & (_lnv <= _bbox_lkp["max_lon"]) &
                    (_bbox_lkp["min_lat"] <= _lv)  & (_lv  <= _bbox_lkp["max_lat"])
                ]["ward_code"].astype(str).tolist()
                _matched.append(", ".join(_hits[:5]) if _hits else "No matching ward found")
            _b2_detail["Intersecting Ward(s) from Boundary"] = _matched

    # B4 (INTEG-04, D-16/D-17/D-19): guarded on the national reference being non-empty --
    # with no reference at all there is no scope for B4 to describe (B5 already returned
    # above in that case), so it emits nothing rather than something false. Hand-built rather
    # than routed through add(), because this is a run-level condition with a 1-over-1
    # denominator, not a row-level one (add() hard-codes Total Rows to the MLoS row count).
    if not ref_df.empty:
        b4_failing = 1 if fallback_fired else 0
        if fallback_fired:
            b4_status = "❌ FAIL"
            b4_desc = (
                "ward_code (B1) and coordinate (B2) checks ran against the full national "
                "boundary reference because state-name filtering matched no ward in the "
                "file's own state(s)"
            )
        else:
            b4_status = "✅ PASS"
            b4_desc = (
                f"validated against {pre_fallback_ward_count} ward(s) in the file's own "
                "state(s), no fallback to the national reference"
            )
        checks.append({
            "Rule#": "B4", "QC Check": "Boundary Reference Fallback",
            "Description": b4_desc,
            "Failing Rows": b4_failing, "Total Rows": 1,
            "Fail %": pct(b4_failing, 1),
            "Status": b4_status,
        })

    # D-11: keep the original mlos row position as the row identity distinct counting keys on
    # — never re-derive it from an id column. An id_col key (ogc_fid, else the first column)
    # was rejected: a CSV without ogc_fid may put a non-unique column first and undercount.
    # Mirrors qc/mlos.py's pd.concat(details), which already omits ignore_index.
    detail_df = pd.concat(details) if details else pd.DataFrame()
    return checks, detail_df
