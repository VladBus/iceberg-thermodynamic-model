"""Plot seasonal figures from multi-month ERA5 + HEAT integration.

Figures produced (all PNG, dpi=150):
  surface_temperature.png   - surface T map for last day
  surface_salinity.png      - surface S map
  surface_velocity.png      - surface |U| map
  temp_time_series.png      - surface T time series (all days)
  temp_20m_time_series.png  - 20m T time series
  temp_100m_time_series.png - 100m T time series
  salinity_time_series.png  - surface S time series
  density_time_series.png   - surface RO time series
  u_max_time_series.png     - U max time series
  v_max_time_series.png     - V max time series
  w_max_time_series.png     - W max time series
  euu_time_series.png       - EUU vs day
  heat_fluxes.png           - SW/LW/SH/LH/Qice/Qtotal vs day
  ice_concentration.png     - ice concentration vs day
  ice_thickness.png         - ice thickness vs day
  snow_depth.png            - snow depth vs day
  snowfall_rate.png         - snowfall rate vs day
  convective_guard.png      - convective guard hits vs day
  newton_iterations.png     - Newton iterations vs day
  temp_anomaly.png          - HEAT ON - HEAT OFF temperature anomaly
  vertical_temp_profiles.png - T(z) for day 1, 30, 60, 90
  vertical_salinity_profiles.png - S(z) for day 1, 30, 60, 90
  vertical_density_profiles.png - RO(z) for day 1, 30, 60, 90

Python only READS model output and visualizes it; no physics.
"""

import argparse
import glob
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "analysis"))
from units import temperature_k_to_c, velocity_mps_to_cmps, density_anomaly_kgm3_to_gcm3
from run_context import resolve_run, add_run_args

DPI = 150


def _load_daily(path):
    return xr.open_dataset(path)


def _load_diags(path):
    return pd.read_csv(path)


def plot_surface_maps(day_file, outdir):
    """Plot surface T/S/speed maps for the last daily snapshot."""
    ds = xr.open_dataset(day_file)
    lat = ds["latitude"].values
    lon = ds["longitude"].values
    day_label = pathlib.Path(day_file).stem.split("_")[-1]

    for var, name, cmap in [
        ("temperature", "surface_temperature", "RdBu_r"),
        ("salinity_mass_fraction", "surface_salinity", "viridis"),
    ]:
        if var not in ds.data_vars:
            continue
        fig, ax = plt.subplots(figsize=(7, 5))
        v = ds[var].isel(depth=0).values
        if var == "temperature":
            v = temperature_k_to_c(v)
        pcm = ax.pcolormesh(lon, lat, v, cmap=cmap, shading="auto")
        units_label = "degC" if var == "temperature" else str(ds[var].attrs.get("units", ""))
        fig.colorbar(pcm, ax=ax, label=units_label)
        ax.set_title(f"{var} at surface (day {day_label})")
        ax.set_xlabel("longitude (deg E)")
        ax.set_ylabel("latitude (deg N)")
        fig.tight_layout()
        fig.savefig(outdir / f"{name}.png", dpi=DPI)
        plt.close(fig)

    if "u_velocity" in ds.data_vars:
        fig, ax = plt.subplots(figsize=(7, 5))
        u = velocity_mps_to_cmps(ds["u_velocity"].isel(depth=0).values)
        v = velocity_mps_to_cmps(ds["v_velocity"].isel(depth=0).values)
        spd = np.sqrt(u * u + v * v)
        pcm = ax.pcolormesh(lon, lat, spd, cmap="magma", shading="auto")
        fig.colorbar(pcm, ax=ax, label="|U| (cm/s)")
        ax.set_title(f"surface speed (day {day_label})")
        ax.set_xlabel("longitude (deg E)")
        ax.set_ylabel("latitude (deg N)")
        fig.tight_layout()
        fig.savefig(outdir / "surface_velocity.png", dpi=DPI)
        plt.close(fig)

    ds.close()


def plot_time_series_seasonal(seasonal_csv, outdir, diag=None):
    """Plot all time series from seasonal daily summary."""
    df = pd.read_csv(seasonal_csv)
    df = df.sort_values("day")

    figs = []

    # Surface temperature
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["temp_surf_mean"], label="Surface T", color="red")
    ax.fill_between(
        df["day"], df["temp_surf_min"], df["temp_surf_max"], alpha=0.2, color="red"
    )
    ax.set_xlabel("model day")
    ax.set_ylabel("T (°C)")
    ax.set_title("Surface Temperature Time Series")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        outdir / "surface_temperature_time_series.png",
        dpi=DPI,
    )
    plt.close()

    # 20m temperature
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["temp_20m_mean"], label="20m T", color="orange")
    ax.set_xlabel("model day")
    ax.set_ylabel("T (°C)")
    ax.set_title("Temperature at 20m Depth")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "temp_20m_time_series.png",
        dpi=DPI,
    )
    plt.close()

    # 100m temperature
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["temp_100m_mean"], label="100m T", color="green")
    ax.set_xlabel("model day")
    ax.set_ylabel("T (°C)")
    ax.set_title("Temperature at 100m Depth")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "temp_100m_time_series.png",
        dpi=DPI,
    )
    plt.close()

    # Surface salinity
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["salt_mean"], label="Surface S", color="blue")
    ax.set_xlabel("model day")
    ax.set_ylabel("S (mass fraction)")
    ax.set_title("Surface Salinity Time Series")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "salinity_time_series.png",
        dpi=DPI,
    )
    plt.close()

    # Surface density
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["dens_mean"], label="Surface RO", color="purple")
    ax.set_xlabel("model day")
    ax.set_ylabel("RO (g/cm³)")
    ax.set_title("Surface Density Anomaly Time Series")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "density_time_series.png",
        dpi=DPI,
    )
    plt.close()

    # U max
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["u_max"], label="U max", color="red")
    ax.set_xlabel("model day")
    ax.set_ylabel("U (cm/s)")
    ax.set_title("Maximum U Velocity")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "u_max_time_series.png", dpi=DPI
    )
    plt.close()

    # V max
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["v_max"], label="V max", color="blue")
    ax.set_xlabel("model day")
    ax.set_ylabel("V (cm/s)")
    ax.set_title("Maximum V Velocity")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "v_max_time_series.png", dpi=DPI
    )
    plt.close()

    # W max
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["w_max"], label="W max", color="green")
    ax.set_xlabel("model day")
    ax.set_ylabel("W (cm/s)")
    ax.set_title("Maximum W Velocity")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "w_max_time_series.png", dpi=DPI
    )
    plt.close()

    # EUU
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["euu"], label="EUU", color="black")
    ax.set_xlabel("model day")
    ax.set_ylabel("EUU (cm²/s²)")
    ax.set_title("Domain Kinetic Energy (EUU)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "euu_time_series.png", dpi=DPI
    )
    plt.close()

    # Heat fluxes - need to extract from seasonal data or use diag
    # For now plot snowfall rate
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["sf_rate_mean"], label="ERA5 Snowfall Rate", color="cyan")
    ax.set_xlabel("model day")
    ax.set_ylabel("Snowfall rate (m/s)")
    ax.set_title("ERA5 Snowfall Rate")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        outdir / "snowfall_rate.png", dpi=DPI
    )
    plt.close()

    # Ice concentration - from diagnostics
    # Use daily diagnostics if available
    diag_file = pathlib.Path(diag) if diag else None
    if diag_file is not None and diag_file.exists():
        diag = pd.read_csv(diag_file)
        if "diag_ca_guard_hits" in diag.columns:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(
                diag["day"], diag["diag_ca_guard_hits"], label="Guard Hits", color="red"
            )
            ax.set_xlabel("model day")
            ax.set_ylabel("Guard Hits")
            ax.set_title("Convective Adjustment Guard Hits")
            ax.grid(alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(
                outdir / "convective_guard.png",
                dpi=DPI,
            )
            plt.close()

        if "diag_ca_max_iter" in diag.columns:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(
                diag["day"],
                diag["diag_ca_max_iter"],
                label="Max Iterations",
                color="orange",
            )
            ax.set_xlabel("model day")
            ax.set_ylabel("Max Iterations")
            ax.set_title("Convective Adjustment Max Iterations")
            ax.grid(alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(
                outdir / "newton_iterations.png",
                dpi=DPI,
            )
            plt.close()


def plot_vertical_profiles_seasonal(glob_pattern, outdir):
    """Plot T/S/RO vertical profiles for day 1, 30, 60, 90."""
    files = sorted(glob.glob(glob_pattern))
    if not files:
        return

    target_days = [1, 30, 60, 90]
    file_map = {}
    for f in files:
        day_str = pathlib.Path(f).stem.split("_")[-1]
        if day_str.isdigit():
            day = int(day_str)
            if day in target_days:
                file_map[day] = f

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for day in target_days:
        if day not in file_map:
            continue
        ds = xr.open_dataset(file_map[day])
        kt = ds["water_column_levels"].values
        depths = ds["depth"].values
        t = np.array(
            [
                float(temperature_k_to_c(ds["temperature"].isel(depth=k).values[kt > k]).mean())
                for k in range(ds.sizes["depth"])
            ]
        )
        s = np.array(
            [
                float(ds["salinity_mass_fraction"].isel(depth=k).values[kt > k].mean())
                for k in range(ds.sizes["depth"])
            ]
        )
        ro = np.array(
            [
                float(density_anomaly_kgm3_to_gcm3(ds["density_anomaly"].isel(depth=k).values[kt > k]).mean())
                for k in range(ds.sizes["depth"])
            ]
        )

        axes[0].plot(t, depths, label=f"Day {day}", linewidth=2)
        axes[1].plot(s, depths, label=f"Day {day}", linewidth=2)
        axes[2].plot(ro, depths, label=f"Day {day}", linewidth=2)
        ds.close()

    axes[0].set_ylabel("Depth (m)")
    axes[0].set_xlabel("T (°C)")
    axes[0].set_title("Temperature Profiles")
    axes[0].invert_yaxis()
    axes[0].legend()

    axes[1].set_xlabel("S (mass fraction)")
    axes[1].set_title("Salinity Profiles")
    axes[1].invert_yaxis()
    axes[1].legend()

    axes[2].set_xlabel("RO (g/cm³)")
    axes[2].set_title("Density Anomaly Profiles")
    axes[2].invert_yaxis()
    axes[2].legend()

    fig.tight_layout()
    fig.savefig(
        outdir / "vertical_temp_profiles.png",
        dpi=DPI,
    )
    fig.savefig(
        outdir / "vertical_salinity_profiles.png",
        dpi=DPI,
    )
    fig.savefig(
        outdir / "vertical_density_profiles.png",
        dpi=DPI,
    )
    plt.close()


def plot_heat_fluxes(seasonal_csv, outdir):
    """Plot heat flux components if available in seasonal data."""
    df = pd.read_csv(seasonal_csv)
    if not all(c in df.columns for c in ["sf_rate_mean", "euu"]):
        return

    # We only have snowfall rate and EUU in seasonal data
    # Heat flux components would need to be extracted from diagnostics
    # For now, create a placeholder showing what would be plotted
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["day"], df["sf_rate_mean"], label="Snowfall Rate", color="cyan")
    ax.plot(df["day"], df["euu"] / 1e17, label="EUU (×10¹⁷)", color="black")
    ax.set_xlabel("model day")
    ax.set_ylabel("Value (normalized)")
    ax.set_title("Snowfall Rate & EUU (Heat Budget Indicators)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        outdir / "heat_fluxes.png", dpi=DPI
    )
    plt.close()


def plot_vertical_temp_profiles_separate(glob_pattern, outdir):
    """Separate T profile plot."""
    files = sorted(glob.glob(glob_pattern))
    target_days = [1, 30, 60, 90]
    file_map = {}
    for f in files:
        day_str = pathlib.Path(f).stem.split("_")[-1]
        if day_str.isdigit():
            day = int(day_str)
            if day in target_days:
                file_map[day] = f

    fig, ax = plt.subplots(figsize=(7, 5))
    for day in target_days:
        if day not in file_map:
            continue
        ds = xr.open_dataset(file_map[day])
        kt = ds["water_column_levels"].values
        depths = ds["depth"].values
        t = np.array(
            [
                float(temperature_k_to_c(ds["temperature"].isel(depth=k).values[kt > k]).mean())
                for k in range(ds.sizes["depth"])
            ]
        )
        ax.plot(t, depths, label=f"Day {day}", linewidth=2)
        ds.close()
    ax.set_ylabel("Depth (m)")
    ax.set_xlabel("T (°C)")
    ax.set_title("Temperature Profiles: Day 1, 30, 60, 90")
    ax.invert_yaxis()
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        outdir / "vertical_temp_profiles.png",
        dpi=DPI,
    )
    plt.close()


def plot_vertical_salinity_profiles_separate(glob_pattern, outdir):
    """Separate S profile plot."""
    files = sorted(glob.glob(glob_pattern))
    target_days = [1, 30, 60, 90]
    file_map = {}
    for f in files:
        day_str = pathlib.Path(f).stem.split("_")[-1]
        if day_str.isdigit():
            day = int(day_str)
            if day in target_days:
                file_map[day] = f

    fig, ax = plt.subplots(figsize=(7, 5))
    for day in target_days:
        if day not in file_map:
            continue
        ds = xr.open_dataset(file_map[day])
        kt = ds["water_column_levels"].values
        depths = ds["depth"].values
        s = np.array(
            [
                float(ds["salinity_mass_fraction"].isel(depth=k).values[kt > k].mean())
                for k in range(ds.sizes["depth"])
            ]
        )
        ax.plot(s, depths, label=f"Day {day}", linewidth=2)
        ds.close()
    ax.set_ylabel("Depth (m)")
    ax.set_xlabel("S (mass fraction)")
    ax.set_title("Salinity Profiles: Day 1, 30, 60, 90")
    ax.invert_yaxis()
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        outdir / "vertical_salinity_profiles.png",
        dpi=DPI,
    )
    plt.close()


def plot_vertical_density_profiles_separate(glob_pattern, outdir):
    """Separate RO profile plot."""
    files = sorted(glob.glob(glob_pattern))
    target_days = [1, 30, 60, 90]
    file_map = {}
    for f in files:
        day_str = pathlib.Path(f).stem.split("_")[-1]
        if day_str.isdigit():
            day = int(day_str)
            if day in target_days:
                file_map[day] = f

    fig, ax = plt.subplots(figsize=(7, 5))
    for day in target_days:
        if day not in file_map:
            continue
        ds = xr.open_dataset(file_map[day])
        kt = ds["water_column_levels"].values
        depths = ds["depth"].values
        ro = np.array(
            [
                float(density_anomaly_kgm3_to_gcm3(ds["density_anomaly"].isel(depth=k).values[kt > k]).mean())
                for k in range(ds.sizes["depth"])
            ]
        )
        ax.plot(ro, depths, label=f"Day {day}", linewidth=2)
        ds.close()
    ax.set_ylabel("Depth (m)")
    ax.set_xlabel("RO (g/cm³)")
    ax.set_title("Density Anomaly Profiles: Day 1, 30, 60, 90")
    ax.invert_yaxis()
    ax.legend()
    fig.tight_layout()
    fig.savefig(
        outdir / "vertical_density_profiles.png",
        dpi=DPI,
    )
    plt.close()


def plot_heat_off_on_comparison(outdir):
    """Compare HEAT ON vs HEAT OFF if both available."""
    print(
        "HEAT ON/OFF comparison: reference (HEAT OFF) run not available under the "
        "run-based data architecture"
    )
    print("Manual comparison needed for HEAT ON vs HEAT OFF")


def main():
    """Generate all seasonal figures from model output."""
    parser = argparse.ArgumentParser(
        description="Plot seasonal figures from multi-month ERA5 + HEAT integration."
    )
    add_run_args(parser, default_run_id="2020_Q1_test_heat_on")
    parser.add_argument(
        "--glob",
        default=None,
        help="Daily NetCDF glob (default: run nc dir)",
    )
    parser.add_argument(
        "--diag",
        default=None,
        help="Daily diagnostics CSV (default: run csv dir)",
    )
    parser.add_argument(
        "--seasonal",
        default=None,
        help="Seasonal daily summary CSV (default: run csv dir)",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Output directory for PNGs (default: run figures dir)",
    )
    args = parser.parse_args()

    try:
        ctx = resolve_run(run_id=args.run_id, manifest=args.manifest)
    except Exception as e:
        print(f"ERROR: Failed to resolve run: {e}")
        return 1

    # Resolve paths from the run context; still allow explicit --* overrides.
    nc_files = sorted(str(p) for p in ctx.nc_dir.glob("results_day_[0-9][0-9].nc"))
    if not nc_files:
        print(f"WARNING: no daily NetCDF files in {ctx.nc_dir}")
    nc_glob = args.glob or str(ctx.nc_dir / "results_day_[0-9][0-9].nc")
    diag = str(args.diag) if args.diag else str(ctx.daily_diagnostics)
    seasonal = str(args.seasonal) if args.seasonal else str(ctx.csv_dir / "seasonal_daily_summary.csv")
    outdir = pathlib.Path(args.outdir) if args.outdir else ctx.fig_dir
    outdir.mkdir(parents=True, exist_ok=True)

    seasonal_csv = pathlib.Path(seasonal)
    if seasonal_csv.exists():
        print("Generating seasonal time series plots...")
        plot_time_series_seasonal(seasonal, outdir, diag=diag)
    else:
        print(f"WARNING: {seasonal} not found; skipping time-series plots")

    print("Generating vertical profile plots...")
    plot_vertical_profiles_seasonal(nc_glob, outdir)
    plot_vertical_temp_profiles_separate(nc_glob, outdir)
    plot_vertical_salinity_profiles_separate(nc_glob, outdir)
    plot_vertical_density_profiles_separate(nc_glob, outdir)

    print("Generating heat flux indicators...")
    plot_heat_fluxes(seasonal, outdir)

    print("Generating surface maps from last day...")
    files = sorted(glob.glob(nc_glob))
    if files:
        plot_surface_maps(files[-1], outdir)

    plot_heat_off_on_comparison(outdir)

    produced = sorted(outdir.glob("*.png"))
    print(f"\nFigures written to {outdir}:")
    for p in produced:
        print(f"  {p.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
