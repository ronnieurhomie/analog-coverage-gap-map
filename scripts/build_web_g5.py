# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G5 display data (run after scripts/build_web_data.py and scripts/g5_increment.py). No new analysis:

* the 10 gap-covering global candidates become selectable in the panel: features and z-distances are recomputed with the
  frozen method from their existing COP30 windows, and every listed (candidate, Moon patch) pair is asserted to have d < T,
  matching results/global_search.json; hillshades rendered like all other windows;
* neighbour-pool labels (Mojave grid entries are not in any comparison set);
* showcase lookup for docs/showcase.md: nearest site in K (all usable USGS + 3 NASA) for one Moon patch.
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from fingerprint import fingerprint  # noqa: E402
from g3v_recommend import frozen_norm  # noqa: E402
from gate3_common import PIX, SCALES, earth_patch, vec  # noqa: E402
from build_web_data import render  # noqa: E402

J = lambda p: json.loads((ROOT / p).read_text())


def main():
    disp = J("web/data/display.json"); gs = J("results/global_search.json"); inc = J("results/g5_candidate_increment.json")
    mu, sd, T, _ = frozen_norm()
    z = lambda v: (np.array(v) - mu) / sd
    gp = {p["id"]: p for p in gs["patches"]}
    cand_ids = [r["id"] for r in inc["candidates"]]
    per_patch = {}
    for cid in cand_ids:
        p = gp[cid]
        arr = earth_patch(str(ROOT / p["file"]), p["lat"], p["lon"])
        f = vec(fingerprint(arr, PIX, SCALES)); disp["features"][cid] = [round(float(x), 4) for x in f]
        disp["earth_names"][cid] = {"name": f"global candidate {cid} ({p['lat']:.3f}, {p['lon']:.3f})", "set": "global candidate (exploratory)"}
        render(arr, ROOT / "web/img/earth" / f"{cid}.png")
        for m in p["covers_current_gap_patches"]:
            d = float(np.linalg.norm(z(disp["features"][m]) - z(f)))
            assert d < T, (cid, m, d)
            per_patch.setdefault(m, []).append({"id": cid, "distance": round(d, 4), "below_T": True,
                                                "beyond_K": m in set(next(r for r in inc["candidates"] if r["id"] == cid)["N_ids"])})
    pool_label = {}
    for p in disp["patches"]:
        p["candidates"] = sorted(per_patch.get(p["id"], []), key=lambda c: c["distance"])
        assert {c["id"] for c in p["candidates"]} == set(p["global_candidates_covering"]), p["id"]
        for n in p["neighbours"]:
            if n["set"].startswith("Mojave"):
                n["set"] = ("Gate 2 test grid (Dumont Dunes; also a NASA test site)" if n["id"] == "mojave_dumont"
                            else "Gate 2 test grid — not in any comparison set")
            pool_label[n["id"]] = n["set"]
        p["status"]["K"] = p["id"] in set(inc["K"]["covered_ids"])
    disp["sets"]["K"] = {"label": "all usable USGS analog sites ∪ 3 NASA test sites (K)", "covered": inc["K"]["covered"], "gap": inc["K"]["gap"],
                         "denominator": 145, "nature": "post-hoc set operation, exploratory", "source": "results/g5_candidate_increment.json"}
    disp["increment"] = {k: inc[k] for k in ["candidates", "g00094", "nature", "method", "status"]}
    disp["neighbour_pool"] = "Neighbours are drawn from USGS-29, the 3 NASA test sites and the 64-window Gate 2 test grid (Mojave); the Gate 2 grid is not part of any comparison set."
    (ROOT / "web/data/display.json").write_text(json.dumps(disp, separators=(",", ":")))

    # showcase: in g00094's N set, smallest d to g00094; nearest site in K
    g = "g00094"
    nset = inc["g00094"]["still_gap_under_K"]
    dd = {m: next(c["distance"] for c in per_patch[m] if c["id"] == g) for m in nset}
    show = min(dd, key=dd.get)
    recs = J("data/processed/analog_sites.json")
    sel = {s["record_index"]: ROOT / f"data/raw/earth_cop30/sites/{s['site_id']}_cop30.tif" for s in J("results/known_sites_selection.json")["sites"]}
    best = (1e9, None)
    for i, r in enumerate(recs):
        f = sel.get(i, ROOT / f"data/raw/earth_cop30/usgs_all/rec{i:03d}_cop30.tif")
        if not f.exists():
            continue
        a = earth_patch(str(f), r["Lat"], r["Lon"])
        if np.isfinite(a).mean() < 0.95:
            continue
        d = float(np.linalg.norm(z(disp["features"][show]) - z(vec(fingerprint(a, PIX, SCALES)))))
        best = min(best, (d, f"USGS: {r['Name']} ({r['AnalogType']})"))
    for k in ["nasa_dumont_dunes", "nasa_moses_lake_sand_dunes", "nasa_haughton_crater"]:
        if k in disp["features"]:
            d = float(np.linalg.norm(z(disp["features"][show]) - z(disp["features"][k])))
            best = min(best, (d, "NASA test site: " + k[5:].replace("_", " ")))
    assert best[0] >= T, "showcase patch should be a gap under K"
    out = {"showcase_patch": show, "d_to_g00094": dd[show], "d_to_g00094_all_N": dd, "nearest_in_K": best[1], "d_nearest_in_K": round(best[0], 4), "T": T}
    (ROOT / "docs/showcase_numbers.json").write_text(json.dumps(out, indent=2))
    print(out)


if __name__ == "__main__":
    main()
