#!/usr/bin/env python3
"""Stage 12.14: 30-day mass-loss convergence order and Richardson error."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from scipy.optimize import brentq

N = np.array([50.0, 70.0, 100.0])
LOSS = np.array([0.039621182116781055, 0.03913328794370936, 0.03872890560857905])
RHO = 916.7


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--outdir", type=Path, default=Path("data/validation/stage12.14/convergence"))
    a = p.parse_args(); a.outdir.mkdir(parents=True, exist_ok=True)
    f1, f2, f3 = LOSS
    R = (f1 - f2) / (f2 - f3)
    r1 = N[1] / N[0]; r2 = N[2] / N[1]
    F = lambda q: (r1**q - 1.0) / (1.0 - r2**(-q)) - R
    p = float(brentq(F, 1e-6, 4.0))
    linf = float(f2 - (f1 - f2) / (r1**p - 1.0))
    err = 100.0 * (f3 - linf) / linf
    # mean submarine melt rate from the run's wet area (mass loss / area / time)
    rates = {}
    for n in (8, 20, 50, 70, 100):
        run = a.outdir.parents[1] / "stage12.12" / "resolution" / str(n) / "run30.nc"
        if not run.exists():
            continue
        import xarray as xr
        ds = xr.open_dataset(run)
        mass = ds.mass.values; awet = ds.a_wet.values
        rates[str(n)] = float((mass[0] - mass[-1]) / (RHO * np.mean(awet) * 30.0))
        ds.close()
    out = {"grids": N.tolist(), "mass_loss_30d": LOSS.tolist(),
           "difference_ratio": float(R), "r_50_70": r1, "r_70_100": r2,
           "p": p, "mass_loss_infinity": linf,
           "error_100_percent": float(err),
           "mean_melt_rate_m_per_day": rates,
           "metric_note": "mass-loss fraction and mean wetted-area melt rate; no T_max convergence metric"}
    (a.outdir / "convergence.json").write_text(json.dumps(out, indent=2) + "\n")
    with open(a.outdir / "convergence.csv", "w") as f:
        f.write("N,mass_loss_30d\n")
        for n, v in zip(N, LOSS):
            f.write(f"{int(n)},{v:.12e}\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
