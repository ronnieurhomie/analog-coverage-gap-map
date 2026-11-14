# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Verify the LOLA LDEM_80S_20M download: size, grid, CRS, and a decimated height sanity check."""
import json, sys
from pathlib import Path
import numpy as np, rasterio
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "data/raw/moon/ldem_80s_20m.img"
LBL = ROOT / "data/raw/moon/ldem_80s_20m.lbl"
EXPECTED = 1848320000
size = IMG.stat().st_size
print("size", size, "expected", EXPECTED, "OK" if size == EXPECTED else "MISMATCH")
with rasterio.open(LBL) as d:
    print("driver", d.driver, "shape", d.shape, "res", d.res, "dtype", d.dtypes[0], "nodata", d.nodata)
    print("scale/offset", d.scales, d.offsets)
    print("crs", d.crs.to_wkt()[:300])
    print("bounds", d.bounds)
    a = d.read(1, out_shape=(1520, 1520), resampling=Resampling.nearest).astype(float)
h = a * 0.5  # height (m) = DN * SCALING_FACTOR, relative to 1737.4 km sphere (label)
print("decimated heights (m): min %.1f max %.1f median %.1f" % (h.min(), h.max(), np.median(h)))
