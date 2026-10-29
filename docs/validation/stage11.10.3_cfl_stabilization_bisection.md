# Stage 11.10.3 — CFL Stabilization, Complete Bisection, Boundary Hardening

**Status:** **FAILED TO STABILIZE N>1** — bisection and hardening complete;
N=24 still NaNs; **Stage 12 NO-GO**. N=1 is diagnostic only, not a final state.
**Date:** 2026-10-27
**Base:** `fa5fdf1`

## Phase 1 — Complete bisection matrix

Added switches in `app/main.f90`:
`STAGE1110_BISECT_WIND`, `STAGE1110_BISECT_THERMO`, `STAGE1110_BISECT_ICE`.
All runs: N=24, `dt=3600`, `MM2=24`, 10 days, OBC OFF, Ah=2000.

| Run | max \|U\| | max \|V\| | First NaN | Final NaN | Conclusion |
|---|---:|---:|---|---:|---|
| Vacuum | 4.38 m/s | 8.72 m/s | none (10 d) | 0 | internal growth |
| Wind-only | 4.35 m/s | 8.76 m/s | none (10 d) | 0 | wind alone does not NaN in 10 d |
| Thermo-only | 3.92 m/s | 3.99 m/s | **day 3 (k0,i8,j114)** | 261,826 | **earliest NaN source** |
| Ice-only | 4.17 m/s | 9.62 m/s | none (10 d) | 0 | ice alone does not NaN in 10 d |

Thermodynamic surface forcing is the fastest NaN trigger; wind/ice alone grow
strongly but remain finite for 10 days. Evidence:
`docs/wiki/stages/stage11/evidence/obc_bisection_matrix.json`.

## Phase 2 — Momentum stabilization

Implemented the low-risk **high-speed Rayleigh drag** option in
`src/stage1110_stab.f90` (default ON for N>1; `STAGE1110_HIGH_SPEED_DRAG=false`
disables):
- threshold 2 m/s, `fac=1/(1+5e-4·dt·(U−2)/100)`;
- boundary strip clip at 5 m/s.

Vacuum N=24 10-day with drag: **max U 1.989 m/s**, no NaN. This meets the
vacuum target and CFL ~0.52, but does not stabilize the forced case.

## Phase 3 — Boundary hardening

Boundary strip (`i≤3 or i≥is−2 or j≤3 or j≥js−2`) velocities are clipped to
5 m/s in the same module. The first full-case NaN moved to day 15
(`k=0,i=2,j=94`) rather than day 4, showing the clip helps but does not remove
the thermodynamic/advective NaN source.

## Phase 4 — N=24 30-day validation

Full forcing, OBC ON, drag ON, Ah=2000, dt=3600:

| Metric | Result |
|---|---:|
| max \|U\| | **1.997 m/s** |
| First NaN | **day 15 (k0,i2,j94)** |
| Final NaN cells | **261,862** |
| CFL from max U | ~0.52 |
| Result | **FAIL** |

The velocity cap is effective, but temperature/salinity can still become NaN;
the earliest thermo-only failure is day 3. Evidence:
`docs/wiki/stages/stage11/evidence/obc_n24_stabilized_results.json`.

## Phase 5 — Regression

- Full `fpm test`: **67/67**, exit 0.
- Strict build: exit 0.
- OBC tests: PASS.
- `git diff --check`: clean.
- CI: final commit run pending at report creation; checked afterward.

## Decision

**N=24 is not stable. N=1 is diagnostic only and is NOT accepted as the final
production state. Stage 12 is NO-GO.** Next work must target the thermodynamic
surface-flux/advection path, not more velocity clipping or OBC.
