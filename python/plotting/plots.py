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

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

DEFAULT_GLOB = "data/output/results_day_[0-9][0-9].nc"
DEFAULT_DIAG = "data/output/daily_diagnostics.csv"
DEFAULT_OUTDIR = "python/plotting/figures"

DPI = 150


def _load_daily(path):
    return xr.open_dataset(path)


def plot_surface_maps(day_file, outdir):
    ds = _load_daily(day_file)
    lat = ds["latitude"].values
    lon = ds["longitude"].values
    day_label = pathlib.Path(day_file).stem.split("_")[-1]

    for var, name, cmap in [
        ("temperature", "surface_temperature", "RdBu_r"),
        ("salinity", "surface_salinity", "viridis"),
    ]:
        if var not in ds.data_vars:
            continue
        fig, ax = plt.subplots(figsize=(7, 5))
        v = ds[var].isel(depth=0).values
        pcm = ax.pcolormesh(lon, lat, v, cmap=cmap, shading="auto")
        fig.colorbar(pcm, ax=ax, label=str(ds[var].attrs.get("units", "")))
        ax.set_title(f"{var} at surface (day {day_label})")
        ax.set_xlabel("longitude (deg E)")
        ax.set_ylabel("latitude (deg N)")
        fig.tight_layout()
        fig.savefig(outdir / f"{name}.png", dpi=DPI)
        plt.close(fig)

    if "u_velocity" in ds.data_vars:
        fig, ax = plt.subplots(figsize=(7, 5))
        u = ds["u_velocity"].isel(depth=0).values
        v = ds["v_velocity"].isel(depth=0).values
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
                float(ds["temperature"].isel(depth=k).values[kt > k].mean())
                for k in range(ds.sizes["depth"])
            ]
        )
        s = np.array(
            [
                float(ds["salinity"].isel(depth=k).values[kt > k].mean())
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
    parser = argparse.ArgumentParser(
        description="Plot standardized figures from model output."
    )
    parser.add_argument("--glob", default=DEFAULT_GLOB, help="Daily NetCDF glob")
    parser.add_argument("--diag", default=DEFAULT_DIAG, help="Daily diagnostics CSV")
    parser.add_argument(
        "--outdir", default=DEFAULT_OUTDIR, help="Output directory for PNGs"
    )
    parser.add_argument(
        "--day", type=int, default=None, help="Day to plot surface maps (default: last)"
    )
    args = parser.parse_args()

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(args.glob))
    if not files:
        print(f"WARNING: no daily NetCDF files match {args.glob}")
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

    diag = pathlib.Path(args.diag)
    if diag.exists():
        plot_daily_series(str(diag), outdir)
    else:
        print(f"WARNING: {diag} not found; skipping time-series plots")

    plot_vertical_profiles(args.glob, outdir)

    produced = sorted(outdir.glob("*.png"))
    print(f"Figures written to {outdir}:")
    for p in produced:
        print("  ", p.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
