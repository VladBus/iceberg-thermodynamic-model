"""Compute per-day summary statistics from the Fortran model output.

Reads
-----
- Fortran daily diagnostics CSV ``data/output/daily_diagnostics.csv``
  (U/V/W/T/S/RO min/max/mean, wind, tau, dp, EUU, convective counters).

Produces
--------
- ``daily_summary.csv`` - one row per model day with all scalar statistics.

Python only READS the diagnostics produced by the Fortran model. It does
not recompute EOS, wind stress, or any physics (see promt.md / AGENTS.md).

Usage
-----
    python python/analysis/diagnostics.py
    python python/analysis/diagnostics.py data/output/daily_diagnostics.csv
"""

import argparse
import pathlib

import pandas as pd

DEFAULT_CSV = "data/output/daily_diagnostics.csv"
DEFAULT_OUT = "data/output/daily_summary.csv"


def main():
    """Read Fortran daily diagnostics CSV and write daily_summary.csv."""
    parser = argparse.ArgumentParser(
        description="Compute daily summary statistics from Fortran daily diagnostics."
    )
    parser.add_argument(
        "csv", nargs="?", default=DEFAULT_CSV, help="Fortran daily diagnostics CSV"
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output CSV path")
    args = parser.parse_args()

    csv_path = pathlib.Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found. Run the Fortran model first.")
        return 1

    df = pd.read_csv(csv_path)

    # Required columns per the Fortran write_daily_diagnostics() format.
    required = [
        "day",
        "u_min",
        "u_max",
        "u_mean",
        "v_min",
        "v_max",
        "v_mean",
        "t_min",
        "t_max",
        "t_mean",
        "s_min",
        "s_max",
        "s_mean",
        "ro_min",
        "ro_max",
        "ro_mean",
        "euu",
        "ca_nmix",
        "ca_max_iter",
        "ca_guard_hits",
        "ca_affected_cols",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"ERROR: missing columns in diagnostics CSV: {missing}")
        return 1

    # Add derived fields: mean kinetic energy proxy and wind info are already
    # present; keep the table as-is but order columns consistently.
    order = [c for c in df.columns if c != "day"]
    df_out = df[["day"] + order].copy()
    df_out.to_csv(args.out, index=False)

    print(f"Daily summary written to {args.out} ({len(df_out)} days)")
    print("\nFirst days:")
    print(df_out.head(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
