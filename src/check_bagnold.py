# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Locate Namib Dune (Bagnold Dunes) in the Gale DTM: ortho + hillshade + slope with Curiosity positions."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, rasterio
from matplotlib.patches import Rectangle
from pyproj import CRS, Transformer
from rasterio.windows import from_bounds
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import hillshade, slope_deg

ROOT = Path(__file__).resolve().parents[1]
DTM = ROOT / "data/raw/mars/DTEEC_040770_1755_039280_1755_U01.IMG"
ORTHO = ROOT / "data/raw/mars/ESP_040770_1755_RED_C_01_ORTHO.JP2"
RES = 1.0117630165416
half = float(sys.argv[1]); dx = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0; dy = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
box = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0  # patch box size to draw at (dx, dy)
wp = {f["properties"]["sol"]: f["properties"] for f in json.loads((ROOT / "data/raw/reference/MSL_waypoints.json").read_text())["features"]}
with rasterio.open(DTM) as d:
    geo = CRS(d.crs).geodetic_crs
    tf = Transformer.from_crs(geo, d.crs, always_xy=True); inv = Transformer.from_crs(d.crs, geo, always_xy=True)
    ref = min((s for s in wp if s >= 1192), key=lambda s: s)
    cx, cy = tf.transform(wp[ref]["lon"], wp[ref]["lat"])
    b = (cx - half, cy - half, cx + half, cy + half)
    z = d.read(1, window=from_bounds(*b, d.transform), masked=True).filled(np.nan).astype(float)
with rasterio.open(ORTHO) as o:
    img = o.read(1, window=from_bounds(*b, o.transform)).astype(float)
img[img == 0] = np.nan
pts = [(s, *tf.transform(p["lon"], p["lat"])) for s, p in wp.items() if 1150 <= s <= 1240]
ext = [-half, half, -half, half]
fig, axs = plt.subplots(1, 3, figsize=(20, 7.2))
for ax, (im, t, cm) in zip(axs, [(img, "HiRISE ortho RED_C_01 (1 m)", "gray"), (hillshade(z, RES), "DTM hillshade", "gray"),
                                  (slope_deg(z, RES), "DTM slope (deg, 0-35)", "magma")]):
    lo, hi = (0, 35) if "slope" in t else np.nanpercentile(im, [1, 99])
    ax.imshow(im, cmap=cm, vmin=lo, vmax=hi, extent=ext)
    for s, x, y in pts:
        if abs(x - cx) < half and abs(y - cy) < half:
            c = "cyan" if 1192 <= s <= 1215 else "yellow"
            ax.plot(x - cx, y - cy, "o", ms=3, color=c, mfc="none")
            if s in (1162, 1170, 1192, 1196, 1215, 1230) or s % 20 == 0:
                ax.annotate(str(s), (x - cx, y - cy), color=c, fontsize=7, xytext=(3, 3), textcoords="offset points")
    if box:
        ax.add_patch(Rectangle((dx - box / 2, dy - box / 2), box, box, fill=False, ec="lime", lw=1.5))
    ax.set_xlim(-half, half); ax.set_ylim(-half, half); ax.set_title(t, fontsize=9); ax.set_xlabel(f"m east of sol {ref} position")
lon, lat = inv.transform(cx + dx, cy + dy)
fig.suptitle(f"Namib Dune area. Curiosity positions sols 1150-1240 (cyan = 1192-1215). Box centre: lat {lat:.6f}, lon {lon:.6f}", fontsize=10)
fig.tight_layout(); out = ROOT / f"results/check_bagnold_{int(half*2)}m.png"; fig.savefig(out, dpi=110)
print(out, "ref sol", ref, "box centre lat/lon", round(lat, 6), round(lon, 6))
