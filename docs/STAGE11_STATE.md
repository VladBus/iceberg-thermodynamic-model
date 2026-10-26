# Stage 11 — Living State (≤150 lines)

**Updated:** 2026-10-25
**Base commit:** `35bf3b7` (T3-CORRECTIVE-3); T3-CORRECTIVE-4 changes in the
current commit.
**Branch policy:** `main` = legacy-frozen default; stage11-physics changes are
env-gated (default OFF) until D-33 approval.

## Current status

| Field | Value |
|---|---|
| Current stage | 11.8.0 T5-CORRECTIVE-3 (monotone advection + sponge) — COMPLETE (FAIL) |
| Ocean rest state | **T3b PASS (bounded)** — max \|U\| **0.147 m/s**, KE30/KE15 **0.568** (dt=1800, Ah=10000, no sponge) |
| T-19 snowfall | **FIXED** — v2 CDS probe R=1.009 (hourly); divisor 3600 |
| T-25 potential CA | Implemented behind `STAGE118_CA_POTENTIAL` (OFF); no effect in LEGACY |
| T-32 prognostic RO | Implemented behind `STAGE118_RO_PROGNOSTIC` (OFF); no effect (CA already refreshes RO) |
| T-31 EUU | **FIXED diagnostically** — 3D KE printed as `KE3D(J)` |
| Next step | **T5-CORRECTIVE-4** (density/thermodynamic coupling); **T6 NO-GO** |

## Issue table (T-01 … T-37)

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
| T-23 | FIXED | `STAGE118_LON_CLAMP`; 75E→70E ON, 10E OFF; T1 spatial PASS |
| T-24 | DOCUMENTED | Nearest-time forcing (T5 tier) |
| T-25 | IMPLEMENTED | Potential-density CA behind `STAGE118_CA_POTENTIAL` (OFF default); no effect in LEGACY; not a T3b fix |
| T-26 | DOCUMENTED | 3-hourly step forcing |
| T-27 | ADDRESSED | E3 CA criterion uses real64 density differences; stored T/S remains f32 |
| T-28 | FIXED | EN4 product/runtime mask unified (143,422 levels) |
| T-29 | FIXED | Advection boundary writeback restricted to interior |
| T-30 | MITIGATED | T3b PASS with dt=1800 + Ah=10000; max \|U\| 0.147, KE30/KE15 0.568 |
| T-31 | FIXED | `KE3D(J)` diagnostic added; EUU remains barotropic-only |
| T-32 | IMPLEMENTED | E1 RO prognostics behind switch; no effect because CA refreshes RO for all wet columns |
| T-33 | MITIGATED | Unresolved baroclinic eddies (R_d 2.36 km vs 13.89 km); bounded by dt=1800 + Ah=10000; fundamental limitation documented |
| T-34 | CLOSED (tentative) | Heat drift physical: −3.94 W/m² Jan, −9.81 W/m² Apr; volume 0, salt <1e-3 |
| T-35 | OPEN | Monotone+sponge: no NaN, Umax 1.141, KE90/KE60 0.975, but RO<0 (3,187 cells) |
| T-36 | OPEN | Salinity advection root; monotone/sponge caps not a density fix |
| T-37 | OPEN | Hard S/T caps create RO<0 (−24.24, 3,187 cells); T5-CORRECTIVE-4 needed |
| H-2 | FIXED | `STAGE118_WIND_ROTATION`; alpha median 50.18°, max 81.28°; dir error 2.8e-14° |

## Switches (default OFF; D-33 gate)

| Env | Purpose | Measured effect |
|---|---|---|
| `STAGE118_RO_PROGNOSTIC` | Recompute RO after CA before B200 | No effect (redundant with CA writeback) |
| `STAGE118_CA_POTENTIAL` | CA compares potential density at lower-level p | No effect in LEGACY; EOS80-only |
| `STAGE118_CA_F64_N2` | real64 CA differences + N² < −1e-6 | Reduces CA mixings/guard; no stabilization |
| `STAGE118_BOUNDARY_SPONGE` | Rayleigh sponge, width 8, τ=1 day | Reduces peak; no plateau; not used in T3b |
| `STAGE118_T3_KEEP_TW` | Retain thermal-wind initial state in rest mode | Still unstable (balanced-init T3b also fails) |
| `STAGE118_LAPLACIAN_VISC` / `STAGE118_AH` | Extra Laplacian viscosity, Ah [m²/s] | **Chosen: Ah=10000 with dt=1800**; T3b PASS |
| `STAGE118_WIND_ROTATION` | ERA5 geographic → rotated grid wind | Verified; default OFF |
| `STAGE118_LON_CLAMP` | Out-of-range longitude → file edge | Verified; default OFF |

## Evidence

- T3b: `data/validation/t3c4_final_results.json`, `t3c4_ah_results.json`, `t3c4_dt_results.json`
- H-2/T-23: `wind_rotation_verification.json`, `wind_rotation_fortran.json`, `lon_clamp_verification.json`, `t3_with_fixes.json`
- T4: `t4_wind_forcing_metrics.json`, `t4_ekman_analysis.json`, `t4_energy_budget.json`, `t4_acceptance.json`, `t4_comparison_t3.json`
- T5: `t5_90day_results.json`, `t5_april_results.json`, `t5_seasonal_comparison.json`, `t34_heat_closure.json`
- T5-CORRECTIVE: `t5c_config1_results.json`…`t5c_config4_results.json`, `t5c_storm_analysis.json`, `t5c_summary.json`
- T5-CORRECTIVE-2: `t5c2_root_cause.json`, `t5c2_ca_diagnostics.json`, `t5c2_advection_diagnostics.json`, `t5c2_boundary_diagnostics.json`, `t5c2_energy_budget.json`
- T5-CORRECTIVE-3: `t5c3_90day_with_fixes.json`, `t5c3_april_with_fixes.json`, `t5c3_monotone_test.json`, `t5c3_sponge_test.json`
- T-19: `data/validation/t19_cds_probe_v2.json`, `snowfall_period_result.json`
- Sponge tests: `t3c3_sponge_results.json`, `t3c3_sponge2_results.json`,
  `t3c3_sponge3_results.json`
- Regression: full `fpm test` battery + strict build; Python suites.

## Next action

1. **T5-CORRECTIVE-3 FAIL**: monotone+sponge eliminates NaN but creates RO<0 via hard S/T caps.
2. **T6 NO-GO**; next **T5-CORRECTIVE-4** (density/thermodynamic coupling, not more tracer caps).
3. D-33 switches remain OFF default; hard caps are not production physics.
