# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Shared Gate 3 settings and 30 m patch extraction helpers."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import reproject

ROOT = Path(__file__).resolve().parents[1]
PIX = 30.0
NPX = 64
PATCH_M = PIX * NPX  # 1920 m
SCALES = [30.0, 60.0, 120.0, 240.0, 480.0]
SEED = 20261114


def aeqd(lat: float, lon: float) -> str:
    """Local azimuthal-equidistant CRS centred on the site (metres, negligible distortion over 2 km)."""
    return f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"


def earth_patch(src_path: str, lat: float, lon: float, resampling=Resampling.bilinear,
                src_nodata=None) -> np.ndarray:
    """64x64 px, 30 m patch centred on (lat, lon), reprojected from a lat/lon DEM to local aeqd."""
    tr = Affine(PIX, 0, -PATCH_M / 2, 0, -PIX, PATCH_M / 2)
    dst = np.full((NPX, NPX), np.nan, dtype=np.float32)
    with rasterio.open(src_path) as d:
        reproject(rasterio.band(d, 1), dst, dst_transform=tr, dst_crs=aeqd(lat, lon),
                  src_nodata=src_nodata if src_nodata is not None else d.nodata, dst_nodata=np.nan,
                  resampling=resampling)
    return dst


def vec(fp: dict, scales=SCALES) -> np.ndarray:
    v = []
    for s in map(str, scales):
        st = fp["scales"][s]
        v += [st["slope_deg"]["median"], st["slope_deg"]["p90"], st["slope_deg"]["iqr"]]
        if st["roughness_m"]["median"] is not None:
            v.append(st["roughness_m"]["median"])
    return np.array(v, dtype=float)


FEATURE_NAMES = []
for _s in SCALES:
    FEATURE_NAMES += [f"slope_median_{int(_s)}m", f"slope_p90_{int(_s)}m", f"slope_iqr_{int(_s)}m"]
    if _s > PIX:
        FEATURE_NAMES.append(f"roughness_median_{int(_s)}m")
