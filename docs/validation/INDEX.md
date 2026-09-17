# Validation Index — Active Stage 10 Validation

Index of reports for the current work on iceberg thermodynamics modernization
(Stage 10). Stage 10 materials stay here until Stage 10 as a whole is
complete; they will then be archived to `docs/wiki/stages/stage10/` (content
is not rewritten, links are updated).

Statuses:

- **ACTIVE** — stage/phase is ongoing, the document is relevant to current work;
- **COMPLETED** — stage finished, report closed, but not yet archived;
- **DRAFT** — draft/intermediate document.

| Document                                               | Stage           | Status                  | Purpose                                                                                                                                              |
| ------------------------------------------------------ | --------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `stage10.7_basal_melt_validation.md`                   | 10.7            | COMPLETED (B)           | Independent analytical validation of basal melt (17 checks), literature band 0.01–1 m/day                                                            |
| `stage10.8.1_python_validation.md`                     | 10.8.1          | COMPLETED (B)           | Independent Python validation layer (`python/validation/`, 44 checks)                                                                                |
| `stage10.8.2_observational_validation.md`              | 10.8.2          | COMPLETED (C)           | Observational validation of basal melt (19 records, 229 checks); systematic limitations documented                                                   |
| `stage10.9_calibration_assessment.md`                  | 10.9            | COMPLETED (C)           | Calibration assessment of the basal-melt coefficient (212 checks); scalar calibration not identifiable — calibration NOT performed                   |
| `stage10.10_three_equation_interface.md`               | 10.10 / 10.10.1 | COMPLETED (C)           | Three-equation ice-ocean interface (H&J99/J2010); includes the 10.10.1 mass/salt convention correction (25 Fortran = 19+6, 65 Python = 46+19 checks) |
| `stage10.11_natural_convection.md`                     | 10.11           | COMPLETED (C)           | Natural convection at the basal face (Ra/Nu, Churchill n=3) — selectable scheme                                                                      |
| `stage10.11.2_natural_convection_audit.md`             | 10.11.2         | COMPLETED (B)           | Audit + Fortran test delivery (23 checks); incorrect claims corrected                                                                                |
| `stage10.11.3_natural_convection_physics_audit.md`     | 10.11.3         | COMPLETED (B)           | Deep scientific audit: Ra cap always active, haline term inert, zero-flow 1.4e-3 m/day does not close the observational gap; production NOT changed  |
| `stage10.12_internal_thermal_evolution.md`             | 10.12           | COMPLETED (C)           | Prognostic internal temperature (two-node lumped), switch `thermal_evolution_enabled`; Fortran 21 + Python 35 checks                                 |
| `stage10.12_internal_thermal_evolution_design_note.md` | 10.12           | COMPLETED (design note) | Phase A design note: two-node model variants and the Variant C choice                                                                                |
| `stage10.13_diffusion_limited_low_flow_design_note.md` | 10.13           | COMPLETED (Phase A)     | Scientific formulation and literature audit of the low-flow closure (MK77 / Keitzl16 / Middleton21)                                                  |
| `stage10.13_phase_b_results.md`                        | 10.13           | COMPLETED (Phase B)     | Research prototype `python/validation/low_flow.py`: 167 checks, sweep 246/270 in the observed band, 10.8.2 re-scoring                                |
| `stage10.13_phase_c_results.md`                        | 10.13           | COMPLETED (Phase C)     | Production integration behind `low_flow_closure_enabled` (OFF by default); Fortran 23 + comparison 56 checks; full battery exit 0                    |
| `stage10.14_three_equation_rescoring.md`               | 10.14           | COMPLETED (C)           | Re-scoring of the 10.8.2 set against the three-equation (10.10/10.10.1) and 3eq+natural-convection (10.11) closures; Python 177 checks; no calibration, no production change |
| `stage10.15_operational_demonstration.md`              | 10.15           | COMPLETED (operational) | Operational end-to-end demonstration: real-forcing 30-day Lagrangian iceberg run (trajectory + diagnostics, 7/7 checks), full-model 1/7-day runs (ocean NaN state documented), dependency audit, reproducible commands |
| `stage10.15.1_trajectory_continuity_audit.md`          | 10.15.1         | COMPLETED (audit; real discontinuity identified) | Follow-up audit of the 10.15 trajectory: model-space x/y continuous and kinematically consistent, but geographic lat/lon contains 8 real jumps (~0.17°) at cell crossings — transposed bilinear weights in `model_coords_to_latlon`/`bilinear_interp_3d` (T-13); source NOT changed (audit-only); corrected projection continuous (corr 0.988); 28 Python regression checks |
| `stage10.15.2_coordinate_mapping_bilinear_fix.md`      | 10.15.2         | COMPLETED (fix; regression-tested, re-run)       | Fix of the transposed bilinear weights (T-13): cross terms swapped in `bilinear_interp_3d` + `model_coords_to_latlon`; new Fortran regression `iceberg_test_bilinear_axis_regression` (13 checks — FAILS pre-fix, PASSES post-fix); TEST_11 re-run: 0 jumps, corr(geo, reported)=0.988; T-07 drift anomaly unchanged (OPEN); physics unchanged |

Note: Stage 10.13 (Phases A–C) is complete and committed (`caa7799`); its
reports remain here because Stage 10 as a whole is still active. Stage 10.13
is a **research parameterization** (numerically tested, production-integrated
behind a switch) — not universally validated. Stage 10.14 is a verification
stage: it re-scores the 10.8.2 observational set against the 3eq and
3eq+natural closures (roadmap item) — no calibration, no production change.
Stage 10.15 is an operational demonstration: 30-day real-forcing Lagrangian
iceberg run (trajectory + diagnostics, reproducible), full-model 1/7-day
runs with the documented ocean NaN state, and the T-12 symlink prerequisite
exercised. It is not a physics change and not an observational validation.
Stage 10.15.1 is a narrow audit of the 10.15 trajectory output: it identifies
a real geographic-coordinate discontinuity (transposed bilinear weights,
T-13) and documents the correction path; the original 10.15 report is kept
unchanged and the corrected figure is linked from the 10.15.1 report.
Stage 10.15.2 fixes the identified defect: the transposed cross terms in
`bilinear_interp_3d` and `model_coords_to_latlon` are swapped (wx along j/X,
wy along i/Y), protected by a new Fortran regression test that fails on the
pre-fix code, and verified by a repeated 30-day TEST_11 run (0 jumps,
corr(implied geo, reported) = 0.988). It is a targeted correctness fix —
no new physics, no calibration, no default change; T-07 drift anomaly
remains open.

## Links to current documentation

- Physics status: `../model/model_physics_status.md`
- Equations: `../model/model_equation_ledger.md`
- Model description: `../model/model_description.md`
- Stage 10 modernization plan: `../model/stage10_modernization_plan.md`
- Decisions: `../DECISIONS.md`
- Archived completed stages: `../wiki/INDEX.md`

## Rules

- Reports here are not rewritten after stage completion (exception: technical
  navigational fixes).
- After Stage 10 as a whole is complete, the directory will be archived to
  `docs/wiki/stages/stage10/` with links and indexes updated.
