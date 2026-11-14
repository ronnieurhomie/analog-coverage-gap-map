# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""G4: copy existing result numbers (no new analysis) into web/data/results_summary.json, each with its source path,
and copy the figures the page shows into web/img/."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
J = lambda p: json.loads((ROOT / p).read_text())


def main():
    g2 = J("results/gate2_ranking.json")
    v1 = J("results/v1_results.json")
    g3v = J("results/g3v_results.json")
    t2 = J("results/task2_robustness.json")
    gs = J("results/global_search.json")
    cc = J("results/candidate_case.json")
    rc = J("results/report_card.json")
    pre1 = J("results/nasa_test_sites_preregistration.json")
    nov = {}
    for p in gs["patches"]:
        nov[p["novelty"]] = nov.get(p["novelty"], 0) + 1
    curve = {c["percentile"]: c for c in t2["threshold_sensitivity_USGS29"]}
    out = {
        "gate2": {"source": "results/gate2_ranking.json", "n_candidates": g2["n_candidates"],
                  "dumont_rank_A": g2["A_primary_zscore"]["dumont_rank"], "dumont_rank_secondary": g2["A_secondary_reldiff"]["dumont_rank"],
                  "dumont_rank_B": g2["B_dinov2_cosine"]["dumont_rank"], "threshold_rank_ceil": g2["top10pct_rank_threshold"], "pass": g2["pass_primary"]},
        "v1": {"source": "results/v1_results.json", "median_A": v1["methods"]["A_zscore"]["median_rank_other_positives"],
               "median_B": v1["methods"]["B_dinov2"]["median_rank_other_positives"], "threshold": v1["thr_ceil"],
               "list_length": v1["ranked_list_length"], "pass_A": v1["methods"]["A_zscore"]["pass_ceil"]},
        "g3v": {"source": "results/g3v_results.json", "branch": g3v["branch"], "groups": g3v["groups"], "step1": g3v["step1"],
                "step2_transparency_only": g3v["step2_conditions"], "start": g3v["start"], "end": g3v["end"],
                "ceiling_explanation": g3v["verification"]["ceiling_explanation"], "n_sites": 62, "n_windows": 64},
        "sensitivity": {"source": "results/task2_robustness.json", "points": {q: {"T": curve[q]["T"], "gap_percent": curve[q]["gap_percent_USGS29"],
                        "gap_n": round(curve[q]["gap_percent_USGS29"] * 145 / 100)} for q in (50, 90, 99)}, "registered_percentile": 90},
        "global": {"source": "results/global_search.json", "processed": gs["processed_kept"], "drawn": gs["drawn"], "skipped": gs["skipped"],
                   "novelty_counts": nov, "n_covering_any_gap": sum(p["n_covered"] > 0 for p in gs["patches"]),
                   "n_current_gap_patches": gs["n_current_gap_patches"]},
        "candidate": {"source": "results/candidate_case.json",
                      **{k: cc[k] for k in ["candidate", "coverage_contribution", "untested_conditions"]},
                      # free-text caveat/check fields are omitted here; the page states them in its own reviewed wording
                      "novelty": {k: cc["novelty"][k] for k in ["flag", "nearest_known", "nearest_known_km"]}},
        "report_card": {"source": "results/report_card.json", "sites": {k: {kk: v[kk] for kk in ["moon_patches_covered", "denominator", "slope_bins_provided_30m"]}
                                                                     for k, v in rc["sites"].items()}, "note": rc["note"]},
        "nasa_sites": {"source": "results/nasa_test_sites_preregistration.json", "included": pre1["included"], "excluded": pre1["excluded"]},
    }
    ms = J("results/gate2b_masked_slopes.json")["boxes"]
    mars = [v["slopes"]["2m"]["median_deg"] for k, v in ms.items() if k != "earth_dumont"]
    out["masked_slopes"] = {"source": "results/gate2b_masked_slopes.json", "bagnold_2m_median_min": round(min(mars), 1),
                            "bagnold_2m_median_max": round(max(mars), 1), "n_bagnold_boxes": len(mars),
                            "dumont_2m_median": round(ms["earth_dumont"]["slopes"]["2m"]["median_deg"], 1)}
    (WEB / "data/results_summary.json").write_text(json.dumps(out, indent=1))
    for f in ["candidate_case.png", "gap_threshold_sensitivity.png", "g3v_groups.png"]:
        shutil.copy2(ROOT / "results" / f, WEB / "img" / f)
    print("ok", (WEB / "data/results_summary.json").stat().st_size, "B;", {k: out["gate2"][k] for k in out["gate2"] if k != "source"},
          out["v1"]["median_A"], out["sensitivity"]["points"])


if __name__ == "__main__":
    main()
