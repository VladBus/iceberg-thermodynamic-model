#!/usr/bin/env python3
"""
Stage 7.2: Snowfall Mass-Balance Diagnostic Script

Computes snowfall input, snow storage, and mass-balance closure
for a given model run.

Usage:
    python python/analysis/snowfall_mass_balance.py --run-id <run_id> [--day-start N] [--day-end N]
"""

import argparse
import numpy as np
import xarray as xr
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Snowfall mass-balance diagnostics")
    parser.add_argument(
        "--run-id", required=True, help="Run ID (e.g., 2020_Q1_snowfall_ERA5_5day)"
    )
    parser.add_argument(
        "--day-start", type=int, default=1, help="Start day (default: 1)"
    )
    parser.add_argument(
        "--day-end", type=int, default=None, help="End day (default: all available)"
    )
    parser.add_argument(
        "--output-dir", default=None, help="Output directory (default: run figures dir)"
    )
    return parser.parse_args()


def find_day_files(run_dir, day_start, day_end):
    """Find all day NetCDF files in range."""
    nc_dir = Path(run_dir) / "output" / "nc"
    files = []
    for day in range(day_start, day_end + 1):
        f = nc_dir / f"results_day_{day:02d}.nc"
        if f.exists():
            files.append((day, f))
    return files


def compute_snowfall_stats(ds):
    """Compute snowfall statistics from a dataset."""
    sf = ds["era5_snowfall_rate"].values  # m/s
    kt1 = ds["water_column_levels"].values
    sd = ds["snow_depth"].values  # (5, 105, 133)
    ic = ds["ice_concentration"].values  # (5, 105, 133)

    water = kt1 > 0
    ice_mask = np.nansum(ic, axis=0) > 0.001
    snow_mask = np.any(sd > 0.001, axis=0)

    # Daily snowfall input (m/s * 86400 = m/day)
    sf_daily = sf * 86400.0  # m/day
    cell_area = 13.89e3 * 13.89e3  # m^2

    stats = {}
    stats["sf_global_mean"] = float(np.nanmean(sf))
    stats["sf_water_mean"] = float(np.nanmean(sf[water]))
    stats["sf_ice_mean"] = float(np.nanmean(sf[ice_mask]))
    stats["sf_global_std"] = float(np.nanstd(sf))
    stats["sf_water_std"] = float(np.nanstd(sf[water]))
    stats["sf_ice_std"] = float(np.nanstd(sf[ice_mask]))
    stats["sf_global_cv"] = (
        float(np.nanstd(sf) / np.nanmean(sf)) if np.nanmean(sf) > 0 else 0
    )
    stats["sf_water_cv"] = (
        float(np.nanstd(sf[water]) / np.nanmean(sf[water]))
        if np.nanmean(sf[water]) > 0
        else 0
    )
    stats["sf_ice_cv"] = (
        float(np.nanstd(sf[ice_mask]) / np.nanmean(sf[ice_mask]))
        if np.nanmean(sf[ice_mask]) > 0
        else 0
    )

    # Snowfall volume (m^3/day)
    stats["sf_volume_total"] = float(np.nansum(sf_daily) * cell_area)
    stats["sf_volume_water"] = float(np.nansum(sf_daily[water]) * cell_area)
    stats["sf_volume_ice"] = float(np.nansum(sf_daily[ice_mask]) * cell_area)

    # Snow storage
    sd_total = np.nansum(sd, axis=0)
    stats["storage_total"] = float(np.nansum(sd_total[water]) * cell_area)
    stats["storage_ice"] = float(np.nansum(sd_total[ice_mask]) * cell_area)
    stats["mean_sd_ice"] = float(np.nanmean(sd_total[ice_mask]))
    stats["max_sd"] = float(np.nanmax(sd_total))

    # Areas
    stats["n_water"] = int(np.sum(water))
    stats["n_ice"] = int(np.sum(ice_mask))
    stats["n_snow"] = int(np.sum(snow_mask))

    # Percentiles
    sf_ice = sf[ice_mask]
    sf_ice = sf_ice[~np.isnan(sf_ice)]
    if len(sf_ice) > 0:
        for p in [10, 25, 50, 75, 90, 95, 99]:
            stats[f"sf_ice_p{p}"] = float(np.percentile(sf_ice, p))

    return stats


def compute_correlation(ds):
    """Compute spatial correlation between snowfall rate and snow depth."""
    sf = ds["era5_snowfall_rate"].values
    kt1 = ds["water_column_levels"].values
    sd = ds["snow_depth"].values
    ic = ds["ice_concentration"].values

    water = kt1 > 0
    ice_mask = np.nansum(ic, axis=0) > 0.001
    sd_total = np.nansum(sd, axis=0)

    results = {}

    # Over ice cells
    sf_ice = sf[ice_mask]
    sd_ice = sd_total[ice_mask]
    valid = ~np.isnan(sf_ice) & ~np.isnan(sd_ice)
    if np.sum(valid) > 10:
        results["corr_ice"] = float(np.corrcoef(sf_ice[valid], sd_ice[valid])[0, 1])
        results["n_ice"] = int(np.sum(valid))

    # Over water cells
    sf_water = sf[water]
    sd_water = sd_total[water]
    valid = ~np.isnan(sf_water) & ~np.isnan(sd_water)
    if np.sum(valid) > 10:
        results["corr_water"] = float(
            np.corrcoef(sf_water[valid], sd_water[valid])[0, 1]
        )
        results["n_water"] = int(np.sum(valid))

    return results


def main():
    args = parse_args()

    run_dir = Path(f"data/runs/{args.run_id}")
    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}")
        return 1

    # Find day files
    day_files = []
    nc_dir = run_dir / "output" / "nc"
    for f in sorted(nc_dir.glob("results_day_*.nc")):
        day_str = f.stem.split("_")[-1]
        if day_str.isdigit():
            day = int(day_str)
            if day >= args.day_start and (args.day_end is None or day <= args.day_end):
                day_files.append((day, f))

    if not day_files:
        print("No day files found")
        return 1

    print(f"Analyzing run: {args.run_id}")
    print(f"Days: {args.day_start} to {args.day_end or 'end'}")
    print(f"Found {len(day_files)} day files")
    print()

    # Load day 0 for initial storage
    ds0 = xr.open_dataset(run_dir / "output" / "nc" / "results_day_00.nc")
    sd0 = ds0["snow_depth"].values
    ic0 = ds0["ice_concentration"].values
    kt1 = ds0["water_column_levels"].values
    water = kt1 > 0
    ice_mask0 = np.nansum(ic0, axis=0) > 0.001
    sd0_total = np.nansum(sd0, axis=0)
    storage0_total = np.nansum(sd0_total[water]) * (13.89e3 * 13.89e3)
    storage0_ice = np.nansum(sd0_total[ice_mask0]) * (13.89e3 * 13.89e3)
    ds0.close()

    print("Day 0 (initial):")
    print(f"  Storage total: {storage0_total:.2e} m^3")
    print(f"  Storage ice:   {storage0_ice:.2e} m^3")
    print()

    # Process each day
    cumulative_input = 0.0
    prev_storage = storage0_total

    print("=" * 100)
    print(
        f"{'Day':>4} {'SF_in(m3/d)':>14} {'SF_in_ice(m3/d)':>16} {'Storage(m3)':>14} {'dStorage(m3)':>14} {'Residual(m3)':>14} {'Closure':>8} {'Corr_ice':>10}"
    )
    print("=" * 100)

    for day, f in day_files:
        ds = xr.open_dataset(f)

        stats = compute_snowfall_stats(ds)
        corr = compute_correlation(ds)

        cumulative_input += stats["sf_volume_total"]
        storage = stats["storage_total"]
        delta_storage = storage - prev_storage
        residual = stats["sf_volume_total"] - delta_storage
        closure = (
            delta_storage / stats["sf_volume_total"]
            if stats["sf_volume_total"] > 0
            else 0
        )

        corr_ice = corr.get("corr_ice", np.nan)

        print(
            f"{day:4d} {stats['sf_volume_total']:14.2e} {stats['sf_volume_ice']:16.2e} {storage:14.2e} {delta_storage:14.2e} {residual:14.2e} {closure:8.2f} {corr_ice:10.4f}"
        )

        prev_storage = storage
        ds.close()

    print("=" * 100)
    print(f"\nCumulative snowfall input: {cumulative_input:.2e} m^3")
    print(f"Final storage: {prev_storage:.2e} m^3")
    print(f"Total residual: {cumulative_input - prev_storage:.2e} m^3")

    # Category-level analysis for last day
    print("\n--- Category-level analysis (last day) ---")
    ds = xr.open_dataset(day_files[-1][1])
    sd = ds["snow_depth"].values
    ic = ds["ice_concentration"].values
    it = ds["ice_thickness"].values

    for k in range(5):
        print(
            f"  Cat {k}: mean_sd={np.nanmean(sd[k]):.4e}, max_sd={np.nanmax(sd[k]):.4f}, "
            f"mean_ic={np.nanmean(ic[k]):.4f}, max_ic={np.nanmax(ic[k]):.4f}, "
            f"mean_it={np.nanmean(it[k]):.4f}, max_it={np.nanmax(it[k]):.4f}"
        )

    ds.close()

    return 0


if __name__ == "__main__":
    exit(main())
