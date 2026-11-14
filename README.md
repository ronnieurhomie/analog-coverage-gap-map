# Analog Coverage Gap Map

NASA Space Apps Challenge 2026 — "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars".
Team: Analog Intelligence.

A planet-agnostic terrain fingerprint that compares DEM patches from Mars, the Moon and Earth.

Status: Gate 1 (Mars Gale crater + Mojave validation smoke run). See `data/manifest.json` for all data sources.

Portions of this repository were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.

License: MIT

## Status (2026-11-15, after G3v/G3b)

Full handoff: [`docs/G3_STATUS.md`](docs/G3_STATUS.md). Change log: `results/CHANGELOG_G3.md`.

- **Executed:** G3v pre-registered acceptance test; G3b Tasks 1, 2, 3, 5, 6, 7 and 8.
- **Verified:** G3v data checks (site grouping, separation, validity, units); the current method reproduces the
  historical USGS-29 gap (60.0%) exactly; AWS and OpenTopography COP30 identical at Dumont; manifest checksums.
- **Results:**
  - G3v: **INCONCLUSIVE** (formal ceiling: random-combination median 100% in 8/8 groups).
  - Moon-side numbers are exploratory: fingerprint A, T = 2.317, denominator 145 patches.
- **Earlier pre-registered tests:** Gate 2 and Gate 2b/V1 both failed. They are kept as recorded.
- **Not done:**
  - Task 4 portfolio (not allowed under INCONCLUSIVE).
  - Vegetation check of COP30 sites.
  - Buried-crater exclusion (no authoritative source reachable).
- **Not published:** nothing pushed, deployed or submitted; local git only.
