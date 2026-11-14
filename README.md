# Which place on Earth is worth checking against this Moon terrain?

**Analog Coverage Gap Map** · NASA Space Apps Challenge 2026, "Identify Earth Locations that Analog the Permanent Moon
Base Locations and Mars" · Local event: Kuala Lumpur · Team: Analog Intelligence (solo entrant Ron).

Pick a terrain patch near the lunar south pole, see Earth candidates at the same scale, and see what matches, what
differs, and what is still unknown. We compare 145 1.92 km patches from NASA LOLA data (84–90°S) with Earth analog
sites and NASA rover/EVA test sites, using a terrain fingerprint built from slope and roughness at 30–480 m.
**Everything shown is exploratory:** our pre-registered acceptance test was inconclusive.

## Run it
```bash
cd web && python3 -m http.server 8000
```
Then open http://localhost:8000/. The page is static, with no backend and no build step.

Rebuild the page data from the existing results (needs the local `data/` folder, which is not in git):
```bash
.venv/bin/python scripts/build_web_data.py && .venv/bin/python scripts/g5_increment.py && .venv/bin/python scripts/build_web_g5.py && .venv/bin/python scripts/build_web_results.py && .venv/bin/python scripts/render_candidate_web.py
```
Analysis scripts live in `src/` (one per gate); tests: `.venv/bin/python -m pytest -q tests`.

## What we tested (including failures)
- **Gate 2 (pre-registered, failed):** starting from a Bagnold dune patch on Mars, Dumont Dunes ranked 51 of 64 Mojave
  candidates (top 10% needed). Measured on sand-only pixels, Dumont's median slope angle is about 3–5× higher than
  the Bagnold boxes.
- **V1 (pre-registered, failed):** known Earth dune patches did not reliably retrieve each other (median rank 17.5;
  threshold 7).
- **G3v (pre-registered, INCONCLUSIVE):** fingerprint-based site picks versus a slope-only method, scored with 2 m lidar.
  Random 3-site picks already reached 100% coverage in all 8 groups, so the test could not tell the methods apart.
- **Current Moon-side numbers** (fingerprint A, T = 2.317, denominator 145, exploratory):

  | Comparison set | Covered | Gap |
  |---|---|---|
  | USGS-29 ∪ 3 NASA test sites | 60 | 85 |
  | All usable USGS sites ∪ 3 NASA test sites (post-hoc) | 85 | 60 |
  | Historical (USGS-29, Gate 3a) | 58 | 87 |

  The candidate g00094 (southern Morocco, Unverified) still gives 2 Moon patches a geometric neighbour beyond the fuller
  set.

Details: `docs/G3_STATUS.md`. Every registration and result is in `results/`.

## Limitations
- G3v cannot discriminate: almost any 1.92 km site contains almost every slope bin.
- The gap share depends strongly on the threshold: 126, 87 and 68 gap patches of 145 at the 50th, 90th and 99th
  percentile.
- Copernicus GLO-30 is a surface model, so vegetation and buildings are included. LOLA heights are quantised to 0.5 m.
- Moses Lake coordinates are approximate. The USGS analog layer has label issues.
- Patch counts are not area fractions of the lunar south pole.
- Earth comparisons do not reproduce gravity, vacuum, atmosphere or radiation, and nothing here tests vehicles, soil or
  hardware.

## Data and references
- NASA LRO LOLA LDEM_80S_20M (PDS Geosciences Node).
- MRO HiRISE DTM DTEEC_040770_1755_039280_1755_U01.
- USGS 3DEP 1 m lidar.
- Copernicus GLO-30 DEM (OpenTopography and AWS Open Data).
- NASADEM, used as a cross-check (doi:10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001).
- MODIS MOD13C2 (doi:10.5067/MODIS/MOD13C2.061).
- USGS Known Terrestrial Analog Sites, Hunter (2020), doi:10.5066/P9J72921.

Every dataset, with source, ID, licence and checksum, is listed in `data/manifest.json`.

Prior work:
- Sanganeria (2026), National High School Journal of Science (image-texture screening).
- EGU2013-11983 (multi-scale DEM roughness of Mars landforms and analogues).
- NTRS 20000105009 (cited, not summarised).

## AI assistance
Ron chose the challenge framing and direction. AI assistance: Claude (planning discussion and critique, drafting),
Claude Code (research lookups and code), OpenAI Codex (plan review). Source files carry headers; Ron reviewed the work.

## Licence
MIT (see `LICENSE`).

## Status (2026-11-15, G5)
- **Executed:** Gates 1–3, G3v, G3b, G4 front end, G5 fixes and packaging (net-contribution set operations, clickable
  candidates, showcase, screen video).
- **Verified:** number checks against the result JSON; headless Chromium at 1280 px and 390 px with 0 console errors;
  banned-word grep clean; manifest checksums.
- **Repository:** https://github.com/ronnieurhomie/analog-coverage-gap-map · **Live page:** https://ronnieurhomie.github.io/analog-coverage-gap-map/
- **Not done:** screen-reader testing; browsers other than Chromium; Space Apps submission.
- **Published:** the repository and the static page (GitHub Pages). Nothing submitted to Space Apps.
