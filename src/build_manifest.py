# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Build data/manifest.json from the datasets actually on disk (values read from the files)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data/processed/meta"
ACCESS_DATE = "2026-11-14"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raster_facts(p: Path) -> dict:
    with rasterio.open(p) as d:
        return {"crs": d.crs.to_wkt() if d.crs and not d.crs.to_epsg() else f"EPSG:{d.crs.to_epsg()}",
                "resolution_m": round(abs(d.transform.a), 6), "shape_rows_cols": [d.height, d.width],
                "nodata": d.nodata, "dtype": d.dtypes[0]}


def main() -> None:
    entries = []
    mars = ROOT / "data/raw/mars/DTEEC_040770_1755_039280_1755_U01.IMG"
    e = {
        "id": "mars_gale_hirise_dtm",
        "file": str(mars.relative_to(ROOT)),
        "source": "NASA PDS Imaging Node / HiRISE (University of Arizona), data set MRO-M-HIRISE-5-DTM-V1.0",
        "product_id": "DTEEC_040770_1755_039280_1755_U01",
        "stereo_pair": ["ESP_040770_1755", "ESP_039280_1755"],
        "pds_rationale": "Gale Crater dunes and Curiosity rover",
        "url": "https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/ORB_040700_040799/ESP_040770_1755_ESP_039280_1755/DTEEC_040770_1755_039280_1755_U01.IMG",
        "instrument": "MRO HiRISE stereo (DTM produced by USGS, version U01)",
        "units": "metres, elevation relative to the Mars areoid (PDS label VALID_MINIMUM/MAXIMUM)",
        "access_date": ACCESS_DATE,
        "license": "NASA PDS data, public. Cite: McEwen et al. (2007) JGR 112, E05S02; HiRISE DTM via PDS (MRO-M-HIRISE-5-DTM-V1.0).",
    }
    if mars.exists() and mars.stat().st_size == 308422800:
        e.update(raster_facts(mars)); e["bytes"] = mars.stat().st_size; e["sha256"] = sha256(mars)
    else:
        e["status"] = "INCOMPLETE DOWNLOAD"
    entries.append(e)

    ortho = ROOT / "data/raw/mars/ESP_040770_1755_RED_C_01_ORTHO.JP2"
    if ortho.exists():
        o = {"id": "mars_gale_hirise_ortho", "file": str(ortho.relative_to(ROOT)),
             "source": "NASA PDS / HiRISE, orthoimage distributed with DTM DTEEC_040770_1755_039280_1755_U01",
             "product_id": "ESP_040770_1755_RED_C_01_ORTHO",
             "url": "https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/ORB_040700_040799/ESP_040770_1755_ESP_039280_1755/ESP_040770_1755_RED_C_01_ORTHO.JP2",
             "instrument": "MRO HiRISE RED", "units": "8-bit DN (visual check only, not used in fingerprints)",
             "used_for": "Visual check of the Mars patch locations",
             "access_date": ACCESS_DATE, "license": e["license"]}
        o.update(raster_facts(ortho)); o["bytes"] = ortho.stat().st_size; o["sha256"] = sha256(ortho)
        entries.append(o)

    for m in sorted(META.glob("*_negctrl.json")) + sorted(META.glob("mojave_*.json")):
        info = json.loads(m.read_text())
        p = ROOT / info["file"]
        info.update(raster_facts(p)); info["bytes"] = p.stat().st_size; info["sha256"] = sha256(p)
        info["id"] = "earth_" + info.pop("name")
        entries.append(info)

    cop = ROOT / "data/raw/earth_cop30/cop30_gate2_area.tif"
    if cop.exists():
        c = {"id": "earth_cop30_gate2_area", "file": str(cop.relative_to(ROOT)),
             "source": "Copernicus DEM GLO-30 via OpenTopography globaldem API (demtype=COP30)",
             "url": "https://portal.opentopography.org/API/globaldem?demtype=COP30&south=35.20&north=36.00&west=-116.75&east=-115.75&outputFormat=GTiff",
             "instrument": "TanDEM-X InSAR (Copernicus DEM, surface model)", "units": "metres (EGM2008 heights per Copernicus DEM spec)",
             "access_date": ACCESS_DATE,
             "license": "Copernicus DEM GLO-30: (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA; free licence. Cite OpenTopography doi:10.5069/G9028PQB.",
             "note": "resolution_m below is in degrees (1 arc-second), CRS EPSG:4326"}
        c.update(raster_facts(cop)); c["bytes"] = cop.stat().st_size; c["sha256"] = sha256(cop)
        entries.append(c)
    cj = ROOT / "results/candidates.json"
    if cj.exists():
        cd = json.loads(cj.read_text())
        tiles = sorted({t for c_ in cd["candidates"] for t in c_["tiles"]})
        entries.append({"id": "earth_gate2_candidates_3dep1m", "files": "data/processed/candidates/*.npy (256 m patches on 2 m grid, float32, NaN nodata)",
                        "source": "USGS 3DEP 1 m DEM, windowed reads from USGS public S3 (same as earth_mojave_dumont_box)",
                        "product_ids": tiles, "n_patches": cd["n_candidates"], "instrument": "Airborne lidar (3DEP)",
                        "resolution_m": 1.0, "resampled_to_m": 2.0, "crs": "EPSG:26911", "nodata": "NaN after resampling (source -999999)",
                        "units": "metres", "access_date": ACCESS_DATE,
                        "license": "Public domain (U.S. Government work). Cite: U.S. Geological Survey, 3D Elevation Program 1-Meter Resolution DEM."})

    nz = ROOT / "data/raw/nasadem/NASADEM_HGT_n35w117.zip"
    if nz.exists():
        entries.append({"id": "earth_nasadem_n35w117", "file": str(nz.relative_to(ROOT)), "bytes": nz.stat().st_size, "sha256": sha256(nz),
                        "source": "NASA LP DAAC via earthaccess (Earthdata Login)", "product_id": "NASADEM_HGT_n35w117",
                        "collection": "NASADEM_HGT v001", "instrument": "SRTM C-band InSAR (reprocessed)",
                        "resolution_m": "1 arc-second (~30 m)", "crs": "EPSG:4326 (WGS84 lat/lon)", "units": "metres (EGM96 heights per NASADEM user guide)",
                        "nodata": "see NASADEM user guide (.hgt is 16-bit signed)", "access_date": ACCESS_DATE,
                        "license": "NASA data, no restrictions. Cite: NASA JPL (2020). NASADEM Merged DEM Global 1 arc second V001. doi:10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001",
                        "status": "Gate 3 prep: download check only, not used yet"})
    vp = ROOT / "results/v1_preregistration.json"
    if vp.exists():
        pre = json.loads(vp.read_text())
        entries.append({"id": "earth_v1_positives_3dep1m", "files": "data/processed/v1_positives/*.npy (256 m, 2 m grid)",
                        "source": "USGS 3DEP 1 m DEM, windowed reads from USGS public S3", "positives": pre["positives"],
                        "resolution_m": 1.0, "resampled_to_m": 2.0, "crs": "EPSG:26911", "access_date": ACCESS_DATE,
                        "license": "Public domain (U.S. Government work)."})
        entries.append({"id": "ref_usgs_imagery_basemap", "kind": "reference (visual check only)",
                        "files": "data/raw/reference/naip/*.png", "source": "USGS The National Map, USGSImageryOnly MapServer export",
                        "url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer", "access_date": ACCESS_DATE,
                        "license": "Public domain (USGS)"})
    lola = ROOT / "data/raw/moon/ldem_80s_20m.img"
    if lola.exists() and lola.stat().st_size == 1848320000:
        entries.append({"id": "moon_lola_ldem_80s_20m", "file": str(lola.relative_to(ROOT)), "label": "data/raw/moon/ldem_80s_20m.lbl",
                        "bytes": lola.stat().st_size, "sha256": sha256(lola),
                        "source": "NASA PDS Geosciences Node, LRO LOLA gridded data record (DATA_SET_ID LRO-L-LOLA-4-GDR-V1.0)",
                        "product_id": "LDEM_80S_20M", "product_version": "V2.0 (label), created 2017-06-15",
                        "url": "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_80s_20m.img",
                        "instrument": "LRO Lunar Orbiter Laser Altimeter", "resolution_m": 20.0,
                        "crs": "Polar stereographic, lat of origin -90, central meridian 0, sphere R=1737.4 km",
                        "units": "int16 DN; height (m) = DN * 0.5 relative to 1737.4 km sphere (label SCALING_FACTOR 0.5, OFFSET 1737400)",
                        "nodata": -32768, "shape_rows_cols": [30400, 30400], "coverage": "80-90 S",
                        "quantisation": "0.5 m vertical step = 1.43 deg slope over one 20 m posting; ~0.48 deg over a 60 m central difference",
                        "access_date": ACCESS_DATE,
                        "license": "NASA PDS, public. Cite: Smith, D.E. et al. (2010) GRL 37, L18204 (LOLA); LRO LOLA GDR via PDS Geosciences Node."})
    fl = ROOT / "data/processed/meta/gate3_site_fetch.json"
    if fl.exists():
        fj = json.loads(fl.read_text())
        entries.append({"id": "earth_cop30_known_sites", "files": "data/raw/earth_cop30/sites/ks??_cop30.tif",
                        "source": "Copernicus DEM GLO-30 via OpenTopography globaldem API (demtype=COP30), one request per site",
                        "per_site": {k: v["cop30"] for k, v in fj.items()}, "resolution_m": "1 arc-second", "crs": "EPSG:4326",
                        "units": "metres", "access_date": ACCESS_DATE,
                        "license": "Copernicus DEM GLO-30: (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the EU and ESA."})
        entries.append({"id": "earth_nasadem_known_sites", "files": "data/raw/nasadem/NASADEM_HGT_*.zip",
                        "source": "NASA LP DAAC NASADEM_HGT v001 via earthaccess", "per_site": {k: v["nasadem"] for k, v in fj.items()},
                        "resolution_m": "1 arc-second", "crs": "EPSG:4326", "units": "metres", "access_date": ACCESS_DATE,
                        "license": "NASA data, no restrictions. doi:10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001"})
    cop_lic = "Copernicus DEM GLO-30: (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the EU and ESA."
    gm = ROOT / "data/processed/g3v/extract_meta.json"
    if gm.exists():
        g = json.loads(gm.read_text())
        entries.append({"id": "g3v_cop30_target_groups", "files": "data/raw/earth_cop30/g3v_targets/ring??_cop30.tif",
                        "source": "Copernicus GLO-30 via OpenTopography globaldem (demtype=COP30), one request per target group",
                        "files_detail": {x["ring_index"]: x["cop30_file"] for x in g["groups"]}, "resolution_m": "1 arc-second", "crs": "EPSG:4326",
                        "units": "metres", "access_date": "2026-11-15", "license": cop_lic})
        tiles = sorted({t for d in list(g["sites"].values()) + list(g["targets"].values()) for t in d["tiles"]})
        entries.append({"id": "g3v_3dep_windows_2m", "files": "data/processed/g3v/{sites,targets}/*_2m.npy (1.92 km, 2 m, float32, NaN nodata)",
                        "source": "USGS 3DEP 1 m DEM read from USGS S3 (TNM Access API), area-averaged to 2 m in EPSG:26911",
                        "product_ids": tiles, "resolution_m": 1.0, "resampled_to_m": 2.0, "crs": "EPSG:26911", "units": "metres",
                        "access_date": "2026-11-15", "license": "Public domain (U.S. Government work)."})
    nf = ROOT / "data/processed/meta/nasa_sites_fetch.json"
    if nf.exists():
        entries.append({"id": "nasa_test_sites_cop30", "files": "data/raw/earth_cop30/nasa_sites/*_cop30.tif",
                        "source": "Copernicus GLO-30 via OpenTopography globaldem", "per_site": json.loads(nf.read_text()),
                        "resolution_m": "1 arc-second", "crs": "EPSG:4326", "units": "metres", "access_date": "2026-11-15", "license": cop_lic})
    mods = sorted((ROOT / "data/raw/modis").glob("MOD13C2*.hdf"))
    if mods:
        entries.append({"id": "modis_mod13c2_2023_4months", "files": [str(m.relative_to(ROOT)) for m in mods],
                        "sha256": {m.name: sha256(m) for m in mods}, "bytes": {m.name: m.stat().st_size for m in mods},
                        "source": "NASA LP DAAC MOD13C2 v061 (Terra MODIS Vegetation Indices Monthly L3 Global 0.05 deg CMG) via earthaccess",
                        "product_ids": [m.stem for m in mods], "resolution_m": "0.05 deg (~5.6 km)", "crs": "geographic lat/lon (CMG)",
                        "units": "NDVI = DN * 0.0001; fill -3000", "access_date": "2026-11-15",
                        "license": "NASA data, no restrictions. Cite: Didan, K. (2021). MODIS/Terra Vegetation Indices Monthly L3 Global 0.05Deg CMG V061. doi:10.5067/MODIS/MOD13C2.061"})
    aws = sorted((ROOT / "data/raw/earth_cop30").glob("*/*.tif"))
    if any(p_.parent.name in ("usgs_all", "global") for p_ in aws):
        entries.append({"id": "cop30_aws_windows", "files": "data/raw/earth_cop30/usgs_all/*.tif, data/raw/earth_cop30/global/*.tif",
                        "source": "Copernicus GLO-30 DEM COGs, AWS Open Data registry (https://copernicus-dem-30m.s3.amazonaws.com), merged per window by src/cop30_aws.py",
                        "why": "OpenTopography key reached 50 calls/24 h; identical product (max |diff| 0.0011 m at Dumont)",
                        "resolution_m": "1 arc-second", "crs": "EPSG:4326", "units": "metres", "nodata": -32767.0,
                        "access_date": "2026-11-15", "license": cop_lic})
    entries.append({"id": "ref_lola_polar_candidates", "kind": "listing only (nothing downloaded)",
                    "source": "PDS Geosciences Node, LRO-L-LOLA-4-GDR-V1.0, polar stereographic LDEMs",
                    "url": "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/",
                    "products": {"LDEM_875S_5M": "5 m, 87.5-90S, 30336x30336, float 3,681,091,584 B / int16 1,840,545,792 B",
                                 "LDEM_875S_10M": "10 m, 87.5-90S, float 920,272,896 B / int16 460,136,448 B",
                                 "LDEM_875S_20M": "20 m, 87.5-90S, float 230,068,224 B / int16 115,034,112 B",
                                 "LDEM_85S_10M": "10 m, 85-90S, float 3,681,091,584 B / int16 1,840,545,792 B",
                                 "LDEM_85S_20M": "20 m, 85-90S, float 920,272,896 B / int16 460,136,448 B",
                                 "LDEM_80S_20M": "20 m, 80-90S, 30400x30400, float 3,696,640,000 B / int16 1,848,320,000 B"},
                    "access_date": ACCESS_DATE})
    az = ROOT / "data/raw/analog_sites/TerrestrialAnalogs.zip"
    if az.exists():
        entries.append({"id": "earth_usgs_known_terrestrial_analog_sites", "file": str(az.relative_to(ROOT)),
                        "unzipped": "data/raw/analog_sites/TerrestrialAnalogs/ (ESRI shapefile, POINT)",
                        "derived": "data/processed/analog_sites.json (records as JSON)",
                        "bytes": az.stat().st_size, "sha256": sha256(az),
                        "source": "Hunter, M.A. (2020) Known Terrestrial Analog Sites for Planetary Science, USGS Astrogeology data release, doi:10.5066/P9J72921 (ScienceBase item 5f88940b82cebb8c13d912ee)",
                        "obtained": "Downloaded manually by the author in a browser on 2026-11-14 (ScienceBase blocks scripted downloads); copied into the project unchanged",
                        "verification": "Matches official USGS metadata (data.usgs.gov USGS.5f88940b82cebb8c13d912ee.xml, saved in data/raw/analog_sites/official_metadata/): title, originator Marc A Hunter, pubdate 20201218, DOI, attribute fields Name/AnalogType/Lat/Lon/AnalogBody, point count 192. Embedded ArcGIS metadata CreaDate 20201015.",
                        "crs": "EPSG:3857 (WGS 84 / Web Mercator Auxiliary Sphere) geometry; Lat/Lon attribute columns in degrees",
                        "resolution_m": None, "units": "point sites", "n_records": 192,
                        "content": {"Impact Crater": 190, "Dunes": 1, "Volcanic Eruption": 1},
                        "known_issues": ["Record named 'Ritland' with AnalogType 'Volcanic Eruption' lies in Iceland (64.93 N, 16.52 W); geometry differs from its Lat/Lon attributes by 0.026 deg",
                                         "'Amboy' (34.5448, -115.791) is labelled Impact Crater; Amboy Crater, California is a volcanic cinder cone",
                                         "6 names occur twice at different coordinates: Boltysh, Clearwater East, Flaxman, Kamensk, Lockne, Ritland",
                                         "Zip entry timestamps are 2026-11-14 07:42 (archive repacked at download time)"],
                        "access_date": ACCESS_DATE,
                        "license": "Public domain (USGS). Cite: Hunter, M.A., 2020, Known Terrestrial Analog Sites for Planetary Science: U.S. Geological Survey data release, https://doi.org/10.5066/P9J72921."})

    entries.append({
        "id": "ref_msl_waypoints",
        "kind": "reference (not a DEM)",
        "source": "NASA/JPL MSL MMGIS waypoint layer (Curiosity localized end-of-drive positions)",
        "url": "https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json",
        "used_for": "Hidden Valley position (sols 705-713) and nominal-drive patch (sol 665)",
        "access_date": ACCESS_DATE, "license": "NASA/JPL public release",
    })
    entries.append({
        "id": "ref_hirise_dtm_index",
        "kind": "reference (not a DEM)",
        "source": "HiRISE PDS cumulative DTM index",
        "url": "https://hirise-pds.lpl.arizona.edu/PDS/INDEX/DTMCUMINDEX.TAB",
        "used_for": "Listing Gale crater DTM candidates (21 DTMs found in lat -6..-4, lon 137..138 E)",
        "access_date": ACCESS_DATE, "license": "NASA PDS, public",
    })
    entries.append({
        "id": "ref_place_coordinates",
        "kind": "reference (not a DEM)",
        "items": {
            "Dumont Dunes": {"lat": 35.67863, "lon": -116.23156, "datum": "NAD83",
                             "source": "TopoQuest place record (GNIS-derived), https://topoquest.com/place-detail.php?id=1667894"},
            "Avawatz Mountains": {"lat": 35.5069188, "lon": -116.2847431,
                                  "source": "TopoZone (GNIS-derived) https://www.topozone.com/california/san-bernardino-ca/range/avawatz-mountains/ ; cross-checked with Wikipedia 35 30 25 N 116 17 05 W"},
        },
        "access_date": ACCESS_DATE,
    })
    (ROOT / "data/manifest.json").write_text(json.dumps({"datasets": entries}, indent=2))
    print(f"wrote {len(entries)} entries")


if __name__ == "__main__":
    main()
