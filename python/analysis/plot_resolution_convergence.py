#!/usr/bin/env python3
"""Summarize 8/20/50/100 voxel resolution tests from Stage 12.12.

Usage: python python/analysis/plot_resolution_convergence.py --root DIR --outdir DIR
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


def _time_mem(path: Path):
    if not path.exists():
        return np.nan, np.nan
    text = path.read_text(errors="replace")
    m = re.search(r"Elapsed \(wall clock\) time.*?\): ([0-9:.]+)", text)
    mem = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
    if not m:
        return np.nan, (int(mem.group(1))/1024.0 if mem else np.nan)
    parts = [float(x) for x in m.group(1).split(":")]
    sec = parts[-1] + (parts[-2]*60 if len(parts) >= 2 else 0) + (parts[-3]*3600 if len(parts) >= 3 else 0)
    return sec, (int(mem.group(1))/1024.0 if mem else np.nan)


def _metrics(root: Path, n: int, suffix: str):
    run = root / str(n) / f"run{suffix}.nc"
    vox = root / str(n) / f"run{suffix}.nc_voxel.nc"
    if not run.exists():
        return None
    ds = xr.open_dataset(run); vo = xr.open_dataset(vox)
    m0 = float(ds.mass[0]); m1 = float(ds.mass[-1])
    T = np.asarray(vo.T.isel(snapshot=-1).values)
    phi = np.asarray(vo.phi.isel(snapshot=-1).values)
    active = phi > 0.01
    out = {
        "n": n, "days": (float(ds.time[-1])-float(ds.time[0]))/86400.0,
        "mass0_kg": m0, "mass_end_kg": m1, "mass_loss_frac": (m0-m1)/m0,
        "T_min_C": float(np.min(T[active])) if active.any() else np.nan,
        "T_max_C": float(np.max(T[active])) if active.any() else np.nan,
        "T_mean_C": float(np.mean(T[active])) if active.any() else np.nan,
        "phi_mean": float(phi[active].mean()) if active.any() else np.nan,
        "draft_m": float(ds.draft[-1]), "freeboard_m": float(ds.freeboard[-1]),
        "cg_iters_max": float(np.nanmax(ds.cg_iters.values)),
        "cg_resid_max": float(np.nanmax(ds.cg_resid.values)),
    }
    ds.close(); vo.close()
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="data/validation/stage12.12/resolution")
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()
    root = Path(args.root); outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in (8, 20, 50, 70, 100):
        for suffix, span in (("", "5d"), ("30", "30d")):
            m = _metrics(root, n, suffix)
            if m is None:
                continue
            sec, mem = _time_mem(root / str(n) / f"time{suffix}.log")
            m.update({"span": span, "elapsed_s": sec, "max_rss_mb": mem})
            rows.append(m)
    with (outdir / "resolution_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for span in ("5d", "30d"):
        subset = [r for r in rows if r["span"] == span]
        n = [r["n"] for r in subset]
        axes[0].plot(n, [r["mass_loss_frac"] for r in subset], "o-", label=span)
        axes[1].plot(n, [r["T_min_C"] for r in subset], "o-", label=f"{span} Tmin")
        axes[1].plot(n, [r["T_max_C"] for r in subset], "o--", label=f"{span} Tmax")
        axes[2].plot(n, [r["elapsed_s"] for r in subset], "o-", label=f"{span} time")
    axes[0].set_xlabel("N (voxels per axis)"); axes[0].set_ylabel("mass loss fraction")
    axes[0].set_xscale("log"); axes[0].grid(alpha=0.3); axes[0].legend()
    axes[1].set_xlabel("N"); axes[1].set_ylabel("temperature [C]")
    axes[1].set_xscale("log"); axes[1].grid(alpha=0.3); axes[1].legend(fontsize=8)
    axes[2].set_xlabel("N"); axes[2].set_ylabel("wall time [s]")
    axes[2].set_xscale("log"); axes[2].set_yscale("log"); axes[2].grid(alpha=0.3); axes[2].legend()
    fig.tight_layout(); fig.savefig(outdir / "resolution_convergence.png", dpi=180); plt.close(fig)
    print(f"wrote {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
