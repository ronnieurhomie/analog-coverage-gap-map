# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Task 2 (post-hoc robustness): Moon coverage under the current method using ALL USGS layer records with valid COP30."""
import json, math, os, sys, time
from pathlib import Path
import numpy as np, requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint
from g3v_recommend import frozen_norm
from gate3_common import PIX, SCALES, earth_patch, vec
import cop30_aws

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data/raw/earth_cop30/usgs_all"; D.mkdir(parents=True, exist_ok=True)
recs = json.loads((ROOT / "data/processed/analog_sites.json").read_text())
sel = json.loads((ROOT / "results/known_sites_selection.json").read_text())["sites"]
done = {s["record_index"]: ROOT / f"data/raw/earth_cop30/sites/{s['site_id']}_cop30.tif" for s in sel}
mu, sd, T, _ = frozen_norm()
P = np.load(ROOT / "data/processed/gate3_patches_30m.npz")
gm = json.loads((ROOT / "results/gap_map.json").read_text())
moon = [r["patch_id"] for r in gm["patches"]]
Zm = {m: (vec(fingerprint(P[m], PIX, SCALES)) - mu) / sd for m in moon}
Z, status, stop = {}, {}, None
for i, r in enumerate(recs):
    f = done.get(i, D / f"rec{i:03d}_cop30.tif")
    if not f.exists():
        try:
            res = cop30_aws.fetch(r["Lat"], r["Lon"], f)
        except Exception as e:
            stop = f"AWS read error {type(e).__name__}: {e}"[:150]; break
        if not res["ok"]:
            status[i] = res["reason"]; continue
    p = earth_patch(str(f), r["Lat"], r["Lon"])
    if np.isfinite(p).mean() < 0.95:
        status[i] = "valid < 95%"; continue
    Z[i] = (vec(fingerprint(p, PIX, SCALES)) - mu) / sd; status[i] = "ok"
cov = [m for m in moon if min(float(np.linalg.norm(Zm[m] - z)) for z in Z.values()) < T] if Z else []
out = {"label": "POST-HOC robustness (not the headline)", "method": "fingerprint A, frozen Gate 3 normalisation, T = %s" % T,
       "set": "all USGS Known Terrestrial Analog Sites records with valid COP30 (centre = Lat/Lon attributes); COP30 from OpenTopography for the 30 Gate 3 sites and AWS Open Data COGs for the rest (identical product)",
       "records_total": len(recs), "records_attempted": len(status), "records_used": len(Z), "stop_reason": stop,
       "skipped": {str(k): v for k, v in status.items() if v != "ok"},
       "covered": len(cov), "denominator": 145, "gap_percent": round(100 * (1 - len(cov) / 145), 2), "nature": "exploratory (post-hoc)"}
(ROOT / "results/task2_all_usgs.json").write_text(json.dumps(out, indent=2))
print({k: v for k, v in out.items() if k != "skipped"}, "n skipped", len(out["skipped"]))
