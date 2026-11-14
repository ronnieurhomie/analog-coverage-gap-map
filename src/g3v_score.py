# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G3v scoring at 2 m (after recommendations are frozen) and classification; writes results/g3v_results.json + figure."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import slope_deg  # noqa: E402
from g3v_common import BINS, bin_counts, coverage  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "data/processed/g3v"


def main(start: str, end: str):
    meta = json.loads((G / "extract_meta.json").read_text())
    rec = json.loads((ROOT / "results/g3v_recommendations.json").read_text())
    sites = {sid: g["eligible_windows"] for sid, g in meta["site_groups"].items() if g["eligible"]}
    SC = {sid: np.sum([bin_counts(slope_deg(np.load(G / "sites" / f"{w}_2m.npy").astype(float), 2.0)) for w in ws], axis=0)
          for sid, ws in sites.items()}
    rows = []
    for g in rec["groups"]:
        TC = [bin_counts(slope_deg(np.load(G / "targets" / f"{t}_2m.npy").astype(float), 2.0)) for t in g["targets"]]
        a = coverage(TC, [SC[s] for s in g["A_picks"]])
        b = coverage(TC, [SC[s] for s in g["B_picks"]])
        rc = [coverage(TC, [SC[s] for s in combo]) for combo in g["C_combinations"]]
        rows.append({"group": g["group"], "A": round(a, 4), "B": round(b, 4), "random_median": round(float(np.median(rc)), 4),
                     "random_p95": round(float(np.percentile(rc, 95)), 4), "A_picks": g["A_picks"], "B_picks": g["B_picks"],
                     "A_note": g["A_note"], "target_bin_area_px_2m": np.sum(TC, axis=0).tolist()})
    n = len(rows)
    step1 = {"fewer_than_8_groups": n < 8,
             "formal_ceiling": sum(r["random_median"] >= 0.95 for r in rows) >= 7,
             "n_groups_random_median_ge_95": sum(r["random_median"] >= 0.95 for r in rows)}
    inconclusive = step1["fewer_than_8_groups"] or step1["formal_ceiling"]
    diff = [100 * (r["A"] - r["B"]) for r in rows]
    cond = {"A_beats_B_groups": sum(r["A"] > r["B"] for r in rows),
            "median_paired_A_minus_B_points": round(float(np.median(diff)), 2) if diff else None,
            "groups_A_worse_than_B_by_gt_10_points": sum(x < -10 for x in diff),
            "A_above_random_p95_groups": sum(r["A"] > r["random_p95"] for r in rows),
            "B_above_random_p95_groups": sum(r["B"] > r["random_p95"] for r in rows)}
    if inconclusive:
        branch = "INCONCLUSIVE"
    elif (cond["A_beats_B_groups"] >= 7 and cond["median_paired_A_minus_B_points"] >= 10
          and cond["groups_A_worse_than_B_by_gt_10_points"] == 0 and cond["A_above_random_p95_groups"] >= 7):
        branch = "PASS_FULL"
    elif cond["B_above_random_p95_groups"] >= 7:
        branch = "BASELINE_ONLY"
    else:
        branch = "NO_SUPPORT"
    out = {"start": start, "end": end, "n_groups": n, "groups": rows, "step1": step1, "step1_inconclusive": inconclusive,
           "step2_conditions": cond, "branch": branch,
           "metric": "metre-scale slope-condition coverage (share of the 3 targets' pooled valid 2 m area whose slope bin is provided by >= 1 selected site; provides = >= 5% of site valid 2 m area)",
           "nature": "current; new spatial holdout in the same region (not external validation); prototype acceptance criteria, not NASA engineering standards",
           "bins_deg": BINS}
    (ROOT / "results/g3v_results.json").write_text(json.dumps(out, indent=2))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(n)
    ax.bar(x - 0.2, [100 * r["A"] for r in rows], 0.4, label="A full fingerprint (T=2.317)")
    ax.bar(x + 0.2, [100 * r["B"] for r in rows], 0.4, label="B slope-only baseline")
    ax.scatter(x, [100 * r["random_median"] for r in rows], c="k", marker="_", s=300, label="random median (200)", zorder=3)
    ax.scatter(x, [100 * r["random_p95"] for r in rows], c="r", marker="_", s=300, label="random 95th pct", zorder=3)
    ax.set_xticks(x); ax.set_xticklabels([f"g{r['group']}" for r in rows]); ax.set_ylim(0, 105)
    ax.set_ylabel("metre-scale slope-condition coverage (%)"); ax.legend(fontsize=8, loc="lower right")
    ax.set_title(f"G3v per-group results (8 groups x 3 targets, 1.92 km windows). Branch: {branch}", fontsize=10)
    fig.tight_layout(); fig.savefig(ROOT / "results/g3v_groups.png", dpi=120)
    for r in rows:
        print(r["group"], "A", r["A"], "B", r["B"], "rand med", r["random_median"], "p95", r["random_p95"], r["A_picks"], r["B_picks"])
    print("step1", step1, "\nstep2", cond, "\nbranch", branch)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
