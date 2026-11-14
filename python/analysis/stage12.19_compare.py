#!/usr/bin/env python3
"""Stage 12.19 control comparison: 12.18 FJL2 2020 vs fixed run."""
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr


def cross(t, m, frac):
    m0 = m[0]
    for i in range(1, len(m)):
        if m[i] <= frac * m0:
            return t[i-1] + (m[i-1] - frac*m0)/(m[i-1] - m[i])*(t[i] - t[i-1])
    return np.nan


def load(path):
    ds = xr.open_dataset(path)
    t = ds.time.values/86400.0; m = ds.mass.values.copy()
    draft = ds.draft.values.copy(); free = ds.freeboard.values.copy()
    cal = ds.calved_mass.values.copy() if "calved_mass" in ds else np.zeros_like(m)
    ds.close()
    return t, m, draft, free, cal


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old", type=Path, default=Path("data/validation/stage12.18/FJL2_2020/run.nc"))
    p.add_argument("--new", type=Path, default=Path("data/validation/stage12.19/FJL2_2020_fixed/run.nc"))
    p.add_argument("--out", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.19/control_FJL2_2020_compare.png"))
    a = p.parse_args(); a.out.parent.mkdir(parents=True, exist_ok=True)
    to, mo, do, fo, _ = load(a.old)
    tn, mn, dn, fn, cn = load(a.new)
    fig, ax = plt.subplots(2, 2, figsize=(13, 8))
    ax[0,0].plot(to, 100*(1-mo/mo[0]), label="12.18 (before)")
    ax[0,0].plot(tn, 100*(1-mn/mn[0]), label="12.19 (fixed)")
    ax[0,0].set_xlabel("day"); ax[0,0].set_ylabel("mass loss [%]"); ax[0,0].legend(); ax[0,0].grid(alpha=.25)
    ax[0,0].set_title("Mass loss")
    ax[0,1].plot(to, do, label="12.18 draft"); ax[0,1].plot(tn, dn, label="12.19 draft")
    ax[0,1].plot(to, fo, "--", label="12.18 freeboard"); ax[0,1].plot(tn, fn, "--", label="12.19 freeboard")
    ax[0,1].set_xlabel("day"); ax[0,1].set_ylabel("m"); ax[0,1].legend(fontsize=7); ax[0,1].grid(alpha=.25)
    ax[0,1].set_title("Draft / freeboard")
    ax[1,0].plot(tn, cn, "C3", label="cumulative calved")
    ax[1,0].set_xlabel("day"); ax[1,0].set_ylabel("kg"); ax[1,0].legend(); ax[1,0].grid(alpha=.25)
    ax[1,0].set_title("Calved mass (fixed run)")
    t50o, t99o = cross(to, mo, .5), cross(to, mo, .01)
    t50n, t99n = cross(tn, mn, .5), cross(tn, mn, .01)
    ax[1,1].bar([0,1,2,3], [t50o,t50n,t99o,t99n], color=["C0","C1","C0","C1"])
    ax[1,1].set_xticks([0,1,2,3]); ax[1,1].set_xticklabels(["t50 12.18","t50 12.19","t99 12.18","t99 12.19"], rotation=15)
    ax[1,1].set_ylabel("day"); ax[1,1].set_title("Lifetimes"); ax[1,1].grid(alpha=.25, axis="y")
    fig.suptitle("FJL2 2020: before/after connectivity + main-body hydrostatics")
    fig.tight_layout(); fig.savefig(a.out, dpi=220); plt.close(fig)
    print({"t50_old": t50o, "t50_new": t50n, "t99_old": t99o, "t99_new": t99n,
           "calved_final_kg": float(cn[-1])})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
