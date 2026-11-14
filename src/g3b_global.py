# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Task 3: exploratory global sampling per results/global_search_preregistration.json.

Usage: python src/g3b_global.py <branch> <deadline HH:MM WIB>
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests
from pyproj import Geod

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint, slope_deg  # noqa: E402
from g3v_common import bin_counts, provides  # noqa: E402
from g3v_recommend import frozen_norm  # noqa: E402
from gate3_common import PIX, SCALES, earth_patch, vec  # noqa: E402
import cop30_aws  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTD = ROOT / "data/raw/earth_cop30/global"
GEOD = Geod(ellps="WGS84")


def ndvi_mean():
    from pyhdf.SD import SD, SDC
    fs = sorted(glob.glob(str(ROOT / "data/raw/modis/MOD13C2.A2023*.hdf")))
    if len(fs) != 4:
        raise RuntimeError(f"expected 4 MOD13C2 files, found {len(fs)}")
    arrs = []
    for f in fs:
        sd = SD(f, SDC.READ)
        name = [n for n in sd.datasets() if "NDVI" in n and "Monthly" in n][0]
        a = sd.select(name).get().astype(float)
        a[a == -3000] = np.nan
        arrs.append(a / 10000.0)
    return np.mean(arrs, axis=0), [Path(f).name for f in fs]


def main(branch: str, deadline: str):
    t_end = dt.datetime.strptime(dt.date.today().isoformat() + " " + deadline, "%Y-%m-%d %H:%M")
    pre = json.loads((ROOT / "results/global_search_preregistration.json").read_text())
    nd, nd_files = ndvi_mean()
    mu, sd, T, _ = frozen_norm()
    method = "slope" if branch == "BASELINE_ONLY" else "A"
    t1 = json.loads((ROOT / "results/task1_nasa_test_sites.json").read_text())
    exp = json.loads((ROOT / "web/data/explorer.json").read_text())
    gaps = [p for p in exp["patches"] if not p["current_status"]["covered"]]
    P = np.load(ROOT / "data/processed/gate3_patches_30m.npz")
    Zm = {p["patch_id"]: (vec(fingerprint(P[p["patch_id"]], PIX, SCALES)) - mu) / sd for p in gaps}
    MB = {p["patch_id"]: bin_counts(slope_deg(P[p["patch_id"]].astype(float), PIX)) for p in gaps}
    sites = json.loads((ROOT / "data/processed/analog_sites.json").read_text())
    known_pts = [(s["Lat"], s["Lon"], f"USGS: {s['Name']}") for s in sites]
    n1 = json.loads((ROOT / "results/nasa_test_sites_preregistration.json").read_text())["included"]
    known_pts += [(v["lat"], v["lon"], f"NASA test site: {k}") for k, v in n1.items()]
    regions = [(-24.5, -69.25, "Atacama"), (19.82, -155.47, "Hawaii/Mauna Kea"), (35.0, -116.0, "Mojave"), (36.5, -117.0, "Death Valley")]
    rng = np.random.default_rng(20261114)
    lo_s, hi_s = math.sin(math.radians(-56)), math.sin(math.radians(60))
    OUTD.mkdir(parents=True, exist_ok=True)
    kept, skipped, drawn, stop_reason = [], {"ndvi_ocean_or_missing": 0, "ndvi_ge_0.15": 0, "cop30_invalid": 0, "cop30_error": 0}, 0, "cap 300 reached"
    while len(kept) < 300:
        if dt.datetime.now() > t_end:
            stop_reason = f"deadline {deadline} reached"; break
        drawn += 1
        lat = math.degrees(math.asin(rng.uniform(lo_s, hi_s))); lon = rng.uniform(-180, 180)
        r_, c_ = int((90 - lat) / 0.05), int((lon + 180) / 0.05)
        v = nd[min(r_, nd.shape[0] - 1), min(c_, nd.shape[1] - 1)]
        if not np.isfinite(v):
            skipped["ndvi_ocean_or_missing"] += 1; continue
        if v >= 0.15:
            skipped["ndvi_ge_0.15"] += 1; continue
        f = OUTD / f"g{drawn:05d}.tif"
        if not f.exists():
            try:
                res = cop30_aws.fetch(lat, lon, f)
            except Exception as e:
                skipped["cop30_error"] += 1; stop_reason = f"AWS read error {type(e).__name__}"; break
            if not res["ok"]:
                skipped["cop30_error"] += 1; continue
        p = earth_patch(str(f), lat, lon)
        if np.isfinite(p).mean() < 0.95:
            skipped["cop30_invalid"] += 1; continue
        z = (vec(fingerprint(p, PIX, SCALES)) - mu) / sd
        if method == "A":
            cov = [m for m in Zm if float(np.linalg.norm(Zm[m] - z)) < T]
        else:
            pr = provides(bin_counts(slope_deg(p.astype(float), PIX)))
            cov = [m for m in MB if MB[m][pr].sum() / MB[m].sum() >= 0.95]
        dk = min((GEOD.inv(lon, lat, b, a)[2] / 1000, n) for a, b, n in known_pts)
        dr = min((GEOD.inv(lon, lat, b, a)[2] / 1000, n) for a, b, n in regions)
        nov = "Known" if dk[0] <= 10 else ("Possibly known" if dk[0] <= 50 or dr[0] <= 150 else "Unverified")
        kept.append({"id": f"g{drawn:05d}", "lat": round(lat, 5), "lon": round(lon, 5), "ndvi_mean4": round(float(v), 4),
                     "covers_current_gap_patches": cov, "n_covered": len(cov), "nearest_known_km": round(dk[0], 1),
                     "nearest_known": dk[1], "nearest_region_km": round(dr[0], 1), "nearest_region": dr[1], "novelty": nov,
                     "file": str(f.relative_to(ROOT))})
        time.sleep(0.5)
    kept.sort(key=lambda k: -k["n_covered"])
    out = {"preregistration": pre, "method": method, "branch": branch, "ndvi_files": nd_files, "drawn": drawn, "processed_kept": len(kept),
           "skipped": skipped, "stop_reason": stop_reason, "current_gap_set": "USGS-29 union NASA test sites",
           "n_current_gap_patches": len(gaps), "denominator": 145, "nature": "exploratory", "patches": kept}
    (ROOT / "results/global_search.json").write_text(json.dumps(out, indent=2))
    print("drawn", drawn, "kept", len(kept), "skipped", skipped, "stop", stop_reason)
    for k in kept[:8]:
        print(k["id"], k["lat"], k["lon"], k["n_covered"], k["novelty"], k["nearest_known"], k["nearest_known_km"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
