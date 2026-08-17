"""Compute monthly statistics from the daily summary.

Reads
-----
- ``data/output/daily_summary.csv`` (produced by diagnostics.py)

Produces
--------
- ``data/output/monthly_summary.txt`` - human-readable monthly statistics.

The script only aggregates the daily statistics produced by the Fortran
model; it does not perform any physics.
"""

import argparse
import pathlib

import pandas as pd

DEFAULT_CSV = "data/output/daily_summary.csv"
DEFAULT_OUT = "data/output/monthly_summary.txt"


def main():
    parser = argparse.ArgumentParser(
        description="Compute monthly statistics from the daily summary CSV."
    )
    parser.add_argument("csv", nargs="?", default=DEFAULT_CSV, help="Daily summary CSV")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output text file path")
    args = parser.parse_args()

    csv_path = pathlib.Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found. Run diagnostics.py first.")
        return 1

    df = pd.read_csv(csv_path)
    if df.empty:
        print("ERROR: empty daily summary.")
        return 1

    lines = []
    lines.append("=" * 72)
    lines.append("  AARI Iceberg Thermodynamic Model - Monthly Statistics")
    lines.append("=" * 72)
    lines.append(f"Days simulated : {len(df)}")
    lines.append(f"First model day: {int(df['day'].iloc[0])}")
    lines.append(f"Last model day : {int(df['day'].iloc[-1])}")
    lines.append("")

    scalar_ranges = [
        ("U (cm/s)", "u_min", "u_max"),
        ("V (cm/s)", "v_min", "v_max"),
        ("W (cm/s)", "w_min", "w_max"),
        ("T (degC)", "t_min", "t_max"),
        ("S (mass fr)", "s_min", "s_max"),
        ("RO (g/cm3)", "ro_min", "ro_max"),
    ]
    lines.append("Physical ranges over the month (overall min / max):")
    for label, cmin, cmax in scalar_ranges:
        lines.append(
            f"  {label:12s}: min={df[cmin].min():.6e}  max={df[cmax].max():.6e}"
        )
    lines.append("")

    lines.append("Kinetic energy EUU (cm2/s2):")
    lines.append(f"  min     : {df['euu'].min():.6e}")
    lines.append(f"  max     : {df['euu'].max():.6e}")
    lines.append(f"  mean    : {df['euu'].mean():.6e}")
    lines.append("")

    lines.append("Convective adjustment:")
    lines.append(f"  total nmix (sum)    : {int(df['ca_nmix'].sum())}")
    lines.append(f"  max iterations/day  : {int(df['ca_max_iter'].max())}")
    lines.append(f"  guard hits (total)  : {int(df['ca_guard_hits'].sum())}")
    lines.append(f"  affected columns/day: {int(df['ca_affected_cols'].mean())}")
    lines.append("")

    lines.append("ERA5 wind (m/s):")
    lines.append(f"  max wind speed     : {df['wind_max'].max():.3f}")
    lines.append("")
    lines.append("=" * 72)

    out_path = pathlib.Path(args.out)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Monthly statistics written to {args.out}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
