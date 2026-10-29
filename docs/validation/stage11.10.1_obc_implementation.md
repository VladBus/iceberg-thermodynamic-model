# Stage 11.10.1 — OBC Implementation and N>1 Stability

**Status:** **PARTIAL / OBC IMPLEMENTED BUT INSUFFICIENT** — N=1 fallback with
explicit caveat; **Stage 12 NO-GO**.
**Date:** 2026-10-27
**Base:** `9535a62`

## Phase 1 — Instability analysis

The NetCDF grid has wet cells on every lateral edge:

| Boundary | Wet cells | Land cells |
|---|---:|---:|
| north `j=1` | 119 | 14 |
| south `j=JS1` | 91 | 42 |
| west `i=1` | 33 | 72 |
| east `i=IS1` | 103 | 2 |

The legacy code applies a no-gradient/copy condition at north/west and
wave-impedance values that are immediately overwritten; south/east are largely
land but have wet strips. At N=4 (dt_ocean=21600 s), one-day max U reaches
**4352 m/s**; at N=24 (3600 s), max U reaches **1.89 m/s**. The immediate
mechanism is CFL violation, not only boundary reflection: CFL = U·dt/dx is
**1464** (N=4) and **1.11** (N=24). Evidence:
`docs/wiki/stages/stage11/evidence/obc_instability_analysis.json`.

## Phase 2 — Flather condition

Implemented in `src/stage1110_obc.f90` and called at the end of every `shal()`:

`q = -eta * sqrt(gH)` (zero external eta/U).

Switch: `STAGE1110_FLATHER_OBC` (default OFF). Focused test
`test_obc_flather.f90` verifies zero-eta and impedance relations. Evidence:
`docs/wiki/stages/stage11/evidence/obc_flather_test.json`.

## Phase 3 — T/S sponge layer

Implemented as an exponential relaxation over the outer 5 wet cells, toward
the initial T/S climatology, with `STAGE1110_SPONGE_ALPHA` (default 1/day) and
`STAGE1110_SPONGE_WIDTH` (default 5). Switches:
`STAGE1110_SPONGE_LAYER` (default OFF). Focused test
`test_obc_sponge.f90` verifies monotone decay and zero interior weight.
Evidence: `docs/wiki/stages/stage11/evidence/obc_sponge_test.json`.

## Phase 4 — Radiation condition

Implemented for boundary transports using
`phi_new = phi_b - c*dt/dx*(phi_b - phi_i)`, with `c=sqrt(gH)`.
Switch: `STAGE1110_RADIATION_OBC` (default OFF). Focused test
`test_obc_radiation.f90` verifies zero-gradient invariance and nonzero
correction. Evidence: `docs/wiki/stages/stage11/evidence/obc_radiation_test.json`.

## Phase 5 — 30-day integration

Configuration: OBC FLATHER+SPONGE+RADIATION ON, Ah=2000, `dt=1800`,
24 fires/day, NetCDF grid/sea-ice, EOS80.

| Scheduler | max \|U\| | max \|V\| | Final NaN cells | Verdict |
|---|---:|---:|---:|---|
| N=4 | **941.38 m/s** | 14002.9 m/s | **262,894** | **FAIL** |
| N=24 | **4.28 m/s** | 7.44 m/s | **261,840** | **FAIL** |

Both complete the 30-day loop but produce NaN fields. N=1 standard matrix
remains the only stable comparison (`max U 0.785 m/s`, `KE30/KE15 1.494`).
Evidence: `docs/wiki/stages/stage11/evidence/obc_n4_n24_results.json`,
`docs/wiki/stages/stage11/evidence/obc_comparison.json`.

## Phase 6 — Fallback

CFL is violated at both target cadences even with Ah=2000; OBC reduces neither
the N=4 catastrophic growth nor N=24 NaN formation. Increasing Ah further is
the documented last resort but is not a substitute for a CFL/advection fix.
The mandated fallback is accepted: **N=1 with explicit caveat**; N=1 is not a
final physical state. The next physical blocker is adaptive
baroclinic timestep/monotone U/V advection, not another boundary copy.

## Phase 7-8 — Verification and deliverables

- Full `fpm test`: **67/67** (64 existing + 3 OBC tests), exit 0.
- Strict build: exit 0.
- Default 30-day OBC-OFF run completes with NetCDF metadata; raw N=1 remains
  physically failing (see `netcdf_default_30day_audit.json`).
- `git diff --check`: clean.
- No EOS/scheduler/iceberg code changed.

## GO/NO-GO for Stage 12

**NO-GO.** N=4 and N=24 do not meet the physical baseline; Stage 12 remains
gated. Required next work: adaptive CFL/timestep and monotone U/V advection,
then re-run N=4/N=24.
