#!/usr/bin/env python3
"""Compare the 2020 and 2024 annual iceberg_run time series.

Usage: python python/analysis/compare_voxel_years.py RUN2020.nc RUN2024.nc --outdir DIR
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


def _load(path: str) -> dict:
    ds = xr.open_dataset(path)
    t = np.asarray(ds["time"].values, dtype=float) / 86400.0
    out = {
        "t": t,
        "mass": np.asarray(ds["mass"].values, dtype=float),
        "volume": np.asarray(ds["volume"].values, dtype=float),
        "draft": np.asarray(ds["draft"].values, dtype=float),
        "freeboard": np.asarray(ds["freeboard"].values, dtype=float),
    }
    for name in ("voxel_mass_loss_basal", "voxel_mass_loss_lateral",
                 "voxel_mass_loss_surface", "voxel_mass_loss_flush"):
        out[name] = np.asarray(ds[name].values, dtype=float) if name in ds else None
    ds.close()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run2020")
    parser.add_argument("run2024")
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    a = _load(args.run2020)
    b = _load(args.run2024)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for ax, key, label, norm in (
        (axes[0, 0], "mass", "mass", True),
        (axes[0, 0], "volume", "volume", True),
    ):
        ax.plot(a["t"], a[key] / a[key][0], label=f"2020 {label}")
        ax.plot(b["t"], b[key] / b[key][0], label=f"2024 {label}")
    axes[0, 0].set_xlabel("time [day]")
    axes[0, 0].set_ylabel("normalized to initial")
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.3)

    axes[0, 1].plot(a["t"], a["draft"], label="2020 draft")
    axes[0, 1].plot(b["t"], b["draft"], label="2024 draft")
    axes[0, 1].plot(a["t"], a["freeboard"], "--", label="2020 freeboard")
    axes[0, 1].plot(b["t"], b["freeboard"], "--", label="2024 freeboard")
    axes[0, 1].set_xlabel("time [day]")
    axes[0, 1].set_ylabel("height [m]")
    axes[0, 1].legend()
    axes[0, 1].grid(alpha=0.3)

    if all(a[k] is not None for k in ("voxel_mass_loss_basal", "voxel_mass_loss_lateral",
                                      "voxel_mass_loss_surface", "voxel_mass_loss_flush")):
        for k, label in (("voxel_mass_loss_basal", "basal"),
                         ("voxel_mass_loss_lateral", "lateral"),
                         ("voxel_mass_loss_surface", "surface"),
                         ("voxel_mass_loss_flush", "flush")):
            axes[1, 0].plot(a["t"], a[k], label=f"2020 {label}")
            axes[1, 0].plot(b["t"], b[k], "--", label=f"2024 {label}")
        axes[1, 0].set_xlabel("time [day]")
        axes[1, 0].set_ylabel("cumulative mass loss [kg]")
        axes[1, 0].legend(fontsize=7, ncol=2)
        axes[1, 0].grid(alpha=0.3)

    axes[1, 1].plot(a["t"], a["mass"], label="2020 mass")
    axes[1, 1].plot(b["t"], b["mass"], label="2024 mass")
    axes[1, 1].set_xlabel("time [day]")
    axes[1, 1].set_ylabel("mass [kg]")
    axes[1, 1].legend()
    axes[1, 1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "comparison_2020_2024.png", dpi=180)
    plt.close(fig)
    print(f"wrote {out / 'comparison_2020_2024.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
