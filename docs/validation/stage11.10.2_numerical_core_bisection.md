# Stage 11.10.2 — Numerical Core Bisection & Time-Stepping Fix

**Status:** **PARTIAL / N>1 STILL UNSTABLE** — subcycling fixed, OBC tested,
N=24 still fails; N=1 fallback with explicit caveat; **Stage 12 NO-GO**.
**Date:** 2026-10-27
**Base:** `a3d5671`

## Phase 1 — Barotropic subcycling / CFL audit

Legacy `shal()` hardcoded `dt1=120 s`, `mm3=30`, independent of the baroclinic
step and of `STAGE115C_OCEAN_SUBSTEPS`; it was also called on every `iii`,
over-integrating the barotropic mode at N=4.

**Fix:**
- `shal(dt_step)` now computes `mm3 = max(1, nint(dt_step/120))` and
  `dt1 = dt_step/mm3` (dt1 ≤ 120 s).
- `shal()` is gated to the same `ostep_115c` cadence as the ocean tail.
- Verified logs:
  - N=24: `dt=3600`, 30 substeps, `dt1=120`.
  - N=4: `dt=21600`, 180 substeps, `dt1=120`.

This removes the hardcoded-substep inconsistency but does not by itself
stabilize N>1.

## Phase 2 — Bisection matrix

| Run | Config | First NaN hour/day | First NaN cell | Conclusion |
|---|---|---|---|---|
| N24 full 30 d | full forcing + OBC + Ah=2000 | **day 4** | **k=0, i=2, j=24** | external + internal dynamics fail |
| N24 vacuum 10 d | `STAGE118_T3_REST_MODE=true` (no wind/ice/thermo), no OBC | none | — | no NaN at 10 d, but max U grows to **4.38 m/s** → internal dynamics unstable |
| N24 wind-only 10 d | component switch absent | — | — | not run: no wind-only switch |
| N24 thermo-only 10 d | component switch absent | — | — | not run: no thermo-only switch |
| N24 ice-only 10 d | component switch absent | — | — | not run: no ice-only switch |

The vacuum control proves external flux shocks are not required for the core
instability. Full component bisection is blocked by missing per-component
switches; this is documented rather than fabricated.

Evidence: `data/validation/obc_bisection_matrix.json`.

## Phase 3 — Momentum/FCT/viscosity findings

- Momentum advection still uses the legacy non-monotone transport path; the FCT
  anti-diffusion remains disabled (T-02).
- Ah=5000 and Ah=10000 were tested at N=24: both still fail 30 days.
- No momentum/FCT patch was applied because the dominant failure is already
  present in the vacuum control and CFL remains >1 at N=24. A monotone U/V
  advection scheme is the next required code change, not a viscosity increase.

Evidence: `obc_n24_ah5000_30d`, `obc_n24_ah10000_30d` (kept), audit JSON.

## Phase 4 — Flux scaling / ice stress / DZ guard

- ERA5 forcing is already applied per model step through the existing
  thermodynamics path; no daily pulse was found in this audit.
- No ice-velocity guardrail was added: the ocean-only failure is reproduced in
  the vacuum control, before ice coupling.
- No vertical `DZ` guard was added: the first NaN is a surface U cell
  (`k=0`) at the lateral boundary strip, not a zero-layer thickness event.
- These remain candidate hardening items after the core CFL/advection fix.

## Phase 5 — N=4/N=24 30-day results

Configuration: corrected subcycling, `dt=3600`, `MM2=24`, OBC ON, Ah=2000.

| Scheduler | max \|U\| | max \|V\| | First NaN | Final NaN cells | Result |
|---|---:|---:|---|---:|---|
| N=4 | **137.8 m/s** | **3009.8 m/s** | day 2 (k0,i2,j46) | 262,894 | FAIL |
| N=24 | **3.94 m/s** | **6.04 m/s** | day 4 (k0,i2,j24) | 261,840 | FAIL |

N=1 standard matrix remains the only stable baseline (`max U 0.785 m/s`,
`KE30/KE15 1.494`), but is explicitly **diagnostic only, not for Stage 12**.
Evidence: `obc_dt3600_n4_n24_results.json`, `obc_comparison.json`,
`obc_cfl_analysis.json`.

## Phase 6 — Regression

- Full `fpm test`: **67/67**, exit 0.
- Strict build: exit 0.
- OBC focused tests: flather/sponge/radiation PASS.
- `git diff --check`: clean.
- No EOS/scheduler/iceberg physics changed (shal subcycling is numerical core).

## GO/NO-GO for Stage 12

**NO-GO.** N=24 does not meet 30-day stability; vacuum control already grows
to 4.38 m/s. Required next work: adaptive CFL / monotone U/V advection; then
re-run N=24. N=1 fallback is accepted only with the explicit caveat above.
