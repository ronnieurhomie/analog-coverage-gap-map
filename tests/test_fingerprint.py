# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fingerprint import fingerprint, hillshade, to_common_grid  # noqa: E402
from rasterio.transform import Affine  # noqa: E402

PIX = 2.0
SCALES = [2.0, 8.0, 32.0, 64.0]
N = 512


def grid():
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    return xx * PIX, yy * PIX


def test_flat_plane_has_zero_slope_and_roughness():
    fp = fingerprint(np.full((N, N), 123.0), PIX, SCALES)
    for s in SCALES:
        st = fp["scales"][str(s)]
        assert st["slope_deg"]["median"] == pytest.approx(0, abs=1e-9)
        assert st["slope_deg"]["p90"] == pytest.approx(0, abs=1e-9)
        if s > PIX:
            assert st["roughness_m"]["median"] == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("deg", [5.0, 20.0, 35.0])
def test_tilted_plane_known_slope(deg):
    x, y = grid()
    dem = np.tan(np.radians(deg)) * (0.6 * x + 0.8 * y)  # unit direction, any azimuth
    fp = fingerprint(dem, PIX, SCALES)
    for s in SCALES:
        st = fp["scales"][str(s)]
        assert st["slope_deg"]["median"] == pytest.approx(deg, abs=1e-6)
        assert st["slope_deg"]["iqr"] == pytest.approx(0, abs=1e-6)
        if s > PIX:  # a plane is fully removed by detrending
            assert st["roughness_m"]["median"] == pytest.approx(0, abs=1e-6)


def test_sinusoid_roughness_scales_as_expected():
    amp, lam = 1.5, 64.0  # metres
    x, _ = grid()
    dem = amp * np.sin(2 * np.pi * x / lam)
    fp = fingerprint(dem, PIX, [4.0, 8.0, 16.0, 32.0, 64.0, 128.0])
    r = [fp["scales"][str(s)]["roughness_m"]["median"] for s in [4.0, 8.0, 16.0, 32.0, 64.0]]
    # roughness grows with window size while the window is shorter than the wavelength
    assert all(b > a for a, b in zip(r, r[1:]))
    # window = n whole wavelengths: the plane fit removes the sine's linear trend, leaving
    # std = A * sqrt(1/2 - 3 / (n^2 pi^2)), which tends to A/sqrt(2) as n grows
    for n, s in [(1, 64.0), (2, 128.0)]:
        expected = amp * np.sqrt(0.5 - 3 / (n**2 * np.pi**2))
        assert fp["scales"][str(s)]["roughness_m"]["median"] == pytest.approx(expected, rel=0.02)
    # tiny windows see almost nothing
    assert r[0] < 0.05 * amp


def test_nodata_is_ignored():
    x, y = grid()
    dem = np.tan(np.radians(10)) * x
    dem[:100, :100] = -9999.0
    fp = fingerprint(dem, PIX, [8.0, 32.0], nodata=-9999.0)
    assert fp["valid_fraction"] < 1
    for s in ["8.0", "32.0"]:
        assert fp["scales"][s]["slope_deg"]["median"] == pytest.approx(10, abs=1e-6)
        assert fp["scales"][s]["slope_deg"]["p90"] == pytest.approx(10, abs=1e-6)


def test_common_grid_preserves_slope():
    # 1 m tilted plane resampled to 2 m keeps its slope
    yy, xx = np.mgrid[0:400, 0:400].astype(float)
    dem = np.tan(np.radians(15)) * xx  # 1 m pixels
    out, tr = to_common_grid(dem, Affine(1, 0, 0, 0, -1, 400), "EPSG:32611", None, 2.0)
    assert tr.a == 2.0 and out.shape == (200, 200)
    fp = fingerprint(out, 2.0, [8.0])
    assert fp["scales"]["8.0"]["slope_deg"]["median"] == pytest.approx(15, abs=0.01)


def test_hillshade_lit_from_northwest():
    x, y = grid()
    facing_nw = 0.3 * (x + y)   # rises to the south-east, so faces north-west
    facing_se = -facing_nw
    assert np.nanmean(hillshade(facing_nw, PIX)) > np.nanmean(hillshade(facing_se, PIX))
