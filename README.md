# Earth candidates for Moon terrain

**Analog Coverage Gap Map** is an exploratory tool for a practical question: **Which lunar terrain types are not represented by the Earth analog sites in our reference list, and where else might researchers look?**

[Explore the interactive map](https://ronnieurhomie.github.io/analog-coverage-gap-map/) · [Watch the 30-second demo](https://ronnieurhomie.github.io/analog-coverage-gap-map/demo/) · [View the 7-slide deck](https://ronnieurhomie.github.io/analog-coverage-gap-map/slides/Analog-Coverage-Gap-Map.pdf)

NASA LRO LOLA elevation data defines **145 sampled terrain squares** near the Moon's south pole. ESA Copernicus elevation data provides Earth comparisons, NASA MODIS vegetation data screens a wider land sample, and NASA HiRISE Mars terrain supports a method test. The delivered search is **Moon-to-Earth**; Mars is used for testing, not presented as a second completed search.

For each 1.92 × 1.92 km window, the project compares **19 slope and roughness measurements** at several scales. Select a Moon square to inspect an Earth candidate, the closest alternative in the known-site list, same-scale terrain views, and the differences that remain. A score below the fixed threshold indicates similarity under this method—not permission or readiness to conduct a field test.

### What the current sample shows

- **85 of 145** sampled Moon squares have a match in a reference list of 190 usable USGS analog-site records and three documented NASA test-site windows; **60 do not**.
- A screened sample of **300 additional Earth locations** provides potential matches for **six of those 60** unmatched squares. These are counts of sampled squares, **not percentages of lunar area**.
- The southern Morocco example passes the terrain-shape threshold for one Moon square, although its larger-scale roughness differs. The region already has analog research; this is not a newly discovered or field-validated test site.
- **Two pre-registered tests failed and one was inconclusive.** Reliable site selection has not been established.

The value of the prototype is to make the comparison and its uncertainty inspectable before anyone invests in field investigation. Terrain alone cannot confirm soil conditions, small rocks, access, permissions, or lunar environmental equivalence.

NASA Space Apps Challenge 2026 · **Ron (solo participant)** · Team **Analog Intelligence** · Kuala Lumpur Local Event  
Challenge: *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.*

## Evidence and limits

The Morocco location is not a discovery: the wider region already has Mars-analog research.
Soil, small rocks, access and lunar conditions remain unconfirmed. Each location is a sampled window, not a whole test field.

[Current project plan](docs/PROJECT_PLAN.md) · [Full report and method](docs/SUBMISSION.md) · [Facts and source fields](docs/FACTS.md) · [Tests and project status](docs/G3_STATUS.md)

## Run the website

```bash
cd web && python3 -m http.server 8000
```

Open http://localhost:8000/. Static HTML, CSS and JavaScript; no backend or build step.

Rebuild display data from the existing local dataset cache (not included in git):

```bash
.venv/bin/python scripts/build_web_data.py && .venv/bin/python scripts/g5_increment.py && .venv/bin/python scripts/build_web_g5.py && .venv/bin/python scripts/build_web_results.py && .venv/bin/python scripts/build_clarity_data.py
```

The last step restores the full-list default data and current worked example. It uses existing data and the unchanged method.
Site and numeric checks: `.venv/bin/python scripts/check_clarity.py`.
Analysis code is in `src/`; analysis tests: `.venv/bin/python -m pytest -q tests`.

## Data and references

- NASA LRO LOLA LDEM_80S_20M: the Moon targets, core data.
- NASA MRO HiRISE DTM DTEEC_040770_1755_039280_1755_U01: the Mars dune test.
- NASA MODIS MOD13C2: vegetation screening of the Earth sample.
- ESA Copernicus GLO-30: Earth elevation data, via OpenTopography and AWS Open Data.
- USGS 3DEP lidar: metre-scale test data.
- USGS Known Terrestrial Analog Sites, Hunter (2020), doi:10.5066/P9J72921.
- NASADEM: only an earlier Earth-elevation cross-check; no website result depends on it.

Products, sources and licences: `data/manifest.json`. Links and prior work are in the website's Method section
and [submission text](docs/SUBMISSION.md). NASA NTRS 20000105009 is cited but not summarised because the record could not be opened.

## AI assistance

Ron chose the challenge framing and direction. Claude helped with planning, critique and drafts.
Claude Code helped with research lookups and code. OpenAI Codex reviewed the plan, revised the layout and narrative, produced the demo and checked consistency.
New and edited code identifies AI assistance. Figures come from elevation data; the demo combines Ron’s seven slides, actual website interaction, his recorded narration and English captions.
No AI-generated images, video or audio are used. Ron reviews the final work before submission.

## Licence and status

MIT; see `LICENSE`. Repository and website are public. Nothing has been submitted to Space Apps by the coding agents.
See [G3_STATUS.md](docs/G3_STATUS.md) for executed, checked and published work, including the Codex clarity pass.
Screen-reader testing and browsers other than Chromium have not been checked.
