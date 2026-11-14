# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Task 7: strongest candidate case file from results/global_search.json (exploratory).

Rule (stated before looking at the candidate): strongest = the processed global patch that covers the most Moon patches
that are gaps for USGS-29 union NASA test sites under the current method; ties -> lower id. Similar/different per
feature uses the card rule (relative difference |a-b|/max(|a|,|b|) <= 0.25 -> similar), against the median of the
Moon patches it covers.
Usage: python src/g3b_candidate.py "<country>" "<web check note>"
"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint, hillshade
from g3v_recommend import frozen_norm
from gate3_common import FEATURE_NAMES, PIX, SCALES, earth_patch, vec

ROOT = Path(__file__).resolve().parents[1]


def main(country: str, check: str):
    g = json.loads((ROOT / "results/global_search.json").read_text())
    if not g["patches"] or g["patches"][0]["n_covered"] == 0:
        out = {"qualifies": False, "statement": "No processed global patch covers any current gap Moon patch; no credible new candidate qualifies."}
        (ROOT / "results/candidate_case.json").write_text(json.dumps(out, indent=2)); print(out); return
    top = sorted(g["patches"], key=lambda k: (-k["n_covered"], k["id"]))[0]
    mu, sd, T, _ = frozen_norm()
    P = np.load(ROOT / "data/processed/gate3_patches_30m.npz")
    p = earth_patch(str(ROOT / top["file"]), top["lat"], top["lon"])
    vc = vec(fingerprint(p, PIX, SCALES)); zc = (vc - mu) / sd
    cov = top["covers_current_gap_patches"]
    dist = {m: float(np.linalg.norm((vec(fingerprint(P[m], PIX, SCALES)) - mu) / sd - zc)) for m in cov}
    targets = sorted(cov, key=lambda m: dist[m])[:2]
    vm = np.median([vec(fingerprint(P[m], PIX, SCALES)) for m in cov], axis=0)
    feats = []
    for n, a, b in zip(FEATURE_NAMES, vc, vm):
        rel = abs(a - b) / max(abs(a), abs(b)) if max(abs(a), abs(b)) > 0 else 0.0
        feats.append({"feature": n, "candidate": round(float(a), 3), "moon_covered_median": round(float(b), 3),
                      "relative_difference": round(rel, 3), "label": "similar" if rel <= 0.25 else "different"})
    gm = {r["patch_id"]: r for r in json.loads((ROOT / "results/gap_map.json").read_text())["patches"]}
    case = {"qualifies": True, "nature": "exploratory (G3v INCONCLUSIVE; geometric neighbours, not an engineering suitability ranking)",
            "candidate": {"id": top["id"], "lat": top["lat"], "lon": top["lon"], "country": country, "ndvi_mean4": top["ndvi_mean4"]},
            "data_sources": ["Copernicus GLO-30 DEM (AWS Open Data COG), 1.92 km window, 30 m", "MODIS MOD13C2 v061 2023 (Jan/Apr/Jul/Oct mean NDVI)",
                             "Moon: LOLA LDEM_80S_20M averaged to 30 m"],
            "coverage_contribution": {"method": "fingerprint A, frozen Gate 3 normalisation, T = %s" % T,
                                      "set": "current gaps for USGS-29 union NASA test sites", "n_gap_patches_covered": len(cov),
                                      "n_current_gap_patches": g["n_current_gap_patches"], "denominator": 145, "covered_patch_ids": cov},
            "novelty": {"flag": top["novelty"], "nearest_known": top["nearest_known"], "nearest_known_km": top["nearest_known_km"],
                        "nearest_region": top["nearest_region"], "nearest_region_km": top["nearest_region_km"], "limited_check": check,
                        "caveat": "> 50 km from a known point does not mean unstudied; Unverified is not a new discovery"},
            "comparison_targets": [{"patch_id": m, "lat": gm[m]["lat"], "lon": gm[m]["lon"], "distance": round(dist[m], 4)} for m in targets],
            "features": feats,
            "similarities": [f["feature"] for f in feats if f["label"] == "similar"],
            "differences": [f["feature"] for f in feats if f["label"] == "different"],
            "untested_conditions": ["gravity (1 g vs 0.17 g)", "regolith/soil mechanics and particle size", "rocks and roughness below 30 m",
                                    "illumination, thermal and vacuum environment", "COP30 is a surface model (vegetation/structures not removed)",
                                    "LOLA 20 m grid smoothing between laser tracks", "physical access, permits and land use"]}
    (ROOT / "results/candidate_case.json").write_text(json.dumps(case, indent=2))
    fig, axs = plt.subplots(1, 1 + len(targets), figsize=(4.6 * (1 + len(targets)), 4.8))
    for ax, (arr, lab) in zip(axs, [(p, f"EARTH {top['id']} ({top['lat']:.3f}, {top['lon']:.3f})\n{country}; {top['novelty']}")] +
                                   [(P[m], f"MOON {m} ({gm[m]['lat']:.2f}, {gm[m]['lon']:.1f})\nz-distance {dist[m]:.2f} (T = {T:.2f})") for m in targets]):
        ax.imshow(hillshade(arr.astype(float), PIX, 315, 30), cmap="gray", vmin=0, vmax=1, extent=[0, 1.92, 0, 1.92])
        ax.set_title(lab, fontsize=9); ax.set_xlabel("km")
    fig.suptitle("Candidate case (exploratory): same-scale hillshades, 1.92 km, 30 m grid, sun az 315 alt 30", fontsize=10)
    fig.tight_layout(); fig.savefig(ROOT / "results/candidate_case.png", dpi=110)
    print(json.dumps({k: case[k] for k in ["candidate", "coverage_contribution", "novelty", "comparison_targets", "similarities"]}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
