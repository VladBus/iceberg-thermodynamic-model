#!/usr/bin/env python3
"""Plot voxel vs legacy prism geometry diagnostics.

Usage: python python/analysis/plot_prism_consistency.py RUN2020.nc RUN2024.nc --outdir DIR
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


def load(path: str):
    ds = xr.open_dataset(path)
    t = np.asarray(ds.time.values, dtype=float) / 86400.0
    out = {"t": t}
    for k in ("mass", "prism_mass", "draft", "prism_draft", "freeboard", "prism_freeboard"):
        out[k] = np.asarray(ds[k].values, dtype=float)
    ds.close()
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run2020")
    p.add_argument("run2024")
    p.add_argument("--outdir", required=True)
    a = p.parse_args()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    runs = {"2020": load(a.run2020), "2024": load(a.run2024)}
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for label, d in runs.items():
        axes[0, 0].plot(d["t"], d["mass"]/d["mass"][0], label=f"{label} voxel")
        axes[0, 0].plot(d["t"], d["prism_mass"]/d["prism_mass"][0], "--", label=f"{label} prism")
        axes[0, 1].plot(d["t"], d["draft"], label=f"{label} voxel")
        axes[0, 1].plot(d["t"], d["prism_draft"], "--", label=f"{label} prism")
        rel = np.divide(np.abs(d["mass"]-d["prism_mass"]), d["prism_mass"],
                        out=np.zeros_like(d["mass"]), where=d["prism_mass"] > 0)
        axes[1, 0].plot(d["t"], rel, label=label)
        relf = np.divide(np.abs(d["freeboard"]-d["prism_freeboard"]), d["prism_freeboard"],
                         out=np.zeros_like(d["freeboard"]), where=d["prism_freeboard"] > 0)
        axes[1, 1].plot(d["t"], relf, label=label)
    axes[0, 0].set_xlabel("time [day]"); axes[0, 0].set_ylabel("mass / initial")
    axes[0, 0].legend(); axes[0, 0].grid(alpha=0.3)
    axes[0, 1].set_xlabel("time [day]"); axes[0, 1].set_ylabel("draft [m]")
    axes[0, 1].legend(); axes[0, 1].grid(alpha=0.3)
    axes[1, 0].set_xlabel("time [day]"); axes[1, 0].set_ylabel("relative mass difference")
    axes[1, 0].legend(); axes[1, 0].grid(alpha=0.3)
    axes[1, 1].set_xlabel("time [day]"); axes[1, 1].set_ylabel("relative freeboard difference")
    axes[1, 1].legend(); axes[1, 1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out / "prism_consistency.png", dpi=180); plt.close(fig)
    print(f"wrote {out / 'prism_consistency.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
