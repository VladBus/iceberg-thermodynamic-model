#!/usr/bin/env python3
"""Seasonal analysis of multi-month ERA5 + HEAT integration.

Reads daily NetCDF files and daily_diagnostics.csv to produce:
- data/output/seasonal_daily_summary.csv
- data/output/seasonal_monthly_summary.csv
- data/output/seasonal_report.txt

Analyzes 3-month (Jan-Mar 2020) HEAT integration on TEST grid.
"""

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd
import xarray as xr


def analyze_seasonal(nc_dir, diag_csv, output_daily_csv, output_monthly_csv, output_txt):
    """Analyze seasonal diagnostics from model output."""

    nc_dir = pathlib.Path(nc_dir)
    diag_csv = pathlib.Path(diag_csv)
    output_daily_csv = pathlib.Path(output_daily_csv)
    output_monthly_csv = pathlib.Path(output_monthly_csv)
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

    # Extract seasonal data from NetCDF
    seasonal_data = []
    for nc_file in nc_files:
        if "final" in nc_file.name:
            continue
        try:
            ds = xr.open_dataset(nc_file)

            # Extract day number from filename
            day_str = nc_file.stem.split("_")[-1]
            day = int(day_str) if day_str.isdigit() else 0

            # Determine month
            if day <= 31:
                month = 1
                month_name = "January"
            elif day <= 60:
                month = 2
                month_name = "February"
            else:
                month = 3
                month_name = "March"

            # Temperature statistics (3D)
            temp = ds['temperature'].values
            temp_mean = float(np.nanmean(temp))
            temp_min = float(np.nanmin(temp))
            temp_max = float(np.nanmax(temp))

            # Surface temperature (k=0)
            temp_surf = ds['temperature'].isel(depth=0).values
            temp_surf_mean = float(np.nanmean(temp_surf))
            temp_surf_min = float(np.nanmin(temp_surf))
            temp_surf_max = float(np.nanmax(temp_surf))

            # 20m depth (~index 3-4 depending on grid)
            # Find depth closest to 20m (2000 cm)
            z_coords = ds.coords.get('depth', None)
            if z_coords is not None:
                depth_vals = z_coords.values
                idx_20m = np.argmin(np.abs(depth_vals - 20.0))
                idx_100m = np.argmin(np.abs(depth_vals - 100.0))
                idx_500m = np.argmin(np.abs(depth_vals - 500.0))
            else:
                idx_20m, idx_100m, idx_500m = 3, 8, 15

            temp_20m = ds['temperature'].isel(depth=idx_20m).values if idx_20m < temp.shape[0] else np.array([np.nan])
            temp_100m = ds['temperature'].isel(depth=idx_100m).values if idx_100m < temp.shape[0] else np.array([np.nan])
            temp_500m = ds['temperature'].isel(depth=idx_500m).values if idx_500m < temp.shape[0] else np.array([np.nan])

            # Salinity statistics
            salt = ds['salinity'].values
            salt_mean = float(np.nanmean(salt))
            salt_min = float(np.nanmin(salt))
            salt_max = float(np.nanmax(salt))

            # Density statistics
            dens = ds['density'].values
            dens_mean = float(np.nanmean(dens))
            dens_min = float(np.nanmin(dens))
            dens_max = float(np.nanmax(dens))

            # Velocity statistics
            u = ds['u_velocity'].values
            v = ds['v_velocity'].values
            w = ds['w_velocity'].values
            u_max = float(np.nanmax(np.abs(u)))
            v_max = float(np.nanmax(np.abs(v)))
            w_max = float(np.nanmax(np.abs(w)))

            # Surface values
            u_surf = ds['u_velocity'].isel(depth=0).values
            v_surf = ds['v_velocity'].isel(depth=0).values
            u_surf_max = float(np.nanmax(np.abs(u_surf)))
            v_surf_max = float(np.nanmax(np.abs(v_surf)))

            # Air temperature (forcing)
            air_temp = ds['air_temp'].values
            air_temp_mean = float(np.nanmean(air_temp))
            air_temp_min = float(np.nanmin(air_temp))
            air_temp_max = float(np.nanmax(air_temp))

            # ERA5 snowfall rate
            if 'era5_snowfall_rate' in ds.data_vars:
                sf = ds['era5_snowfall_rate'].values
                sf_mean = float(np.nanmean(sf))
                sf_max = float(np.nanmax(sf))
            else:
                sf_mean = sf_max = np.nan

            # Humidity
            if 'humidity' in ds.data_vars:
                hum = ds['humidity'].values
                hum_mean = float(np.nanmean(hum))
            else:
                hum_mean = np.nan

            # Cloud
            if 'cloud' in ds.data_vars:
                cld = ds['cloud'].values
                cld_mean = float(np.nanmean(cld))
            else:
                cld_mean = np.nan

            # Wind
            wind = ds['wind_speed'].values
            wind_mean = float(np.nanmean(wind))
            wind_max = float(np.nanmax(wind))

            # Stress
            tau_x = ds['tau_x'].values
            tau_y = ds['tau_y'].values
            tau_max = float(np.nanmax(np.sqrt(tau_x**2 + tau_y**2)))

            # Pressure gradient
            dp_x = ds['dp_x'].values
            dp_y = ds['dp_y'].values
            dp_max = float(np.nanmax(np.sqrt(dp_x**2 + dp_y**2)))

            # Kinetic energy from diagnostics
            euu = np.nan
            if 'diag_euu' in diag.columns:
                day_diag = diag[diag['day'] == day]
                if len(day_diag) > 0:
                    euu = float(day_diag['diag_euu'].values[0]) if 'diag_euu' in day_diag.columns else np.nan

            # Convective stats from diagnostics
            ca_nmix = np.nan
            ca_guard = np.nan
            ca_maxiter = np.nan
            if 'diag_ca_nmix' in diag.columns:
                day_diag = diag[diag['day'] == day]
                if len(day_diag) > 0:
                    ca_nmix = float(day_diag['diag_ca_nmix'].values[0]) if 'diag_ca_nmix' in day_diag.columns else np.nan
                    ca_guard = float(day_diag['diag_ca_guard_hits'].values[0]) if 'diag_ca_guard_hits' in day_diag.columns else np.nan
                    ca_maxiter = float(day_diag['diag_ca_max_iter'].values[0]) if 'diag_ca_max_iter' in day_diag.columns else np.nan

            seasonal_data.append({
                'day': day,
                'month': month,
                'month_name': month_name,
                # Ocean 3D
                'temp_mean': temp_mean, 'temp_min': temp_min, 'temp_max': temp_max,
                'temp_surf_mean': temp_surf_mean, 'temp_surf_min': temp_surf_min, 'temp_surf_max': temp_surf_max,
                'temp_20m_mean': float(np.nanmean(temp_20m)) if len(temp_20m) > 0 else np.nan,
                'temp_100m_mean': float(np.nanmean(temp_100m)) if len(temp_100m) > 0 else np.nan,
                'temp_500m_mean': float(np.nanmean(temp_500m)) if len(temp_500m) > 0 else np.nan,
                'salt_mean': salt_mean, 'salt_min': salt_min, 'salt_max': salt_max,
                'dens_mean': dens_mean, 'dens_min': dens_min, 'dens_max': dens_max,
                # Velocities
                'u_max': u_max, 'v_max': v_max, 'w_max': w_max,
                'u_surf_max': u_surf_max, 'v_surf_max': v_surf_max,
                # Atmosphere
                'air_temp_mean': air_temp_mean, 'air_temp_min': air_temp_min, 'air_temp_max': air_temp_max,
                'humidity_mean': hum_mean,
                'cloud_mean': cld_mean,
                'wind_mean': wind_mean, 'wind_max': wind_max,
                'tau_max': tau_max,
                'sf_rate_mean': sf_mean, 'sf_rate_max': sf_max,
                # Diagnostics
                'euu': euu,
                'ca_nmix': ca_nmix, 'ca_guard': ca_guard, 'ca_maxiter': ca_maxiter,
            })

            ds.close()
        except Exception as e:
            print(f"Warning: Failed to read {nc_file}: {e}")
            continue

    if not seasonal_data:
        print("No seasonal data extracted")
        return 1

    seasonal_df = pd.DataFrame(seasonal_data)
    seasonal_df = seasonal_df.sort_values('day').reset_index(drop=True)

    # Merge with daily diagnostics if available
    if 'day' in diag.columns:
        diag_renamed = diag.copy()
        diag_renamed.columns = [f'diag_{c}' if c != 'day' else 'day' for c in diag_renamed.columns]
        seasonal_df = seasonal_df.merge(diag_renamed, on='day', how='left')

    # Save daily summary CSV
    seasonal_df.to_csv(output_daily_csv, index=False)
    print(f"Saved daily summary to {output_daily_csv}")

    # Create monthly summary
    monthly_summary = seasonal_df.groupby('month_name').agg({
        'temp_mean': ['mean', 'min', 'max'],
        'temp_surf_mean': ['mean', 'min', 'max'],
        'salt_mean': ['mean', 'min', 'max'],
        'dens_mean': ['mean', 'min', 'max'],
        'u_max': ['mean', 'max'],
        'v_max': ['mean', 'max'],
        'w_max': ['mean', 'max'],
        'air_temp_mean': ['mean', 'min', 'max'],
        'sf_rate_mean': ['mean', 'max'],
        'euu': ['mean', 'max'],
    }).round(4)

    monthly_summary.to_csv(output_monthly_csv)
    print(f"Saved monthly summary to {output_monthly_csv}")

    # Generate text report
    with open(output_txt, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("SEASONAL ANALYSIS: JANUARY-MARCH 2020 ERA5 + HEAT INTEGRATION\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Analyzed {len(seasonal_df)} daily NetCDF files\n")
        f.write(f"Source directory: {nc_dir}\n")
        f.write(f"Diagnostics CSV: {diag_csv}\n\n")

        f.write("-" * 80 + "\n")
        f.write("SEASONAL SUMMARY STATISTICS\n")
        f.write("-" * 80 + "\n")

        # Temperature
        f.write(f"\nOcean Temperature (3D):\n")
        f.write(f"  Mean: {seasonal_df['temp_mean'].mean():.3f} °C (min {seasonal_df['temp_min'].min():.3f}, max {seasonal_df['temp_max'].max():.3f})\n")
        f.write(f"  Surface Mean: {seasonal_df['temp_surf_mean'].mean():.3f} °C (min {seasonal_df['temp_surf_min'].min():.3f}, max {seasonal_df['temp_surf_max'].max():.3f})\n")

        # Vertical temperature structure
        f.write(f"\nVertical Temperature Structure:\n")
        f.write(f"  20m Mean: {seasonal_df['temp_20m_mean'].mean():.3f} °C\n")
        f.write(f"  100m Mean: {seasonal_df['temp_100m_mean'].mean():.3f} °C\n")
        f.write(f"  500m Mean: {seasonal_df['temp_500m_mean'].mean():.3f} °C\n")

        # Salinity
        f.write(f"\nSalinity (mass fraction):\n")
        f.write(f"  Mean: {seasonal_df['salt_mean'].mean():.5f} (min {seasonal_df['salt_min'].min():.5f}, max {seasonal_df['salt_max'].max():.5f})\n")

        # Density
        f.write(f"\nDensity Anomaly (g/cm³):\n")
        f.write(f"  Mean: {seasonal_df['dens_mean'].mean():.5f} (min {seasonal_df['dens_min'].min():.5f}, max {seasonal_df['dens_max'].max():.5f})\n")

        # Velocities
        f.write(f"\nVelocities (cm/s):\n")
        f.write(f"  U max: {seasonal_df['u_max'].max():.2f}, V max: {seasonal_df['v_max'].max():.2f}, W max: {seasonal_df['w_max'].max():.4f}\n")
        f.write(f"  Surface U max: {seasonal_df['u_surf_max'].max():.2f}, V max: {seasonal_df['v_surf_max'].max():.2f}\n")

        # Air temperature
        f.write(f"\nAir Temperature (forcing):\n")
        f.write(f"  Mean: {seasonal_df['air_temp_mean'].mean():.2f} °C (min {seasonal_df['air_temp_min'].min():.2f}, max {seasonal_df['air_temp_max'].max():.2f})\n")

        # Snowfall
        f.write(f"\nERA5 Snowfall Rate:\n")
        f.write(f"  Mean: {seasonal_df['sf_rate_mean'].mean():.3e} m/s\n")
        f.write(f"  Max:  {seasonal_df['sf_rate_max'].max():.3e} m/s\n")

        # Kinetic Energy
        f.write(f"\nKinetic Energy (EUU):\n")
        f.write(f"  Mean: {seasonal_df['euu'].mean():.3e} cm²/s²\n")
        f.write(f"  Max:  {seasonal_df['euu'].max():.3e} cm²/s²\n")

        # Daily diagnostics
        diag_cols = [c for c in seasonal_df.columns if c.startswith('diag_')]
        if diag_cols:
            f.write(f"\n\nDAILY DIAGNOSTICS SUMMARY\n")
            f.write("-" * 80 + "\n")
            for col in diag_cols:
                if seasonal_df[col].notna().any():
                    f.write(f"  {col}: mean={seasonal_df[col].mean():.3e}, min={seasonal_df[col].min():.3e}, max={seasonal_df[col].max():.3e}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("MONTHLY BREAKDOWN\n")
        f.write("=" * 80 + "\n")

        for month_num, month_name in [(1, "January"), (2, "February"), (3, "March")]:
            month_data = seasonal_df[seasonal_df['month'] == month_num]
            if len(month_data) == 0:
                continue

            f.write(f"\n--- {month_name} (Days {month_data['day'].min()}-{month_data['day'].max()}) ---\n")
            f.write(f"  Days: {len(month_data)}\n")
            f.write(f"  T mean: {month_data['temp_mean'].mean():.3f} °C (surface: {month_data['temp_surf_mean'].mean():.3f} °C)\n")
            f.write(f"  T range: {month_data['temp_min'].min():.3f} to {month_data['temp_max'].max():.3f} °C\n")
            f.write(f"  S mean: {month_data['salt_mean'].mean():.5f}\n")
            f.write(f"  RO mean: {month_data['dens_mean'].mean():.5f} g/cm³\n")
            f.write(f"  Air T: {month_data['air_temp_mean'].mean():.2f} °C\n")
            f.write(f"  Snowfall: {month_data['sf_rate_mean'].mean():.3e} m/s (max {month_data['sf_rate_max'].max():.3e})\n")
            f.write(f"  EUU: {month_data['euu'].mean():.3e} cm²/s²\n")
            if 'diag_ca_nmix' in month_data.columns:
                f.write(f"  nmix: {month_data['diag_ca_nmix'].mean():.0f}, guard: {month_data['diag_ca_guard_hits'].mean():.0f}, maxiter: {month_data['diag_ca_max_iter'].mean():.1f}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("PER-DAY DETAILS\n")
        f.write("=" * 80 + "\n")

        for _, row in seasonal_df.iterrows():
            f.write(f"\nDay {int(row['day']):2d} ({row['month_name']}):\n")
            f.write(f"  T: {row['temp_mean']:.3f} °C (surf: {row['temp_surf_mean']:.3f}, 20m: {row['temp_20m_mean']:.3f}, 100m: {row['temp_100m_mean']:.3f})\n")
            f.write(f"  S: {row['salt_mean']:.5f}, RO: {row['dens_mean']:.5f} g/cm³\n")
            f.write(f"  U/V/W max: {row['u_max']:.1f}/{row['v_max']:.1f}/{row['w_max']:.3f} cm/s\n")
            f.write(f"  Air T: {row['air_temp_mean']:.2f} °C, Hum: {row['humidity_mean']:.3f}, Cloud: {row['cloud_mean']:.3f}\n")
            f.write(f"  Wind: {row['wind_mean']:.2f} m/s, Tau: {row['tau_max']:.3f} dyn/cm², Snowfall: {row['sf_rate_mean']:.3e} m/s\n")
            if 'diag_nmix' in row and not np.isnan(row.get('diag_nmix', np.nan)):
                f.write(f"  nmix: {int(row['diag_nmix'])}, guard: {int(row['diag_guard'])}, maxiter: {int(row['diag_maxiter'])}\n")

    print(f"Saved report to {output_txt}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Analyze seasonal ERA5 + HEAT integration diagnostics")
    parser.add_argument("--nc-dir", default="data/output", help="Directory with results_day_*.nc files")
    parser.add_argument("--diag-csv", default="data/output/daily_diagnostics.csv", help="Daily diagnostics CSV")
    parser.add_argument("--output-daily-csv", default="data/output/seasonal_daily_summary.csv", help="Output daily CSV")
    parser.add_argument("--output-monthly-csv", default="data/output/seasonal_monthly_summary.csv", help="Output monthly CSV")
    parser.add_argument("--output-txt", default="data/output/seasonal_report.txt", help="Output report TXT")
    args = parser.parse_args()

    return analyze_seasonal(args.nc_dir, args.diag_csv, args.output_daily_csv, args.output_monthly_csv, args.output_txt)


if __name__ == "__main__":
    sys.exit(main())