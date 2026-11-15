# Verified facts — Analog Coverage Gap Map

Numerical facts and source fields for the project.
All matches concern ground shape under the unchanged cut-off. They do not establish engineering suitability.
No historical result, dataset, method or cut-off was changed.

## Main facts

| Fact | Value | Existing JSON source / derivation |
|---|---|---|
| Moon squares | 145 | `results/moon_patches.json: n_grid_points; patches[]` |
| Each square; latitude band | 1.92 km × 1.92 km; 84–90°S | `results/moon_patches.json: rule; patches[].lat` |
| Features; scales | 19; slope 30/60/120/240/480 m, roughness 60/120/240/480 m | `web/data/display.json: feature_names[]` |
| Cut-off (unchanged) | 2.3166 (displayed 2.317); 90th percentile | `results/gap_map.json: threshold_T; results/gap_preregistration.json: threshold, normalisation` |
| Known list | 190 usable USGS records + 3 NASA test sites | `results/task2_all_usgs.json: records_used (of records_total = 192); results/report_card.json: sites` |
| Known list matched / no match | 85 / 60 of 145 | `results/g5_candidate_increment.json: K.covered, K.gap, K.covered_ids` |
| Smaller list matched / no match | 60 / 85 of 145 | `web/data/display.json: sets.union; results/task1_nasa_test_sites.json: sets.b_USGS29_union_NASA` |
| Original list matched / no match | 58 / 87 of 145 | `web/data/display.json: sets.historical; results/gap_map.json: patches[].covered` |
| NASA alone; each site | 45 of 145; Haughton 41, Moses Lake 29, Dumont 4 | `results/report_card.json: sites[].moon_patches_covered, covered_patch_ids; union of IDs = 45` |
| Sampling | 5,775 draws; 300 processed; 56°S–60°N; NDVI < 0.15 | `results/global_search.json: drawn, processed_kept, preregistration.sampling, preregistration.ndvi` |
| Sampling exclusions | 4,202 ocean/missing; 1,273 vegetation; 0 DEM-invalid | `results/global_search.json: skipped` |
| Sample flags | 294 Unverified, 6 Possibly known, 0 Known; 10 candidates with matches | `web/data/results_summary.json: global.novelty_counts; results/g5_candidate_increment.json: candidates[]` |
| Additional matches from random sample | 6 of 60: m014, m064, m101, m106, m123, m137 | `union(results/g5_candidate_increment.json: candidates[].N_ids) intersect K gaps; confirmed from results/global_search.json: patches[].covers_current_gap_patches` |
| Additional matches from Mojave test windows | 5 of 60: m064, m101, m102, m106, m109 | `web/data/display.json: patches[].neighbours where id starts mojave_, distance < T, status.K = false` |
| Morocco additional matches | 2 of 60: m014, m101 (13 of 85 in the smaller list) | `results/g5_candidate_increment.json: g00094.N, still_gap_under_K, listed_13` |
| Morocco coordinates; vegetation; nearest catalog point | 29.66522°N, 9.32073°W; NDVI 0.1468; Ouarkziz 187.1 km (187 rounded) | `results/candidate_case.json: candidate; novelty.nearest_known_km` |
| Other additional candidates | g00955 +3; g02176 +2; combined sample adds 6, not 7 | `results/g5_candidate_increment.json: candidates[].N_beyond_K, N_ids (one target overlaps)` |
| Showcase | {"patch": "m014", "candidate": "g00094", "candidate_d": 2.2496, "known_id": "usgs_rec050", "known_name": "Gardnos", "known_lat": 60.65, "known_lon": 9.0, "known_d": 2.6639, "T": 2.3166, "source": "docs/FACTS.md"} | `web/data/display.json: showcase; patches[id=m014].known_K, candidates; existing cached COP30, unchanged frozen distance` |
| m014 nearest Mojave window | 2.3409 | `web/data/display.json: patches[id=m014].neighbours[].distance; minimum Mojave value; above cut-off` |
| Test results | 3 tests: 2 failed, 1 could not decide | `web/data/results_summary.json: gate2, v1, g3v` |
| Mars-to-Dumont test | 51 of 64; top 10% required; secondary ranks 31 and 57 | `web/data/results_summary.json: gate2` |
| Dune retrieval test | median rank 17.5; threshold 7; alternative 21.5 of list 68 | `web/data/results_summary.json: v1` |
| Lidar test | 8 groups × 3 targets; 64 windows → 62 sites; 200 random combinations; random median 100% in 8/8 | `web/data/results_summary.json: g3v; results/g3v_preregistration.json` |
| All per-group percentages | fractions × 100, rounded to 1 decimal | `web/data/results_summary.json: g3v.groups[].A, B, random_median, random_p95; g3v.step2_transparency_only` |
| Sand slopes | Dumont 19.7°; Bagnold 3.8–7.4° at 2 m; about 3–5× higher median angle | `web/data/results_summary.json: masked_slopes` |
| Cut-off sensitivity, original 29-site list | 126/145 at 50th; 87/145 at 90th; 68/145 at 99th | `web/data/results_summary.json: sensitivity.points (includes T and percentages)` |
| Every displayed slope/roughness/coordinate/distance | source value; slopes 1 decimal, roughness 2, distances 2 or 3; coordinates up to 3 | `web/data/display.json: feature_names, feature_sd, features[entity_id][feature_index], patches[].lat/lon, neighbours, candidates, known_K; increment.candidates[]` |
| Image sizes and map | 1.92 km window; 30 m grid; 500 m bar; azimuth 315°, altitude 30°; full map 364 km | `scripts/build_web_data.py: render; src/gate3_common.py: PIX, PATCH_M; web/data/lola_84S_hillshade.json` |
| Other fixed context | 2026 event; 2012 Dumont field test; 2018, 2020, 2013 cited work; 1 g / 0.17 g; 0.5 m LOLA quantisation | `results/candidate_case.json: novelty, untested_conditions; results/nasa_test_sites_preregistration.json; cited source metadata (gravity is a stated limitation, not a result)` |
| Data-source amendment | 50 requests/day; max 0.0011 m = 1.1 mm at Dumont; four months Jan/Apr/Jul/Oct 2023 | `results/global_search_preregistration.json: ndvi, amendment_before_computation` |
| Selected demo | 29.9 s, 1920×1080; seven slides, real website interaction, Ron’s recorded voice, English captions | `web/demo/demo.mp4`, `web/demo/captions.vtt`, `docs/final_demo_check.json` |
| Similar measurement count, m014 vs Morocco | 18 of 19 absolute scaled differences ≤ 1 | `web/data/display.json: features[Moon], features[Earth], feature_sd; abs((Moon-Earth)/feature_sd) <= 1` |

## Citation identifiers and source metadata

Displayed citation IDs, years and coordinates in inclusion/exclusion explanations are source strings,
not coverage counts. Sources: `web/data/results_summary.json` `nasa_sites.included`, `nasa_sites.excluded`;
`results/nasa_test_sites_preregistration.json`; DOI `10.5066/P9J72921`, EGU2013-11983,
NASA NTRS 20000105009 and 20100036344. Excluded-site coordinates 35.0275, −111.0222 and citation year 2010
are copied from those existing records. Numeric audit reads these strings as well as numeric JSON fields.

## Machine-readable acceptance facts

```json
{
  "moon_count": 145,
  "patch_side_km": 1.92,
  "known_USGS_count": 190,
  "NASA_count": 3,
  "K_matched": 85,
  "K_unmatched": 60,
  "sample_count": 300,
  "random_new_matches": 6,
  "random_new_ids": [
    "m014",
    "m064",
    "m101",
    "m106",
    "m123",
    "m137"
  ],
  "Mojave_new_matches": 5,
  "Mojave_new_ids": [
    "m064",
    "m101",
    "m102",
    "m106",
    "m109"
  ],
  "Morocco_new_matches": 2,
  "showcase": {
    "patch": "m014",
    "candidate": "g00094",
    "candidate_d": 2.2496,
    "known_id": "usgs_rec050",
    "known_name": "Gardnos",
    "known_lat": 60.65,
    "known_lon": 9.0,
    "known_d": 2.6639,
    "T": 2.3166,
    "source": "docs/FACTS.md"
  },
  "checks": {
    "K_85_matched_60_unmatched": true,
    "sample_adds_six": true,
    "mojave_adds_five": true,
    "m014_only_sampled_match_Morocco": true
  }
}
```

The audit checks these values and all displayed numeric tokens against this ledger's named JSON sources.
Numbers are sample counts, not lunar area shares. Nearby values around the cut-off are not a safety boundary.
