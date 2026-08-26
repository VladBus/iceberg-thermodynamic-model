#!/usr/bin/env python3
"""
Stage 7.6B: Diagnostic plots and ERA5 domain mismatch analysis.

Reads:  data/input/processed/grid/ibcao_model_grid.nc
        data/input/generated/real_grid/{KOORD.DAT, hhh.bar}
        data/runs/2020_Q1_test_heat_on/output/nc/results_day_00.nc
Writes: data/output/diagnostics/stage7.6B/*.png
"""

import os
import sys
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import xarray as xr

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRID_SRC = os.path.join(
    PROJECT, "data", "input", "processed", "grid", "ibcao_model_grid.nc"
)
OUT_DIR = os.path.join(PROJECT, "data", "output", "diagnostics", "stage7.6B")
ERA5_FILE = os.path.join(
    PROJECT,
    "data",
    "input",
    "processed",
    "era5",
    "2020",
    "2020_Q1",
    "era5_2020_0103_barents_expanded_merged.nc",
)

IS1, JS1, KS = 133, 105, 18
LAND_CODE = 8
MAX_DEPTH_M = 600

Z_LEVELS_CM = np.array(
    [
        250.0,
        500.0,
        1000.0,
        1500.0,
        2000.0,
        2500.0,
        3000.0,
        4000.0,
        5000.0,
        7500.0,
        10000.0,
        15000.0,
        20000.0,
        25000.0,
        30000.0,
        40000.0,
        50000.0,
        60000,
    ],
    dtype=np.float32,
)


def load_grid():
    ds = xr.open_dataset(GRID_SRC)
    lat = ds["lat"].values
    lon = ds["lon"].values
    depth = ds["depth"].values
    mask = ds["mask"].values
    ds.close()
    return lat, lon, depth, mask


def load_day00():
    path = os.path.join(
        PROJECT,
        "data",
        "runs",
        "2020_Q1_test_heat_on",
        "output",
        "nc",
        "results_day_00.nc",
    )
    ds = xr.open_dataset(path)
    lat_nc = ds["latitude"].values
    lon_nc = ds["longitude"].values
    temp = ds["temperature"].values
    salt = ds["salinity_mass_fraction"].values
    kt1_nc = ds["water_column_levels"].values
    ds.close()
    return lat_nc, lon_nc, temp, salt, kt1_nc


def compute_kt1(depth, mask):
    """Compute KT1 from depth using Z-level centres (same as coup1)."""
    kt1 = np.zeros((IS1, JS1), dtype=np.int32)
    wet = mask == 1
    for i in range(IS1):
        for j in range(JS1):
            if not wet[i, j]:
                continue
            hht_cm = depth[i, j] * 100.0
            kt1[i, j] = 1
            for k in range(1, KS):
                if hht_cm < Z_LEVELS_CM[k]:
                    break
                kt1[i, j] = k + 1
    return kt1


def plot_depth_bathymetry(lat, lon, depth, mask):
    """Panel 1: Bathymetry with land mask."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Left: raw depth
    depth_plot = np.where(mask == 0, np.nan, depth)
    im0 = axes[0].pcolormesh(lon, lat, depth_plot, cmap="ocean", vmin=0, vmax=3000)
    axes[0].set_title("Bathymetry (m) — IBCAO V5.2 reconstructed grid")
    axes[0].set_xlabel("Longitude (°E)")
    axes[0].set_ylabel("Latitude (°N)")
    plt.colorbar(im0, ax=axes[0], label="Depth (m)", extend="max")

    # Right: capped depth (as model sees it)
    depth_capped = np.where(mask == 0, np.nan, np.clip(depth, 0, MAX_DEPTH_M))
    im1 = axes[1].pcolormesh(lon, lat, depth_capped, cmap="ocean", vmin=0, vmax=600)
    axes[1].set_title(f"Bathymetry capped at {MAX_DEPTH_M} m (model view)")
    axes[1].set_xlabel("Longitude (°E)")
    axes[1].set_ylabel("Latitude (°N)")
    plt.colorbar(im1, ax=axes[1], label="Depth (m)", extend="max")

    # Mark deep cells (>600m) on right panel
    deep = (mask == 1) & (depth > MAX_DEPTH_M)
    if deep.any():
        axes[1].scatter(
            lon[deep],
            lat[deep],
            c="red",
            s=1,
            alpha=0.5,
            label=f"{deep.sum()} cells >600m",
        )
        axes[1].legend(fontsize=8, loc="upper left")

    for ax in axes:
        ax.set_aspect("equal")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "01_bathymetry.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def plot_land_mask(mask, kt1):
    """Panel 2: Land mask and KT1."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Land/wet mask
    im0 = axes[0].pcolormesh(mask, cmap="RdYlBu_r", vmin=0, vmax=1)
    axes[0].set_title(f"Land/Wet Mask — {(mask==1).sum()} wet, {(mask==0).sum()} land")
    axes[0].set_xlabel("j index")
    axes[0].set_ylabel("i index")

    # KT1 (Z-level count)
    kt1_plot = np.where(mask == 0, np.nan, kt1)
    im1 = axes[1].pcolormesh(kt1_plot, cmap="viridis", vmin=1, vmax=KS)
    axes[1].set_title(f"KT1 (Z-levels active) — max={KS}")
    axes[1].set_xlabel("j index")
    axes[1].set_ylabel("i index")
    plt.colorbar(im1, ax=axes[1], label="KT1 (level count)")

    for ax in axes:
        ax.invert_yaxis()
        ax.set_aspect("equal")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "02_land_mask_kt1.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def plot_coordinates(lat, lon):
    """Panel 3: Latitude and longitude fields."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    im0 = axes[0].pcolormesh(lon, lat, lat, cmap="RdYlBu_r", vmin=64, vmax=85)
    axes[0].set_title("Latitude (°N)")
    axes[0].set_xlabel("Longitude (°E)")
    axes[0].set_ylabel("Latitude (°N)")
    plt.colorbar(im0, ax=axes[0], label="Latitude (°N)")

    im1 = axes[1].pcolormesh(lon, lat, lon, cmap="viridis", vmin=8, vmax=77)
    axes[1].set_title("Longitude (°E)")
    axes[1].set_xlabel("Longitude (°E)")
    axes[1].set_ylabel("Latitude (°N)")
    plt.colorbar(im1, ax=axes[1], label="Longitude (°E)")

    for ax in axes:
        ax.set_aspect("equal")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "03_coordinates.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def plot_era5_mismatch(lat, lon, mask):
    """Panel 4: ERA5 domain coverage mismatch."""
    try:
        ds = xr.open_dataset(ERA5_FILE)
        era5_lat = ds["latitude"].values
        era5_lon = ds["longitude"].values
        lat_min, lat_max = era5_lat.min(), era5_lat.max()
        lon_min, lon_max = era5_lon.min(), era5_lon.max()
        ds.close()
    except Exception:
        lat_min, lat_max = 66.0, 90.0
        lon_min, lon_max = 10.0, 70.0

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    # Grid coverage (all wet cells)
    wet = mask == 1
    ax.scatter(
        lon[wet],
        lat[wet],
        c="steelblue",
        s=2,
        alpha=0.3,
        label=f"Grid wet ({wet.sum()} cells)",
    )

    # Cells outside ERA5 domain
    outside_lat = wet & ((lat < lat_min) | (lat > lat_max))
    outside_lon = wet & ((lon < lon_min) | (lon > lon_max))
    outside = outside_lat | outside_lon
    if outside.any():
        ax.scatter(
            lon[outside],
            lat[outside],
            c="red",
            s=4,
            alpha=0.7,
            label=f"Outside ERA5 ({outside.sum()} cells)",
        )

    # ERA5 domain rectangle
    rect = Rectangle(
        (lon_min, lat_min),
        lon_max - lon_min,
        lat_max - lat_min,
        linewidth=2,
        edgecolor="green",
        facecolor="none",
        linestyle="--",
        label=f"ERA5 domain [{lat_min:.0f}-{lat_max:.0f}°N, {lon_min:.0f}-{lon_max:.0f}°E]",
    )
    ax.add_patch(rect)

    ax.set_title("ERA5 Domain Coverage Mismatch")
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.legend(fontsize=9)
    ax.set_aspect("equal")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "04_era5_domain_mismatch.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")

    # Compute mismatch stats
    total_wet = wet.sum()
    outside_count = outside.sum()
    outside_lat_count = outside_lat.sum()
    outside_lon_count = outside_lon.sum()
    print(f"\n  === ERA5 Domain Mismatch ===")
    print(f"  Grid wet cells: {total_wet}")
    print(f"  Outside ERA5 total: {outside_count} ({100*outside_count/total_wet:.1f}%)")
    print(f"  Outside lat only: {outside_lat_count}")
    print(f"  Outside lon only: {outside_lon_count}")
    print(f"  ERA5 lat: {lat_min:.1f}°N .. {lat_max:.1f}°N")
    print(f"  ERA5 lon: {lon_min:.1f}°E .. {lon_max:.1f}°E")
    print(f"  Grid lat: {lat.min():.1f}°N .. {lat.max():.1f}°N")
    print(f"  Grid lon: {lon.min():.1f}°E .. {lon.max():.1f}°E")

    return {
        "era5_lat_range": [float(lat_min), float(lat_max)],
        "era5_lon_range": [float(lon_min), float(lon_max)],
        "grid_lat_range": [float(lat.min()), float(lat.max())],
        "grid_lon_range": [float(lon.min()), float(lon.max())],
        "total_wet": int(total_wet),
        "outside_era5": int(outside_count),
        "outside_pct": float(100 * outside_count / total_wet),
    }


def plot_day00_temp_salt(lat_nc, lon_nc, temp, salt, kt1_nc, mask):
    """Panel 5: Day 00 T/S fields from model output."""
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    # Temperature at surface (k=0)
    temp_s = temp[0, :, :]  # (105, 133) = (y, x)
    im0 = axes[0].pcolormesh(lon_nc, lat_nc, temp_s, cmap="RdBu_r", vmin=270, vmax=300)
    axes[0].set_title("Temperature at surface (K) — Day 00")
    axes[0].set_xlabel("Longitude (°E)")
    axes[0].set_ylabel("Latitude (°N)")
    plt.colorbar(im0, ax=axes[0], label="Temperature (K)")

    # Temperature at mid-depth (k=8, ~40 m)
    temp_m = temp[8, :, :]
    im1 = axes[1].pcolormesh(lon_nc, lat_nc, temp_m, cmap="RdBu_r", vmin=270, vmax=300)
    axes[1].set_title("Temperature at 40 m (K) — Day 00")
    axes[1].set_xlabel("Longitude (°E)")
    axes[1].set_ylabel("Latitude (°N)")
    plt.colorbar(im1, ax=axes[1], label="Temperature (K)")

    # KT1 from model output (transpose mask to match NC output (y,x) = (105,133))
    mask_yx = mask.T  # (133,105) -> (105,133) to match output (y,x)
    kt1_plot = np.where(mask_yx == 0, np.nan, kt1_nc)
    im2 = axes[2].pcolormesh(lon_nc, lat_nc, kt1_plot, cmap="viridis", vmin=1, vmax=18)
    axes[2].set_title("KT1 (water column levels) — Day 00")
    axes[2].set_xlabel("Longitude (°E)")
    axes[2].set_ylabel("Latitude (°N)")
    plt.colorbar(im2, ax=axes[2], label="KT1")

    for ax in axes:
        ax.set_aspect("equal")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "05_day00_temp_salt.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("=" * 60)
    print("Stage 7.6B: Diagnostic Plots & ERA5 Mismatch Analysis")
    print("=" * 60)

    lat, lon, depth, mask = load_grid()
    kt1 = compute_kt1(depth, mask)
    lat_nc, lon_nc, temp, salt, kt1_nc = load_day00()

    print("\n--- Generating plots ---")
    plot_depth_bathymetry(lat, lon, depth, mask)
    plot_land_mask(mask, kt1)
    plot_coordinates(lat, lon)
    mismatch = plot_era5_mismatch(lat, lon, mask)
    plot_day00_temp_salt(lat_nc, lon_nc, temp, salt, kt1_nc, mask)

    print("\n--- Summary ---")
    print(f"  Output directory: {OUT_DIR}")
    print(f"  Plots generated: 5")
    print(f"  ERA5 mismatch: {mismatch['outside_pct']:.1f}% of wet cells outside ERA5")

    return 0


if __name__ == "__main__":
    sys.exit(main())
