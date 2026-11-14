# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Gate 2b item 2: slope stats on Bagnold boxes using only sand, non-facet pixels; Dumont for comparison.

Masks (1 m DTM grid, same rules as src/mars_patch_quality.py):
  sand  = ortho DN < 30th percentile (whole ortho) AND 5 px local DN std < median (whole ortho)
  facet = 5x5 plane-fit RMS < 5 mm
  usable = sand AND NOT facet AND valid DTM
Procedure per box (256 m): DTM and usable-mask are area-averaged to the 2 m grid. A 2 m cell is used
if >= 75 % of it is usable. Slope at 2 m = central differences on the 2 m grid (a cell is used only if it
and its 4 neighbours are used). Slope at 16 m = 8x8 block mean of the 2 m grid (block used if >= 75 %
of its 2 m cells are used), central differences on that grid, same neighbour rule.
Dumont: every valid pixel used (lidar; no facet/sand masking applied), same slope procedure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import _block_mean, slope_deg, to_common_grid  # noqa: E402
from mars_patch_quality import plane_rms5  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DTM = ROOT / "data/raw/mars/DTEEC_040770_1755_039280_1755_U01.IMG"
ORTHO = ROOT / "data/raw/mars/ESP_040770_1755_RED_C_01_ORTHO.JP2"
MASKS = ROOT / "data/processed/mars_masks_1m.npz"
THR = 0.75
BOXES = {  # name: (lat, lon, origin)
    "mars_sand": (-4.682895, 137.366378, "Gate 2 mars_sand (Namib Dune area)"),
    "allsand_1": (-4.675094, 137.408008, "Gate 2 all-sand search #1"),
    "allsand_2": (-4.704709, 137.372299, "Gate 2 all-sand search #2"),
    "allsand_3": (-4.693939, 137.392612, "Gate 2 all-sand search #3"),
    "allsand_4": (-4.655038, 137.423046, "Gate 2 all-sand search #4"),
    "allsand_5": (-4.663675, 137.419410, "Gate 2 all-sand search #5"),
    "allsand_6": (-4.679259, 137.396537, "Gate 2 all-sand search #6"),
}


def build_masks():
    if MASKS.exists():
        m = np.load(MASKS)
        return m["usable"].astype(bool), m["sand"].astype(bool), m["facet"].astype(bool)
    with rasterio.open(ORTHO) as o:
        im = o.read(1).astype(float)
    with rasterio.open(DTM) as d:
        z = d.read(1, masked=True).filled(np.nan).astype(np.float64)
    valid = (im > 0) & np.isfinite(z)
    mu = uniform_filter(im, 5); sd = np.sqrt(np.maximum(uniform_filter(im * im, 5) - mu * mu, 0))
    sand = valid & (im < np.percentile(im[valid], 30)) & (sd < np.percentile(sd[valid], 50))
    facet = valid & (plane_rms5(z) < 0.005)
    usable = sand & ~facet
    np.savez_compressed(MASKS, usable=usable, sand=sand, facet=facet)
    return usable, sand, facet


def masked_slopes(z2: np.ndarray, use2: np.ndarray) -> dict:
    out = {}
    for s, k in [(2, 1), (16, 8)]:
        if k == 1:
            g, u = z2, use2
        else:
            g = _block_mean(z2, k)
            u = _block_mean(use2.astype(float), k) >= THR
        sl = slope_deg(g, 2.0 * k)
        nb = u.copy()
        nb[1:, :] &= u[:-1, :]; nb[:-1, :] &= u[1:, :]; nb[:, 1:] &= u[:, :-1]; nb[:, :-1] &= u[:, 1:]
        nb[0, :] = nb[-1, :] = False; nb[:, 0] = nb[:, -1] = False
        v = sl[nb & np.isfinite(sl)]
        out[f"{s}m"] = {"n_cells_used": int(v.size), "cells_total": int(sl.size),
                        "median_deg": float(np.median(v)) if v.size else None,
                        "p90_deg": float(np.percentile(v, 90)) if v.size else None}
    return out


def main():
    usable, sand, facet = build_masks()
    res = {"rule": __doc__.strip(), "boxes": {}}
    with rasterio.open(DTM) as d:
        tf = Transformer.from_crs(CRS(d.crs).geodetic_crs, d.crs, always_xy=True)
        res_m = abs(d.transform.a)
        for name, (lat, lon, origin) in BOXES.items():
            x, y = tf.transform(lon, lat)
            n = int(np.ceil(272 / res_m)); c0, r0 = ~d.transform * (x - 136, y + 136)
            w = Window(int(c0), int(r0), n, n)
            z = d.read(1, window=w); tr = d.window_transform(w)
            sl = (slice(w.row_off, w.row_off + n), slice(w.col_off, w.col_off + n))
            z2, gtr = to_common_grid(z, tr, d.crs, d.nodata, 2.0)
            u2, _ = to_common_grid(usable[sl].astype(np.float32), tr, d.crs, None, 2.0)
            cc, rr = ~gtr * (x, y); k = 128; r_, c_ = int(round(rr - 64)), int(round(cc - 64))
            z2 = z2[r_:r_ + k, c_:c_ + k]; u2 = u2[r_:r_ + k, c_:c_ + k] >= THR
            # 1 m fractions inside the exact 256 m box
            b = int(round(128 / res_m)); rc, cc1 = int(round(n / 2)), int(round(n / 2))
            box1 = (slice(w.row_off + rc - b, w.row_off + rc + b), slice(w.col_off + cc1 - b, w.col_off + cc1 + b))
            res["boxes"][name] = {"lat": lat, "lon": lon, "origin": origin,
                                  "sand_frac_1m": round(float(sand[box1].mean()), 3),
                                  "facet_frac_1m": round(float(facet[box1].mean()), 3),
                                  "usable_frac_1m": round(float(usable[box1].mean()), 3),
                                  "usable_frac_2m_cells": round(float(u2.mean()), 3),
                                  "slopes": masked_slopes(z2.astype(float), u2)}
    # Dumont (all valid pixels)
    dp = np.load(ROOT / "data/processed/candidates/dumont.npy").astype(float)
    res["boxes"]["earth_dumont"] = {"lat": 35.67863, "lon": -116.23156, "origin": "Gate 2 Dumont candidate (GNIS centre)",
                                   "usable_frac_2m_cells": round(float(np.isfinite(dp).mean()), 3),
                                   "slopes": masked_slopes(dp, np.isfinite(dp))}
    (ROOT / "results/gate2b_masked_slopes.json").write_text(json.dumps(res, indent=2))
    for k, v in res["boxes"].items():
        s = v["slopes"]
        print(f"{k:13s} usable1m {v.get('usable_frac_1m','-')!s:6} sand {v.get('sand_frac_1m','-')!s:6} facet {v.get('facet_frac_1m','-')!s:6} "
              f"| 2m med {s['2m']['median_deg']} p90 {s['2m']['p90_deg']} n={s['2m']['n_cells_used']} "
              f"| 16m med {s['16m']['median_deg']} p90 {s['16m']['p90_deg']} n={s['16m']['n_cells_used']}")


if __name__ == "__main__":
    main()
