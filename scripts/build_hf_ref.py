"""Build health_facility_ref.csv.gz from the health_facilities table, used by MLoS Rule 2.

Facilities without a ward_code or primary_name are dropped.

Usage:
    python scripts/build_hf_ref.py health_facilities.sqlite health_facility_ref.csv.gz
"""
import sqlite3, sys
import pandas as pd
src, out = sys.argv[1], sys.argv[2]
hf = pd.read_sql("select ward_code, primary_name, alternate_name, globalid from health_facilities",
                 sqlite3.connect(src)).fillna("")
for c in hf.columns:
    hf[c] = hf[c].astype(str).str.strip()
hf = hf[(hf.ward_code != "") & (hf.primary_name != "")].sort_values(["ward_code", "primary_name"])
hf.to_csv(out, index=False, compression="gzip")
print(len(hf), "facilities,", hf.ward_code.nunique(), "wards")
