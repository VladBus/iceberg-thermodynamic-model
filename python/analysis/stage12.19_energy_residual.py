#!/usr/bin/env python3
"""Plot energy residual before/after Stage 12.19 with calving markers."""
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--old", type=Path, default=Path("data/validation/stage12.18/FJL2_2020/run.nc_energy.csv"))
    p.add_argument("--new", type=Path, default=Path("data/validation/stage12.19/FJL2_2020_fixed/run.nc_energy.csv"))
    p.add_argument("--calved", type=Path, default=Path("data/validation/stage12.19/FJL2_2020_fixed/run.nc_calved.csv"))
    p.add_argument("--out", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.19/energy_residual_calving.png"))
    a = p.parse_args(); a.out.parent.mkdir(parents=True, exist_ok=True)
    o = pd.read_csv(a.old); n = pd.read_csv(a.new); c = pd.read_csv(a.calved)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(o.time_s/86400, o.residual_pct_latent, label="12.18 (before fix)")
    ax.plot(n.time_s/86400, n.residual_pct_latent, label="12.19 (corrected ledger)")
    for _, r in c.iterrows():
        ax.axvline(r.time_s/86400, color="k", ls="--", lw=.8)
        ax.annotate(f"calved {r.mass_kg/1e6:.2f} Mt", (r.time_s/86400, ax.get_ylim()[0]),
                    xytext=(3, 4), textcoords="offset points", fontsize=7, rotation=90)
    ax.axhline(0, color="k", lw=.5)
    ax.axhline(2, color="r", ls=":", lw=.8); ax.axhline(-2, color="r", ls=":", lw=.8)
    ax.set_xlabel("day"); ax.set_ylabel("residual [% of latent]")
    ax.set_title("FJL2 2020 energy closure and calving times"); ax.legend(); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(a.out, dpi=220); plt.close(fig)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
