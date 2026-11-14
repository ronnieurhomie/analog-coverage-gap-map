# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Visual check: HiRISE ortho + DTM hillshade around Hidden Valley with Curiosity's path and patch boxes."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, rasterio
from matplotlib.patches import Rectangle
from pyproj import CRS, Transformer
from rasterio.windows import from_bounds
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import hillshade

ROOT = Path(__file__).resolve().parents[1]
DTM = ROOT / "data/raw/mars/DTEEC_040770_1755_039280_1755_U01.IMG"
ORTHO = ROOT / "data/raw/mars/ESP_040770_1755_RED_C_01_ORTHO.JP2"
WP = ROOT / "data/raw/reference/MSL_waypoints.json"
spec = json.loads((ROOT / "data/processed/meta/gate1_patches.json").read_text())["patches"]
half = float(sys.argv[1]) if len(sys.argv) > 1 else 500.0
sols = (600, 780)

with rasterio.open(DTM) as d:
    tf = Transformer.from_crs(CRS(d.crs).geodetic_crs, d.crs, always_xy=True)
    cx, cy = tf.transform(spec["mars_sand"]["lon"], spec["mars_sand"]["lat"])
    bounds = (cx - half, cy - half, cx + half, cy + half)
    z = d.read(1, window=from_bounds(*bounds, d.transform), masked=True).filled(np.nan).astype(float)
with rasterio.open(ORTHO) as o:
    img = o.read(1, window=from_bounds(*bounds, o.transform)).astype(float)
img[img == 0] = np.nan
pts = []
for f in json.loads(WP.read_text())["features"]:
    p = f["properties"]
    if sols[0] <= p["sol"] <= sols[1]:
        pts.append((p["sol"], *tf.transform(p["lon"], p["lat"])))
pts = np.array(pts)
ext = [-half, half, -half, half]
fig, axs = plt.subplots(1, 2, figsize=(14, 7.2))
for ax, (im, cm, title) in zip(axs, [(img, "gray", "HiRISE ortho ESP_040770_1755_RED_C_01 (DTM grid)"),
                                      (hillshade(z, 1.0117630165416), "gray", "DTM hillshade (az 315, alt 30)")]):
    lo, hi = np.nanpercentile(im, [1, 99])
    ax.imshow(im, cmap=cm, vmin=lo, vmax=hi, extent=ext)
    ax.plot(pts[:, 1] - cx, pts[:, 2] - cy, "-", color="cyan", lw=1)
    for s, x, y in pts:
        col = "red" if 705 <= s <= 713 else "yellow"
        ax.plot(x - cx, y - cy, "o", ms=3, color=col)
        if int(s) % 10 == 0 or s in (665, 705, 713):
            ax.annotate(str(int(s)), (x - cx, y - cy), color=col, fontsize=7, xytext=(3, 3), textcoords="offset points")
    for name, c in [("mars_sand", "red"), ("mars_nominal", "lime")]:
        px, py = tf.transform(spec[name]["lon"], spec[name]["lat"])
        ax.add_patch(Rectangle((px - cx - 128, py - cy - 128), 256, 256, fill=False, ec=c, lw=1.5))
    ax.set_title(title, fontsize=9); ax.set_xlabel("m east of patch centre")
axs[0].set_ylabel("m north of patch centre")
fig.suptitle(f"Curiosity end-of-drive positions sols {sols[0]}-{sols[1]} (red = 705-713); red box = Mars sand patch, green = nominal", fontsize=10)
fig.tight_layout(); out = ROOT / f"results/check_hidden_valley_{int(half*2)}m.png"; fig.savefig(out, dpi=130); print(out)
