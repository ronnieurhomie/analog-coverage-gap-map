# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Copernicus GLO-30 DEM windows from the AWS Open Data COGs (s3://copernicus-dem-30m), merged and saved locally."""
import math
from pathlib import Path
import rasterio, requests
from rasterio.merge import merge

BASE = "https://copernicus-dem-30m.s3.amazonaws.com"
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="2", GDAL_HTTP_TIMEOUT="60")


def tile_name(lat_floor: int, lon_floor: int) -> str:
    ns = f"N{lat_floor:02d}" if lat_floor >= 0 else f"S{-lat_floor:02d}"
    ew = f"E{lon_floor:03d}" if lon_floor >= 0 else f"W{-lon_floor:03d}"
    return f"Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM"


def fetch(lat: float, lon: float, out: Path, half_deg_lat: float = 0.03) -> dict:
    """Merge the tiles covering a small box around (lat, lon) into `out` (GeoTIFF, EPSG:4326)."""
    dlon = min(half_deg_lat / max(math.cos(math.radians(lat)), 0.05), 1.0)
    box = (lon - dlon, lat - half_deg_lat, lon + dlon, lat + half_deg_lat)
    tiles = {(math.floor(la), math.floor(lo)) for la in (box[1], box[3]) for lo in (box[0], box[2])}
    urls = []
    for la, lo in sorted(tiles):
        n = tile_name(la, lo); u = f"{BASE}/{n}/{n}.tif"
        if requests.head(u, timeout=30).status_code == 200:
            urls.append(u)
    if not urls:
        return {"ok": False, "reason": "no Copernicus tile (ocean or not distributed)", "tiles": []}
    with rasterio.Env(**ENV):
        srcs = [rasterio.open("/vsicurl/" + u) for u in urls]
        arr, tr = merge(srcs, bounds=box, nodata=-32767.0)
        prof = srcs[0].profile.copy()
        for s in srcs:
            s.close()
    prof.update(driver="GTiff", height=arr.shape[1], width=arr.shape[2], transform=tr, nodata=-32767.0, count=1,
                compress="deflate", tiled=False)
    prof.pop("blockxsize", None); prof.pop("blockysize", None)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **prof) as d:
        d.write(arr)
    return {"ok": True, "tiles": [u.split("/")[-1] for u in urls], "file": str(out)}
