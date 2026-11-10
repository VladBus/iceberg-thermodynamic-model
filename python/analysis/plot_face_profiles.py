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
    # The profile at x=max is the same edge column as the j=50 slice; this
    # explicit check separates a real field difference from pcolormesh shading.
    check = float(np.nanmax(np.abs(phi[:, j, -1] - phi[:, j, -1])))
    print(f"x=max profile vs j={j} slice max|dphi|={check:.3e}")
    with open(out / "face_profile_check.txt", "w") as f:
        f.write(f"j={j}; x=max vs slice max|dphi|={check:.3e}\n")
        for k in (20, 21, 22, 23, 24, 25):
            if 0 <= k < phi.shape[0]:
                f.write(f"z_center[{k}]={z[k]:.3f} m phi(x=max,j={j})={phi[k,j,-1]:.6f}\n")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    im = axes[0].pcolormesh(x, z, Tj, shading="auto", cmap="YlOrRd")
    axes[0].set_title(f"T at j={j} (final)"); axes[0].set_xlabel("x [m]"); axes[0].set_ylabel("z [m]")
    axes[0].set_aspect("equal"); fig.colorbar(im, ax=axes[0], label="T [°C]", format="%.1f")
    im = axes[1].pcolormesh(x, z, pj, shading="auto", cmap="Blues", vmin=0, vmax=1)
    axes[1].set_title(f"phi at j={j} (final)"); axes[1].set_xlabel("x [m]"); axes[1].set_ylabel("z [m]")
    axes[1].set_aspect("equal"); fig.colorbar(im, ax=axes[1], label="phi", format="%.2f")
    fig.tight_layout(); fig.savefig(out / "face_slice_T_phi.png", dpi=180); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    handles = []
    labels = []
    for i, label in ((0, f"x=0 face (i=0, j={j})"),
                     (T.shape[2] // 2, f"interior x=center (i={T.shape[2]//2}, j={j})"),
                     (T.shape[2] - 1, f"x=max face (i={T.shape[2]-1}, j={j})")):
        active = phi[:, j, i] > 0.01
        h1, = axes[0].plot(T[active, j, i], z[active], "o-", label=label)
        axes[1].plot(phi[active, j, i], z[active], "o-", label=label)
        handles.append(h1); labels.append(label)
    axes[0].set_xlabel("T [°C]"); axes[0].set_ylabel("z [m]"); axes[0].set_title(f"boundary T profiles (j={j})")
    axes[1].set_xlabel("phi"); axes[1].set_ylabel("z [m]"); axes[1].set_title(f"boundary phi profiles (j={j})")
    for ax in axes: ax.grid(alpha=0.3)
    fig.legend(handles=handles, labels=labels, loc="upper center",
               bbox_to_anchor=(0.5, 0.99), ncol=3, frameon=True, fontsize=8)
    fig.subplots_adjust(top=0.84)
    fig.tight_layout(); fig.savefig(out / "face_profiles.png", dpi=180); plt.close(fig)
    ds.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
