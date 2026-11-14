# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G5 §1: net contribution of global candidates beyond the fuller known set K (set operations on existing outputs only)."""
import datetime as dt, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
J = lambda p: json.loads((ROOT / p).read_text())
disp = J("web/data/display.json"); gs = J("results/global_search.json"); cc = J("results/candidate_case.json")
a2 = J("results/task2_all_usgs.json"); t1 = J("results/task1_nasa_test_sites.json")
ids = [p["id"] for p in disp["patches"]]
allusgs = {p["id"] for p in disp["patches"] if p["status"]["allusgs"]}
nasa = {p["id"] for p in disp["patches"] if p["status"]["nasa"]}
union = {p["id"] for p in disp["patches"] if p["status"]["union"]}
checks = {"n_moon": len(ids) == 145, "allusgs_matches_result_file": len(allusgs) == a2["covered"],
          "nasa_matches_result_file": len(nasa) == t1["sets"]["a_NASA_test_sites_alone"]["covered"],
          "union_matches_result_file": len(union) == t1["sets"]["b_USGS29_union_NASA"]["covered"],
          "candidate_lists_inside_union_gap": all(set(p["covers_current_gap_patches"]) <= set(ids) - union for p in gs["patches"])}
out = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "nature": "exploratory, post-hoc (set operations on existing outputs; no new analysis)",
       "method": "fingerprint A, 19 frozen 30 m features, Gate 3 pooled normalisation, covered if z-distance < T = 2.317 (unchanged)",
       "denominator": 145, "consistency_checks": checks}
if not all(checks.values()):
    out["status"] = "net contribution not verified"
else:
    K = allusgs | nasa; gapK = set(ids) - K
    out.update({"status": "verified",
      "sets": {"K": "all usable USGS Known Terrestrial Analog Sites records (190/192; per-patch flags rebuilt in G4 with the frozen method, total 85) UNION the 3 included NASA test sites (per-patch flags from results/report_card.json), de-duplicated by Moon patch",
               "gap_set_of_candidate_lists": "USGS-29 UNION 3 NASA test sites (current-method gaps, 85 patches; results/global_search.json)"},
      "K": {"covered": len(K), "gap": len(gapK), "denominator": 145, "covered_ids": sorted(K)}})
    g13 = cc["coverage_contribution"]["covered_patch_ids"]
    out["g00094"] = {"listed_13": g13, "still_gap_under_K": sorted(set(g13) & gapK), "N": len(set(g13) & gapK),
                     "covered_under_K_already": sorted(set(g13) & K)}
    rows = []
    for p in sorted(gs["patches"], key=lambda k: (-k["n_covered"], k["id"])):
        if p["n_covered"] == 0: continue
        s = set(p["covers_current_gap_patches"])
        rows.append({"id": p["id"], "lat": p["lat"], "lon": p["lon"], "novelty": p["novelty"], "covers_gap_union": len(s),
                     "N_beyond_K": len(s & gapK), "N_ids": sorted(s & gapK)})
    out["candidates"] = rows
(ROOT / "results/g5_candidate_increment.json").write_text(json.dumps(out, indent=2))
print(out.get("status"), checks)
if out["status"] == "verified":
    print("K covered", out["K"]["covered"], "gap", out["K"]["gap"]); print("g00094", out["g00094"])
    for r in out["candidates"]: print(r["id"], r["lat"], r["lon"], r["novelty"], r["covers_gap_union"], r["N_beyond_K"], r["N_ids"])
