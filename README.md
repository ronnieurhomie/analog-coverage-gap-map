# Earth candidates for Moon terrain

**Analog Coverage Gap Map** helps Moon field-test planners compare a lunar target with Earth candidates and inspect what still differs.

[Explore Moon terrain](https://ronnieurhomie.github.io/analog-coverage-gap-map/) · [7-slide demo](https://ronnieurhomie.github.io/analog-coverage-gap-map/slides/Analog-Coverage-Gap-Map.pdf)

The website opens with 145 selectable Moon squares and a linked Earth comparison. Start with the Morocco example: Morocco passes our shape cut-off, while the closest listed site does not.
Steep-end slopes are close, but larger-scale bumpiness differs. Villages, roads and vegetation remain; this is a candidate to investigate, not a ready test site.

The broader sample contains 145 Moon squares. The known list matches 85; a 300-location sample provides candidates for 6 of the remaining 60.
Two tests failed and one could not decide. The method has not established reliable site selection.

NASA Space Apps 2026 · Ron, team Analog Intelligence · Kuala Lumpur.
Challenge: Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.

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
New and edited code identifies AI assistance. Figures come from elevation data; the demo is a captioned screen recording.
No AI-generated images, video or audio are used. Ron reviews the final work before submission.

## Licence and status

MIT; see `LICENSE`. Repository and website are public. Nothing has been submitted to Space Apps by the coding agents.
See [G3_STATUS.md](docs/G3_STATUS.md) for executed, checked and published work, including the Codex clarity pass.
Screen-reader testing and browsers other than Chromium have not been checked.
