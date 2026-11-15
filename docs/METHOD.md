# Method and findings

Analog Coverage Gap Map compares lunar south-pole terrain with sampled Earth windows to identify candidates for further investigation. It is an exploratory terrain-comparison tool; field suitability remains unestablished.

## Data and comparison

- **Moon:** NASA LRO LOLA elevation data; 145 sampled squares at 84–90°S.
- **Earth:** ESA Copernicus GLO-30 elevation data. The reference list contains 190 usable USGS analog-site records and three cited NASA test-site windows.
- **Wider sample:** 300 Earth windows screened with NASA MODIS vegetation data. NASA HiRISE Mars terrain supports the first method test; the delivered search is Moon-to-Earth.

Each window is 1.92 km square. The fingerprint uses 19 measurements: slope median, 90th percentile and spread at 30, 60, 120, 240 and 480 m; plane-detrended roughness at 60–480 m. The analysis retains its fixed pooled normalization, Euclidean distance and cut-off of 2.3166 (displayed as 2.317). Lower distances indicate closer measured ground shape.

## Findings

Of the 145 sampled Moon squares, 85 match the full known list and 60 do not. The 300-window Earth sample supplies additional candidates for six of those 60. These are counts of sampled squares, not lunar area shares or an exhaustive Earth search.

For Moon square m014, the Morocco candidate scores 2.2496; the closest listed site, Gardnos, scores 2.6639. The Moon and Morocco have similar steep-end slopes (14.3° and 15.5°), but different 480 m roughness (2.78 m and 6.46 m). Eighteen of the 19 measurements differ by at most one pooled standard deviation. Morocco adds candidates for two full-list gaps; the earlier count of 13 used a smaller reference list.

## Tests

Pass/fail criteria were specified before each test and remain unchanged.

| Test | Observed result | Outcome |
|---|---|---|
| Mars dunes to Dumont Dunes | Rank 51 of 64; top 10% required | Failed |
| Retrieval among Earth dune fields | Median rank 17.5; 7 required | Failed |
| Fingerprint versus simple slope | Random selections reached median coverage 100% in all eight groups; ceiling prevented discrimination | Inconclusive |

These tests do not establish reliable site selection. A passing shape score is a reason to investigate, not approval of a test site.

## Limits and evidence

Each site is represented by a sampled window. Surface-elevation data can include vegetation and structures; the Morocco window contains villages, roads and trees. Soil mechanics, small rocks, access, permissions and operational safety need independent checks. Earth does not reproduce lunar gravity, vacuum, radiation or polar thermal conditions. The wider Moroccan region already has analog research; this is not a discovery.

The overview map uses lightweight display previews of the retained NASA LOLA hillshade. These previews do not change map bounds, fingerprints or comparison values.

- [Numerical facts and source fields](FACTS.md)
- [Dataset manifest and licences](../data/manifest.json)
- [Registered gap definition](../results/gap_preregistration.json)
- [Registered acceptance-test design](../results/g3v_preregistration.json)
- [Full-list candidate increments](../results/g5_candidate_increment.json)
- [Acceptance-test results](../results/g3v_results.json)

The repository retains the original analysis code, registered criteria and scientific results. The website's method disclosures link the NASA, ESA and USGS data sources and cited prior work.
