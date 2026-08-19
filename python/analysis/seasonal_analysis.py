#!/usr/bin/env python3
"""Seasonal analysis of multi-month ERA5 + HEAT integration.

Reads daily NetCDF files and daily_diagnostics.csv using a run manifest
to produce validated seasonal outputs inside the run directory:
- data/runs/<run_id>/output/csv/seasonal_daily_summary.csv
- data/runs/<run_id>/output/csv/seasonal_monthly_summary.csv
- data/runs/<run_id>/output/txt/seasonal_report.txt
"""

import argparse
import json
import pathlib
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import xarray as xr

from units import temperature_k_to_c, velocity_mps_to_cmps, density_anomaly_kgm3_to_gcm3
from run_context import resolve_run, add_run_args


def load_manifest(manifest_path: pathlib.Path) -> dict:
    """Load and validate run manifest."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())

    # Validate manifest
    expected_days = manifest.get("expected_days", 0)
    files = manifest.get("files", [])
    if len(files) != expected_days:
        raise ValueError(
            f"Manifest has {len(files)} files but expected {expected_days} days"
        )

    # Check for duplicates
    days = [f["day"] for f in manifest["files"]]
    if len(days) != len(set(days)):
        raise ValueError("Manifest contains duplicate day entries")

    # Verify dates
    start_date = datetime.fromisoformat(manifest["start_date"])
    for f in manifest["files"]:
        # Model integration day d = start_date + d days
        expected_date = (start_date + timedelta(days=f["day"])).date().isoformat()
        if f["date"] != expected_date:
            raise ValueError(
                f"Date mismatch for day {f['day']}: expected {expected_date} (model day {f['day']} = start_date + {f['day']} days), got {f['date']}"
            )
        if not pathlib.Path(f["file"]).exists():
            raise FileNotFoundError(f"Missing file for day {f['day']}: {f['file']}")

    return manifest


def analyze_seasonal(
    manifest: dict,
    manifest_path: pathlib.Path,
    diag_csv: pathlib.Path,
    output_daily_csv: pathlib.Path,
    output_monthly_csv: pathlib.Path,
    output_txt: pathlib.Path,
) -> int:
    """Analyze seasonal diagnostics from model output using validated manifest."""

    nc_dir = pathlib.Path(manifest["base_dir"])
    diag_csv_path = pathlib.Path(diag_csv)
    output_daily_csv = pathlib.Path(output_daily_csv)
    output_monthly_csv = pathlib.Path(output_monthly_csv)
    output_txt = pathlib.Path(output_txt)

    if not diag_csv_path.exists():
        print(f"ERROR: Diagnostics CSV {diag_csv} not found")
        return 1

    # Read daily diagnostics and deduplicate
    diag = pd.read_csv(diag_csv)
    print(f"Read {len(diag)} rows from {diag_csv}")

    # Deduplicate daily diagnostics: keep last entry per day
    if "day" in diag.columns:
        diag = diag.sort_values("day").drop_duplicates(subset=["day"], keep="last")
        print(f"After deduplication: {len(diag)} unique days")

    # Compute month from day if not present or all same
    if "month" not in diag.columns or diag["month"].nunique() == 1:
        start_date = datetime.fromisoformat(manifest["start_date"])
        diag["month"] = diag["day"].apply(
            lambda d: (start_date + timedelta(days=d - 1)).month
        )
        diag["month_name"] = diag["month"].apply(
            lambda m: {1: "January", 2: "February", 3: "March"}.get(m, str(m))
        )

    # Use manifest file list
    manifest_files = manifest["files"]
    expected_days = len(manifest["files"])

    # Extract seasonal data from NetCDF files
    seasonal_data = []

    for f_info in manifest["files"]:
        nc_file = pathlib.Path(f_info["file"])
        day = f_info["day"]

        try:
            ds = xr.open_dataset(nc_file)

            # Determine month from day using actual calendar
            current_date = start_date + timedelta(days=day - 1)
            month = current_date.month
            month_name = current_date.strftime("%B")

            # Temperature statistics (3D) - NetCDF in K, convert to degC
            temp = temperature_k_to_c(ds["temperature"].values)
            temp_mean = float(np.nanmean(temp))
            temp_min = float(np.nanmin(temp))
            temp_max = float(np.nanmax(temp))

            # Surface temperature (depth=0)
            temp_surf = temperature_k_to_c(ds["temperature"].isel(depth=0).values)
            temp_surf_mean = float(np.nanmean(temp_surf))
            temp_surf_min = float(np.nanmin(temp_surf))
            temp_surf_max = float(np.nanmax(temp_surf))

            # 20m, 100m, 500m depths
            z_coords = ds.coords.get("depth", None)
            if z_coords is not None:
                depth_vals = z_coords.values
                idx_20m = int(np.argmin(np.abs(depth_vals - 20.0)))
                idx_100m = int(np.argmin(np.abs(depth_vals - 100.0)))
                idx_500m = int(np.argmin(np.abs(depth_vals - 500.0)))
            else:
                idx_20m, idx_100m, idx_500m = 3, 8, 15

            temp_20m = (
                temperature_k_to_c(ds["temperature"].isel(depth=idx_20m).values)
                if idx_20m < temp.shape[0]
                else np.array([np.nan])
            )
            temp_100m = (
                temperature_k_to_c(ds["temperature"].isel(depth=idx_100m).values)
                if idx_100m < temp.shape[0]
                else np.array([np.nan])
            )
            temp_500m = (
                temperature_k_to_c(ds["temperature"].isel(depth=idx_500m).values)
                if idx_500m < temp.shape[0]
                else np.array([np.nan])
            )

            # Salinity (mass fraction, already canonical 1 = kg/kg)
            salt = ds["salinity_mass_fraction"].values
            salt_mean = float(np.nanmean(salt))
            salt_min = float(np.nanmin(salt))
            salt_max = float(np.nanmax(salt))

            # Density anomaly (kg m-3 canonical; present as g cm-3)
            dens = density_anomaly_kgm3_to_gcm3(ds["density_anomaly"].values)
            dens_mean = float(np.nanmean(dens))
            dens_min = float(np.nanmin(dens))
            dens_max = float(np.nanmax(dens))

            # Velocities (canonical m s-1; present as cm s-1)
            u = velocity_mps_to_cmps(ds["u_velocity"].values)
            v = velocity_mps_to_cmps(ds["v_velocity"].values)
            w = velocity_mps_to_cmps(ds["w_velocity"].values)
            u_max = float(np.nanmax(np.abs(u)))
            v_max = float(np.nanmax(np.abs(v)))
            w_max = float(np.nanmax(np.abs(w)))

            u_surf = velocity_mps_to_cmps(ds["u_velocity"].isel(depth=0).values)
            v_surf = velocity_mps_to_cmps(ds["v_velocity"].isel(depth=0).values)
            u_surf_max = float(np.nanmax(np.abs(u_surf)))
            v_surf_max = float(np.nanmax(np.abs(v_surf)))

            # Atmosphere (air_temp canonical K, present as degC)
            air_temp = temperature_k_to_c(ds["air_temp"].values)
            air_temp_mean = float(np.nanmean(air_temp))
            air_temp_min = float(np.nanmin(air_temp))
            air_temp_max = float(np.nanmax(air_temp))

            # Snowfall rate
            if "era5_snowfall_rate" in ds.data_vars:
                sf = ds["era5_snowfall_rate"].values
                sf_mean = float(np.nanmean(sf))
                sf_max = float(np.nanmax(sf))
            else:
                sf_mean = sf_max = np.nan

            # Humidity
            if "humidity" in ds.data_vars:
                hum = ds["humidity"].values
                hum_mean = float(np.nanmean(hum))
            else:
                hum_mean = np.nan

            # Cloud
            if "cloud" in ds.data_vars:
                cld = ds["cloud"].values
                cld_mean = float(np.nanmean(cld))
            else:
                cld_mean = np.nan

            # Wind
            wind = ds["wind_speed"].values
            wind_mean = float(np.nanmean(wind))
            wind_max = float(np.nanmax(wind))

            # Stress
            tau_x = ds["tau_x"].values
            tau_y = ds["tau_y"].values
            tau_max = float(np.nanmax(np.sqrt(tau_x**2 + tau_y**2)))

            # Pressure gradient
            dp_x = ds["dp_x"].values
            dp_y = ds["dp_y"].values
            dp_max = float(np.nanmax(np.sqrt(dp_x**2 + dp_y**2)))

            # ERA5 snowfall rate
            if "era5_snowfall_rate" in ds.data_vars:
                sf = ds["era5_snowfall_rate"].values
                sf_mean = float(np.nanmean(sf))
                sf_max = float(np.nanmax(sf))
            else:
                sf_mean = sf_max = np.nan

            # EUU from diagnostics (match by day)
            euu = np.nan
            ca_nmix = ca_guard = ca_maxiter = np.nan
            if "day" in diag.columns:
                day_diag = diag[diag["day"] == day]
                if len(day_diag) > 0:
                    row = day_diag.iloc[0]
                    if "euu" in row:
                        euu = float(row["euu"])
                    if "ca_nmix" in day_diag.columns:
                        ca_nmix = float(day_diag["ca_nmix"].values[0])
                        ca_guard = float(day_diag["ca_guard_hits"].values[0])
                        ca_maxiter = float(day_diag["ca_max_iter"].values[0])

            seasonal_data.append(
                {
                    "day": day,
                    "month": month,
                    "month_name": ["January", "February", "March"][
                        min(2, (day - 1) // 31)
                    ],
                    "temp_mean": temp_mean,
                    "temp_min": temp_min,
                    "temp_max": temp_max,
                    "temp_surf_mean": temp_surf_mean,
                    "temp_surf_min": temp_surf_min,
                    "temp_surf_max": temp_surf_max,
                    "temp_20m_mean": (
                        float(np.nanmean(temp_20m)) if len(temp_20m) > 0 else np.nan
                    ),
                    "temp_100m_mean": (
                        float(np.nanmean(temp_100m)) if len(temp_100m) > 0 else np.nan
                    ),
                    "temp_500m_mean": (
                        float(np.nanmean(temp_500m)) if len(temp_500m) > 0 else np.nan
                    ),
                    "salt_mean": salt_mean,
                    "salt_min": salt_min,
                    "salt_max": salt_max,
                    "dens_mean": dens_mean,
                    "dens_min": dens_min,
                    "dens_max": dens_max,
                    "u_max": u_max,
                    "v_max": v_max,
                    "w_max": w_max,
                    "u_surf_max": u_surf_max,
                    "v_surf_max": v_surf_max,
                    "air_temp_mean": air_temp_mean,
                    "air_temp_min": air_temp_min,
                    "air_temp_max": air_temp_max,
                    "humidity_mean": hum_mean,
                    "cloud_mean": cld_mean,
                    "wind_mean": wind_mean,
                    "wind_max": wind_max,
                    "tau_max": tau_max,
                    "sf_rate_mean": sf_mean,
                    "sf_rate_max": sf_max,
                    "euu": euu,
                    "ca_nmix": ca_nmix,
                    "ca_guard": ca_guard,
                    "ca_maxiter": ca_maxiter,
                }
            )

            ds.close()
        except Exception as e:
            print(f"Warning: Failed to read {nc_file}: {e}")
            continue

    if not seasonal_data:
        print("No seasonal data extracted")
        return 1

    seasonal_df = pd.DataFrame(seasonal_data)
    seasonal_df = seasonal_df.sort_values("day").reset_index(drop=True)

    # VALIDATION: Check for exactly expected_days unique days
    if len(seasonal_df) != expected_days:
        print(f"ERROR: Expected {expected_days} daily records, got {len(seasonal_df)}")
        return 1

    if seasonal_df["day"].nunique() != expected_days:
        print(
            f"ERROR: Duplicate days detected. Unique days: {seasonal_df['day'].nunique()}, expected: {expected_days}"
        )
        return 1

    # Check for missing days
    expected_days_set = set(range(1, expected_days + 1))
    actual_days_set = set(seasonal_df["day"].values)
    missing = set(range(1, expected_days + 1)) - set(seasonal_df["day"].values)
    if missing:
        print(f"ERROR: Missing days: {sorted(missing)}")
        return 1

    # Merge with daily diagnostics if available
    if "day" in diag.columns:
        diag_renamed = diag.copy()
        diag_renamed.columns = [
            f"diag_{c}" if c != "day" else "day" for c in diag_renamed.columns
        ]
        seasonal_df = seasonal_df.merge(diag_renamed, on="day", how="left")

    # Save daily summary CSV
    seasonal_df.to_csv(output_daily_csv, index=False)
    print(f"Saved daily summary to {output_daily_csv}")

    # Create monthly summary
    monthly_summary = (
        seasonal_df.groupby("month_name")
        .agg(
            {
                "temp_mean": ["mean", "min", "max"],
                "temp_surf_mean": ["mean", "min", "max"],
                "salt_mean": ["mean", "min", "max"],
                "dens_mean": ["mean", "min", "max"],
                "u_max": ["mean", "max"],
                "v_max": ["mean", "max"],
                "w_max": ["mean", "max"],
                "air_temp_mean": ["mean", "min", "max"],
                "sf_rate_mean": ["mean", "max"],
                "euu": ["mean", "max"],
            }
        )
        .round(4)
    )

    monthly_summary.to_csv(output_monthly_csv)
    print(f"Saved monthly summary to {output_monthly_csv}")

    # Generate text report
    with open(output_txt, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("SEASONAL ANALYSIS: JANUARY-MARCH 2020 ERA5 + HEAT INTEGRATION\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Analyzed {len(seasonal_df)} daily NetCDF files\n")
        f.write(f"Source directory: {pathlib.Path(manifest['base_dir'])}\n")
        f.write(f"Manifest: {manifest_path}\n\n")

        f.write("-" * 80 + "\n")
        f.write("SEASONAL SUMMARY STATISTICS\n")
        f.write("-" * 80 + "\n")

        f.write(f"\nOcean Temperature (3D):\n")
        f.write(
            f"  Mean: {seasonal_df['temp_mean'].mean():.3f} °C (min {seasonal_df['temp_min'].min():.3f}, max {seasonal_df['temp_max'].max():.3f})\n"
        )
        f.write(
            f"  Surface Mean: {seasonal_df['temp_surf_mean'].mean():.3f} °C (min {seasonal_df['temp_surf_min'].min():.3f}, max {seasonal_df['temp_surf_max'].max():.3f})\n"
        )

        f.write(f"\nVertical Temperature Structure:\n")
        f.write(f"  20m Mean: {seasonal_df['temp_20m_mean'].mean():.3f} °C\n")
        f.write(f"  100m Mean: {seasonal_df['temp_100m_mean'].mean():.3f} °C\n")
        f.write(f"  500m Mean: {seasonal_df['temp_500m_mean'].mean():.3f} °C\n")

        f.write(f"\nSalinity (mass fraction):\n")
        f.write(
            f"  Mean: {seasonal_df['salt_mean'].mean():.5f} (min {seasonal_df['salt_min'].min():.5f}, max {seasonal_df['salt_max'].max():.5f})\n"
        )

        f.write(f"\nDensity Anomaly (g/cm³; canonical NetCDF unit kg/m³):\n")
        f.write(
            f"  Mean: {seasonal_df['dens_mean'].mean():.5f} (min {seasonal_df['dens_min'].min():.5f}, max {seasonal_df['dens_max'].max():.5f})\n"
        )

        f.write(f"\nVelocities (cm/s):\n")
        f.write(
            f"  U max: {seasonal_df['u_max'].max():.2f}, V max: {seasonal_df['v_max'].max():.2f}, W max: {seasonal_df['w_max'].max():.4f}\n"
        )

        f.write(f"\nAir Temperature (forcing):\n")
        f.write(
            f"  Mean: {seasonal_df['air_temp_mean'].mean():.2f} °C (min {seasonal_df['air_temp_min'].min():.2f}, max {seasonal_df['air_temp_max'].max():.2f})\n"
        )

        f.write(f"\nERA5 Snowfall Rate:\n")
        f.write(f"  Mean: {seasonal_df['sf_rate_mean'].mean():.3e} m/s\n")
        f.write(f"  Max:  {seasonal_df['sf_rate_max'].max():.3e} m/s\n")

        f.write(f"\nKinetic Energy (EUU):\n")
        f.write(f"  Mean: {seasonal_df['euu'].mean():.3e} cm²/s²\n")
        f.write(f"  Max:  {seasonal_df['euu'].max():.3e} cm²/s²\n")

        diag_cols = [c for c in seasonal_df.columns if c.startswith("diag_")]
        if diag_cols:
            f.write(f"\n\nDAILY DIAGNOSTICS SUMMARY\n")
            f.write("-" * 80 + "\n")
            for col in diag_cols:
                if seasonal_df[col].notna().any() and pd.api.types.is_numeric_dtype(
                    seasonal_df[col]
                ):
                    f.write(
                        f"  {col}: mean={seasonal_df[col].mean():.3e}, min={seasonal_df[col].min():.3e}, max={seasonal_df[col].max():.3e}\n"
                    )

        f.write("\n" + "=" * 80 + "\n")
        f.write("MONTHLY BREAKDOWN\n")
        f.write("=" * 80 + "\n")

        for month_num, month_name in [(1, "January"), (2, "February"), (3, "March")]:
            month_data = seasonal_df[seasonal_df["month"] == month_num]
            if len(month_data) == 0:
                continue

            f.write(
                f"\n--- {month_name} (Days {month_data['day'].min()}-{month_data['day'].max()}) ---\n"
            )
            f.write(f"  Days: {len(month_data)}\n")
            f.write(
                f"  T mean: {month_data['temp_mean'].mean():.3f} °C (surface: {month_data['temp_surf_mean'].mean():.3f} °C)\n"
            )
            f.write(
                f"  T range: {month_data['temp_min'].min():.3f} to {month_data['temp_max'].max():.3f} °C\n"
            )
            f.write(f"  S mean: {month_data['salt_mean'].mean():.5f}\n")
            f.write(f"  RO mean: {month_data['dens_mean'].mean():.5f} g/cm³\n")
            f.write(f"  Air T: {month_data['air_temp_mean'].mean():.2f} °C\n")
            f.write(
                f"  Snowfall: {month_data['sf_rate_mean'].mean():.3e} m/s (max {month_data['sf_rate_max'].max():.3e})\n"
            )
            f.write(f"  EUU: {month_data['euu'].mean():.3e} cm²/s²\n")
            if "diag_ca_nmix" in month_data.columns:
                f.write(
                    f"  nmix: {month_data['diag_ca_nmix'].mean():.0f}, guard: {month_data['diag_ca_guard_hits'].mean():.0f}, maxiter: {month_data['diag_ca_max_iter'].mean():.1f}\n"
                )

        f.write("\n" + "=" * 80 + "\n")
        f.write("DATA INTEGRITY CHECK\n")
        f.write("=" * 80 + "\n")
        f.write(f"Expected days: {expected_days}\n")
        f.write(f"Actual records: {len(seasonal_df)}\n")
        f.write(f"Unique days: {seasonal_df['day'].nunique()}\n")
        f.write(
            f"Missing days: {set(range(1, expected_days + 1)) - set(seasonal_df['day'].values)}\n"
        )
        f.write(f"Duplicate rows: {len(seasonal_df) - seasonal_df['day'].nunique()}\n")
        f.write("DATA INTEGRITY: PASS\n")

    print(f"Saved report to {output_txt}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Analyze seasonal ERA5 + HEAT integration diagnostics"
    )
    add_run_args(parser, default_run_id="2020_Q1_test_heat_on")
    parser.add_argument(
        "--diag-csv", default=None, help="Daily diagnostics CSV (default: run csv dir)"
    )
    parser.add_argument(
        "--output-daily-csv",
        default=None,
        help="Output daily CSV (default: run csv dir)",
    )
    parser.add_argument(
        "--output-monthly-csv",
        default=None,
        help="Output monthly CSV (default: run csv dir)",
    )
    parser.add_argument(
        "--output-txt", default=None, help="Output report TXT (default: run txt dir)"
    )
    args = parser.parse_args()

    try:
        ctx = resolve_run(run_id=args.run_id, manifest=args.manifest)
        manifest = load_manifest(ctx.manifest)
    except Exception as e:
        print(f"ERROR: Failed to resolve/load run: {e}")
        return 1

    diag_csv = pathlib.Path(args.diag_csv) if args.diag_csv else ctx.daily_diagnostics
    out_daily = (
        pathlib.Path(args.output_daily_csv)
        if args.output_daily_csv
        else ctx.csv_dir / "seasonal_daily_summary.csv"
    )
    out_monthly = (
        pathlib.Path(args.output_monthly_csv)
        if args.output_monthly_csv
        else ctx.csv_dir / "seasonal_monthly_summary.csv"
    )
    out_txt = (
        pathlib.Path(args.output_txt)
        if args.output_txt
        else ctx.txt_dir / "seasonal_report.txt"
    )

    return analyze_seasonal(
        manifest, ctx.manifest, diag_csv, out_daily, out_monthly, out_txt
    )


if __name__ == "__main__":
    sys.exit(main())
