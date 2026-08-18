"""Analyze HEAT thermodynamics diagnostics from model output.

Reads daily NetCDF files and daily_diagnostics.csv to produce:
- data/output/daily_heat_summary.csv
- data/output/heat_report.txt

Compares HEAT ON vs HEAT OFF runs when both are available.
"""

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd
import xarray as xr

from units import temperature_k_to_c, density_anomaly_kgm3_to_gcm3
from run_context import resolve_run, add_run_args


def analyze_heat_diagnostics(nc_dir, diag_csv, output_csv, output_txt):
    """Analyze HEAT diagnostics from model output."""

    nc_dir = pathlib.Path(nc_dir)
    diag_csv = pathlib.Path(diag_csv)
    output_csv = pathlib.Path(output_csv)
    output_txt = pathlib.Path(output_txt)

    if not nc_dir.exists():
        print(f"ERROR: NetCDF directory {nc_dir} not found")
        return 1
    if not diag_csv.exists():
        print(f"ERROR: Diagnostics CSV {diag_csv} not found")
        return 1

    # Read daily diagnostics
    diag = pd.read_csv(diag_csv)
    print(f"Read {len(diag)} rows from {diag_csv}")

    # Find daily NetCDF files
    nc_files = sorted(nc_dir.glob("results_day_*.nc"))
    if not nc_files:
        print(f"No results_day_*.nc files found in {nc_dir}")
        return 1

    # Extract heat-relevant variables from NetCDF
    heat_data = []
    for nc_file in nc_files:
        if "final" in nc_file.name:
            continue
        try:
            ds = xr.open_dataset(nc_file)

            # Extract day number from filename
            day_str = nc_file.stem.split("_")[-1]
            day = int(day_str) if day_str.isdigit() else 0

            # Temperature statistics (canonical K, present as degC)
            temp = temperature_k_to_c(ds["temperature"].values)
            temp_mean = np.nanmean(temp)
            temp_min = np.nanmin(temp)
            temp_max = np.nanmax(temp)

            # Salinity statistics (mass fraction)
            salt = ds["salinity_mass_fraction"].values
            salt_mean = np.nanmean(salt)
            salt_min = np.nanmin(salt)
            salt_max = np.nanmax(salt)

            # Density anomaly statistics (canonical kg m-3, present as g cm-3)
            dens = density_anomaly_kgm3_to_gcm3(ds["density_anomaly"].values)
            dens_mean = np.nanmean(dens)
            dens_min = np.nanmin(dens)
            dens_max = np.nanmax(dens)

            # Velocity statistics
            u = ds["u_velocity"].values
            v = ds["v_velocity"].values
            w = ds["w_velocity"].values
            u_max = np.nanmax(np.abs(u))
            v_max = np.nanmax(np.abs(v))
            w_max = np.nanmax(np.abs(w))

            # Surface layer (k=0) temperature
            temp_surf = temperature_k_to_c(ds["temperature"].isel(depth=0).values)
            temp_surf_mean = np.nanmean(temp_surf)
            temp_surf_min = np.nanmin(temp_surf)
            temp_surf_max = np.nanmax(temp_surf)

            # Air temperature (forcing; canonical K, present as degC)
            air_temp = temperature_k_to_c(ds["air_temp"].values)
            air_temp_mean = np.nanmean(air_temp)
            air_temp_min = np.nanmin(air_temp)
            air_temp_max = np.nanmax(air_temp)

            # Humidity
            humidity = ds["humidity"].values if "humidity" in ds.data_vars else None
            hum_mean = np.nanmean(humidity) if humidity is not None else np.nan
            hum_min = np.nanmin(humidity) if humidity is not None else np.nan
            hum_max = np.nanmax(humidity) if humidity is not None else np.nan

            # Cloud
            cloud = ds["cloud"].values if "cloud" in ds.data_vars else None
            cld_mean = np.nanmean(cloud) if cloud is not None else np.nan
            cld_min = np.nanmin(cloud) if cloud is not None else np.nan
            cld_max = np.nanmax(cloud) if cloud is not None else np.nan

            # Wind
            wind = ds["wind_speed"].values
            wind_mean = np.nanmean(wind)
            wind_max = np.nanmax(wind)

            # Stress
            tau_x = ds["tau_x"].values
            tau_y = ds["tau_y"].values
            tau_max = np.nanmax(np.sqrt(tau_x**2 + tau_y**2))

            # Pressure gradient
            dp_x = ds["dp_x"].values
            dp_y = ds["dp_y"].values
            dp_max = np.nanmax(np.sqrt(dp_x**2 + dp_y**2))

            heat_data.append(
                {
                    "day": day,
                    "temp_mean": temp_mean,
                    "temp_min": temp_min,
                    "temp_max": temp_max,
                    "temp_surf_mean": temp_surf_mean,
                    "temp_surf_min": temp_surf_min,
                    "temp_surf_max": temp_surf_max,
                    "salt_mean": salt_mean,
                    "salt_min": salt_min,
                    "salt_max": salt_max,
                    "dens_mean": dens_mean,
                    "dens_min": dens_min,
                    "dens_max": dens_max,
                    "u_max": u_max,
                    "v_max": v_max,
                    "w_max": w_max,
                    "air_temp_mean": air_temp_mean,
                    "air_temp_min": air_temp_min,
                    "air_temp_max": air_temp_max,
                    "humidity_mean": hum_mean,
                    "humidity_min": hum_min,
                    "humidity_max": hum_max,
                    "cloud_mean": cld_mean,
                    "cloud_min": cld_min,
                    "cloud_max": cld_max,
                    "wind_mean": wind_mean,
                    "wind_max": wind_max,
                    "tau_max": tau_max,
                    "dp_max": dp_max,
                }
            )

            ds.close()
        except Exception as e:
            print(f"Warning: Failed to read {nc_file}: {e}")
            continue

    if not heat_data:
        print("No heat data extracted")
        return 1

    heat_df = pd.DataFrame(heat_data)
    heat_df = heat_df.sort_values("day").reset_index(drop=True)

    # Merge with daily diagnostics if available
    if "day" in diag.columns:
        # Rename diag columns to avoid conflicts
        diag_renamed = diag.copy()
        diag_renamed.columns = [
            f"diag_{c}" if c != "day" else "day" for c in diag_renamed.columns
        ]
        heat_df = heat_df.merge(diag_renamed, on="day", how="left")

    # Save CSV
    heat_df.to_csv(output_csv, index=False)
    print(f"Saved heat summary to {output_csv}")

    # Generate text report
    with open(output_txt, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("HEAT THERMODYNAMICS DIAGNOSTIC REPORT\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Analyzed {len(heat_df)} daily NetCDF files\n")
        f.write(f"Source directory: {nc_dir}\n")
        f.write(f"Diagnostics CSV: {diag_csv}\n\n")

        f.write("-" * 70 + "\n")
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 70 + "\n")

        # Temperature
        f.write(f"\nOcean Temperature (3D):\n")
        f.write(
            f"  Mean: {heat_df['temp_mean'].mean():.3f} °C (min {heat_df['temp_min'].min():.3f}, max {heat_df['temp_max'].max():.3f})\n"
        )
        f.write(
            f"  Surface Mean: {heat_df['temp_surf_mean'].mean():.3f} °C (min {heat_df['temp_surf_min'].min():.3f}, max {heat_df['temp_surf_max'].max():.3f})\n"
        )

        # Salinity
        f.write(f"\nSalinity (mass fraction):\n")
        f.write(
            f"  Mean: {heat_df['salt_mean'].mean():.5f} (min {heat_df['salt_min'].min():.5f}, max {heat_df['salt_max'].max():.5f})\n"
        )

        # Density
        f.write(f"\nDensity Anomaly (g/cm³):\n")
        f.write(
            f"  Mean: {heat_df['dens_mean'].mean():.5f} (min {heat_df['dens_min'].min():.5f}, max {heat_df['dens_max'].max():.5f})\n"
        )

        # Velocities
        f.write(f"\nVelocities (cm/s):\n")
        f.write(
            f"  U max: {heat_df['u_max'].max():.2f}, V max: {heat_df['v_max'].max():.2f}, W max: {heat_df['w_max'].max():.4f}\n"
        )

        # Air temperature
        f.write(f"\nAir Temperature (forcing):\n")
        f.write(
            f"  Mean: {heat_df['air_temp_mean'].mean():.2f} °C (min {heat_df['air_temp_min'].min():.2f}, max {heat_df['air_temp_max'].max():.2f})\n"
        )

        # Humidity
        if not heat_df["humidity_mean"].isna().all():
            f.write(f"\nHumidity (relative, 0-1):\n")
            f.write(
                f"  Mean: {heat_df['humidity_mean'].mean():.3f} (min {heat_df['humidity_min'].min():.3f}, max {heat_df['humidity_max'].max():.3f})\n"
            )

        # Cloud
        if not heat_df["cloud_mean"].isna().all():
            f.write(f"\nCloud Cover (0-1):\n")
            f.write(
                f"  Mean: {heat_df['cloud_mean'].mean():.3f} (min {heat_df['cloud_min'].min():.3f}, max {heat_df['cloud_max'].max():.3f})\n"
            )

        # Wind
        f.write(f"\nWind (m/s):\n")
        f.write(
            f"  Mean: {heat_df['wind_mean'].mean():.2f}, Max: {heat_df['wind_max'].max():.2f}\n"
        )

        # Stress
        f.write(f"\nSurface Stress (dyn/cm²):\n")
        f.write(f"  Max magnitude: {heat_df['tau_max'].max():.3f}\n")

        # Pressure gradient
        f.write(f"\nPressure Gradient (hPa/km):\n")
        f.write(f"  Max magnitude: {heat_df['dp_max'].max():.6f}\n")

        # Daily diagnostics if available
        diag_cols = [c for c in heat_df.columns if c.startswith("diag_")]
        if diag_cols:
            f.write(f"\n\nDAILY DIAGNOSTICS (from daily_diagnostics.csv)\n")
            f.write("-" * 70 + "\n")
            for col in diag_cols:
                if heat_df[col].notna().any():
                    f.write(
                        f"  {col}: mean={heat_df[col].mean():.3e}, min={heat_df[col].min():.3e}, max={heat_df[col].max():.3e}\n"
                    )

        f.write("\n" + "=" * 70 + "\n")
        f.write("PER-DAY DETAILS\n")
        f.write("=" * 70 + "\n")

        for _, row in heat_df.iterrows():
            f.write(f"\nDay {int(row['day']):2d}:\n")
            f.write(
                f"  T: {row['temp_mean']:.3f} °C (surf: {row['temp_surf_mean']:.3f})\n"
            )
            f.write(f"  S: {row['salt_mean']:.5f}, RO: {row['dens_mean']:.5f} g/cm³\n")
            f.write(
                f"  U/V/W max: {row['u_max']:.1f}/{row['v_max']:.1f}/{row['w_max']:.3f} cm/s\n"
            )
            f.write(
                f"  Air T: {row['air_temp_mean']:.2f} °C, Hum: {row['humidity_mean']:.3f}, Cloud: {row['cloud_mean']:.3f}\n"
            )
            f.write(
                f"  Wind: {row['wind_mean']:.2f} m/s, Tau: {row['tau_max']:.3f} dyn/cm²\n"
            )
            if "diag_nmix" in row and not pd.isna(row["diag_nmix"]):
                f.write(
                    f"  nmix: {int(row['diag_nmix'])}, guard: {int(row['diag_guard'])}, maxiter: {int(row['diag_maxiter'])}\n"
                )

    print(f"Saved report to {output_txt}")
    return 0


def compare_heat_on_off(on_dir, off_dir, output_csv, output_txt):
    """Compare HEAT ON vs HEAT OFF runs."""
    on_dir = pathlib.Path(on_dir)
    off_dir = pathlib.Path(off_dir)

    # This would require both runs to have same day outputs
    # For now, just note the comparison capability
    print("HEAT ON/OFF comparison not yet implemented - need matching day outputs")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze HEAT thermodynamics diagnostics"
    )
    add_run_args(parser, default_run_id="2020_Q1_test_heat_on")
    parser.add_argument(
        "--nc-dir",
        default=None,
        help="Directory with results_day_*.nc files (default: run nc dir)",
    )
    parser.add_argument(
        "--diag-csv",
        default=None,
        help="Daily diagnostics CSV (default: run csv dir)",
    )
    parser.add_argument(
        "--output-csv", default=None, help="Output CSV (default: run csv dir)"
    )
    parser.add_argument(
        "--output-txt", default=None, help="Output report TXT (default: run txt dir)"
    )
    parser.add_argument(
        "--compare-on-off",
        action="store_true",
        help="Compare HEAT ON vs OFF (not yet implemented)",
    )

    args = parser.parse_args()

    try:
        ctx = resolve_run(run_id=args.run_id, manifest=args.manifest)
    except Exception as e:
        print(f"ERROR: Failed to resolve run: {e}")
        return 1

    nc_dir = str(args.nc_dir) if args.nc_dir else str(ctx.nc_dir)
    diag_csv = str(args.diag_csv) if args.diag_csv else str(ctx.daily_diagnostics)
    out_csv = (
        str(args.output_csv)
        if args.output_csv
        else str(ctx.csv_dir / "daily_heat_summary.csv")
    )
    out_txt = (
        str(args.output_txt)
        if args.output_txt
        else str(ctx.txt_dir / "heat_report.txt")
    )

    if args.compare_on_off:
        compare_heat_on_off(nc_dir, nc_dir, out_csv, out_txt)
    else:
        return analyze_heat_diagnostics(nc_dir, diag_csv, out_csv, out_txt)


if __name__ == "__main__":
    sys.exit(main())
