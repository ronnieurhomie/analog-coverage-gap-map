# Which Moon terrain has an Earth look-alike?

**Analog Coverage Gap Map** helps teams planning Moon field tests compare ground shape before investigating Earth locations.
Pick a Moon square, view Earth candidates at the same scale, and see similarities, differences and what to check next.

[Open the map](https://ronnieurhomie.github.io/analog-coverage-gap-map/) ·
[Watch the 30-second demo](https://ronnieurhomie.github.io/analog-coverage-gap-map/demo/) ·
[Verified facts and JSON sources](docs/FACTS.md)

Built by Ron, team Analog Intelligence, for NASA Space Apps 2026, Kuala Lumpur.
Challenge: Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.

## What it found

We sample **145 squares**, each **1.92 km × 1.92 km**, near the lunar south pole using NASA LOLA elevation data.
The default known-site list is **190 USGS analog sites + 3 NASA test sites**.

- **85 of 145** Moon squares have a ground-shape look-alike in that list; **60 do not**.
- **300** random land locations with little vegetation give candidate look-alikes for **6 of those 60**.
- Separately, **5 of the 60** match a window in our Mojave test grid. The grid is outside the known-site list. These counts overlap.
- A candidate in southern Morocco matches **2 of the 60**. The worked example is a Moon square (m014) matched by this candidate alone among the locations compared.

A look-alike passes our fixed ground-shape cut-off (distance d < **2.317**, exact value **2.3166**).
This is an early result, not evidence that a location is ready for field tests.
Morocco's wider region already has Mars-analog research. Villages, roads and vegetation occur in the sampled window.
It is **not a discovery** and **not a ready test site**.

Other lists remain in Comparison settings. Their counts must not be mixed:

| Earth locations compared | Matched Moon squares | No match |
|---|---:|---:|
| 190 USGS analog sites + 3 NASA test sites (default) | 85 of 145 | 60 of 145 |
| 29 USGS analog sites + 3 NASA test sites (smaller list) | 60 of 145 | 85 of 145 |
| 29 USGS analog sites only (original result) | 58 of 145 | 87 of 145 |

## How much to trust it

We wrote each pass/fail rule before its test:

- **Failed:** starting from Mars dunes, Dumont Dunes ranked **51 of 64** candidates; the top **10%** was required.
- **Failed:** Earth dune fields did not reliably find each other; median rank **17.5**, with **7** required.
- **Could not decide:** in the fingerprint-versus-slope test, random choices had median coverage **100% in all 8 groups**.

These results do not establish that the method can select test sites. The tool supports comparisons and further investigation.
All original registrations and results remain in `results/`. The current status is in [G3_STATUS.md](docs/G3_STATUS.md).

## Limits

- Shape only: no soil mechanics, small rocks, gravity, vacuum, lighting or temperature.
- Copernicus GLO-30 includes trees and buildings. Moses Lake's coordinates are approximate.
- The cut-off matters: the original 29-site list leaves **126, 87 or 68 of 145** squares unmatched at the **50th, 90th or 99th** percentile cut-offs.
- Square counts are not area shares of the lunar south pole. Each site is represented by a sampled window.
- No vehicle testing, land access or permission is established by this project.

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
Claude Code helped with research lookups and code. OpenAI Codex reviewed the plan, edited text and checked consistency.
New and edited code identifies AI assistance. Figures come from elevation data; the demo is a captioned screen recording.
No AI-generated images, video or audio are used. Ron reviews the final work before submission.

## Licence and status

MIT; see `LICENSE`. Repository and website are public. Nothing has been submitted to Space Apps by the coding agents.
See [G3_STATUS.md](docs/G3_STATUS.md) for executed, checked and published work, including the Codex clarity pass.
Screen-reader testing and browsers other than Chromium have not been checked.
