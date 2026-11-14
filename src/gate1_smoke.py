# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Gate 1 smoke run: fingerprints + hillshades for four patches.

  mars_sand      Hidden Valley, Gale crater (Curiosity turned back on slippery sand, Aug 2014)
  mars_nominal   a site on Curiosity's route inside the same DTM where it drove normally
  earth_dumont   Dumont Dunes, CA (Scarecrow mobility tests, May 2012)
  earth_negctrl  Avawatz Mountains, CA (rugged bedrock)

All patches are resampled to a common 2 m grid (area average) and cut to PATCH_M x PATCH_M.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint, hillshade, to_common_grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GRID_M = 2.0
PATCH_M = 256.0
SCALES_M = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0]

MARS_DTM = ROOT / "data/raw/mars/DTEEC_040770_1755_039280_1755_U01.IMG"
MARS_URL = ("https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/ORB_040700_040799/"
            "ESP_040770_1755_ESP_039280_1755/DTEEC_040770_1755_039280_1755_U01.IMG")
MARS_BYTES = 308422800  # Content-Length reported by the PDS server
if not MARS_DTM.exists() or MARS_DTM.stat().st_size != MARS_BYTES:
    MARS_DTM = "/vsicurl/" + MARS_URL  # same file, windowed HTTP range reads
EARTH_BOX = ROOT / "data/raw/earth/mojave_dumont_box_3dep1m.tif"
EARTH_NEG = ROOT / "data/raw/earth/avawatz_negctrl_3dep1m.tif"
PATCHES_JSON = ROOT / "data/processed/meta/gate1_patches.json"


def cut(path, lat: float, lon: float, size_m: float = PATCH_M) -> tuple[np.ndarray, dict]:
    """Cut a size_m square around (lat, lon), resample to GRID_M, return array + info."""
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(path) as d:
        geo = CRS(d.crs).geodetic_crs
        x, y = Transformer.from_crs(geo, d.crs, always_xy=True).transform(lon, lat)
        res = abs(d.transform.a)
        half = size_m / 2 + 4 * res  # small margin, trimmed after resampling
        col0, row0 = ~d.transform * (x - half, y + half)
        n = int(np.ceil(2 * half / res))
        win = Window(int(np.floor(col0)), int(np.floor(row0)), n, n)
        if win.col_off < 0 or win.row_off < 0 or win.col_off + n > d.width or win.row_off + n > d.height:
            raise RuntimeError(f"Patch at {lat},{lon} falls outside {path}")
        a = d.read(1, window=win)
        tr = d.window_transform(win)
        g, gtr = to_common_grid(a, tr, d.crs, d.nodata, GRID_M)
    # trim to exactly PATCH_M centred on the point
    c_col, c_row = ~gtr * (x, y)
    k = int(size_m / GRID_M)
    r0, c0 = int(round(c_row - k / 2)), int(round(c_col - k / 2))
    patch = g[r0:r0 + k, c0:c0 + k]
    src = str(path.relative_to(ROOT)) if isinstance(path, Path) else path.replace("/vsicurl/", "")
    info = {"file": src, "center_lat": lat, "center_lon": lon,
            "native_res_m": res, "grid_m": GRID_M, "size_m": size_m, "shape": list(patch.shape),
            "valid_fraction": float(np.isfinite(patch).mean())}
    return patch, info


def main() -> None:
    spec = json.loads(PATCHES_JSON.read_text())
    srcs = {"mars": MARS_DTM, "earth_box": EARTH_BOX, "earth_neg": EARTH_NEG}
    patches, results = {}, {"grid_m": GRID_M, "patch_m": PATCH_M, "scales_m": SCALES_M, "patches": {}}
    for name, p in spec["patches"].items():
        arr, info = cut(srcs[p["source"]], p["lat"], p["lon"])
        info["why"] = p["why"]
        fp = fingerprint(arr, GRID_M, SCALES_M)
        patches[name] = arr
        results["patches"][name] = {"info": info, "fingerprint": fp}

    # Distance: mean Canberra-style relative difference |a-b|/(|a|+|b|) over the feature
    # vector (slope median/P90/IQR at every scale + roughness median at every scale >= 4 m).
    def vec(fp):
        v = []
        for s in map(str, SCALES_M):
            st = fp["scales"][s]
            v += [st["slope_deg"]["median"], st["slope_deg"]["p90"], st["slope_deg"]["iqr"]]
            if st["roughness_m"]["median"] is not None:
                v.append(st["roughness_m"]["median"])
        return np.array(v, dtype=float)

    def dist(a, b):
        va, vb = vec(a), vec(b)
        den = np.abs(va) + np.abs(vb)
        return float(np.mean(np.where(den > 0, np.abs(va - vb) / np.where(den > 0, den, 1), 0)))

    names = list(patches)
    results["distance_metric"] = "mean over features of |a-b|/(|a|+|b|); 0 = identical, 1 = maximally different"
    results["distances"] = {f"{a}__{b}": dist(results["patches"][a]["fingerprint"], results["patches"][b]["fingerprint"])
                            for i, a in enumerate(names) for b in names[i + 1:]}
    out = ROOT / "results/gate1_fingerprints.json"
    out.write_text(json.dumps(results, indent=2))

    # Hillshades at the same scale (2 m grid, same extent), sun az 315, alt 30
    fig, axs = plt.subplots(1, len(names), figsize=(4 * len(names), 4.4))
    for ax, n in zip(axs, names):
        hs = hillshade(patches[n], GRID_M, 315.0, 30.0)
        ax.imshow(hs, cmap="gray", vmin=0, vmax=1, extent=[0, PATCH_M, 0, PATCH_M])
        ax.set_title(spec["patches"][n]["label"], fontsize=10)
        ax.set_xlabel("m")
    axs[0].set_ylabel("m")
    fig.suptitle(f"Gate 1 patches: {PATCH_M:.0f} m squares on a common {GRID_M:.0f} m grid; "
                 "hillshade sun azimuth 315°, altitude 30°", fontsize=10)
    fig.tight_layout()
    fig.savefig(ROOT / "results/gate1_hillshades.png", dpi=150)
    print(json.dumps({"distances": results["distances"]}, indent=2))


if __name__ == "__main__":
    main()
