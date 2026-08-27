#!/usr/bin/env python3
"""Diagnostic figures for the Stage 7.7 realistic initial ocean state.

Reads data/input/processed/ocean/initial_ts_2020-01-01.nc and writes 10 PNGs
into data/output/diagnostics/stage7.7/figures/:

  01_surface_temperature.png      surface T (level 1, deg-C)
  02_surface_salinity.png         surface S (level 1, mass fraction)
  03_surface_density.png          surface density anomaly (g/cm3)
  04_deep_temperature.png         deep T (level 18, deg-C)
  05_deep_salinity.png            deep S (level 18)
  06_vertical_profiles.png        3 representative columns
  07_ts_diagram.png               T-S diagram (colored by depth level)
  08_diff_surface_t_vs_synthetic.png   surface T minus synthetic-T (deg-C)
  09_diff_surface_s_vs_synthetic.png   surface S minus synthetic-S
  10_regrid_flags.png             vertical interpolation flags (coverage audit)

Usage:
    python python/ocean/make_initial_ts_diagnostics.py [--proj-dir .]
"""

import argparse
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from build_initial_ts import eckart_ro, synthetic_baseline, Z_CM, Z_M  # noqa: E402


def _load():
    p = pathlib.Path("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    ds = xr.open_dataset(p)
    t = ds["temperature_celsius"].values
    s = ds["salinity_mass_fraction"].values
    ro = ds["density_anomaly_gcm3"].values
    flag = ds["regrid_flag"].values
    lat, lon = ds["lat"].values, ds["lon"].values
    kk1 = ds["water_column_levels"].values
    wet = ds["wet_mask"].values.astype(bool)
    ds.close()
    return t, s, ro, flag, lat, lon, kk1, wet


def _pcol(ax, z, vmin=None, vmax=None, cmap="viridis", title="", label=""):
    m = np.ma.masked_where(z == 0.0, z)
    pc = ax.pcolormesh(m, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel("j (x) index")
    ax.set_ylabel("i (y) index")
    ax.set_aspect("equal")
    cb = plt.colorbar(pc, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label(label)
    return pc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proj-dir", type=pathlib.Path, default=pathlib.Path("."))
    args = ap.parse_args()
    proj = args.proj_dir
    sys.path.insert(0, str(proj / "python" / "ocean"))
    sys.path.insert(0, str(proj / "python" / "ice"))

    t, s, ro, flag, lat, lon, kk1, wet = _load()
    is1, js1, ks = t.shape
    outdir = proj / "data/output/diagnostics/stage7.7/figures"
    outdir.mkdir(parents=True, exist_ok=True)

    lvl = np.arange(1, ks + 1)
    deep = min(ks - 1, 17)  # level 18

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    _pcol(
        axes[0],
        t[:, :, 0],
        vmin=-2.5,
        vmax=7.0,
        cmap="cividis",
        title="surface T (deg-C), level 1 (2.5 m)",
        label="deg-C",
    )
    _pcol(
        axes[1],
        s[:, :, 0],
        vmin=0.030,
        vmax=0.0375,
        cmap="YlGnBu",
        title="surface S (mass fraction), level 1",
        label="kg/kg",
    )
    _pcol(
        axes[2],
        ro[:, :, 0] * 1000.0,
        cmap="plasma",
        title="surface density anomaly (kg/m3), level 1",
        label="kg/m3",
    )
    fig.suptitle("Stage 7.7 realistic initial ocean - surface", y=1.02)
    fig.tight_layout()
    fig.savefig(outdir / "01_surface_temperature.png", bbox_inches="tight")
    fig.savefig(outdir / "02_surface_salinity.png", bbox_inches="tight")
    fig.savefig(outdir / "03_surface_density.png", bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    _pcol(
        axes[0],
        t[:, :, deep],
        vmin=-2.5,
        vmax=4.0,
        cmap="cividis",
        title=f"deep T (deg-C), level {deep+1} ({Z_M[deep]:g} m)",
        label="deg-C",
    )
    _pcol(
        axes[1],
        s[:, :, deep],
        vmin=0.034,
        vmax=0.0365,
        cmap="YlGnBu",
        title=f"deep S (mass fraction), level {deep+1}",
        label="kg/kg",
    )
    fig.suptitle("Stage 7.7 realistic initial ocean - deep", y=1.02)
    fig.tight_layout()
    fig.savefig(outdir / "04_deep_temperature.png", bbox_inches="tight")
    fig.savefig(outdir / "05_deep_salinity.png", bbox_inches="tight")
    plt.close(fig)

    # representative columns: Atlantic-inflow (west, deep), central basin,
    # cold shelf cell (near Svalbard-ish north), shallow coastal
    wh_t = np.argwhere(wet)
    cols = {
        "Atlantic inflow (SW)": (60, 85),
        "Central Barents": (60, 45),
        "Northern FJL shelf": (100, 55),
        "Shallow coast": (10, 10),
    }
    fig, ax = plt.subplots(1, 2, figsize=(12, 7))
    for i, j in cols.values():
        i, j = int(i), int(j)
        m = kk1[i, j]
        if m <= 1:
            m = 1
        zk = Z_M[:m]
        ax[0].plot(
            t[i, j, :m],
            zk,
            "o-",
            label=f"({i},{j}) lat={lat[i,j]:.2f} lon={lon[i,j]:.2f} kt1={m}",
        )
        ax[1].plot(s[i, j, :m], zk, "s-", label=f"({i},{j})")
    ax[0].invert_yaxis()
    ax[1].invert_yaxis()
    ax[0].set_xlabel("T (deg-C)")
    ax[0].set_ylabel("depth (m)")
    ax[1].set_xlabel("S (mass fraction)")
    ax[0].legend(fontsize=7)
    ax[1].legend(fontsize=7)
    fig.suptitle("Vertical profiles at representative columns", y=1.02)
    fig.tight_layout()
    fig.savefig(outdir / "06_vertical_profiles.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 7))
    m = wet[:, :, None] & (lvl[None, None, :] <= kk1[:, :, None])
    sc = ax.scatter(
        s[m],
        t[m],
        c=np.broadcast_to(Z_M[None, None, :], t.shape)[m],
        s=3,
        cmap="viridis",
    )
    ax.set_xlabel("salinity (mass fraction)")
    ax.set_ylabel("temperature (deg-C)")
    ax.set_title("T-S diagram of the realistic initial state")
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("depth (m)")
    fig.tight_layout()
    fig.savefig(outdir / "07_ts_diagram.png", bbox_inches="tight")
    plt.close(fig)

    t_syn, s_syn = synthetic_baseline(wet, kk1)
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    _pcol(
        axes[0],
        t[:, :, 0] - t_syn[:, :, 0],
        cmap="RdBu_r",
        vmin=-12,
        vmax=12,
        title="surface T diff vs synthetic (deg-C)",
        label="deg-C",
    )
    _pcol(
        axes[1],
        (s[:, :, 0] - s_syn[:, :, 0]) * 1e4,
        cmap="RdBu_r",
        vmin=-4.5,
        vmax=4.5,
        title="surface S diff vs synthetic (x1e-4)",
        label="x1e-4",
    )
    fig.suptitle("Realistic minus synthetic (init_ocean) initial state", y=1.02)
    fig.tight_layout()
    fig.savefig(outdir / "08_diff_surface_t_vs_synthetic.png", bbox_inches="tight")
    fig.savefig(outdir / "09_diff_surface_s_vs_synthetic.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5.5))
    _pcol(
        ax,
        flag[:, :, 0],
        cmap="tab10",
        vmin=-0.5,
        vmax=3.5,
        title="vertical regrid flags, level 1 (0=interp 1=top 2=deepest 3=land)",
        label="flag",
    )
    fig.tight_layout()
    fig.savefig(outdir / "10_regrid_flags.png", bbox_inches="tight")
    plt.close(fig)

    for p in sorted(outdir.glob("*.png")):
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
