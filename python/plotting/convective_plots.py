"""Stage 4.3 convective-adjustment root-cause diagnostic figures.

Figures produced (all PNG, dpi=150) into python/plotting/figures/convective/:
  guard_hits_evolution.png      - full guard hits vs model day (from daily CSV)
  guard_nmix_kproblem.png       - nmix/iteration and k_problem distribution
  guard_vs_scalars.png          - guard hits vs EUU and RO_max (2-panel scatter)
  residual_inversion.png        - histogram of resid_inv (shows 2^-23 quantization)
  representative_profiles.png   - T/S/RO profiles at typical + max-nmix columns

Python only READS model output and visualizes it; no physics.
"""

import argparse
import pathlib

import matplotlib

matplotlib.use("Agg")  # pylint: disable=wrong-import-position
import matplotlib.pyplot as plt  # pylint: disable=wrong-import-position
import numpy as np  # pylint: disable=wrong-import-position
import pandas as pd  # pylint: disable=wrong-import-position
import xarray as xr  # pylint: disable=wrong-import-position

import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "analysis"))
from units import temperature_k_to_c, density_anomaly_kgm3_to_gcm3

DEFAULT_EVENTS = "data/output/convective_guard_events.csv"
DEFAULT_DIAG = "data/output/daily_diagnostics.csv"
DEFAULT_PROF = "data/output/results_day_[0-9][0-9].nc"
DEFAULT_OUTDIR = "python/plotting/figures/convective"

DPI = 150

REPR_DAYS = [1, 5, 10, 15, 20, 25, 30]


def load_column(path, i, j):
    """T/S/RO/depth at column (i,j) - NetCDF x<->i (axis2), y<->j (axis1).

    NetCDF canonical units: T in K, RO anomaly in kg m-3. Convert to degC /
    g cm-3 for presentation.
    """
    ds = xr.open_dataset(path)
    ki = int(ds["water_column_levels"].values[j - 1, i - 1])
    depth = ds["depth"].values[:ki]
    t = temperature_k_to_c(ds["temperature"].values[:ki, j - 1, i - 1])
    s = ds["salinity_mass_fraction"].values[:ki, j - 1, i - 1]
    ro = density_anomaly_kgm3_to_gcm3(ds["density_anomaly"].values[:ki, j - 1, i - 1])
    ds.close()
    return depth, t, s, ro


def plot_guard_hits_evolution(daily, outdir):
    """Plot per-day convective guard-hit counts."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(daily["day"], daily["ca_guard_hits"], marker="o", ms=3, color="crimson")
    ax.set_xlabel("model day")
    ax.set_ylabel("guard hits")
    ax.set_title("Convective-adjustment guard hits per day (super-linear growth)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "guard_hits_evolution.png", dpi=DPI)
    plt.close(fig)


def plot_guard_nmix_kproblem(events, outdir):
    """Plot mixings-per-iteration and problem-interface level histograms."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(events["nmix"] / 1001, bins=40, color="steelblue")
    axes[0].set_xlabel("nmix per iteration (mean ~2.03)")
    axes[0].set_ylabel("events")
    axes[0].set_title("Mixings per outer iteration at guard")
    axes[0].grid(alpha=0.3)

    kp = events["k_problem"].value_counts().sort_index()
    axes[1].bar(kp.index.astype(str), kp.values, color="indianred")
    axes[1].set_xlabel("problem interface level k")
    axes[1].set_ylabel("events")
    axes[1].set_title("Residual-inversion interface at guard")
    axes[1].grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(outdir / "guard_nmix_kproblem.png", dpi=DPI)
    plt.close(fig)


def plot_guard_vs_scalars(daily, outdir):
    """Plot guard hits against kinetic energy and density anomaly."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, var, lab in [
        (axes[0], "euu", "EUU (cm2/s2)"),
        (axes[1], "ro_max", "RO max (g/cm3)"),
    ]:
        ax.scatter(daily[var], daily["ca_guard_hits"], s=18, color="darkgreen")
        ax.set_xlabel(lab)
        ax.set_ylabel("guard hits")
        ax.grid(alpha=0.3)
    axes[0].set_title("Guard hits vs kinetic energy")
    axes[1].set_title("Guard hits vs max density anomaly")
    fig.tight_layout()
    fig.savefig(outdir / "guard_vs_scalars.png", dpi=DPI)
    plt.close(fig)


def plot_residual_inversion(events, outdir):
    """Plot residual-inversion histogram in float32 ulp units."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ulp = 2**-23
    vals = events["resid_inv"].values / ulp  # units of ulp
    ax.hist(vals, bins=np.arange(0.5, 3.0, 0.25), color="rebeccapurple")
    ax.axvline(
        0.9e-7 / ulp,
        color="crimson",
        ls="--",
        label=f"threshold 0.9e-7 = {0.9e-7 / ulp:.3f} ulp",
    )
    ax.set_xlabel("residual inversion (units of float32 ulp = 2^-23)")
    ax.set_ylabel("events")
    ax.set_title("All guard events end at the 1-ulp quantization level")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(outdir / "residual_inversion.png", dpi=DPI)
    plt.close(fig)


# pylint: disable=too-many-locals
def plot_representative_profiles(events, prof_glob, outdir):
    """T/S/RO profiles at a typical guard column for representative days."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 6))
    cmap = plt.get_cmap("viridis")
    norm = plt.Normalize(0, max(REPR_DAYS))

    n = 0
    for day in REPR_DAYS:
        ev = events[events["day"] == day]
        if len(ev) == 0:
            continue
        f = pathlib.Path(prof_glob.replace("[0-9][0-9]", f"{day:02d}"))
        if not f.exists():
            continue
        i = ev["i"].iloc[-1]
        j = ev["j"].iloc[-1]
        depth, t, s, ro = load_column(f, i, j)
        c = cmap(norm(day))
        axes[0].plot(t, depth, color=c, label=f"day {day}")
        axes[1].plot(s, depth, color=c, label=f"day {day}")
        axes[2].plot(ro, depth, color=c, label=f"day {day}")
        n += 1

    for ax, xlab in [
        (axes[0], "T (deg C)"),
        (axes[1], "S (mass frac)"),
        (axes[2], "RO anomaly (g/cm3)"),
    ]:
        ax.set_ylim(0, 100)
        ax.invert_yaxis()
        ax.set_xlabel(xlab)
        ax.set_ylabel("depth (m)")
        ax.grid(alpha=0.3)
    axes[0].set_title("Typical guard-column T profile")
    axes[1].set_title("Typical guard-column S profile")
    axes[2].set_title("Typical guard-column RO profile")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=6, fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(outdir / "representative_profiles.png", dpi=DPI)
    plt.close(fig)


def main():
    """Generate all Stage 4.3 convective guard-cycling figures."""
    parser = argparse.ArgumentParser(
        description="Stage 4.3 convective guard-cycling diagnostic figures."
    )
    parser.add_argument("--events", default=DEFAULT_EVENTS)
    parser.add_argument("--daily", default=DEFAULT_DIAG)
    parser.add_argument("--profiles", default=DEFAULT_PROF)
    parser.add_argument("--outdir", default=DEFAULT_OUTDIR)
    args = parser.parse_args()

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    events = pd.read_csv(args.events)
    daily = pd.read_csv(args.daily)

    plot_guard_hits_evolution(daily, outdir)
    plot_guard_nmix_kproblem(events, outdir)
    plot_guard_vs_scalars(daily, outdir)
    plot_residual_inversion(events, outdir)
    plot_representative_profiles(events, args.profiles, outdir)

    print(f"Convective figures written to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
