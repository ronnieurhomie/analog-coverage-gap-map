# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G4: build display-only data for the static site from existing results (no new analysis).

Writes web/data/display.json and web/img/{moon,earth}/*.png (same-scale hillshades, 1.92 km, az 315, alt 30).
The only re-derivation is the per-patch flags for the post-hoc all-USGS set (results/task2_all_usgs.json stores only
the count); it uses the identical frozen method and is asserted to reproduce covered = 85 exactly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fingerprint import fingerprint, hillshade  # noqa: E402
from g3v_recommend import frozen_norm  # noqa: E402
from gate3_common import FEATURE_NAMES, PIX, SCALES, earth_patch, vec  # noqa: E402

WEB = ROOT / "web"
PX = 192  # rendered size (64 px at 30 m, nearest-neighbour x3: no smoothing implied)


def render(arr: np.ndarray, out: Path):
    hs = hillshade(arr.astype(float), PIX, 315.0, 30.0)
    img = Image.fromarray((np.clip(hs, 0, 1) * 255).astype(np.uint8), mode="L").resize((PX, PX), Image.NEAREST)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)


def main():
    ex = json.loads((ROOT / "web/data/explorer.json").read_text())
    gm = json.loads((ROOT / "results/gap_map.json").read_text())
    rc = json.loads((ROOT / "results/report_card.json").read_text())
    t1 = json.loads((ROOT / "results/task1_nasa_test_sites.json").read_text())
    a2 = json.loads((ROOT / "results/task2_all_usgs.json").read_text())
    pre1 = json.loads((ROOT / "results/nasa_test_sites_preregistration.json").read_text())["included"]
    fetch1 = json.loads((ROOT / "data/processed/meta/nasa_sites_fetch.json").read_text())
    cc = json.loads((ROOT / "results/candidate_case.json").read_text())
    mu, sd, T, _ = frozen_norm()
    P = np.load(ROOT / "data/processed/gate3_patches_30m.npz")

    arrays = {k: P[k] for k in P.files}
    for k, s in pre1.items():
        arrays[f"nasa_{k}"] = earth_patch(fetch1[k]["file"], s["lat"], s["lon"])
    c = cc["candidate"]
    gfile = json.loads((ROOT / "results/global_search.json").read_text())
    gpatch = {p["id"]: p for p in gfile["patches"]}
    arrays[c["id"]] = earth_patch(str(ROOT / gpatch[c["id"]]["file"]), c["lat"], c["lon"])

    # entities shown in the UI
    moon_ids = [p["patch_id"] for p in ex["patches"]]
    earth_ids = sorted({n["id"] for p in ex["patches"] for n in p["neighbours"]} | {c["id"]})
    feats = {k: [round(float(x), 4) for x in vec(fingerprint(arrays[k], PIX, SCALES))] for k in moon_ids + earth_ids}

    # per-patch status by set
    nasa_cov = set().union(*[set(v["covered_patch_ids"]) for v in rc["sites"].values()])
    assert len(nasa_cov) == t1["sets"]["a_NASA_test_sites_alone"]["covered"]
    # all-USGS: identical frozen method over the 190 usable records
    recs = json.loads((ROOT / "data/processed/analog_sites.json").read_text())
    sel = {s["record_index"]: ROOT / f"data/raw/earth_cop30/sites/{s['site_id']}_cop30.tif"
           for s in json.loads((ROOT / "results/known_sites_selection.json").read_text())["sites"]}
    Zs = []
    for i, r in enumerate(recs):
        f = sel.get(i, ROOT / f"data/raw/earth_cop30/usgs_all/rec{i:03d}_cop30.tif")
        if not f.exists():
            continue
        p = earth_patch(str(f), r["Lat"], r["Lon"])
        if np.isfinite(p).mean() < 0.95:
            continue
        Zs.append((vec(fingerprint(p, PIX, SCALES)) - mu) / sd)
    assert len(Zs) == a2["records_used"], (len(Zs), a2["records_used"])
    all_cov = {m for m in moon_ids if min(float(np.linalg.norm((np.array(feats[m]) - mu) / sd - z)) for z in Zs) < T}
    assert len(all_cov) == a2["covered"], (len(all_cov), a2["covered"])

    hist = {r["patch_id"]: r for r in gm["patches"]}
    patches = []
    for p in ex["patches"]:
        m = p["patch_id"]
        patches.append({"id": m, "lat": p["lat"], "lon": p["lon"], "x": p["ps_x_m"], "y": p["ps_y_m"],
                        "status": {"union": bool(p["current_status"]["covered"]), "nasa": m in nasa_cov,
                                   "allusgs": m in all_cov, "historical": bool(hist[m]["covered"])},
                        "neighbours": [dict(n, below_T=n["distance"] < T) for n in p["neighbours"]],
                        "global_candidates_covering": p["global_candidates_covering"]})
    sets = {
        "union": {"label": "USGS-29 ∪ 3 NASA test sites", "covered": t1["sets"]["b_USGS29_union_NASA"]["covered"],
                  "nature": "current method, exploratory", "source": "results/task1_nasa_test_sites.json"},
        "nasa": {"label": "3 NASA test sites only", "covered": t1["sets"]["a_NASA_test_sites_alone"]["covered"],
                 "nature": "current method, exploratory", "source": "results/task1_nasa_test_sites.json"},
        "allusgs": {"label": "all USGS analog sites (190/192 usable)", "covered": a2["covered"],
                    "nature": "post-hoc robustness, exploratory", "source": "results/task2_all_usgs.json"},
        "historical": {"label": "historical: USGS-29 (Gate 3a)", "covered": 145 - sum(not r["covered"] for r in gm["patches"]),
                       "nature": "historical (fingerprint A, T = 2.317)", "source": "results/gap_map.json"}}
    for k, s in sets.items():
        s["gap"] = 145 - s["covered"]; s["denominator"] = 145
        assert s["covered"] == sum(p["status"][k] for p in patches), k

    names = {n["id"]: {"name": n["name"], "set": n["set"]} for p in ex["patches"] for n in p["neighbours"]}
    names[c["id"]] = {"name": f"global candidate {c['id']}", "set": "global candidate"}
    out = {"T": T, "feature_names": FEATURE_NAMES, "feature_sd": [round(float(x), 4) for x in sd],
           "features": feats, "earth_names": names, "sets": sets, "patches": patches,
           "method": "fingerprint A: 19 frozen 30 m features, Gate 3 pooled mean/std, covered if z-distance < T",
           "denominator": 145, "generated_from": ["web/data/explorer.json", "results/gap_map.json", "results/report_card.json",
                                                  "results/task1_nasa_test_sites.json", "results/task2_all_usgs.json",
                                                  "results/candidate_case.json"]}
    (WEB / "data/display.json").write_text(json.dumps(out, separators=(",", ":")))
    for k in moon_ids:
        render(arrays[k], WEB / "img/moon" / f"{k}.png")
    for k in earth_ids:
        render(arrays[k], WEB / "img/earth" / f"{k}.png")
    print("display.json", (WEB / "data/display.json").stat().st_size, "B | moon imgs", len(moon_ids), "| earth imgs", len(earth_ids),
          "| sets", {k: (v["covered"], v["gap"]) for k, v in sets.items()})


if __name__ == "__main__":
    main()
