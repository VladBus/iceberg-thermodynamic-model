#!/usr/bin/env python3
"""Stage 12.17 summary: convergence, Enderlin, and energy closure."""
from __future__ import annotations

import argparse, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("docs/wiki/stages/stage12/figures/stage12.17/validation_summary.png"))
    a = p.parse_args(); a.out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(2, 2, figsize=(13, 10))

    conv = pd.read_csv("data/validation/stage12.14/convergence/convergence.csv")
    ax[0, 0].plot(conv["N"], 100 * conv["mass_loss_30d"], "o-")
    ax[0, 0].set_xlabel("grid N"); ax[0, 0].set_ylabel("30-day mass loss [%]")
    ax[0, 0].set_title("Convergence (p=0.711, 100^3 error 3.75%)"); ax[0, 0].grid(alpha=.25)

    d = pd.read_csv("data/validation/stage12.16/enderlin_diagnostics.csv")
    obs = d["observed_melt_rate"].to_numpy(float); mod = d["modeled_melt_rate_voxel"].to_numpy(float)
    ax[0, 1].scatter(obs, mod, s=12, alpha=.6)
    lim = [max(1e-3, min(obs.min(), mod.min()) * .7), max(obs.max(), mod.max()) * 1.3]
    ax[0, 1].plot(lim, lim, "k--", lw=.8, label="1:1")
    ax[0, 1].set_xscale("log"); ax[0, 1].set_yscale("log"); ax[0, 1].set_xlim(lim); ax[0, 1].set_ylim(lim)
    ax[0, 1].set_xlabel("observed [m/day]"); ax[0, 1].set_ylabel("voxel [m/day]")
    ax[0, 1].set_title("Enderlin23: median ratio 0.54, Spearman 0.156"); ax[0, 1].legend(); ax[0, 1].grid(alpha=.25)

    d["size"] = np.sqrt(d["surface_area"])
    ax[1, 0].scatter(d["size"], d["ratio_voxel"], s=12, alpha=.6)
    ax[1, 0].axhline(1, color="k", ls="--", lw=.8)
    ax[1, 0].set_xscale("log"); ax[1, 0].set_xlabel("sqrt surface area [m]"); ax[1, 0].set_ylabel("model / observed")
    ax[1, 0].set_title("Enderlin ratio vs size (Spearman -0.506)"); ax[1, 0].grid(alpha=.25)

    labels, final, mx = [], [], []
    for name, f in [("50^3", "data/validation/stage12.16/energy_50_30d/closure.json"),
                    ("100^3", "data/validation/stage12.16/energy_100_30d/closure.json")]:
        if Path(f).exists():
            j = json.loads(Path(f).read_text())
            labels.append(name); final.append(abs(j["residual_final_pct_latent"])); mx.append(abs(j["residual_max_abs_pct_latent"]))
    x = np.arange(len(labels))
    if labels:
        ax[1, 1].bar(x - .18, final, .36, label="final")
        ax[1, 1].bar(x + .18, mx, .36, label="max abs")
        ax[1, 1].set_xticks(x); ax[1, 1].set_xticklabels(labels)
    ax[1, 1].axhline(2.0, color="r", ls="--", lw=.8, label="2% target")
    ax[1, 1].set_ylabel("residual [% of latent]"); ax[1, 1].set_title("Energy closure (30 d)")
    ax[1, 1].legend(); ax[1, 1].grid(alpha=.25, axis="y")

    fig.tight_layout(); fig.savefig(a.out, dpi=220); plt.close(fig)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
