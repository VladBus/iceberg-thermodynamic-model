#!/usr/bin/env python3
"""Stage 12.14: 2020 tail mass, drift, bathymetry/grounding and fallback."""
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv"); p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(); d = pd.read_csv(a.csv); a.out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    ax[0].plot(d.day, d.mass / d.mass.iloc[0], label="mass / initial")
    ax[0].set_ylabel("mass / initial"); ax[0].grid(alpha=.3); ax[0].legend()
    ax[1].plot(d.day, d.speed_m_s, label="drift speed")
    ax[1].plot(d.day, d.bathymetry, label="bathymetry")
    ax[1].plot(d.day, d.draft, label="draft")
    ax[1].axhline(7, color="k", ls="--", lw=.8)
    ax[1].set_ylabel("m or m/s"); ax[1].grid(alpha=.3); ax[1].legend(ncol=3, fontsize=8)
    ax[2].bar(d.day, d.fallback, width=0.8, color="tab:red", alpha=.7, label="fallback events/day")
    ax[2].set_ylabel("fallback/day"); ax[2].set_xlabel("day"); ax[2].grid(alpha=.3); ax[2].legend()
    for x in (295, 300):
        for a0 in ax: a0.axvline(x, color="0.5", ls=":", lw=.8)
    fig.tight_layout(); fig.savefig(a.out, dpi=170); plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
