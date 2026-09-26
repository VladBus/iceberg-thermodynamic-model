# Stage 10 — Iceberg Thermodynamics Modernization (Complete)

Stage 10 modernization of the iceberg thermodynamics is **complete**. All reports have been archived here.

This directory contains all 25 Stage 10 validation reports (10.7 through 10.22).

## Reports (25)

| # | File | Report | Stage | Status |
|---|------|--------|-------|--------|
| 1 | `stage10.7_basal_melt_validation.md` | Stage 10.7 — Independent Basal Melt Validation | 10.7 | COMPLETED (B) |
| 2 | `stage10.8.1_python_validation.md` | Stage 10.8.1 — Independent Python Validation Layer | 10.8.1 | COMPLETED (B) |
| 3 | `stage10.8.2_observational_validation.md` | Stage 10.8.2 — Observational Validation of Basal Melt | 10.8.2 | COMPLETED (C) |
| 4 | `stage10.9_calibration_assessment.md` | Stage 10.9 — Calibration Assessment of Basal-Melt Coefficient | 10.9 | COMPLETED (C) |
| 5 | `stage10.10_three_equation_interface.md` | Stage 10.10/10.10.1 — Three-Equation Ice-Ocean Interface | 10.10/10.10.1 | COMPLETED (C) |
| 6 | `stage10.11_natural_convection.md` | Stage 10.11 — Natural Convection Basal Melt | 10.11 | COMPLETED (C) |
| 7 | `stage10.11.2_natural_convection_audit.md` | Stage 10.11.2 — Natural Convection Audit | 10.11.2 | COMPLETED (B) |
| 8 | `stage10.11.3_natural_convection_physics_audit.md` | Stage 10.11.3 — Natural Convection Physics Audit | 10.11.3 | COMPLETED (B) |
| 9 | `stage10.12_internal_thermal_evolution.md` | Stage 10.12 — Prognostic Internal Thermal Evolution | 10.12 | COMPLETED (C) |
| 10 | `stage10.12_internal_thermal_evolution_design_note.md` | Stage 10.12 Design Note | 10.12 | COMPLETED (design note) |
| 11 | `stage10.13_diffusion_limited_low_flow_design_note.md` | Stage 10.13A — Low-Flow Closure Design Note | 10.13 | COMPLETED (Phase A) |
| 12 | `stage10.13_phase_b_results.md` | Stage 10.13B — Low-Flow Prototype Results | 10.13 | COMPLETED (Phase B) |
| 13 | `stage10.13_phase_c_results.md` | Stage 10.13C — Low-Flow Production Integration | 10.13 | COMPLETED (Phase C) |
| 14 | `stage10.14_three_equation_rescoring.md` | Stage 10.14 — Three-Equation Rescoring | 10.14 | COMPLETED (C) |
| 15 | `stage10.15_operational_demonstration.md` | Stage 10.15 — Operational End-to-End Demonstration | 10.15 | COMPLETED (operational) |
| 16 | `stage10.15.1_trajectory_continuity_audit.md` | Stage 10.15.1 — Trajectory Continuity Audit | 10.15.1 | COMPLETED (audit) |
| 17 | `stage10.15.2_coordinate_mapping_bilinear_fix.md` | Stage 10.15.2 — Coordinate Mapping Bilinear Fix | 10.15.2 | COMPLETED (fix) |
| 18 | `stage10.16_drift_dynamics_t07_investigation.md` | Stage 10.16 — Drift Dynamics / T-07 Investigation | 10.16 | COMPLETED (investigation) |
| 19 | `stage10.17_melt_thermodynamic_budget_audit.md` | Stage 10.17 — Melt/Thermodynamic Budget Audit | 10.17 | COMPLETED (audit) |
| 20 | `stage10.18a_lateral_melt_parameterization_audit.md` | Stage 10.18A — Lateral Melt Parameterization Audit | 10.18A | COMPLETED (research) |
| 21 | `stage10.18b_observational_constraint.md` | Stage 10.18B — Observational Constraint | 10.18B | COMPLETED (observational) |
| 22 | `stage10.18c_existing_observations_reanalysis.md` | Stage 10.18C — Existing Observations Reanalysis | 10.18C | COMPLETED (reanalysis) |
| 23 | `stage10.18d_velocity_resolved_observational_upgrade.md` | Stage 10.18D — Velocity-Resolved Observational Upgrade | 10.18D | COMPLETED (upgrade) |
| 24 | `stage10.19_production_runtime_coupling_recovery.md` | Stage 10.19 — Production Runtime & Coupling Recovery | 10.19 | COMPLETED (runtime) |
| 25 | `stage10.20_ocean_initialization_numerical_stabilization.md` | Stage 10.20 — Ocean Initialization Numerical Stabilization | 10.20 | COMPLETED (stabilization) |
| 26 | `stage10.21_convective_precision_stabilization.md` | Stage 10.21 — Convective Precision Stabilization | 10.21 | COMPLETED (negative result) |
| 27 | `stage10.22_ocean_density_thermal_wind_block200_audit.md` | Stage 10.22 — Ocean Density/Thermal-Wind/Block-200 Audit | 10.22 | COMPLETED (audit) |

## Early Stage 10 Reports (Pre-Validation Structure)

These reports were created before the `docs/validation/` structure was adopted:

| File | Report |
|------|--------|
| `Stage10.4.2.1_Independent_Q_surface_output_validation.md` | Stage 10.4.2.1 — Independent Q_surface Output Validation |
| `Stage10.4.2_Independent_monotonicity_validation.md` | Stage 10.4.2 — Independent Monotonicity Validation |
| `Stage10.5_Ocean_Thermal_Forcing.md` | Stage 10.5 — Ocean Thermal Forcing |

## Status

- **ARCHIVED** — stage materials are complete and not edited retroactively.
- Current model state: `../../../model/`; decisions: `../../../DECISIONS.md`.
- Active validation reports (Stage 11+): `../../../validation/INDEX.md`.
- General navigation: `../../README.md` → `../../INDEX.md`.

---

## Stage Summary

Stage 10 (iceberg thermodynamics modernization) spanned **10.7–10.22** and achieved:

- **Basal melt validation** (10.7–10.9): Independent analytical, Python, and observational validation; calibration assessment showed scalar calibration not identifiable.
- **Three-equation interface** (10.10/10.10.1): H&J99/J2010 implementation with mass/salt convention correction.
- **Natural convection** (10.11/10.11.2/10.11.3): Ra-cap always active; zero-flow melt doesn't close observational gap; production unchanged.
- **Internal thermal evolution** (10.12): Two-node lumped prognostic temperature; fully gated switch.
- **Low-flow closure** (10.13A–C): Research parameterization behind OFF-by-default switch; 167 checks.
- **Three-equation rescoring** (10.14): Re-scoring 10.8.2 set against 3eq and 3eq+natural; no calibration.
- **Operational demonstration** (10.15): 30-day real-forcing iceberg run; full-model runs documented NaN state.
- **Trajectory audit & fix** (10.15.1/10.15.2): Geographic coordinate discontinuity identified (transposed bilinear weights), fixed and regression-tested.
- **Drift dynamics** (10.16): T-07 partially explained — Coriolis-limited equilibrium of 100-m cube.
- **Melt/thermodynamic budget** (10.17): Lateral legacy melt dominates 96.8%; findings diagnostics-only.
- **Lateral melt audit** (10.18A–D): Legacy C_LATERAL ≡ forced-convection at U_eq≈0.30 m/s (factor 10–60 above simulated); observational constraints (OPTION E/D); per-iceberg Enderlin23 dataset retrieved (743 icebergs); legacy exceeds 99.6% of observed melt; velocity dependence NOT IDENTIFIABLE; ADCP campaign designed.
- **Production coupling** (10.19): Iceberg module connected behind `ICEBERG_PRODUCTION=true` gate; NaN guard added; CASE C/D forensic analysis.
- **Ocean initialization stabilization** (10.20): Full-coverage ERA5 data fixed CASE C; residual CA instability characterized (T-01/T-03 family); acceptance 360 NOT met.
- **CA/EOS precision stabilization** (10.21): Float32 2⁻²³ quantization root cause confirmed; eliminating CA residual does NOT stabilize ocean; production KEEP_CURRENT.
- **Block-200/210 stability audit** (10.22): Causal chain ISOLATED (CA/EOS → ρ<0 day 4 → NaN day 5 → Block 200 transmitter → Block 210 amplifier → zombie); Thomas pivots negative by construction; stabilizer levers diagnostic-only; production KEEP_CURRENT (D-20).

**Stage 10 Conclusion:** The ocean prognostic instability persists (density-first divergence → NaN/zombie). Stage 11 begins with seasonal stability characterization.

## Navigation

- **Current model specification**: `../../../model/`
- **Decisions**: `../../../DECISIONS.md`
- **Active validation (Stage 11)**: `../../../validation/INDEX.md`
- **General navigation**: `../../README.md` → `../../INDEX.md`