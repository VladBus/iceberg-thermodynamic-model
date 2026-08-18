"""Plot standardized figures from AARI model daily output.

Figures produced (all PNG, dpi=150):
  surface_temperature.png   - surface T map for a chosen day (last day by default)
  surface_salinity.png      - surface S map
  surface_velocity.png      - surface |U| map
  daily_energy.png          - EUU vs model day (from daily diagnostics CSV)
  convective_stats.png      - guard hits / affected columns vs day
  vertical_profiles.png     - horizontal-mean T/S vertical profiles

Python only READS model output and visualizes it; no physics.
"""

import argparse
import glob
import pathlib

import matplotlib

matplotlib.use("Agg")  # pylint: disable=wrong-import-position
import matplotlib.pyplot as plt  # pylint: disable=wrong-import-position
import numpy as np  # pylint: disable=wrong-import-position
import pandas as pd  # pylint: disable=wrong-import-position
import xarray as xr  # pylint: disable=wrong-import-position

import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "analysis"))
from units import temperature_k_to_c, velocity_mps_to_cmps
from run_context import resolve_run, add_run_args

DPI = 150


def _load_daily(path):
    return xr.open_dataset(path)


def plot_surface_maps(day_file, outdir):
    """Plot surface T/S/speed maps for one daily snapshot."""
    ds = _load_daily(day_file)
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
        units_label = (
            "degC" if var == "temperature" else str(ds[var].attrs.get("units", ""))
        )
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


def plot_daily_series(diag_csv, outdir):
    """Plot EUU and convective statistics vs model day."""
    df = pd.read_csv(diag_csv)
    if "euu" not in df.columns:
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["day"], df["euu"], marker="o", ms=3)
    ax.set_xlabel("model day")
    ax.set_ylabel("EUU (cm2/s2)")
    ax.set_title("Domain kinetic energy (EUU) per model day")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "daily_energy.png", dpi=DPI)
    plt.close(fig)

    if {"ca_guard_hits", "ca_affected_cols"}.issubset(df.columns):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df["day"], df["ca_guard_hits"], label="guard hits", marker="o", ms=3)
        ax.plot(
            df["day"], df["ca_affected_cols"], label="affected cols", marker="s", ms=3
        )
        ax.set_xlabel("model day")
        ax.set_ylabel("columns")
        ax.set_title("Convective adjustment monitoring (guard preserved)")
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(outdir / "convective_stats.png", dpi=DPI)
        plt.close(fig)


def plot_vertical_profiles(glob_pattern, outdir):
    """Plot horizontal-mean T/S vertical profiles over days."""
    files = sorted(glob.glob(glob_pattern))
    if not files:
        return
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    for f in files[::6]:  # subsample for readability
        ds = xr.open_dataset(f)
        kt = ds["water_column_levels"].values
        depths = ds["depth"].values
        t = np.array(
            [
                float(
                    temperature_k_to_c(
                        ds["temperature"].isel(depth=k).values[kt > k]
                    ).mean()
                )
                for k in range(ds.sizes["depth"])
            ]
        )
        s = np.array(
            [
                float(ds["salinity_mass_fraction"].isel(depth=k).values[kt > k].mean())
                for k in range(ds.sizes["depth"])
            ]
        )
        day = f.split("_")[-1].split(".")[0]
        axes[0].plot(t, depths, label=f"day {day}")
        axes[1].plot(s, depths, label=f"day {day}")
        ds.close()
    axes[0].set_ylabel("depth (m)")
    axes[0].set_xlabel("T (degC)")
    axes[0].set_title("Horizontal-mean temperature profile")
    axes[1].set_xlabel("S (mass fraction)")
    axes[1].set_title("Horizontal-mean salinity profile")
    axes[0].invert_yaxis()
    axes[1].invert_yaxis()
    axes[0].legend(fontsize=7)
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(outdir / "vertical_profiles.png", dpi=DPI)
    plt.close(fig)


def main():
    """Generate all standardized figures from model output."""
    parser = argparse.ArgumentParser(
        description="Plot standardized figures from model output."
    )
    add_run_args(parser, default_run_id="2020_Q1_test_heat_on")
    parser.add_argument(
        "--glob", default=None, help="Daily NetCDF glob (default: run nc dir)"
    )
    parser.add_argument(
        "--diag", default=None, help="Daily diagnostics CSV (default: run csv dir)"
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Output directory for PNGs (default: run figures dir)",
    )
    parser.add_argument(
        "--day", type=int, default=None, help="Day to plot surface maps (default: last)"
    )
    args = parser.parse_args()

    try:
        ctx = resolve_run(run_id=args.run_id, manifest=args.manifest)
    except Exception as e:
        print(f"ERROR: Failed to resolve run: {e}")
        return 1

    nc_glob = (
        str(args.glob) if args.glob else str(ctx.nc_dir / "results_day_[0-9][0-9].nc")
    )
    diag = str(args.diag) if args.diag else str(ctx.daily_diagnostics)
    outdir = pathlib.Path(args.outdir) if args.outdir else ctx.fig_dir
    outdir.mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(nc_glob))
    if not files:
        print(f"WARNING: no daily NetCDF files match {nc_glob}")
    else:
        day_file = files[-1]
        if args.day is not None:
            matches = [
                f for f in files if int(f.split("_")[-1].split(".")[0]) == args.day
            ]
            if matches:
                day_file = matches[0]
        print("Surface maps from:", day_file)
        plot_surface_maps(day_file, outdir)

    diag_path = pathlib.Path(diag)
    if diag_path.exists():
        plot_daily_series(str(diag_path), outdir)
    else:
        print(f"WARNING: {diag_path} not found; skipping time-series plots")

    plot_vertical_profiles(nc_glob, outdir)

    produced = sorted(outdir.glob("*.png"))
    print(f"Figures written to {outdir}:")
    for p in produced:
        print("  ", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
