"""Build ward_boundary_ref.csv from the ward_boundary_sept SpatiaLite table.

state_code is carried over from the existing ward_boundary_ref.csv by state_name.
Wards of every status are kept; for duplicate ward codes the non-Invalid row wins.

Usage:
    python scripts/build_ward_ref.py ward_boundary_sept.sqlite .
"""
import sqlite3, sys
import pandas as pd

src, repo = sys.argv[1], sys.argv[2]
old = pd.read_csv(f"{repo}/ward_boundary_ref.csv", dtype=str, keep_default_na=False)
state_codes = old.groupby("state_name").state_code.first().to_dict()

con = sqlite3.connect(src)
rows = con.execute("select wardcode, wardname, lgacode, lga_name, state_name, status from ward_boundary_sept").fetchall()

recs = []
for wc, wn, lc, ln, sn, status in rows:
    sn = sn.strip()
    if sn == "Cross Rive":
        sn = "Cross River"
    recs.append(dict(state_code=state_codes[sn], state_name=sn, lga_code=lc.strip(), lga_name=ln.strip(),
                     ward_code=wc.strip(), ward_name=wn.strip(), status=status))
df = pd.DataFrame(recs)

# Duplicate codes: keep the non-Invalid row's metadata
df["_inv"] = df.status.eq("Invalid")
ref = (df.sort_values(["ward_code", "_inv"]).drop_duplicates("ward_code")
         [["state_code","state_name","lga_code","lga_name","ward_code","ward_name"]]
         .sort_values(["state_name","lga_name","ward_code"]))
ref.to_csv(f"{repo}/ward_boundary_ref.csv", index=False)
print(len(rows), "source rows ->", len(ref), "wards")
