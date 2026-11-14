# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G3b Moon-side outputs: Task 1 (NASA test sites), Task 2 (robustness), Task 5 (report card), Task 6 (explorer data).

Usage: python src/g3b_moon.py <branch>   (branch from results/g3v_results.json)
Current method: fingerprint A, T = 2.317, frozen Gate 3 normalisation, unless branch == BASELINE_ONLY (then slope
method per results/nasa_test_sites_preregistration.json). Historical Gate 3 results are read, never rewritten.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.enums import Resampling

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint, hillshade, slope_deg  # noqa: E402
from g3v_common import BINS, bin_counts, provides  # noqa: E402
from g3v_recommend import frozen_norm  # noqa: E402
from gate3_common import FEATURE_NAMES, PIX, SCALES, earth_patch, vec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(branch: str):
    now = dt.datetime.now().isoformat(timespec="seconds")
    gm = json.loads((ROOT / "results/gap_map.json").read_text())
    pre1 = json.loads((ROOT / "results/nasa_test_sites_preregistration.json").read_text())
    fetch1 = json.loads((ROOT / "data/processed/meta/nasa_sites_fetch.json").read_text())
    P = np.load(ROOT / "data/processed/gate3_patches_30m.npz")
    mu, sd, T, npool = frozen_norm()
    method = "slope" if branch == "BASELINE_ONLY" else "A"
    moon = [r["patch_id"] for r in gm["patches"]]
    usgs = list(gm["known_sites"])
    mojave = [k for k in P.files if k.startswith("mojave_")]
    patches = {k: P[k] for k in P.files}
    labels = {k: gm["known_sites"][k]["name"] for k in usgs}
    sets = {k: "USGS-29" for k in usgs}

    nasa, skipped = [], {}
    for k, s in pre1["included"].items():
        f = fetch1.get(k, {})
        if not f.get("ok"):
            skipped[k] = f"COP30 fetch failed ({f.get('status')})"; continue
        p = earth_patch(f["file"], s["lat"], s["lon"])
        v = float(np.isfinite(p).mean())
        if v < 0.95:
            skipped[k] = f"valid {v:.3f} < 0.95"; continue
        patches[f"nasa_{k}"] = p; nasa.append(f"nasa_{k}"); labels[f"nasa_{k}"] = k.replace("_", " "); sets[f"nasa_{k}"] = "NASA test site"
    for k in mojave:
        labels[k] = k.replace("mojave_", "Mojave "); sets[k] = "Mojave grid (Gate 2)"

    V = {k: vec(fingerprint(p, PIX, SCALES)) for k, p in patches.items()}
    Z = {k: (v - mu) / sd for k, v in V.items()}
    SB = {k: provides(bin_counts(slope_deg(patches[k].astype(float), PIX))) for k in usgs + nasa + mojave}
    MB = {m: bin_counts(slope_deg(patches[m].astype(float), PIX)) for m in moon}

    def covered(m, site_list):
        if not site_list:
            return False, None, None
        if method == "A":
            d = {s: float(np.linalg.norm(Z[m] - Z[s])) for s in site_list}
            b = min(d, key=d.get); return d[b] < T, b, d[b]
        prov = np.any([SB[s] for s in site_list], axis=0)
        frac = float(MB[m][prov].sum() / MB[m].sum())
        return frac >= 0.95, None, frac

    method_info = {
        "method": "fingerprint A (19 frozen 30 m features, Gate 3 pooled mean/std)" if method == "A" else "slope method (30 m slope bins)",
        "threshold_or_definition": f"covered if z-distance to nearest site in set < T = {T}" if method == "A"
        else "site provides a 30 m slope bin if >= 5% of its valid 30 m area; Moon patch covered if >= 95% of its valid 30 m area is in provided bins",
        "denominator": "145 Moon patches (results/moon_patches.json, 84-90 S grid); patch fractions are not area fractions of the lunar south pole",
        "nature": "current (method chosen by G3v branch " + branch + ")" + ("; exploratory: G3v evidence insufficient" if branch == "INCONCLUSIVE" else ""),
        "historical_note": "historical Gate 3 result (fingerprint A, T = 2.317, USGS-29): gap 60.0% (87/145); kept separate, not spliced",
        "generated": now}

    # ---- Task 1 ----
    t1 = {"method_info": method_info, "nasa_sites_used": nasa, "nasa_sites_skipped": skipped, "sets": {}}
    for name, sl in [("a_NASA_test_sites_alone", nasa), ("b_USGS29_union_NASA", usgs + nasa), ("ref_USGS29_current_method", usgs)]:
        c = [covered(m, sl)[0] for m in moon]
        t1["sets"][name] = {"n_sites": len(sl), "covered": int(sum(c)), "denominator": len(moon),
                            "covered_percent": round(100 * sum(c) / len(moon), 2), "gap_percent": round(100 * (1 - sum(c) / len(moon)), 2)}
    (ROOT / "results/task1_nasa_test_sites.json").write_text(json.dumps(t1, indent=2))

    # ---- Task 5: report card ----
    card = {"method_info": method_info, "note": "Covers only the cited NASA test sites in results/nasa_test_sites_preregistration.json, "
            "not all NASA test sites, and says nothing about their overall value.", "sites": {}}
    for s in nasa:
        cov = [m for m in moon if covered(m, [s])[0]]
        card["sites"][labels[s]] = {"moon_patches_covered": len(cov), "denominator": len(moon),
                                    "covered_percent": round(100 * len(cov) / len(moon), 2),
                                    "slope_bins_provided_30m": [f"[{lo},{hi})" for (lo, hi), p in zip(BINS, SB[s]) if p],
                                    "covered_patch_ids": cov}
    (ROOT / "results/report_card.json").write_text(json.dumps(card, indent=2))

    # ---- Task 2: robustness (post-hoc) ----
    t2 = {"label": "POST-HOC robustness (not the headline); historical results unchanged", "method_info": method_info}
    if method == "A":
        moj_nn = [min(float(np.linalg.norm(Z[a] - Z[b])) for b in mojave if b != a) for a in mojave]
        nn_moon = {m: min(float(np.linalg.norm(Z[m] - Z[s])) for s in usgs) for m in moon}
        pcts = list(range(50, 100)); curve = []
        for q in pcts:
            Tq = float(np.percentile(moj_nn, q))
            curve.append({"percentile": q, "T": round(Tq, 4), "gap_percent_USGS29": round(100 * np.mean([nn_moon[m] >= Tq for m in moon]), 2)})
        t2["threshold_sensitivity_USGS29"] = curve
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([c["percentile"] for c in curve], [c["gap_percent_USGS29"] for c in curve], "-o", ms=3)
        ax.axvline(90, color="r", ls="--", lw=0.8); ax.set_xlabel("threshold = percentile of Mojave NN distances")
        ax.set_ylabel("gap % of 145 Moon patches (USGS-29)"); ax.set_title("Post-hoc threshold sensitivity, fingerprint A (registered: 90th pct)", fontsize=9)
        fig.tight_layout(); fig.savefig(ROOT / "results/gap_threshold_sensitivity.png", dpi=120)
    rows = []
    for m in moon:
        c, b, d = covered(m, usgs + nasa)
        rows.append((d, m, b))
    rows.sort(key=lambda r: r[0])
    sm = FEATURE_NAMES.index("slope_median_30m")
    pick = rows[:5] + rows[-5:] if method == "A" else rows[-5:] + rows[:5]
    t2["best_and_worst_covered_USGS29_union_NASA"] = [{"patch_id": m, "distance_or_fraction": round(d, 4), "nearest": labels.get(b) if b else None,
                                                       "slope_median_30m": round(float(V[m][sm]), 2)} for d, m, b in pick]
    a2f = ROOT / "results/task2_all_usgs.json"
    t2["all_usgs_sites"] = ({k: v for k, v in json.loads(a2f.read_text()).items() if k != "skipped"} if a2f.exists()
                            else "not run")
    (ROOT / "results/task2_robustness.json").write_text(json.dumps(t2, indent=2))

    # ---- Task 6: explorer data ----
    comp = usgs + nasa + mojave
    ex = {"method_info": dict(method_info, comparison_sets={"USGS-29": "Gate 3 known sites (COP30)", "NASA test site": "Task 1 cited sites",
                                                            "Mojave grid (Gate 2)": "64 Gate 2 candidate centres at 30 m"},
                              neighbours="5 nearest by fingerprint-A z-distance (geometric neighbours, not an engineering suitability ranking)"),
          "patches": []}
    hist = {r["patch_id"]: r for r in gm["patches"]}
    for m in moon:
        h = hist[m]; c, b, d = covered(m, usgs + nasa)
        dd = sorted(((float(np.linalg.norm(Z[m] - Z[s])), s) for s in comp))[:5]
        ex["patches"].append({"patch_id": m, "lat": h["lat"], "lon": h["lon"], "ps_x_m": h["x_m"], "ps_y_m": h["y_m"],
                              "features": {k: h["features"][k] for k in ["slope_median_30m", "slope_p90_30m", "slope_median_120m", "slope_median_480m", "roughness_median_480m"]},
                              "current_status": {"set": "USGS-29 union NASA test sites", "covered": bool(c), "value": round(d, 4) if d is not None else None},
                              "historical_A_status": {"set": "USGS-29", "covered": h["covered"], "distance": h["distance"], "nearest": h["nearest_site_name"],
                                                      "label": "historical (fingerprint A, T = 2.317)"},
                              "neighbours": [{"id": s, "name": labels[s], "set": sets[s], "distance": round(x, 4)} for x, s in dd]})
    web = ROOT / "web/data"; web.mkdir(parents=True, exist_ok=True)
    (web / "explorer.json").write_text(json.dumps(ex))
    with rasterio.open(ROOT / "data/raw/moon/ldem_80s_20m.lbl") as dsrc:
        rho = 182100.0
        win = rasterio.windows.from_bounds(-rho, -rho, rho, rho, dsrc.transform)
        n = 1820
        a = dsrc.read(1, window=win, out_shape=(n, n), resampling=Resampling.average).astype(float) * 0.5
    hs = hillshade(a, 2 * rho / n, 315, 30)
    plt.imsave(web / "lola_84S_hillshade.png", hs, cmap="gray", vmin=0, vmax=1)
    (web / "lola_84S_hillshade.json").write_text(json.dumps({"image": "lola_84S_hillshade.png", "crs": "LOLA polar stereographic (lat0 -90, lon0 0, R 1737.4 km)",
        "bounds_m": [-rho, -rho, rho, rho], "pixel_m": 2 * rho / n, "source": "LDEM_80S_20M (PDS), area-averaged, height = DN*0.5 m",
        "hillshade": "az 315, alt 30"}, indent=2))
    print("method", method, "T", T)
    print("Task1", json.dumps(t1["sets"]), "skipped", skipped)
    print("Report card", {k: v["covered_percent"] for k, v in card["sites"].items()})
    print("explorer.json bytes", (web / "explorer.json").stat().st_size)


if __name__ == "__main__":
    main(sys.argv[1])
