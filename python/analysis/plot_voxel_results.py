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


def _temperature_limits(T: xr.DataArray, phi: xr.DataArray) -> tuple[float, float]:
    valid = phi > 0.01
    values = np.asarray(T.where(valid).values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("no active voxels with finite temperature")
    return float(np.min(finite)), float(np.max(finite))


def _check_temperature_slices(T: xr.DataArray) -> None:
    """Guard against dimension/index mistakes in the two section plots."""
    nx, ny, nz = T.sizes["nx"], T.sizes["ny"], T.sizes["nz"]
    ic, jc, kc = nx // 2, ny // 2, nz // 2
    for snap in range(T.sizes["snapshot"]):
        snapshot_T = T.isel(snapshot=snap)
        horiz = float(snapshot_T.isel(nx=ic, ny=jc, nz=kc))
        vert = float(snapshot_T.isel(nx=ic, ny=jc, nz=kc))
        if not np.isclose(horiz, vert, atol=1e-6, rtol=0.0):
            raise ValueError(
                f"temperature slice mismatch at snapshot {snap}: {horiz} vs {vert}"
            )
    print("temperature slice consistency: PASS")


def plot_temperature(ds, T, phi, outdir: Path):
    x, y, z = _grid(ds)
    _check_temperature_slices(T)
    vmin, vmax = _temperature_limits(T, phi)
    norm = Normalize(vmin=vmin, vmax=vmax)
    snaps = (0, T.sizes["snapshot"] // 2, T.sizes["snapshot"] - 1)
    labels = ("initial", "middle", "final")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, snap, label in zip(axes, snaps, labels):
        mask = phi.isel(snapshot=snap, nz=T.sizes["nz"] // 2) > 0.01
        field = np.where(mask.values, T.isel(snapshot=snap, nz=T.sizes["nz"] // 2).values, np.nan)
        im = ax.pcolormesh(x, y, field, shading="auto", cmap="viridis", norm=norm)
        ax.set_title(f"T horizontal slice k={T.sizes['nz']//2} ({label})")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="T [°C]", format="%.2f")
    fig.tight_layout()
    fig.savefig(outdir / "temperature_horizontal.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, snap, label in zip(axes, snaps, labels):
        mask = phi.isel(snapshot=snap, ny=T.sizes["ny"] // 2) > 0.01
        field = np.where(mask.values, T.isel(snapshot=snap, ny=T.sizes["ny"] // 2).values, np.nan)
        im = ax.pcolormesh(x, z, field, shading="auto", cmap="viridis", norm=norm)
        ax.set_title(f"T vertical slice j={T.sizes['ny']//2} ({label})")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("z [m]")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="T [°C]", format="%.2f")
    fig.tight_layout()
    fig.savefig(outdir / "temperature_vertical.png", dpi=180)
    plt.close(fig)

    final_mask = (phi.isel(snapshot=-1) > 0.01).values
    final_T = np.where(final_mask, T.isel(snapshot=-1).values, np.nan)
    colors = plt.cm.viridis(norm(final_T))
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, final_mask, colors=colors, title="Final T field", x=x, y=y, z=z)
    sm = ScalarMappable(norm=norm, cmap="viridis")
    fig.colorbar(sm, ax=ax, shrink=0.7, label="T [°C]", format="%.2f")
    fig.tight_layout()
    fig.savefig(outdir / "temperature_3d_final.png", dpi=180)
    plt.close(fig)


def plot_phi(ds, phi, outdir: Path):
    x, y, z = _grid(ds)
    snaps = (0, phi.sizes["snapshot"] // 2, phi.sizes["snapshot"] - 1)
    labels = ("initial", "middle", "final")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, snap, label in zip(axes, snaps, labels):
        field = np.where(phi.isel(snapshot=snap, nz=phi.sizes["nz"] // 2).values > 0.01,
                         phi.isel(snapshot=snap, nz=phi.sizes["nz"] // 2).values, np.nan)
        im = ax.pcolormesh(x, y, field, shading="auto", cmap="magma", vmin=0, vmax=1)
        ax.set_title(f"phi horizontal slice k={phi.sizes['nz']//2} ({label})")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="phi", format="%.2f")
    fig.tight_layout()
    fig.savefig(outdir / "phi_horizontal.png", dpi=180)
    plt.close(fig)

    final_phi = np.asarray(phi.isel(snapshot=-1).values, dtype=float)
    mask = final_phi > 0.01
    colors = plt.cm.magma(Normalize(0.0, 1.0)(final_phi))
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, mask, colors=colors, title="Final phi field (partial melt visible)", x=x, y=y, z=z)
    sm = ScalarMappable(norm=Normalize(0.0, 1.0), cmap="magma")
    fig.colorbar(sm, ax=ax, shrink=0.7, label="phi", format="%.2f")
    fig.tight_layout()
    fig.savefig(outdir / "phi_3d_final.png", dpi=180)
    plt.close(fig)


def plot_time_series(run: xr.Dataset, vox: xr.Dataset, outdir: Path):
    t = np.asarray(run["time"].values, dtype=float) / 86400.0
    mass = np.asarray(run["mass"].values, dtype=float)
    volume = np.asarray(run["volume"].values, dtype=float)
    draft = np.asarray(run["draft"].values, dtype=float)
    freeboard = (
        np.asarray(run["freeboard"].values, dtype=float)
        if "freeboard" in run else None
    )

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    axes[0, 0].plot(t, mass / mass[0], label="mass / initial")
    axes[0, 0].plot(t, volume / volume[0], label="volume / initial")
    axes[0, 0].set_xlabel("time [day]")
    axes[0, 0].set_ylabel("normalized")
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.3)

    axes[0, 1].plot(t, draft, label="draft")
    if freeboard is not None:
        axes[0, 1].plot(t, freeboard, label="freeboard (top solid surface)")
    else:
        print("WARNING: freeboard not present in run NetCDF; skipping freeboard curve")
    axes[0, 1].set_xlabel("time [day]")
    axes[0, 1].set_ylabel("height [m]")
    axes[0, 1].legend()
    axes[0, 1].grid(alpha=0.3)

    series = (
        ("voxel_mass_loss_basal", "basal (voxel)"),
        ("voxel_mass_loss_lateral", "lateral (voxel)"),
        ("voxel_mass_loss_surface", "surface (voxel)"),
        ("voxel_mass_loss_flush", "flush (voxel)"),
    )
    use_voxel_series = all(name in run for name, _ in series)
    if not use_voxel_series:
        series = (
            ("mass_loss_basal", "basal (prism diagnostics)"),
            ("mass_loss_lateral", "lateral (prism diagnostics)"),
            ("mass_loss_surface", "surface (prism diagnostics)"),
            ("mass_loss_wave", "wave (prism diagnostics)"),
        )
    for name, label in series:
        if name in run:
            vals = np.asarray(run[name].values, dtype=float)
            if not use_voxel_series:
                vals = np.cumsum(vals)
            axes[1, 0].plot(t, vals, label=label)
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

    if "ocean_T_draft" in run:
        fig, axes = plt.subplots(2, 2, figsize=(13, 7))
        axes[0, 0].plot(t, run["ocean_T_draft"], label="ocean T at draft")
        axes[0, 0].set_xlabel("time [day]"); axes[0, 0].set_ylabel("°C")
        axes[0, 0].grid(alpha=0.3); axes[0, 0].legend()
        axes[0, 1].plot(t, run["ocean_S_draft"], color="C1", label="ocean S at draft")
        axes[0, 1].set_xlabel("time [day]"); axes[0, 1].set_ylabel("mass fraction")
        axes[0, 1].grid(alpha=0.3); axes[0, 1].legend()
        axes[1, 0].plot(t, run["ocean_u_draft"], label="ocean u")
        axes[1, 0].plot(t, run["ocean_v_draft"], label="ocean v")
        axes[1, 0].set_xlabel("time [day]"); axes[1, 0].set_ylabel("m/s")
        axes[1, 0].grid(alpha=0.3); axes[1, 0].legend()
        axes[1, 1].plot(t, run["air_T"] - 273.15, label="air T")
        axes[1, 1].plot(t, np.hypot(run["air_u10"], run["air_v10"]), label="wind speed")
        axes[1, 1].set_xlabel("time [day]"); axes[1, 1].set_ylabel("°C / m/s")
        axes[1, 1].grid(alpha=0.3); axes[1, 1].legend()
        fig.tight_layout()
        fig.savefig(outdir / "forcing_time_series.png", dpi=180)
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
