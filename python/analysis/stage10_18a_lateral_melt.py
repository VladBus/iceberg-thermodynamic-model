#!/usr/bin/env python3
"""
Stage 10.18A — Lateral Melt Parameterization Research Audit: analysis.

Reads:
    data/output/diagnostics/stage9.3/test11_trajectory.csv  (extended 30-day TEST_11)
Writes (all gitignored):
    data/output/stage10.18a/
        baseline_results.csv          legacy m_l vs DeltaT (m/s, m/day)
        sensitivity_matrix.csv        DeltaT x U x L melt rates for all variants
        parameterization_comparison.csv  per-variant rates/areas at reference state
        test11_comparison.csv         30-day replay: mass/geometry/component shares
        literature_comparison.csv     parameterized rates vs published ranges
        summary.json
        plots/fig01_legacy_vs_deltaT.png ... fig10_literature_ranges.png

Variants (see python/validation/lateral_melt.py for formulas/provenance):
    LEGACY_FULL_HEIGHT   production: m = C_LATERAL*<dT>_D, area H(L+W)
    LEGACY_SUBMERGED     production rate, submerged full-perimeter area 2(L+W)D
    BULK_FORCED          model basal closure applied to side (L_char=D)
    BIGG1997             K*U^0.8*dT/L^0.2 (K=0.58)
    BIGG_PLUS_BUOY       Bigg + Neshyba-Josberger buoyant term
    FITZMAURICE_PLUME    plume-regime piecewise (attached/detached)

Conventions: melt rates in m/day; mass in Mt (1e6 kg); SI elsewhere.
Time: day 0 = initial state; 30 days = 720 hourly steps (dt = 3600 s).

Run:
    conda run -n iceberg-thermodynamic-model \
        python python/analysis/stage10_18a_lateral_melt.py
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model")
sys.path.insert(0, str(REPO))  # repo root -> `python.validation` package imports
sys.path.insert(0, str(REPO / "python" / "validation"))  # flat module imports

from python.validation.lateral_melt import (
    BIGG_K_OCEAN,
    C_LATERAL,
    NESHYBA_A,
    NESHYBA_B,
    PLUME_SPEED_LAB,
    bigg1997_forced_convection_melt_rate,
    bulk_velocity_dependent_side_melt,
    fitzmaurice_plume_side_melt,
    lateral_area_full_height,
    lateral_area_submerged_full_perimeter,
    lateral_volume_rate_full_height,
    lateral_volume_rate_submerged_full_perimeter,
    legacy_lateral_melt_rate,
    m_day_to_m_s,
    m_s_to_m_day,
    neshyba_josberger_buoyant_melt_rate,
    numeric_exponent,
    side_heat_transfer_coefficient,
)
from python.validation.basal_melt import LATENT_HEAT, RHO_ICE, RHO_WATER

REPO = Path("/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model")
OUT = REPO / "data" / "output" / "stage10.18a"
PLOTS = OUT / "plots"
TRAJ_30 = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"

DT_S = 3600.0
SEC_PER_DAY = 86400.0
M_TONNE = 1.0e6

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight"})

VARIANTS = ["LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED", "BULK_FORCED",
            "BIGG1997", "BIGG_PLUS_BUOY", "FITZMAURICE_PLUME"]


def load_traj(path: Path) -> pd.DataFrame:
    """TEST_11 CSV: comma header + Fortran fixed-width whitespace rows."""
    with open(path) as f:
        header = f.readline().strip().split(",")
    df = pd.read_csv(path, sep=r"\s+", skiprows=1, names=header)
    df["day"] = (df["step"].astype(float) - 1.0) / 24.0
    return df


def davg_from_ml(ml_mday: np.ndarray) -> np.ndarray:
    """Recover production <DeltaT>_D from ml_mday (ml = C_LATERAL*<dT>_D*86400)."""
    return np.asarray(ml_mday) / C_LATERAL / SEC_PER_DAY


# ---------------------------------------------------------------------------
# 1. Baseline table: legacy m_l vs DeltaT
# ---------------------------------------------------------------------------
def baseline_table():
    dts = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0]
    rows = []
    for dt in dts:
        m_s = legacy_lateral_melt_rate(dt)
        rows.append({"delta_t_degC": dt, "m_lateral_m_s": m_s,
                     "m_lateral_m_day": m_s_to_m_day(m_s)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Research variant melt rates at a reference state
# ---------------------------------------------------------------------------
def variant_melt(delta_t: float, u_rel: float, L: float, D: float) -> dict:
    """Per-variant lateral melt rate [m/day] at one state."""
    m_legacy = legacy_lateral_melt_rate(delta_t)
    m_bulk = bulk_velocity_dependent_side_melt(delta_t, u_rel, D)
    m_bigg = bigg1997_forced_convection_melt_rate(u_rel, delta_t, L)
    m_buoy = neshyba_josberger_buoyant_melt_rate(delta_t)
    m_plume = fitzmaurice_plume_side_melt(u_rel, delta_t, L, D)
    return {
        "LEGACY_FULL_HEIGHT": m_s_to_m_day(m_legacy),
        "LEGACY_SUBMERGED": m_s_to_m_day(m_legacy),
        "BULK_FORCED": m_s_to_m_day(m_bulk),
        "BIGG1997": m_s_to_m_day(m_bigg),
        "BIGG_PLUS_BUOY": m_s_to_m_day(m_bigg + m_buoy),
        "FITZMAURICE_PLUME": m_s_to_m_day(m_plume),
    }


def parameterization_comparison():
    L = W = H = 100.0
    D = H * RHO_ICE / RHO_WATER
    delta_t = 3.0
    u_rel = 0.1
    rates = variant_melt(delta_t, u_rel, L, D)

    a_full = lateral_area_full_height(L, W, H)
    a_sub = lateral_area_submerged_full_perimeter(L, W, H)
    rows = []
    for name in VARIANTS:
        m_day = rates[name]
        m_s = m_day_to_m_s(m_day)
        if name == "LEGACY_SUBMERGED":
            dV = lateral_volume_rate_submerged_full_perimeter(m_s, L, W, H)
            a = a_sub
        else:
            dV = lateral_volume_rate_full_height(m_s, L, W, H)
            a = a_full
        rows.append({
            "variant": name, "m_lateral_m_day": m_day, "area_m2": a,
            "dV_dt_m3_s": dV, "dm_dt_kg_s": RHO_ICE * dV,
            "mass_loss_Mt_day": RHO_ICE * dV * SEC_PER_DAY / M_TONNE,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Sensitivity matrix: DeltaT x U x L
# ---------------------------------------------------------------------------
def sensitivity_matrix():
    dts = [0.5, 1.0, 2.0, 3.0, 4.0, 6.0]
    us = [0.0, 0.001, 0.01, 0.03, 0.1, 0.3, 1.0]
    Ls = [10.0, 50.0, 100.0, 200.0, 300.0]
    D = 88.5
    rows = []
    for dt in dts:
        for u in us:
            for L in Ls:
                rates = variant_melt(dt, u, L, D)
                row = {"delta_t_degC": dt, "u_rel_m_s": u, "L_m": L, "D_m": D}
                for k, v in rates.items():
                    row[k + "_m_day"] = v
                rows.append(row)
    return pd.DataFrame(rows)


def scalings(sens: pd.DataFrame):
    """Numeric exponents dln m/dln x from the sensitivity matrix at U=0.1, L=100."""
    out = {}
    dts = [1.0, 3.0]
    us = [0.1, 0.3]
    Ls = [100.0, 200.0]
    for v in VARIANTS:
        col = v + "_m_day"
        sub = sens[(sens["u_rel_m_s"] == 0.1) & (sens["L_m"] == 100.0)]
        m1 = sub[sub["delta_t_degC"] == dts[0]][col].iloc[0]
        m3 = sub[sub["delta_t_degC"] == dts[1]][col].iloc[0]
        n_dt = numeric_exponent(dts[1], dts[0], m3, m1)
        sub2 = sens[(sens["delta_t_degC"] == 3.0) & (sens["L_m"] == 100.0)]
        mu1 = sub2[sub2["u_rel_m_s"] == us[0]][col].iloc[0]
        mu2 = sub2[sub2["u_rel_m_s"] == us[1]][col].iloc[0]
        n_u = numeric_exponent(us[1], us[0], mu2, mu1) if mu1 > 0 else float("nan")
        sub3 = sens[(sens["delta_t_degC"] == 3.0) & (sens["u_rel_m_s"] == 0.1)]
        ml1 = sub3[sub3["L_m"] == Ls[0]][col].iloc[0]
        ml2 = sub3[sub3["L_m"] == Ls[1]][col].iloc[0]
        n_l = numeric_exponent(Ls[1], Ls[0], ml2, ml1) if ml1 > 0 else float("nan")
        out[v] = {"dlnm_dlnDeltaT": n_dt, "dlnm_dlnU": n_u, "dlnm_dlnL": n_l}
    return out


# ---------------------------------------------------------------------------
# 4. Full-height vs submerged geometry (exact comparison at fixed state)
# ---------------------------------------------------------------------------
def geometry_comparison():
    L = W = H = 100.0
    D = H * RHO_ICE / RHO_WATER
    m_l = 3.008e-6  # TEST_11 <DeltaT>_D = 3.008 K, C_LATERAL = 1e-6
    a_full = lateral_area_full_height(L, W, H)
    a_sub = lateral_area_submerged_full_perimeter(L, W, H)
    dV_full = lateral_volume_rate_full_height(m_l, L, W, H)
    dV_sub = lateral_volume_rate_submerged_full_perimeter(m_l, L, W, H)
    return {
        "L_m": L, "W_m": W, "H_m": H, "D_m": D,
        "m_l_m_s": m_l,
        "A_full_height_m2": a_full,
        "A_submerged_full_perim_m2": a_sub,
        "dV_full_height_m3_s": dV_full,
        "dV_submerged_full_perim_m3_s": dV_sub,
        "area_ratio_sub_over_full": a_sub / a_full,
        "vol_ratio_sub_over_full": dV_sub / dV_full,
        "H_over_D": H / D,
    }


# ---------------------------------------------------------------------------
# 5. TEST_11 replay (offline, production trajectory as common forcing)
# ---------------------------------------------------------------------------
def side_melt_variant_rate(variant: str, delta_t: float, u_rel: float,
                           L: float, D: float) -> float:
    """Per-step lateral melt rate [m/s] for a research variant.

    For LEGACY_SUBMERGED the geometry factors the submerged full-perimeter
    convention (2(L+W)D) into the prism update (H(L+W)): the effective
    horizontal shrink is m_l * (2D/H) = m_l * 2*rho_i/rho_w (constant).
    """
    if variant == "LEGACY_FULL_HEIGHT":
        return legacy_lateral_melt_rate(delta_t)
    if variant == "LEGACY_SUBMERGED":
        return legacy_lateral_melt_rate(delta_t) * 2.0 * RHO_ICE / RHO_WATER
    if variant == "BULK_FORCED":
        return bulk_velocity_dependent_side_melt(delta_t, u_rel, D)
    if variant == "BIGG1997":
        return bigg1997_forced_convection_melt_rate(u_rel, delta_t, L)
    if variant == "BIGG_PLUS_BUOY":
        return (bigg1997_forced_convection_melt_rate(u_rel, delta_t, L)
                + neshyba_josberger_buoyant_melt_rate(delta_t))
    if variant == "FITZMAURICE_PLUME":
        return fitzmaurice_plume_side_melt(u_rel, delta_t, L, D)
    raise ValueError(f"unknown variant {variant}")


def replay_test11(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Replay the 30-day TEST_11 with the model's update rule under each
    lateral variant, holding basal/surface/vapor and U_rel at production
    values (controlled first-order comparison)."""
    n = len(df)
    davg = davg_from_ml(df["ml_mday"].to_numpy())
    u_rel = df["u_rel_draft_ms"].to_numpy()
    m_b = m_day_to_m_s(df["mb_mday"].to_numpy())
    m_s = m_day_to_m_s(df["ms_mday"].to_numpy())
    m_v = df["m_vapor_kgm2s"].to_numpy()
    rows = {v: {"L": np.empty(n), "W": np.empty(n), "H": np.empty(n),
                "M": np.empty(n), "ml": np.empty(n),
                "lat_loss": np.empty(n)} for v in VARIANTS}
    for v in VARIANTS:
        L = 100.0
        W = 100.0
        H = 100.0
        for i in range(n):
            D = H * RHO_ICE / RHO_WATER
            m_l = side_melt_variant_rate(v, float(davg[i]), float(u_rel[i]),
                                         float(L), float(D))
            rows[v]["ml"][i] = m_l
            # volume accounting is consistent with the geometry update through
            # the variant-specific m_l (m_apply encodes the area convention)
            A = lateral_area_full_height(L, W, H)
            rows[v]["lat_loss"][i] = RHO_ICE * A * m_l * DT_S
            H = max(H - DT_S * (m_b[i] + m_s[i] - m_v[i] / RHO_ICE), 0.0)
            L = max(L - DT_S * m_l, 0.0)
            W = max(W - DT_S * m_l, 0.0)
            rows[v]["L"][i] = L
            rows[v]["W"][i] = W
            rows[v]["H"][i] = H
            rows[v]["M"][i] = RHO_ICE * L * W * H

    # production component losses (common to all variants). Vapor sign follows
    # production: diag%vapor_mass_loss = -rho_i*dV_vapor = -L*W*dt*m_v (m_v<0
    # sublimation -> positive loss).
    basal_loss = np.sum(RHO_ICE * df["L_m"].to_numpy() * df["W_m"].to_numpy()
                        * m_b * DT_S)
    surf_loss = np.sum(RHO_ICE * df["L_m"].to_numpy() * df["W_m"].to_numpy()
                       * m_s * DT_S)
    vapor_loss = -np.sum(df["L_m"].to_numpy() * df["W_m"].to_numpy()
                         * m_v * DT_S)
    M0 = RHO_ICE * 100.0 * 100.0 * 100.0

    out = []
    for v in VARIANTS:
        lat = float(np.sum(rows[v]["lat_loss"]))
        tot = basal_loss + surf_loss + vapor_loss + lat
        out.append({
            "variant": v,
            "M0_Mt": M0 / M_TONNE,
            "Mf_Mt": rows[v]["M"][-1] / M_TONNE,
            "dM_Mt": (M0 - rows[v]["M"][-1]) / M_TONNE,
            "dM_pct": (M0 - rows[v]["M"][-1]) / M0 * 100.0,
            "lateral_loss_Mt": lat / M_TONNE,
            "basal_loss_Mt": basal_loss / M_TONNE,
            "surface_loss_Mt": surf_loss / M_TONNE,
            "vapor_loss_Mt": vapor_loss / M_TONNE,
            "lateral_pct": lat / tot * 100.0,
            "basal_pct": basal_loss / tot * 100.0,
            "surface_pct": surf_loss / tot * 100.0,
            "vapor_pct": vapor_loss / tot * 100.0,
            "Lf_m": rows[v]["L"][-1],
            "Wf_m": rows[v]["W"][-1],
            "Hf_m": rows[v]["H"][-1],
            "ml_mean_m_day": m_s_to_m_day(float(np.mean(rows[v]["ml"]))),
            "ml_max_m_day": m_s_to_m_day(float(np.max(rows[v]["ml"]))),
        })
    return pd.DataFrame(out), rows


# ---------------------------------------------------------------------------
# 6. Literature comparison
# ---------------------------------------------------------------------------
def literature_comparison():
    delta_t = 3.0
    L = 100.0
    D = 88.5
    u_low, u_hi = 0.01, 0.3  # TEST_11-like and legacy-equivalent speeds
    rows = []
    for u in (u_low, u_hi):
        m_bigg = bigg1997_forced_convection_melt_rate(u, delta_t, L)
        m_buoy = neshyba_josberger_buoyant_melt_rate(delta_t)
        m_plume = fitzmaurice_plume_side_melt(u, delta_t, L, D)
        rows.append({
            "source": "Bigg-type forced convection (K=0.58, FitzMaurice2017 quote)",
            "u_rel_m_s": u, "delta_t_degC": delta_t,
            "m_day": m_s_to_m_day(m_bigg),
            "note": "K=0.58 m/day per (m/s)^0.8 K m^-0.2; validity: forced regime",
        })
        rows.append({
            "source": "Neshyba-Josberger buoyant (Cenedese & Straneo 2023)",
            "u_rel_m_s": u, "delta_t_degC": delta_t,
            "m_day": m_s_to_m_day(m_buoy),
            "note": "a=7.62e-3, b=1.29e-3 m/day; velocity-independent",
        })
        rows.append({
            "source": "FitzMaurice plume (2017 GRL)",
            "u_rel_m_s": u, "delta_t_degC": delta_t,
            "m_day": m_s_to_m_day(m_plume),
            "note": f"regime {'attached' if u < PLUME_SPEED_LAB else 'detached'}; "
                    f"plume speed {PLUME_SPEED_LAB} m/s",
        })
    rows.append({
        "source": "Cenedese & Straneo 2023 typical max (side melt)",
        "u_rel_m_s": float("nan"), "delta_t_degC": float("nan"),
        "m_day": 0.2, "note": "parameterized upper bound, sparse field validation",
    })
    rows.append({
        "source": "FitzMaurice et al. 2017 Sermilik attached-plume side melt",
        "u_rel_m_s": float("nan"), "delta_t_degC": float("nan"),
        "m_day": 0.08, "note": "0.06-0.10 m/day mean; area-averaged obs ~0.39 m/day",
    })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def make_figures(baseline: pd.DataFrame, sens: pd.DataFrame, geom: dict,
                 replay: pd.DataFrame, replay_rows: dict, df: pd.DataFrame,
                 lit: pd.DataFrame):
    dts = baseline["delta_t_degC"].to_numpy()
    m_day = baseline["m_lateral_m_day"].to_numpy()

    # fig01: legacy m_l vs DeltaT
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(dts, m_day, "o-", label="LEGACY_FULL_HEIGHT (C_LATERAL=1e-6)")
    ax.set_xlabel(r"$\langle\Delta T\rangle_D$ [degC]")
    ax.set_ylabel("m_lateral [m/day]")
    ax.set_title("Fig 1. Legacy lateral melt vs thermal driving")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig01_legacy_vs_deltaT.png")
    plt.close(fig)

    # fig02: research parameterizations vs U_rel (several DeltaT)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    us = np.array([0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0])
    for ax, dt in zip(axes, (1.0, 3.0, 6.0)):
        for v in ("BULK_FORCED", "BIGG1997", "BIGG_PLUS_BUOY", "FITZMAURICE_PLUME"):
            vals = [variant_melt(dt, u, 100.0, 88.5)[v] for u in us]
            ax.plot(us, vals, "-o", ms=3, label=v)
        ax.axhline(m_s_to_m_day(legacy_lateral_melt_rate(dt)), color="k", ls="--",
                   label="LEGACY")
        ax.axvline(PLUME_SPEED_LAB, color="grey", ls=":", label="plume speed")
        ax.set_xscale("log")
        ax.set_xlabel("U_rel [m/s]")
        ax.set_title(f"Fig 2. Side melt vs U_rel, dT={dt} K")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3, which="both")
    axes[0].set_ylabel("m_lateral [m/day]")
    fig.savefig(PLOTS / "fig02_research_vs_U.png")
    plt.close(fig)

    # fig03: full-height vs submerged volume/mass-loss rate
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["FULL-HEIGHT\nH(L+W)", "SUBMERGED\n2(L+W)D"]
    vals = [geom["dV_full_height_m3_s"], geom["dV_submerged_full_perim_m3_s"]]
    bars = ax.bar(labels, vals, color=["tab:blue", "tab:orange"])
    for b, val in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, val, f"{val:.4f}", ha="center",
                va="bottom", fontsize=8)
    ax.set_ylabel("dV_lateral/dt [m³/s]")
    ax.set_title(f"Fig 3. Lateral volume-loss rate (m_l=3.008e-6 m/s)\n"
                 f"ratio submerged/full-height = {geom['vol_ratio_sub_over_full']:.3f}")
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig03_full_vs_submerged.png")
    plt.close(fig)

    # fig04: size sensitivity (melt rate vs L) + fractional loss
    Ls = np.array([10.0, 50.0, 100.0, 200.0, 300.0])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for v in ("LEGACY_FULL_HEIGHT", "BULK_FORCED", "BIGG1997", "BIGG_PLUS_BUOY"):
        vals = [variant_melt(3.0, 0.1, L, 88.5)[v] for L in Ls]
        axes[0].plot(Ls, vals, "-o", ms=3, label=v)
    axes[0].set_xlabel("L [m]")
    axes[0].set_ylabel("m_lateral [m/day]")
    axes[0].set_title("Fig 4a. Melt rate vs L (dT=3 K, U=0.1 m/s)")
    axes[0].legend(fontsize=7)
    axes[0].grid(alpha=0.3)
    for v in ("LEGACY_FULL_HEIGHT", "BIGG1997"):
        vals = []
        for L in Ls:
            m_s = m_day_to_m_s(variant_melt(3.0, 0.1, L, 88.5)[v])
            W = H = L
            M0 = RHO_ICE * L * W * H
            frac = RHO_ICE * lateral_area_full_height(L, W, H) * m_s * SEC_PER_DAY / M0
            vals.append(frac)
        axes[1].plot(Ls, vals, "-o", ms=3, label=v)
    axes[1].set_xlabel("L [m]")
    axes[1].set_ylabel("fractional lateral mass loss [day⁻¹]")
    axes[1].set_title("Fig 4b. Fractional loss vs L (cube)")
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    fig.savefig(PLOTS / "fig04_size_sensitivity.png")
    plt.close(fig)

    # fig05: TEST_11 lateral melt time series
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for v in ("LEGACY_FULL_HEIGHT", "LEGACY_SUBMERGED", "BULK_FORCED",
              "BIGG1997", "BIGG_PLUS_BUOY", "FITZMAURICE_PLUME"):
        ax.plot(df["day"], m_s_to_m_day(replay_rows[v]["ml"]), lw=1.2, label=v)
    ax.set_xlabel("day (2020-01-01 + d)")
    ax.set_ylabel("m_lateral [m/day]")
    ax.set_title("Fig 5. 30-day TEST_11: lateral melt rate by variant")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig05_test11_lateral_timeseries.png")
    plt.close(fig)

    # fig06: TEST_11 mass(t)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for v in VARIANTS:
        ax.plot(df["day"], replay_rows[v]["M"] / M_TONNE, lw=1.4, label=v)
    ax.set_xlabel("day")
    ax.set_ylabel("mass [Mt]")
    ax.set_title("Fig 6. 30-day TEST_11: mass evolution by variant")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig06_test11_mass.png")
    plt.close(fig)

    # fig07: geometry L/W/H/D
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for j, (var, ylab) in enumerate([("L", "L [m]"), ("W", "W [m]"),
                                     ("H", "H [m]"), ("D", "D [m]")]):
        ax = axes[j // 2][j % 2]
        for v in VARIANTS:
            if var == "D":
                val = replay_rows[v]["H"] * RHO_ICE / RHO_WATER
            else:
                val = replay_rows[v][var]
            ax.plot(df["day"], val, lw=1.2, label=v)
        ax.set_xlabel("day")
        ax.set_ylabel(ylab)
        ax.set_title(f"Fig 7. {var}(t)")
        ax.legend(fontsize=6)
        ax.grid(alpha=0.3)
    fig.savefig(PLOTS / "fig07_test11_geometry.png")
    plt.close(fig)

    # fig08: mass-budget contribution (stacked)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    comps = ["lateral", "basal", "surface", "vapor"]
    bottom = np.zeros(len(replay))
    for c in comps:
        ax.bar(replay["variant"], replay[c + "_pct"], bottom=bottom, label=c)
        bottom += replay[c + "_pct"].to_numpy()
    ax.set_ylabel("mass-loss contribution [%]")
    ax.set_title("Fig 8. 30-day mass budget by variant")
    ax.legend()
    ax.tick_params(axis="x", rotation=20)
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig08_mass_budget.png")
    plt.close(fig)

    # fig09: relative difference research/baseline - 1
    base = replay[replay["variant"] == "LEGACY_FULL_HEIGHT"].iloc[0]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    rel_mass = replay["dM_pct"] / base["dM_pct"] - 1.0
    rel_lat = replay["lateral_pct"] / base["lateral_pct"] - 1.0
    x = np.arange(len(replay))
    ax.bar(x - 0.2, rel_mass, 0.4, label="relative dM (vs LEGACY_FULL_HEIGHT)")
    ax.bar(x + 0.2, rel_lat, 0.4, label="relative lateral share")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(replay["variant"], rotation=20)
    ax.set_ylabel("research / baseline - 1")
    ax.set_title("Fig 9. Relative difference vs production baseline")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig09_relative_diff.png")
    plt.close(fig)

    # fig10: model vs literature ranges
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = ["LEGACY\n(TEST_11)", "BULK\n(TEST_11 U)", "BIGG\n(TEST_11 U)",
             "BIGG+BUOY\n(TEST_11 U)", "lit: side max\n(C&S 2023)",
             "lit: Sermilik\n(F2017)"]
    vals = [replay.loc[replay.variant == "LEGACY_FULL_HEIGHT", "ml_mean_m_day"].iloc[0],
            replay.loc[replay.variant == "BULK_FORCED", "ml_mean_m_day"].iloc[0],
            replay.loc[replay.variant == "BIGG1997", "ml_mean_m_day"].iloc[0],
            replay.loc[replay.variant == "BIGG_PLUS_BUOY", "ml_mean_m_day"].iloc[0],
            0.2, 0.08]
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red", "grey", "grey"]
    bars = ax.bar(names, vals, color=colors)
    for b, val in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, val, f"{val:.3f}", ha="center",
                va="bottom", fontsize=7)
    ax.set_ylabel("side melt [m/day]")
    ax.set_title("Fig 10. Model parameterizations vs literature ranges")
    ax.grid(alpha=0.3, axis="y")
    fig.savefig(PLOTS / "fig10_literature_ranges.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    log = [f"# Stage 10.18A analysis log — {datetime.now(UTC).isoformat()}",
           f"baseline trajectory: {TRAJ_30}"]

    df = load_traj(TRAJ_30)
    log.append(f"trajectory rows: {len(df)}")

    baseline = baseline_table()
    baseline.to_csv(OUT / "baseline_results.csv", index=False)

    sens = sensitivity_matrix()
    sens.to_csv(OUT / "sensitivity_matrix.csv", index=False)

    par = parameterization_comparison()
    par.to_csv(OUT / "parameterization_comparison.csv", index=False)

    geom = geometry_comparison()
    pd.DataFrame([geom]).to_csv(OUT / "geometry_comparison.csv", index=False)

    replay, replay_rows = replay_test11(df)
    replay.to_csv(OUT / "test11_comparison.csv", index=False)

    lit = literature_comparison()
    lit.to_csv(OUT / "literature_comparison.csv", index=False)

    sc = scalings(sens)

    make_figures(baseline, sens, geom, replay, replay_rows, df, lit)

    equivalent_u = None
    target_gamma = RHO_ICE * LATENT_HEAT * C_LATERAL  # W/(m2 K) implied by C_LATERAL
    for u_guess in np.logspace(-3, 1.5, 2000):
        g = side_heat_transfer_coefficient(u_guess, geom["D_m"])
        if g >= target_gamma:
            equivalent_u = float(u_guess)
            break

    summary = {
        "stage": "10.18A",
        "generated_utc": datetime.now(UTC).isoformat(),
        "baseline_trajectory": str(TRAJ_30),
        "production_physics_changed": False,
        "C_LATERAL_m_per_s_K": C_LATERAL,
        "legacy_ml_m_day_at_3K": m_s_to_m_day(legacy_lateral_melt_rate(3.0)),
        "recovered_deltaT_D_degC": float(davg_from_ml(
            np.array([0.259892]))[0]),
        "geometry_comparison": geom,
        "scalings": sc,
        "equivalent_u_for_legacy_constant_m_s": equivalent_u,
        "implied_heat_transfer_coefficient_W_m2_K": target_gamma,
        "test11_replay": replay.to_dict("records"),
    }
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    log.append(f"production physics changed: False")
    log.append(f"equivalent U for legacy constant: {equivalent_u} m/s")
    (OUT / "reproducibility.log").write_text("\n".join(log) + "\n")

    print(json.dumps(summary, indent=2, default=str))
    print(f"\nfigures: {len(list(PLOTS.glob('fig*.png')))}")
    print("Stage 10.18A analysis complete.")


if __name__ == "__main__":
    main()