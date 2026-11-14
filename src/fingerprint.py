# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Planet-agnostic terrain fingerprint (method A).

For each scale s (metres) the fingerprint holds:
  * slope stats (degrees): the DEM is block-averaged to s-metre cells, slope is taken
    from central differences on that coarser grid, and we report median, P90 and IQR.
  * roughness (metres): the DEM is cut into non-overlapping s x s windows, a plane is
    fitted to each by least squares, and the std of the residuals is the window's
    roughness. We report the median (and P90) over windows.

Inputs should already be on a common grid (see `to_common_grid`, default 2 m) so that
Mars, Moon and Earth patches are compared like for like.
"""
from __future__ import annotations

import numpy as np
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import reproject

MIN_VALID = 0.5  # fraction of valid pixels a block/window needs to count


def _as_float(dem: np.ndarray, nodata: float | None) -> np.ndarray:
    a = np.asarray(dem, dtype=np.float64).copy()
    if nodata is not None:
        a[a == nodata] = np.nan
    a[~np.isfinite(a)] = np.nan
    return a


def _block_mean(a: np.ndarray, k: int) -> np.ndarray:
    """NaN-aware k x k block mean; blocks under MIN_VALID valid become NaN."""
    if k == 1:
        return a
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    b = a[:h, :w].reshape(h // k, k, w // k, k)
    valid = np.isfinite(b).sum(axis=(1, 3))
    with np.errstate(invalid="ignore"):
        m = np.nansum(b, axis=(1, 3)) / np.maximum(valid, 1)
    m[valid < MIN_VALID * k * k] = np.nan
    return m


def slope_deg(a: np.ndarray, cell_m: float) -> np.ndarray:
    """Slope in degrees by central differences; NaN wherever a neighbour is NaN."""
    gy, gx = np.gradient(a, cell_m)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def _window_roughness(a: np.ndarray, k: int) -> np.ndarray:
    """Std of plane-detrended elevation in each non-overlapping k x k window."""
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    if h == 0 or w == 0:
        return np.array([])
    b = a[:h, :w].reshape(h // k, k, w // k, k).transpose(0, 2, 1, 3).reshape(-1, k * k)
    yy, xx = np.mgrid[0:k, 0:k]
    X = np.column_stack([np.ones(k * k), xx.ravel(), yy.ravel()]).astype(np.float64)
    out = np.full(b.shape[0], np.nan)
    full = np.isfinite(b).all(axis=1)
    if full.any():  # fast path: one shared least-squares solve for complete windows
        coef, *_ = np.linalg.lstsq(X, b[full].T, rcond=None)
        out[full] = (b[full].T - X @ coef).std(axis=0)
    for i in np.where(~full)[0]:
        m = np.isfinite(b[i])
        if m.sum() >= max(MIN_VALID * k * k, 4):
            c, *_ = np.linalg.lstsq(X[m], b[i, m], rcond=None)
            out[i] = (b[i, m] - X[m] @ c).std()
    return out


def _stats(v: np.ndarray) -> dict:
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"median": None, "p90": None, "iqr": None, "n": 0}
    q25, q50, q75, q90 = np.percentile(v, [25, 50, 75, 90])
    return {"median": float(q50), "p90": float(q90), "iqr": float(q75 - q25), "n": int(v.size)}


def fingerprint(dem: np.ndarray, pixel_m: float, scales_m: list[float],
                nodata: float | None = None) -> dict:
    """Return {scale_m: {"slope_deg": {median,p90,iqr,n}, "roughness_m": {median,p90,n}}}.

    Scales are rounded to a whole number of pixels (k = round(s / pixel_m) >= 1);
    the effective scale actually used is reported as "effective_scale_m".
    """
    a = _as_float(dem, nodata)
    out: dict = {"pixel_m": float(pixel_m), "valid_fraction": float(np.isfinite(a).mean()), "scales": {}}
    for s in scales_m:
        k = max(1, int(round(s / pixel_m)))
        coarse = _block_mean(a, k)
        sl = slope_deg(coarse, k * pixel_m) if min(coarse.shape) >= 3 else np.array([])
        rough = _window_roughness(a, k) if k >= 2 else np.array([])
        rs = _stats(rough)
        out["scales"][str(s)] = {
            "effective_scale_m": k * pixel_m,
            "slope_deg": _stats(sl),
            "roughness_m": {"median": rs["median"], "p90": rs["p90"], "n": rs["n"]},
        }
    return out


def to_common_grid(dem: np.ndarray, transform: Affine, crs, nodata: float | None,
                   target_m: float = 2.0) -> tuple[np.ndarray, Affine]:
    """Area-average resample a projected (metre) DEM to target_m pixels in its own CRS.

    Returns a float32 array with NaN as nodata, plus the new transform.
    """
    src = _as_float(dem, nodata).astype(np.float32)
    left, top = transform.c, transform.f
    width_m = abs(transform.a) * dem.shape[1]
    height_m = abs(transform.e) * dem.shape[0]
    w, h = int(width_m // target_m), int(height_m // target_m)
    dst_tr = Affine(target_m, 0, left, 0, -target_m, top)
    dst = np.full((h, w), np.nan, dtype=np.float32)
    reproject(src, dst, src_transform=transform, src_crs=crs, dst_transform=dst_tr, dst_crs=crs,
              src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.average)
    return dst, dst_tr


def hillshade(dem: np.ndarray, cell_m: float, azimuth: float = 315.0, altitude: float = 30.0) -> np.ndarray:
    """Standard hillshade in [0, 1]; NaN where the DEM is NaN."""
    g_row, g_col = np.gradient(dem, cell_m)
    dzdx, dzdy = g_col, -g_row  # x = east, y = north (rows run southwards)
    norm = np.sqrt(dzdx**2 + dzdy**2 + 1.0)
    az, alt = np.radians(azimuth), np.radians(altitude)  # azimuth clockwise from north
    sx, sy, sz = np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)
    hs = (-dzdx * sx - dzdy * sy + sz) / norm
    return np.clip(hs, 0, 1)
