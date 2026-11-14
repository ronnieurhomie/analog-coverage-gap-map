# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Gate 3: compute the Moon-to-known-Earth-analog gap map exactly as in results/gap_preregistration.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import reproject
from rasterio.windows import from_bounds
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint, hillshade, slope_deg  # noqa: E402
from gate3_common import FEATURE_NAMES, NPX, PATCH_M, PIX, ROOT, SCALES, earth_patch, vec  # noqa: E402

LBL = ROOT / "data/raw/moon/ldem_80s_20m.lbl"
COP_AREA = ROOT / "data/raw/earth_cop30/cop30_gate2_area.tif"


def moon_patch(d, x, y):
    m = 120.0
    w = from_bounds(x - PATCH_M / 2 - m, y - PATCH_M / 2 - m, x + PATCH_M / 2 + m, y + PATCH_M / 2 + m, d.transform)
    w = w.round_offsets().round_lengths()
    dn = d.read(1, window=w)
    if d.nodata is not None and np.any(dn == d.nodata):
        return None
    h = dn.astype(np.float32) * 0.5  # label: HEIGHT = DN * SCALING_FACTOR (0.5 m)
    dst = np.full((NPX, NPX), np.nan, dtype=np.float32)
    reproject(h, dst, src_transform=d.window_transform(w), src_crs=d.crs,
              dst_transform=Affine(PIX, 0, x - PATCH_M / 2, 0, -PIX, y + PATCH_M / 2), dst_crs=d.crs,
              src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.average)
    return None if np.isnan(dst).any() else dst


def flat_frac(p):
    return float(np.mean(slope_deg(p.astype(float), PIX) < 0.1))


def main():
    pre = json.loads((ROOT / "results/gap_preregistration.json").read_text())
    moon_spec = json.loads((ROOT / "results/moon_patches.json").read_text())
    sites = json.loads((ROOT / "results/known_sites_selection.json").read_text())["sites"]
    fetch = json.loads((ROOT / "data/processed/meta/gate3_site_fetch.json").read_text())
    mojave = json.loads((ROOT / "results/candidates.json").read_text())["candidates"]

    P, kind, info = {}, {}, {}
    # Mojave reference
    for c in mojave:
        k = f"mojave_{c['name']}"; P[k] = earth_patch(str(COP_AREA), c["lat"], c["lon"]); kind[k] = "mojave"
        info[k] = {"lat": c["lat"], "lon": c["lon"]}
    # Known sites (+ NASADEM check)
    dropped, nas_pairs = [], []
    for s in sites:
        f = fetch.get(s["site_id"], {}).get("cop30", {})
        if f.get("status") not in ("ok", "exists"):
            dropped.append({"site_id": s["site_id"], "name": s["name"], "reason": f"COP30 {f.get('status')}"}); continue
        p = earth_patch(str(ROOT / f["file"]), s["lat"], s["lon"])
        if np.isnan(p).any():
            dropped.append({"site_id": s["site_id"], "name": s["name"], "reason": "NaN in COP30 patch"}); continue
        k = s["site_id"]; P[k] = p; kind[k] = "site"
        info[k] = {"name": s["name"], "type": s["type"], "lat": s["lat"], "lon": s["lon"], "flags": list(s["flags"]),
                   "flat_fraction_30m": round(flat_frac(p), 3)}
        if info[k]["flat_fraction_30m"] > 0.5:
            info[k]["flags"].append("flat/water-like: >50% of 30 m cells have slope < 0.1 deg")
        nz = fetch[s["site_id"]].get("nasadem", {})
        if nz.get("status") == "ok":
            stem = nz["granule"].replace("NASADEM_HGT_", "")
            q = earth_patch(f"/vsizip/{ROOT / nz['file']}/{stem}.hgt", s["lat"], s["lon"], src_nodata=-32768)
            if not np.isnan(q).any():
                nas_pairs.append((k, vec(fingerprint(q, PIX, SCALES))))
    # Moon
    moon_ok, moon_skip = [], []
    with rasterio.open(LBL) as d:
        for m in moon_spec["patches"]:
            p = moon_patch(d, m["x_m"], m["y_m"])
            if p is None:
                moon_skip.append(m["patch_id"]); continue
            P[m["patch_id"]] = p; kind[m["patch_id"]] = "moon"; info[m["patch_id"]] = m; moon_ok.append(m["patch_id"])

    V = {k: vec(fingerprint(p, PIX, SCALES)) for k, p in P.items()}
    keys = list(V); M = np.stack([V[k] for k in keys])
    mu, sd = M.mean(0), M.std(0); sd[sd == 0] = 1
    Z = {k: (V[k] - mu) / sd for k in keys}
    moj = [k for k in keys if kind[k] == "mojave"]; site_k = [k for k in keys if kind[k] == "site"]
    nn_moj = [min(np.linalg.norm(Z[a] - Z[b]) for b in moj if b != a) for a in moj]
    T = float(np.percentile(nn_moj, 90))

    rows = []
    for m in moon_ok:
        dists = {s: float(np.linalg.norm(Z[m] - Z[s])) for s in site_k}
        best = min(dists, key=dists.get)
        rows.append({"patch_id": m, "lat": info[m]["lat"], "lon": info[m]["lon"], "x_m": info[m]["x_m"], "y_m": info[m]["y_m"],
                     "nearest_site_id": best, "nearest_site_name": info[best]["name"], "distance": round(dists[best], 4),
                     "covered": dists[best] <= T,
                     "features": {n: round(float(v), 4) for n, v in zip(FEATURE_NAMES, V[m])}})
    # POST-HOC sensitivity (results/gap_sensitivity_rule.json): exclude flat/water-like sites
    surf = [s for s in site_k if not any(f.startswith("flat/water-like") for f in info[s]["flags"])]
    for r in rows:
        dd = {s: float(np.linalg.norm(Z[r["patch_id"]] - Z[s])) for s in surf}
        b = min(dd, key=dd.get)
        r["sensitivity_nearest_site_name"] = info[b]["name"]; r["sensitivity_distance"] = round(dd[b], 4)
        r["sensitivity_covered"] = dd[b] <= T
    sens = {"label": "POST-HOC SENSITIVITY CHECK (not the headline)", "n_sites_used": len(surf),
            "sites_excluded": [info[s]["name"] for s in site_k if s not in surf],
            "gap_fraction_percent": round(100.0 * sum(not r["sensitivity_covered"] for r in rows) / len(rows), 2) if rows else None}
    gap = [r for r in rows if not r["covered"]]
    X = 100.0 * len(gap) / len(rows) if rows else float("nan")
    fi = {n: FEATURE_NAMES.index(n) for n in ["slope_median_30m", "slope_p90_120m", "roughness_median_480m"]}
    summ = lambda grp: {n: (round(float(np.median([V[r["patch_id"]][i] for r in grp])), 3) if grp else None) for n, i in fi.items()}
    site_summ = {n: round(float(np.median([V[k][i] for k in site_k])), 3) for n, i in fi.items()}
    nas = None
    if nas_pairs:
        rhos = [float(spearmanr(V[k], v)[0]) for k, v in nas_pairs]
        nas = {"n_sites": len(nas_pairs), "spearman_feature_vectors_cop30_vs_nasadem": {k: round(r, 3) for (k, _), r in zip(nas_pairs, rhos)},
               "median_rho": round(float(np.median(rhos)), 3)}
    out = {"preregistration": pre, "threshold_T": round(T, 4), "n_moon_valid": len(rows), "n_moon_skipped_nodata": len(moon_skip),
           "moon_skipped": moon_skip, "n_known_sites_used": len(site_k), "known_sites_dropped": dropped,
           "known_sites": {k: info[k] for k in site_k}, "gap_fraction_percent": round(X, 2), "n_gap": len(gap),
           "terrain_medians": {"gap": summ(gap), "covered": summ([r for r in rows if r["covered"]]), "known_sites": site_summ},
           "nearest_site_counts": {info[s]["name"]: sum(r["nearest_site_id"] == s for r in rows) for s in site_k},
           "nasadem_check": nas, "sensitivity_post_hoc": sens, "patches": rows}
    (ROOT / "results/gap_map.json").write_text(json.dumps(out, indent=2))
    np.savez_compressed(ROOT / "data/processed/gate3_patches_30m.npz", **P)

    # Figure
    top3 = sorted(rows, key=lambda r: -r["distance"])[:3]
    fig = plt.figure(figsize=(18, 9))
    ax = fig.add_axes([0.03, 0.08, 0.42, 0.84])
    xs = np.array([r["x_m"] for r in rows]) / 1000; ys = np.array([r["y_m"] for r in rows]) / 1000
    ds = np.array([r["distance"] for r in rows]); cov = np.array([r["covered"] for r in rows])
    sc = ax.scatter(xs, ys, c=ds, cmap="viridis", s=70, marker="s")
    ax.scatter(xs[~cov], ys[~cov], s=120, marker="s", facecolors="none", edgecolors="red", linewidths=1.5, label=f"gap (d > T = {T:.2f})")
    for r in top3:
        ax.annotate(r["patch_id"], (r["x_m"] / 1000, r["y_m"] / 1000), color="red", fontsize=8, xytext=(4, 4), textcoords="offset points")
    th = np.linspace(0, 2 * np.pi, 400); rho = moon_spec["rho_84S_m"] / 1000
    ax.plot(rho * np.cos(th), rho * np.sin(th), "k--", lw=0.8)
    ax.plot(0, 0, "k+", ms=10); ax.set_aspect("equal"); ax.legend(loc="lower left", fontsize=8)
    ax.set_xlabel("polar stereographic x (km)"); ax.set_ylabel("y (km)")
    ax.set_title(f"South-polar Artemis candidate zone (84-90 S), {len(rows)} patches of 1.92 km\n"
                 f"colour = z-distance to nearest known Earth analog site; gap = {X:.1f}%", fontsize=10)
    plt.colorbar(sc, ax=ax, shrink=0.7, label="distance (z units)")
    for i, r in enumerate(top3):
        for j, k in enumerate([r["patch_id"], r["nearest_site_id"]]):
            a = fig.add_axes([0.52 + j * 0.23, 0.68 - i * 0.31, 0.2, 0.27])
            p = P[k]; a.imshow(hillshade(p.astype(float), PIX, 315, 30), cmap="gray", vmin=0, vmax=1, extent=[0, 1.92, 0, 1.92])
            lab = (f"MOON {k} ({r['lat']:.2f}, {r['lon']:.1f}) d={r['distance']:.2f}" if j == 0
                   else f"nearest known site: {info[k]['name']}")
            a.set_title(lab, fontsize=8); a.tick_params(labelsize=6)
    fig.text(0.52, 0.02, "Hillshades: 1.92 km squares, 30 m grid, sun az 315 alt 30, same scale (km).", fontsize=8)
    fig.savefig(ROOT / "results/gap_map.png", dpi=110)
    print(json.dumps({k: out[k] for k in ["threshold_T", "n_moon_valid", "n_moon_skipped_nodata", "n_known_sites_used", "known_sites_dropped",
                                          "gap_fraction_percent", "n_gap", "terrain_medians", "nasadem_check", "sensitivity_post_hoc"]}, indent=1))
    print("top3:", [(r["patch_id"], r["lat"], r["lon"], r["distance"], r["nearest_site_name"]) for r in top3])
    print("nearest-site counts:", {k: v for k, v in out["nearest_site_counts"].items() if v})


if __name__ == "__main__":
    main()
