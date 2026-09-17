# CHANGELOG.md — History of Significant Changes

Brief stage-by-stage records. Details: stage reports (`docs/validation/` —
active, `docs/wiki/stages/stageXX/` — archived), decisions —
`docs/DECISIONS.md`, physics status — `docs/model/model_physics_status.md`.
Full commit list — `git log`.

## Stage 10 (iceberg thermodynamics modernization)

| Stage             | Summary                                                                                                                | Commits                         | Report                                                                                                                                                                   |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 10.1.1            | Solar geometry (Spencer 1971)                                                                                          | `0177712`                       | Stage 10 plan                                                                                                                                                            |
| 10.2              | Prognostic surface temperature                                                                                         | `741e627`                       | Stage 10 plan                                                                                                                                                            |
| 10.3              | Modern atmospheric fluxes (bulk, Murphy & Koop 2005)                                                                   | `f82c527`                       | Stage 10 plan                                                                                                                                                            |
| 10.4 / 10.4.1     | Phase-change partitioning; latent-heat energy-partition correction                                                     | `8af9f1f`                       | `docs/wiki/stages/stage10/` (10.4.2, 10.4.2.1)                                                                                                                           |
| 10.4.2 / 10.4.2.1 | Independent monotonicity and Q_surface output validation                                                               | `8af9f1f`+                      | `docs/wiki/stages/stage10/Stage10.4.2*`                                                                                                                                  |
| 10.5              | EOS-80/UNESCO freezing point (replaces the Zubov law)                                                                  | `b4e67cc`                       | `docs/wiki/stages/stage10/Stage10.5_Ocean_Thermal_Forcing.md`                                                                                                            |
| 10.6.1            | Ocean heat-transfer audit + documentation correction                                                                   | `40d4a3b`                       | — (in plan)                                                                                                                                                              |
| 10.7              | Independent basal-melt validation (17 checks)                                                                          | —                               | `docs/validation/stage10.7_basal_melt_validation.md`                                                                                                                     |
| 10.8.1            | Independent Python validation layer (44 checks)                                                                        | `b6265f4` (+CI)                 | `docs/validation/stage10.8.1_python_validation.md`                                                                                                                       |
| 10.8.2            | Observational validation of basal melt (19 records, 229 checks)                                                        | `f45c2d4` (data)                | `docs/validation/stage10.8.2_observational_validation.md`                                                                                                                |
| 10.9              | Calibration assessment of C_γ (212 checks); calibration NOT performed                                                  | `a92c755`                       | `docs/validation/stage10.9_calibration_assessment.md`                                                                                                                    |
| 10.10 / 10.10.1   | Three-equation ice-ocean interface (H&J99/J2010); mass/salt convention correction                                      | `dcb9f3c`+                      | `docs/validation/stage10.10_three_equation_interface.md`                                                                                                                 |
| 10.11 / 10.11.2   | Natural-convection basal melt (selectable); audit + test delivery                                                      | `6a0014e`, `dcb9f3c`            | `docs/validation/stage10.11_natural_convection.md`, `docs/validation/stage10.11.2_natural_convection_audit.md`                                                           |
| 10.11.3           | Deep audit: Ra cap always active; zero-flow 1.4e-3 m/day does not close the gap; production unchanged                  | `db0524e`                       | `docs/validation/stage10.11.3_natural_convection_physics_audit.md`                                                                                                       |
| 10.12             | Prognostic internal temperature (two-node lumped, switch fully gates the stage); stdlib dependency removed             | `a5fc4c5`, `608b4c5`, `14c5fee` | `docs/validation/stage10.12_internal_thermal_evolution.md`                                                                                                               |
| 10.13 (A–C)       | Low-flow closure: scientific formulation → research prototype → production integration behind an OFF-by-default switch | `acb9c7a`, `8bc1216`, `caa7799` | `docs/validation/stage10.13_diffusion_limited_low_flow_design_note.md`, `docs/validation/stage10.13_phase_b_results.md`, `docs/validation/stage10.13_phase_c_results.md` |
| 10.14             | Re-scoring of the 10.8.2 observational set against the 3eq (10.10/10.10.1) and 3eq+natural (10.11) closures: u>0 metrics (teq worse than bulk; NJ80 mismatch persists), quiescent teq_nat 5/5 in band at lab scale (10.11.3 gap scale-qualified); Python 177 checks; no calibration, no production change | `ca60c62`                | `docs/validation/stage10.14_three_equation_rescoring.md`                                                                                                             |
| 10.15             | Operational end-to-end demonstration: 30-day real-forcing Lagrangian iceberg run (TEST_11: trajectory, mass −15.4 %, 7/7 checks; diagnostics 7/7, 7 figures) + full-model 1/7-day runs (exit 0; 3D ocean NaN from day 1 — pre-existing Stage 8 family); T-12 symlink prerequisite exercised; dependency audit; key finding: production executable does not run the iceberg module | `472fe75`                | `docs/validation/stage10.15_operational_demonstration.md`                                                                                                             |
| 10.15.1           | Trajectory continuity and output integrity audit (follow-up to 10.15): model-space x/y continuous and kinematically consistent (implied speed == reported, corr 0.988), but geographic lat/lon has 8 real jumps (~0.17°, ~19 km) at model-cell crossings — root cause: transposed bilinear weights in `model_coords_to_latlon`/`bilinear_interp_3d` (T-13); audit-only (source NOT changed); corrected projection continuous; 28 Python regression checks; existing Fortran coord tests miss the bug (node sampling + 0.2° tolerance) | — (pending)               | `docs/validation/stage10.15.1_trajectory_continuity_audit.md`                                                                                                         |

## Stage 9 — minimal Lagrangian iceberg model

| Stage                  | Summary                                                                                                             | Report                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 9.1                    | Forensic reconstruction and physical specification                                                                  | `docs/wiki/stages/stage09/Stage9.1_*.md`  |
| 9.2                    | Minimal Lagrangian model                                                                                            | `docs/wiki/stages/stage09/Stage9.2_*.md`  |
| 9.3                    | Scientific verification + TEST_11 (30-day run, 74.5% mass loss, 0.013% budget error)                                | `docs/wiki/stages/stage09/Stage9.3_*.md`  |
| 9.4A                   | Lagrangian-core correction: motion + position-dependent forcing; lat/lon updated each step                          | `docs/wiki/stages/stage09/Stage9.4A_*.md` |
| 9.4B                   | Numerical verification, forcing-pipeline audit, force budget (9 plots)                                              | `docs/wiki/stages/stage09/Stage9.4B_*.md` |
| 9.4C / 9.4C.1 / 9.4C.2 | Critical verification fixes; latent-heat, solar-radiation audits, test inventory; surface energy-balance correction | `docs/wiki/stages/stage09/Stage9.4C*`     |

## Stage 8 — ocean initialization and spin-up

EN4 preprocessing, energy-instability forensics, thermal-wind correction,
controlled spin-up, operator splitting, predictor–corrector coupling, forensic
reconstruction of the legacy iceberg module. Reports: `docs/wiki/stages/stage08/`
(8.0–8.7). Key commits: `a0e99c4`, `1977b05`, `1963ef1`.

## Stage 7 — real grid, ice and ocean initialization

Real-grid reconstruction from IBCAO V5.2, real ice initialization
(OSI-SAF SIC + C3S CS2SMOS SIT), ocean-initialization forensics and
stabilization (7.7A–7.9). Reports: `docs/wiki/stages/stage07/` (7.1–7.9).
Key commits: `69e0303`, `e694372`, `ec76d5c`, `b73bfe7`.

## Stage 6 — real data and domain

Real-file recovery, Barents research domain, calendar semantics, unit audit,
ERA5 data. Reports: `docs/wiki/stages/stage06/` (6.1–6.7).
Key commits: `b591055`, `1e565db`, `0101957`, `3f1182b`, `6b37d9c`.

## Stage 5 — thermodynamics (HEAT)

Heat-block enablement and validation, snowfall, multi-month integration,
NetCDF-output unit audit. Reports: `docs/wiki/stages/stage05/` (5.1–5.5b).
Key commits: `298b6f9`, `09653fc`, `a731e87`.

## Stage 4 — ERA5 and EOS precision

ERA5 integration, January 2020, convective-cycle root cause (float32 EOS
quantization), precision study. Reports: `docs/wiki/stages/stage04/` (4.1–4.4).
Key commits: `c3ac6d8`, `5a2e0ea`.

## Stage 3 — dynamics restoration

3D-momentum restoration (blocks 200/210/280), baroclinic–barotropic coupling,
real grid. Reports: `docs/wiki/stages/stage03/` (3.3–3.5).
Key commits: `fffa04d`, `45a472c`.

## Stages 1–2 — base integration

ERA5 forcing integration, diagnostic output, test scaffolding. Commits:
`5a2e0ea`, `21a6bf7` and others.

---

## Notes

- Test counts in these records reflect the state at stage completion; current
  counts are in `docs/model/model_physics_status.md`.
- "`+`" after a commit denotes subsequent commits of the same stage.
