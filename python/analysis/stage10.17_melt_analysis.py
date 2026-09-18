# ==============================================================================
# Stage 10.17 — Iceberg Melt and Thermodynamic Budget Audit: Analysis
# ==============================================================================
# Reads:
#   data/output/diagnostics/stage9.3/test11_trajectory.csv   (extended 30-day TEST_11)
#   data/output/stage10.17/test11_90day_stage10.17_trajectory.csv
#   data/output/stage10.17/*.csv (synthetic experiments from the Fortran test)
# Writes (all gitignored):
#   data/output/stage10.17/plots/fig*.png          (12 figures)
#   data/output/stage10.17/stage10.17_summary.json
#   data/output/stage10.17/mass_geometry_budget.csv
#   data/output/stage10.17/melt_component_budget.csv
#   data/output/stage10.17/thermal_budget.csv
#   data/output/stage10.17/test11_stage10.17_trajectory.csv (copy, extended)
#   data/output/stage10.17/reproducibility.log
#
# Conventions: time in days (day 1 = first step, 2020-01-01 + d days);
# melt rates in m/day; mass in Mt (1e6 kg); SI elsewhere.
# ==============================================================================

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model")
OUT = REPO / "data" / "output" / "stage10.17"
PLOTS = OUT / "plots"
TRAJ_30 = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"
TRAJ_90 = OUT / "test11_90day_stage10.17_trajectory.csv"

RHO_ICE = 910.0
RHO_WATER = 1028.0
DT_S = 3600.0
SECONDS_PER_DAY = 86400.0

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight"})


def load_traj(path: Path) -> pd.DataFrame:
    """TEST_11 CSV: comma header + Fortran fixed-width whitespace rows."""
    with open(path) as f:
        header = f.readline().strip().split(",")
    df = pd.read_csv(path, sep=r"\s+", skiprows=1, names=header)
    df["day"] = (df["step"].astype(float) - 1.0) / 24.0  # day 0 = initial state
    return df


def component_losses(df: pd.DataFrame) -> dict:
    """Per-step component mass losses [kg] with the production update convention
    (pre-melt geometry approximated by previous step geometry)."""
    L = df["L_m"].values
    W = df["W_m"].values
    H = df["H_m"].values
    mb = (df["mb_mday"] / SECONDS_PER_DAY).values
    ml = (df["ml_mday"] / SECONDS_PER_DAY).values
    ms = (df["ms_mday"] / SECONDS_PER_DAY).values
    mv = df["m_vapor_kgm2s"].values if "m_vapor_kgm2s" in df.columns else np.zeros(len(df))
    dmb = RHO_ICE * L * W * DT_S * mb
    dml = RHO_ICE * (H * W + L * H) * DT_S * ml
    dms = RHO_ICE * L * W * DT_S * ms
    dmv = -L * W * DT_S * mv  # positive = sublimation loss
    return {"basal": dmb, "lateral": dml, "surface": dms, "vapor": dmv}


def budget_table(df: pd.DataFrame) -> pd.DataFrame:
    """mass_geometry_budget.csv: per-step reported vs reconstructed values."""
    comp = component_losses(df)
    v_geom = df["L_m"] * df["W_m"] * df["H_m"]
    m_geom = RHO_ICE * v_geom
    m_rep = df["M_kg"].values
    d_m_obs = np.concatenate(([m_rep[0] - m_rep[1]], -np.diff(m_rep)))
    d_m_comp = comp["basal"] + comp["lateral"] + comp["surface"] + comp["vapor"]
    return pd.DataFrame(
        {
            "step": df["step"],
            "day": df["day"],
            "M_reported_kg": m_rep,
            "M_geometry_kg": m_geom,
            "rel_diff_M": np.abs(m_rep - m_geom) / m_rep,
            "dM_observed_kg": d_m_obs,
            "dM_components_kg": d_m_comp,
            "dM_residual_kg": d_m_obs - d_m_comp,
        }
    )


def component_budget(df: pd.DataFrame) -> pd.DataFrame:
    """melt_component_budget.csv: aggregate per-component budget."""
    comp = component_losses(df)
    total = sum(comp.values())
    rows = []
    for name, arr in comp.items():
        rows.append(
            {
                "component": name,
                "mass_loss_Mt": arr.sum() / 1e6,
                "fraction_of_total": arr.sum() / total.sum(),
                "rate_mean_mday": (
                    (arr / (RHO_ICE * (df["L_m"] * df["W_m"]).values * DT_S) * SECONDS_PER_DAY).mean()
                    if name != "lateral"
                    else (arr / (RHO_ICE * ((df["H_m"] * df["W_m"] + df["L_m"] * df["H_m"]).values) * DT_S) * SECONDS_PER_DAY).mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def savefig(fig, name: str):
    fig.savefig(PLOTS / name)
    plt.close(fig)


def make_plots(traj30: pd.DataFrame, traj90: pd.DataFrame, budget: pd.DataFrame, synth: dict):
    # 1. mass_timeseries
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(traj30["day"], traj30["M_kg"] / 1e6, "-", label="30-day TEST_11", lw=1.6)
    ax.plot(traj90["day"], traj90["M_kg"] / 1e6, "--", label="90-day diagnostic", lw=1.4, alpha=0.85)
    ax.set_xlabel("time [day] (day 0 = 2020-01-01)")
    ax.set_ylabel("mass [Mt]")
    ax.set_title("Iceberg mass evolution")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig, "mass_timeseries.png")

    # 2. geometry_timeseries
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(traj30["day"], traj30["L_m"], "-", label="L (30d)", lw=1.4)
    ax.plot(traj30["day"], traj30["W_m"], "-", label="W (30d)", lw=1.4)
    ax.plot(traj30["day"], traj30["H_m"], "-", label="H (30d)", lw=1.4)
    ax.plot(traj90["day"], traj90["L_m"], "--", label="L (90d)", lw=1.2, alpha=0.8)
    ax.plot(traj90["day"], traj90["H_m"], "--", label="H (90d)", lw=1.2, alpha=0.8)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("dimension [m]")
    ax.set_title("Geometry evolution (L = W under isotropic lateral erosion)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    savefig(fig, "geometry_timeseries.png")

    # 3. melt_components_timeseries
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(traj30["day"], traj30["mb_mday"], "-", label="basal", lw=1.2)
    ax.plot(traj30["day"], traj30["ml_mday"], "-", label="lateral", lw=1.2)
    ax.plot(traj30["day"], traj30["ms_mday"], "-", label="surface", lw=1.2)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Melt components (30-day real-forcing run)")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig, "melt_components_timeseries.png")

    # 4. cumulative_mass_loss
    comp = component_losses(traj30)
    cum = pd.DataFrame({k: np.cumsum(v) / 1e6 for k, v in comp.items()}, index=traj30["day"])
    cum["total"] = cum.sum(axis=1)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for col in ["basal", "lateral", "surface", "vapor", "total"]:
        ax.plot(cum.index, cum[col], label=col, lw=1.4)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("cumulative mass loss [Mt]")
    ax.set_title("Cumulative component mass loss (30-day run)")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig, "cumulative_mass_loss.png")

    # 5. component_mass_loss (bar)
    agg = component_budget(traj30)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(agg["component"], agg["mass_loss_Mt"], color=["#4C72B0", "#DD8452", "#55A868", "#C44E52"])
    ax.set_ylabel("mass loss [Mt]")
    ax.set_title("Component mass loss (30-day run, total %.1f Mt)" % agg["mass_loss_Mt"].sum())
    ax.grid(axis="y", alpha=0.3)
    savefig(fig, "component_mass_loss.png")

    # 6. mass_geometry_consistency
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(traj30["day"], traj30["M_kg"] / 1e6, "-", label="reported M", lw=1.6)
    ax.plot(traj30["day"], budget["M_geometry_kg"] / 1e6, "--", label="rho_ice*L*W*H", lw=1.4)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("mass [Mt]")
    ax.set_title("Mass-consistency: reported vs reconstructed from geometry")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig, "mass_geometry_consistency.png")

    # 7. thermal_forcing_timeseries
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(traj30["day"], traj30["t_draft_degC"], "-", label="T at draft", lw=1.2)
    ax.plot(traj30["day"], traj30["tf_draft_degC"], "-", label="Tf at draft", lw=1.2)
    ax.plot(traj30["day"], traj30["delta_t_ocean_degC"], "-", label="dT = T - Tf", lw=1.2)
    ax.plot(traj30["day"], traj30["t_surface_degC"], "-", label="T surface", lw=1.0, alpha=0.8)
    ax.plot(traj30["day"], traj30["t_ice_degC"], "-", label="T internal", lw=1.0, alpha=0.8)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("temperature [degC]")
    ax.set_title("Thermal forcing (30-day run)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    savefig(fig, "thermal_forcing_timeseries.png")

    # 8. relative_velocity_vs_melt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(traj30["u_rel_draft_ms"], traj30["mb_mday"], s=10, alpha=0.6, label="basal")
    ax.scatter(traj30["u_rel_draft_ms"], traj30["ml_mday"], s=10, alpha=0.6, label="lateral")
    ax.set_xlabel("relative water velocity at draft [m/s]")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Melt rate vs relative velocity (30-day run)")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig, "relative_velocity_vs_melt.png")

    # 9. temperature_vs_melt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(traj30["delta_t_ocean_degC"], traj30["mb_mday"], s=10, alpha=0.6, label="basal vs dT ocean")
    ax.scatter(traj30["delta_t_ocean_degC"], traj30["ml_mday"], s=10, alpha=0.6, label="lateral vs dT ocean")
    ax2 = ax.twinx()
    ax2.scatter(traj30["t_surface_degC"], traj30["ms_mday"], s=10, alpha=0.6, color="green", label="surface vs T surface")
    ax2.set_ylabel("surface melt [m/day]")
    ax.set_xlabel("ocean dT [degC] / surface T [degC]")
    ax.set_ylabel("ocean melt [m/day]")
    ax.set_title("Melt rate vs temperature (30-day run)")
    ax.legend(loc="upper left", fontsize=8)
    ax2.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.3)
    savefig(fig, "temperature_vs_melt.png")

    # 10. melt_budget_closure
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(traj30["day"], budget["dM_observed_kg"].cumsum() / 1e6, "-", label="observed dM (cumulative)", lw=1.6)
    ax.plot(traj30["day"], budget["dM_components_kg"].cumsum() / 1e6, "--", label="component sum (cumulative)", lw=1.4)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("mass [Mt]")
    ax.set_title("Budget closure: observed vs component-summed mass loss")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig, "melt_budget_closure.png")

    # 11. timestep_sensitivity (synthetic)
    ts = synth["timestep"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar([str(int(d)) for d in ts["dt_s"]], ts["dM_kg"] / 1e6, color="#4C72B0")
    ax.set_xlabel("time step [s]")
    ax.set_ylabel("mass loss over 1 simulated day [Mt]")
    ax.set_title("Timestep sensitivity (synthetic warm-water case)")
    ax.grid(axis="y", alpha=0.3)
    savefig(fig, "timestep_sensitivity.png")

    # 12. size_sensitivity (synthetic)
    sz = synth["size"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(sz["L_m"], sz["dM_frac_day"] * 100, "o-", label="fractional loss/day")
    ax.set_xlabel("iceberg size L [m]")
    ax.set_ylabel("fractional mass loss per day [%]")
    ax.set_title("Size sensitivity (synthetic warm-water case)")
    ax.legend()
    ax.grid(alpha=0.3)
    savefig(fig, "size_sensitivity.png")


def write_outputs(traj30: pd.DataFrame, budget: pd.DataFrame):
    # machine-readable outputs
    budget.to_csv(OUT / "mass_geometry_budget.csv", index=False)
    component_budget(traj30).to_csv(OUT / "melt_component_budget.csv", index=False)
    # thermal_budget.csv: surface energy terms per day (sampled daily)
    daily = traj30.iloc[::24].copy()
    daily["m_surface_x_rhoLf_Wm2"] = daily["ms_mday"] / SECONDS_PER_DAY * RHO_ICE * 334000.0
    daily.to_csv(OUT / "thermal_budget.csv", index=False)


def write_summary(traj30: pd.DataFrame, traj90: pd.DataFrame, budget: pd.DataFrame,
                  synth: dict, repro_lines: list):
    agg = component_budget(traj30)
    summary = {
        "stage": "10.17",
        "description": "Iceberg melt and thermodynamic budget audit",
        "trajectory_30d": {
            "rows": int(len(traj30)),
            "M0_Mt": float(traj30["M_kg"].iloc[0] / 1e6),
            "Mf_Mt": float(traj30["M_kg"].iloc[-1] / 1e6),
            "dM_Mt": float((traj30["M_kg"].iloc[0] - traj30["M_kg"].iloc[-1]) / 1e6),
            "dM_fraction": float((traj30["M_kg"].iloc[0] - traj30["M_kg"].iloc[-1]) / traj30["M_kg"].iloc[0]),
            "L_final_m": float(traj30["L_m"].iloc[-1]),
            "W_final_m": float(traj30["W_m"].iloc[-1]),
            "H_final_m": float(traj30["H_m"].iloc[-1]),
            "mb_mean_mday": float(traj30["mb_mday"].mean()),
            "ml_mean_mday": float(traj30["ml_mday"].mean()),
            "ms_mean_mday": float(traj30["ms_mday"].mean()),
            "delta_t_mean_degC": float(traj30["delta_t_ocean_degC"].mean()),
            "u_rel_max_ms": float(traj30["u_rel_draft_ms"].max()),
            "budget_model_err_rel": float(np.abs(budget["dM_observed_kg"].sum() - budget["dM_components_kg"].sum())
                                          / max(abs(budget["dM_observed_kg"].sum()), 1.0)),
        },
        "trajectory_90d": {
            "rows": int(len(traj90)),
            "M0_Mt": float(traj90["M_kg"].iloc[0] / 1e6),
            "Mf_Mt": float(traj90["M_kg"].iloc[-1] / 1e6),
            "dM_Mt": float((traj90["M_kg"].iloc[0] - traj90["M_kg"].iloc[-1]) / 1e6),
            "dM_fraction": float((traj90["M_kg"].iloc[0] - traj90["M_kg"].iloc[-1]) / traj90["M_kg"].iloc[0]),
            "L_final_m": float(traj90["L_m"].iloc[-1]),
            "H_final_m": float(traj90["H_m"].iloc[-1]),
        },
        "component_budget_Mt": {r["component"]: float(r["mass_loss_Mt"]) for _, r in agg.iterrows()},
        "component_fractions": {r["component"]: float(r["fraction_of_total"]) for _, r in agg.iterrows()},
        "max_mass_geometry_rel_diff": float(budget["rel_diff_M"].max()),
        "timestep_sensitivity": synth["timestep"].to_dict("records"),
        "size_sensitivity": synth["size"].to_dict("records"),
    }
    (OUT / "stage10.17_summary.json").write_text(json.dumps(summary, indent=2))
    (OUT / "reproducibility.log").write_text("\n".join(repro_lines) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    repro = [
        "# Stage 10.17 reproducibility log",
        f"# generated: {datetime.now(UTC).isoformat()}",
        "# commands:",
        "#   rm -rf build && fpm test --flag \"-I/usr/include\" iceberg_test_10p17_melt_budget",
        "#   fpm test --flag \"-I/usr/include\" iceberg_test_11_30day_offline",
        "#   fpm test --flag \"-I/usr/include\" iceberg_test_10p17_90day",
        "#   conda run -n iceberg-thermodynamic-model python python/analysis/stage10.17_melt_analysis.py",
    ]
    assert TRAJ_30.exists(), f"missing {TRAJ_30} (run TEST_11 first)"
    assert TRAJ_90.exists(), f"missing {TRAJ_90} (run 90-day test first)"

    traj30 = load_traj(TRAJ_30)
    traj90 = load_traj(TRAJ_90)
    budget = budget_table(traj30)

    # synthetic experiment tables (written by the Fortran test)
    def load_synth(name):
        p = OUT / name
        if not p.exists():
            return pd.DataFrame()
        return pd.read_csv(p)

    synth = {
        "timestep": load_synth("timestep_sensitivity.csv"),
        "size": load_synth("size_sensitivity.csv"),
        "velocity": load_synth("velocity_sensitivity.csv"),
        "temperature": load_synth("temperature_sensitivity.csv"),
        "experiments": load_synth("synthetic_melt_experiments.csv"),
    }

    make_plots(traj30, traj90, budget, synth)
    write_outputs(traj30, budget)
    write_summary(traj30, traj90, budget, synth, repro)

    # copy extended trajectory into the stage output dir
    shutil.copy(TRAJ_30, OUT / "test11_stage10.17_trajectory.csv")

    print(f"Stage 10.17 analysis complete: {PLOTS} ({len(list(PLOTS.glob('*.png')))} figures)")
    print(f"Summary: {OUT / 'stage10.17_summary.json'}")


if __name__ == "__main__":
    main()