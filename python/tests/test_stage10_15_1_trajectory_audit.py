#!/usr/bin/env python3
"""
Stage 10.15.1 — regression tests for the trajectory continuity and output
integrity audit (python/analysis/stage10.15_1_trajectory_audit.py).

Covers the required audit blocks:

  A. time integrity (720 rows, monotonic steps, no duplicates, dt = 1 h)
  B. coordinate integrity (finite, in-domain, CSV == as-written formula,
     jump detection, corrected-formula continuity)
  C. kinematics (finite velocity, implied speed from x/y vs reported,
     plausible speed band)
  D. thermodynamics (finite mass, positive geometry, monotone mass,
     finite/non-negative/bounded melt)
  E. interpolation formula regression (synthetic grid: as-written formula
     reproduces the transposed pattern; corrected formula is continuous
     across cell boundaries)

The audit script operates on the actual Stage 10.15 output CSV; tests
SKIP the CSV-dependent blocks with a clear message if the output file is
absent (deterministic behavior documented in the Stage 10.15.1 report).

Run:
    conda run -n iceberg-thermodynamic-model python python/tests/test_stage10_15_1_trajectory_audit.py
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
_AUDIT_PY = REPO / "python" / "analysis" / "stage10.15_1_trajectory_audit.py"
# The analysis script name contains dots ("stage10.15.1"), which Python
# cannot import with `import`; load it by file path (bootstrap import).
_spec = importlib.util.spec_from_file_location("stage10_15_1_trajectory_audit",
                                               _AUDIT_PY)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load {_AUDIT_PY}")
aud = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aud)
CSV = REPO / "data" / "output" / "stage10.15" / "test11_trajectory.csv"
RAW_CSV = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"
KOORD = REPO / "data" / "input" / "generated" / "real_grid" / "KOORD.DAT"

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


# ---------------------------------------------------------------------------
# E. Synthetic-grid interpolation regression (always runs; no data required)
# ---------------------------------------------------------------------------
def test_synthetic_interpolation() -> None:
    print("\n=== E. interpolation formula regression (synthetic grid) ===")
    # Grid with a strong anisotropic gradient: fi grows with i (Y) and weakly
    # with j; dl grows with j (X) and weakly with i.
    is1, js1 = 10, 10
    fi = np.zeros((is1, js1))
    dl = np.zeros((is1, js1))
    for i in range(is1):
        for j in range(js1):
            fi[i, j] = 70.0 + 0.1 * i + 0.02 * j   # lat: strong in Y, weak in X
            dl[i, j] = 10.0 + 0.5 * j + 0.05 * i   # lon: strong in X, weak in Y

    # Asymmetric point inside cell (i_idx=3, j_idx=3):
    #   x = (j1 - 1 + 0.2) * DX, y = (i1 - 1 + 0.8) * DX  (wx=0.2, wy=0.8)
    i_idx, j_idx = 3, 3
    xm = (j_idx - 1 + 0.2) * aud.DX
    ym = (i_idx - 1 + 0.8) * aud.DX

    lat_code, lon_code = aud.interp_latlon(xm, ym, fi, dl, corrected=False)
    lat_corr, lon_corr = aud.interp_latlon(xm, ym, fi, dl, corrected=True)

    # Expected values
    i1, i2 = i_idx, i_idx + 1
    j1, j2 = j_idx, j_idx + 1
    wy = 0.8
    wx = 0.2
    # Corrected: x-weight on j, y-weight on i
    exp_lat_corr = ((1 - wx) * (1 - wy) * fi[i1 - 1, j1 - 1] +
                    wx * (1 - wy) * fi[i1 - 1, j2 - 1] +
                    (1 - wx) * wy * fi[i2 - 1, j1 - 1] +
                    wx * wy * fi[i2 - 1, j2 - 1])
    exp_lon_corr = ((1 - wx) * (1 - wy) * dl[i1 - 1, j1 - 1] +
                    wx * (1 - wy) * dl[i1 - 1, j2 - 1] +
                    (1 - wx) * wy * dl[i2 - 1, j1 - 1] +
                    wx * wy * dl[i2 - 1, j2 - 1])
    ok(abs(lat_corr - exp_lat_corr) < 1e-9, "corrected formula lat == analytic",
       f"{lat_corr:.6f} vs {exp_lat_corr:.6f}")
    ok(abs(lon_corr - exp_lon_corr) < 1e-9, "corrected formula lon == analytic",
       f"{lon_corr:.6f} vs {exp_lon_corr:.6f}")

    # As-written formula differs from corrected for anisotropic gradient
    ok(abs(lat_code - lat_corr) > 1e-6, "as-written formula differs from corrected",
       f"lat_code={lat_code:.6f} lat_corr={lat_corr:.6f}")

    # Continuity across a cell boundary (path along x at fixed y):
    # corrected formula must be continuous; as-written must jump.
    # Use a field that varies ONLY with i (Y), so the corrected formula is
    # exactly constant along x and any step is numerical zero.
    fi_y = 70.0 + 0.1 * np.arange(is1)[:, None] * np.ones((1, js1))
    dl_y = 10.0 + 0.05 * np.arange(is1)[:, None] * np.ones((1, js1))
    y_fixed = (i_idx - 1 + 0.5) * aud.DX
    xs = np.linspace((j_idx - 1 - 0.01) * aud.DX, (j_idx + 0.01) * aud.DX, 200)
    lat_corr_path = np.array([aud.interp_latlon(x, y_fixed, fi_y, dl_y, True)[0]
                              for x in xs])
    lat_code_path = np.array([aud.interp_latlon(x, y_fixed, fi_y, dl_y, False)[0]
                              for x in xs])
    max_step_corr = np.abs(np.diff(lat_corr_path)).max()
    max_step_code = np.abs(np.diff(lat_code_path)).max()
    ok(max_step_corr < 1e-9, "corrected formula continuous across cell boundary",
       f"max step {max_step_corr:.2e}")
    ok(max_step_code > 1e-2, "as-written formula jumps at cell boundary",
       f"max step {max_step_code:.2e}")


# ---------------------------------------------------------------------------
# A–D. CSV-dependent audit blocks (SKIP if output absent)
# ---------------------------------------------------------------------------
def test_real_trajectory() -> None:
    print("\n=== A–D. real Stage 10.15 output audit ===")
    src = CSV if CSV.exists() else (RAW_CSV if RAW_CSV.exists() else None)
    if src is None:
        skip("load trajectory", "Stage 10.15 CSV absent")
        return
    if not KOORD.exists():
        skip("load grid", "KOORD.DAT absent")
        return

    t = aud.load_trajectory(src)
    fi, dl = aud.load_grid(KOORD)
    res = aud.audit(t, fi, dl)
    c = res["checks"]

    # A. time
    ok(res["row_count"] == aud.EXPECTED_ROWS, "row count == 720",
       f"{res['row_count']}")
    ok(c["time_steps_monotonic"], "steps strictly monotonic (1..720)")
    ok(c["time_duplicates"] == 0, "no duplicate timestamps",
       f"{c['time_duplicates']}")
    ok(c["time_interval_constant"], "time interval constant (1 h)")
    ok(abs(c["total_duration_h"] - 720.0) < 1e-6, "total duration 720 h",
       f"{c['total_duration_h']:.1f}")

    # B. coordinates
    ok(c["lat_finite"] and c["lon_finite"], "lat/lon finite")
    ok(c["lat_in_domain"] and c["lon_in_domain"], "lat/lon in domain")
    # Post-fix contract (Stage 10.15.2): CSV must match the corrected
    # (production) formula; the transposed pre-fix formula must NOT match.
    ok(c["csv_matches_corrected_formula"], "CSV == corrected (production) formula",
       f"max lat err {res['repro_corr_max_err_lat']:.2e} deg")
    ok(c["csv_does_not_match_transposed"], "CSV does NOT match transposed pre-fix formula",
       f"max lat err {res['repro_max_err_lat']:.2e} deg")
    j = res["coord_jumps"]
    ok(j["count"] == 0, "0 coordinate jumps (post-fix)",
       f"steps {j['steps']}")
    ok(j["max_dlat_deg"] < 0.05, "no large coordinate jumps post-fix",
       f"max dlat {j['max_dlat_deg']:.4f} deg")
    ok(res["corrected_continuous"], "geographic trajectory continuous",
       f"max step {res['corrected_max_step_dlat_deg']:.5f} deg lat / "
       f"{res['corrected_max_step_dlon_deg']:.5f} deg lon")

    # C. kinematics
    ok(c["vel_finite"] and c["speed_finite"], "velocity/speed finite")
    ok(c["implied_speed_from_xy_matches_reported"],
       "implied speed (x/y) matches reported",
       f"max |diff| {res['max_mismatch_implied_vs_reported_ms']:.4f} m/s")
    ok(res["speed_reported"]["plausible"], "reported speed in plausible band",
       f"max {res['speed_reported']['max_ms']:.4f} m/s")
    ok(res["anomalous_intervals"]["count"] == 0,
       "no >5 km/step intervals in x/y")
    # Geographic implied speed (corrected) must match reported speed
    ok(res["speed_implied_geographic_corrected"]["max_ms"] < 0.05,
       "geographic implied speed (corrected) plausible",
       f"max {res['speed_implied_geographic_corrected']['max_ms']:.4f} m/s")

    # D. thermodynamics
    ok(c["mass_finite"], "mass finite")
    ok(c["geometry_positive"], "geometry positive")
    ok(c["mass_monotone_non_increasing"], "mass monotone non-increasing")
    ok(c["melt_finite"], "melt rates finite")
    ok(c["melt_non_negative"], "melt rates non-negative")
    ok(c["melt_bounded"], "melt rates bounded",
       f"max {res['melt_max_mday']} m/day")
    ok(c["timeseries_length_consistent"], "time-series lengths consistent")


def main() -> int:
    print("=" * 72)
    print("STAGE 10.15.1 — TRAJECTORY AUDIT REGRESSION TESTS")
    print("=" * 72)
    test_synthetic_interpolation()
    test_real_trajectory()
    print("\n" + "=" * 72)
    print(f"Total checks: {_CHECKS}, errors: {_ERRORS}")
    print("=" * 72)
    if _ERRORS == 0:
        print("SUCCESS: Stage 10.15.1 audit tests PASSED")
        return 0
    print(f"FAILURE: {_ERRORS} errors")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())