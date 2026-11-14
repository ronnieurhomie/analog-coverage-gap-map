# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Gate 2 figure: Mars sand + top 5 Earth candidates (A primary, then B) + Dumont + negative control."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import hillshade

ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT / "results/gate2_ranking.json").read_text())
P = np.load(ROOT / "data/processed/gate2_patches_2m.npz")
rows = [("A_primary_zscore", "Method A (z-score Euclidean)"), ("B_dinov2_cosine", "Method B (DINOv2 cosine)")]
fig, axs = plt.subplots(2, 8, figsize=(22, 6.6))
for (key, title), ax_row in zip(rows, axs):
    rk = r[key]["ranking"]; by = {e["name"]: e for e in rk}
    items = [("mars_sand", f"MARS SAND (Bagnold)\nquery")]
    items += [(e["name"], f"#{e['rank']} {e['name'].replace('grid_', '')}\n{e['lat']:.4f}, {e['lon']:.4f}  d={e['dist']:.3f}") for e in rk[:5]]
    for n, lab in [("dumont", "DUMONT"), ("avawatz_negctrl", "NEG CTRL Avawatz")]:
        e = by[n]; items.append((n, f"{lab} #{e['rank']}/{len(rk)}\nd={e['dist']:.3f}"))
    for ax, (n, lab) in zip(ax_row, items):
        z = P[n]; hs = hillshade(np.where(np.isfinite(z), z, np.nanmean(z)), 2.0, 315.0, 30.0)
        ax.imshow(hs, cmap="gray", vmin=0, vmax=1, extent=[0, 256, 0, 256]); ax.set_title(lab, fontsize=8)
        ax.set_xticks([0, 128, 256]); ax.set_yticks([0, 128, 256]); ax.tick_params(labelsize=6)
    ax_row[0].set_ylabel(title, fontsize=9)
fig.suptitle("Gate 2 ranking vs Mars sand (all panels 256 m, 2 m grid, hillshade az 315 alt 30). "
             f"Pre-registered: Dumont in top 10% of {r['n_candidates']} -> rank A = {r['A_primary_zscore']['dumont_rank']} (FAIL)", fontsize=10)
fig.tight_layout(); fig.savefig(ROOT / "results/gate2_ranking.png", dpi=120); print("ok")
