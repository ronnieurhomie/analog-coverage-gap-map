# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Fetch USGS 3DEP 1 m DEM windows straight from the public USGS S3 COGs.

OpenTopography's USGS1m endpoint is restricted to academic keys, so we query the
USGS TNM Access API for the 1 m tiles covering an area, then read only the needed
window of each Cloud-Optimized GeoTIFF over HTTP and mosaic them.

Usage:
    python src/fetch_3dep.py NAME CENTER_LAT CENTER_LON WIDTH_M HEIGHT_M
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
import requests
from pyproj import Transformer
from rasterio.merge import merge
from rasterio.warp import transform_bounds

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "earth"
TNM = "https://tnmaccess.nationalmap.gov/api/v1/products"
DST_CRS = "EPSG:26911"  # NAD83 / UTM zone 11N, the native CRS of these tiles
GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif")


def utm_box(lat: float, lon: float, w: float, h: float) -> tuple[float, float, float, float]:
    x, y = Transformer.from_crs("EPSG:4326", DST_CRS, always_xy=True).transform(lon, lat)
    # snap to whole metres so the 1 m grid stays aligned
    return (round(x - w / 2), round(y - h / 2), round(x + w / 2), round(y + h / 2))


def tnm_tiles(bbox_ll: tuple[float, float, float, float]) -> list[dict]:
    r = requests.get(TNM, params={
        "datasets": "Digital Elevation Model (DEM) 1 meter",
        "bbox": ",".join(f"{v:.6f}" for v in bbox_ll),
        "outputFormat": "JSON", "max": 100}, timeout=120)
    r.raise_for_status()
    items = r.json().get("items", [])
    # if several projects overlap, keep the most recently published one per tile name
    best: dict[str, dict] = {}
    for it in items:
        key = it["title"].split(" ")[4]  # e.g. x56y395
        if key not in best or it.get("publicationDate", "") > best[key].get("publicationDate", ""):
            best[key] = it
    return list(best.values())


def fetch(name: str, lat: float, lon: float, w: float, h: float) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    box = utm_box(lat, lon, w, h)
    bbox_ll = transform_bounds(DST_CRS, "EPSG:4326", *box)
    tiles = tnm_tiles(bbox_ll)
    if not tiles:
        raise RuntimeError(f"No 3DEP 1 m tiles cover {name} {bbox_ll}")
    urls = ["/vsicurl/" + t["downloadURL"] for t in tiles]
    out = RAW / f"{name}_3dep1m.tif"
    with rasterio.Env(**GDAL_ENV):
        srcs = [rasterio.open(u) for u in urls]
        for s in srcs:
            if s.crs.to_string() != DST_CRS:
                raise RuntimeError(f"Unexpected CRS {s.crs} in {s.name}")
        nodata = srcs[0].nodata
        arr, tr = merge(srcs, bounds=box, res=1.0, nodata=nodata)
        prof = srcs[0].profile.copy()
        for s in srcs:
            s.close()
    prof.update(driver="GTiff", height=arr.shape[1], width=arr.shape[2], transform=tr,
                count=1, compress="deflate", tiled=True, blockxsize=512, blockysize=512, BIGTIFF="IF_SAFER")
    with rasterio.open(out, "w", **prof) as d:
        d.write(arr)
    valid = float(np.mean(arr[0] != nodata))
    return {
        "name": name,
        "file": str(out.relative_to(ROOT)),
        "source": "USGS 3D Elevation Program (3DEP) 1 m DEM, read from the USGS public S3 staged products",
        "product_ids": sorted(t["title"] for t in tiles),
        "urls": sorted(t["downloadURL"] for t in tiles),
        "publication_dates": sorted({t.get("publicationDate", "") for t in tiles}),
        "instrument": "Airborne lidar (3DEP)",
        "resolution_m": 1.0,
        "crs": DST_CRS,
        "units": "metres (elevation, NAVD88 per USGS 3DEP 1 m product spec)",
        "nodata": nodata,
        "aoi": {"center_lat": lat, "center_lon": lon, "width_m": w, "height_m": h,
                "utm_bounds": box, "lonlat_bounds": [round(v, 6) for v in bbox_ll]},
        "valid_fraction": round(valid, 4),
        "access_date": dt.date.today().isoformat(),
        "license": "Public domain (U.S. Government work). Cite: U.S. Geological Survey, 3D Elevation Program 1-Meter Resolution Digital Elevation Model.",
        "note": "OpenTopography USGS1m API refused this key (academic-only), so tiles were read directly from USGS S3.",
    }


if __name__ == "__main__":
    n, la, lo, w, h = sys.argv[1], *map(float, sys.argv[2:6])
    print(json.dumps(fetch(n, la, lo, w, h), indent=2))
