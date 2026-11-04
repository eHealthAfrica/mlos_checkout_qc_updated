"""Rasterise GRID3 settlement extents (EPSG:3857) into a 25 m type mask.

Cell values: 0 none, 1 Hamlet, 2 Small Settlement Area, 3 Built-up Area.
Output: tiled, zlib-compressed npz with only non-empty tiles kept.

Usage (build-time only; needs rasterio and pyogrio, which the app does not):
    pip install rasterio pyogrio numpy
    python scripts/build_extent_mask.py settlement_extent.gpkg settlement_extent_mask.npz
"""
import sys, time, zlib
import numpy as np, pyogrio
from rasterio import features
from rasterio.transform import from_origin

SRC, OUT = sys.argv[1], sys.argv[2]
LAYER = "main_grid3_nga_settlement_extents_v4_1"
RES, TILE = 25.0, 256
X0, Y1 = 298600.0, 1561050.0
W = int(np.ceil((1633720.0 - X0) / RES / TILE)) * TILE
H = int(np.ceil((Y1 - 476300.0) / RES / TILE)) * TILE
tf = from_origin(X0, Y1, RES, RES)
grid = np.zeros((H, W), dtype=np.uint8)
print("grid", H, W, flush=True)

CHUNK = 200_000
for val, etype in [(1, "Hamlet"), (2, "Small Settlement Area"), (3, "Built-up Area")]:
    off = 0
    while True:
        t = time.time()
        gdf = pyogrio.read_dataframe(SRC, layer=LAYER, columns=[], where=f"extent_type = '{etype}'",
                                     skip_features=off, max_features=CHUNK)
        if gdf.empty:
            break
        features.rasterize(((g, val) for g in gdf.geometry.values if g is not None),
                           out=grid, transform=tf, all_touched=True)
        off += len(gdf)
        print(etype, off, round(time.time() - t, 1), flush=True)

ty, tx = H // TILE, W // TILE
keys, blobs = [], []
for r in range(ty):
    for c in range(tx):
        tile = grid[r*TILE:(r+1)*TILE, c*TILE:(c+1)*TILE]
        if tile.any():
            packed = (tile[:, 0::4] | (tile[:, 1::4] << 2) | (tile[:, 2::4] << 4) | (tile[:, 3::4] << 6))
            keys.append(r * tx + c)
            blobs.append(zlib.compress(packed.tobytes(), 9))
lens = np.array([len(b) for b in blobs], dtype=np.int64)
np.savez(OUT, meta=np.array([X0, Y1, RES, TILE, tx, ty]), keys=np.array(keys, dtype=np.int32),
         offsets=np.concatenate([[0], np.cumsum(lens)]), data=np.frombuffer(b"".join(blobs), dtype=np.uint8))
print("tiles", len(keys), "of", tx * ty, "bytes", int(lens.sum()))
print("cells by type", np.bincount(grid.ravel(), minlength=4))
