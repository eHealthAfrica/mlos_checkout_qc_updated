"""Build ward_boundary_geom.csv.gz (ward_code + WKB hex, EPSG:4326) for the B2 spatial join.

Empty geometries are dropped, invalid ones repaired with make_valid, and
duplicate ward codes dissolved into one polygon.

Usage (build-time only; needs geopandas):
    python scripts/build_ward_geom.py ward_boundary_sept.sqlite ward_boundary_geom.csv.gz
"""
import sys
import geopandas as gpd, pandas as pd, shapely

src, out = sys.argv[1], sys.argv[2]
g = gpd.read_file(src, layer="ward_boundary_sept")
print(len(g), g.crs, g.geometry.geom_type.value_counts().to_dict())
g["ward_code"] = g["wardcode"].str.strip()
g = g[~g.geometry.isna() & ~g.geometry.is_empty]
print("non-empty", len(g), "invalid", (~g.geometry.is_valid).sum())
g["geometry"] = shapely.make_valid(g.geometry.values)
d = g.dissolve("ward_code").reset_index()[["ward_code", "geometry"]]
d["wkb"] = shapely.to_wkb(d.geometry.values, hex=True)
d[["ward_code", "wkb"]].to_csv(out, index=False, compression="gzip")
print(len(d), "wards written")
