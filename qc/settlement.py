"""Settlement QC layer, relocated verbatim from app.py:459-553 (run_settlement_qc).

Registers SQ1, SQ2, SQ2b, SQ3 and SQ4 at import time — all five identifiers are frozen by D-04
and unchanged by this relocation. The numpy import used by SQ4's haversine distance calculation
stays local to the function body, exactly as it was in app.py: hoisting it to module level would
move the import cost from first call to package import time, which every test and every
``import qc`` would then pay — a behaviour change this phase's relocation-only scope forbids.
"""

import pandas as pd

from .predicates import pct
from .results import register

register("SQ1", "Settlement", "Duplicate Settlement Name in Ward",
         "settlement_name must not repeat within the same ward_code")
register("SQ2", "Settlement", "Latitude/Longitude — Not Null",
         "latitude and longitude must not be null or missing")
register("SQ2b", "Settlement", "Latitude/Longitude — Not Zero",
         "latitude and longitude must not be zero")
register("SQ3", "Settlement", "Stacked Coordinates",
         "no two settlements may share identical latitude/longitude coordinates")
register("SQ4", "Settlement", "Settlements Too Close (< 30 m)",
         "each settlement must be more than 30 metres from all other settlements")


def run_settlement_qc(mlos: pd.DataFrame):
    import numpy as np
    checks, details = [], []
    total  = len(mlos)
    id_col = "ogc_fid" if "ogc_fid" in mlos.columns else mlos.columns[0]
    BASE   = [c for c in [id_col,"state_name","lga_name","ward_code","settlement_name"]
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

    # SQ1 — settlement_name must be unique within each ward_code
    if "settlement_name" in mlos.columns and "ward_code" in mlos.columns:
        add("SQ1", "Duplicate Settlement Name in Ward",
            "settlement_name must not repeat within the same ward_code",
            mlos.duplicated(subset=["ward_code", "settlement_name"], keep=False),
            ["ward_code", "settlement_name"])

    # SQ2 — latitude and longitude must not be null
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce")
        lon = pd.to_numeric(mlos["longitude"], errors="coerce")
        add("SQ2", "Latitude/Longitude — Not Null",
            "latitude and longitude must not be null or missing",
            lat.isna() | lon.isna(),
            ["latitude", "longitude"])

    # SQ2b — latitude and longitude must not be zero (where non-null)
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce")
        lon = pd.to_numeric(mlos["longitude"], errors="coerce")
        has_value = lat.notna() & lon.notna()
        add("SQ2b", "Latitude/Longitude — Not Zero",
            "latitude and longitude must not be zero",
            has_value & ((lat == 0) | (lon == 0)),
            ["latitude", "longitude"])

    # SQ3 — no two settlements may share identical coordinates (stacked)
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce")
        lon = pd.to_numeric(mlos["longitude"], errors="coerce")
        valid = lat.notna() & lon.notna() & (lat != 0) & (lon != 0)
        coord_df   = pd.DataFrame({"_lat": lat, "_lon": lon})
        stacked    = coord_df[valid].duplicated(keep=False)
        mask_sq3   = pd.Series(False, index=mlos.index)
        mask_sq3[stacked[stacked].index] = True
        add("SQ3", "Stacked Coordinates",
            "no two settlements may share identical latitude/longitude coordinates",
            mask_sq3, ["latitude", "longitude"])

    # SQ4 — every settlement must be > 30 m from every other settlement
    if "latitude" in mlos.columns and "longitude" in mlos.columns:
        lat = pd.to_numeric(mlos["latitude"],  errors="coerce")
        lon = pd.to_numeric(mlos["longitude"], errors="coerce")
        valid     = lat.notna() & lon.notna() & (lat != 0) & (lon != 0)
        valid_idx = mlos.index[valid]
        mask_sq4  = pd.Series(False, index=mlos.index)

        if len(valid_idx) > 1:
            R      = 6371000.0           # Earth radius in metres
            lats_r = np.radians(lat[valid].values)
            lons_r = np.radians(lon[valid].values)
            n      = len(lats_r)
            too_close = set()

            for i in range(n - 1):
                dlat = lats_r[i] - lats_r[i + 1:]
                dlon = lons_r[i] - lons_r[i + 1:]
                a    = (np.sin(dlat / 2) ** 2 +
                        np.cos(lats_r[i]) * np.cos(lats_r[i + 1:]) *
                        np.sin(dlon / 2) ** 2)
                d    = 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
                close_j = np.where(d < 30)[0]
                if len(close_j):
                    too_close.add(i)
                    too_close.update(int(i + 1 + j) for j in close_j)

            for k in too_close:
                mask_sq4[valid_idx[k]] = True

        add("SQ4", "Settlements Too Close (< 30 m)",
            "each settlement must be more than 30 metres from all other settlements",
            mask_sq4, ["ward_code", "settlement_name", "latitude", "longitude"])

    return checks, pd.concat(details) if details else pd.DataFrame()
