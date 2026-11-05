#!/usr/bin/env python3
"""CI-safe tests for ERA5 hourly -> daily aggregation."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "era5_daily", ROOT / "python/era5/download_era5_daily.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_ds(nhours: int = 24) -> xr.Dataset:
    t = pd.date_range("2020-01-01", periods=nhours, freq="h")
    shape = (nhours, 2, 2)
    return xr.Dataset({
        "10m_u_component_of_wind": (("time", "latitude", "longitude"), np.ones(shape)),
        "10m_v_component_of_wind": (("time", "latitude", "longitude"), np.ones(shape) * 2),
        "2m_temperature": (("time", "latitude", "longitude"), np.ones(shape) * 270),
        "2m_dewpoint_temperature": (("time", "latitude", "longitude"), np.ones(shape) * 265),
        "total_cloud_cover": (("time", "latitude", "longitude"), np.ones(shape) * 0.5),
        "mean_sea_level_pressure": (("time", "latitude", "longitude"), np.ones(shape) * 101325),
        "snowfall": (("time", "latitude", "longitude"), np.ones(shape) * 0.001),
    }, coords={"time": t})


def main() -> None:
    d = mod.aggregate(make_ds())
    assert d.sizes["time"] == 1
    assert np.isclose(float(d.t2m.values[0, 0, 0]), 270.0)
    assert np.isclose(float(d.sf.values[0, 0, 0]), 24 * 0.001 / 86400.0)
    assert d.sf.attrs["units"] == "m s-1"
    assert d.time.values[0] == 1577836800.0
    try:
        mod.aggregate(make_ds(23))
    except RuntimeError as e:
        assert "incomplete" in str(e)
    else:
        raise AssertionError("incomplete 23-hour window was accepted")
    print("SUCCESS: ERA5 daily aggregation tests passed")


if __name__ == "__main__":
    main()
