# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Gate 3 Task 1: register the Moon patch grid (rule + list) BEFORE reading any LOLA heights.

Zone: 'south-polar Artemis candidate zone' = 84-90 S. No authoritative coordinates for the 2024 Artemis III
candidate regions were found (NASA release names regions only), so the whole band is sampled.
Grid: square grid in the LDEM_80S_20M polar-stereographic plane (sphere R = 1737.4 km, true scale at pole),
spacing 27 km, origin shifted by one random offset in [-13.5, 13.5) km per axis (numpy default_rng(20261114)).
A grid point is kept if its centre lies at or poleward of 84 S. Patch = 1.92 km square (64 x 64 px at 30 m),
area-averaged from the 20 m LOLA grid. Patches with any nodata are skipped (decided after reading heights).
"""
import datetime as dt, json, math, sys
from pathlib import Path
import numpy as np, rasterio
from pyproj import CRS, Transformer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate3_common import ROOT, SEED

LBL = ROOT / "data/raw/moon/ldem_80s_20m.lbl"
SPACING = 27_000.0
R = 1737400.0
rho84 = 2 * R * math.tan(math.radians(90 - 84) / 2)
with rasterio.open(LBL) as d:
    crs = d.crs
inv = Transformer.from_crs(crs, CRS(crs).geodetic_crs, always_xy=True)
off = np.random.default_rng(SEED).uniform(-SPACING / 2, SPACING / 2, 2)
n = int(math.ceil(rho84 / SPACING)) + 1
pts = []
for j in range(-n, n + 1):
    for i in range(-n, n + 1):
        x, y = i * SPACING + off[0], j * SPACING + off[1]
        if math.hypot(x, y) <= rho84:
            lon, lat = inv.transform(x, y)
            pts.append({"patch_id": f"m{len(pts):03d}", "x_m": round(x, 1), "y_m": round(y, 1), "lat": round(lat, 5), "lon": round(lon, 5)})
doc = {"registered_at": dt.datetime.now().isoformat(timespec="seconds"), "rule": __doc__.strip(), "seed": SEED,
       "grid_offset_m": [round(float(o), 1) for o in off], "rho_84S_m": round(rho84, 1), "crs_wkt": crs.to_wkt(),
       "n_grid_points": len(pts), "patches": pts}
(ROOT / "results/moon_patches.json").write_text(json.dumps(doc, indent=2))
print(len(pts), "grid points; rho84 = %.1f km" % (rho84 / 1000), "lat range", min(p["lat"] for p in pts), max(p["lat"] for p in pts))
