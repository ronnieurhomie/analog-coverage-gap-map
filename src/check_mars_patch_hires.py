# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Zoomed check of the Hidden Valley patch on the 1 m HiRISE ortho on the DTM grid."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, rasterio
from matplotlib.patches import Rectangle
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import hillshade

ROOT = Path(__file__).resolve().parents[1]
URL = str(ROOT / "data/raw/mars/ESP_040770_1755_RED_C_01_ORTHO.JP2")  # 1 m ortho on the DTM grid
DTM = ROOT / "data/raw/mars/DTEEC_040770_1755_039280_1755_U01.IMG"
spec = json.loads((ROOT / "data/processed/meta/gate1_patches.json").read_text())["patches"]
half = float(sys.argv[1]) if len(sys.argv) > 1 else 160.0
NAME = sys.argv[2] if len(sys.argv) > 2 else "mars_sand"
SOLS = (690, 730) if NAME == "mars_sand" else (655, 675)
with rasterio.open(DTM) as d:
    tf = Transformer.from_crs(CRS(d.crs).geodetic_crs, d.crs, always_xy=True)
    cx, cy = tf.transform(spec[NAME]["lon"], spec[NAME]["lat"])
    b = (cx - half, cy - half, cx + half, cy + half)
    z = d.read(1, window=from_bounds(*b, d.transform), masked=True).filled(np.nan).astype(float)
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(URL) as o:
    w = from_bounds(*b, o.transform)
    n = int(2 * half / 1.0117630165416)
    img = o.read(1, window=w, out_shape=(n, n), resampling=Resampling.average).astype(float)
img[img == 0] = np.nan
pts = []
for f in json.loads((ROOT / "data/raw/reference/MSL_waypoints.json").read_text())["features"]:
    p = f["properties"]
    if SOLS[0] <= p["sol"] <= SOLS[1]:
        x, y = tf.transform(p["lon"], p["lat"]); pts.append((p["sol"], x - cx, y - cy))
ext = [-half, half, -half, half]
fig, axs = plt.subplots(1, 2, figsize=(14, 7.4))
for ax, im, t in [(axs[0], img, "HiRISE ESP_040770_1755_RED_C_01 ortho (1 m, DTM grid)"),
                  (axs[1], hillshade(z, 1.0117630165416), "DTM hillshade 1 m (az 315, alt 30)")]:
    lo, hi = np.nanpercentile(im, [1, 99]); ax.imshow(im, cmap="gray", vmin=lo, vmax=hi, extent=ext)
    for s, x, y in pts:
        c = "red" if 705 <= s <= 713 else "yellow"
        ax.plot(x, y, "o", ms=4, color=c, mfc="none")
        ax.annotate(str(int(s)), (x, y), color=c, fontsize=7, xytext=(4, 2), textcoords="offset points")
    ax.add_patch(Rectangle((-128, -128), 256, 256, fill=False, ec="red", lw=1.5))
    ax.set_xlim(-half, half); ax.set_ylim(-half, half); ax.set_title(t, fontsize=9); ax.set_xlabel("m east")
axs[0].set_ylabel("m north")
fig.suptitle(f"{NAME} check: rover end-of-drive positions sols {SOLS[0]}-{SOLS[1]} (red = 705-713); red box = 256 m patch", fontsize=10)
fig.tight_layout(); out = ROOT / f"results/check_{NAME}_zoom.png"; fig.savefig(out, dpi=130); print(out)
