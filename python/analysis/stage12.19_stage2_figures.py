#!/usr/bin/env python3
"""Stage 12.19 Stage 2 diagnostic/thesis figures.

Rows are the three representative fixed-geometry cases:
FJL1 2020, FJL2 2020, FJL2 2024 (50^3, 50 m, N=6 h).  The 3x5 matrix shows
the whole phi field, without cut-aways.  Profiles use ice-weighted means for T
and the horizontal mean for phi; T(x) is the phi-weighted mean over y,z.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm, colors
import numpy as np
import pandas as pd
import xarray as xr
from PIL import Image
from scipy.ndimage import binary_erosion, generate_binary_structure, label

RHO_ICE = 916.7
R_EARTH = 6371000.0
CASES = [
    ("FJL1_2020", "FJL1 2020", "data/validation/stage12.19/FJL1_2020_fixed_N6"),
    ("FJL2_2020", "FJL2 2020", "data/validation/stage12.19/FJL2_2020_fixed_N6"),
    ("FJL2_2024", "FJL2 2024", "data/validation/stage12.19/FJL2_2024_fixed_N6"),
]
DAYS = (0, 90, 180, 270, 350)
STRUCT = generate_binary_structure(3, 1)


def block_mean(a, target):
    a = np.asarray(a, float)
    f = [max(1, int(np.ceil(n / target))) for n in a.shape]
    pad = [(-n) % f[i] for i, n in enumerate(a.shape)]
    if any(pad):
        a = np.pad(a, ((0, pad[0]), (0, pad[1]), (0, pad[2])), mode="constant")
    nz, ny, nx = a.shape
    return a.reshape(nz // f[0], f[0], ny // f[1], f[1], nx // f[2], f[2]).mean(axis=(1, 3, 5))


def downsample(phi, T, target):
    ph = block_mean(phi, target)
    num = block_mean(np.asarray(T, float) * np.asarray(phi, float), target)
    return ph, num / np.maximum(ph, 1.0e-6)


def snapshots(run_dir):
    return sorted(Path(run_dir).glob("run.nc_snap_*.nc"))


def snapshot_day(f):
    with xr.open_dataset(f) as ds:
        return float(ds.time.values[0]) / 86400.0


def nearest(files, day):
    return min(files, key=lambda f: abs(snapshot_day(f) - day))


def load(f, target=None):
    with xr.open_dataset(f) as ds:
        phi = np.asarray(ds.phi.values, float)
        T = np.asarray(ds.T.values, float)
        x = np.asarray(ds.x.values, float); y = np.asarray(ds.y.values, float); z = np.asarray(ds.z.values, float)
        t = float(ds.time.values[0])
        mass = float(ds.mass.values[0]) if "mass" in ds else np.nan
    if target:
        phi, T = downsample(phi, T, target)
    return phi, T, x, y, z, t, mass


def set_axes(ax, nx, ny, nz, extent=50.0):
    ax.set_xlim(0, nx); ax.set_ylim(0, ny); ax.set_zlim(0, nz)
    ax.set_xticks([0, nx / 2, nx]); ax.set_yticks([0, ny / 2, ny]); ax.set_zticks([0, nz / 2, nz])
    ax.set_xticklabels([0, f"{extent/2:.0f}", f"{extent:.0f}"])
    ax.set_yticklabels([0, f"{extent/2:.0f}", f"{extent:.0f}"])
    ax.set_zticklabels([0, f"{extent/2:.0f}", f"{extent:.0f}"])
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(22, -60)


def matrix(out, target=32):
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 6, width_ratios=[1, 1, 1, 1, 1, .06], wspace=.04, hspace=.16)
    norm = colors.Normalize(0, 1)
    for i, (tag, label, run) in enumerate(CASES):
        files = snapshots(run)
        mass0 = None
        with xr.open_dataset(Path(run) / "run.nc") as ds:
            mass0 = float(ds.mass.values[0])
        for j, day in enumerate(DAYS):
            ax = fig.add_subplot(gs[i, j], projection="3d")
            f = nearest(files, day)
            phi, T, x, y, z, t, mass = load(f, target=target)
            pht = phi.transpose(2, 1, 0)
            nz, ny, nx = pht.shape
            ax.voxels(pht > .25, facecolors=cm.Blues(norm(pht)), edgecolor="none")
            set_axes(ax, nx, ny, nz)
            pct = 100 * mass / mass0 if mass0 else np.nan
            if i == 0:
                ax.set_title(f"day {int(round(t/86400))}", fontsize=9)
            ax.text2D(.02, .90, f"{pct:.1f}%", transform=ax.transAxes, fontsize=8)
    cax = fig.add_subplot(gs[:, 5])
    cb = fig.colorbar(cm.ScalarMappable(norm=norm, cmap="Blues"), cax=cax)
    cb.set_label(r"ice volume fraction $\phi$")
    fig.suptitle("Stage 12.19 fixed-geometry cases: whole-model ice volume fraction", fontsize=15)
    fig.subplots_adjust(left=.08, right=.94, top=.92, bottom=.04)
    fig.canvas.draw()
    for i, (_, label, _) in enumerate(CASES):
        b = fig.axes[i * len(DAYS)].get_position()
        fig.text(.022, (b.y0 + b.y1) / 2, label, rotation=90, va="center", fontsize=13)
    fig.savefig(out, dpi=220, bbox_inches="tight"); plt.close(fig)
    print(out)


def profiles(tag, label, run, out):
    files = snapshots(run)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    colors_ = plt.cm.viridis(np.linspace(.05, .95, len(DAYS)))
    for c, day in zip(colors_, DAYS):
        phi, T, x, y, z, t, mass = load(nearest(files, day))
        solid = phi > .01
        tz = np.array([np.nanmean(T[k][solid[k]]) if solid[k].any() else np.nan for k in range(phi.shape[0])])
        pz = phi.mean(axis=(1, 2))
        zb = np.sum(z[:, None, None] * phi) / max(phi.sum(), 1e-6)
        kz = int(np.argmin(np.abs(z - zb)))
        col = phi[kz].sum(axis=0)
        tx = (T[kz] * phi[kz]).sum(axis=0) / np.maximum(col, 1e-6)
        tx[col <= 1e-8] = np.nan
        lab = f"day {int(round(t/86400))}"
        axes[0].plot(tz, z, color=c, label=lab)
        axes[1].plot(pz, z, color=c, label=lab)
        axes[2].plot(x, tx, color=c, label=f"{lab}, z={z[kz]:.1f} m")
    axes[0].set_xlabel("T [°C]"); axes[0].set_ylabel("z [m]"); axes[0].set_title("T(z), ice mean")
    axes[1].set_xlabel(r"$\phi$"); axes[1].set_ylabel("z [m]"); axes[1].set_title(r"$\phi(z)$, horizontal mean")
    axes[2].set_xlabel("x [m]"); axes[2].set_ylabel("T [°C]"); axes[2].set_title("T(x), y-mean at mid-ice z")
    for a in axes:
        a.grid(alpha=.25); a.legend(fontsize=7)
    fig.suptitle(f"{label}: vertical and horizontal profiles"); fig.tight_layout()
    fig.savefig(out, dpi=220, bbox_inches="tight"); plt.close(fig)
    print(out)


def daily_table(run):
    with xr.open_dataset(Path(run) / "run.nc") as ds:
        t = np.asarray(ds.time.values, float) / 86400.
        day = np.floor(t + 1e-9).astype(int)
        last = np.r_[np.where(np.diff(day))[0], len(day) - 1]
        rec = {"day": t[last], "mass": ds.mass.values[last], "draft": ds.draft.values[last],
               "freeboard": ds.freeboard.values[last], "grounded": ds.grounded.values[last],
               "lat": ds.latitude.values[last], "lon": ds.longitude.values[last],
               "T_w": ds.ocean_T_draft.values[last], "S_w": ds.ocean_S_draft.values[last]}
        for v in ("voxel_mass_loss_basal", "voxel_mass_loss_lateral", "voxel_mass_loss_surface",
                  "voxel_mass_loss_flush", "calved_mass"):
            rec[v] = ds[v].values[last]
    df = pd.DataFrame(rec)
    df["melt"] = df.voxel_mass_loss_basal + df.voxel_mass_loss_lateral + df.voxel_mass_loss_surface
    df["loss"] = df.mass.iloc[0] - df.mass
    df["residual"] = df.loss - (df["melt"] + df.voxel_mass_loss_flush + df.calved_mass)
    return df


def geom_from_snapshots(run):
    rows = []
    for f in snapshots(run):
        phi, T, x, y, z, t, mass = load(f)
        solid = phi > .01
        lab, n = label(solid, structure=STRUCT)
        if n:
            counts = np.bincount(lab.ravel()); counts[0] = 0
            c = int(counts.argmax()); m = lab == c
            ks = np.where(m.any(axis=(1, 2)))[0]; js = np.where(m.any(axis=(0, 2)))[0]
            rows.append((t / 86400., (js.max() - js.min() + 1) * (x[1] - x[0]),
                         (ks.max() - ks.min() + 1) * (z[1] - z[0])))
        else:
            rows.append((t / 86400., 0., 0.))
    return np.array(rows)


def shade_grounded(ax, t, g):
    g = np.asarray(g).astype(int)
    starts = np.where((g == 1) & np.r_[True, g[:-1] == 0])[0]
    ends = np.where((g == 1) & np.r_[g[1:] == 0, True])[0]
    for a, b in zip(starts, ends):
        ax.axvspan(t[a], t[b], color="0.5", alpha=.16, lw=0)


def series(tag, label, run, out, static):
    df = daily_table(run)
    geo = geom_from_snapshots(run)
    m0 = float(df.mass.iloc[0])
    t = df.day.values
    cal = pd.read_csv(Path(run) / "run.nc_calved.csv") if (Path(run) / "run.nc_calved.csv").exists() else pd.DataFrame()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    ax = axes[0, 0]
    ax.plot(t, 100 * df.loss / m0, "k-", label="total loss")
    ax.set_ylabel("% of initial mass"); ax.set_title("Mass loss")
    ax.legend(fontsize=8); ax.grid(alpha=.25)
    shade_grounded(ax, t, df.grounded.values)
    # track inset
    ins = ax.inset_axes([.56, .56, .41, .41])
    for i in range(1, len(df)):
        dash = "--" if (df.grounded.iloc[i] or df.grounded.iloc[i - 1]) else "-"
        ins.plot(df.lon.iloc[i - 1:i + 1], df.lat.iloc[i - 1:i + 1], "k", lw=.6, ls=dash)
    ins.scatter(df.lon.iloc[0], df.lat.iloc[0], marker="*", c="r", s=40, zorder=3)
    ins.scatter(df.lon.iloc[-1], df.lat.iloc[-1], marker="X", c="k", s=25, zorder=3)
    ins.set_title("track (inset)", fontsize=7); ins.tick_params(labelsize=6); ins.grid(alpha=.2)

    ax = axes[0, 1]
    ax.plot(t, df.draft, label="draft", color="C0")
    ax.plot(t, df.freeboard, label="freeboard", color="C1")
    ax.set_ylabel("m"); ax.set_title("Geometry"); ax.legend(fontsize=8); ax.grid(alpha=.25)
    shade_grounded(ax, t, df.grounded.values)
    gd = geo[:, 0]
    ax.step(gd, geo[:, 1], where="post", color="C2", ls="--", label="main width")
    ax.step(gd, geo[:, 2], where="post", color="C3", ls=":", label="main height")
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ax.plot(t, df["melt"] / m0 * 100, label="basal+lateral+surface")
    ax.plot(t, df.voxel_mass_loss_flush / m0 * 100, label="flush")
    ax.plot(t, df.calved_mass / m0 * 100, label="calved")
    ax.plot(t, df.loss / m0 * 100, "k--", label="total")
    ax.plot(t, df.residual / m0 * 100, "r-", lw=.8, label="residual")
    for k, r in cal.iterrows():
        ax.axvline(r.time_s / 86400., color="k", ls=":", lw=.8)
        ax.annotate(f"{r.mass_kg/1e6:.2f} Mt", (r.time_s / 86400., ax.get_ylim()[1]),
                    xytext=(2, -10), textcoords="offset points", fontsize=7, rotation=90, va="top")
    ax.set_ylabel("% of initial mass"); ax.set_title("Mass-loss components")
    ax.legend(fontsize=7); ax.grid(alpha=.25); shade_grounded(ax, t, df.grounded.values)

    ax = axes[1, 1]
    ax.plot(t, df.T_w, color="C3", label="T at draft")
    ax.set_ylabel("T [°C]", color="C3"); ax.tick_params(axis="y", colors="C3")
    ax.set_title("Water at draft"); ax.grid(alpha=.25)
    ax2 = ax.twinx()
    ax2.plot(t, df.S_w * 1000, color="C0", label="S at draft")
    ax2.set_ylabel("S [g/kg]", color="C0"); ax2.tick_params(axis="y", colors="C0")
    shade_grounded(ax, t, df.grounded.values)
    for a in axes.ravel():
        a.set_xlabel("day")
    fig.suptitle(f"{label}: fixed-geometry run summary"); fig.tight_layout()
    fig.savefig(out, dpi=220, bbox_inches="tight"); plt.close(fig)
    print(out)


def balance(tag, label, run, out):
    df = daily_table(run); m0 = float(df.mass.iloc[0]); t = df.day.values
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(t, df["melt"] / m0 * 100, label="basal+lateral+surface")
    ax.plot(t, df.voxel_mass_loss_flush / m0 * 100, label="flush")
    ax.plot(t, df.calved_mass / m0 * 100, label="calved")
    ax.plot(t, df.loss / m0 * 100, "k--", label="total loss")
    ax.plot(t, df.residual / m0 * 100, "r-", lw=.8, label="residual")
    ax.set_xlabel("day"); ax.set_ylabel("% of initial mass"); ax.grid(alpha=.25)
    ax.set_title(f"{label}: mass balance"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out, dpi=220); plt.close(fig)
    print(out)


def gif(tag, label, run, prefix, target=24):
    files = snapshots(run); frames_phi, frames_T = [], []
    tmp = Path("/tmp/opencode/stage12.19_frames"); tmp.mkdir(parents=True, exist_ok=True)
    with xr.open_dataset(Path(run) / "run.nc") as ds:
        m0 = float(ds.mass.values[0])
    for f in files:
        phi, T, x, y, z, t, mass = load(f, target=target)
        pht = phi.transpose(2, 1, 0); Tt = T.transpose(2, 1, 0); nz, ny, nx = pht.shape
        day = int(round(t / 86400.)); pct = 100 * mass / m0
        fig = plt.figure(figsize=(4.8, 4.4)); ax = fig.add_subplot(111, projection="3d")
        ax.voxels(pht > .25, facecolors=cm.Blues(.25 + .75 * pht), edgecolor="none")
        set_axes(ax, nx, ny, nz); ax.set_title(f"phi  day {day}  mass {pct:.1f}%", fontsize=9)
        fig.subplots_adjust(left=.02, right=.98, bottom=.02, top=.90)
        fn = tmp / f"_{tag}_phi_{day:03d}.png"
        fig.savefig(fn, dpi=110); plt.close(fig)
        frames_phi.append(Image.open(fn).convert("P", palette=Image.ADAPTIVE))
        solid = pht > .05
        surface = solid & ~binary_erosion(solid, structure=STRUCT, border_value=0)
        fig = plt.figure(figsize=(4.8, 4.4)); ax = fig.add_subplot(111, projection="3d")
        ax.voxels(surface, facecolors=cm.YlOrRd(colors.Normalize(-10, 0)(Tt)), edgecolor="none")
        set_axes(ax, nx, ny, nz); ax.set_title(f"T  day {day}  mass {pct:.1f}%", fontsize=9)
        fig.subplots_adjust(left=.02, right=.98, bottom=.02, top=.90)
        fn = tmp / f"_{tag}_T_{day:03d}.png"; fig.savefig(fn, dpi=110); plt.close(fig)
        frames_T.append(Image.open(fn).convert("P", palette=Image.ADAPTIVE))
    for frames, suffix in ((frames_phi, "phi"), (frames_T, "T")):
        if frames:
            frames[0].save(str(prefix) + f"_{suffix}.gif", save_all=True, append_images=frames[1:],
                           duration=80, loop=0, optimize=True)
    print(prefix)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fig-dir", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.19"))
    p.add_argument("--static", type=Path, default=Path("data/input/static/glorys_static_barents.nc"))
    a = p.parse_args(); a.fig_dir.mkdir(parents=True, exist_ok=True)
    matrix(a.fig_dir / "stage2_matrix_phi.png")
    for tag, label, run in CASES:
        d = a.fig_dir / tag
        d.mkdir(parents=True, exist_ok=True)
        profiles(tag, label, run, d / "profiles.png")
        series(tag, label, run, d / "time_series.png", a.static)
        balance(tag, label, run, d / "mass_balance.png")
        gif(tag, label, run, d / "evolution")
    print("done")


if __name__ == "__main__":
    main()
