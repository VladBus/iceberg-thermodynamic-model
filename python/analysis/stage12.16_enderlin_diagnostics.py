#!/usr/bin/env python3
"""Stage 12.16: Enderlin diagnostics without calibration.

Baselines: constant (median observed), bulk thermodynamic output (12.7a),
current-code voxel (12.15). Ratios are regressed against water-minus-freezing
temperature, draft, relative water speed, size, site, and duration.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats


def skill(pred, obs):
    mse = np.mean((pred - obs) ** 2)
    mse0 = np.mean((np.median(obs) - obs) ** 2)
    return 1.0 - mse / mse0 if mse0 > 0 else np.nan


def metrics(name, pred, obs):
    ok = np.isfinite(pred) & np.isfinite(obs) & (obs > 0)
    if ok.sum() == 0:
        return {"predictor": name, "n": 0}
    p, o = pred[ok], obs[ok]
    return {
        "predictor": name,
        "n": int(ok.sum()),
        "mae_m_per_day": float(np.mean(np.abs(p - o))),
        "rmse_m_per_day": float(np.sqrt(np.mean((p - o) ** 2))),
        "bias_m_per_day": float(np.mean(p - o)),
        "skill_vs_constant": float(skill(p, o)),
    }


def read_speed(path: Path) -> float:
    try:
        with xr.open_dataset(path) as ds:
            if "ocean_u_draft" not in ds or "ocean_v_draft" not in ds:
                return np.nan
            u = np.asarray(ds["ocean_u_draft"].values, float)
            v = np.asarray(ds["ocean_v_draft"].values, float)
            return float(np.nanmean(np.hypot(u, v)))
    except Exception:
        return np.nan


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path,
                   default=Path("data/validation/stage12.15/enderlin_current2/enderlin23_hindcast_results.csv"))
    p.add_argument("--manifest", type=Path,
                   default=Path("data/validation/stage12.15/enderlin_trajectory_manifest.csv"))
    p.add_argument("--bulk", type=Path,
                   default=Path("docs/wiki/stages/stage12/evidence/stage12.7a_results.csv"))
    p.add_argument("--run-dir", type=Path,
                   default=Path("data/validation/stage12.15/enderlin_current2"))
    p.add_argument("--out-dir", type=Path,
                   default=Path("data/validation/stage12.16"))
    p.add_argument("--fig-dir", type=Path,
                   default=Path("docs/wiki/stages/stage12/figures/stage12.16"))
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    a.fig_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(a.results)
    man = pd.read_csv(a.manifest)
    d = df.merge(man[["case_id", "surface_area", "draft"]], on="case_id", how="left")
    d["size_m"] = np.sqrt(d["surface_area"])
    d["size_bin"] = pd.cut(d["size_m"], [0, 100, 300, 1e9],
                           labels=["<=100 m", "100-300 m", ">300 m"])
    d["draft_bin"] = pd.cut(d["draft"], [0, 100, 300, 1e9],
                            labels=["<=100 m", "100-300 m", ">300 m"])
    d["rel_speed_m_s"] = [
        read_speed(a.run_dir / f"{c}_voxel.nc") for c in d["case_id"]
    ]

    obs = d["observed_melt_rate"].to_numpy(float)
    const = np.full_like(obs, np.nanmedian(obs))
    bulk_df = pd.read_csv(a.bulk)[["case_id", "modeled_melt_rate_bulk"]].rename(
        columns={"modeled_melt_rate_bulk": "bulk_rate"})
    bulk = d[["case_id"]].merge(bulk_df, on="case_id", how="left")["bulk_rate"].to_numpy(float)
    vox = d["modeled_melt_rate_voxel"].to_numpy(float)

    base = pd.DataFrame([
        metrics("constant (median observed)", const, obs),
        metrics("bulk thermodynamic (12.7a)", bulk, obs),
        metrics("voxel current (12.15)", vox, obs),
    ])
    base.to_csv(a.out_dir / "enderlin_baselines.csv", index=False)

    corr_rows = []
    for v in ["mean_delta_t_voxel", "draft", "size_m", "rel_speed_m_s",
              "interval_days", "mean_a_wet_voxel"]:
        x = d[v].to_numpy(float)
        y = d["ratio_voxel"].to_numpy(float)
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() > 2:
            corr_rows.append({
                "variable": v, "n": int(ok.sum()),
                "pearson_r": float(stats.pearsonr(x[ok], y[ok]).statistic),
                "pearson_p": float(stats.pearsonr(x[ok], y[ok]).pvalue),
                "spearman_rho": float(stats.spearmanr(x[ok], y[ok]).statistic),
                "spearman_p": float(stats.spearmanr(x[ok], y[ok]).pvalue),
            })
    pd.DataFrame(corr_rows).to_csv(a.out_dir / "enderlin_correlations.csv", index=False)

    site_rows = []
    for site, g in d.groupby("site"):
        ok = np.isfinite(g["ratio_voxel"])
        site_rows.append({
            "site": site, "n": int(ok.sum()),
            "median_ratio": float(g.loc[ok, "ratio_voxel"].median()),
            "mean_ratio": float(g.loc[ok, "ratio_voxel"].mean()),
            "mae_m_per_day": float(np.mean(np.abs(
                g.loc[ok, "modeled_melt_rate_voxel"] - g.loc[ok, "observed_melt_rate"]))),
            "median_observed": float(g.loc[ok, "observed_melt_rate"].median()),
            "median_modeled": float(g.loc[ok, "modeled_melt_rate_voxel"].median()),
        })
    pd.DataFrame(site_rows).to_csv(a.out_dir / "enderlin_site_table.csv", index=False)

    d.to_csv(a.out_dir / "enderlin_diagnostics.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    panels = [
        ("mean_delta_t_voxel", "water - freezing [C]", "ratio vs dT"),
        ("draft", "draft [m]", "ratio vs draft"),
        ("rel_speed_m_s", "mean relative water speed [m/s]", "ratio vs speed"),
    ]
    for ax, (col, xlabel, title) in zip(axes, panels):
        x = d[col].to_numpy(float)
        y = d["ratio_voxel"].to_numpy(float)
        ax.scatter(x, y, s=14, alpha=0.65)
        ax.axhline(1.0, color="k", ls="--", lw=0.8)
        ax.axhline(np.median(y[np.isfinite(y)]), color="C1", ls=":", lw=0.9,
                   label="median ratio")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("voxel / observed melt")
        ax.set_title(title)
        ax.set_yscale("log")
        ax.grid(alpha=0.25)
        ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(a.fig_dir / "enderlin_ratio_drivers.png", dpi=170)
    plt.close(fig)

    print(base.to_string(index=False))
    print()
    print(pd.DataFrame(corr_rows).to_string(index=False))
    print()
    print(pd.DataFrame(site_rows).to_string(index=False))
    print(f"\nwrote {a.out_dir} and {a.fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
