#!/usr/bin/env python3
"""
Stage 9.4B Diagnostic Plots Generator
Generates all required plots for Stage 9.4B documentation.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

# Output directory
PLOT_DIR = "docs/wiki/plots_stage9.4b"
os.makedirs(PLOT_DIR, exist_ok=True)


# Load data
def load_trajectory():
    """Load TEST_11 trajectory CSV"""
    csv_path = "data/output/diagnostics/stage9.3/test11_trajectory.csv"
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return None


def load_force_budget():
    """Load force budget CSV"""
    csv_path = "data/output/diagnostics/stage9.3/force_budget.csv"
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return None


def load_coriolis_convergence():
    """Load coriolis convergence data (from test output)"""
    # We'll generate this from the test results
    return None


# ============================================================
# Figure 1: Coriolis period error vs timestep
# ============================================================
def plot_figure1():
    """Coriolis period error vs timestep"""
    # Data from Coriolis convergence test
    dt_vals = np.array([3600, 1800, 900, 600, 300, 120, 60])
    period_error = np.array([3177, 982, 292, 140, 32, 8, 7])  # percent

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.loglog(dt_vals, period_error, "o-", linewidth=2, markersize=8)
    ax.set_xlabel("Timestep dt [s]")
    ax.set_ylabel("Relative period error [%]")
    ax.set_title("Figure 1: Coriolis period error vs timestep (75°N)")
    ax.grid(True, which="both", ls="--", alpha=0.5)
    ax.axhline(y=8, color="r", linestyle="--", label="dt=3600s error (8%)")
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig1_coriolis_period_error.png"), dpi=150)
    plt.close()
    print("Figure 1 saved")


# ============================================================
# Figure 2: Coriolis phase/trajectory error vs timestep
# ============================================================
def plot_figure2():
    """Coriolis phase/trajectory error vs timestep"""
    dt_vals = np.array([3600, 1800, 900, 600, 300, 120, 60])
    phase_error = np.array([131, 36, 9, 4, 1, 0, 0])  # degrees

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.loglog(dt_vals, phase_error, "o-", linewidth=2, markersize=8, color="orange")
    ax.set_xlabel("Timestep dt [s]")
    ax.set_ylabel("Phase error over 5 periods [deg]")
    ax.set_title("Figure 2: Coriolis phase/trajectory error vs timestep")
    ax.grid(True, which="both", ls="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig2_coriolis_phase_error.png"), dpi=150)
    plt.close()
    print("Figure 2 saved")


# ============================================================
# Figure 3: Force-budget components vs time
# ============================================================
def plot_figure3():
    """Force-budget components vs time"""
    df = load_force_budget()
    if df is None:
        print("Force budget data not found")
        return

    time_h = df["time_h"]

    fig, axes = plt.subplots(2, 1, figsize=(10, 10), sharex=True)

    # Fx components
    ax = axes[0]
    ax.plot(time_h, df["fx_wind"], label="Wind", linewidth=1.5)
    ax.plot(time_h, df["fx_water"], label="Water", linewidth=1.5)
    ax.plot(time_h, df["fx_cor"], label="Coriolis", linewidth=1.5)
    ax.plot(
        time_h,
        df["fx_total"],
        label="Total",
        linewidth=2,
        linestyle="--",
        color="black",
    )
    ax.set_ylabel("Force Fx [N]")
    ax.set_title("Figure 3a: Force budget components Fx vs time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Fy components
    ax = axes[1]
    ax.plot(time_h, df["fy_wind"], label="Wind", linewidth=1.5)
    ax.plot(time_h, df["fy_water"], label="Water", linewidth=1.5)
    ax.plot(time_h, df["fy_cor"], label="Coriolis", linewidth=1.5)
    ax.plot(
        time_h,
        df["fy_total"],
        label="Total",
        linewidth=2,
        linestyle="--",
        color="black",
    )
    ax.set_xlabel("Time [hours]")
    ax.set_ylabel("Force Fy [N]")
    ax.set_title("Figure 3b: Force budget components Fy vs time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig3_force_budget.png"), dpi=150)
    plt.close()
    print("Figure 3 saved")


# ============================================================
# Figure 4: Wind-drift ratio vs CD_AIR
# ============================================================
def plot_figure4():
    """Wind-drift ratio vs CD_AIR"""
    # Data from wind drift sensitivity test
    cd_air = np.array([0.5e-3, 1.0e-3, 1.3e-3, 2.0e-3])
    # Case A (Coriolis OFF)
    drift_a = np.array([0.97, 1.36, 1.55, 1.92])
    # Case B (Coriolis ON)
    drift_b = np.array([0.03, 0.06, 0.08, 0.12])

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(
        cd_air * 1e3, drift_a, "o-", label="Coriolis OFF", linewidth=2, markersize=8
    )
    ax.plot(cd_air * 1e3, drift_b, "s-", label="Coriolis ON", linewidth=2, markersize=8)
    ax.axhline(y=1, color="r", linestyle="--", label="Literature 1-2%")
    ax.axhline(y=2, color="r", linestyle="--")
    ax.set_xlabel("CD_AIR [x10⁻³]")
    ax.set_ylabel("Drift ratio [%]")
    ax.set_title("Figure 4: Wind-drift ratio vs CD_AIR (10 m/s wind)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig4_drift_vs_cd_air.png"), dpi=150)
    plt.close()
    print("Figure 4 saved")


# ============================================================
# Figure 5: Wind-drift ratio vs CD_water
# ============================================================
def plot_figure5():
    """Wind-drift ratio vs CD_water"""
    cd_water = np.array([1.0e-3, 2.0e-3, 3.0e-3, 4.0e-3])
    # Case C (Coriolis OFF, CD_AIR=1.3e-3)
    drift_c = np.array([2.18, 1.55, 1.27, 1.10])
    # Case D (Coriolis ON, CD_AIR=1.3e-3)
    drift_d = np.array([0.08, 0.08, 0.08, 0.08])

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(
        cd_water * 1e3, drift_c, "o-", label="Coriolis OFF", linewidth=2, markersize=8
    )
    ax.plot(
        cd_water * 1e3, drift_d, "s-", label="Coriolis ON", linewidth=2, markersize=8
    )
    ax.axhline(y=1, color="r", linestyle="--", label="Literature 1-2%")
    ax.axhline(y=2, color="r", linestyle="--")
    ax.set_xlabel("CD_water [x10⁻³]")
    ax.set_ylabel("Drift ratio [%]")
    ax.set_title("Figure 5: Wind-drift ratio vs CD_water (CD_AIR=1.3e-3)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig5_drift_vs_cd_water.png"), dpi=150)
    plt.close()
    print("Figure 5 saved")


# ============================================================
# Figure 6: Method A vs Method B water-drag force
# ============================================================
def plot_figure6():
    """Method A vs Method B water-drag force"""
    cases = [
        "Uniform\nCoriolis OFF",
        "Uniform\nCoriolis ON",
        "Sheared\nCoriolis OFF",
        "Sheared\nCoriolis ON",
        "Wind only\nCoriolis OFF",
        "Wind only\nCoriolis ON",
    ]
    method_a = [0.0265, 0.00063, 0.0579, 0.00155, 0.298, 0.0081]
    method_b = [0.0651, 0.00315, 0.0875, 0.00489, 0.155, 0.0081]
    ratio = np.array(method_b) / np.array(method_a)

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(cases))
    width = 0.35
    ax.bar(
        x - width / 2, method_a, width, label="Method A (side areas)", color="skyblue"
    )
    ax.bar(
        x + width / 2,
        method_b,
        width,
        label="Method B (total wetted)",
        color="lightcoral",
    )
    ax.set_ylabel("Terminal speed [m/s]")
    ax.set_title("Figure 6: Method A vs Method B water-drag terminal speed")
    ax.set_xticks(x)
    ax.set_xticklabels(cases, rotation=15, ha="right")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    # Add ratio annotations
    for i, r in enumerate(ratio):
        ax.annotate(
            f"×{r:.2f}",
            xy=(i, max(method_a[i], method_b[i])),
            ha="center",
            va="bottom",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig6_method_a_vs_b.png"), dpi=150)
    plt.close()
    print("Figure 6 saved")


# ============================================================
# Figure 7: TEST_11 trajectory
# ============================================================
def plot_figure7():
    """TEST_11 trajectory"""
    df = load_trajectory()
    if df is None:
        print("Trajectory data not found")
        return

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(df["lon_deg"], df["lat_deg"], "b-", linewidth=1.5)
    ax.plot(
        df["lon_deg"].iloc[0], df["lat_deg"].iloc[0], "go", markersize=10, label="Start"
    )
    ax.plot(
        df["lon_deg"].iloc[-1], df["lat_deg"].iloc[-1], "ro", markersize=10, label="End"
    )
    ax.set_xlabel("Longitude [°]")
    ax.set_ylabel("Latitude [°]")
    ax.set_title("Figure 7: TEST_11 trajectory (30 days, moving iceberg)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig7_test11_trajectory.png"), dpi=150)
    plt.close()
    print("Figure 7 saved")


# ============================================================
# Figure 8: TEST_11 forcing evolution
# ============================================================
def plot_figure8():
    """TEST_11 forcing evolution"""
    df = load_trajectory()
    if df is None:
        print("Trajectory data not found")
        return

    fig, axes = plt.subplots(3, 2, figsize=(12, 12), sharex=True)
    axes = axes.flatten()

    time_h = df["time_h"]

    # u10, v10
    ax = axes[0]
    ax.plot(time_h, df["u_ms"] * 10, label="Iceberg u", linewidth=1)
    # We don't have ERA5 u10/v10 in trajectory CSV, but we can plot iceberg velocity
    ax.plot(time_h, df["u_ms"], label="Iceberg u", linewidth=1.5)
    ax.plot(time_h, df["v_ms"], label="Iceberg v", linewidth=1.5)
    ax.set_ylabel("Velocity [m/s]")
    ax.set_title("Figure 8a: Iceberg velocity components")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Melt rates
    ax = axes[1]
    ax.plot(time_h, df["mb_mday"], label="Basal", linewidth=1.5)
    ax.plot(time_h, df["ml_mday"], label="Lateral", linewidth=1.5)
    ax.plot(time_h, df["ms_mday"], label="Surface", linewidth=1.5)
    ax.set_ylabel("Melt rate [m/day]")
    ax.set_title("Figure 8b: Melt rates")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Geometry
    ax = axes[2]
    ax.plot(time_h, df["L_m"], label="Length", linewidth=1.5)
    ax.plot(time_h, df["W_m"], label="Width", linewidth=1.5)
    ax.plot(time_h, df["H_m"], label="Height", linewidth=1.5)
    ax.set_ylabel("Geometry [m]")
    ax.set_title("Figure 8c: Iceberg geometry")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Mass
    ax = axes[3]
    ax.plot(time_h, df["M_kg"] / 1e8, "k-", linewidth=1.5)
    ax.set_ylabel("Mass [10⁸ kg]")
    ax.set_title("Figure 8d: Iceberg mass")
    ax.grid(True, alpha=0.3)

    # Position
    ax = axes[4]
    ax.plot(time_h, df["lat_deg"], label="Latitude", linewidth=1.5)
    ax.plot(time_h, df["lon_deg"], label="Longitude", linewidth=1.5)
    ax.set_ylabel("Position [°]")
    ax.set_title("Figure 8e: Iceberg position")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Speed
    ax = axes[5]
    speed = np.sqrt(df["u_ms"] ** 2 + df["v_ms"] ** 2)
    ax.plot(time_h, speed, "k-", linewidth=1.5)
    ax.set_ylabel("Speed [m/s]")
    ax.set_xlabel("Time [hours]")
    ax.set_title("Figure 8f: Iceberg speed")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig8_test11_evolution.png"), dpi=150)
    plt.close()
    print("Figure 8 saved")


# ============================================================
# Figure 9: Coriolis parameter vs iceberg latitude
# ============================================================
def plot_figure9():
    """Coriolis parameter vs iceberg latitude"""
    df = load_trajectory()
    if df is None:
        print("Trajectory data not found")
        return

    lat = df["lat_deg"]
    f = 2 * 7.2921150e-5 * np.sin(np.radians(lat))

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(lat, f * 1e4, "b-", linewidth=2)
    ax.scatter(lat.iloc[0], f[0] * 1e4, color="green", s=100, zorder=5, label="Start")
    ax.scatter(
        lat.iloc[len(lat) - 1],
        f[len(f) - 1] * 1e4,
        color="red",
        s=100,
        zorder=5,
        label="End",
    )
    ax.set_xlabel("Latitude [°]")
    ax.set_ylabel("Coriolis parameter f [×10⁻⁴ s⁻¹]")
    ax.set_title("Figure 9: Coriolis parameter vs iceberg latitude")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "fig9_coriolis_vs_lat.png"), dpi=150)
    plt.close()
    print("Figure 9 saved")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("Generating Stage 9.4B diagnostic plots...")
    print(f"Output directory: {PLOT_DIR}")

    plot_figure1()
    plot_figure2()
    plot_figure3()
    plot_figure4()
    plot_figure5()
    plot_figure6()
    plot_figure7()
    plot_figure8()
    plot_figure9()

    print(f"\nAll plots saved to {PLOT_DIR}")
    print("Done!")
