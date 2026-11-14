# G3 changelog

- G3v start: 2026-11-15 01:27:59 WIB (90-minute cap runs from here)
- 01:29 pre-check: 5/8 pseudo-groups random median >= 95% -> continue. g3v_preregistration.json written.
- 01:30 extraction started. Note: target 2 m windows are read during extraction only to apply the >=95% validity rule (registered qualification); no slope computed from them before recommendations are frozen.
- 01:38:18 recommendations frozen: results/g3v_recommendations.json sha256 9e3b907f40489fd5
- 01:39:04 G3v scored and verified. End: 2026-11-15 01:39:04 WIB. Branch INCONCLUSIVE (Step 1: formal ceiling 8/8 groups random median 100%). No bug fixes, no rule changes.
- 01:42 OpenTopography hit its 50 calls/24 h limit during Task 2 all-USGS (stopped after 9/192 records; partial number not used). Amendment before computation: Task 2 all-USGS and Task 3 now read the identical Copernicus GLO-30 COGs from AWS Open Data (src/cop30_aws.py); AWS vs OpenTopography at Dumont: max |diff| 0.0011 m.
