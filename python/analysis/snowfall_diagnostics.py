"""Analyze ERA5 snowfall data and model snowfall diagnostics.

Reads daily NetCDF files and daily_diagnostics.csv to produce:
- data/output/snowfall_daily.csv
- data/output/snowfall_report.txt

Analyzes:
- snowfall rate time series
- snow depth evolution
- ice/snow interaction
- heat flux impact
"""

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd
import xarray as xr


def analyze_snowfall_diagnostics(nc_dir, diag_csv, output_csv, output_txt):
    """Analyze snowfall diagnostics from model output."""

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

    # Extract snowfall-relevant variables from NetCDF
    snow_data = []
    for nc_file in nc_files:
        if "final" in nc_file.name:
            continue
        try:
            ds = xr.open_dataset(nc_file)

            # Extract day number from filename
            day_str = nc_file.stem.split("_")[-1]
            day = int(day_str) if day_str.isdigit() else 0

            # Snowfall rate (from ERA5 forcing)
            if 'era5_snowfall_rate' in ds.data_vars:
                sf_rate = ds['era5_snowfall_rate'].values
                sf_rate_mean = np.nanmean(sf_rate)
                sf_rate_max = np.nanmax(sf_rate)
                sf_rate_min = np.nanmin(sf_rate)
            else:
                sf_rate_mean = sf_rate_max = sf_rate_min = np.nan

            # Snow depth (from model state)
            if 'hsnp' in ds.data_vars:
                # hsnp is snow depth per category
                hsnp = ds['hsnp'].values
                snow_depth_mean = np.nanmean(hsnp)
                snow_depth_max = np.nanmax(hsnp)
                snow_depth_min = np.nanmin(hsnp)
            else:
                snow_depth_mean = snow_depth_max = snow_depth_min = np.nan

            # Ice thickness
            if 'hicp' in ds.data_vars:
                hicp = ds['hicp'].values
                ice_thick_mean = np.nanmean(hicp)
                ice_thick_max = np.nanmax(hicp)
            else:
                ice_thick_mean = ice_thick_max = np.nan

            # Ice concentration
            if 'an1' in ds.data_vars:
                an1 = ds['an1'].values
                ice_conc_mean = np.nanmean(an1[:, :, 1:])
            else:
                ice_conc_mean = np.nan

            # Surface temperature
            if 'temperature' in ds.data_vars:
                temp = ds['temperature'].values
                temp_surf = ds['temperature'].isel(depth=0).values
                temp_surf_mean = np.nanmean(temp_surf)
                temp_surf_min = np.nanmin(temp_surf)
                temp_surf_max = np.nanmax(temp_surf)
            else:
                temp_surf_mean = temp_surf_min = temp_surf_max = np.nan

            # Air temperature (forcing)
            if 'air_temp' in ds.data_vars:
                air_temp = ds['air_temp'].values
                air_temp_mean = np.nanmean(air_temp)
                air_temp_min = np.nanmin(air_temp)
                air_temp_max = np.nanmax(air_temp)
            else:
                air_temp_mean = air_temp_min = air_temp_max = np.nan

            # ERA5 snowfall rate
            if 'era5_snowfall_rate' in ds.data_vars:
                sf = ds['era5_snowfall_rate'].values
                sf_mean = np.nanmean(sf)
                sf_max = np.nanmax(sf)
            else:
                sf_mean = sf_max = np.nan

            # Heat fluxes (if available in diagnostics)
            snow_data.append({
                'day': day,
                'sf_rate_mean': sf_mean,
                'sf_rate_max': sf_max,
                'snow_depth_mean': snow_depth_mean,
                'snow_depth_max': snow_depth_max,
                'snow_depth_min': snow_depth_min,
                'ice_thick_mean': ice_thick_mean,
                'ice_thick_max': ice_thick_max,
                'ice_conc_mean': ice_conc_mean,
                'temp_surf_mean': temp_surf_mean,
                'temp_surf_min': temp_surf_min,
                'temp_surf_max': temp_surf_max,
                'air_temp_mean': air_temp_mean,
                'air_temp_min': air_temp_min,
                'air_temp_max': air_temp_max,
                'sf_rate_mean': sf_mean,
                'sf_rate_max': sf_max,
            })

            ds.close()
        except Exception as e:
            print(f"Warning: Failed to read {nc_file}: {e}")
            continue

    if not snow_data:
        print("No snow data extracted")
        return 1

    snow_df = pd.DataFrame(snow_data)
    snow_df = snow_df.sort_values('day').reset_index(drop=True)

    # Merge with daily diagnostics if available
    if 'day' in diag.columns:
        diag_renamed = diag.copy()
        diag_renamed.columns = [f'diag_{c}' if c != 'day' else 'day' for c in diag_renamed.columns]
        snow_df = snow_df.merge(diag_renamed, on='day', how='left')

    # Save CSV
    snow_df.to_csv(output_csv, index=False)
    print(f"Saved snowfall summary to {output_csv}")

    # Generate text report
    with open(output_txt, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("SNOWFALL DIAGNOSTIC REPORT\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Analyzed {len(snow_df)} daily NetCDF files\n")
        f.write(f"Source directory: {nc_dir}\n")
        f.write(f"Diagnostics CSV: {diag_csv}\n\n")

        f.write("-" * 70 + "\n")
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 70 + "\n")

        # ERA5 snowfall rate
        f.write(f"\nERA5 Snowfall Rate (m/s):\n")
        f.write(f"  Mean: {snow_df['sf_rate_mean'].mean():.3e}\n")
        f.write(f"  Max:  {snow_df['sf_rate_max'].max():.3e}\n")

        # Snow depth
        if not snow_df['snow_depth_mean'].isna().all():
            f.write(f"\nSnow Depth (m):\n")
            f.write(f"  Mean: {snow_df['snow_depth_mean'].mean():.4f}\n")
            f.write(f"  Max:  {snow_df['snow_depth_max'].max():.4f}\n")

        # Ice thickness
        if not snow_df['ice_thick_mean'].isna().all():
            f.write(f"\nIce Thickness (m):\n")
            f.write(f"  Mean: {snow_df['ice_thick_mean'].mean():.3f}\n")
            f.write(f"  Max:  {snow_df['ice_thick_max'].max():.3f}\n")

        # Ice concentration
        if not snow_df['ice_conc_mean'].isna().all():
            f.write(f"\nIce Concentration:\n")
            f.write(f"  Mean: {snow_df['ice_conc_mean'].mean():.3f}\n")

        # Temperatures
        f.write(f"\nSurface Temperature (°C):\n")
        f.write(f"  Mean: {snow_df['temp_surf_mean'].mean():.2f}\n")
        f.write(f"  Min:  {snow_df['temp_surf_min'].min():.2f}\n")
        f.write(f"  Max:  {snow_df['temp_surf_max'].max():.2f}\n")

        f.write(f"\nAir Temperature (°C):\n")
        f.write(f"  Mean: {snow_df['air_temp_mean'].mean():.2f}\n")
        f.write(f"  Min:  {snow_df['air_temp_min'].min():.2f}\n")
        f.write(f"  Max:  {snow_df['air_temp_max'].max():.2f}\n")

        # Daily diagnostics if available
        diag_cols = [c for c in snow_df.columns if c.startswith('diag_')]
        if diag_cols:
            f.write(f"\n\nDAILY DIAGNOSTICS (from daily_diagnostics.csv)\n")
            f.write("-" * 70 + "\n")
            for col in diag_cols:
                if snow_df[col].notna().any():
                    f.write(f"  {col}: mean={snow_df[col].mean():.3e}, min={snow_df[col].min():.3e}, max={snow_df[col].max():.3e}\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("PER-DAY DETAILS\n")
        f.write("=" * 70 + "\n")

        for _, row in snow_df.iterrows():
            f.write(f"\nDay {int(row['day']):2d}:\n")
            f.write(f"  ERA5 sf rate: {row['sf_rate_mean']:.3e} m/s (max {row['sf_rate_max']:.3e})\n")
            if not np.isnan(row['snow_depth_mean']):
                f.write(f"  Snow depth: {row['snow_depth_mean']:.4f} m (max {row['snow_depth_max']:.4f})\n")
            if not np.isnan(row['ice_thick_mean']):
                f.write(f"  Ice thick: {row['ice_thick_mean']:.3f} m (max {row['ice_thick_max']:.3f})\n")
            if not np.isnan(row['ice_conc_mean']):
                f.write(f"  Ice conc: {row['ice_conc_mean']:.3f}\n")
            f.write(f"  T_surf: {row['temp_surf_mean']:.2f} °C (range {row['temp_surf_min']:.2f}..{row['temp_surf_max']:.2f})\n")
            f.write(f"  T_air: {row['air_temp_mean']:.2f} °C (range {row['air_temp_min']:.2f}..{row['air_temp_max']:.2f})\n")
            if 'diag_nmix' in row and not pd.isna(row['diag_nmix']):
                f.write(f"  nmix: {int(row['diag_nmix'])}, guard: {int(row['diag_guard'])}, maxiter: {int(row['diag_maxiter'])}\n")

    print(f"Saved report to {output_txt}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Analyze snowfall diagnostics from model output")
    parser.add_argument("--nc-dir", default="data/output", help="Directory with results_day_*.nc files")
    parser.add_argument("--diag-csv", default="data/output/daily_diagnostics.csv", help="Daily diagnostics CSV")
    parser.add_argument("--output-csv", default="data/output/snowfall_daily.csv", help="Output CSV")
    parser.add_argument("--output-txt", default="data/output/snowfall_report.txt", help="Output report TXT")
    args = parser.parse_args()

    return analyze_snowfall_diagnostics(args.nc_dir, args.diag_csv, args.output_csv, args.output_txt)


if __name__ == "__main__":
    sys.exit(main())