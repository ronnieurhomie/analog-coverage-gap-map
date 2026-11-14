# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""V1: Earth-only retrieval test, as pre-registered in results/v1_preregistration.json."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate2_candidates as gc  # noqa: E402
from fingerprint import fingerprint, hillshade  # noqa: E402
from gate2_rank import SCALES, embed_all, vec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/v1_positives"


def main():
    pre = json.loads((ROOT / "results/v1_preregistration.json").read_text())
    cands = json.loads((ROOT / "results/candidates.json").read_text())["candidates"]
    OUT.mkdir(parents=True, exist_ok=True)
    patches, meta = {}, {}
    for c in cands:
        patches[c["name"]] = np.load(ROOT / c["file"]); meta[c["name"]] = (c["lat"], c["lon"])
    pos = list(pre["positives"])
    for n in pos:
        la, lo = pre["positives"][n]["lat"], pre["positives"][n]["lon"]
        f = OUT / f"{n}.npy"
        if f.exists():
            p, v = np.load(f), None
        else:
            x, y = gc.to_utm.transform(lo, la)
            p, tiles, v = gc.read_patch(x, y)
            if p is None or v < gc.MIN_VALID:
                raise RuntimeError(f"positive {n} invalid ({v})")
            np.save(f, p.astype(np.float32))
        patches[n] = p; meta[n] = (la, lo)
    names = list(patches)
    N = len(names); others = N - 1
    thr_ceil, thr_floor = math.ceil(0.1 * others), math.floor(0.1 * others)

    V = {k: vec(fingerprint(patches[k], 2.0, SCALES)) for k in names}
    M = np.stack([V[k] for k in names]); mu, sd = M.mean(0), M.std(0); sd[sd == 0] = 1
    Z = {k: (V[k] - mu) / sd for k in names}
    distA = lambda a, b: float(np.linalg.norm(Z[a] - Z[b]))
    emb = embed_all(patches)
    distB = lambda a, b: float(1 - emb[a] @ emb[b])

    res = {"n_patches": N, "ranked_list_length": others, "thr_ceil": thr_ceil, "thr_floor": thr_floor, "methods": {}}
    for mname, dist in [("A_zscore", distA), ("B_dinov2", distB)]:
        table, all_r, all_r_dum = [], [], []
        for q in pos:
            order = sorted((k for k in names if k != q), key=lambda k: dist(q, k))
            rk = {k: i + 1 for i, k in enumerate(order)}
            row = {"query": q, "ranks_of_other_positives": {o: rk[o] for o in pos if o != q},
                   "rank_of_gnis_dumont": rk["dumont"], "top5": [(k, round(dist(q, k), 3)) for k in order[:5]]}
            table.append(row); all_r += list(row["ranks_of_other_positives"].values())
            all_r_dum += list(row["ranks_of_other_positives"].values()) + [rk["dumont"]]
        med = float(np.median(all_r))
        res["methods"][mname] = {"table": table, "median_rank_other_positives": med,
                                 "pass_ceil": med <= thr_ceil, "pass_floor": med <= thr_floor,
                                 "median_incl_gnis_dumont": float(np.median(all_r_dum))}
    (ROOT / "results/v1_results.json").write_text(json.dumps(res, indent=2))

    # contact sheet: each positive as query (row) -> its top 6 under A
    fig, axs = plt.subplots(len(pos), 7, figsize=(17, 2.6 * len(pos)))
    for r_, q in enumerate(pos):
        order = sorted((k for k in names if k != q), key=lambda k: distA(q, k))[:6]
        for c_, k in enumerate([q] + order):
            z = patches[k]; ax = axs[r_, c_]
            ax.imshow(hillshade(np.where(np.isfinite(z), z, np.nanmean(z)), 2.0), cmap="gray", vmin=0, vmax=1)
            ax.set_xticks([]); ax.set_yticks([])
            lab = f"QUERY {q}" if c_ == 0 else f"#{c_} {k.replace('grid_', '')}{' *' if k in pos else ''}\nd={distA(q, k):.2f}"
            ax.set_title(lab, fontsize=8, color=("red" if (c_ and k in pos) else "black"))
    A = res["methods"]["A_zscore"]
    fig.suptitle(f"V1 retrieval, Method A (z-score). Red * = another positive. Median rank of other positives = {A['median_rank_other_positives']} "
                 f"(threshold {thr_ceil}; {'PASS' if A['pass_ceil'] else 'FAIL'}). All panels 256 m, 2 m grid.", fontsize=10)
    fig.tight_layout(); fig.savefig(ROOT / "results/v1_retrieval.png", dpi=90)
    for m, v in res["methods"].items():
        print(m, "median", v["median_rank_other_positives"], "pass_ceil", v["pass_ceil"], "pass_floor", v["pass_floor"], "incl GNIS", v["median_incl_gnis_dumont"])
        for row in v["table"]:
            print("  ", row["query"], row["ranks_of_other_positives"], "GNIS dumont", row["rank_of_gnis_dumont"])


if __name__ == "__main__":
    main()
