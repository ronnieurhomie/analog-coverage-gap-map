# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Fingerprint card: Bagnold (mars_sand, masked to usable sand pixels) vs Dumont, per feature.

Rule (fixed before computing): rel = |a - b| / max(|a|, |b|); "similar" if rel <= 0.25, else "different".
Bagnold masking: 2 m cells with < 75 % usable (sand AND NOT facet, see src/gate2b_masked.py) set to NaN
before the standard fingerprint (src/fingerprint.py, unchanged).
"""
import json, sys
from pathlib import Path
import numpy as np, rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint, to_common_grid
from gate2b_masked import DTM, THR, build_masks
from gate2_rank import SCALES

ROOT = Path(__file__).resolve().parents[1]
RULE = 0.25
usable, _, _ = build_masks()
spec = json.loads((ROOT / "data/processed/meta/gate2_patches.json").read_text())["patches"]["mars_sand"]
with rasterio.open(DTM) as d:
    tf = Transformer.from_crs(CRS(d.crs).geodetic_crs, d.crs, always_xy=True)
    x, y = tf.transform(spec["lon"], spec["lat"]); r = abs(d.transform.a)
    n = int(np.ceil(272 / r)); c0, r0 = ~d.transform * (x - 136, y + 136); w = Window(int(c0), int(r0), n, n)
    z = d.read(1, window=w); tr = d.window_transform(w)
    z2, gtr = to_common_grid(z, tr, d.crs, d.nodata, 2.0)
    u2, _ = to_common_grid(usable[w.row_off:w.row_off + n, w.col_off:w.col_off + n].astype(np.float32), tr, d.crs, None, 2.0)
cc, rr = ~gtr * (x, y); r_, c_ = int(round(rr - 64)), int(round(cc - 64))
zb = z2[r_:r_ + 128, c_:c_ + 128].astype(float); ub = u2[r_:r_ + 128, c_:c_ + 128] >= THR
zb[~ub] = np.nan
fb = fingerprint(zb, 2.0, SCALES)
fd = fingerprint(np.load(ROOT / "data/processed/candidates/dumont.npy"), 2.0, SCALES)
rows = []
for s in SCALES:
    for kind, stat, unit in [("slope_deg", "median", "deg"), ("slope_deg", "p90", "deg"), ("slope_deg", "iqr", "deg"), ("roughness_m", "median", "m")]:
        a = fb["scales"][str(s)][kind][stat]; b = fd["scales"][str(s)][kind][stat]
        if a is None or b is None:
            continue
        rel = abs(a - b) / max(abs(a), abs(b)) if max(abs(a), abs(b)) > 0 else 0.0
        rows.append({"feature": f"{kind.split('_')[0]}_{stat}_{int(s)}m", "unit": unit, "bagnold_masked": round(a, 4), "dumont": round(b, 4),
                     "difference_bagnold_minus_dumont": round(a - b, 4), "relative_difference": round(rel, 3),
                     "label": "similar" if rel <= RULE else "different"})
card = {"rule": f"relative_difference = |a-b| / max(|a|,|b|); 'similar' if <= {RULE}, else 'different'",
        "bagnold_patch": {"lat": spec["lat"], "lon": spec["lon"], "masked_valid_fraction_2m": round(float(np.isfinite(zb).mean()), 3),
                          "masking": "2 m cells with < 75% usable (sand AND NOT facet) excluded"},
        "dumont_patch": {"lat": 35.67863, "lon": -116.23156, "valid_fraction_2m": round(float(fd["valid_fraction"]), 3)},
        "n_features": len(rows), "n_similar": sum(r_["label"] == "similar" for r_ in rows), "features": rows}
(ROOT / "results/card_bagnold_vs_dumont.json").write_text(json.dumps(card, indent=2))
print(card["n_similar"], "/", card["n_features"], "similar; masked valid", card["bagnold_patch"]["masked_valid_fraction_2m"])
for r_ in rows: print(f"{r_['feature']:20s} {r_['bagnold_masked']:9.4f} {r_['dumont']:9.4f} {r_['relative_difference']:6.3f} {r_['label']}")
