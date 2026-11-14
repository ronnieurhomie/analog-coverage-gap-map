# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Gate 2 ranking: Method A (fingerprint, z-score Euclidean + Gate 1 relative difference),
Method B (DINOv2-small hillshade embeddings, cosine), and the COP30 30 m vs 2 m consistency check.

All choices below were fixed before any ranking was computed:
  * Method A features: slope median/P90/IQR at 2,4,8,16,32,64 m + roughness median at 4..64 m (23).
    z-score uses mean/std over the Earth candidate set; same transform applied to Mars patches.
  * Method B: hillshade (az 315, alt 30) of the 2 m patch, fixed contrast (hillshade value in [0,1]
    mapped linearly to 0..255, no per-image stretch), 128x128 px bilinear-upsampled to 224x224,
    grey replicated to 3 channels, ImageNet normalisation (AutoImageProcessor with resize/crop off),
    embedding = CLS token of the last hidden state of facebook/dinov2-small; cosine distance.
  * COP30 check: same 256 m footprints (centres); COP30 reprojected to UTM 11N at 30 m (bilinear);
    Mars DTM area-averaged to 30 m; features = slope median/P90/IQR at 30 m and 60 m (roughness is
    not computable with so few 30 m pixels). A second variant uses a 960 m footprint with slope at
    30/60/120 m + roughness median at 60/120 m. Ranking = z-score Euclidean to mars_sand, as primary.
    Spearman rho between the 30 m and 2 m (Method A primary) candidate rankings.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.transform import Affine
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fingerprint import fingerprint, hillshade, to_common_grid  # noqa: E402
import gate1_smoke as g1  # noqa: E402  (Mars cut helper)

ROOT = Path(__file__).resolve().parents[1]
SCALES = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0]
GRID_M = 2.0
MARS_NAMES = ["mars_sand", "mars_nominal", "mars_hidden_valley_limitation"]
COP30 = ROOT / "data/raw/earth_cop30/cop30_gate2_area.tif"


def vec(fp, scales=SCALES):
    v = []
    for s in map(str, scales):
        st = fp["scales"][s]
        v += [st["slope_deg"]["median"], st["slope_deg"]["p90"], st["slope_deg"]["iqr"]]
        if st["roughness_m"]["median"] is not None:
            v.append(st["roughness_m"]["median"])
    return np.array(v, dtype=float)


def reldiff(a, b):
    den = np.abs(a) + np.abs(b)
    return float(np.mean(np.where(den > 0, np.abs(a - b) / np.where(den > 0, den, 1), 0)))


def zdist(cand: dict[str, np.ndarray], ref: np.ndarray) -> dict[str, float]:
    M = np.stack(list(cand.values()))
    mu, sd = M.mean(0), M.std(0)
    sd[sd == 0] = 1
    r = (ref - mu) / sd
    return {k: float(np.linalg.norm((v - mu) / sd - r)) for k, v in cand.items()}


def ranks(d: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(d.items(), key=lambda kv: kv[1])


def rank_of(d, name):
    return [k for k, _ in ranks(d)].index(name) + 1


# ---------- Method B ----------
def embed_all(patches: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    import torch
    from transformers import AutoImageProcessor, AutoModel
    proc = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
    model = AutoModel.from_pretrained("facebook/dinov2-small").eval()
    out = {}
    for k, p in patches.items():
        hs = hillshade(np.where(np.isfinite(p), p, np.nanmean(p)), GRID_M, 315.0, 30.0)
        img = (np.clip(hs, 0, 1) * 255).astype(np.float32)
        t = torch.from_numpy(img)[None, None]
        t = torch.nn.functional.interpolate(t, size=(224, 224), mode="bilinear", align_corners=False)[0, 0].numpy()
        rgb = np.repeat(np.clip(t, 0, 255).astype(np.uint8)[..., None], 3, axis=2)
        inp = proc(images=rgb, return_tensors="pt", do_resize=False, do_center_crop=False)
        with torch.no_grad():
            h = model(**inp).last_hidden_state[0, 0].numpy()
        out[k] = h / np.linalg.norm(h)
    return out


# ---------- COP30 ----------
def cop30_patch(lat, lon, size_m):
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:26911", always_xy=True)
    x, y = to_utm.transform(lon, lat)
    n = int(round(size_m / 30.0))
    tr = Affine(30.0, 0, x - n * 15.0, 0, -30.0, y + n * 15.0)
    dst = np.full((n, n), np.nan, dtype=np.float32)
    with rasterio.open(COP30) as d:
        reproject(rasterio.band(d, 1), dst, dst_transform=tr, dst_crs="EPSG:26911", dst_nodata=np.nan,
                  resampling=Resampling.bilinear)
    return dst


def mars30(lat, lon, size_m):
    with rasterio.open(g1.MARS_DTM) as d:
        a, _ = g1.cut(g1.MARS_DTM, lat, lon, size_m=size_m + 64)  # 2 m grid with margin
    # area-average 2 m -> 30 m (non-integer: use reproject on a local metric grid)
    n = int(round(size_m / 30.0))
    k = a.shape[0]
    src_tr = Affine(2.0, 0, -k, 0, -2.0, k)
    dst_tr = Affine(30.0, 0, -n * 15.0, 0, -30.0, n * 15.0)
    dst = np.full((n, n), np.nan, dtype=np.float32)
    reproject(a.astype(np.float32), dst, src_transform=src_tr, src_crs="EPSG:32611", dst_transform=dst_tr,
              dst_crs="EPSG:32611", src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.average)
    return dst


def main():
    cands = json.loads((ROOT / "results/candidates.json").read_text())
    spec = json.loads((ROOT / "data/processed/meta/gate2_patches.json").read_text())["patches"]
    earth = {c["name"]: np.load(ROOT / c["file"]) for c in cands["candidates"]}
    meta = {c["name"]: c for c in cands["candidates"]}
    mars = {n: g1.cut(g1.MARS_DTM, spec[n]["lat"], spec[n]["lon"])[0] for n in MARS_NAMES}
    N = len(earth)
    top_k = math.ceil(0.10 * N)

    fps = {k: fingerprint(v, GRID_M, SCALES) for k, v in {**earth, **mars}.items()}
    V = {k: vec(f) for k, f in fps.items()}
    E = {k: V[k] for k in earth}
    res = {"n_candidates": N, "top10pct_rank_threshold": top_k, "preregistration": cands["preregistration"],
           "method_notes": __doc__.strip(), "change_log": []}

    # Method A
    dA = zdist(E, V["mars_sand"])
    dA2 = {k: reldiff(v, V["mars_sand"]) for k, v in E.items()}
    res["A_primary_zscore"] = {"dumont_rank": rank_of(dA, "dumont"), "negctrl_rank": rank_of(dA, "avawatz_negctrl"),
                               "ranking": [{"rank": i + 1, "name": k, "dist": round(d, 4), "lat": meta[k]["lat"], "lon": meta[k]["lon"]}
                                           for i, (k, d) in enumerate(ranks(dA))]}
    res["A_secondary_reldiff"] = {"dumont_rank": rank_of(dA2, "dumont"), "negctrl_rank": rank_of(dA2, "avawatz_negctrl"),
                                  "ranking": [{"rank": i + 1, "name": k, "dist": round(d, 4)} for i, (k, d) in enumerate(ranks(dA2))]}
    res["pass_primary"] = res["A_primary_zscore"]["dumont_rank"] <= top_k
    # Mars-Mars distances under A (same z transform)
    allz = zdist({**E, "mars_nominal": V["mars_nominal"], "mars_hidden_valley_limitation": V["mars_hidden_valley_limitation"]}, V["mars_sand"])
    M = np.stack(list(E.values())); mu, sd = M.mean(0), M.std(0); sd[sd == 0] = 1
    zz = lambda v: (v - mu) / sd
    res["mars_pairs_A_zscore"] = {n: float(np.linalg.norm(zz(V[n]) - zz(V["mars_sand"]))) for n in MARS_NAMES[1:]}
    res["mars_pairs_A_reldiff"] = {n: reldiff(V[n], V["mars_sand"]) for n in MARS_NAMES[1:]}
    res["fingerprints"] = {k: {"slope_median_deg": {s: fps[k]["scales"][str(s)]["slope_deg"]["median"] for s in SCALES},
                               "roughness_median_m": {s: fps[k]["scales"][str(s)]["roughness_m"]["median"] for s in SCALES}}
                           for k in ["dumont", "avawatz_negctrl", *MARS_NAMES]}

    # Method B
    try:
        emb = embed_all({**earth, **mars})
        dB = {k: float(1 - emb[k] @ emb["mars_sand"]) for k in earth}
        res["B_dinov2_cosine"] = {"dumont_rank": rank_of(dB, "dumont"), "negctrl_rank": rank_of(dB, "avawatz_negctrl"),
                                  "pass_same_criterion": rank_of(dB, "dumont") <= top_k,
                                  "ranking": [{"rank": i + 1, "name": k, "dist": round(d, 4), "lat": meta[k]["lat"], "lon": meta[k]["lon"]}
                                              for i, (k, d) in enumerate(ranks(dB))]}
        res["mars_pairs_B"] = {n: float(1 - emb[n] @ emb["mars_sand"]) for n in MARS_NAMES[1:]}
        res["spearman_A_vs_B"] = float(spearmanr([dA[k] for k in earth], [dB[k] for k in earth])[0])
    except Exception as e:
        res["B_dinov2_cosine"] = {"error": f"{type(e).__name__}: {e}"}

    # COP30 consistency
    for label, size, scales in [("cop30_256m_footprint", 256.0, [30.0, 60.0]), ("cop30_960m_footprint", 960.0, [30.0, 60.0, 120.0])]:
        f30 = {k: vec(fingerprint(cop30_patch(meta[k]["lat"], meta[k]["lon"], size), 30.0, scales), scales) for k in earth}
        m30 = vec(fingerprint(mars30(spec["mars_sand"]["lat"], spec["mars_sand"]["lon"], size), 30.0, scales), scales)
        d30 = zdist(f30, m30)
        rho = spearmanr([d30[k] for k in earth], [dA[k] for k in earth])
        res[label] = {"features_per_patch": int(len(m30)), "spearman_vs_2m_A": float(rho[0]), "p_value": float(rho[1]),
                      "dumont_rank_30m": rank_of(d30, "dumont"),
                      "top5_30m": [k for k, _ in ranks(d30)[:5]]}

    (ROOT / "results/gate2_ranking.json").write_text(json.dumps(res, indent=2))
    np.savez(ROOT / "data/processed/gate2_patches_2m.npz", **{**earth, **mars})
    print(json.dumps({k: v for k, v in res.items() if k not in ("fingerprints", "method_notes", "preregistration")}, indent=1)[:6000])


if __name__ == "__main__":
    main()
