"""Stage 7.6C.2: ERA5 forcing coverage + unit-conversion tests.

Validates the expanded full-coverage ERA5 product for the real model grid:

- 100% coverage of the required forcing points (active wet cells, coup1-
  consistent mask; the same set the Fortran forcing interpolation visits).
- No silent extrapolation: points outside the ERA5 latitude range (the only
  hard failure in era5_bilinear2d) AND points outside the file's longitude
  span (edge-clamped = extrapolation) must be flagged as uncovered.
- ERA5 coordinate conventions: latitude stored decreasing (reader flips to
  increasing), longitude monotonic increasing.
- Unit conversions exactly as applied in src/wind_forcing.f90 era5_wind:
      msl  Pa -> hPa   (x 0.01)
      t2m  K  -> degC  (- 273.15)
      wind m/s -> cm/s (x 100)
- Required forcing variables all present (u10, v10, t2m, d2m, msl, tcc, sf).

Run directly (pytest also collects the test_* functions):

    conda run -n iceberg-thermodynamic-model python python/tests/test_era5_coverage.py
"""

import sys
from pathlib import Path

import numpy as np

PROJ_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ_ROOT / "python" / "era5"))
sys.path.insert(0, str(PROJ_ROOT / "python" / "ice"))

from model_coverage import (  # noqa: E402
    PROJ_ROOT as _PC,
    covered_point,
    era5_extent,
    load_model_geometry,
)

EXPANDED = (
    _PC
    / "data/input/processed/era5/2020/2020_01"
    / "era5_2020_01_fullcoverage_d1_4_merged.nc"
)
LEGACY_Q1 = (
    _PC
    / "data/input/processed/era5/2020/2020_Q1"
    / "era5_2020_0103_barents_expanded_merged.nc"
)


def _load(file):
    import xarray as xr

    return xr.open_dataset(file)


def _required_points():
    lat, lon, wet = load_model_geometry()
    active = np.zeros_like(wet, dtype=bool)
    active[:132, :104] = True
    return lat, lon, wet & active


def _point_mask(lat, lon, pts, ext):
    lat_min, lat_max, lon_min, lon_max = ext
    l = lat[pts].ravel()
    lo = lon[pts].ravel()
    return np.array(
        [covered_point(a, b, lat_min, lat_max, lon_min, lon_max) for a, b in zip(l, lo)]
    )


def test_expanded_file_100pct_coverage():
    """The expanded forcing must cover every required forcing point."""
    if not EXPANDED.exists():
        raise AssertionError(f"expanded ERA5 not present: {EXPANDED}")
    lat, lon, req = _required_points()
    with _load(EXPANDED) as ds:
        ext = era5_extent(ds)
    n = int(req.sum())
    assert n == 10966, f"expected 10966 required points, got {n}"
    cov = _point_mask(lat, lon, req, ext)
    assert cov.all(), f"{int((~cov).sum())} required points uncovered"


def test_legacy_file_is_not_fully_covered():
    """The old 66N/10-70E file must still be flagged as incomplete.

    Guards that the coverage test discriminates and would have failed on the
    pre-Stage-7.6C.2 ERA5 domain.
    """
    if not LEGACY_Q1.exists():
        raise AssertionError(f"legacy Q1 file not present: {LEGACY_Q1}")
    with _load(LEGACY_Q1) as ds:
        ext = era5_extent(ds)
    lat, lon, req = _required_points()
    cov = _point_mask(lat, lon, req, ext)
    assert int((~cov).sum()) > 0
    assert cov.mean() < 0.96


def test_no_silent_extrapolation_latitude():
    """A point south of the ERA5 latitude floor is uncovered (Fortran zeroes it)."""
    ext = era5_extent(_load(EXPANDED))
    assert ext[0] >= 63.0  # sanity: file starts at 63N
    assert not covered_point(ext[0] - 0.30, 30.0, *ext)


def test_no_silent_extrapolation_longitude():
    """A point outside the file's longitude span is uncovered (edge-clamp)."""
    ext = era5_extent(_load(EXPANDED))
    assert not covered_point(70.0, ext[3] + 1.0, *ext)


def test_era5_coordinate_convention():
    """Fortran reader requires: raw lat decreasing, lon increasing."""
    with _load(EXPANDED) as ds:
        lat = ds["latitude"].values
        lon = ds["longitude"].values
    assert lat[0] > lat[-1], "raw file latitude must be decreasing (90..63)"
    assert np.all(np.diff(lon) > 0)
    ext = era5_extent(ds)
    assert ext[0] < ext[1]  # reader flips lat -> reported extent increasing


def test_unit_conversions_pa_hpa():
    """msl: Pa -> hPa (x 0.01), as in era5_wind p1 = msl*0.01."""
    pa = np.array([94689.8125, 98718.15625, 101888.5625], dtype=np.float64)
    assert np.allclose(pa * 0.01, [946.898125, 987.1815625, 1018.885625])


def test_unit_conversions_k_to_c():
    """t2m: K -> degC (-273.15), as in era5_wind tatm = t2m - 273.15."""
    k = np.array([241.30598, 259.52599, 284.379], dtype=np.float64)
    assert np.allclose(k - 273.15, [-31.84402, -13.62401, 11.229])


def test_unit_conversions_ms_to_cm_s():
    """u10/v10: m/s -> cm/s (x 100), as in era5_wind u_cm = u10*100."""
    ms = np.array([-22.2667, 21.7828], dtype=np.float64)
    assert np.allclose(ms * 100.0, [-2226.67, 2178.28])


def test_required_variables_present():
    """The variables consumed by the model forcing must all be present."""
    expect = {"u10", "v10", "t2m", "d2m", "msl", "tcc", "sf"}
    with _load(EXPANDED) as ds:
        have = set(ds.data_vars)
    assert expect.issubset(have), f"missing {expect - have}; have {have}"


_CHECKS = [
    test_expanded_file_100pct_coverage,
    test_legacy_file_is_not_fully_covered,
    test_no_silent_extrapolation_latitude,
    test_no_silent_extrapolation_longitude,
    test_era5_coordinate_convention,
    test_unit_conversions_pa_hpa,
    test_unit_conversions_k_to_c,
    test_unit_conversions_ms_to_cm_s,
    test_required_variables_present,
]


def main():
    failures = 0
    for fn in _CHECKS:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    if failures:
        print(f"\n{len(_CHECKS) - failures}/{len(_CHECKS)} passed; {failures} FAILURES")
        return 1
    print(f"\nOK: {len(_CHECKS)}/{len(_CHECKS)} ERA5 coverage/conversion checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
