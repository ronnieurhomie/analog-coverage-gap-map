# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Task 8: regenerate front-end data once with Task 3 candidates and the Task 7 case (Task 4 not run)."""
import datetime as dt, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import g3b_moon
g3b_moon.main("INCONCLUSIVE")  # rebuild Task 1/2/5/6 outputs from scratch (same inputs, same method)
ex = json.loads((ROOT / "web/data/explorer.json").read_text())
gs = json.loads((ROOT / "results/global_search.json").read_text())
case = json.loads((ROOT / "results/candidate_case.json").read_text())
a2 = json.loads((ROOT / "results/task2_all_usgs.json").read_text())
top = sorted(gs["patches"], key=lambda k: (-k["n_covered"], k["id"]))[:10]
ex["global_candidates"] = {"nature": "exploratory (Task 3; G3v INCONCLUSIVE)", "rule": "results/global_search_preregistration.json (incl. DEM-source amendment)",
                           "processed": gs["processed_kept"], "drawn": gs["drawn"], "skipped": gs["skipped"],
                           "contribution_definition": "number of current gap Moon patches (set USGS-29 union NASA test sites, fingerprint A, T = 2.317) covered by the patch alone; denominator 145",
                           "top10": [{k: c[k] for k in ["id", "lat", "lon", "n_covered", "novelty", "nearest_known", "nearest_known_km", "ndvi_mean4"]} for c in top]}
ex["candidate_case"] = {"file": "results/candidate_case.json", "figure": "results/candidate_case.png", "id": case["candidate"]["id"], "novelty": case["novelty"]["flag"]}
ex["portfolio"] = {"included": False, "reason": "Task 4 not run: G3v branch INCONCLUSIVE (portfolio allowed only under PASS_FULL or BASELINE_ONLY)"}
cov = {}
for c in gs["patches"]:
    for m in c["covers_current_gap_patches"]:
        cov.setdefault(m, []).append(c["id"])
for p in ex["patches"]:
    p["global_candidates_covering"] = sorted(cov.get(p["patch_id"], []))
ex["method_info"]["robustness_post_hoc"] = {"all_usgs_190_sites_gap_percent": a2["gap_percent"], "denominator": 145, "nature": "post-hoc, exploratory"}
ex["method_info"]["generated"] = dt.datetime.now().isoformat(timespec="seconds")
(ROOT / "web/data/explorer.json").write_text(json.dumps(ex))
rc = json.loads((ROOT / "results/report_card.json").read_text())
rc["exploratory_candidate"] = {"id": case["candidate"]["id"], "lat": case["candidate"]["lat"], "lon": case["candidate"]["lon"],
                               "not_a_NASA_test_site": True, "covers_current_gap_patches": case["coverage_contribution"]["n_gap_patches_covered"],
                               "denominator": 145, "novelty": case["novelty"]["flag"], "nature": "exploratory"}
(ROOT / "results/report_card.json").write_text(json.dumps(rc, indent=2))
print("explorer.json bytes", (ROOT / "web/data/explorer.json").stat().st_size, "| patches with >=1 global candidate:", sum(1 for p in ex["patches"] if p["global_candidates_covering"]))
