#!/usr/bin/env python3
"""Plot reproducible diagnostics from iceberg_run + voxel NetCDF output.

Usage:
    python python/analysis/plot_voxel_results.py RUN.nc VOXEL.nc --outdir DIR

The script only reads saved results; it does not rerun the model.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import numpy as np
import xarray as xr


def _slices(ds: xr.Dataset):
    """Return T/phi with dimensions (snapshot, nx, ny, nz)."""
    for name in ("T", "phi"):
        if name not in ds:
            raise KeyError(f"missing {name!r} in {ds.encoding.get('source', 'voxel file')}")
    T = ds["T"].transpose("snapshot", "nx", "ny", "nz")
    phi = ds["phi"].transpose("snapshot", "nx", "ny", "nz")
    return T, phi


def _grid(ds: xr.Dataset):
    return (
        np.asarray(ds["x"].values, dtype=float),
        np.asarray(ds["y"].values, dtype=float),
        np.asarray(ds["z"].values, dtype=float),
    )


def _voxel_axes(ax, mask, colors=None, title="", x=None, y=None, z=None):
    ax.voxels(mask, facecolors=colors, edgecolor="k", linewidth=0.2)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_zlabel("z [m]")
    ax.set_title(title)
    ax.set_box_aspect(np.array(mask.shape))
    for axis, coords in ((ax.set_xticks, x), (ax.set_yticks, y), (ax.set_zticks, z)):
        if coords is None or len(coords) < 2:
            continue
        step = float(coords[1] - coords[0])
        n = len(coords)
        pos = sorted({0, n // 2, n})
        labels = [f"{coords[0] - step / 2 + p * step:.0f}" for p in pos]
        axis(pos)
        # labels are assigned by the caller below; matplotlib's 3D labels need a separate call
    if x is not None and len(x) > 1:
        step = float(x[1] - x[0]); n = len(x); pos = sorted({0, n // 2, n})
        ax.set_xticks(pos); ax.set_xticklabels([f"{x[0]-step/2+p*step:.0f}" for p in pos])
    if y is not None and len(y) > 1:
        step = float(y[1] - y[0]); n = len(y); pos = sorted({0, n // 2, n})
        ax.set_yticks(pos); ax.set_yticklabels([f"{y[0]-step/2+p*step:.0f}" for p in pos])
    if z is not None and len(z) > 1:
        step = float(z[1] - z[0]); n = len(z); pos = sorted({0, n // 2, n})
        ax.set_zticks(pos); ax.set_zticklabels([f"{z[0]-step/2+p*step:.0f}" for p in pos])


def plot_shape(ds, T, phi, outdir: Path):
    x, y, z = _grid(ds)
    mask = np.asarray(phi.isel(snapshot=-1).values > 0.01)
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, mask, title="Final iceberg shape (phi > 0.01)", x=x, y=y, z=z)
    fig.tight_layout()
    fig.savefig(outdir / "voxel_shape_final.png", dpi=180)
    plt.close(fig)


def plot_temperature(ds, T, phi, outdir: Path):
    x, y, z = _grid(ds)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, snap, label in zip(
        axes,
        (0, T.sizes["snapshot"] // 2, T.sizes["snapshot"] - 1),
        ("initial", "middle", "final"),
    ):
        field = np.asarray(T.isel(snapshot=snap, nz=T.sizes["nz"] // 2).values)
        im = ax.pcolormesh(x, y, field, shading="auto", cmap="viridis")
        ax.set_title(f"T horizontal slice ({label})")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="T [°C]")
    fig.tight_layout()
    fig.savefig(outdir / "temperature_horizontal.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, snap, label in zip(
        axes,
        (0, T.sizes["snapshot"] // 2, T.sizes["snapshot"] - 1),
        ("initial", "middle", "final"),
    ):
        field = np.asarray(T.isel(snapshot=snap, ny=T.sizes["ny"] // 2).values)
        im = ax.pcolormesh(x, z, field, shading="auto", cmap="viridis")
        ax.set_title(f"T vertical slice ({label})")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("z [m]")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="T [°C]")
    fig.tight_layout()
    fig.savefig(outdir / "temperature_vertical.png", dpi=180)
    plt.close(fig)

    # 3D temperature distribution on the final solid voxels.
    final_T = np.asarray(T.isel(snapshot=-1).values)
    mask = np.asarray(phi.isel(snapshot=-1).values > 0.01)
    norm = Normalize(vmin=float(np.nanmin(final_T[mask])), vmax=0.0)
    colors = plt.cm.viridis(norm(final_T))
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, mask, colors=colors, title="Final T field", x=x, y=y, z=z)
    sm = ScalarMappable(norm=norm, cmap="viridis")
    fig.colorbar(sm, ax=ax, shrink=0.7, label="T [°C]")
    fig.tight_layout()
    fig.savefig(outdir / "temperature_3d_final.png", dpi=180)
    plt.close(fig)


def plot_phi(ds, phi, outdir: Path):
    x, y, z = _grid(ds)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, snap, label in zip(
        axes,
        (0, phi.sizes["snapshot"] // 2, phi.sizes["snapshot"] - 1),
        ("initial", "middle", "final"),
    ):
        field = np.asarray(phi.isel(snapshot=snap, nz=phi.sizes["nz"] // 2).values)
        im = ax.pcolormesh(x, y, field, shading="auto", cmap="magma", vmin=0, vmax=1)
        ax.set_title(f"phi horizontal slice ({label})")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="phi")
    fig.tight_layout()
    fig.savefig(outdir / "phi_horizontal.png", dpi=180)
    plt.close(fig)

    final_phi = np.asarray(phi.isel(snapshot=-1).values)
    mask = final_phi > 0.01
    colors = plt.cm.magma(Normalize(0.0, 1.0)(final_phi))
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, mask, colors=colors, title="Final phi field", x=x, y=y, z=z)
    sm = ScalarMappable(norm=Normalize(0.0, 1.0), cmap="magma")
    fig.colorbar(sm, ax=ax, shrink=0.7, label="phi")
    fig.tight_layout()
    fig.savefig(outdir / "phi_3d_final.png", dpi=180)
    plt.close(fig)


def plot_time_series(run: xr.Dataset, vox: xr.Dataset, outdir: Path):
    t = np.asarray(run["time"].values, dtype=float) / 86400.0
    mass = np.asarray(run["mass"].values, dtype=float)
    volume = np.asarray(run["volume"].values, dtype=float)
    draft = np.asarray(run["draft"].values, dtype=float)
    z = np.asarray(vox["z"].values, dtype=float) if "z" in vox else None

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    axes[0, 0].plot(t, mass / mass[0], label="mass / initial")
    axes[0, 0].plot(t, volume / volume[0], label="volume / initial")
    axes[0, 0].set_xlabel("time [day]")
    axes[0, 0].set_ylabel("normalized")
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.3)

    freeboard = None
    if z is not None and len(z) > 1:
        height = float(z[-1] - z[0] + (z[1] - z[0]))
        freeboard = height - draft
    axes[0, 1].plot(t, draft, label="draft")
    if freeboard is not None:
        axes[0, 1].plot(t, freeboard, label="freeboard")
    axes[0, 1].set_xlabel("time [day]")
    axes[0, 1].set_ylabel("height [m]")
    axes[0, 1].legend()
    axes[0, 1].grid(alpha=0.3)

    for name, label in (
        ("mass_loss_basal", "basal"),
        ("mass_loss_lateral", "lateral"),
        ("mass_loss_surface", "surface"),
        ("mass_loss_wave", "wave"),
    ):
        if name in run:
            vals = np.asarray(run[name].values, dtype=float)
            axes[1, 0].plot(t, np.cumsum(vals), label=label)
    axes[1, 0].set_xlabel("time [day]")
    axes[1, 0].set_ylabel("cumulative mass loss [kg]")
    axes[1, 0].legend()
    axes[1, 0].grid(alpha=0.3)

    if "sensible_energy" in run:
        axes[1, 1].plot(t, np.asarray(run["sensible_energy"].values, dtype=float)/1e9,
                        label="sensible heat content [GJ]")
    if "flushed_energy" in run:
        axes[1, 1].plot(t, np.asarray(run["flushed_energy"].values, dtype=float)/1e9,
                        label="flushed energy [GJ]")
    axes[1, 1].set_xlabel("time [day]")
    axes[1, 1].set_ylabel("energy [GJ]")
    axes[1, 1].legend()
    axes[1, 1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "time_series.png", dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_nc")
    parser.add_argument("voxel_nc")
    parser.add_argument("--outdir", default="voxel_plots")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    run = xr.open_dataset(args.run_nc)
    vox = xr.open_dataset(args.voxel_nc)
    try:
        T, phi = _slices(vox)
        plot_shape(vox, T, phi, outdir)
        plot_temperature(vox, T, phi, outdir)
        plot_phi(vox, phi, outdir)
        plot_time_series(run, vox, outdir)
    finally:
        run.close()
        vox.close()
    print(f"wrote plots to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
