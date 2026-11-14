# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G3v data extraction per results/g3v_preregistration.json (sites + target groups, 1.92 km windows).

Writes data/processed/g3v/{sites,targets}/<name>_{30m,2m}.npy and data/processed/g3v/extract_meta.json.
Target 2 m windows are read here ONLY to apply the >= 95% validity rule; no slope is computed from them here.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.merge import merge
from rasterio.warp import transform_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate2_candidates as gc  # noqa: E402
from fingerprint import to_common_grid  # noqa: E402
from gate3_common import earth_patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/g3v"
W = 1920.0
HALF = W / 2
COP_AREA = ROOT / "data/raw/earth_cop30/cop30_gate2_area.tif"
COP_DIR = ROOT / "data/raw/earth_cop30/g3v_targets"


def read_2m(x, y):
    m = 8.0
    box = (round(x - HALF - m), round(y - HALF - m), round(x + HALF + m), round(y + HALF + m))
    tiles = gc.tiles_for(box)
    if not tiles:
        return None, [], 0.0
    with rasterio.Env(**gc.ENV):
        srcs = [rasterio.open("/vsicurl/" + t["downloadURL"]) for t in tiles]
        srcs = [s for s in srcs if s.crs.to_string() == gc.CRS_UTM]
        if not srcs:
            return None, [], 0.0
        nod = srcs[0].nodata
        arr, tr = merge(srcs, bounds=box, res=1.0, nodata=nod)
        for s in srcs:
            s.close()
    g, gtr = to_common_grid(arr[0], tr, gc.CRS_UTM, nod, 2.0)
    c, r = ~gtr * (x, y)
    k = int(W / 2.0)
    r0, c0 = int(round(r - k / 2)), int(round(c - k / 2))
    p = g[r0:r0 + k, c0:c0 + k]
    return p, sorted(t["title"] for t in tiles), float(np.isfinite(p).mean()) if p.size == k * k else 0.0


def edge_dist(a, b):
    """Edge-to-edge distance between two axis-aligned 1.92 km windows (UTM centres)."""
    dx = max(abs(a[0] - b[0]) - W, 0.0); dy = max(abs(a[1] - b[1]) - W, 0.0)
    return math.hypot(dx, dy)


def cop30_fetch(name, lat_lo, lat_hi, lon_lo, lon_hi):
    COP_DIR.mkdir(parents=True, exist_ok=True)
    out = COP_DIR / f"{name}_cop30.tif"
    if out.exists() and out.stat().st_size > 1000:
        return out
    r = requests.get("https://portal.opentopography.org/API/globaldem", params=dict(
        demtype="COP30", south=lat_lo, north=lat_hi, west=lon_lo, east=lon_hi, outputFormat="GTiff",
        API_Key=os.environ["OPENTOPO_API_KEY"]), timeout=300)
    if r.status_code != 200 or r.content[:2] not in (b"II", b"MM"):
        raise RuntimeError(f"COP30 {name}: HTTP {r.status_code} {r.text[:120]}")
    out.write_bytes(r.content)
    return out


def main():
    t0 = time.time()
    (OUT / "sites").mkdir(parents=True, exist_ok=True); (OUT / "targets").mkdir(parents=True, exist_ok=True)
    cj = json.loads((ROOT / "results/candidates.json").read_text())
    cands = cj["candidates"]
    meta = {"sites": {}, "site_groups": {}, "targets": {}, "groups": [], "rejected_ring_points": []}

    # --- candidate windows ---
    cpos = {c["name"]: (c["utm_x"], c["utm_y"]) if "utm_x" in c else gc.to_utm.transform(c["lon"], c["lat"]) for c in cands}

    def do_site(c):
        n = c["name"]; x, y = cpos[n]
        p30 = earth_patch(str(COP_AREA), c["lat"], c["lon"])
        p2, tiles, v2 = read_2m(x, y)
        v30 = float(np.isfinite(p30).mean())
        np.save(OUT / "sites" / f"{n}_30m.npy", p30)
        if p2 is not None:
            np.save(OUT / "sites" / f"{n}_2m.npy", p2.astype(np.float32))
        return n, {"lat": c["lat"], "lon": c["lon"], "utm": [x, y], "valid_30m": round(v30, 4), "valid_2m": round(v2, 4),
                   "tiles": tiles, "eligible": v30 >= 0.95 and v2 >= 0.95}
    with ThreadPoolExecutor(8) as ex:
        for n, rec in ex.map(do_site, cands):
            meta["sites"][n] = rec
    print("sites done", round(time.time() - t0), "s", flush=True)

    # site grouping (union-find): centres < 5 km apart or windows overlap
    names = sorted(cpos); par = {n: n for n in names}
    def f(a):
        while par[a] != a:
            a = par[a]
        return a
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            pa, pb = cpos[a], cpos[b]
            if math.hypot(pa[0] - pb[0], pa[1] - pb[1]) < 5000 or edge_dist(pa, pb) == 0.0:
                ra, rb = f(a), f(b)
                if ra != rb:
                    par[max(ra, rb)] = min(ra, rb)
    groups = {}
    for n in names:
        groups.setdefault(f(n), []).append(n)
    for root, mem in groups.items():
        el = [m for m in sorted(mem) if meta["sites"][m]["eligible"]]
        meta["site_groups"][sorted(mem)[0]] = {"windows": sorted(mem), "eligible_windows": el, "eligible": bool(el)}

    # --- target groups on the ring ---
    x0, y0, x1, y1 = cj["area_utm11n"]
    R = 15000.0
    X0, Y0, X1, Y1 = x0 - R, y0 - R, x1 + R, y1 + R
    per = 2 * ((X1 - X0) + (Y1 - Y0)); step = per / 16
    ring = []
    for i in range(16):
        s = i * step
        L1, L2 = X1 - X0, Y1 - Y0
        if s < L1: ring.append((X0 + s, Y1))
        elif s < L1 + L2: ring.append((X1, Y1 - (s - L1)))
        elif s < 2 * L1 + L2: ring.append((X1 - (s - L1 - L2), Y0))
        else: ring.append((X0, Y0 + (s - 2 * L1 - L2)))
    used = []  # earlier-gate patch centres (UTM) with their half-size
    for la, lo, hs in [(35.67863, -116.23156, 4000), (35.5069188, -116.2847431, 500), (34.9035, -115.71805, 128),
                       (36.612, -117.11517, 128), (37.09579, -117.67534, 128), (35.680852, -116.226566, 128),
                       (35.676675, -116.235999, 128)]:
        used.append((*gc.to_utm.transform(lo, la), hs))
    accepted = []
    for gi, (gx, gy) in enumerate(ring):
        if len(accepted) == 8:
            break
        tpos = [(gx - 2500, gy), (gx, gy), (gx + 2500, gy)]
        reason = None
        if any(edge_dist(t, cpos[c]) < 5000 for t in tpos for c in cpos):
            reason = "within 5 km of a candidate window"
        elif any(math.hypot(gx - a["utm"][0], gy - a["utm"][1]) < 20000 for a in accepted):
            reason = "within 20 km of an accepted group"
        elif any(max(abs(t[0] - u[0]) - HALF - u[2], abs(t[1] - u[1]) - HALF - u[2], 0) < 5000 for t in tpos for u in used):
            reason = "within 5 km of an earlier-gate patch"
        if reason:
            meta["rejected_ring_points"].append({"ring_index": gi, "utm": [gx, gy], "reason": reason}); continue
        lls = [gc.to_ll.transform(*t) for t in tpos]
        recs, ok = [], True
        with ThreadPoolExecutor(3) as ex:
            twos = list(ex.map(lambda t: read_2m(*t), tpos))
        lat_lo = min(l[1] for l in lls) - 0.03; lat_hi = max(l[1] for l in lls) + 0.03
        lon_lo = min(l[0] for l in lls) - 0.04; lon_hi = max(l[0] for l in lls) + 0.04
        try:
            cop = cop30_fetch(f"ring{gi:02d}", lat_lo, lat_hi, lon_lo, lon_hi)
        except Exception as e:
            meta["rejected_ring_points"].append({"ring_index": gi, "utm": [gx, gy], "reason": str(e)[:150]}); continue
        for k, (t, (lon, lat), (p2, tiles, v2)) in enumerate(zip(tpos, lls, twos)):
            p30 = earth_patch(str(cop), lat, lon); v30 = float(np.isfinite(p30).mean())
            recs.append({"name": f"g{len(accepted)}_t{k}", "lat": round(lat, 6), "lon": round(lon, 6), "utm": list(t),
                         "valid_30m": round(v30, 4), "valid_2m": round(v2, 4), "tiles": tiles, "p30": p30, "p2": p2})
            ok &= v30 >= 0.95 and v2 >= 0.95
        if not ok:
            meta["rejected_ring_points"].append({"ring_index": gi, "utm": [gx, gy], "reason": "a target < 95% valid at 30 m or 2 m",
                                                 "valid": [(r["valid_30m"], r["valid_2m"]) for r in recs]}); continue
        for r in recs:
            np.save(OUT / "targets" / f"{r['name']}_30m.npy", r.pop("p30"))
            np.save(OUT / "targets" / f"{r['name']}_2m.npy", r.pop("p2").astype(np.float32))
            meta["targets"][r["name"]] = r
        accepted.append({"group": len(accepted), "ring_index": gi, "utm": [gx, gy], "cop30_file": str(cop.relative_to(ROOT)),
                         "targets": [r["name"] for r in recs]})
        print("accepted group", len(accepted) - 1, "ring", gi, round(time.time() - t0), "s", flush=True)
    meta["groups"] = accepted
    meta["n_groups"] = len(accepted)
    meta["elapsed_s"] = round(time.time() - t0)
    (OUT / "extract_meta.json").write_text(json.dumps(meta, indent=2, default=float))
    print("groups:", len(accepted), "sites:", len(meta["site_groups"]), "eligible sites:",
          sum(g["eligible"] for g in meta["site_groups"].values()), "elapsed", meta["elapsed_s"], "s")


if __name__ == "__main__":
    main()
