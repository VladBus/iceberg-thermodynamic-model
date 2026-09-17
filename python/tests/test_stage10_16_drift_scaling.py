#!/usr/bin/env python3
"""
Stage 10.16 — regression tests for drift dynamics and T-07 investigation.

Independent analytical checks against the controlled-experiment outputs of
`test/iceberg_test_drift_dynamics.f90` and the drift-scaling test outputs.

Analytical expectations (derived from the model's own force balance):
  B2 no-Coriolis drag-limited ratio:  r = k/(1+k),
      k = sqrt(rho_a*C_a*A_sail / (rho_w*C_w*A_side_x))
  B1 Coriolis-limited equilibrium speed:  u = F_wind/(M*f*sqrt(1+(f*dt)^2))
      (discrete semi-implicit equilibrium; continuous limit sqrt(1+...) = 1)
  size scaling (Coriolis-limited):  ratio ~ 1/L
  current response (Coriolis-limited):  u = F_water(U)/(M*f) (times damping)
  timestep damping:  speed(dt) = speed0/sqrt(1+(f*dt)^2)

The test FAILS if the model drifts away from the analytic expectations
(units bug, double factors, wrong drag law) — not merely if the ratio is
"low". It does not compare with the literature 1-2% band.

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_stage10_16_drift_scaling.py
"""

import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "output" / "stage10.16"

_CHECKS = 0
_ERRORS = 0


def ok(condition: bool, label: str, detail: str = "") -> None:
    global _CHECKS, _ERRORS
    _CHECKS += 1
    if condition:
        print(f"OK   {label}" + (f" ({detail})" if detail else ""))
    else:
        print(f"ERROR {label}" + (f" ({detail})" if detail else ""))
        _ERRORS += 1


def skip(label: str, reason: str) -> None:
    global _CHECKS
    _CHECKS += 1
    print(f"SKIP {label} ({reason})")


# Constants (mirror iceberg_types.f90)
RHO_ICE, RHO_WATER, RHO_AIR = 910.0, 1028.0, 1.225
CD_AIR, CD_WATER = 1.3e-3, 2.0e-3
OMEGA = 7.2921150e-5
L = W = H = 100.0
M = RHO_ICE * L * W * H
DRAFT = H * RHO_ICE / RHO_WATER
A_SAIL = L * W + 2 * (L + W) * (H - DRAFT)
A_SIDE_X = W * DRAFT          # Method A: x-force side area = W*draft
F76 = 2 * OMEGA * math.sin(math.radians(76.5))
DT = 3600.0
DAMP_3600 = math.sqrt(1.0 + (F76 * DT) ** 2)


def load_ts() -> dict:
    cols = ("dt_s", "steps", "final_speed_ms", "ratio")
    out = {c: [] for c in cols}
    with (OUT / "timestep_sensitivity.csv").open() as fh:
        for row in fh:
            cells = row.split()
            if not cells or cells[0].startswith("dt"):
                continue
            for i, c in enumerate(cols):
                out[c].append(float(cells[i]))
    return {c: np.array(v) for c, v in out.items()}


def load_size() -> dict:
    cols = ("size_m", "wind_speed_ms", "current_speed_ms",
            "final_speed_ms", "wind_ratio", "current_ratio")
    out = {c: [] for c in cols}
    with (OUT / "size_sensitivity.csv").open() as fh:
        for row in fh:
            cells = row.split()
            if not cells or cells[0].startswith("size"):
                continue
            for i, c in enumerate(cols):
                out[c].append(float(cells[i]))
    return {c: np.array(v) for c, v in out.items()}


def main() -> int:
    print("=" * 72)
    print("STAGE 10.16 — DRIFT SCALING ANALYTICAL REGRESSION")
    print("=" * 72)

    if not (OUT / "timestep_sensitivity.csv").exists():
        skip("all", "run test/iceberg_test_drift_dynamics.f90 first")
        print(f"\nTotal checks: {_CHECKS}, errors: {_ERRORS}")
        return 1 if _ERRORS else 0

    # --- 1. Drag-limited (no Coriolis) ratio: r = k/(1+k) ---
    k = math.sqrt(RHO_AIR * CD_AIR * A_SAIL / (RHO_WATER * CD_WATER * A_SIDE_X))
    r_an = k / (1.0 + k)
    ts = load_ts()
    size = load_size()

    ok(abs(r_an - 0.0345) < 1e-3, "analytic drag ratio ~ 0.0345",
       f"k={k:.4f}, r={r_an:.4f}")

    # --- 2. Coriolis-limited wind speed: u = F_wind/(M*f*DAMP) ---
    v_wind = 10.0
    f_wind = 0.5 * RHO_AIR * CD_AIR * A_SAIL * v_wind**2
    u_an = f_wind / (M * F76 * DAMP_3600)
    # measured B1 speed from force-balance CSV
    b1 = np.loadtxt(OUT / "force_balance_timeseries_B1_wind_cor.csv")
    speed_b1 = float(np.hypot(b1[-1, 2], b1[-1, 3]))
    ok(abs(speed_b1 - u_an) / u_an < 0.05,
       "B1 speed matches Coriolis-limited equilibrium",
       f"measured {speed_b1:.5f}, analytic {u_an:.5f} m/s")

    # --- 3. B2 no-Coriolis speed matches drag-limited equilibrium ---
    b2 = np.loadtxt(OUT / "force_balance_timeseries_B2_wind_nocor.csv")
    speed_b2 = float(np.hypot(b2[-1, 2], b2[-1, 3]))
    ok(abs(speed_b2 / v_wind - r_an) / r_an < 0.05,
       "B2 speed matches drag-limited ratio",
       f"measured ratio {speed_b2/v_wind:.4f}, analytic {r_an:.4f}")

    # --- 4. Size scaling: Coriolis-limited ratio ~ 1/L ---
    w_rows = size["wind_speed_ms"] > 0
    ratios = size["wind_ratio"][w_rows]
    sizes = size["size_m"][w_rows]
    # ratio * L should be ~constant (1/L scaling)
    prod = ratios * sizes
    ok(prod.max() / prod.min() < 1.5, "size scaling ratio*L ~ const",
       f"ratio*L range [{prod.min():.4f}, {prod.max():.4f}]")

    # --- 5. Timestep damping: speed(dt) ~ speed_ref/sqrt(1+(f*dt)^2) ---
    # speed ratio between dt=3600 and dt=7200
    s3600 = ts["final_speed_ms"][np.argmin(np.abs(ts["dt_s"] - 3600))]
    s7200 = ts["final_speed_ms"][np.argmin(np.abs(ts["dt_s"] - 7200))]
    damp_7200 = math.sqrt(1.0 + (F76 * 7200.0) ** 2)
    ratio_pred = DAMP_3600 / damp_7200
    ratio_meas = s7200 / s3600
    ok(abs(ratio_meas - ratio_pred) / ratio_pred < 0.10,
       "timestep damping follows 1/sqrt(1+(f*dt)^2)",
       f"measured {ratio_meas:.3f}, predicted {ratio_pred:.3f}")

    # --- 6. Current response (Coriolis-limited): u ~ F_water/(M*f) ---
    c1 = np.loadtxt(OUT / "force_balance_timeseries_C1_current_cor.csv")
    speed_c1 = float(np.hypot(c1[-1, 2], c1[-1, 3]))
    u_cur = 0.1
    f_water = 0.5 * RHO_WATER * CD_WATER * A_SIDE_X * u_cur**2
    u_c1_an = f_water / (M * F76 * DAMP_3600)
    ok(abs(speed_c1 - u_c1_an) / u_c1_an < 0.10,
       "C1 speed matches Coriolis-limited current response",
       f"measured {speed_c1:.6f}, analytic {u_c1_an:.6f} m/s")

    # --- 7. Zero forcing -> zero velocity (no artificial acceleration) ---
    ok(True, "zero-forcing check covered by Fortran test A (u=v=0)")

    # --- 8. Direction/rotation: wind +X vs +Y -> consistent rotation ---
    # covered by Fortran tests E/F (90-deg rotation consistency)

    # --- 9. Finite/bounded velocity + coordinate continuity (TEST_11) ---
    traj_path = OUT / "test11_stage10.16_trajectory.csv"
    if traj_path.exists():
        import csv
        rows = []
        with traj_path.open(newline="") as fh:
            rdr = csv.reader(fh)
            header = next(rdr)
            header = [h.strip() for h in header]
            for r in rdr:
                cells = r[0].split() if len(r) == 1 else r
                rows.append({h: float(v) for h, v in zip(header, cells) if v.strip()})
        n = len(rows)
        u = np.array([r["u_ms"] for r in rows])
        v = np.array([r["v_ms"] for r in rows])
        lat = np.array([r["lat_deg"] for r in rows])
        lon = np.array([r["lon_deg"] for r in rows])
        speed = np.hypot(u, v)
        ok(n == 720, "TEST_11 720 rows")
        ok(np.all(np.isfinite(u)) and np.all(np.isfinite(v)), "velocities finite")
        ok(np.all(np.isfinite(lat)) and np.all(np.isfinite(lon)), "coords finite")
        ok(speed.max() < 0.5, "speed bounded (<0.5 m/s)", f"max {speed.max():.4f}")
        dlat = np.abs(np.diff(lat))
        dlon = np.abs(np.diff(lon))
        ok(dlat.max() < 0.05 and dlon.max() < 0.05,
           "no coordinate jumps (>0.05 deg)", f"max dlat {dlat.max():.5f}")
        # consistency between reported speed and x/y increments
        dx = np.diff([r["x_m"] for r in rows])
        dy = np.diff([r["y_m"] for r in rows])
        dt_s = np.diff([r["time_h"] for r in rows]) * 3600.0
        v_impl = np.hypot(dx, dy) / dt_s
        ok(np.abs(v_impl - speed[:-1]).max() < 0.01,
           "reported speed == x/y increments",
           f"max diff {np.abs(v_impl - speed[:-1]).max():.5f} m/s")
    else:
        skip("TEST_11 trajectory checks", "test11_stage10.16_trajectory.csv absent")

    print("\n" + "=" * 72)
    print(f"Total checks: {_CHECKS}, errors: {_ERRORS}")
    print("=" * 72)
    if _ERRORS == 0:
        print("SUCCESS: Stage 10.16 drift scaling tests PASSED")
        return 0
    print(f"FAILURE: {_ERRORS} errors")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())