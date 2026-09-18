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
| `stage10.16_drift_dynamics_t07_investigation.md`       | 10.16           | COMPLETED (investigation; T-07 partially explained) | Controlled experiments A–K (wind/current/Coriolis/timestep/size/drag): the low wind-drift ratio is the physically correct **Coriolis-limited equilibrium** u = F_wind/(M·f) of a 100-m cube (analytic match 0.1 %; ratio ∝ 1/L; C_Dw-independent); 1–2 % reference assumes drag-limited regime or wind-driven (Ekman) current absent from the offline model; secondary numerical damping 1/√(1+(f·dt)²) ~11 % at dt=3600 s; NO source change; TEST_11 re-run byte-identical |
| `stage10.17_melt_thermodynamic_budget_audit.md`        | 10.17           | COMPLETED (audit; no correction) | Melt/thermodynamic budget audit: mass ≡ ρ_i·L·W·H (max 1.5e-5 rel), model budget closure 5e-4 % over 30 d; **lateral legacy melt dominates 96.8 %** (C_LATERAL = 1e-6 m/(s·K), velocity-independent, near-constant 0.26 m/day); basal 3.0 % (bulk, U_rel-limited), surface 0.12 % (winter), vapor 0.08 %; scalings verified (U^0.5/U^0.8, ΔT-linear, L^-0.2, 1/L, dt-insensitive); findings: lateral full-height area vs submerged convention in dead helpers (F2), q_net_surface dimensional defect (F3), diag%q_cond/q_bot never populated (F5), CSV format defect (F4) — all diagnostics-only, no physics change; TEST_11 re-run byte-identical (15 shared columns); 90-day diagnostic run −42.2 % (Q1 atmosphere cycle, ocean frozen at January — annual extrapolation premature); 47+7 Fortran + 40 Python checks |
| `stage10.18a_lateral_melt_parameterization_audit.md`   | 10.18A          | COMPLETED (research audit; no production change) | Lateral melt parameterization research audit: independent reference layer `python/validation/lateral_melt.py` reproduces production exactly (replay dM 15.43 %/lateral 96.83 % vs production 15.41 %/96.8 %); **legacy C_LATERAL = 1e-6 m/(s·K) ≡ forced-convection side melt at U_eq ≈ 0.30 m/s** (γ_T = 304 W/(m²·K)) vs simulated U_rel 0.005–0.027 m/s (factor 10–60); literature-based velocity-dependent variants (bulk/Bigg1997 K=0.58/plume, +Neshyba–Josberger buoyant) give 30-day lateral 0.013–0.052 m/day (5–20× below legacy) and ΔM 1.3–3.6 % (vs 15.4 %) — **lateral dominance formulation-dependent**; geometry ambiguity quantified (submerged full-perimeter vs full-height = 1.77× volume; depth-only 1.13 = Stage 10.17 F2); scalings verified (U^0.8/U^0.5, D^-0.2/D^-0.5, ΔT-linear, legacy U^0); wave erosion NOT TESTABLE; literature brackets legacy but does not validate; decision OPTION D; git diff `src/`/`test/` empty; 458 Python checks + 10 figures |
| `stage10.18b_observational_constraint.md`              | 10.18B          | COMPLETED (observational constraint; no production change) | Observational constraint and parameterization discrimination: curated dataset `data/validation/observations/iceberg_lateral_melt_observations*.csv` (17 cases, 9 sources; RH80 lab DIRECT 5, Sermilik + Antarctic + velocity INDIRECT 12; every number from fetched primary texts; Grand Banks/Barents side-melt obs unverified & excluded); prediction engine `python/validation/observational_constraint.py` + 62 independent tests + analysis (`stage10_18b_observational_constraint.py`, 10 figures); **directly comparable N=5 (RH80 lab only)** — leave-one-source-out NOT APPLICABLE; quiescent lab melt 0.04–1.6 m/day **requires a buoyant/plume U=0 term** (BULK/BIGG → 0, bias −0.56 m/day); lab temperature dependence **nonlinear ΔT^1.5** (legacy linear over-predicts 3.6× at 1.8 K → 1.1× at 19.8 K); legacy lateral exceeds observed **total** submarine melt in 3/4 Antarctic cold-shelf cases; observational **C_eff N=9 median 5.43e-7 = 0.54× production** (range 0.28–1.06×; Thwaites slope 24 m/a/°C = 0.76×); legacy equivalent-U 0.30 m/s is 10–15× above observed Sermilik velocities (0.018–0.023 m/s); velocity dependence qualitatively supported but not field-quantified; **geometry and wave erosion NOT CONSTRAINED**; **decision OPTION E** (insufficient discrimination) + **production KEEP_CURRENT**; git diff `src/`/`test/` empty; 62 Python checks + 10 figures |
| `stage10.18c_existing_observations_reanalysis.md`      | 10.18C          | COMPLETED (observations reanalysis; no production change) | Existing observations reanalysis and velocity-resolved melt constraint: reanalyzed dataset `data/validation/observations/stage10.18c/` (18 rows; explicit independence/melt-definition/velocity classification) + analysis (`stage10_18c_existing_observations.py`, 10 figures) + tests (`test_stage10_18c_observations.py`, 61 checks); **methodological corrections to 10.18B** (RH80 = PUBLISHED_FIT_EVALUATION of ONE fit, NOT 5 independent observations; C_eff_lab vs C_eff_submarine separated; Moyer19 = u_ice NOT u_rel; nonzero U=0 melt = NONZERO_BUOYANCY_OR_FREE_CONVECTION_COMPONENT; Enderlin23 slope = submarine sensitivity); Schild21 raw GPS/CTD/multibeam data identified at Arctic Data Center (no ADCP → U_rel impossible); Enderlin23 individual-iceberg dataset identified at USAP-DC 601679 (account-gated, not retrieved); **FIELD velocity-resolved cases (melt+ΔT+U_rel) = 0** — velocity dependence NOT IDENTIFIABLE quantitatively; RH80 curve-evaluation diagnostics (legacy +0.198 bias low-ΔT; BULK/BIGG 0 at U=0); legacy lateral > total submarine melt in 3/4 Antarctic cold-shelf region cases; C_eff_lab_lateral 0.54× / C_eff_submarine 0.59× production (separate; compatible, not validated); geometry/side-basal/wave NOT CONSTRAINED; **decision OPTION D** (bounds) + OPTION E elements; **production KEEP_CURRENT**; git diff `src/`/`test/` empty; 61 Python checks + 10 figures |

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
Stage 10.16 investigates T-07 with controlled experiments (A–K): the low
wind-drift ratio is the physically correct Coriolis-limited equilibrium
u = F_wind/(M·f) of a 100-m cube (analytic match 0.1 %; ratio ∝ 1/L;
C_Dw-independent; wind ≈ Coriolis ≫ water drag at equilibrium). The 1–2 %
reference assumes a drag-limited regime or a wind-driven surface current
absent from this offline model; a secondary numerical damping
1/√(1+(f·dt)²) ≈ 0.89 at dt = 3600 s contributes ~11 %. No source
correction was made; the repeated TEST_11 run is byte-identical to 10.15.2.

Stage 10.17 audits the melt and thermodynamic budgets with controlled
experiments (A–K) and the extended real-forcing TEST_11: mass is
identically ρ_i·L·W·H (max rel diff 1.5e-5), the model budget closes to
5e-4 % over 30 days, and the legacy **lateral melt dominates (96.8 %)**
via the constant C_LATERAL = 1e-6 m/(s·K) at ⟨ΔT⟩_D ≈ 3 K — a documented
simplification, not a bug. Findings are diagnostics-only (lateral
full-height vs submerged area convention in unused helpers; q_net_surface
dimensional defect; unpopulated diag%q_cond/q_bot; non-CSV trajectory
format). A 90-day diagnostic run (Q1 atmosphere, ocean frozen at January)
loses 42.2 % of mass — annual extrapolation is premature. No physical
correction was made; TEST_11 remains byte-identical to 10.15.2/10.16.

Stage 10.18A is a research/sensitivity/parameterization audit of the lateral
melt closure: an independent reference layer (`python/validation/lateral_melt.py`)
reproduces production exactly (30-day replay: dM 15.43 %/lateral 96.83 % vs
production 15.41 %/96.8 %), then quantifies the formulation sensitivity. The
legacy constant C_LATERAL = 1e-6 m/(s·K) is equivalent to forced-convection
side melt at **U_eq ≈ 0.30 m/s** (γ_T = 304 W/(m²·K)), while the simulated
U_rel at the draft is 0.005–0.027 m/s — a factor 10–60. Every
literature-based velocity-dependent variant (model-consistent bulk closure,
Bigg et al. 1997, FitzMaurice et al. 2017 plume, + Neshyba–Josberger buoyant
term) gives 30-day lateral melt 0.013–0.052 m/day (5–20× below legacy) and
total ΔM 1.3–3.6 % (vs 15.4 %): **the dominance of lateral melt is
formulation-dependent, not a robust physical outcome**. The geometry
ambiguity is quantified (submerged full-perimeter vs production full-height
= factor 2·ρ_i/ρ_w = 1.77 by volume; depth-only 1.13, the Stage 10.17 F2
quantity). Wave erosion is **NOT TESTABLE** with the current forcing (no
wave fields; White et al. 1980 / Kubat et al. 2007 equations unverified).
Literature brackets the legacy rate (Sermilik model 0.06–0.10 m/day,
observational estimate ~0.39 m/day; C&S 2023 side-melt max 0.2 m/day) but
does not validate it. **No production physics change** (git diff on `src/`
and `test/` is empty); decision **OPTION D** — a dedicated
observational/calibration constraint stage is required before any production
change; T-07 remains untouched.

Stage 10.18B adds the observational constraint: a curated 17-case dataset
(RH80 lab DIRECT; Sermilik + Antarctic + velocity INDIRECT; every number from
a fetched primary text; Grand Banks/Barents side-melt observations unverified
and excluded) and an independent prediction/comparison engine. The directly
comparable set is the Russell-Head lab (N=5), so leave-one-source-out is NOT
APPLICABLE. The lab evidence requires a nonzero-at-U=0 (buoyant/plume) term —
the forced-convection-only variants (BULK, BIGG) predict zero and fail — and
shows a nonlinear ΔT^1.5 temperature dependence that the linear legacy
over-predicts at low ΔT (3.6× at 1.8 K). The legacy lateral rate exceeds the
observed total submarine melt in 3/4 Antarctic cold-shelf cases. The
observational C_eff distribution (N=9, median 0.54× production, range
0.28–1.06×; Thwaites slope 24 m/a/°C = 0.76×) brackets the production
constant without uniquely determining it; the legacy equivalent-U (0.30 m/s)
is 10–15× above observed Sermilik iceberg velocities (0.018–0.023 m/s).
Velocity dependence is qualitatively supported but not field-quantified;
geometry (full-height vs submerged) and wave erosion are NOT CONSTRAINED by
available observations. **Decision: OPTION E** (insufficient discrimination;
multiple formulations remain observationally plausible) with **production
KEEP_CURRENT**; no production physics change (git diff on `src/` and `test/`
is empty); next: Stage 10.18C targeted observational design.

Stage 10.18C reanalyzes the existing observations with explicit
methodological corrections: the RH80 rows are evaluations of **one published
laboratory fit** (NOT five independent observations); the field effective
coefficient is a **submarine-total** quantity (C_eff_submarine), kept
separate from the lab lateral coefficient (C_eff_lab_lateral); Moyer19 speeds
are **iceberg translational velocities**, not U_rel; nonzero quiescent melt
indicates a buoyancy/free-convection component (not necessarily a plume
mechanism); the Enderlin23 thermal slope (24 m/a/°C) is a submarine-melt
sensitivity. Data recovery: Schild21 raw GPS/CTD/multibeam records exist at
the Arctic Data Center (no ADCP/current-meter data); Enderlin23 individual
iceberg CSVs exist at USAP-DC 601679 (account-gated, not retrieved). **No
field case provides simultaneous melt + ΔT + U_rel: the velocity-resolved
field subset is empty, and velocity dependence is NOT IDENTIFIABLE
quantitatively.** Legacy over-predicts cold low-ΔT (lab + Antarctic shelf);
geometry distribution, side/basal separation and wave erosion are NOT
CONSTRAINED. **Decision: OPTION D** (existing observations provide useful
bounds) with OPTION E elements; **production KEEP_CURRENT**; no production
physics change (git diff on `src/` and `test/` is empty); next: Stage 10.18D
(velocity-resolved observational upgrade: Enderlin23 per-iceberg retrieval +
ADCP-equipped campaign design).

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
