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
| 10.15.1           | Trajectory continuity and output integrity audit (follow-up to 10.15): model-space x/y continuous and kinematically consistent (implied speed == reported, corr 0.988), but geographic lat/lon has 8 real jumps (~0.17°, ~19 km) at model-cell crossings — root cause: transposed bilinear weights in `model_coords_to_latlon`/`bilinear_interp_3d` (T-13); audit-only (source NOT changed); corrected projection continuous; 28 Python regression checks; existing Fortran coord tests miss the bug (node sampling + 0.2° tolerance) | `d1bfc30`               | `docs/validation/stage10.15.1_trajectory_continuity_audit.md`                                                                                                         |
| 10.15.2           | Coordinate mapping and bilinear interpolation fix (T-13): cross terms swapped in `bilinear_interp_3d` + `model_coords_to_latlon` (wx along j/X, wy along i/Y); new Fortran regression `iceberg_test_bilinear_axis_regression` (13 checks — FAILS pre-fix, PASSES post-fix, incl. 0.17° boundary-jump detection); TEST_11 re-run: 0 jumps, corr(implied geo, reported)=0.988; drift-scaling numbers unchanged → T-07 remains OPEN; no physics/default change | `93b8554`               | `docs/validation/stage10.15.2_coordinate_mapping_bilinear_fix.md`                                                                                                         |
| 10.16             | Drift dynamics and T-07 investigation: controlled experiments A–K (wind/current/Coriolis/timestep/size/drag) + force-balance diagnostics; **T-07 PARTIALLY EXPLAINED** — the low wind-drift ratio (0.04–0.13 %) is the physically correct Coriolis-limited equilibrium u = F_wind/(M·f) of a 100-m cube (analytic match 0.1 %; ratio ∝ 1/L; C_Dw-independent; wind ≈ Coriolis ≫ water drag); the 1–2 % reference implies a drag-limited regime or wind-driven (Ekman) surface current absent from the offline model; secondary numerical damping 1/√(1+(f·dt)²) ≈ 0.89 at dt=3600 s (~11 %); NO source change; new tests `iceberg_test_drift_dynamics` (16) + `test_stage10_16_drift_scaling.py` (13); TEST_11 re-run byte-identical | `b4d62bf`               | `docs/validation/stage10.16_drift_dynamics_t07_investigation.md`                                                                                                         |
| 10.17             | Melt and thermodynamic budget audit: mass ≡ ρ_i·L·W·H (max 1.5e-5 rel), model budget closure 5e-4 % (30 d); **lateral legacy melt dominates 96.8 %** (C_LATERAL = 1e-6 m/(s·K), velocity-independent, 0.26 m/day at ⟨ΔT⟩_D ≈ 3 K); basal 3.0 %, surface 0.12 %, vapor 0.08 %; scalings verified (U^0.5/U^0.8, ΔT-linear, L^-0.2, 1/L, dt-insensitive); findings diagnostics-only (lateral full-height vs submerged area convention in unused helpers; q_net_surface dimensional ÷dt defect; diag%q_cond/q_bot never populated; TEST_11 CSV format defect); extended TEST_11 diagnostics (24 columns, 15 shared byte-identical); 90-day diagnostic run −42.2 % (Q1 atmosphere, ocean frozen — annual extrapolation premature); **NO physics correction**; new tests `iceberg_test_10p17_melt_budget` (47) + `iceberg_test_10p17_90day` (7) + `test_stage10_17_melt_budget.py` (40) | `022f871`               | `docs/validation/stage10.17_melt_thermodynamic_budget_audit.md`                                                                                                         |
| 10.18A            | Lateral melt parameterization research audit: independent reference layer `python/validation/lateral_melt.py` (legacy full-height/submerged, bulk velocity-dependent, Bigg1997, Neshyba–Josberger, FitzMaurice plume) + 458 analytic checks + analysis `stage10_18a_lateral_melt.py` (sensitivity matrix ΔT×U×L, TEST_11 offline replay of 6 variants, 10 figures); reference layer reproduces production exactly (replay dM 15.43 %/lateral 96.83 % vs production 15.41 %/96.8 %); **legacy C_LATERAL ≡ forced-convection side melt at U_eq ≈ 0.30 m/s** (γ_T = 304 W/(m²·K)) vs simulated U_rel 0.005–0.027 m/s (factor 10–60); velocity-dependent literature variants give 30-day lateral 0.013–0.052 m/day (5–20× below legacy) and ΔM 1.3–3.6 % (vs 15.4 %) — **lateral dominance is formulation-dependent**; geometry ambiguity quantified (submerged full-perimeter = 1.77× full-height volume; depth-only 1.13); scalings verified (U^0.8/U^0.5, D^-0.2/D^-0.5, ΔT-linear; legacy U^0); wave erosion NOT TESTABLE (no wave fields, primary sources unverified); literature brackets legacy (Sermilik 0.06–0.10 m/day model / ~0.39 obs; C&S2023 side max 0.2 m/day) but does not validate; **NO production physics change** (git diff `src/`/`test/` empty); decision **OPTION D** — dedicated observational/calibration constraint stage required before any production change; T-07 untouched | `0504853`             | `docs/validation/stage10.18a_lateral_melt_parameterization_audit.md`                                                                                                     |
| 10.18B            | Observational constraint and parameterization discrimination: curated observational dataset `data/validation/observations/iceberg_lateral_melt_observations*.csv` (17 cases, 9 sources; RH80 lab DIRECT 5, Sermilik/Antarctic/velocity INDIRECT 12; every number from fetched primary texts; Grand Banks/Barents side-melt obs unverified & excluded) + prediction engine `python/validation/observational_constraint.py` + analysis `stage10_18b_observational_constraint.py` (normalization, comparison, filtered statistics, C_eff, bounded comparison, 10 figures) + 62 independent tests; **directly comparable N=5 (RH80 lab only)** — leave-one-source-out NOT APPLICABLE; quiescent lab melt 0.04–1.6 m/day **requires buoyant/plume U=0 term** (BULK/BIGG → 0, bias −0.56 m/day); lab ΔT dependence **nonlinear ΔT^1.5** (legacy linear over-predicts 3.6× at 1.8 K → 1.1× at 19.8 K); legacy lateral exceeds observed **total** submarine melt in 3/4 Antarctic cold-shelf cases; observational **C_eff N=9 median 0.54× production** (range 0.28–1.06×; Thwaites slope 24 m/a/°C = 0.76×); legacy equivalent-U 0.30 m/s above observed Sermilik velocities (0.018–0.023 m/s); velocity dependence qualitative; **geometry and wave erosion NOT CONSTRAINED**; decision **OPTION E** (insufficient discrimination) + **production KEEP_CURRENT**; **NO production physics change** (git diff `src/`/`test/` empty) | — (pending)             | `docs/validation/stage10.18b_observational_constraint.md`                                                                                                     |

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
