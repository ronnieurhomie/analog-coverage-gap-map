# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Fetch COP30 (OpenTopography globaldem) and NASADEM (earthaccess) around each pre-selected known site."""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
COP_DIR = ROOT / "data/raw/earth_cop30/sites"
NAS_DIR = ROOT / "data/raw/nasadem"
LOG = ROOT / "data/processed/meta/gate3_site_fetch.json"


def cop30(site) -> dict:
    out = COP_DIR / f"{site['site_id']}_cop30.tif"
    if out.exists() and out.stat().st_size > 1000:
        return {"file": str(out.relative_to(ROOT)), "status": "exists"}
    la, lo = site["lat"], site["lon"]
    dlat = 0.03
    dlon = min(0.03 / max(math.cos(math.radians(la)), 0.05), 1.0)
    params = dict(demtype="COP30", south=la - dlat, north=la + dlat, west=lo - dlon, east=lo + dlon,
                  outputFormat="GTiff", API_Key=os.environ["OPENTOPO_API_KEY"])
    r = requests.get("https://portal.opentopography.org/API/globaldem", params=params, timeout=300)
    if r.status_code != 200 or r.content[:2] not in (b"II", b"MM"):
        return {"status": f"HTTP {r.status_code}", "body": r.text[:200]}
    out.write_bytes(r.content)
    return {"file": str(out.relative_to(ROOT)), "status": "ok", "bytes": len(r.content),
            "bbox": [params["west"], params["south"], params["east"], params["north"]]}


def nasadem(site) -> dict:
    la, lo = site["lat"], site["lon"]
    if not (-56 <= la < 60):
        return {"status": "outside NASADEM coverage (60N-56S)"}
    import earthaccess
    earthaccess.login(strategy="netrc")
    g = earthaccess.search_data(short_name="NASADEM_HGT", point=(lo, la), count=1)
    if not g:
        return {"status": "no granule found (ocean or void tile)"}
    ur = g[0]["umm"]["GranuleUR"]
    z = NAS_DIR / f"{ur}.zip"
    if not z.exists():
        earthaccess.download(g, str(NAS_DIR), show_progress=False)
    if not z.exists():
        return {"status": "download failed", "granule": ur}
    return {"status": "ok", "granule": ur, "file": str(z.relative_to(ROOT)), "bytes": z.stat().st_size}


def main():
    COP_DIR.mkdir(parents=True, exist_ok=True); NAS_DIR.mkdir(parents=True, exist_ok=True)
    sites = json.loads((ROOT / "results/known_sites_selection.json").read_text())["sites"]
    log = {}
    for s in sites:
        rec = {"cop30": cop30(s)}
        try:
            rec["nasadem"] = nasadem(s)
        except Exception as e:
            rec["nasadem"] = {"status": f"error {type(e).__name__}: {e}"[:200]}
        log[s["site_id"]] = rec
        print(s["site_id"], s["name"], rec["cop30"]["status"], rec["nasadem"]["status"], flush=True)
        time.sleep(1)
    LOG.write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
