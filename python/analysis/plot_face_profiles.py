#!/usr/bin/env python3
"""Plot face-adjacent T/phi profiles and symmetry metrics for a voxel run.

Usage: python python/analysis/plot_face_profiles.py VOXEL.nc --outdir DIR
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("voxel_nc")
    p.add_argument("--outdir", required=True)
    a = p.parse_args()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    ds = xr.open_dataset(a.voxel_nc)
    T = np.asarray(ds.T.isel(snapshot=-1).values)       # (nz, ny, nx)
    phi = np.asarray(ds.phi.isel(snapshot=-1).values)
    x = np.asarray(ds.x.values); z = np.asarray(ds.z.values)
    j = T.shape[1] // 2
    Tj = T[:, j, :]; pj = phi[:, j, :]
    txsym = float(np.nanmax(np.abs(T - T[:, :, ::-1])))
    pxsym = float(np.nanmax(np.abs(phi - phi[:, :, ::-1])))
    print(f"T x-symmetry max|T-T[::-1]|={txsym:.3e}; phi={pxsym:.3e}")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    im = axes[0].pcolormesh(x, z, Tj, shading="auto", cmap="YlOrRd")
    axes[0].set_title(f"T at j={j} (final)"); axes[0].set_xlabel("x [m]"); axes[0].set_ylabel("z [m]")
    axes[0].set_aspect("equal"); fig.colorbar(im, ax=axes[0], label="T [°C]", format="%.1f")
    im = axes[1].pcolormesh(x, z, pj, shading="auto", cmap="Blues", vmin=0, vmax=1)
    axes[1].set_title(f"phi at j={j} (final)"); axes[1].set_xlabel("x [m]"); axes[1].set_ylabel("z [m]")
    axes[1].set_aspect("equal"); fig.colorbar(im, ax=axes[1], label="phi", format="%.2f")
    fig.tight_layout(); fig.savefig(out / "face_slice_T_phi.png", dpi=180); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for i, label in ((0, "x=0"), (T.shape[2] // 2, "x=center"), (T.shape[2] - 1, "x=max")):
        active = phi[:, j, i] > 0.01
        axes[0].plot(T[active, j, i], z[active], "o-", label=label)
        axes[1].plot(phi[active, j, i], z[active], "o-", label=label)
    axes[0].set_xlabel("T [°C]"); axes[0].set_ylabel("z [m]"); axes[0].set_title("boundary T profiles")
    axes[1].set_xlabel("phi"); axes[1].set_ylabel("z [m]"); axes[1].set_title("boundary phi profiles")
    for ax in axes: ax.grid(alpha=0.3); ax.legend()
    fig.tight_layout(); fig.savefig(out / "face_profiles.png", dpi=180); plt.close(fig)
    ds.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
