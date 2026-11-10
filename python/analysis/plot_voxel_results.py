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
    """Return T/phi/S with dimensions (snapshot, nx, ny, nz)."""
    for name in ("T", "phi"):
        if name not in ds:
            raise KeyError(f"missing {name!r} in {ds.encoding.get('source', 'voxel file')}")
    T = ds["T"].transpose("snapshot", "nx", "ny", "nz")
    phi = ds["phi"].transpose("snapshot", "nx", "ny", "nz")
    S = ds["S_boundary"].transpose("snapshot", "nx", "ny", "nz") if "S_boundary" in ds else None
    return T, phi, S


def _grid(ds: xr.Dataset):
    return (
        np.asarray(ds["x"].values, dtype=float),
        np.asarray(ds["y"].values, dtype=float),
        np.asarray(ds["z"].values, dtype=float),
    )


def _downsample(a, max_dim=32):
    """Block-mean a 3D array for display; keeps partial phi fractions."""
    a = np.asarray(a, dtype=float)
    if max(a.shape) <= max_dim:
        return a
    factor = int(np.ceil(max(a.shape) / max_dim))
    for axis in range(3):
        n = a.shape[axis]
        m = n // factor
        if m == 0:
            return a
        cut = a.take(range(m * factor), axis=axis)
        shape = list(cut.shape)
        shape[axis:axis + 1] = [m, factor]
        a = np.nanmean(cut.reshape(shape), axis=axis + 1)
    return a


def _downsample_coord(c, max_dim=32):
    c = np.asarray(c, dtype=float)
    if len(c) <= max_dim:
        return c
    factor = int(np.ceil(len(c) / max_dim))
    m = len(c) // factor
    return c[:m * factor].reshape(m, factor).mean(axis=1)


def _cutaway(mask):
    """Remove one octant for a display cut-away; does not change data."""
    m = np.array(mask, copy=True)
    nx, ny, nz = m.shape
    m[:max(1, nx // 2), :max(1, ny // 2), :max(1, nz // 2)] = False
    return m


def _voxel_axes(ax, mask, colors=None, title="", x=None, y=None, z=None, edges=True, shade=True):
    ax.voxels(mask, facecolors=colors, edgecolor=("k" if edges else None),
              linewidth=(0.2 if edges else 0.0), shade=shade)
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
    raw_phi = np.asarray(phi.isel(snapshot=-1).values)
    phi_ds = _downsample(raw_phi)
    mask = phi_ds > 0.01
    xd = _downsample_coord(x, phi_ds.shape[0])
    yd = _downsample_coord(y, phi_ds.shape[1])
    zd = _downsample_coord(z, phi_ds.shape[2])
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, _cutaway(mask), title="Final iceberg shape (phi > 0.01; cut-away)", x=xd, y=yd, z=zd,
               edges=(raw_phi.shape[0] <= 32))
    if not mask.any():
        ax.set_title("MELT-OUT: zero active mass")
        ax.text2D(0.5, 0.5, "MELT-OUT\nzero active mass", ha="center", va="center")
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
        horiz = snapshot_T.isel(nz=kc)   # (nx, ny)
        vert = snapshot_T.isel(ny=jc)    # (nx, nz)
        if horiz.dims != ("nx", "ny") or vert.dims != ("nx", "nz"):
            raise ValueError(f"unexpected slice dimensions: {horiz.dims}, {vert.dims}")
        h_value = float(horiz.isel(nx=ic, ny=jc))
        v_value = float(vert.isel(nx=ic, nz=kc))
        original = float(snapshot_T.isel(nx=ic, ny=jc, nz=kc))
        if not (np.isclose(h_value, v_value, atol=1e-6, rtol=0.0) and
                np.isclose(h_value, original, atol=1e-6, rtol=0.0)):
            raise ValueError(
                f"temperature slice mismatch at snapshot {snap}: "
                f"horizontal={h_value}, vertical={v_value}, original={original}"
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
        im = ax.pcolormesh(x, y, field, shading="auto", cmap="YlOrRd", norm=norm)
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
        im = ax.pcolormesh(x, z, field, shading="auto", cmap="YlOrRd", norm=norm)
        ax.set_title(f"T vertical slice j={T.sizes['ny']//2} ({label})")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("z [m]")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="T [°C]", format="%.2f")
    fig.tight_layout()
    fig.savefig(outdir / "temperature_vertical.png", dpi=180)
    plt.close(fig)

    raw_T = np.asarray(T.isel(snapshot=-1).values)
    raw_phi = np.asarray(phi.isel(snapshot=-1).values)
    Tds = _downsample(raw_T); phids = _downsample(raw_phi)
    final_mask = phids > 0.01
    final_T = np.where(final_mask, Tds, np.nan)
    colors = plt.cm.YlOrRd(norm(final_T))
    xd = _downsample_coord(x, Tds.shape[0]); yd = _downsample_coord(y, Tds.shape[1]); zd = _downsample_coord(z, Tds.shape[2])
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, _cutaway(final_mask), colors=colors, title="Final T field (cut-away; shade=False)", x=xd, y=yd, z=zd,
               edges=(raw_T.shape[0] <= 32), shade=False)
    if not final_mask.any():
        ax.set_title("MELT-OUT: no active voxels")
        ax.text2D(0.5, 0.5, "MELT-OUT\nno active voxels", ha="center", va="center")
    sm = ScalarMappable(norm=norm, cmap="YlOrRd")
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
        im = ax.pcolormesh(x, y, field, shading="auto", cmap="Blues", vmin=0, vmax=1)
        ax.set_title(f"phi horizontal slice k={phi.sizes['nz']//2} ({label})")
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="phi", format="%.2f")
    fig.tight_layout()
    fig.savefig(outdir / "phi_horizontal.png", dpi=180)
    plt.close(fig)

    raw_phi = np.asarray(phi.isel(snapshot=-1).values, dtype=float)
    final_phi = _downsample(raw_phi)
    mask = final_phi > 0.01
    colors = plt.cm.Blues(Normalize(0.0, 1.0)(final_phi))
    xd = _downsample_coord(x, final_phi.shape[0]); yd = _downsample_coord(y, final_phi.shape[1]); zd = _downsample_coord(z, final_phi.shape[2])
    fig = plt.figure(figsize=(7, 6))
    ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, _cutaway(mask), colors=colors, title="Final phi field (partial melt; cut-away)", x=xd, y=yd, z=zd,
               edges=(raw_phi.shape[0] <= 32))
    if not mask.any():
        ax.set_title("MELT-OUT: zero active mass")
        ax.text2D(0.5, 0.5, "MELT-OUT\nzero active mass", ha="center", va="center")
    sm = ScalarMappable(norm=Normalize(0.0, 1.0), cmap="Blues")
    fig.colorbar(sm, ax=ax, shrink=0.7, label="phi", format="%.2f")
    fig.tight_layout()
    fig.savefig(outdir / "phi_3d_final.png", dpi=180)
    plt.close(fig)


def plot_salinity(ds, S, phi, outdir: Path):
    x, y, z = _grid(ds)
    valid = S.where(phi > 0.01)
    vals = np.asarray(valid.values, dtype=float)
    finite = vals[np.isfinite(vals)]
    if finite.size == 0:
        return
    vmin, vmax = float(np.min(finite)), float(np.max(finite))
    norm = Normalize(vmin=vmin, vmax=vmax)
    snaps = (0, S.sizes["snapshot"] // 2, S.sizes["snapshot"] - 1)
    labels = ("initial", "middle", "final")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, snap, label in zip(axes, snaps, labels):
        mask = phi.isel(snapshot=snap, nz=S.sizes["nz"] // 2) > 0.01
        field = np.where(mask.values, S.isel(snapshot=snap, nz=S.sizes["nz"] // 2).values, np.nan)
        im = ax.pcolormesh(x, y, field, shading="auto", cmap="Greens", norm=norm)
        ax.set_title(f"interface S_B horizontal k={S.sizes['nz']//2} ({label})")
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="interface salinity S_B (mass fraction)", format="%.4f")
    fig.tight_layout(); fig.savefig(outdir / "salinity_horizontal.png", dpi=180); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, snap, label in zip(axes, snaps, labels):
        mask = phi.isel(snapshot=snap, ny=S.sizes["ny"] // 2) > 0.01
        field = np.where(mask.values, S.isel(snapshot=snap, ny=S.sizes["ny"] // 2).values, np.nan)
        im = ax.pcolormesh(x, z, field, shading="auto", cmap="Greens", norm=norm)
        ax.set_title(f"interface S_B vertical j={S.sizes['ny']//2} ({label})")
        ax.set_xlabel("x [m]"); ax.set_ylabel("z [m]"); ax.set_aspect("equal")
        fig.colorbar(im, ax=ax, label="interface salinity S_B (mass fraction)", format="%.4f")
    fig.tight_layout(); fig.savefig(outdir / "salinity_vertical.png", dpi=180); plt.close(fig)

    raw = np.asarray(S.isel(snapshot=-1).values, dtype=float)
    rawphi = np.asarray(phi.isel(snapshot=-1).values, dtype=float)
    Sds = _downsample(raw); pds = _downsample(rawphi)
    mask = pds > 0.01
    colors = plt.cm.Greens(norm(Sds))
    xd = _downsample_coord(x, Sds.shape[0]); yd = _downsample_coord(y, Sds.shape[1]); zd = _downsample_coord(z, Sds.shape[2])
    fig = plt.figure(figsize=(7, 6)); ax = fig.add_subplot(111, projection="3d")
    _voxel_axes(ax, _cutaway(mask), colors=colors, title="Final interface salinity S_B (cut-away; ice without salt)", x=xd, y=yd, z=zd,
               edges=(raw.shape[0] <= 32))
    sm = ScalarMappable(norm=norm, cmap="Greens")
    fig.colorbar(sm, ax=ax, shrink=0.7, label="interface salinity S_B (mass fraction)", format="%.4f")
    fig.tight_layout(); fig.savefig(outdir / "salinity_3d_final.png", dpi=180); plt.close(fig)


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
        T, phi, S = _slices(vox)
        plot_shape(vox, T, phi, outdir)
        plot_temperature(vox, T, phi, outdir)
        plot_phi(vox, phi, outdir)
        if S is not None:
            plot_salinity(vox, S, phi, outdir)
        else:
            print("WARNING: S_boundary not present; salinity plots skipped")
        plot_time_series(run, vox, outdir)
    finally:
        run.close()
        vox.close()
    print(f"wrote plots to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
