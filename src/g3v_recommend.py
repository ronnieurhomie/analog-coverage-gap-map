# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G3v recommendations (methods A, B, C) from 30 m data ONLY; writes results/g3v_recommendations.json (frozen)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint, slope_deg  # noqa: E402
from g3v_common import BINS, bin_counts, provides  # noqa: E402
from gate3_common import PIX, SCALES, vec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "data/processed/g3v"


def frozen_norm():
    P = np.load(ROOT / "data/processed/gate3_patches_30m.npz")
    M = np.stack([vec(fingerprint(P[k], PIX, SCALES)) for k in P.files])
    mu, sd = M.mean(0), M.std(0); sd[sd == 0] = 1
    gm = json.loads((ROOT / "results/gap_map.json").read_text())
    return mu, sd, float(gm["threshold_T"]), len(P.files)


def main():
    meta = json.loads((G / "extract_meta.json").read_text())
    mu, sd, T, npool = frozen_norm()
    sites = {sid: g["eligible_windows"] for sid, g in sorted(meta["site_groups"].items()) if g["eligible"]}
    win30 = {w: np.load(G / "sites" / f"{w}_30m.npy") for ws in sites.values() for w in ws}
    Zs = {w: (vec(fingerprint(p, PIX, SCALES)) - mu) / sd for w, p in win30.items()}
    Bs = {sid: provides(np.sum([bin_counts(slope_deg(win30[w].astype(float), PIX)) for w in ws], axis=0)) for sid, ws in sites.items()}
    out = {"T": T, "pool_size_for_norm": npool, "eligible_sites": list(sites), "n_eligible_sites": len(sites), "groups": []}
    for g in meta["groups"]:
        tn = g["targets"]
        t30 = {t: np.load(G / "targets" / f"{t}_30m.npy") for t in tn}
        Zt = {t: (vec(fingerprint(p, PIX, SCALES)) - mu) / sd for t, p in t30.items()}
        d = {(s, t): min(float(np.linalg.norm(Zs[w] - Zt[t])) for w in sites[s]) for s in sites for t in tn}
        # --- A ---
        unc, pickA, stepsA = set(tn), [], []
        while len(pickA) < 3 and unc:
            best = None
            for s in sites:
                if s in pickA:
                    continue
                gain = sum(d[(s, t)] < T for t in unc)
                md = float(np.mean([d[(s, t)] for t in unc]))
                key = (-gain, md, s)
                if best is None or key < best[0]:
                    best = (key, s, gain, md)
            if best is None or best[2] == 0:
                stepsA.append({"stop": "zero gain", "best_site": None if best is None else best[1]}); break
            pickA.append(best[1]); unc -= {t for t in unc if d[(best[1], t)] < T}
            stepsA.append({"pick": best[1], "gain": best[2], "mean_dist_uncovered": round(best[3], 4)})
        # --- B ---
        TC = np.sum([bin_counts(slope_deg(p.astype(float), PIX)) for p in t30.values()], axis=0)
        cov, pickB, stepsB = np.zeros(len(BINS), bool), [], []
        while len(pickB) < 3:
            best = None
            for s in sites:
                if s in pickB:
                    continue
                gain = int(TC[Bs[s] & ~cov].sum())
                key = (-gain, s)
                if best is None or key < best[0]:
                    best = (key, s, gain)
            if best is None or best[2] == 0:
                stepsB.append({"stop": "zero gain"}); break
            pickB.append(best[1]); cov |= Bs[best[1]]
            stepsB.append({"pick": best[1], "gain_30m_px": best[2]})
        # --- C ---
        rng = np.random.default_rng(20261114 + g["group"]); sl = list(sites)
        pickC = [[sl[i] for i in rng.choice(len(sl), 3, replace=False)] for _ in range(200)]
        out["groups"].append({"group": g["group"], "targets": tn, "A_picks": pickA, "A_steps": stepsA,
                              "A_note": None if pickA else "no coverage meeting the threshold",
                              "B_picks": pickB, "B_steps": stepsB, "C_combinations": pickC,
                              "A_min_dist_per_target": {t: round(min(d[(s, t)] for s in sites), 4) for t in tn}})
    (ROOT / "results/g3v_recommendations.json").write_text(json.dumps(out, indent=2))
    for g in out["groups"]:
        print(g["group"], "A:", g["A_picks"] or g["A_note"], "| B:", g["B_picks"], "| min d:", g["A_min_dist_per_target"])


if __name__ == "__main__":
    main()
