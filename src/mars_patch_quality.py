# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Score 256 m boxes in the Gale DTM for (a) dune-sand cover from the ortho and (b) DTM interpolation facets.

sand  = ortho DN below the 30th percentile AND local (5 px) DN std below the median (dark, smooth texture)
facet = pixel whose 5x5 neighbourhood fits a plane with RMS residual < 5 mm (TIN-interpolated
        surfaces are piecewise planar; float32 quantisation at -4400 m is ~0.5 mm)
"""
import json, sys
from pathlib import Path
import numpy as np, rasterio
from pyproj import CRS, Transformer
from scipy.ndimage import uniform_filter

ROOT = Path(__file__).resolve().parents[1]
R = 1.0117630165416
K = int(round(256 / R))


def plane_rms5(z):
    """RMS residual of a least-squares plane in each 5x5 window (closed form via moments)."""
    zz = np.nan_to_num(z)
    n = 25.0
    yy, xx = np.mgrid[0:z.shape[0], 0:z.shape[1]].astype(float)
    m = lambda a: uniform_filter(a, 5) * n
    sz, szz = m(zz), m(zz * zz)
    # local coordinates: within a 5x5 window, x and y offsets are -2..2 (sum 0, sum sq 50)
    sxz = m(zz * xx) - xx * sz
    syz = m(zz * yy) - yy * sz
    ss = szz - sz * sz / n - sxz ** 2 / 50.0 - syz ** 2 / 50.0
    return np.sqrt(np.maximum(ss, 0) / n)


def main():
    with rasterio.open(ROOT / "data/raw/mars/ESP_040770_1755_RED_C_01_ORTHO.JP2") as o:
        im = o.read(1).astype(float); T = o.transform; crs = o.crs
    with rasterio.open(ROOT / "data/raw/mars/DTEEC_040770_1755_039280_1755_U01.IMG") as d:
        z = d.read(1, masked=True).filled(np.nan).astype(np.float64)
    valid = (im > 0) & np.isfinite(z)
    mu = uniform_filter(im, 5); sd = np.sqrt(np.maximum(uniform_filter(im * im, 5) - mu * mu, 0))
    sand = valid & (im < np.percentile(im[valid], 30)) & (sd < np.percentile(sd[valid], 50))
    facet = valid & (plane_rms5(z) < 0.005)
    vf = uniform_filter(valid.astype(float), K)
    fs = uniform_filter(sand.astype(float), K); ff = uniform_filter(facet.astype(float), K)
    g = CRS(crs).geodetic_crs; inv = Transformer.from_crs(crs, g, always_xy=True); tf = Transformer.from_crs(g, crs, always_xy=True)

    def at(lat, lon):
        x, y = tf.transform(lon, lat); c, r = ~T * (x, y); r, c = int(r), int(c)
        return {"sand_frac": round(float(fs[r, c]), 3), "facet_frac": round(float(ff[r, c]), 3), "valid": round(float(vf[r, c]), 3)}

    named = {k: (v["lat"], v["lon"]) for k, v in json.loads((ROOT / "data/processed/meta/gate1_patches.json").read_text())["patches"].items() if v["source"] == "mars"}
    named["namib_box_try1"] = (-4.682777, 137.366054)
    named["allsand_box_try2"] = (-4.704709, 137.372299)
    report = {"rule": __doc__.strip(), "named": {k: at(*v) for k, v in named.items()}}
    # best boxes: sand >= 0.9, full validity, lowest facet fraction (sample every 32 px)
    cand = []
    for r in range(K // 2, im.shape[0] - K // 2, 32):
        for c in range(K // 2, im.shape[1] - K // 2, 32):
            if vf[r, c] > 0.999 and fs[r, c] >= 0.9:
                cand.append((float(ff[r, c]), float(fs[r, c]), r, c))
    cand.sort()
    picked = []
    for f_, s_, r, c in cand:
        if all(abs(r - pr) > K or abs(c - pc) > K for _, _, pr, pc in picked):
            picked.append((f_, s_, r, c))
        if len(picked) == 8:
            break
    report["best_sand_boxes"] = []
    for f_, s_, r, c in picked:
        x, y = T * (c + 0.5, r + 0.5); lon, lat = inv.transform(x, y)
        report["best_sand_boxes"].append({"lat": round(lat, 6), "lon": round(lon, 6), "sand_frac": round(s_, 3), "facet_frac": round(f_, 3)})
    out = ROOT / "data/processed/meta/mars_patch_quality.json"; out.write_text(json.dumps(report, indent=2)); print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
