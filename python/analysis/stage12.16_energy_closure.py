#!/usr/bin/env python3
"""Stage 12.16: energy-budget closure from run.nc_energy.csv.

The model accumulates boundary heat by face type (submerged Dirichlet/Stefan,
air Robin, test-only Dirichlet) and the flushed-ice energy. The closure checked
here is

  (E_sens - E_sens0) + L*(m_melt - m_melt0) + (E_flush - E_flush0)
      - (Q_sub + Q_air + Q_test) = residual.

Residual is reported in J and as % of the latent heat change over the interval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()
    d = pd.read_csv(a.csv)
    r = d["residual_J"].to_numpy(float)
    pct = d["residual_pct_latent"].to_numpy(float)
    latent = d["latent_melt_J"].to_numpy(float)
    latent0 = latent[0]
    L = 334000.0
    melt = d["cum_melt_mass_kg"].to_numpy(float)
    melt0 = melt[0]
    summary = {
        "records": int(len(d)),
        "days": float(d["time_s"].iloc[-1] / 86400.0),
        "sensible_initial_J": float(d["sensible_energy_J"].iloc[0]),
        "sensible_final_J": float(d["sensible_energy_J"].iloc[-1]),
        "latent_total_J": float(latent[-1] - latent0),
        "boundary_submerged_J": float(d["boundary_submerged_J"].iloc[-1]),
        "boundary_air_J": float(d["boundary_air_J"].iloc[-1]),
        "boundary_test_J": float(d["boundary_test_J"].iloc[-1]),
        "flushed_energy_J": float(d["flushed_energy_J"].iloc[-1]),
        "residual_final_J": float(r[-1]),
        "residual_final_pct_latent": float(pct[-1]),
        "residual_max_abs_pct_latent": float(pd.Series(pct).abs().max()),
        "residual_median_abs_pct_latent": float(pd.Series(pct).abs().median()),
        "q_sub_minus_latent_total_J": float(
            d["boundary_submerged_J"].iloc[-1] - L * (melt[-1] - melt0)),
        "q_air_total_J": float(
            d["boundary_air_J"].iloc[-1]),
        "flushed_energy_minus_L_flush_J": float(
            d["flushed_energy_J"].iloc[-1] -
            L * (d["cum_flush_mass_kg"].iloc[-1] - d["cum_flush_mass_kg"].iloc[0])),
        "sensible_change_J": float(
            d["sensible_energy_J"].iloc[-1] - d["sensible_energy_J"].iloc[0]),
    }
    out = a.out or a.csv.with_suffix(".json")
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
