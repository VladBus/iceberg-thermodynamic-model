# Stage 11.10.4 — Thermodynamic Core Rewrite

**Status:** **PASS — N=24 30-day stable with rewritten thermodynamics**; N=1
diagnostic only; Stage 12 implementation not started.
**Date:** 2026-10-27
**Base:** `ac0a04d`

## Phase 1 — Hard T/S limits

`src/stage1110_thermo.f90` enforces after every thermodynamic update:
- `S = clamp(S, 0, 40 PSU)`;
- `T >= Tf(S)` using the UNESCO freezing-point approximation;
- `T <= 30 °C`.
Switch `STAGE1110_HARD_LIMITS` (default ON for N>1).

Thermo-only N=24 10-day: **0 NaN**, max U 1.98 m/s.
`docs/wiki/stages/stage11/evidence/thermo_hard_limits_test.json`.

## Phase 2 — Implicit vertical diffusion

Implemented backward-Euler vertical diffusion with a Thomas solve for T and S
in `src/stage1110_thermo.f90`; switch `STAGE1110_IMPLICIT_VDIFF` (ON for N>1).
The solver uses a conservative column tridiagonal system and the validated
layer thickness convention. N=24 full 30-day passes with 0 NaN.
`docs/wiki/stages/stage11/evidence/thermo_implicit_test.json`.

## Phase 3 — Surface flux clipping

Every open-water net heat flux `qn` is clipped to **[-500, +500] W/m²** before
application. Switch `STAGE1110_FLUX_CLIPPING` (ON for N>1).
Full N=24 10/30-day runs remain finite.
`docs/wiki/stages/stage11/evidence/thermo_flux_clipping_test.json`.

## Phase 4 — Post-CA smoothing

A 3-point vertical smoother (`0.25/0.5/0.25`) is applied after CA over wet
levels 2..ki-1. Switch `STAGE1110_CA_SMOOTHING` (ON for N>1).
`docs/wiki/stages/stage11/evidence/thermo_ca_smoothing_test.json`.

## Phase 5 — N=24 30-day validation

Configuration: all four thermodynamic features ON, Rayleigh drag ON,
boundary clip ON, OBC ON, Ah=2000, `dt=3600`, `MM2=24`, NetCDF, EOS80.

| Metric | Result |
|---|---:|
| NaN cells at day 30 | **0** |
| max \|U\| | **1.999 m/s** |
| max \|V\| | **2.000 m/s** |
| max CFL (U·dt/dx) | **0.518** |
| T range | **−1.94 … 30.00 °C** |
| S range | **0.00 … 37.05 PSU** |
| KE day 10/20/30 | 7.19e16 / 2.16e16 / 2.11e16 J |
| KE stable after day 10 | **YES** (decaying) |

Registry: `docs/wiki/stages/stage11/evidence/n24_30day_thermo_rewrite_results.json`.
N=1 diagnostic with all new switches explicitly OFF: 1-day, 0 NaN.
No bit-identity claim is made for the thermodynamic rewrite.

## Phase 6 — Regression

- Full `fpm test`: **67/67**, exit 0.
- Strict build: exit 0.
- `git diff --check`: clean.
- No EOS/iceberg-dynamics code changed.

## Decision

The N=24 thermodynamic stability gate **PASSES** for the validated 30-day run.
Stage 12 remains **not started**; N=1 is diagnostic only and is rejected as the
final production state. Hard limits are active caps; the 30 °C/40 PSU edges
are explicit limiter values and must be reviewed in Stage 12.
