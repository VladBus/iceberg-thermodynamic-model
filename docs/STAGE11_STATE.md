# Stage 11 — Living State (≤150 lines)

**Updated:** 2026-10-25
**Base commit:** `8d40cc0` (T3-CORRECTIVE-2); T3-CORRECTIVE-3 changes in the
current worktree/commit.
**Branch policy:** `main` = legacy-frozen default; stage11-physics changes are
env-gated (default OFF) until D-33 approval.

## Current status

| Field | Value |
|---|---|
| Current stage | 11.8.0 T3-CORRECTIVE-3 (implementation + hygiene) |
| Ocean rest state | **UNSTABLE after E1–E3** (T3b fails: max \|U\| 3.90 m/s, KE30/KE15 52.98) |
| T-19 snowfall | **FIXED** — v2 CDS probe R=1.009 (hourly); divisor 3600 |
| T-25 potential CA | Implemented behind `STAGE118_CA_POTENTIAL` (OFF); no effect in LEGACY |
| T-32 prognostic RO | Implemented behind `STAGE118_RO_PROGNOSTIC` (OFF); no effect (CA already refreshes RO) |
| T-31 EUU | **FIXED diagnostically** — 3D KE printed as `KE3D(J)` |
| Next step | T3-CORRECTIVE-4: coupled advection/density instability; **T4 NO-GO** |

## Issue table (T-01 … T-33)

| # | Status | Notes |
|---|---|---|
| T-01 | OPEN | CA threshold 0.9e-7 / f32 quantization; do not change without RULES procedure |
| T-02 | OPEN | FCT anti-diffusion intentionally disabled; do not “fix” |
| T-03 | DIAGNOSED | Root cause chain characterized; no production fix yet |
| T-04 | OPEN | Ice-ocean drag singularity guard active |
| T-05 | FIXED | ERA5 coverage 100% after domain expansion |
| T-06 | OPEN | Semi-implicit Coriolis period error ~8% |
| T-07 | PARTIAL | Wind-drift ratio explained as Coriolis-limited equilibrium |
| T-08 | WORKAROUND | Procedural workaround |
| T-09 | OPEN | Do not use affected path |
| T-10 | OPEN | Usage condition |
| T-11 | DOCUMENTED | Normal limitation |
| T-12 | DOCUMENTED | Working-tree symlinks; do not remove |
| T-13 | FIXED | Coordinate/bilinear mapping fixed (10.15.2) |
| T-14 | CHARACTERIZED | Revisit if operational runs demand |
| T-15 | QUIRK | Legacy grid quirk; never silent oracle adjustment |
| T-16 | PARTIAL | Jan OSI-SAF/C3S connected; seasonal data missing |
| T-17 | QUIRK | Documented legacy behavior |
| T-18 | VERIFIED | NetCDF dimension-order convention verified |
| T-19 | FIXED | v2 CDS probe: 24 hourly fields, R=1.009 → hourly accumulation; merge divider 3600; v1 INVALID |
| T-20 | FIXED | EN4 z-grid regenerated |
| T-21 | ACCEPTED | April south margin 8 cells, D32 clamp |
| T-22 | FIXED | Sub-freezing EN4 cells clamped |
| T-23 | OPEN | ERA5 wrap; T1-CORRECTIVE before T4 — do not touch now |
| T-24 | DOCUMENTED | Nearest-time forcing (T5 tier) |
| T-25 | IMPLEMENTED | Potential-density CA behind `STAGE118_CA_POTENTIAL` (OFF default); no effect in LEGACY; not a T3b fix |
| T-26 | DOCUMENTED | 3-hourly step forcing |
| T-27 | ADDRESSED | E3 CA criterion uses real64 density differences; stored T/S remains f32 |
| T-28 | FIXED | EN4 product/runtime mask unified (143,422 levels) |
| T-29 | FIXED | Advection boundary writeback restricted to interior |
| T-30 | OPEN | T3b still unstable after E1–E3; max \|U\| 3.90, KE30/KE15 52.98 |
| T-31 | FIXED | `KE3D(J)` diagnostic added; EUU remains barotropic-only |
| T-32 | IMPLEMENTED | E1 RO prognostics behind switch; no effect because CA refreshes RO for all wet columns |
| T-33 | OPEN | Coupled T/S advection + density refresh remains baroclinically unstable at 13.9 km/dt=3600; T4 blocked |

## Switches (default OFF; D-33 gate)

| Env | Purpose | Measured effect |
|---|---|---|
| `STAGE118_RO_PROGNOSTIC` | Recompute RO after CA before B200 | No effect (redundant with CA writeback) |
| `STAGE118_CA_POTENTIAL` | CA compares potential density at lower-level p | No effect in LEGACY; EOS80-only |
| `STAGE118_CA_F64_N2` | real64 CA differences + N² < −1e-6 | Reduces CA mixings/guard; no stabilization |
| `STAGE118_BOUNDARY_SPONGE` | Rayleigh sponge, width 8, τ=1 day | Reduces peak; no plateau; not used in T3b |
| `STAGE118_T3_KEEP_TW` | Retain thermal-wind initial state in rest mode | Still unstable (balanced-init T3b also fails) |

## Evidence

- T3b: `data/validation/t3c3_fix_results.json`, `t3c3_experiments.json`
- T-19: `data/validation/t19_cds_probe_v2.json`, `snowfall_period_result.json`
- Sponge tests: `t3c3_sponge_results.json`, `t3c3_sponge2_results.json`,
  `t3c3_sponge3_results.json`
- Regression: full `fpm test` battery + strict build; Python suites.

## Next action

1. **T3-CORRECTIVE-4** (required): stabilize the coupled advection/density
   system — candidate levers: horizontal/vertical dissipation, boundary
   radiation, time-step/CA sub-cycling, or a balanced test initialization.
2. Keep **T4 NO-GO** until T3b passes and T-23/H-2 are fixed.
3. Do not promote any E1–E3 switch to production without D-33 and a passing
   T3b/T3a gate.
