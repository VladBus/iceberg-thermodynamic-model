#!/usr/bin/env python3
"""Stage 8.1 Energy Budget Analysis - Complete kinetic energy budget from daily diagnostics."""

import pandas as pd
import numpy as np
import json
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[2]


def analyze_energy_budget(run_dir, run_name):
    """Analyze kinetic energy evolution from daily diagnostics."""
    csv_path = Path(run_dir) / "output" / "csv" / "daily_diagnostics.csv"
    if not csv_path.exists():
        print(f"No CSV found for {run_name}")
        return None

    df = pd.read_csv(csv_path)

    # KE is in euu column
    ke = df["euu"].values
    days = df["day"].values

    # Compute KE growth rate
    if len(ke) > 1:
        # Exponential fit: KE = KE0 * exp(sigma * t)
        # log(KE) = log(KE0) + sigma * t
        valid = ke > 0
        if valid.sum() > 2:
            log_ke = np.log(ke[valid])
            t = days[valid]
            coeffs = np.polyfit(t, log_ke, 1)
            sigma = coeffs[0]  # per day
            ke0 = np.exp(coeffs[1])
            doubling_time = np.log(2) / sigma if sigma > 0 else np.inf
        else:
            sigma = np.nan
            ke0 = np.nan
            doubling_time = np.nan
    else:
        sigma = np.nan
        ke0 = np.nan
        doubling_time = np.nan

    # Convective adjustment stats
    ca_nmix = df["ca_nmix"].values
    ca_max_iter = df["ca_max_iter"].values
    ca_guard_hits = df["ca_guard_hits"].values
    ca_affected_cols = df["ca_affected_cols"].values

    results = {
        "run_name": run_name,
        "days": days.tolist(),
        "ke": ke.tolist(),
        "ke_initial": float(ke[0]) if len(ke) > 0 else np.nan,
        "ke_final": float(ke[-1]) if len(ke) > 0 else np.nan,
        "ke_max": float(np.max(ke)) if len(ke) > 0 else np.nan,
        "ke_growth_rate_per_day": float(sigma),
        "ke_doubling_time_days": float(doubling_time),
        "ca_nmix_mean": float(np.mean(ca_nmix)),
        "ca_nmix_max": float(np.max(ca_nmix)),
        "ca_max_iter_mean": float(np.mean(ca_max_iter)),
        "ca_max_iter_max": float(np.max(ca_max_iter)),
        "ca_guard_hits_total": int(np.sum(ca_guard_hits)),
        "ca_affected_cols_mean": float(np.mean(ca_affected_cols)),
    }

    print(f"\n=== {run_name} Energy Budget ===")
    print(f"  Days: {len(days)}")
    print(f"  KE initial: {results['ke_initial']:.3e}")
    print(f"  KE final: {results['ke_final']:.3e}")
    print(f"  KE max: {results['ke_max']:.3e}")
    print(f"  Growth rate (per day): {results['ke_growth_rate_per_day']:.4f}")
    print(f"  Doubling time (days): {results['ke_doubling_time_days']:.2f}")
    print(f"  CA nmix mean: {results['ca_nmix_mean']:.3e}")
    print(f"  CA max_iter max: {results['ca_max_iter_max']:.0f}")
    print(f"  CA guard hits total: {results['ca_guard_hits_total']}")
    print(f"  CA affected cols mean: {results['ca_affected_cols_mean']:.1f}")

    return results


def main():
    print("=" * 80)
    print("STAGE 8.1 ENERGY BUDGET ANALYSIS")
    print("=" * 80)

    runs = [
        ("stage81_forensic_3d", "realistic_ref"),
        ("stage81_ref_zero", "reference_level (u=v=0)"),
        ("stage81_dyn_height", "dynamic_height (SSH from DH)"),
        ("stage81_zero", "zero (synthetic drift)"),
    ]

    all_results = {}
    for run_dir, run_name in runs:
        full_path = PROJ_ROOT / "data" / "runs" / run_dir
        result = analyze_energy_budget(full_path, run_name)
        if result:
            all_results[run_name] = result

    # Comparison table
    print("\n" + "=" * 80)
    print("COMPARISON MATRIX")
    print("=" * 80)
    print(
        f"{'Run':<30} {'KE_init':>12} {'KE_final':>12} {'KE_max':>12} {'Growth/d':>10} {'2x time':>8} {'CA_maxiter':>10}"
    )
    print("-" * 80)
    for name, r in all_results.items():
        print(
            f"{name:<30} {r['ke_initial']:>12.3e} {r['ke_final']:>12.3e} {r['ke_max']:>12.3e} {r['ke_growth_rate_per_day']:>10.4f} {r['ke_doubling_time_days']:>8.2f} {r['ca_max_iter_max']:>10.0f}"
        )

    # Save
    out_file = (
        PROJ_ROOT
        / "data"
        / "output"
        / "diagnostics"
        / "stage8.1"
        / "energy_budget.json"
    )
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nSaved: {out_file}")


if __name__ == "__main__":
    main()
