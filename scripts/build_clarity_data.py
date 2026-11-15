# AI assistance: OpenAI Codex; display-only consistency work, no new method or data.
"""Reconcile published values and prepare the m014 example from cached data only."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from fingerprint import fingerprint
from gate3_common import PIX, SCALES, earth_patch, vec
from g3v_recommend import frozen_norm
from build_web_data import render


def load(path):
    return json.loads((ROOT / path).read_text())


def main():
    d = load("web/data/display.json")
    ex = load("web/data/explorer.json")
    inc = load("results/g5_candidate_increment.json")
    gs = load("results/global_search.json")
    summary = load("web/data/results_summary.json")
    ids = {p["id"] for p in d["patches"]}
    known = set(inc["K"]["covered_ids"])
    gaps = ids - known
    additions = set().union(*(set(p["covers_current_gap_patches"]) & gaps for p in gs["patches"]))
    mojave = {p["id"] for p in d["patches"] if p["id"] in gaps and any(
        n["id"].startswith("mojave_") and n["distance"] < d["T"] for n in p["neighbours"])}
    m14 = next(p for p in d["patches"] if p["id"] == "m014")
    m14_candidates = [p["id"] for p in gs["patches"] if "m014" in p["covers_current_gap_patches"]]
    m14_grid = min(n["distance"] for n in m14["neighbours"] if n["id"].startswith("mojave_"))
    checks = {
        "K_85_matched_60_unmatched": len(known) == 85 and len(gaps) == 60,
        "sample_adds_six": additions == {"m014", "m064", "m101", "m106", "m123", "m137"},
        "mojave_adds_five": mojave == {"m064", "m101", "m102", "m106", "m109"},
        "m014_only_sampled_match_Morocco": m14_candidates == ["g00094"] and m14_grid >= d["T"] and "m014" in gaps,
    }
    assert all(checks.values()), checks

    # Use the identical frozen distance on existing cached windows, as the G4 builder does.
    # No downloads, changed thresholds or edits to historical results.
    mu, sd, threshold, _ = frozen_norm()
    recs = load("data/processed/analog_sites.json")
    selected = {s["record_index"]: ROOT / f"data/raw/earth_cop30/sites/{s['site_id']}_cop30.tif"
                for s in load("results/known_sites_selection.json")["sites"]}
    z = lambda f: (np.asarray(f) - mu) / sd
    sites, arrays = [], {}
    for i, r in enumerate(recs):
        path = selected.get(i, ROOT / f"data/raw/earth_cop30/usgs_all/rec{i:03d}_cop30.tif")
        if not path.exists():
            continue
        a = earth_patch(str(path), r["Lat"], r["Lon"])
        if np.isfinite(a).mean() < 0.95:
            continue
        key = f"usgs_rec{i:03d}"
        features = vec(fingerprint(a, PIX, SCALES))
        sites.append((key, z(features), r["Name"], r["Lat"], r["Lon"]))
        arrays[key] = (a, features)
    assert len(sites) == load("results/task2_all_usgs.json")["records_used"] == 190
    for key in ["nasa_dumont_dunes", "nasa_moses_lake_sand_dunes", "nasa_haughton_crater"]:
        sites.append((key, z(d["features"][key]), d["earth_names"][key]["name"], None, None))
    zs = np.stack([s[1] for s in sites])
    closest_ids = set()
    for p in d["patches"]:
        dist = np.linalg.norm(zs - z(d["features"][p["id"]]), axis=1)
        j = int(np.argmin(dist)); key, _, name, lat, lon = sites[j]
        assert bool(dist[j] < threshold) == p["status"]["K"], p["id"]
        p["known_K"] = {"id": key, "name": name, "distance": round(float(dist[j]), 4),
                        "below_T": bool(dist[j] < threshold), "lat": lat, "lon": lon}
        closest_ids.add(key)
    for key in closest_ids:
        if key in arrays:
            a, f = arrays[key]
            d["features"][key] = [round(float(v), 4) for v in f]
            name = next(s[2] for s in sites if s[0] == key)
            d["earth_names"][key] = {"name": name, "set": "USGS"}
            render(a, ROOT / "web/img/earth" / f"{key}.png")
    m14 = next(p for p in d["patches"] if p["id"] == "m014")
    k = m14["known_K"]
    d["showcase"] = {"patch": "m014", "candidate": "g00094", "candidate_d": m14["candidates"][0]["distance"],
                     "known_id": k["id"], "known_name": k["name"], "known_lat": k["lat"], "known_lon": k["lon"],
                     "known_d": k["distance"], "T": threshold, "source": "docs/FACTS.md"}
    d["sets"]["K"]["label"] = "190 USGS analog sites + 3 NASA test sites"
    d["sets"]["K"]["nature"] = "early result; fuller site list added after the main test"
    d["sets"]["union"]["label"] = "29 USGS analog sites + 3 NASA test sites"
    d["sets"]["union"]["nature"] = "early result; smaller site list"
    d["sets"]["allusgs"]["label"] = "190 USGS analog sites only"
    d["sets"]["allusgs"]["nature"] = "early result; added after the main test"
    d["sets"]["historical"]["label"] = "29 USGS analog sites only (original result)"
    d["sets"]["historical"]["nature"] = "original result; same fingerprint and cut-off"
    d["sets"]["nasa"]["nature"] = "early result"
    d["clarity"] = {"source": "docs/FACTS.md", "random_additional_ids": sorted(additions),
                    "random_additional_count": len(additions), "mojave_additional_ids": sorted(mojave),
                    "mojave_additional_count": len(mojave), "m014_nearest_grid_distance": m14_grid,
                    "m014_sampled_matches": m14_candidates, "checks": checks}
    d["neighbour_pool"] = ("Nearest listed site is checked against all 190 USGS analog sites + 3 NASA test sites. "
                           "Other windows below come from the smaller original list and our Mojave test grid. "
                           "Mojave test windows are not known test sites.")
    (ROOT / "web/data/display.json").write_text(json.dumps(d, separators=(",", ":")))
    ex["method_info"]["default_comparison_set"] = d["sets"]["K"]["label"]
    ex["method_info"]["fact_ledger"] = "docs/FACTS.md"
    for p in ex["patches"]:
        q = next(q for q in d["patches"] if q["id"] == p["patch_id"])
        p["default_K_status"] = {"set": d["sets"]["K"]["label"], "covered": q["status"]["K"],
                                 "nearest": q["known_K"]}
    (ROOT / "web/data/explorer.json").write_text(json.dumps(ex, separators=(",", ":")))

    facts = {"moon_count": len(ids), "patch_side_km": 1.92, "known_USGS_count": 190, "NASA_count": 3,
             "K_matched": len(known), "K_unmatched": len(gaps), "sample_count": gs["processed_kept"],
             "random_new_matches": len(additions), "random_new_ids": sorted(additions),
             "Mojave_new_matches": len(mojave), "Mojave_new_ids": sorted(mojave),
             "Morocco_new_matches": inc["g00094"]["N"], "showcase": d["showcase"], "checks": checks}
    lines = ["# Verified facts — Analog Coverage Gap Map", "", "Single ledger for website, README, captions and submission text.",
             "All matches concern ground shape under the unchanged cut-off. They do not establish engineering suitability.",
             "No historical result, dataset, method or cut-off was changed.", "", "## Main facts", "",
             "| Fact | Value | Existing JSON source / derivation |", "|---|---|---|"]
    rows = [
        ("Moon squares", len(ids), "results/moon_patches.json: n_grid_points; patches[]"),
        ("Each square; latitude band", "1.92 km × 1.92 km; 84–90°S", "results/moon_patches.json: rule; patches[].lat"),
        ("Features; scales", "19; slope 30/60/120/240/480 m, roughness 60/120/240/480 m", "web/data/display.json: feature_names[]"),
        ("Cut-off (unchanged)", f"{threshold} (displayed 2.317); 90th percentile", "results/gap_map.json: threshold_T; results/gap_preregistration.json: threshold, normalisation"),
        ("Known list", "190 usable USGS records + 3 NASA test sites", "results/task2_all_usgs.json: records_used (of records_total = 192); results/report_card.json: sites"),
        ("Known list matched / no match", "85 / 60 of 145", "results/g5_candidate_increment.json: K.covered, K.gap, K.covered_ids"),
        ("Smaller list matched / no match", "60 / 85 of 145", "web/data/display.json: sets.union; results/task1_nasa_test_sites.json: sets.b_USGS29_union_NASA"),
        ("Original list matched / no match", "58 / 87 of 145", "web/data/display.json: sets.historical; results/gap_map.json: patches[].covered"),
        ("NASA alone; each site", "45 of 145; Haughton 41, Moses Lake 29, Dumont 4", "results/report_card.json: sites[].moon_patches_covered, covered_patch_ids; union of IDs = 45"),
        ("Sampling", "5,775 draws; 300 processed; 56°S–60°N; NDVI < 0.15", "results/global_search.json: drawn, processed_kept, preregistration.sampling, preregistration.ndvi"),
        ("Sampling exclusions", "4,202 ocean/missing; 1,273 vegetation; 0 DEM-invalid", "results/global_search.json: skipped"),
        ("Sample flags", "294 Unverified, 6 Possibly known, 0 Known; 10 candidates with matches", "web/data/results_summary.json: global.novelty_counts; results/g5_candidate_increment.json: candidates[]"),
        ("Additional matches from random sample", f"{len(additions)} of 60: {', '.join(sorted(additions))}", "union(results/g5_candidate_increment.json: candidates[].N_ids) intersect K gaps; confirmed from results/global_search.json: patches[].covers_current_gap_patches"),
        ("Additional matches from Mojave test windows", f"{len(mojave)} of 60: {', '.join(sorted(mojave))}", "web/data/display.json: patches[].neighbours where id starts mojave_, distance < T, status.K = false"),
        ("Morocco additional matches", "2 of 60: m014, m101 (13 of 85 in the smaller list)", "results/g5_candidate_increment.json: g00094.N, still_gap_under_K, listed_13"),
        ("Morocco coordinates; vegetation; nearest catalog point", "29.66522°N, 9.32073°W; NDVI 0.1468; Ouarkziz 187.1 km (187 rounded)", "results/candidate_case.json: candidate; novelty.nearest_known_km"),
        ("Other additional candidates", "g00955 +3; g02176 +2; combined sample adds 6, not 7", "results/g5_candidate_increment.json: candidates[].N_beyond_K, N_ids (one target overlaps)"),
        ("Showcase", json.dumps(d["showcase"], ensure_ascii=False), "web/data/display.json: showcase; patches[id=m014].known_K, candidates; existing cached COP30, unchanged frozen distance"),
        ("m014 nearest Mojave window", m14_grid, "web/data/display.json: patches[id=m014].neighbours[].distance; minimum Mojave value; above cut-off"),
        ("Test results", "3 tests: 2 failed, 1 could not decide", "web/data/results_summary.json: gate2, v1, g3v"),
        ("Mars-to-Dumont test", "51 of 64; top 10% required; secondary ranks 31 and 57", "web/data/results_summary.json: gate2"),
        ("Dune retrieval test", "median rank 17.5; threshold 7; alternative 21.5 of list 68", "web/data/results_summary.json: v1"),
        ("Lidar test", "8 groups × 3 targets; 64 windows → 62 sites; 200 random combinations; random median 100% in 8/8", "web/data/results_summary.json: g3v; results/g3v_preregistration.json"),
        ("All per-group percentages", "fractions × 100, rounded to 1 decimal", "web/data/results_summary.json: g3v.groups[].A, B, random_median, random_p95; g3v.step2_transparency_only"),
        ("Sand slopes", "Dumont 19.7°; Bagnold 3.8–7.4° at 2 m; about 3–5× higher median angle", "web/data/results_summary.json: masked_slopes"),
        ("Cut-off sensitivity, original 29-site list", "126/145 at 50th; 87/145 at 90th; 68/145 at 99th", "web/data/results_summary.json: sensitivity.points (includes T and percentages)"),
        ("Every displayed slope/roughness/coordinate/distance", "source value; slopes 1 decimal, roughness 2, distances 2 or 3; coordinates up to 3", "web/data/display.json: feature_names, feature_sd, features[entity_id][feature_index], patches[].lat/lon, neighbours, candidates, known_K; increment.candidates[]"),
        ("Similar measurement count", "count of the 19 absolute scaled differences <= 1", "web/data/display.json: features[Moon], features[Earth], feature_sd; abs((Moon-Earth)/feature_sd) <= 1"),
        ("Image sizes and map", "1.92 km window; 30 m grid; 500 m bar; azimuth 315°, altitude 30°; full map 364 km", "scripts/build_web_data.py: render; src/gate3_common.py: PIX, PATCH_M; web/data/lola_84S_hillshade.json"),
        ("Other fixed context", "2026 event; 2012 Dumont field test; 2018, 2020, 2013 cited work; 1 g / 0.17 g; 0.5 m LOLA quantisation", "results/candidate_case.json: novelty, untested_conditions; results/nasa_test_sites_preregistration.json; docs/G3_STATUS.md; cited source metadata (gravity is a stated limitation, not a result)"),
        ("Data-source amendment", "50 requests/day; max 0.0011 m = 1.1 mm at Dumont; four months Jan/Apr/Jul/Oct 2023", "results/global_search_preregistration.json: ndvi, amendment_before_computation"),
        ("Demo", "≤30 seconds; intended 29.9; 1280×720", "scripts/make_demo.py: SHOTS, W, H; actual duration checked with ffprobe"),
    ]
    for name, value, source in rows:
        lines.append(f"| {name} | {str(value).replace('|', '/')} | `{source}` |")
    lines += ["", "## Citation identifiers and source metadata", "",
              "Displayed citation IDs, years and coordinates in inclusion/exclusion explanations are source strings, not coverage counts.",
              "Sources: `web/data/results_summary.json` `nasa_sites.included`, `nasa_sites.excluded`; `results/nasa_test_sites_preregistration.json`.",
              "DOI 10.5066/P9J72921, EGU2013-11983, NASA NTRS 20000105009 and 20100036344; excluded-site coordinates 35.0275, −111.0222 and citation year 2010 come from those records.",
              "", "## Machine-readable acceptance facts", "", "```json", json.dumps(facts, indent=2), "```", "",
              "The audit checks these values and all displayed numeric tokens against this ledger's named JSON sources.",
              "Numbers are sample counts, not lunar area shares. Nearby values around the cut-off are not a safety boundary.", ""]
    (ROOT / "docs/FACTS.md").write_text("\n".join(lines))
    previous = load("docs/showcase_numbers.json")
    previous.update({"showcase_patch": "m014", "d_to_g00094": d["showcase"]["candidate_d"],
                     "nearest_in_K": k["name"], "d_nearest_in_K": k["distance"], "T": threshold,
                     "source": "docs/FACTS.md"})
    (ROOT / "docs/showcase_numbers.json").write_text(json.dumps(previous, indent=2))
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()
