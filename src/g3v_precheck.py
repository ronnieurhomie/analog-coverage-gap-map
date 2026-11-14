# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G3v ceiling pre-check on the old 64 patches, exactly as results/g3v_precheck_rule.json."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import slope_deg
from g3v_common import bin_counts, coverage

ROOT = Path(__file__).resolve().parents[1]
cands = json.loads((ROOT / "results/candidates.json").read_text())["candidates"]
names = sorted(c["name"] for c in cands)
C = {c["name"]: bin_counts(slope_deg(np.load(ROOT / c["file"]).astype(float), 2.0)) for c in cands}
perm = list(np.random.default_rng(20261114).permutation(names))
groups = [perm[i * 3:(i + 1) * 3] for i in range(8)]
pool = perm[24:]
res = []
for gi, g in enumerate(groups):
    rng = np.random.default_rng(20261114 + gi)
    covs = [coverage([C[t] for t in g], [C[pool[j]] for j in rng.choice(len(pool), 3, replace=False)]) for _ in range(200)]
    res.append({"group": gi, "targets": g, "random_median": round(float(np.median(covs)), 4),
                "random_p95": round(float(np.percentile(covs, 95)), 4), "random_min": round(float(np.min(covs)), 4)})
n_ceiling = sum(r["random_median"] >= 0.95 for r in res)
out = {"pool": pool, "groups": res, "n_groups_random_median_ge_95": n_ceiling, "stop": n_ceiling >= 7}
(ROOT / "results/g3v_precheck_results.json").write_text(json.dumps(out, indent=2))
for r in res: print(r["group"], r["targets"], r["random_median"], r["random_p95"], r["random_min"])
print("groups with random median >= 95%:", n_ceiling, "/ 8 -> stop" if out["stop"] else "-> continue")
