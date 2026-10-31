#!/usr/bin/env python3
"""Stage 12.7a analysis: Enderlin23 bulk/voxel hindcast metrics and plots.

Reads the CSV produced by ``enderlin23_hindcast.py``.  If no successful rows
exist (e.g. GLORYS Antarctic data unavailable), exits with status 2 and does
not create figures.  No calibration is performed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", type=Path,
                   default=Path("data/validation/results/enderlin23/enderlin23_hindcast_results.csv"))
    p.add_argument("--manifest", type=Path,
                   default=Path("docs/validation/stage12.7a_trajectory_manifest.csv"))
    p.add_argument("--figures", type=Path, default=Path("docs/validation/figures/enderlin23"))
    p.add_argument("--summary", type=Path,
                   default=Path("data/validation/results/enderlin23/summary.json"))
    return p.parse_args()


def metrics(df: pd.DataFrame, model: str) -> dict:
    obs = df["observed_melt_rate"].to_numpy(float)
    mod = df[f"modeled_melt_rate_{model}"].to_numpy(float)
    ok = np.isfinite(obs) & np.isfinite(mod) & (obs > 0)
    obs, mod = obs[ok], mod[ok]
    if len(obs) == 0:
        return {"n": 0}
    ratio = mod / obs
    rho = stats.spearmanr(mod, obs).statistic if len(obs) > 2 else np.nan
    return {
        "n": int(len(obs)),
        "median_ratio": float(np.median(ratio)),
        "mean_ratio": float(np.mean(ratio)),
        "spearman": float(rho) if np.isfinite(rho) else None,
        "mae_m_per_day": float(np.mean(np.abs(mod - obs))),
        "rmse_m_per_day": float(np.sqrt(np.mean((mod - obs) ** 2))),
        "bias_m_per_day": float(np.mean(mod - obs)),
        "median_observed_m_per_day": float(np.median(obs)),
        "median_modeled_m_per_day": float(np.median(mod)),
    }


def add_strata(df: pd.DataFrame, man: pd.DataFrame) -> pd.DataFrame:
    m = man.set_index("case_id")
    df = df.copy()
    df["sqrt_area"] = df["case_id"].map(lambda c: np.sqrt(m.loc[c, "surface_area"])
                                        if c in m.index else np.nan)
    df["size_bin"] = pd.cut(df["sqrt_area"], [0, 100, 300, 1e9],
                            labels=["<=100 m", "100-300 m", ">300 m"])
    tf = df["mean_delta_t_bulk"]
    df["tf_bin"] = pd.cut(tf, [-1e9, 0, 1, 2, 1e9],
                          labels=["<=0", "0-1", "1-2", ">2"])
    return df


def stratified(df: pd.DataFrame, by: str, model: str) -> list[dict]:
    out = []
    for key, g in df.groupby(by, observed=True, dropna=True):
        mm = metrics(g, model)
        if mm.get("n", 0) > 0:
            out.append({"stratum": str(key), "model": model, **mm})
    return out


def main() -> int:
    a = args()
    if not a.results.exists():
        print(f"BLOCKED: results file absent: {a.results}")
        return 2
    df = pd.read_csv(a.results)
    ok = df[df["status"] == "OK"].copy()
    if ok.empty:
        print("BLOCKED: no successful hindcast rows; GLORYS Antarctic data unavailable")
        return 2
    man = pd.read_csv(a.manifest)
    ok = add_strata(ok, man)

    summary = {"overall": {m: metrics(ok, m) for m in ("bulk", "voxel")},
               "by_region": [], "by_size": [], "by_thermal_forcing": []}
    for m in ("bulk", "voxel"):
        summary["by_region"] += stratified(ok, "region", m)
        summary["by_size"] += stratified(ok, "size_bin", m)
        summary["by_thermal_forcing"] += stratified(ok, "tf_bin", m)

    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    a.figures.mkdir(parents=True, exist_ok=True)

    # 1. modeled vs observed
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, m in zip(axes, ("bulk", "voxel")):
        ax.scatter(ok["observed_melt_rate"], ok[f"modeled_melt_rate_{m}"],
                   s=18, alpha=0.7)
        lim = [max(1e-3, ok["observed_melt_rate"].min() * 0.7),
               max(ok["observed_melt_rate"].max(), ok[f"modeled_melt_rate_{m}"].max()) * 1.3]
        ax.plot(lim, lim, "k--", lw=1, label="1:1")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("Наблюдаемая скорость таяния, м/сут")
        ax.set_ylabel("Модельная скорость таяния, м/сут")
        ax.set_title(f"{m}: медиана отношения = {summary['overall'][m]['median_ratio']:.2f}")
        ax.legend()
    fig.tight_layout(); fig.savefig(a.figures / "scatter_modeled_vs_observed.png", dpi=160)
    plt.close(fig)

    # 2. ratio histogram
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bins = np.logspace(-2, 2, 40)
    for m, c in (("bulk", "tab:blue"), ("voxel", "tab:orange")):
        r = ok[f"ratio_{m}"].replace([np.inf, -np.inf], np.nan).dropna()
        if len(r):
            ax.hist(r, bins=bins, alpha=0.55, label=m, color=c)
    ax.axvline(1.0, color="k", ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("Отношение модель/наблюдение")
    ax.set_ylabel("Число айсбергов")
    ax.legend(); fig.tight_layout()
    fig.savefig(a.figures / "ratio_histogram.png", dpi=160)
    plt.close(fig)

    # 3. map of trajectories colored by bulk ratio
    fig, ax = plt.subplots(figsize=(9, 6))
    for _, r in ok.iterrows():
        row = man[man.case_id == r.case_id]
        if row.empty:
            continue
        row = row.iloc[0]
        ax.plot([row.lon_i, row.lon_f], [row.lat_i, row.lat_f], color="0.7", lw=0.5)
    sc = ax.scatter(ok["case_id"].map(lambda c: man.loc[man.case_id == c, "lon_i"].iloc[0]),
                    ok["case_id"].map(lambda c: man.loc[man.case_id == c, "lat_i"].iloc[0]),
                    c=ok["ratio_bulk"], cmap="coolwarm", norm=matplotlib.colors.LogNorm(vmin=0.1, vmax=10),
                    s=22, edgecolor="k", linewidth=0.3)
    fig.colorbar(sc, ax=ax, label="ratio bulk")
    ax.set_xlabel("Долгота, °"); ax.set_ylabel("Широта, °")
    ax.set_title("Траектории Enderlin23 (цвет — отношение bulk)")
    fig.tight_layout(); fig.savefig(a.figures / "trajectory_map_ratio.png", dpi=160)
    plt.close(fig)

    # 4. stratifications
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, by, title in zip(axes, ("region", "size_bin", "tf_bin"),
                             ("Регион", "Размер √A", "T_w − T_f, °C")):
        data = [ok.loc[ok[by] == k, "ratio_bulk"].dropna() for k in ok[by].dropna().unique()]
        labels = [str(k) for k in ok[by].dropna().unique()]
        if data:
            ax.boxplot(data, tick_labels=labels, showfliers=False)
            ax.axhline(1.0, color="k", ls="--", lw=1)
            ax.set_yscale("log")
        ax.set_title(title); ax.set_ylabel("ratio bulk")
        ax.tick_params(axis="x", rotation=30)
    fig.tight_layout(); fig.savefig(a.figures / "stratified_ratio_bulk.png", dpi=160)
    plt.close(fig)

    print(f"wrote {a.summary}")
    print(f"figures: {a.figures}")
    print(json.dumps(summary["overall"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
