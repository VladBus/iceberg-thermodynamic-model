#!/usr/bin/env python
"""Hot-run day_00 vs day_03 ice/ocean aggregates (Stage 7.6C.2).

Reads the real-ice + expanded-ERA5 3-day hot run NetCDF outputs and reports:
  - ice area, mean SIC, mean SIT, total volume (m^3)
  - category resolved area & volume distribution
  - snow depth vs cumulative ERA5 snowfall
  - ocean T/S ranges
  - NaN/Inf scan across all 3D/scalar fields

Usage:
  python python/analysis/hot_run_ice_aggregates.py \
      --nc-dir data/runs/hot_run_20200101_3d_realice/output/nc \
      [--days 0 3]
  Writes <nc-dir>/../analysis/ice_days_00_03.json
"""

import json
import argparse
from pathlib import Path

import numpy as np
import xarray as xr

LAND = 8888.0
CELL_AREA = 13890.0 * 13890.0  # m^2


def is_water(da):
    """True where cell is not masked land marker."""
    return np.abs(da - LAND) > 1e-8


def scan_nan(da):
    return int(float(np.isnan(da).sum())), int(float(np.isinf(da).sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc-dir", required=True)
    ap.add_argument("--days", nargs="+", type=int, default=[0, 3])
    args = ap.parse_args()

    nc_dir = Path(args.nc_dir)
    out_dir = nc_dir.parent / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = {}
    for d in args.days:
        ds = xr.open_dataset(nc_dir / f"results_day_{d:02d}.nc")
        w = is_water(ds["water_column_levels"])
        frames[d] = (ds, w)

    report = {"run": nc_dir.parent.name, "days": args.days, "cell_area_m2": CELL_AREA}
    for d in args.days:
        ds, w = frames[d]
        area = w.sum().item() * CELL_AREA

        conc = ds["ice_concentration"]  # (cat, y, x)
        thick = ds["ice_thickness"]
        sdepth = ds["snow_depth"]

        an1 = conc.where(w, 0.0)
        hbars = thick.where(w, 0.0)
        wice_col = (an1 * hbars).sum("ice_category")

        ice_cells = an1.sum("ice_category").where(w, 0.0)
        mask = ice_cells >= 0.005
        n_ice = int(mask.sum().item())
        sic = float(ice_cells.where(mask).mean().item()) if n_ice else float("nan")
        sit = (
            float((wice_col / ice_cells).where(mask).mean().item())
            if n_ice
            else float("nan")
        )
        volume = float(wice_col.sum().item() * CELL_AREA)

        cat_conc = np.array(an1.sum(dim=("y", "x")).values)
        cat_vol = np.array((an1 * hbars).sum(dim=("y", "x")).values * CELL_AREA)
        cat_area = np.array(an1.sum(dim=("y", "x")).values)
        cat_hbar = np.divide(
            cat_vol, CELL_AREA * cat_area, out=np.full(5, np.nan), where=cat_area > 0
        )
        snow = float(sdepth.where(w, 0.0).sum().item() * CELL_AREA)

        t = ds["temperature"]
        s = ds["salinity_mass_fraction"]
        tw = t.where(w)
        sw = s.where(w)

        f = {
            "water_area_m2": float(area),
            "ice_cells": n_ice,
            "mean_sic": sic,
            "mean_sit_m": sit,
            "ice_volume_m3": volume,
            "category_area_fraction": [float(a) for a in np.atleast_1d(cat_conc)],
            "category_volume_m3": [float(v) for v in np.atleast_1d(cat_vol)],
            "category_mean_thickness_m": [float(a) for a in np.atleast_1d(cat_hbar)],
            "snow_volume_m3": snow,
            "temp_min_c": float(tw.min().item()) - 273.15,
            "temp_max_c": float(tw.max().item()) - 273.15,
            "sal_min": float(sw.min().item()),
            "sal_max": float(sw.max().item()),
        }
        report[f"day_{d:02d}"] = f
        report[f"day_{d:02d}_nan_inf"] = {
            "temperature": scan_nan(t),
            "salinity": scan_nan(s),
            "ice_concentration": scan_nan(ds["ice_concentration"]),
            "ice_thickness": scan_nan(ds["ice_thickness"]),
            "snow_depth": scan_nan(ds["snow_depth"]),
            "u_velocity": scan_nan(ds["u_velocity"]),
            "v_velocity": scan_nan(ds["v_velocity"]),
        }

    # ERA5 forcing diagnostics at last integration day
    dlast = args.days[-1]
    ds, w = frames[dlast]
    report["forcing_day_last"] = {
        "wind_speed_min": float(ds["wind_speed"].where(w).min().item()),
        "wind_speed_max": float(ds["wind_speed"].where(w).max().item()),
        "wind_speed_mean": float(ds["wind_speed"].where(w).mean().item()),
        "tau_x_min": float(ds["tau_x"].where(w).min().item() * 1.0e-1),  # dyn/cm2 -> Pa
        "tau_x_max": float(ds["tau_x"].where(w).max().item() * 1.0e-1),
        "air_press_min_Pa": float(ds["air_press"].where(w).min().item()),
        "air_press_max_Pa": float(ds["air_press"].where(w).max().item()),
        "air_temp_min_c": float(ds["air_temp"].where(w).min().item()) - 273.15,
        "air_temp_max_c": float(ds["air_temp"].where(w).max().item()) - 273.15,
        "snowfall_rate_mean_m_s": float(
            ds["era5_snowfall_rate"].where(w).mean().item()
        ),
    }

    out_json = out_dir / "ice_days_00_03.json"
    out_json.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"wrote: {out_json}")


if __name__ == "__main__":
    main()
