# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Gate 2 step 1: build and pre-register the Earth candidate set (no fingerprints, no ranking here).

Rule: 8 x 8 regular grid, 10 km spacing, over an 80 x 80 km square in NAD83 / UTM 11N centred midway
between Dumont Dunes and the Avawatz Mts. The whole grid is shifted by one random offset in
[-5, 5) km per axis (seed below) so the grid does not depend on hand-picked origins. Each grid point
is the centre of a 256 m patch read from USGS 3DEP 1 m and area-averaged to 2 m. Patches with < 95 %
valid data are skipped. Dumont (GNIS centre) and Avawatz (negative control) are added explicitly;
nothing else is added or removed by hand.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
import requests
from pyproj import Transformer
from rasterio.merge import merge
from rasterio.warp import transform_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import to_common_grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/processed/candidates"
CRS_UTM = "EPSG:26911"
SEED = 20261114
SPACING_M = 10_000
N_GRID = 8
PATCH_M = 256.0
GRID_M = 2.0
MIN_VALID = 0.95
DUMONT = (35.67863, -116.23156)
AVAWATZ = (35.5069188, -116.2847431)
TNM = "https://tnmaccess.nationalmap.gov/api/v1/products"
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2",
           GDAL_HTTP_TIMEOUT="45", GDAL_HTTP_LOW_SPEED_TIME="30", GDAL_HTTP_LOW_SPEED_LIMIT="1000")
to_utm = Transformer.from_crs("EPSG:4326", CRS_UTM, always_xy=True)
to_ll = Transformer.from_crs(CRS_UTM, "EPSG:4326", always_xy=True)

PREREG = {
    "success_criterion": "Dumont ranks in the top 10% of the Earth candidate set by distance to mars_sand "
                         "under the primary metric (rank <= ceil(0.10 * N_candidates); for N ~ 60 that is top 6).",
    "primary_metric": "Method A: z-score each fingerprint feature across the Earth candidate set (mean/std of candidates), "
                      "apply the same transform to mars_sand, Euclidean distance.",
    "secondary_metrics": ["Method A: mean over features of |a-b|/(|a|+|b|) (Gate 1 metric)",
                          "Method B: cosine distance between DINOv2-small embeddings of hillshades"],
    "features": "slope median/P90/IQR (deg) at scales 2,4,8,16,32,64 m + roughness median (m) at 4,8,16,32,64 m = 23 features",
    "registered_at": None,
}


def tiles_for(box):
    ll = transform_bounds(CRS_UTM, "EPSG:4326", *box)
    r = requests.get(TNM, params={"datasets": "Digital Elevation Model (DEM) 1 meter",
                                  "bbox": ",".join(f"{v:.6f}" for v in ll), "outputFormat": "JSON", "max": 50}, timeout=120)
    r.raise_for_status()
    best = {}
    for it in r.json().get("items", []):
        key = it["title"].split(" ")[4]
        if key not in best or it.get("publicationDate", "") > best[key].get("publicationDate", ""):
            best[key] = it
    return list(best.values())


def read_patch(x, y):
    m = 8.0
    box = (round(x - PATCH_M / 2 - m), round(y - PATCH_M / 2 - m), round(x + PATCH_M / 2 + m), round(y + PATCH_M / 2 + m))
    tiles = tiles_for(box)
    if not tiles:
        return None, [], 0.0
    with rasterio.Env(**ENV):
        srcs = [rasterio.open("/vsicurl/" + t["downloadURL"]) for t in tiles]
        srcs = [s for s in srcs if s.crs.to_string() == CRS_UTM]
        if not srcs:
            return None, [t["title"] for t in tiles], 0.0
        nod = srcs[0].nodata
        arr, tr = merge(srcs, bounds=box, res=1.0, nodata=nod)
        for s in srcs:
            s.close()
    g, gtr = to_common_grid(arr[0], tr, CRS_UTM, nod, GRID_M)
    c, r = ~gtr * (x, y)
    k = int(PATCH_M / GRID_M)
    r0, c0 = int(round(r - k / 2)), int(round(c - k / 2))
    p = g[r0:r0 + k, c0:c0 + k]
    return p, sorted(t["title"] for t in tiles), float(np.isfinite(p).mean())


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    dx, dy = to_utm.transform(DUMONT[1], DUMONT[0])
    ax, ay = to_utm.transform(AVAWATZ[1], AVAWATZ[0])
    cx, cy = (dx + ax) / 2, (dy + ay) / 2
    off = rng.uniform(-SPACING_M / 2, SPACING_M / 2, size=2)
    xs = cx - SPACING_M * (N_GRID - 1) / 2 + off[0] + SPACING_M * np.arange(N_GRID)
    ys = cy - SPACING_M * (N_GRID - 1) / 2 + off[1] + SPACING_M * np.arange(N_GRID)
    pts = [(f"grid_r{j}_c{i}", float(x), float(y)) for j, y in enumerate(ys[::-1]) for i, x in enumerate(xs)]
    pts += [("dumont", dx, dy), ("avawatz_negctrl", ax, ay)]
    half = SPACING_M * N_GRID / 2
    area_ll = transform_bounds(CRS_UTM, "EPSG:4326", cx - half, cy - half, cx + half, cy + half)

    doc = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "rule": __doc__.strip(), "seed": SEED,
           "grid_offset_m": [round(float(o), 1) for o in off], "area_utm11n": [round(cx - half), round(cy - half), round(cx + half), round(cy + half)],
           "area_lonlat": [round(v, 5) for v in area_ll], "patch_m": PATCH_M, "grid_m": GRID_M, "min_valid": MIN_VALID,
           "preregistration": dict(PREREG, registered_at=dt.datetime.now().isoformat(timespec="seconds")),
           "candidates": [], "skipped": []}
    def work(item):
        name, x, y = item
        lon, lat = to_ll.transform(x, y)
        try:
            p, tiles, v = read_patch(x, y)
        except Exception as e:  # network/IO failure is recorded, never silently dropped
            return name, None, {"name": name, "lat": round(lat, 6), "lon": round(lon, 6), "reason": f"error: {type(e).__name__}: {e}"[:200]}
        rec = {"name": name, "lat": round(lat, 6), "lon": round(lon, 6), "utm_x": round(x, 1), "utm_y": round(y, 1),
               "valid_fraction": round(v, 4), "tiles": tiles}
        if p is None or v < MIN_VALID:
            rec["reason"] = "no 3DEP 1 m tile" if p is None else f"valid {v:.3f} < {MIN_VALID}"
            return name, None, rec
        np.save(OUT_DIR / f"{name}.npy", p.astype(np.float32))
        rec["file"] = str((OUT_DIR / f"{name}.npy").relative_to(ROOT))
        return name, rec, None

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(work, pts))
    for name, ok, bad in results:  # keep grid order
        if ok:
            doc["candidates"].append(ok)
        else:
            doc["skipped"].append(bad); print("skip", name, bad["reason"])
    doc["n_candidates"] = len(doc["candidates"])
    (ROOT / "results/candidates.json").write_text(json.dumps(doc, indent=2))
    print("candidates:", doc["n_candidates"], "skipped:", len(doc["skipped"]))


if __name__ == "__main__":
    main()
