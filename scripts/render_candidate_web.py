# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G5: web copy of the candidate figure with unclipped titles (same arrays, same hillshade; results/candidate_case.png unchanged)."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fingerprint import hillshade
from gate3_common import PIX, earth_patch

cc = json.loads((ROOT / "results/candidate_case.json").read_text())
gs = {p["id"]: p for p in json.loads((ROOT / "results/global_search.json").read_text())["patches"]}
P = np.load(ROOT / "data/processed/gate3_patches_30m.npz")
c = cc["candidate"]
panels = [(earth_patch(str(ROOT / gs[c["id"]]["file"]), c["lat"], c["lon"]), f"Earth {c['id']}\n{c['lat']:.3f}, {c['lon']:.3f} (Morocco)")]
for t in cc["comparison_targets"]:
    panels.append((P[t["patch_id"]], f"Moon {t['patch_id']}\nd = {t['distance']:.2f} (T = 2.32)"))
fig, axs = plt.subplots(1, 3, figsize=(12, 4.6), layout="constrained")
for ax, (a, lab) in zip(axs, panels):
    ax.imshow(hillshade(a.astype(float), PIX, 315, 30), cmap="gray", vmin=0, vmax=1, extent=[0, 1.92, 0, 1.92])
    ax.set_title(lab, fontsize=11); ax.set_xlabel("km")
fig.savefig(ROOT / "web/img/candidate_case_web.png", dpi=100)
print("ok")
