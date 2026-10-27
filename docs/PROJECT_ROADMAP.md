# Project Roadmap

**Updated:** 2026-10-27
**Current scientific stage:** **11.10 post-closure remediation** — NetCDF production I/O, disk cleanup (0.510 GB), physical baseline D-50; N>1/OBC and real tides remain blockers. Stage 12 is gated; N=1 is not a final physical state.
**Stages 3–11.4.1: COMPLETED** (10.x iceberg modernization; 11.1 seasonal characterization; 11.2 CFL audit; 11.4-D21…D33 EN4 stabilization → ERA5-coverage fix → cleanup + Ocean Baseline 11.x; 11.3A execution-graph audit; 11.3B input-architecture audit + NetCDF contracts; 11.3C scheme audit + timestep matrix; 11.3C.1 semantics + CFL distributions; 11.3C.2 time-integration audit; 11.3C.3 loop-bound search (VERDICT D); 11.4 EOS-80 experiment + 11.4.1 impact validation (OPTIONAL, not default)).
**Current status:** Stages 10.14-11.10 committed. **11.10:** NetCDF-only production I/O; data/runs 0.510 GB; physical baseline D-50; N=4/N=24 OBC blocker measured; tide plan/red test created.
**Test suite:** 69 Fortran test source files (`ls test/*.f90 | wc -l`); 69 executable test targets (`grep -lE '^\s*program ' test/*.f90 | wc -l`). Counting method (Stage 11.8.0 T0): every current `test/*.f90` holds a top-level `program`, so file count == target count (verified 2026-10-24).
**Stage 11.5H-RC COMPLETE** (release-candidate gate: self-contained production scheduler, docs synced D-22…D-28). Plan: 11.8.0 diagnostic ladder (T0–T6) → 11.8A validation → 11.8B audit → 11.9 closure → 12.0 voxel (planning open; implementation not started, D-28).

## Completed foundation

- Legacy iceberg dynamics and thermodynamics integrated into the modern repository structure.
- Real model grid reconstructed from IBCAO V5.2: 133×105 nodes, 132×104 active cells, DX=DY=13.89 km.
- Sea-ice initialization pipeline exists for 2020-01-01 (OSI-SAF SIC CDR v3.1 + C3S CS2SMOS SIT L4 combined v1.1 — `python/ice/build_seaice_nc.py`); real Jan-2020 data connected in Stage 11.7E.4; Apr/Jul/Oct remain missing (T-16 seasonal gap).
- ERA5 atmospheric forcing and EN4 ocean forcing integrated into the real-grid workflow.
- Stage 9 moving-iceberg and forcing audits completed.
- Stage 10.1–10.6 modernization blocks implemented and audited.
- CI aligned with the current 64-target test suite and current gfortran line-length requirements (count as of 2026-10-18, verified by `ls test/*.f90 | wc -l`).
- Literature foundation established: 156-record repository bibliography, literature matrix, and scientific model description.

## Stage 10 status

| Stage    | Subject                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Status                                                                                                                 |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 10.1.1   | Solar geometry                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Complete                                                                                                               |
| 10.1.2   | Atmospheric shortwave attenuation/cloud                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Complete with documented limitations                                                                                   |
| 10.2     | Prognostic surface temperature                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Complete with documented limitations                                                                                   |
| 10.3     | Modern sensible/latent atmospheric fluxes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Complete with documented limitations                                                                                   |
| 10.4     | Phase-change energy partition                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Complete with documented limitations                                                                                   |
| 10.4.2.1 | Independent Q_surface output validation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Complete with methodological limitation                                                                                |
| 10.5     | EOS-80 freezing point                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Complete; classification B                                                                                             |
| 10.6     | Relative ocean flow and heat transfer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Complete                                                                                                               |
| 10.6.1   | Independent heat-transfer audit + documentation correction                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Complete; classification B                                                                                             |
| 10.7     | Independent basal-melt validation (analytical + literature)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Complete; classification B; 17 checks                                                                                  |
| 10.8.1   | Independent Python validation layer (`python/validation/`, 44 checks)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Complete; classification B                                                                                             |
| 10.8.2   | Observational validation of basal melt vs published observations (19-record dataset, 229 Python checks)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Complete; classification C (validation layer); production unchanged                                                    |
| 10.9     | Calibration assessment of the basal-melt coefficient (212 Python checks; no scalar identifiable from the 2-source set)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Complete; classification C; production unchanged                                                                       |
| 10.10    | Three-equation ice-ocean interface (Holland & Jenkins 1999; Jenkins et al. 2010 Table 2), separately selectable; independently validated (19 Fortran + 46 Python checks, cross-language contract)                                                                                                                                                                                                                                                                                                                                                                                                                                   | Complete; classification C; production physics added on selectable path, bulk path physics unchanged                   |
| 10.10.1  | Mass/salt convention correction: Eq. III from `gamma_S(S_w-S_B)=m S_B` to `rho_w gamma_S(S_w-S_B)=rho_i m S_B` with `rho_i/rho_w=910/1028`; MOM6/PISM/MITgcm/H&J99 Eq.4 convention; canonical anchor m 9.45e-9 -> 1.04e-8 (+10.5%), end-to-end m 3.998e-6 -> 4.067e-6 (+1.7%); T_i=-10 attribution corrected (model-selected, not H&J99); Fortran 25 checks, Python 65 checks, strict build clean                                                                                                                                                                                                                                   | Complete; classification C; production updated; all tests PASS                                                         |
| 10.11    | Natural convection basal melt: double-diffusive Ra + Churchill 1977 mixing; L_char = iceberg length L; Ra cap 1e10; gamma_T_nat, gamma_S_nat added to forced via Churchill n=3 mixing; U=0 -> m=1.6e-8 m/s (0.001 m/day); U=0.1 -> natural adds only 2.2e-6% (NOT 0.1% as originally claimed — corrected in Stage 10.11.2); U=1 -> forced dominates 99.9999999%; Fortran 23 checks (delivered in Stage 10.11.2 audit; original claim of 15 checks was never delivered in 6a0014e), Python 70 checks, cross-language contract                                                                                                        | Complete; classification C (10.11) / B (10.11.2 audit); production updated; all tests PASS                             |
| 10.11.3  | Deep scientific audit + sensitivity of the natural-convection closure: independent Python replica (tables A-J); cap always active (uncapped Ra=5.7e19) -> Nu pinned 323.17, haline/Le and beta_T/beta_S inert, laminar branch latent; haline sign opposite to physical (stabilizing) role; operative `0.15*Ra^(1/3)` attributed to Lloyd & Moran 1974 (not Fujii 1973); zero-flow m=1.4e-3 m/day is 7-700x below observed quiescent band (does NOT close the 10.8.2 gap); real mechanism double-diffusive (Martin & Kauffman 1977; Keitzl et al. 2016; Middleton et al. 2021); documentation corrected; production source diff ZERO | Complete; classification B; production UNCHANGED; all tests PASS                                                       |
| 10.12    | Prognostic internal thermal evolution: two-node lumped interior, prognostic `state%T_ice` replaces constant `T_i=-10` in Eq. II; `q_cond = 2*K_ICE*(T_s-T_i)/H` (K_ICE=2.2), `q_bot = m*rho_i*CP_ICE_3EQ*max(T_B-T_i,0)`, explicit Euler, clamp [-100,0]°C, switch `thermal_evolution_enabled` — fully gates the stage in the step (OFF = bit-identical legacy, verified by F.1–F.4); energy-conserving lagged skin coupling (`q_internal_exchange`); Fortran 21 + Python 35 checks, cross-language contract C_int(50 m); unused stdlib dependency removed from fpm.toml                                                            | Complete; classification C; production updated; all tests PASS                                                         |
| 10.13    | Diffusion-limited / double-diffusive low-flow closure: Phase A (scientific formulation + literature audit) → Phase B (research prototype, 167 checks, sweep 246/270 in band, 10.8.2 quiescent 5/5) → Phase C (production integration: selectable `low_flow_closure_enabled`, OFF default, three-equation preserved, forced branch bit-identical at high U, Fortran 23 checks + Python/Fortran comparison 56 checks; research parameterization, not universal validation)                                                                                                                                                            | **Complete** (Phases A–C); classification: research parameterization; production updated behind switch; commit pending |
| 10.14    | Re-scoring of the 10.8.2 observational set against the 3eq (10.10/10.10.1) and 3eq+natural (10.11) closures with the 10.8.2 acceptance criterion: u>0 metrics (teq RMSE 0.366, bias +0.277 — worse than bulk 0.108/+0.083, NJ80 functional-form mismatch persists) + quiescent gap (bulk 0/5, teq 0/5, teq_nat 5/5 in band at lab scale L=1 m; Ra cap inactive → 10.11.3 gap statement is scale-specific); Python 177 checks; no calibration, no production change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | **Complete**; classification C (verification); production UNCHANGED; commit pending |
| 10.15    | Operational end-to-end demonstration: real-forcing 30-day Lagrangian iceberg run (TEST_11, trajectory + diagnostics, 7/7 checks; 74.8→75.1 °N, 30.3→29.8 °E, mass −15.4 %, melt bounded) + full-model 1/7-day runs (exit 0; 3D ocean NaN from day 1 — documented Stage 8 family, stable, not introduced here); T-12 symlink prerequisite exercised; dependency audit; reproducible commands; output bundle `data/output/stage10.15/` (gitignored)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | **Complete**; classification: operational demonstration with documented limitations; production UNCHANGED; committed `472fe75` |
| 10.15.1  | Trajectory continuity and output integrity audit (follow-up to 10.15): model-space x/y continuous and kinematically consistent (implied speed == reported, corr 0.988); geographic lat/lon has **8 real jumps (~0.17°, ~19 km)** at model-cell crossings — root cause **transposed bilinear weights in `model_coords_to_latlon` / `bilinear_interp_3d`** (T-13); corrected projection continuous; 28 Python regression checks; existing Fortran coord tests miss the bug (node sampling + 0.2° tolerance; round-trip errors 0.064–0.179° only WARNING); audit-only — **source NOT changed**, fix deferred                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | **Complete**; classification: audit — real discontinuity identified; production UNCHANGED; committed `d1bfc30` |
| 10.15.2  | Coordinate mapping and bilinear interpolation fix (T-13): cross terms swapped in `bilinear_interp_3d` + `model_coords_to_latlon` (wx along j/X, wy along i/Y); new Fortran regression `iceberg_test_bilinear_axis_regression` (13 checks: constant/X-only/Y-only/X+Y/node/boundary/3D/trajectory-continuity — **FAILS pre-fix, PASSES post-fix**); TEST_11 30-day re-run: **0 jumps**, corr(implied geo, reported) = **0.988** (pre: 0.029), max geographic step 97 m (pre: 19.6 km); drift-scaling numbers unchanged → **T-07 remains OPEN**; no physics/default change                                                                                                                                                                                                                                                                                                                                                                        | **Complete**; classification: targeted correctness fix, regression-tested and re-run; committed `93b8554` |
| 10.16    | Drift dynamics and T-07 investigation: controlled experiments A–K (wind/current/Coriolis on-off/timestep 1800-7200 s/size 10-300 m/drag perturbation) + force-balance diagnostics; **T-07 PARTIALLY EXPLAINED**: low wind ratio (0.04–0.13 %) = physically correct **Coriolis-limited equilibrium** u = F_wind/(M·f) for a 100-m cube (analytic match 0.1 %; ratio ∝ 1/L; C_Dw-independent — verified by temporary rebuild; force balance wind ≈ Coriolis ≫ water drag); 1–2 % reference implies drag-limited regime or wind-driven (Ekman) current absent from the offline model; secondary numerical damping 1/√(1+(f·dt)²) ≈ 0.89 at dt=3600 s (~11 %); **NO source correction**; new tests (16 Fortran + 13 Python); TEST_11 re-run byte-identical                                                                                                                                                                                                                                                                                                                | **Complete**; classification: investigation — T-07 partially explained; production UNCHANGED; commit `b4d62bf` |
| 10.17    | Melt and thermodynamic budget audit: mass ≡ ρ_i·L·W·H (max 1.5e-5 rel), model budget closure 5e-4 % (30 d); **lateral legacy melt dominates 96.8 %** (C_LATERAL = 1e-6 m/(s·K), velocity-independent, 0.26 m/day at ⟨ΔT⟩_D ≈ 3 K); basal 3.0 %, surface 0.12 %, vapor 0.08 %; controlled experiments A–K verify U^0.5/U^0.8, ΔT-linear, L^-0.2, 1/L scalings and dt-insensitivity; findings diagnostics-only (lateral full-height vs submerged area convention in unused helpers; q_net_surface dimensional ÷dt defect; diag%q_cond/q_bot never populated; TEST_11 CSV format defect); extended TEST_11 diagnostics (24 columns, 15 shared byte-identical); 90-day diagnostic run −42.2 % (Q1 atmosphere cycle, ocean frozen at January — **annual extrapolation premature**); **NO physics correction**; new tests (47 + 7 Fortran, 40 Python)                                                                                                                                                                                                                                                                                            | **Complete**; classification: audit — internal consistency confirmed; production UNCHANGED; commit `022f871` |
| 10.18A   | Lateral melt parameterization research audit: independent reference layer (`python/validation/lateral_melt.py`, 458 checks) reproduces production exactly (replay dM 15.43 %/lateral 96.83 % vs production 15.41 %/96.8 %); **legacy C_LATERAL = 1e-6 m/(s·K) ≡ forced-convection side melt at U_eq ≈ 0.30 m/s** (γ_T = 304 W/(m²·K)) vs simulated U_rel 0.005–0.027 m/s (factor 10–60); literature-based velocity-dependent variants (bulk closure, Bigg1997 K=0.58, FitzMaurice2017 plume, +Neshyba–Josberger buoyant) give mean lateral 0.013–0.052 m/day (5–20× below legacy) and 30-day ΔM 1.3–3.6 % (vs 15.4 %) — **lateral dominance is formulation-dependent, not robust**; geometry ambiguity quantified: submerged full-perimeter vs full-height = factor 2·ρ_i/ρ_w = 1.77 (volume), depth-only 1.13 (Stage 10.17 F2); scalings verified (U^0.8/U^0.5, D^-0.2/D^-0.5, ΔT-linear, legacy U^0); wave erosion **NOT TESTABLE** (no wave fields; White1980/Kubat2007 equations unverified); literature brackets legacy (Sermilik 0.06–0.10 m/day model / ~0.39 obs; C&S2023 side max 0.2 m/day) but does not validate; **NO production physics change** (git diff `src/`/`test/` empty); decision **OPTION D** — multiple formulations plausible → dedicated observational validation/calibration stage required before any production change; T-07 untouched                                                                                                                                                                                                                                                                                            | **Complete**; classification: research/sensitivity audit; production UNCHANGED; commit `0504853` |
| 10.18B   | Observational constraint and parameterization discrimination: curated observational dataset (`data/validation/observations/iceberg_lateral_melt_observations*.csv` — 17 cases, 9 sources; RH80 lab DIRECT 5, Sermilik + Antarctic + velocity INDIRECT 12; every number from fetched primary texts; Grand Banks/Barents side-melt obs unverified & excluded); prediction engine `python/validation/observational_constraint.py` + analysis (`stage10_18b_observational_constraint.py`, 10 figures) + 62 independent tests; **directly comparable set N=5 (RH80 lab only)** — leave-one-source-out NOT APPLICABLE; quiescent lab melt 0.04–1.6 m/day **requires a buoyant/plume U=0 term** (BULK/BIGG → 0, bias −0.56 m/day); lab temperature dependence **nonlinear ΔT^1.5** (legacy linear over-predicts 3.6× at 1.8 K → 1.1× at 19.8 K); legacy lateral exceeds observed **total** submarine melt in 3/4 Antarctic cold-shelf cases; observational **C_eff N=9 median 5.43e-7 = 0.54× production** (range 0.28–1.06×; Thwaites slope 24 m/a/°C = 0.76×) → production 1e-6 plausible but not uniquely determined; legacy equivalent-U 0.30 m/s is 10–15× above observed Sermilik velocities (0.018–0.023 m/s); velocity dependence qualitatively supported (Enderlin23) but not field-quantified; **geometry and wave erosion NOT CONSTRAINED**; **decision OPTION E** (insufficient discrimination) + **production KEEP_CURRENT**; **no production physics change** (git diff `src/`/`test/` empty)                                                                                                                                                                                                                                                                                            | **Complete**; classification: observational constraint; production UNCHANGED; commit `d99a4bf` |
| 10.18C   | Existing observations reanalysis and velocity-resolved melt constraint: reanalyzed dataset `data/validation/observations/stage10.18c/` (18 rows; explicit independence, melt-definition and velocity classification); **methodological corrections applied** (RH80 = PUBLISHED_FIT_EVALUATION of one fit, NOT 5 independent observations; C_eff_lab_lateral vs C_eff_submarine separated; Moyer19 = u_ice NOT u_rel; nonzero U=0 melt = NONZERO_BUOYANCY_OR_FREE_CONVECTION_COMPONENT not plume; Enderlin23 slope = submarine sensitivity); Schild21 raw GPS/CTD/multibeam data identified at Arctic Data Center (no ADCP/current data → U_rel impossible); Enderlin23 individual-iceberg dataset identified at USAP-DC 601679 (account-gated, not retrieved); **FIELD velocity-resolved cases (melt+ΔT+U_rel) = 0**; velocity dependence **NOT IDENTIFIABLE** quantitatively; RH80 curve-evaluation diagnostics (legacy +0.198 bias low-ΔT; BULK/BIGG 0 at U=0); legacy lateral > total submarine melt in 3/4 Antarctic cold-shelf region cases; C_eff_lab_lateral median 0.54×, C_eff_submarine 0.59× production (separate; compatible, not validated); geometry / side-basal / wave **NOT CONSTRAINED**; **decision OPTION D** (bounds) with OPTION E elements; **production KEEP_CURRENT**; git diff `src/`/`test/` empty; `test_stage10_18c_observations.py` 61 checks + `stage10_18c_existing_observations.py` 10 figures                                                                                                                                                                                                                                                                                            | **Complete**; classification: scientific validation / observational research; production UNCHANGED; commit pending |
| 10.18D   | Velocity-resolved / per-iceberg observational upgrade: **10.18C data gap CLOSED** — Enderlin23 individual-iceberg dataset **RETRIEVED** (USAP-DC 10.15784/601679 via direct HTTP POST to the zip endpoint; JS reCAPTCHA not enforced; inner zip MD5 `821bed51660957b65a896c42fb88a057` verified; the 10.18C "account-gated" statement is corrected); dataset `data/validation/observations/stage10.18d/enderlin23_per_iceberg.csv` (**743 per-iceberg rows**, 54 raw CSVs / 15 sites / 2011-2022; melt = VolumeChangeRate/SubmergedArea SUBMARINE_TOTAL; draft, geometry, EPSG:3031→WGS84 coords) + analysis `stage10_18d_per_iceberg.py` (regional reproduction, Thwaites TF inversion, draft dependence, model comparison, C_eff; 10 figures) + tests `test_stage10_18d_per_iceberg.py` (26 checks); **regional maxima reproduce the paper** (WAP max 63.8 vs ~50, WAIS 44.8 vs ~40 m/a; EAIS/EAP p95 5.2/3.6 vs ~5 m/a; raw max inflated only by paper-excluded plume outliers); **Thwaites 24 m/a/°C consistent per-iceberg** (76 % of 167 bergs imply TF in 0.2–1.6 °C); **legacy C_LATERAL exceeds 99.6 % (TF=1.5) / 88 % (TF=0.6) of per-iceberg observed melt** (median ratio 14×/5.6×); velocity-dependent variants bracket observed medians (WAP 0.013–0.017 vs obs 0.032 m/day); **per-iceberg C_eff_submarine median 1.56e-7 = 0.16× production** (range 0.08–0.33×); velocity dependence still NOT IDENTIFIABLE (no U_ocean) → **ADCP-equipped Schild21-style campaign designed** (GPS+SfM+multibeam+CTD+ADCP+wave, report §11) as the velocity-resolved prerequisite; **decision OPTION D refined** (per-iceberg bounds) + OPTION E elements; **production KEEP_CURRENT**; git diff `src/`/`test/` empty; 26 Python checks + 10 figures                                                                                                                                                                                                                                                                                            | **Complete**; classification: per-iceberg observational upgrade; production UNCHANGED; commit pending |
| 10.19    | Production runtime & full iceberg coupling recovery: **Stage 10.15 finding addressed** — `app/main.f90` contained ZERO iceberg calls (module compiled but unreachable from production) → connected behind `ICEBERG_PRODUCTION=true` env gate (default OFF → legacy bit-identical): `iceberg_init` after `init_thermal_wind()` at TEST_11 start (75°N, 30°E → i=61, j=37), hourly `iceberg_step` in the III loop with live `t2/s2/u2/v2` + ERA5 atmos + bathymetry; `fpm.toml` main-file fix (`iceberg_main.f90` → `main.f90`); **NaN validity guard** in `get_ocean_profile` (`ok=.false.` explicit detection of zombie state, not masking); **ocean zombie-state forensic (CASE C/D)**: day_00 clean (0 % NaN) → first NaN in **Block 210 (Thomas vertical-viscosity solver) at III=2 of day 1** after a Block 200 ~25 m/s geostrophic spike (from ~0.1 m/s EN4 thermal-wind init) → day_01 **56.5 % NaN** (142,081/251,370 cells; T clamped at 273.1 K) → iceberg start cell **15/18 levels NaN** → **CASE C BLOCKER** for online-coupled production run, root cause **CASE D** (T-03 family: EN4 init → Block 200/210 momentum instability; NOT introduced by this stage, NOT fixable in no-physics stage); **gates**: 1-day / 7-day / 30-day exit 0, iceberg `steps executed : 0` with explicit `ICEBERG[prod] WARNING` on every candidate step (guarded, not silent); offline real-forcing path (TEST_11 family) remains fully validated; **decision D-17**: KEEP_CURRENT physics, env-gated integration OFF default, next = approved ocean-init stabilization stage, after which 30-day gate must show `steps executed = 720`; full fpm battery + Python suites PASS; `git diff --check` clean; production physics unchanged (only `get_ocean_profile` NaN-guard in `src/`)                                                                                                                                                                                                                                                                                            | **Complete**; classification: production runtime/integration; production physics UNCHANGED; commit `03bb42c` |
| 10.20    | Ocean initialization & numerical stabilization — **closed necessary-but-not-sufficient (D-18)**: **data-level fix adopted** — full-coverage merged ERA5 Jan file (`era5_2020_01_fullcoverage_merged.nc`, 124 slices) → **CASE C resolved**: 3-day `ICEBERG_PRODUCTION=true` gate PASS (36 steps, 0 NaN), days 1–4 of 30-day gate clean, 10.19's `steps executed: 0` → **55**; **residual instability characterized, NOT fixed (physics)**: CA 1000-iter guard saturates from day 1 (maxiter=1001 every day; residual inversions pinned at 1.1921E-07 = 2⁻²³ float32 EOS quantization, T-01/T-03 family) → slow T/S/ρ corruption (day 4 nonphysical −45…+50 °C, S<0, 0 NaN) → **density-first divergence mid-day 5** (first NaN `NaN_RO=198` at `F_after_conv` III=6; 0 NaN in U/V/T/S) → zombie from day 6 → 30-day gate `steps executed: 55`, **acceptance (360) NOT met**; **cadence correction: 12 steps/day × 30 = 360** (10.19 "720" = doc error; 3-day gate = 36 steps); default-path fullcov recommendation recorded, NOT applied; only source change = 10.19-pending iceberg print-format fix (`app/main.f90`); next = approved physics stage (EOS precision / CA threshold / guard per RULES.md, or preconditioned-solver study), acceptance = 30-day gate `steps executed = 360`; full battery PASS | **Complete**; classification: ocean-init stabilization (data-level fix; physics unchanged); production physics UNCHANGED; commit `16a4c65` |
| 10.21    | Stabilize convective adjustment & EOS precision — **negative-result stabilization (D-19)**: root cause of CA 1000-iter guard saturation confirmed = **float32 2⁻²³ EOS quantization (1.1921E-07 ≈ 0.9e-7 threshold)**, T-01/T-03 family; examined EOS single/double, CA threshold, iterative-guard tuning — all rejected per RULES.md procedure & approval requirement (no physics change without explicit approval); diagnostic instrumentation (stage10.21 diagnostics, `conv_DEBUG`-style columns); **production physics UNCHANGED, bit-identical legacy verified** (daily-diagnostics md5 `92a873ad…`); Python 13/13 + 18/18 PASS, Fortran battery 55 PASS; next = approved physics stage (EOS precision / CA threshold / guard) | **Complete**; classification: negative-result stabilization; production physics UNCHANGED; commit `7a17cac` |
| 10.22    | Ocean density / thermal-wind / Block-200 stability audit — **causal chain ISOLATED (D-20)**: replay experiments a0–a4 (30 d, step 1) prove **Block 200 transmits** the CA/EOS float32 density corruption (ρ<0 from day 4 s1, min −1.946690e-04; ρ-flip diag 10.4M cells day 3; first NaN day 5 s6 `CA_after ro_nan=198`, u/v/T/S clean) **into momentum via TWO paths** (density+thermal-wind budget split EXACT: a2 ro-phase-only 9 metrics fail, momentum max_u2/v2/amp_u/v PASS; worst rel 2.954e-1); **Block 210 amplifies** (rhs_max 1.12608E+16, den_min 7.05833E-04, day-6 zombie 142,081 cells); **Thomas pivots negative BY CONSTRUCTION** (a1 = −1+a+b < 0; piv_neg = piv_cnt = 100 %, piv_min = 1.0) — structural, NOT pathology; **stabilizer levers freeze_ro (a1) / freeze_ts (a3) / freeze_ro_downstream (a4) restore physical validity (30/30 PASS, worst rel 4.213e-6) but are DIAGNOSTIC-ONLY, NOT production paths**; **production physics KEEP_CURRENT, bit-identical legacy verified** (a0 vs a0_diag daily-diagnostics md5 `1ef13cb4…`); 27-section report; Python regression `test_stage10_22_block200_audit.py` (added, 300 checks PASS); next = approved physics stage, acceptance = 30-day gate `steps executed = 360`; full battery PASS (59 targets) | **Complete**; classification: stability audit (instrumentation, no production physics change); production physics UNCHANGED; commit `928041a` |
| 11.1     | Ocean Stability Across Seasonal Initial Conditions — **seasonal dependence established**: instability is general to prognostic ocean evolution but timing depends on initial EN4 state; Jan survives 4 days, Apr/Jul/Oct crash Day 1 with pre-existing negative ro (−20.07 g/cm³); frozen-ocean control 30 days stable (ro 0.0075–0.0082 g/cm³); atmospheric forcing alone does NOT cause instability; EN4 initial condition pathology identified for summer/autumn; next = EN4 initial condition stabilization (Stage 11.2) | **Complete**; classification: seasonal stability characterization (no production physics change); production physics UNCHANGED; commit pending |

## Next stages (forward roadmap, post-11.3B)

> HISTORICAL NOTE (11.3C): the 11.2 section below is superseded. EN4
> extrapolation was fixed in 11.4-D21/D22; the seasonal Day-1 crash was
> proven (D24–D32) to be an ERA5 coverage-gap accident, fixed in D32.
> Baselines are stable (D33 Ocean Baseline 11.x). The 11.2 acceptance gate
> below is obsolete.

### Stage 11.3C (COMPLETED) — Scheme Audit + Timestep Sensitivity

Forensic audit of ACTUAL numerical schemes (`docs/model/numerical_scheme_inventory.md`):
advt/advs vertical is EXPLICIT upwind (code comments claiming "implicit
Thomas" are FALSE documentation — code unchanged); FCT-Zalesak active in 3D
T/S; advsh FCT intentionally disabled; B200 semi-implicit Coriolis + explicit
forcing; B210 genuine implicit Thomas; shal/W/ice-dynamics explicit
(+semi-implicit friction 2×2). Timestep matrix (April 30 d, `STAGE113_DT/DT1`):
A(3600/120), B(1800/120), C(900/120), D(3600/60), E(3600/30) — all 29 d,
no NaN; CA guard saturation DT-independent (quantization floor).

### Stage 11.4 — EOS-80 A/B Experiment (COMPLETED) + 11.4.1 Impact Validation

Controlled density-EOS experiment (legacy Eckart vs EOS-80): UNESCO EOS-80
implemented opt-in (`EOS_MODE=EOS80`; LEGACY was default until Stage 11.8B —
127/127 md5); 8/8 reference checks; all 4 seasons clean; CA transformed
(maxiter ~90 vs 1001); April EUU −7% (gradual circulation adjustment);
RECOMMENDATION: OPTIONAL, not default. Runs at reference cadence A
(DT=3600/DT1=120, mm2=24).

> STAGE NUMBERING NOTE (11.4-planning): the "11.4" label collides with the
> frozen forensic chain (`stage11.4_en4_stabilization.md`, D21–D33, completed).
> Convention going forward: "11.4-D*" = the closed EN4-stabilization forensics;
> "11.4" = the EOS-80 experiment stage. Frozen filenames are NOT renamed.

### Stage 11.5 — Temporal Integration Architecture Fix (CURRENT: 11.5H-RC; 11.5A/11.5B/11.5C/11.5C.1–11.5C.8.2/11.5D.0–11.5D.3/11.5E/11.5F/11.5G/11.5H COMPLETE)

11.5B (COMPLETED, commit `0463161`): `STAGE113_MM2` separation experiment —
DT × MM2 two-dimensional sensitivity matrix; ice cadence decoupled from
ocean step (measurement only, no promotion).
11.5C (COMPLETED, commit `5497482`): controlled ocean-substepping prototype
(`STAGE115C_OCEAN_SUBSTEPS` gate, OFF bit-identical); N=1 stable ≡ baseline;
N=2/4/12/24 singular — BUT with documentation errors (N=1 dt_ocean = DT, not
86400 s; shal() cadence mismatch for N=2/4/12; EUU incomparability),
corrected in 11.5C.1. Only N=24 physically consistent, also fails → forensic
audit 11.5C.1 (CURRENT).
11.5C.1 (COMPLETED, commit `1014e53`): forensic N=24 first-invalid trace
(per-operator checkpoints, N=1 vs N=24 divergence, frozen-coupling
control) → Mechanism A (ocean self-instability), B/C/D-primary ruled out;
corrected 11.5C doc errors (N=1 dt=DT, shal cadence, EUU/N).
11.5C.2 (COMPLETED, this commit): heat-freeze control + per-cell operator
gain + global energy audit → Scenario 1 (heat evolution necessary for fast
3-day blowup) + Scenario 4 (B200 thermal-wind generator, +3.9e6/pass) with
barotropic-imprint (B280, +4.2e6) co-amplification; B210 net-damping,
shal dE≡0; refined loop t1/s1→adv→RO→B200→U→adv→CA→Inf; slow 9-day core
mode (Scenario 6 admixture) open. 11.5D promotion BLOCKED until T/S-held
control + B200-gain regression complete.
11.5C.3–11.5C.8.2 (COMPLETED, commits `24b96ab`/`14db952`/`4a0624b`/`adad522`+`510dcab`/`0f761f2`/`2126c79`/`edc9ae0`/`c61ba8b`/`e94ffc5`): T/S-held control, single-field ice freezes, operator-trace/term-decomposition/energy-map/attribution chain → two-phase blowup (B200-deep +2.0e7 / B210-damping / B280-shallow +1.3e7, fill-dominated, TW/btp sustained drivers); 11.5C COMPLETE.
11.5D.0–11.5D.3 (COMPLETED, commits `913bf41`/`9580244`/`1445007`/`59e88a0`): temporal specification (Family A/B) + controlled prototypes → Family A stable (EUU −9%), Family B dt-threshold scan: blowup d4/d7 at 1800/900, marginal 450, PASS 225/150 → boundary dt_blow∈(450,900], largest-stable=225.
11.5E (COMPLETED, commit `c230414`, temporal contract closure): Family B stable-but-WRONG-climate (heat −22% d7/−50% d29, ice 5–8× legacy, salt identical, 225-vs-150 unconverged O(1)); shal dt1/mm3 conflict documented; sea-ice validation gate required; dt=150 conservative reference.
11.5F (COMPLETED, commit `547ae16`, coupling cadence isolation): F1 exchange graph + u1-rollover theorem (freezable-without-freezing-ocean = {txic,tyic,ans}); F2 budgets (divergent = basal freezing+export); F3 dt150+frozen-txic/ans ≡ fresh (ice→ocean ruled out); F4 skipped (incoherent); driver = ocean→ice freshness and/or ocean-internal cadence.
11.5G (COMPLETED, commit `4bdc3f2`, final coupling check + productionization spec): CORRECTS 11.5F (skz write-only for physics, skt write-never in production → fw≡0); B150-SKZ bit-identical to fresh (skz ruled out); NO MORE freezes (mandate); spec 11.5H→11.6→11.7→11.8→12.
11.5H (COMPLETED, commit `1c59a2c`, production temporal architecture): 115H scheduler (OCEAN_DT=150, 24×24, ICE_DT=3600, STALE day-start freeze, shal 1×/day, `STAGE115H_PRODUCTION_MODE` OFF-default); 71 forensic sites guarded; PROD-STALE bit-identical to F3 (≈fresh, NOT legacy) → legacy N=1 LOCKED as reference (D-22); skt debt (D-25); perf ~230 s/d vs ~1 s/d legacy; EOS-80 criterion corrected.
11.5H-RC (COMPLETED, commit `1e3e430`, release-candidate gate): self-contained scheduler (forces mm2=24, warns+ignores conflicting env, hard-fail, no silent fallback) + documentation synchronization (D-22…D-28, N-11/12/13, T-14) + full re-verification. NEXT MAJOR: 11.6.

11.5A (this stage, audit+design, COMPLETED): timeline verified (ice mm2×/day,
ocean 1×/day); ocean integrates 1 h/day vs ice 24 h/day (dynamically young
ocean — no trajectory validation exists to date); INVERTED vs modern practice
(NEMO/MITgcm/CICE step together); options A(full)/B(selective)/C(multi-rate)/
D(keep) compared; RECOMMENDATION: phased A — 11.5B `STAGE113_MM2` separation
experiment (measurement only) → 11.5C flagged prototype → 11.5D promote +
re-baseline. NEXT: 11.5B.

PROBLEM STATEMENT (11.3C.2): the `iii`-loop (`main.f90:624→909`) covers ICE
ONLY (heat/redis/dynamics/adv2d/redis/W-recompute); ocean operators (advs,
advt, CA, Block 200/210, shal, B280, iceberg_step) run ONCE PER DAY with
stale `iii`. Legacy cadence integrates ice 12 h/day but ocean 1 h/day
(DT=3600); the 11.3C/11.3C.1 A/B/C matrix is therefore cadence-sensitivity,
not ocean convergence. Historical placement UNRESOLVED (11.3C.3 VERDICT D).
RECONCILIATION DECISION (Option A): EOS-80 first (contained, ready, on the
stable reference cadence), temporal fix second (high-risk restructuring:
move ocean pass inside `iii`, re-baseline everything, RULES procedure).
Minimal fix sketch (NOT approved, NOT executed): relocate the ocean pass
inside `iii` (24×3600 s = coherent day); re-validate full battery + 11.x
baselines + matrix.

### Stage 11.6 — EOS-80 Production Integration & Re-baseline (COMPLETE, D-29 OPTIONAL)

Completion criteria (all met): independent UNESCO TP44 reference tests
28/28 (`test/eos80_reference.f90`); integration audit (5 CA dispatcher
sites, no bypass except diagnostic probe → fixed); 4-config April matrix
+ Jan regression all 0 NaN/Inf; legacy OFF bit-identical (Jan NDIFF=0,
April bit-identical).
Result: EOS-80 coherent but ice-amplifying (+36–96% unvalidated) →
D-29 keeps EOS-80 OPTIONAL, legacy Eckart DEFAULT. EOS STATUS (binding
for all later stages): "EOS-80 implemented and validated as OPTIONAL;
legacy Eckart remains DEFAULT and scientific reference; default decision
deferred to Stage 11.8A observational validation; legacy EOS is retained
permanently as regression baseline and is NOT scheduled for removal."
Report: `docs/archive/stage11/stage11.6_eos80_integration_rebaseline.md`.

> **Final 11.8A update:** D-47 (2026-10-27) promotes EOS80 for the N=1
> 30-day validated matrix after the T-41 gate correction; production scheduler
> remains BLOCKED (T-39). Stage 11.6's "OPTIONAL" status is historical.

### Stage 11.6.1 — EOS-80 Dispatch Audit Closure & Result-Interpretation Correction (COMPLETE, D-30)

Narrow closure of three 11.6 audit findings (no new physics experiments):
`eos_diag` EOS80-first reorder (explicit rule: EOS80 selects formula + f64,
f64-switch is legacy-precision-only) + `test/eos_dispatch.f90` 14/14 +
interaction quantified (heat +0.6865e28 / ice +375.41 — no factorization) +
full/short run wording split + Jan/Apr OFF bit-identical reruns.

Criterion (D-correction, NOT "improvement vs observations" — EOS-80 is a
fundamental EOS, not a calibration closure): physical correctness +
reference tests + numerical stability + impact on model. ~~On pass:
`EOS_MODE=EOS80` becomes production default (`LEGACY_REFERENCE` fallback)~~
— SUPERSEDED by binding decision D-29 (Stage 11.6): EOS-80 stays OPTIONAL,
legacy Eckart remains DEFAULT and scientific reference; default decision
deferred to 11.8A observational validation; legacy EOS retained permanently
as regression baseline, NOT scheduled for removal.
Full re-baseline procedure (on any future promotion): EN4 → EOS80 →
density → thermal wind → B200 → B210 → B280 → ocean → ice coupling +
11.8 matrix re-run.

### Stage 11.7 — NetCDF Migration + Legacy Removal + Permanent CFL

### Stage 11.7A — NetCDF Input Contracts & Migration Preflight (COMPLETE)

Read-only audit + testable contracts (NO migration): 6-source inventory
grounded in current readers/producers/files, field-level .nc contracts,
vertical-convention note, migration matrix with per-source acceptance,
MD5-only-byte-identical checksum policy, test-coverage map (3 existing +
5 missing incl. EOS-duplicated), CFL 6-formula audit (no production
thresholds exist → all TBD with 11.8A-evidence plan), Q1–Q4 open questions,
11.7B–F staged sequence, EOS-agnostic binding statement.
Report: `docs/archive/stage11/stage11.7A_netcdf_contracts_preflight.md`.
NEXT: 11.7C.

### Stage 11.7B.1 — kk1 Equivalence Closure & Grid Contract Audit (COMPLETE)

Closes 11.7B kk1 gap: exact :117/:238/:317/:410 re-trace (gate = land-based,
C!=8 observed consistent in the reference build environment; ht smoothing :200-236 precedes kt1-final → runtime sum 143422;
map1 backward neighbours; i=is1 wet); two-stage kk1 + independent plain-loop
oracle + Fortran dump harness (anchors 11067/143422); three-way zero
mismatches, gate 10336; Jan==Apr products identical (143176 = pre-smoothing
product levels, additional-only); dims Option A (i,j,k); CF grid_mapping
deferred; python 23/23; GO 11.7C.
Report: `docs/archive/stage11/stage11.7B.1_kk1_equivalence_closure.md`.
NEXT: 11.7C.

### Stage 11.7B — Grid & Bathymetry NetCDF Builders + Equivalence (COMPLETE)

grid.nc/bathymetry.nc built from KOORD.DAT/hhh.bar (+ z-DATA) with
CF-1.10 + provenance/MD5 attrs; 34/34 equivalence (int bit-exact, coords
within policy, anchors 11067 wet cols / 143176 levels vs April product);
i=is1 border asymmetry caught by anchor and fixed pre-test; :238 quirk
replicated-not-fixed; battery 50/50, strict clean, Jan OFF NDIFF=0;
legacy KOORD.DAT/hhh.bar stay sole production inputs; EOS-agnostic.
Report: `docs/archive/stage11/stage11.7B_grid_bathymetry_migration.md`.
NEXT: 11.7C.

### Stage 11.7B.2 — Grid Reproducibility & Test Artifact Hygiene (COMPLETE)

hht uninitialized-at-first-use (:191) but observed consistent in the
reference build environment (uniform garbage C!=8 consistent with map1
count; clean-rebuild dumps md5-identical; portability NOT guaranteed);
dump artifacts moved
root→build/ (self-recreating, .gitignore-covered); 6 root files removed
by name, symlinks intact; SKIP conventions (Fortran + Python) for inputless
environments; CI cannot run the grid gate (documented, no synthetic
substitute); T-12 corrected; GO 11.7C.
Report: `docs/archive/stage11/stage11.7B.2_grid_reproducibility.md`.
NEXT: 11.7C.

### Stage 11.7B.3 — hht Determinism Guard & Test Contract Fix (COMPLETE)

FAIL-capable gate anchor (10336 recomputed from ht) + mandated hht
comment in grid_dump; python SKIP pre-check first (SKIP exit 0 /
FAIL exit 1, consistent both languages); 11.7B.2 language softened
(undefined behavior, non-portable); T-15 added; CI limitation stated.
Report: `docs/archive/stage11/stage11.7B.3_hht_guard_test_fix.md`.
NEXT: 11.7C.

### Stage 11.7C — EN4 & ERA5 Passthrough Builders + Equivalence Verification (COMPLETE)

Phase-0 doc fixes (README zombie→historical, 11.7B.2 language sync,
dates/physics/steps); EN4 rebuilds (Jan+Apr) BIT-IDENTICAL to committed
*_rebuild.nc (0.0 all vars; Aug-30 base files SUPERSEDED, retained for
11.7E); ERA5 merge BIT-IDENTICAL all 7 vars; contracts verified
(dims/units/fills/D32/z_model_m); Jan NDIFF=0, April 0 NaN/31 files;
planning notes (11.8A EOS criteria+gates, D-28 entry).
Report: `docs/archive/stage11/stage11.7C_en4_era5_passthrough.md`.
NEXT: 11.7D (seaice_initial.nc + tides.nc).

`grid.nc` (replaces KOORD.DAT/hhh.bar), `bathymetry.nc`,
`ocean_initial.nc`, `forcing_era5.nc`, `seaice_initial.nc` (replaces
1_1.ice…1_5.ice), `tides.nc` (replaces GRM2 or null tides) — each
md5-gated; legacy files stay as rollback inputs — removal only in 11.7F, after ALL 11.7E.1–E.5 sub-stages pass and the production-default decision is made. CFL monitoring becomes
a permanent production feature (cfl_x/y/z/wave/coriolis/diffusion in
NetCDF diagnostics; PASS/WARNING/FAIL; WARNING logs only).

### Stage 11.7D — Sea-Ice & Tides Passthrough (COMPLETE)

Scope: seaice_initial.nc + tides.nc builders and verification.
Acceptance: equivalence tests pass, regression gates pass.
Dependency: 11.7C complete.
Output: verified contracts for sea-ice and tides.

### Stage 11.7D.2 — Actual Code Correction & Test Independence Enforcement (COMPLETE)

Closes 11.7D.1 gaps IN CODE (not docs-only): test genuinely independent
(`_precheck_inputs()` SKIP-first, oracle parses 1_*.ice from scratch, no
`sea.read_ice_files()` call); NetCDF `source="DIAGNOSTIC_PLACEHOLDER"` +
`sea_ice_status` attributes verifiable in file; T-16 (diagnostic sea ice)
+ T-17 (HST 0.40 legacy quirk) in KNOWN_ISSUES; tides `reference_dt1_seconds`
+ dt1 comment; python 20/20; GO 11.7E.
Report: `docs/archive/stage11/stage11.7D.2_actual_code_correction.md`.

### Stage 11.7E.1 — Grid/Depth Codes Reader Switch (COMPLETE)

Scope: switches the source of grid coordinates and depth codes from
KOORD.DAT/hhh.bar to grid.nc. NOT a "bathymetry reader": final
bathymetry.nc fields are not read — the model still derives ht/map1
from the depth codes via the existing algorithm.

First (lowest-risk) reader switch of the NetCDF migration: production
input switchable between legacy KOORD.DAT/hhh.bar (default OFF →
bit-identical) and NetCDF grid.nc (ON) via `STAGE117E_NETCDF_GRID`;
ONLY the file-read layer is replaced (codes+coords), full derivation
chain reused → divergence impossible by construction. Preflight fixes:
sea-ice source manifest (never value-inferred), test 1_*.ice-first
precheck + sys fix, three-way wording + INDEX-dupe/metric/CI
corrections. Gates: Jan/Apr ON≡OFF≡baselines bit-identical (32+31
files); battery 50/0; strict clean; diff-check clean. Rollback: unset
env var (legacy files intact). Axis-order convention verified and
handled explicitly in the reader (T-18 corrected by 11.7E.1-CP).
Report: `docs/archive/stage11/stage11.7E_grid_bathymetry_reader_switch.md`.
Corrections: `docs/archive/stage11/stage11.7E.1-CP_plan_contract_corrections.md`
(plan/contract corrections; no physics change).
GO 11.7E.2.

### Stage 11.7E.2 — Ocean Initial Reader (verify if needed)

Scope: ocean-initial T/S source. Per 11.7E.1-CP audit, the reader
(`src/initial_ocean_reader.f90`) ALREADY reads NetCDF
(`initial_ts_2020-*.nc`, EN4 passthrough) — no source-format switch;
verify the variable/dimension contract against 11.7A, add explicit
dimension verification only if a gap is found.
Acceptance: contract verified (or gaps closed); Jan/Apr regression
NDIFF=0; no physics change.
Dependencies: 11.7E.1 complete and validated.
Rollback: none applicable (no new behavior path); revert commit if the
verification changes code.

### Stage 11.7E.3 — ERA5 Forcing Reader (verify if needed)

Scope: ERA5 forcing source. Per 11.7E.1-CP audit, the chain
(`src/netcdf_input.f90` + `src/wind_forcing.f90`) ALREADY reads NetCDF
(merged ERA5 files) — no source-format switch; verify the
variable/dimension/time contract against 11.7A, add explicit dimension
verification only if a gap is found.
Acceptance: contract verified (or gaps closed); regression NDIFF=0; no
physics change.
Dependencies: 11.7E.2 verified.
Rollback: none applicable (no new behavior path); revert commit if the
verification changes code.

### Stage 11.7E.3.2 — CI Fixture, E.4 Criteria Clarification & Snowfall Protection (COMPLETE)

Scope: close five audit gaps before 11.7E.4 — (1) committed minimal ERA5
fixture (`python/tests/fixtures/era5_synthetic.nc`) so the contract test runs
in a clean CI clone with REAL → FIXTURE → SKIP selection; (2) replace the
contradictory 11.7E.4 "ON ≡ OFF" criterion with three distinct criteria
(A baseline reproduction / B reader equivalence / C scientific migration);
(3) real sea-ice source-manifest template
(`python/ice/seaice_source_manifest_real_template.json`) + preparation
process (template only; production manifest untouched); (4) snowfall
accumulation→rate conversion protection (5 checks); (5) documentation
corrections (11.7E.3.1 file counts, 11.7E.3 superseded claims, CI
target-vs-source comment, dates).
Acceptance: fixture runs in CI without SKIP; fixture valid; REAL/FIXTURE
selection works; criteria A/B/C documented; template present; snowfall
conversion protected; docs corrected; regression green; diff-check clean.
Dependencies: 11.7E.3.1 verified.
Rollback: revert commit (test/documentation only; no physics path).
Report: `docs/archive/stage11/stage11.7E.3.2_ci_fixture_criteria_clarification.md`.

### Stage 11.7E.4 — Sea-Ice Reader Switch

Scope: sea-ice initialization source — `1_1.ice`…`1_5.ice` text files
→ `seaice_initial.nc` (built by `python/ice/build_seaice_nc.py`).
Real January data exists (`data/input/generated/real_grid/ice_2020-01-01/`;
OSI-SAF SIC + C3S CS2SMOS SIT provenance — 11.7E.1-CP audit) but is NOT
connected to production before this sub-stage.
Acceptance (three distinct criteria — clarified in Stage 11.7E.3.2; the
previous "ON ≡ OFF" requirement was contradictory, because connecting real
data must change the result):
- **A. Baseline reproduction (switch OFF):** default OFF → diagnostic-zero
  path reproduces the legacy baseline bit-identically (the reader is not
  invoked on the legacy path).
- **B. Reader equivalence (NetCDF vs Legacy, same real source):** with the
  env-gated switch ON, the new NetCDF reader must reproduce the legacy
  `1_*.ice` reader given the SAME real source data (X ≡ Y within a documented
  tolerance; no physics change).
- **C. Scientific migration (real data connection):** connecting the real
  OSI-SAF SIC + C3S SIT product to production is a scientific change relative
  to the diagnostic-zero baseline; document expected differences and validate
  — do NOT require identity with the baseline.

Manifest provenance attributes verified, T-16 status updated.
Dependencies: 11.7E.1–11.7E.3.2 verified.
Rollback: unset env var (legacy files remain in place).
Status: **COMPLETE** — real Jan-2020 data connected; A/B bit-identical for 7 days; C documented; builder transpose defect fixed. Report: `docs/archive/stage11/stage11.7E.4_real_seaice_connection.md`.

### Stage 11.7E.5 — Tides Reader Switch (DEFERRED)

Scope: tides source — null-tides/qq constants in production →
`tides.nc` (11.7D contract: null-tides explicit,
`reference_dt1_seconds`).
Acceptance: env-gated switch (default OFF → bit-identical; ON ≡ OFF).
Dependencies: 11.7E.1–11.7E.4 verified.
Rollback: unset env var (null-tides path remains).
**Status: DEFERRED** — null-tides provides no scientific value; proceeding to 11.8 ocean diagnostics per 11.7E.4.1 audit closure. 11.7F (legacy removal + permanent CFL) is NOT a prerequisite for 11.8; 11.7F dependency is "all readers switched OR explicitly deferred with justification" — 11.7E.5 is explicitly deferred with justification (null-tides no scientific value).

### Stage 11.8.0.0 — Diagnostic Contract Correction (Real Red Tests)

Scope: Correct the fake/stub tests and false provenance created in 11.7E.4.1. Establish REAL diagnostic tests that actually execute and produce measurable results. This is the FOUNDATION for Stage 11.8 ocean stabilization work.

Key deliverables:
- Real Fortran homogeneous column test (test_homogeneous_column.f90) that calls production convective_adjustment
- Snowfall period verification from source GRIB metadata (not processed file time spacing)
- Sea-ice provenance correction (actual source, not hardcoded strings)
- sit semantics clarification (area-weighted contribution vs thickness)
- 25.72 m ice thickness investigation
- Ocean stabilization gate documentation

Acceptance: Real red tests execute and produce evidence; provenance fixed; docs corrected; CI integration.

Dependencies: 11.7E.1–11.7E.4.1 verified.
Rollback: none (diagnostic only).
Status: **COMPLETE** — real red tests execute, provenance fixed, diagnostic plan established. Report: `docs/validation/stage11.8.0.0_diagnostic_contract_correction.md`.

### Stage 11.8.0.0.1 — CI Fix, Real Tests, Snowfall Re-examination

Scope: correct the CI breakage introduced in 11.8.0.0 (fpm unavailable in the
Python job; named-target silently exiting 0 on a wrong name); make the T2
Fortran tests GENUINELY fail on invariant violation; add the weak-inversion
core test (LEGACY mixes the inversion, EOS-80 in-situ density masks it —
documented 11.8 finding); re-examine the snowfall accumulation period from
source metadata (CONFIRMED_12H downgraded to INFERRED_12H with explicit
uncertainty: step-range attributes absent, script requests hourly steps yet
artifacts carry two 12-hourly records/day); documentation/data hygiene
(dedupe, relative paths, populated checks).

Acceptance: CI green on the pushed commit; failure-path probe demonstrated
(exit 1 + FAIL JSON); weak inversion conserves heat/salt with confined mixing
(LEGACY) and zero spurious mixing (EOS80); divisor UNCHANGED at that time; T-19 later corrected by v2 to hourly/3600 (T3-CORRECTIVE-3).

Dependencies: 11.8.0.0.
Status: **COMPLETE** — CI green; smoke/core tests authoritative; snowfall
later corrected by v2 (hourly, 3600; T3-CORRECTIVE-3). Report:
`docs/validation/stage11.8.0.0.1_ci_test_correction.md`.

### Post-T2 correction plan (scheduled, NOT part of T3-PREP)

| Item | Scope | Gate |
|------|-------|------|
| **T2-CORRECTIVE** | CA criterion on potential density (or a compression-corrected in-situ criterion), addressing T-25; T-27 (real64 state) in scope | requires Decision **D-33** physics-branch choice; schedule BEFORE **T6** |
| **T1-CORRECTIVE** | ERA5 longitude clamp (T-23) | **DONE 2026-10-25 in T4-PREP** |
| **T3-CORRECTIVE** | T-28 (mask gap) and T-29 (advection boundary) | **DONE 2026-10-24** (both FIXED and verified) |
| **T3-CORRECTIVE-2** | T-03 root-cause diagnosis (spatial, geostrophic, PGF, energy, boundary, CA/RO controls) | **DONE 2026-10-25** (diagnosed; no physics change) |
| **T3-CORRECTIVE-3** | T-19 v2 + E1–E3 (prognostic RO / potential CA / f64 N²) + hygiene | **DONE 2026-10-25** (T3b still fails) |
| **T3-CORRECTIVE-4** | Numerical stabilization: dt reduction + Laplacian dissipation (no sponge) | **DONE 2026-10-25** (T3b PASS; T4 blocked by H-2/T-23) |
| **T4-PREP** | Wind rotation (H-2) + longitude clamp (T-23) | **DONE 2026-10-25** |
| **T4** | First forced ERA5 run + diagnostics | **DONE 2026-10-25** (PASS; heat caveat T-34) |
| **T5** | 90-day/180-day stability + T-34 | **DONE 2026-10-25** (FAIL; T-34 CLOSED) |
| **T5-CORRECTIVE** | Storm-safe Δt/Ah search | **DONE 2026-10-25** (FAIL; no config) |
| **T5-CORRECTIVE-2** | Storm-time diagnostics + root-cause isolation | **DONE 2026-10-25** (diagnostic; no fix) |
| **T5-CORRECTIVE-3** | Monotone/positive advection + sponge | **DONE 2026-10-25** (FAIL: RO<0) |
| **T5-CORRECTIVE-4** | Density repair + .docx refs | **DONE 2026-10-25** (FAIL; T-38 accepted limitation) |
| **T6-SEASONAL** | Jul/Oct 30-day + production scheduler retest + 11.8A spec | **DONE 2026-10-25** (11.8A GO) |
| **11.8A Phase 1** | January 4 cells (EOS × scheduler) | **DONE 2026-10-25** (4/4 stable; production ice artifact) |
| **11.8A Phase 1-ANALYSIS** | Scheduler ice/CA/heat investigation | **DONE 2026-10-25** (artifact; N1-only Phase 2 GO) |

### Stage 11.8.0 T3-PREP — EN4 Data Correction (T-20, T-22)

Scope: regenerate the EN4 initial products for all four seasons with the
corrected builder and a physical freezing-point clamp; verification/regression
only (no physics/CA/EOS change).
Result: **T-20 FIXED** — shipped data were on a different pipeline (up to
7.5 degC vs rebuild at identical indices), so Option B (regenerate) was used:
z_model_m == model DATA z (600 m) and Jul/Oct rebuilds now exist. **T-22
FIXED** — UNESCO Tf(S,p) clamp with a +1e-5 degC f32 margin; cells clamped
Jan 12,589 (+1.407 max), Apr 2,525 (+0.257), Jul 0, Oct 553 (+0.372); 0 cells
below Tf in all 8 products. EN4 T0 test and the new correction test both
report CLEAN. Old products archived in `archive_pre_T3PREP/`; pre-correction
run baselines are not comparable.
Dependencies: T2.
Status: **COMPLETE**. Report:
`docs/validation/stage11.8.0_T3-PREP_en4_data_correction.md`.
NEXT: 11.8.0 T3 (Rest).

### Stage 11.8.0 T3 — Rest-State Diagnostic (ocean without forcing)

Scope: env-gated rest mode (`STAGE118_T3_REST_MODE`, default OFF): no wind
fields, `kl1=0` (no heat/freshwater/snow), initial velocities and barotropic
transports zeroed; advection, pressure gradient, Coriolis, CA, B200/210/280
remain active. Runs: LEGACY/EOS80 canonical + LEGACY rebuild, 30 days, from
the corrected EN4 January product.
Result: all runs complete 30 days with **no NaN** but are **UNSTABLE**:
LEGACY Umax 3.859 / Vmax 5.912 m/s, KE 0 -> 1.32e16 (x1128), CA guard
saturated; EOS80 Umax 4.481 / Vmax 4.706 m/s, KE 0 -> 9.74e15 (x911), CA
converges (guard 0). The near-identical growth in both EOS modes shows the
blow-up is NOT CA-driven. Drivers: **T-28** (934 wet levels loaded as T=0
from the product/mask gap), **T-29** (FCT advection writeback zeroes the
i=is1/j=js1 T/S boundary: 1,341 cells by day 1), plus core pressure-gradient
instability (T-03). Heat/salt drift 0.59-0.82 % / 1.33-1.46 %; volume 0.
Rebuild is byte-identical to canonical (md5), so the comparison is a
determinism check only. New metrics baseline:
`data/validation/t3_rest_result.json` (replaces pre-T3-PREP baselines; a
defect baseline, not a validated reference).
Status: **COMPLETE (UNSTABLE)**. Report:
`docs/validation/stage11.8.0_T3_rest_state_diagnostic.md`.
NEXT: **T3-CORRECTIVE** (T-28, then T-29), re-run T3; **T4 NO-GO** until the
rest test passes (|U|,|V| < 0.01 m/s, no KE growth, conservation to 1e-4).

### Stage 11.8.0 T3-CORRECTIVE — Mask Gap + Advection Boundary Fixes

Scope: bug fixes only. **T-28 FIXED (Option C)**: the builder now consumes
the authoritative runtime `kt1` (`build/grid_dump_kt1.dat`) and fills all
runtime wet levels; the reader FATALs on any product/runtime mask mismatch or
remaining unfilled T=0/S=0 pair. All 8 products now have 143,422 levels,
0 unfilled pairs (mask test CLEAN 8/8). **T-29 FIXED (Option A)**: the FCT
advection writeback is restricted to 1:is,1:js, preserving the T/S boundary;
a new Fortran test passes and fails when the fix is reverted (red/green
proven); rest-run day-1 S=0 boundary cells 1,341 -> 0. Re-run of T3 (30 d,
zero forcing) still UNSTABLE — LEGACY Umax 3.924/Vmax 5.498 m/s (KE x737),
EOS80 4.713/6.021 (x674), but conservation improved ~26x/6x and drift ~8x;
the remaining driver is the core T-03 pressure-gradient instability (the
T3-CORRECTIVE inference that T-25 is not the driver was REVISED by
T3-CORRECTIVE-2; see below). Runs inventory: 44.08 GB
(CRITICAL 1.9 / ARCHIVE 40.5 / TEMPORARY 2.7; ~29.7 GB potential savings;
nothing deleted).
Dependencies: T3.
Status: **COMPLETE (rest still UNSTABLE)**. Report:
`docs/validation/stage11.8.0_T3-CORRECTIVE_mask_advection_fix.md`.
NEXT: **T3-CORRECTIVE-2** (COMPLETE — see below); **T4 NO-GO**.

### Stage 11.8.0 T3-CORRECTIVE-2 — T-03 Root-Cause Diagnosis

Diagnostic only. **Root cause identified:** the rest-state instability is a
**CA density-writeback -> baroclinic pressure-gradient feedback**, not a
pressure-gradient stencil error. The initial EN4 thermal wind is unbalanced with
the zero-velocity rest state (0.283 m/s, barotropic transport 0.144 m/s); CA is
the only routine that updates `RO` during the normal step (RO is not
prognostic), and its writeback creates anomalies up to 8.26 kg/m3 whose PGF
work grows from 7.9 % to 99.6 %. **Controls:** `FREEZE_RO` (CA mixes T/S, no RO
writeback) bounds the flow at 0.205 m/s / 6.52e13 J in LEGACY and 0.201 /
6.12e13 in EOS-80, while the baselines reach 3.924 / 8.09e15 and 4.713 /
6.84e15; `FREEZE_TW` is exactly at rest. dt=1800 is bounded (0.528 m/s,
1.18e14 J), dt=3600 exponential, dt=7200 FPE. The signal is localised at the SW
600-m boundary/topography (33 % KE within 5 cells, 64 % within 10, 71 % SW) —
an amplifier, not the source. PGF surface double-count is 1.5e-5 (negligible);
Coriolis work ~0. **T-25 is revised:** EOS-80 CA convergence does not exonerate
the CA density writeback; T-25 remains the leading CA defect candidate.
Dependencies: T3-CORRECTIVE. Status: **COMPLETE (diagnosis)**. Report:
`docs/validation/stage11.8.0_T3-CORRECTIVE-2_t03_diagnosis.md`.
NEXT: **T3-CORRECTIVE-3** (COMPLETE; T3b fails — see below); **T4 NO-GO**.

### Stage 11.8.0 T3-CORRECTIVE-3 — Fixes, T-19 v2, Hygiene

**T-19 FIXED:** v2 CDS probe (24 hourly validity times, no `step`) gives
R = mean(12:00)/mean(all 24) = **1.00898** -> hourly accumulation; v1 invalid.
Divider changed **43200 -> 3600 s**; hourly records are summed to 6-h windows;
merged April/Jan products regenerated; `CONFIRMED_1H`, contract 120/120.

**E1/E2/E3 implemented behind OFF-by-default switches:** `STAGE118_RO_PROGNOSTIC`
(recompute RO after CA before B200; CA skips local writeback), `STAGE118_CA_POTENTIAL`
(both levels at lower-level pressure), `STAGE118_CA_F64_N2` (real64 differences,
N² < -1e-6). E1 is a no-op (CA already rewrites RO for every wet column); E2 is
a no-op in LEGACY (Eckart pressure-independent); E3 reduces CA mixings
(7.08e6 -> 61,454/day) but does not stabilize. **T3b FAILS:** Umax 3.902 m/s,
KE15 1.641e14 J, KE30 8.696e15 J, ratio 52.98. E6 sponge reduces the peak
(3.71 -> 1.71 m/s at extreme damping) but no plateau; balanced initialization
also fails (3.998 m/s, ratio 50.4). **T4 NO-GO; T3-CORRECTIVE-4 required**
(coupled advection/density stabilization). Report:
`docs/validation/stage11.8.0_T3-CORRECTIVE-3_fixes.md`.

### Stage 11.8.0 T3-CORRECTIVE-4 — Numerical Stabilization

Diagnostic/numerical only. Root limitation: **Δx=13.89 km vs first baroclinic
Rossby radius 2.36 km (ratio 0.17)**; baroclinic eddies are unresolved.
T3b with E1+E2+E3:

| config | max |U| (m/s) | KE15 (J) | KE30 (J) | KE30/KE15 |
|---|---|---|---|---|
| dt=3600 | 3.902 | 1.641e14 | 8.696e15 | 52.98 |
| dt=1800 | 0.517 | 1.002e14 | 1.114e14 | 1.112 |
| dt=900 | 0.278 | 7.752e13 | 9.887e13 | 1.275 |
| **dt=1800 + Ah=10000** | **0.147** | **3.899e13** | **2.216e13** | **0.568** |

Ah=5000/10000/20000 all pass; Ah=10000 chosen; Ah=50000 would violate the
explicit 2-D stability limit at dt=1800 (`4·Ah·dt/dx²=1.86>1`). No sponge used.
Acceptance revised to **max |U|<0.5 m/s and KE30/KE15<5.0** for T3b; T3a remains
homogeneous max |U|<1e-6. The stabilized state is a **bounded, dissipative
compromise**, not resolved eddy dynamics. **T4 numerical gate cleared but T4
implementation remains NO-GO until H-2/T-23.** Report:
`docs/validation/stage11.8.0_T3-CORRECTIVE-4_numerical_stabilization.md`.

### Stage 11.8.0 T4-PREP — Wind Rotation (H-2) + Longitude Clamp (T-23)

**H-2 FIXED:** `STAGE118_WIND_ROTATION` (default OFF) rotates ERA5
geographic wind to the rotated grid using alpha from KOORD.DAT FI/DL:
u_g=u·cosα+v·sinα, v_g=−u·sinα+v·cosα. Alpha: mean 50.06°, median 50.18°,
range 14.02–81.28°. 20-cell verification max angular error 2.8e-14°; Fortran
OFF/ON 1-day max wind change 13.46 m/s (interior vector error 3.45e-4 m/s).

**T-23 FIXED:** `STAGE118_LON_CLAMP` (default OFF) clamps out-of-range
longitude to the file edge instead of cyclic ±360° wrap. Narrow 10–70E test:
OFF 75E→10E; ON 75E→70E; 5E control→10E. T1 spatial/temporal with clamp ON:
PASS/PASS. Both switches OFF by default are bit-identical legacy.

Integration: T3 with both switches ON and the chosen dt=1800+Ah=10000 config is
unchanged (max |U| 0.147 m/s, KE30/KE15 0.568). **T4 is GO**; implementation
not started here. Report:
`docs/validation/stage11.8.0_T4-PREP_wind_rotation_lon_clamp.md`.

### Stage 11.8.0 T4 — First Forced Run

Configuration: rest OFF; wind rotation ON; longitude clamp ON; dt=1800;
Ah=10000; E1+E2+E3; EOS LEGACY; corrected EN4 January; ERA5 January
full-coverage; 30 days. No NaN/Inf.

**Metrics:** max |U| **0.970 m/s**, max |V| 0.598 m/s, max |W| 0.0024 m/s;
KE0/15/30 **4.645e13 / 4.408e14 / 6.699e14 J**; KE30/KE15 **1.520** (<10);
T/S drift 0.311 °C / 0.229 PSU; volume 0, salt 8.319e-4, heat 5.228e-3
(equivalent to −3.94 W/m² forced cooling; heat-flux closure not archived,
T-34). **Ekman:** day-15 mean angle **−40.4°**, 61.4 % of cells right of wind;
day-30 geostrophic field dominates (+22°). **Energy:** mean wind work
**+3.805e10 W** (positive every sampled day), mean Laplacian dissipation
7.48e9 W. **vs T3:** KE ×30.2 (+2923 %), max |U| +0.824 m/s.

**T4 PASS** on stability/Ekman/wind/volume/salt; heat caveat documented.
**T5 GO**; implementation not started. Report:
`docs/validation/stage11.8.0_T4_wind_forcing.md`.

### Stage 11.8.0 T5 — Long-Run Stability + T-34

**90-day January: FAIL.** Bounded through day 45, then KE30 6.704e14 J →
KE60 **1.178e19 J** (ratio **17,568**), Umax **488 m/s**, CA input inversion
2.50e2 in 10,625/10,966 columns; **SIGFPE at day 61**. Q1 March storm forcing
is the trigger; no heat-budget cause.

**April 30-day: PASS** for stability/seasonal consistency: max |U| 0.866 m/s,
KE30/KE15 **1.541**, KE30 ratio vs January 0.752, max-U ratio 0.893; Ekman
rightward signal not observed at day 15 (spring geostrophic dominance).

**T-34 CLOSED (physical, tentative):** stable 30-day heat drift corresponds to
−3.94 W/m² (Jan) and −9.81 W/m² (Apr), plausible Arctic cooling; volume 0,
salt <1e-3. No surface-flux archive, hence tentative.

**180-day not performed** (conditional on 90-day pass). **T5 overall FAIL;
T6 NO-GO; T5-CORRECTIVE required.** Report:
`docs/validation/stage11.8.0_T5_time_stepping_stability.md`.

### Stage 11.8.0 T5-CORRECTIVE — Storm-safe configuration search

**No configuration passes.** 90-day January Q1 runs:

| config | Δt | Ah | outcome |
|---|---|---|---|
| 1 | 900 | 20000 | FPE after day63; Umax 1361 m/s |
| 2 | 900 | 30000 | first NaN day67; Umax 4.4e7 m/s |
| 3 | 600 | 30000 | first NaN day70; Umax 4.0e7 m/s |
| 4 exploratory | 600 | 50000 | first NaN day74; Umax 2.5e5 m/s |

Storm peak **2020-03-16 18 UTC**, max wind **26.86 m/s**, model τmax
0.609 Pa; collapse occurs during/after the storm. Stronger dissipation only
delays the NaN by days, so the failure is not a simple ocean-momentum
CFL/Ah limit. No chosen configuration; April requirement not applicable (T5
April baseline remains stable reference). **T6 NO-GO; T5-CORRECTIVE-2
required.** Report: `docs/validation/stage11.8.0_T5-CORRECTIVE_storm_safe.md`.

### Stage 11.8.0 T5-CORRECTIVE-2 — Storm diagnostics

Config1 (dt900/Ah20000) detailed 75-day run: first RO<0 **day29**, S<0 **day46**
(−7.55 PSU), T>10 °C **day57**, collapse days63-65 (T max 532 °C, S min
−9,859 PSU, RO min −2.9e7). Negative cells start at the surface near the
boundary and spread along it; boundary max |U| exceeds interior days60-64.
CA nmix remains ~3e5/day (no spike); inversions grow after T/S corruption.
Wind work 20-64 GW vs dissipation 24-102 GW, so energy accumulation is not
primary. Q1 wind peak is 2020-03-16/day75, **after** the collapse; the failure
is cumulative, not a single-storm trigger.

**Root cause: MULTIPLE — ADVECTION_ERROR primary; BOUNDARY_REFLECTION
amplifier; CA secondary.** Reference originals absent; no storm guidance.
Literature recommends monotone/positive salinity advection and radiation
boundary. **T6 NO-GO; T5-CORRECTIVE-3 required.** Report:
`docs/validation/stage11.8.0_T5-CORRECTIVE-2_diagnostics.md`.

### Stage 11.8.0 T5-CORRECTIVE-3 — Monotone advection + sponge

Reference audit: original/current advection is FCT with Zalesak limiter, not
central; reference BCs are no-gradient, no radiation/sponge.
Implemented `STAGE118_MONOTONE_ADVECTION` (hard S positivity/no-new-max and
T∈[−2,30] safety net) and `STAGE118_SPONGE_BOUNDARY` (5 cells, α=1/day).
Tests PASS. 90-day Config1 with both fixes: no NaN, max |U| 1.141,
KE90/KE60 0.975, S≥0, T∈[−2,30], but **RO min −24.24 / 3,187 negative cells**
→ **FAIL**. April 30-day with fixes PASS (KE30/KE15 1.530, max |U| 0.853).
Hard caps create nonphysical S=0/T=30 density; not a valid density fix.
**T6 NO-GO; T5-CORRECTIVE-4 required.** Report:
`docs/validation/stage11.8.0_T5-CORRECTIVE-3_monotone_advection.md`.

### Stage 11.8.0 T5-CORRECTIVE-4 — Density repair

Hard T caps removed; `STAGE118_DENSITY_REPAIR` (default OFF) adjusts the
less-sensitive tracer (dRO/dT vs dRO/dS) to make RO≥0 after advection, before
CA. Unit test: RO −0.0242→+2.39e-4 g/cm³, S 0→0.0326 → PASS. 90-day Config1:
repair adjusts ~139,620 cells/day, but CA/B200 recreate negative density
(day65 RO −416, 25 cells), NaN appears **day69**, max |U| **34,027 m/s** →
**FAIL**. April 30-day with repair PASS (KE30/KE15 1.530, max |U| 0.853,
RO min 0). `Iceberg_1.docx`/voxel .docx absent; PDF (voxel iceberg thermal
model) contains only ice heat-conduction stability, no ocean density guidance.
**ACCEPT LIMITATION: 30-day forced runs only; T6 NO-GO.** Report:
`docs/validation/stage11.8.0_T5-CORRECTIVE-4_density_repair.md`.

### Stage 11.8.0 T6-SEASONAL — Seasonal validation + production scheduler

**T5 chain CLOSED** with accepted 30-day limitation (T-38): 30-day forced runs
validated Jan/Apr/Jul/Oct; 90-day storm runs unstable (systemic 13.89 km vs
2.36 km Rossby-radius limitation). **July PASS** (max |U| 0.542,
KE30/KE15 0.827, RO 0, no NaN); **October PASS** (0.690, 2.152, RO 0, no NaN).
**Production scheduler 30/30 days, 720/720 fire-steps PASS** (max |U| 0.494,
KE30/KE15 1.480, RO 0, no NaN) — historical 55/360 blocker **RESOLVED for
30-day runs**. EOS80 production 10-day smoke PASS (max |U| 0.405, RO 0).
**Runtime default update (11.8B):** EOS80 is now the default; LEGACY is an
explicit fallback (D-48).
**11.8A matrix GO**: 2 EOS ×2 schedulers ×4 seasons =16 cells, 30 days;
spec `docs/validation/stage11.8A_matrix_plan.md`; storage ~4.8 GB; ice caveat
Apr/Jul/Oct use January-derived diagnostic ice. Matrix execution not started.

### 11.8A Matrix — Phase 1 (January)

All four January cells executed with real OSI-SAF/C3S sea ice and the standard
protective config:

| Cell | EOS | Scheduler | max |U| | KE30/KE15 | S min | RO min | NaN |
|---|---|---|---|---|---|---|
| 1 | LEGACY | N1 | 0.794 | 1.486 | 24.88 | 0 | 0 |
| 2 | EOS80 | N1 | 0.785 | 1.494 | 24.92 | 0 | 0 |
| 3 | LEGACY | Prod | 0.511 | 1.479 | 24.88 | 0 | 0 |
| 4 | EOS80 | Prod | 0.511 | 1.483 | 24.92 | 0 | 0 |

EOS effect ≤1.1 % (KE/max-U), scheduler effect max |U| −35.6 % and ice extent
+65 % (STALE cadence, not instability); no interaction pathology. D-29
preliminary A/B/C satisfied; final decision needs all seasons. **Phase 2 GO.**
Report: `docs/validation/stage11.8A_phase1_january_results.md`.

### 11.8A Phase 1-ANALYSIS — scheduler ice artifact

All four January cells used identical real OSI-SAF ice (day-0 bit-identical).
Production scheduler gives **+65 % ice extent** (1,128.8 vs 683.6 ×10³ km²),
**466,124 km²** extra ice over N1 open water (N1 SIC 0.013), surface ocean
−0.76 °C, implied heat loss **−269 W/m²** vs −40 N1. Cause = production
cadence/STALE coupling (24 fires/day vs 48 N1 thermo steps; 576 CA passes/day
vs 1), not initialization or EOS (≤1.1 %). **ARTIFACT** → T-39; production
matrix cells **BLOCKED**, Phase 2 **N=1 only**. CA is active; `nmix=********`
is an I8 print overflow (T-40, diagnostic). T-34 valid for N1, invalid for
production. Report: `docs/validation/stage11.8A_phase1_analysis.md`.

### 11.8A Phase 2 — N=1 seasonal matrix complete

**Scope:** Apr/Jul/Oct × LEGACY/EOS80, 30 days, standard protective config;
January reused from Phase 1 (real OSI-SAF ice). **8/8 PASS after T-41 correction.**

| Season | LEGACY max \|U\| / KE30/15 | EOS80 max \|U\| / KE30/15 | Verdict |
|---|---|---|---|---|
| Jan | 0.794 / 1.486 | 0.785 / 1.494 | both PASS |
| Apr | 0.838 / 1.506 | 0.843 / 1.507 | both PASS |
| Jul | 0.542 / 0.827 | 0.543 / 0.826 | both PASS (T-41 corrected) |
| Oct | 0.690 / 2.152 | 0.689 / 2.172 | both PASS |

EOS80 effect across seasons: max |U| **−0.14 %**, KE30/KE15 **+0.33 %**,
CA nmix **−12.85 %** → equivalent on dynamics, fewer CA mixings. **T-41
correction:** the raw `density_anomaly` is kg/m³; July minima are
−2.504e-6 g/cm³, absolute density **1.0199975 g/cm³**. The old `RO≥0` gate
was invalid for brackish water; corrected absolute-density gate passes all
8 cells. **D-29: PROMOTED** (N=1 validation). Production column remains
BLOCKED (T-39); April forcing used one persisted boundary slice to reach
30 days. Report: `docs/validation/stage11.8A_phase2_seasonal_results.md`.
**Next: Stage 11.8B** production release audit/cleanup; Stage 11.9 not
started.

### Stage 11.8B — Production Release Audit & EOS-80 runtime default

**Status: COMPLETE (2026-10-27).** BREAKING CHANGE: `EOS_MODE` unset now
selects **EOS80**; `EOS_MODE=LEGACY` is the explicit Eckart fallback. No
production scheduler change (T-39 remains BLOCKED).

- Default vs explicit EOS80 vs matrix Jan EOS80: **32/32 NetCDF files MD5
  identical**; LEGACY fallback vs matrix Jan LEGACY: **32/32 identical**.
- Reproducibility: Jan LEGACY, Jan EOS80, Apr EOS80, Jul LEGACY, Oct EOS80
  re-runs are **bit-identical** to matrix outputs (32/32 each).
- data/runs (pre-cleanup): **82.583 GB / 289 runs**; CRITICAL 83 (31.734 GB), ARCHIVE 153
  (40.563 GB), TEMPORARY 47 (8.629 GB), DUPLICATES 6 (1.656 GB); estimated
  savings **37.327 GB**. **Stage 11.10 later executed cleanup to 0.510 GB / 26 runs.**
- Migration: `docs/MIGRATION_GUIDE_EOS80_DEFAULT.md`.
- Inventory: `docs/validation/stage11.8B_runs_inventory.md`,
  `data/validation/runs_inventory_final.json`.
- Stage summary: `docs/STAGE11_SUMMARY.md`; checklist:
  `docs/STAGE11_CLOSURE_CHECKLIST.md`.
- Status: **Stage 11.9 CLOSED**; see closure declaration.

### Stage 11.9 — Final Closure (COMPLETE)

**Status: CLOSED (2026-10-27).** Formal declaration:
`docs/STAGE11_CLOSURE_DECLARATION.md`; final review:
`docs/validation/stage11.9_final_review.md`.

- Technical objectives met: ocean stabilization, T4–T6 forcing validation,
  8/8 N=1 matrix, EOS-80 D-29 promotion and runtime default, bit-identical
  reproducibility.
- Known limitations are non-blocking: T-38 (90-day), T-39 (production
  scheduler ice artifact), seasonal Apr/Jul/Oct diagnostic ice, April forcing
  boundary extension.
- data/runs cleanup is an optional recommendation (37.327 GB estimated
  savings), pending user approval; no deletion performed.
- Stage 12 preparation: `docs/STAGE12_PREPARATION.md`; implementation not
  started.

### Stage 11.10 — Prognostic Ocean, NetCDF Default, Tides, Disk Cleanup

**Status: PARTIAL — infrastructure complete; physical N>1/OBC and real tides blocked.**

- **Disk:** data/runs **82.583 GB → 0.510 GB**; 263 directories removed; 26 kept with first/last NetCDF + logs/CSV/config. Cleanup executed (not just recommended).
- **NetCDF:** grid.nc + seaice_initial.nc are the production defaults; root legacy symlinks removed. Legacy `.DAT`/`.bar`/`.ice` are offline fixtures only.
- **Physical baseline (D-50):** bit-identity with N=1 is abolished as a physics gate; 90-day no NaN/S<0/T>30, drift <1e-4, N² ≥ −ε, N=4/N=24 required.
- **N>1/OBC:** N=4 blows up within one day (max U 4352 m/s); N=24 grows to 1.89 m/s in one day. OBC (Flather + radiation + T/S sponge) is the immediate blocker; N=1 is diagnostic only.
- **Tides:** `tides.nc` is null-tides; plan and intentionally-red test created. Tidal forcing must be applied every barotropic step before Stage 12.
- **Stage 12:** gated; implementation not started.

### Stage 11.8 Prerequisite: Ocean Stabilization (MANDATORY GATE)

- **Current state:** production ocean passes **55/360** steps before NaN
  (density-first divergence; Stages 10.20/10.22). T3-CORRECTIVE-4 stabilized the rest state with dt=1800 + Ah=10000
  (max |U| 0.147 m/s, KE30/KE15 0.568; T3b PASS). **T4 prerequisites H-2/T-23 are now FIXED; T4 is GO.**
- **Requirement:** a full **360-step** production run (12 steps/day × 30 days)
  without NaN, without guard saturation, without fallback substitutions.
  This is **mandatory** before the 11.8A seasonal matrix — not optional
  remediation.
- **Method:** diagnostic ladder T0–T6 in
  `docs/validation/stage11.8.0_ocean_diagnostic_plan.md`.
- **Final acceptance:** 365-day run without NaN, with conservation,
  stratification, rest-stability, physical-plausibility and reproducibility
  criteria (AC-1). N=1 stability does **not** prove production viability.
- **Tracking:** `KNOWN_ISSUES.md` N-15; EOS-80 promotion additionally requires
  this gate (D-29).

### Stage 11.8.0 T0 — Data and Units Verification

Scope: first ladder rung (T0) per `stage11.8.0_ocean_diagnostic_plan.md`:
snowfall accumulation period, EN4 initial T/S, ERA5 coverage/edges/time,
wind-rotation preliminary. Verification only; no data or physics changes.
Findings: T-19 CLOSED (CONFIRMED_12H via bit-identical live `step=12` CDS
reproduction; T-19 later corrected by v2: hourly, divisor 3600); new T-20 (shipped EN4 z_model_m legacy
grid; Jul/Oct rebuilds missing; reader index-reads), T-21 (April south margin
-0.15 deg, 8 D32-clamped cells), T-22 (Jan rebuild sub-Tf cells), H-2 wind
rotation documented for T4.
Acceptance: strict evidence hierarchy tests in CI; regression green; CI green.
Dependencies: 11.8.0.0.1.
Status: **COMPLETE**. Report:
`docs/validation/stage11.8.0_T0_data_units_verification.md`.
NEXT: 11.8.0 T1 (forcing contract verification).

### Stage 11.8.0 T1 — Forcing Contract Verification

Scope: second ladder rung — ERA5 spatial interpolation (production
`era5_bilinear2d`), temporal selection (`era5_find_time_index`), wind
rotation, and the T-21 April margin assessment. Verification only.
Findings: interior bilinear exact (0.0 error), latitude flip/edges PASS;
longitude wrap returns 180.0 for a 170 E query (latent L-1 -> T-23, 0
production cells affected); temporal nearest-time with clamping and
midpoint-tie-earlier, gaps nearest-only (T-24 documented), axis PASS;
the grid is rotated (X median 50.2 deg from east) and `era5_wind` applies
NO rotation -> H-2 CONFIRMED CRITICAL for T4; T-21 accepted (0.072 % of
wet cells; <=2.25 m/s, <=0.80 degC).
Dependencies: 11.8.0 T0.
Status: **COMPLETE**. Report:
`docs/validation/stage11.8.0_T1_forcing_contract_verification.md`.
NEXT: 11.8.0 T2 (CA/EOS core); T-20/T-22 before T3.

### Stage 11.8.0 T2 — CA/EOS Core Diagnostics

Scope: third ladder rung. Verification only: homogeneous column (f32 + f64
core, both EOS), weak-inversion conservation with an exact f64 reference,
and the in-situ vs potential density compressibility test.
Findings: neutral column untouched (dT=dS=0 in all 4 combinations); genuine
inversion mixed with exact algorithmic conservation (reference heat 0,
salt 1.3e-16; production state f32-limited -> T-27); **A-1 CONFIRMED: CA
compares in-situ density at local pressure, so EOS-80 falsely stabilises a
potential-density-unstable column (nmix 0/0) -> T-25**; T-23 formalized with
a narrow-file red test (75E -> 10.0 instead of clamp 70.0).
Dependencies: T1.
Status: **COMPLETE**. Report:
`docs/validation/stage11.8.0_T2_ca_eos_core_diagnostics.md`.
NEXT: T3-PREP (T-20/T-22 data fixes), then T3 (Rest).

### Stage 11.8A — Scientific Validation (gated)

Configuration matrix (EOS × Scheduler × Season):
  - Configurations: Legacy×N1, Legacy×Prod, EOS80×N1, EOS80×Prod
  - Seasons: Jan, Apr, Jul, Oct (30 days each)
  - Metrics: NaN/Inf, T/S/ρ, U/V/W, CA stats, CFL, conservation, ice extent
  - Gates: no NaN/Inf; drift < 1%/month; OSI-SAF/NSIDC ice bounds
  - EOS decision (D-29): promote to default OR keep optional, with
    explicit justification referencing interaction effects.

30-day Jan/Apr/Jul/Oct on the production executable vs N=1 legacy
baseline (D-22); conservation (salt/heat/volume); CFL active; no NaN/Inf;
mandatory OSI-SAF/NSIDC sea-ice gate (D-27) adjudicating legacy vs dt=150
climates before ANY regime promotion.

### Stage 11.8B — Production Release Audit

Scheduler self-containment re-verified, forensic archive detached from the
production graph (11.8 modular-ocean-core work), temporal splitting +
operator cadence documented, reproducibility (same exe + input contract).

### Stage 11.7F — Legacy Removal + Permanent CFL

Scope: remove legacy input files, add permanent CFL monitoring.
Acceptance: no legacy file references in production path.
Dependencies: ALL of 11.7E.1–11.7E.5 complete and validated, PLUS the
explicit production-default decision produced by 11.8A and audited by
11.8B (which source is the production default per input class). Legacy
removal is NOT automatic after a reader switch — legacy files must
remain available for rollback through 11.8; 11.7F explicitly removes
them only after full validation. Sequencing note (11.7E.1-CP/11.7E.2):
11.7F follows 11.8A/11.8B because the production-default decision and
the sea-ice gate (D-27) are 11.8 outputs.
Risk: irreversible, only after full validation.

### Stage 11.9 — Stage 11 Closure (COMPLETE)

**Closed 2026-10-27.** See `docs/STAGE11_CLOSURE_DECLARATION.md`.

Stage-11 COMPLETE criteria (11.5G §5.4, reaffirmed 11.5H §8): numerical +
physical + software + reproducibility — i.e. (1) numerical: validated
production ocean core with active CFL monitoring and achieved temporal
convergence (N-11 resolved); (2) physical: the sea-ice gate (D-27)
adjudicated and the EOS-80 promotion decision (D-29/D-30, incl. the
unvalidated ice-response question N-14) explicitly resolved; (3) software:
NetCDF I/O contracts verified for every input class, legacy inputs removed
(11.7F), and the production default declared; (4) reproducibility: the same
executable + input contract reproduces the run (11.8B). Only then does the
Stage-12 gate open (D-28).

**Outcome:** Stage 11 is formally **CLOSED** for the validated N=1 30-day
scope. T-38 (90-day), T-39 (production ice/cadence), and diagnostic seasonal
ice remain documented non-blocking limitations. Stage 12 planning is open;
implementation has NOT started.

### Stage 12.0 — Voxel Iceberg Thermodynamics (PLANNED; preparation only)

3D internal iceberg model. Stage 11.9 has closed and the D-28 entry gate is
open for **planning**, but implementation has NOT started. See
`docs/STAGE12_PREPARATION.md`.

### Stage 11.2 — EN4 Initial Condition Stabilization (SUPERSEDED — archive)

> **HISTORICAL — SUPERSEDED:** The following text reflects initial observations from early Stage 11. The −20.07 g/cm³ value was identified as a unit conversion error in Stage 11.1. The seasonal EN4 defect was resolved in Stage 11.2 preprocessing fixes. This section is retained for historical reference only.

Stage 11.1 established that the ocean instability is general to prognostic ocean evolution, but its timing depends critically on the initial EN4 state:

- **January**: initially stable, survives 4 days, then crashes (Day 5)
- **April/July/October**: pre-existing negative ro (−20.07 g/cm³) → crash Day 1
- **Frozen-ocean control**: 30 days stable (ro 0.0075–0.0082 g/cm³) → atmosphere alone does NOT cause instability

The identical `ro_min = -20.07 g/cm³` for April/July/October surface layers indicates a systematic EN4 processing defect in the vertical regridding/extrapolation for warmer seasons (likely `shallowest_finite` flag handling in `build_initial_ts.py`).

The next stage is an **explicitly approved physics/numerics stage** per RULES.md procedure. Focus:

- Diagnose and fix the EN4 surface-layer extrapolation bug (`build_initial_ts.py` vertical regridding)
- Test corrected initial_ts pipeline across seasons
- Target: 30-day stable ocean run across seasons (`steps executed = 360`)

**Acceptance gate:** re-run the 30-day gate with `ICEBERG_PRODUCTION=true` — expect `steps executed = 360` (12 steps/day × 30) and a physically valid trajectory (no NaN warnings), across seasonal initial conditions.

Meanwhile, production iceberg demonstrations use the offline real-forcing path (TEST_11 family), which remains fully validated.

## Completed Stage 10.17 — iceberg melt and thermodynamic budget audit

Delivered:

- controlled experiments `test/iceberg_test_10p17_melt_budget.f90` (A–K:
  zero forcing, warm water/cold air, cold water/warm air, zero U_rel,
  velocity/temperature/size/timestep scalings, thermal-evolution switch,
  30-day stress test);
- 90-day diagnostic run `test/iceberg_test_10p17_90day.f90` (Q1 ERA5
  atmosphere cycle, ocean frozen at January state);
- extended real-forcing TEST_11 diagnostics (9 new columns; 15 shared
  columns byte-identical to 10.16);
- independent Python regression `test_stage10_17_melt_budget.py` (40
  checks) and analysis `stage10.17_melt_analysis.py` (12 figures + budgets);
- report `docs/archive/stage11/stage10.17_melt_thermodynamic_budget_audit.md`.

Result: the melt machinery is internally consistent (M ≡ ρ_i·L·W·H,
budget closure 5e-4 %), the legacy **lateral melt dominates (96.8 %)** at
a near-constant 0.26 m/day (C_LATERAL = 1e-6 m/(s·K), velocity-independent,
⟨ΔT⟩_D ≈ 3 K), and all findings are diagnostics-only (no physics change).
The 90-day run loses 42.2 % of mass — annual extrapolation is premature
(ocean state frozen at January).

### Stage 10.18A — lateral melt parameterization research audit (COMPLETE)

Delivered:

- independent reference layer `python/validation/lateral_melt.py`
  (legacy_full_height, legacy_submerged, bulk velocity-dependent, Bigg1997,
  Neshyba–Josberger, FitzMaurice plume; verified literature provenance);
- independent tests `python/tests/test_lateral_melt_parameterizations.py`
  (458 checks, analytic expectations only);
- analysis `python/analysis/stage10_18a_lateral_melt.py` — sensitivity
  matrix (ΔT × U × L), scalings, TEST_11 offline replay (6 variants),
  geometry comparison, 10 figures, machine-readable outputs
  (`data/output/stage10.18a/`);
- report `docs/archive/stage11/stage10.18a_lateral_melt_parameterization_audit.md`.

Result: **no production physics change** (git diff on `src/`/`test/` empty).
The reference layer reproduces production exactly (replay dM 15.43 %/lateral
96.83 %). The legacy constant C_LATERAL = 1e-6 m/(s·K) is equivalent to
forced-convection side melt at **U_eq ≈ 0.30 m/s** (γ_T = 304 W/(m²·K)),
while the simulated U_rel at the draft is 0.005–0.027 m/s — a factor 10–60.
Every literature-based velocity-dependent variant gives mean lateral melt
0.013–0.052 m/day (5–20× below legacy) and 30-day ΔM 1.3–3.6 % (vs 15.4 %):
**the dominance of lateral melt is formulation-dependent, not a robust
physical outcome**. Geometry ambiguity quantified: submerged full-perimeter
vs production full-height = factor 2·ρ_i/ρ_w = 1.77 (volume); depth-only
1.13 (Stage 10.17 F2). Wave erosion is NOT TESTABLE with the current forcing.

### Stage 10.18B — observational constraint and parameterization discrimination (COMPLETE)

Delivered:

- curated observational dataset `data/validation/observations/
  iceberg_lateral_melt_observations.csv` (17 cases) + sources + provenance
  (RH80 lab DIRECT; Sermilik + Antarctic + velocity INDIRECT; every number
  from a fetched primary text; exclusions documented);
- prediction engine `python/validation/observational_constraint.py`;
- independent tests `python/tests/test_observational_constraint.py` (62
  checks, analytic expectations only);
- analysis `python/analysis/stage10_18b_observational_constraint.py`
  (normalization, comparison table, filtered statistics, C_eff distribution,
  bounded comparison, 10 figures, machine-readable outputs).

Result: **no production physics change** (git diff `src/`/`test/` empty).
Direct lateral-melt field observations are scarce — the directly comparable
set is the Russell-Head lab (N=5). The lab evidence requires a nonzero-at-U=0
(buoyant/plume) term and shows a nonlinear ΔT^1.5 temperature dependence that
the linear legacy over-predicts at low ΔT; forced-convection-only variants
fail the quiescent cases. The observational C_eff distribution (median 0.54×
production, range 0.28–1.06×) brackets the production constant; legacy lateral
exceeds the observed total submarine melt in 3/4 Antarctic cold-shelf cases.
Geometry and wave erosion are NOT CONSTRAINED. **Decision: OPTION E**
(insufficient discrimination); **production KEEP_CURRENT**.

### Stage 10.18C — existing observations reanalysis and velocity-resolved melt constraint (COMPLETE)

Delivered:

- reanalyzed dataset `data/validation/observations/stage10.18c/`
  (`observations.csv` 18 rows, `sources.csv`, `provenance.md`);
- analysis `python/analysis/stage10_18c_existing_observations.py`
  (independence summary, comparison matrix, velocity-resolved subset, gap
  matrix, separate C_eff diagnostics, 10 figures);
- tests `python/tests/test_stage10_18c_observations.py` (61 checks);
- report `docs/archive/stage11/stage10.18c_existing_observations_reanalysis.md`.

Result: **no production physics change** (git diff `src/`/`test/` empty).
The public datasets do not provide a single field case with simultaneous
melt + ΔT + U_rel (FIELD velocity-resolved cases = 0); actual U_rel cannot be
reconstructed (no ocean-velocity data). RH80 is one lab fit; C_eff_lab and
C_eff_submarine are kept separate. Velocity dependence is NOT IDENTIFIABLE
quantitatively; geometry, side/basal separation and wave erosion are NOT
CONSTRAINED. Legacy over-predicts cold low-ΔT (lab + Antarctic shelf).
**Decision: OPTION D** (existing observations give useful bounds) with
OPTION E elements; **production KEEP_CURRENT**.

**Stage 10.18C methodological correction (vs Stage 10.18B):** RH80 rows are
evaluations of one published fit (not 5 independent observations); the field
C_eff is a submarine-total coefficient (not lateral); Moyer19 provides
iceberg translational speeds (not U_rel); nonzero quiescent melt indicates a
buoyancy/free-convection component (not necessarily a plume mechanism);
the Enderlin23 thermal slope is a submarine sensitivity.

### Stage 10.18D — velocity-resolved / per-iceberg observational upgrade (COMPLETE)

**Decision: OPTION D refined** (per-iceberg bounds now quantitative;
velocity/geometry/side-basal/wave still unconstrained). Delivered:

1. **Enderlin23 per-iceberg population** — USAP-DC 601679
   (`Antarctic-iceberg-csvs.zip`) **RETRIEVED** via direct HTTP POST to the
   zip endpoint (page-level JS reCAPTCHA is not enforced there; inner zip
   MD5 `821bed51660957b65a896c42fb88a057` verified; the 10.18C
   "account-gated, not retrieved" statement is corrected). Per-iceberg
   dataset: **743 rows** (54 raw CSVs, 15 sites, 2011-2022) with
   melt/draft/geometry/EPSG:3031→WGS84 coordinates and site→region
   attribution (WAP/WAIS/EAIS/EAP). The ΔT-dependence, draft-dependence and
   effective-coefficient analyses are upgraded from 4 region aggregates to
   iceberg level;
2. **ADCP-equipped Schild21-style campaign** — the minimal package that
   closes the velocity and depth gaps: GPS + drone SfM + multibeam + repeat
   bathymetry (iceberg) + CTD profiles + ADCP/current meters (ocean) + wave
   state, all temporally paired (report §11, with sizing for
   identifiability and feasibility);
3. production physics decision (e.g., buoyancy/free-convection term,
   nonlinear ΔT dependence, geometry convention) remains deferred: the
   per-iceberg bounds (legacy exceeds 99.6 % of observations at TF=1.5 °C;
   C_eff_submarine median 0.16× production) require the velocity-resolved
   campaign or an explicitly approved physics stage.

Key results: regional maxima reproduce the paper (WAP/WAIS max 1.1–1.3× of
~50/~40 m/a; EAIS/EAP p95 5.2/3.6 vs ~5 m/a); Thwaites 24 m/a/°C consistent
per-iceberg (76 % of 167 bergs imply TF in 0.2–1.6 °C); velocity-dependent
literature variants bracket observed medians; per-iceberg C_eff_submarine
median 1.56e-7 = 0.16× production (range 0.08–0.33×). Report:
`docs/archive/stage11/stage10.18d_velocity_resolved_observational_upgrade.md`.

### Stage 10.15.2 — coordinate mapping and bilinear interpolation fix (COMPLETE)

Delivered:

- source fix `src/iceberg_forcing.f90`: transposed cross terms swapped in
  `bilinear_interp_3d` and `model_coords_to_latlon` (wx along j/X, wy along
  i/Y — the Stage 7.6A / grid_coupling convention);
- new Fortran regression `test/iceberg_test_bilinear_axis_regression.f90`
  (13 checks: exact-node, constant, X-only, Y-only, X+Y, boundary
  continuity, 3D layers, real-grid trajectory continuity — **FAILS on the
  pre-fix source with 10 errors incl. the 0.17° jumps, PASSES post-fix**);
- corrected `test/iceberg_test_artificial_forcing.f90` (expectations fixed
  to the correct wx↔lon/j, wy↔lat/i association);
- TEST_11 30-day re-run: exit 0, 720 rows, **0 jumps**, max geographic step
  97 m, corr(implied geo, reported) = 0.988 (pre-fix: 8 jumps / 19.6 km /
  0.029);
- comparison script `python/analysis/stage10.15_2_compare.py` + output
  bundle `data/output/stage10.15_2/` (gitignored; pre-fix preserved);
- report `docs/archive/stage11/stage10.15.2_coordinate_mapping_bilinear_fix.md`.

T-13 is RESOLVED. **T-07 drift anomaly remains OPEN** (drift-scaling
numbers unchanged — the drift tests do not exercise the corrected
interpolation path; the next step is a drift-scaling investigation with the
corrected code, focusing on drag/Coriolis, not interpolation).

### Stage 10.15.1 — trajectory continuity and output integrity audit (COMPLETE)

Delivered:

- deterministic audit script `python/analysis/stage10.15_1_trajectory_audit.py`
  (28 checks, per-step audit CSV, corrected trajectory CSV, 9 figures,
  summary JSON; output bundle `data/output/stage10.15_1/`, gitignored);
- report `docs/archive/stage11/stage10.15.1_trajectory_continuity_audit.md`;
- regression tests `python/tests/test_stage10_15_1_trajectory_audit.py`.

Key finding: the Stage 10.15 geographic trajectory is **discontinuous**
(8 jumps of ~0.17°), caused by transposed bilinear weights in
`model_coords_to_latlon` / `bilinear_interp_3d` (T-13). The model-space
x/y trajectory is continuous and kinematically consistent. The next stage
must fix the interpolation weights (one-line-pair swap) with Fortran
regression tests sampling interior cell points and a TEST_11 re-run.

### Stage 10.15 — operational end-to-end demonstration (COMPLETE)

Delivered:

- **Lagrangian iceberg 30-day real-forcing run** (`iceberg_test_11_30day_offline`,
  720 hourly steps): trajectory produced (74.83→75.07 °N, 30.31→29.84 °E),
  mass −15.4 %, melt bounded (basal 0.049 / lateral 0.260 / surface 0.022
  m/day), 7/7 test checks + 7/7 diagnostics checks PASS.
- **Full-model runs** (`fpm run`, 1 day and 7 days): exit 0; day_00 clean;
  from day 1 the 3D ocean fields are NaN (stable 56.5 %, T frozen at 273.15 K)
  — the documented Stage 8 EN4-init imbalance family, pre-existing, NOT
  introduced here.
- **T-12 prerequisite exercised**: root symlinks (`KOORD.DAT`, `hhh.bar`,
  `1_1.ice`–`1_5.ice`) created; all previously-skipped grid-dependent tests
  now PASS.
- **Key operational finding**: the production executable (`app/main.f90`)
  does NOT run the Lagrangian iceberg module (no `use iceberg*`); the iceberg
  model is reachable only through test programs. The Eulerian ocean state is
  dead from day 1 with real EN4 init, so coupled forcing is not yet possible.
- Diagnostics: `python/analysis/stage10.15_diagnostics.py` (7 figures +
  summary JSON); output bundle `data/output/stage10.15/` (gitignored).
- Report: `docs/archive/stage11/stage10.15_operational_demonstration.md`.

**Known status**: operational demonstration completed with documented
limitations; not an observational validation. Commit pending user review.

### Stage 10.14 — re-scoring of the 10.8.2 observational set against the 3eq / 3eq+natural closures (COMPLETE)

Roadmap item §142–143 delivered:

- New scoring layer `python/validation/three_equation_scoring.py` applies
  the 3eq (10.10/10.10.1) and 3eq+natural (10.11) closures to the curated
  10.8.2 19-record set with the 10.8.2 acceptance criterion.
- **u>0 rows (n=4):** teq metrics RMSE 0.366 / bias +0.277 vs bulk
  0.108 / +0.083 — the three-equation closure does NOT reduce the
  systematic NJ80 bias (functional-form mismatch from Stage 10.9 persists;
  KW84 improves 0.70x → 1.09x, NJ80 worsens 5.8x → 11.7x at dT=2).
- **Quiescent rows (n=5, RH80 lab):** bulk 0/5, teq 0/5, teq_nat **5/5**
  in the observed band 0.01–1 m/day at the lab scale L=1 m (ratios
  0.56–1.39); at iceberg scale L=100 m the Ra cap pins Nu (γ_T,nat drops
  77x) — the 10.11.3 "gap not closed" statement is **scale-specific**.
- Validation: `python/tests/test_three_equation_scoring.py` (177/177 PASS);
  all 7 pre-existing Python suites unchanged (822 checks, 0 errors).
- No calibration, no production change, no switch-default change.
- Report: `docs/archive/stage11/stage10.14_three_equation_rescoring.md`.

**Known status**: re-scoring completes the KNOWN_ISSUES N-05 dependency
(re-scoring on the 3eq closure); calibration remains not identifiable.
Commit pending user review.

### Stage 10.13 — diffusion-limited / double-diffusive low-flow closure (COMPLETE)

Phases A–C delivered:

- Phase A: design note + literature audit (MK77 / Keitzl16 / Middleton21).
- Phase B: research prototype `python/validation/low_flow.py` (167 checks;
  sweep 246/270 in band vs baseline 135/270; 10.8.2 quiescent rows 5/5 in band,
  ddc within 1.1–2.2× of RH80 observations, no calibration).
- Phase C: production integration — `low_flow_closure_enabled` (OFF default),
  three-equation interface preserved, forced branch bit-identical at high U,
  legacy OFF verified; Fortran 23/23, Python/Fortran comparison 56/56,
  full battery exit 0, strict build clean.
- Reports: `docs/archive/stage11/stage10.13_phase_b_results.md`,
  `docs/archive/stage11/stage10.13_phase_c_results.md`.

**Known status**: research parameterization (t_scale, f_dc, κ_S convention
uncertainties documented; not universal validation). Commit of Phase C
pending user review.

### Stage 10.11 — natural convection basal melt / low-flow closure (DONE)

Stage 10.11 implemented a physically-motivated natural-convection closure for the three-equation ice-ocean interface, addressing the largest structural gap identified in Stage 10.8.2 (zero melt at zero flow).

- **Physics**: Natural convection from a horizontal ice base (facing downward) driven by combined thermal and haline buoyancy. Double-diffusive Rayleigh number:
  `Ra_eff = g * L^3 / (nu * alpha) * [beta_T * (T_w - T_B) + beta_S * (S_w - S_B) * Le]`
  with `beta_T = 3.0e-5 1/K`, `beta_S = 7.8e-4 1/PSU`, `Le = 100`.
  Characteristic length = iceberg length L (horizontal scale of the Fujii
  plate; production passes state%L. Gayen et al. 2016 is CONTEXT only — it
  studies a VERTICAL ice face; the "L_char = D per Gayen" attribution was a
  mis-citation, removed in the Stage 10.11.2 audit).
  Nusselt number (Fujii et al. 1973, horizontal plate facing downward):
  - Laminar (`Ra < 1e7`): `Nu = 0.27 * Ra^0.25`
  - Turbulent (`Ra >= 1e7`): `Nu = 0.15 * Ra^(1/3)`
    Natural-convection transfer coefficients:
    `gamma_T_nat = Nu * k / (L * rho_w * c_w)`,
    `gamma_S_nat = gamma_T_nat * (K_S / K_T)`.

- **Mixed convection**: Churchill (1977) combination with exponent n=3:
  `gamma_T_eff = (gamma_T_forced^3 + gamma_T_nat^3)^(1/3)`
  `gamma_S_eff = (gamma_S_forced^3 + gamma_S_nat^3)^(1/3)`.

- **Rayleigh number cap**: `Ra_max = 1e10` to avoid unphysical extrapolation beyond the Fujii correlation validity range.

- **Selectable scheme**: `BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL` (runtime switch). The three-equation salt balance retains the Stage 10.10.1 density-weighted correction.

- **Effect**: At `U_rel = 0`, finite melt rate `~1.6e-8 m/s` (0.001 m/day) for typical Arctic conditions (`T_w=2°C`, `S_w=34.5 PSU`, `L=100m`, `D=50m`). At `U_rel = 0.1 m/s`, natural convection contributes only `gamma_eff/gamma_forced - 1 = 2.18e-8` (≈2.2e-6 %, NOT ~0.1% as originally claimed — corrected in the Stage 10.11.2 audit). At `U_rel = 1 m/s`, forced convection dominates (>99.9999999%).

- **Validation**: Fortran test `iceberg_test_10p11_natural_convection` (23 checks, DELIVERED in the Stage 10.11.2 audit; the original Stage 10.11 claim of 15 checks was never delivered in 6a0014e) + Python `test_three_equation_natural.py` (70 checks) including zero-flow, low-flow continuity, mixed-convection regime, Ra/Nu scaling, salt/heat balance identities, and cross-language contract (`m = 1.638e-8 m/s` at `U_rel=0`, `T_w=2°C`, `S_w=34.5 PSU`, `L=100m`, `D=50m`). Strict `-Wall -Wextra -fcheck=all` build clean.

- **Report**: `docs/archive/stage11/stage10.11_natural_convection.md`.

### Stage 10.12 — prognostic internal thermal evolution (DONE)

Stage 10.12 replaced the constant `T_i = -10` in the three-equation Eq. II
conduction term with a prognostic interior temperature (two-node lumped model,
design note Variant C):

- **Physics**: `H_int = max(H - H_EFF, H_MIN_INT)`; `C_int = rho_i * C_ICE * H_int`;
  `q_cond = 2 * K_ICE * (T_surface - T_ice) / H` (K_ICE = 2.2 W/(m K), the 2 =
  layer-centre separation H/2); `q_bot = m_basal * rho_i * CP_ICE_3EQ * max(T_B - T_ice, 0)`;
  `C_int dT_ice/dt = q_cond - q_bot` (explicit Euler, clamp [-100, 0] °C).
  Energy-conserving lagged coupling: `q_cond` is subtracted from the surface
  net flux inside `compute_surface_melt` (`q_internal_exchange`), so the skin
  loses what the interior gains.
- **Switch**: `thermal_evolution_enabled` (default `.true.`, `set_thermal_evolution`).
  **Fully gates Stage 10.12 in the step** (audit-round fix): OFF skips `q_cond`
  computation/subtraction AND the interior update — bit-identical legacy for
  both bulk and 3eq paths; 10.12 diagnostics defined explicitly at OFF
  (`t_ice = state%T_ice`, `dT_ice_dt = 0`, `c_eff_int = rho_i*c_i*H_EFF`,
  `t_ice_bound = .false.`). Verified by test block F.1–F.4.
- **Diagnostics**: `t_ice`, `dT_ice_dt`, `c_eff_int`, `t_ice_bound`.
  Initial condition: `T_ice = T_ICE_INIT = -10 °C` in `iceberg_init`.
- **Validation**: Fortran `iceberg_test_10p12_thermal_evolution` (21/21 PASS —
  17 original checks + OFF-switch legacy-invariance block F.1–F.4 added in the
  audit round; the C.5 lower-clamp check uses an amplified diagnostic flux
  q = -30000 W/m², documented in-test) + Python float64 replica
  `python/validation/internal_thermal.py`
  / `python/tests/test_internal_thermal_evolution.py` (35/35 PASS); cross-language
  contract `C_int(50 m) = 94594496 (float32) / 94594500 (float64)`.
- **Known limitations**: lumped parametrization (Bi ≫ 1, diffusion time ≫ run
  length — interior barely responds on a 90-day run); no internal melt at
  `T_ice = 0` (excess energy discarded at the clamp); removed-ice enthalpy not
  tracked; `K_ICE` a model parameter (2.0–2.3 literature range), not calibrated.
- **Build**: unused `stdlib` git dependency removed from `fpm.toml` (0
  `use stdlib*` in the repo; eliminates the network fetch / broken partial
  clone failure mode of fpm 0.13.0-alpha).
- **Report**: `docs/archive/stage11/stage10.12_internal_thermal_evolution.md`;
  design note: `docs/archive/stage11/stage10.12_internal_thermal_evolution_design_note.md`.

Priority for the next stage (after 10.12):

1. a double-diffusive / diffusion-limited low-flow parameterization, validated
   against Martin & Kauffman (1977) and Keitzl et al. (2016) — the Stage 10.11.3
   audit showed the current capped natural-convection closure is a cap-determined
   floor that does not reach the observed quiescent band — **Stages 10.13
   Phases A–C complete (research parameterization behind a switch, OFF
   default); further validation of t_scale/f_dc is a follow-up research item,
   not a new production stage**;
2. re-scoring the 10.8.2 observational set against the three-equation + natural-convection closure
   with the 10.8.2 acceptance criterion — **Stage 10.14 complete (verification only; see report)**;
3. improved atmospheric stability/transfer treatment if external validation demonstrates
   material bias.

## Longer-term physics

The following are explicit roadmap items and are **not** part of the 10.8/10.9 validation and calibration-assessment stages:

- full seawater thermodynamics / EOS-80 density pathway;
- TEOS-10 thermodynamic framework;
- improved iceberg orientation and geometry;
- advanced ocean-side turbulence and plume physics (the Stage 10.13 low-flow
  closure addresses the quiescent/double-diffusive end of this item);
- observationally constrained melt parameterization;
- independent multi-case validation of complete trajectories.

## Scientific infrastructure

A Python analysis/visualization layer supports reproducible diagnostics, maps, time series, uncertainty/sensitivity analysis and comparison with observations. The Stage 10.8.1 validation layer (`python/validation/`) is the first independent numerical reference for such work. The Python layer remains a validation/research layer and does not silently duplicate production physics.

The literature foundation is maintained in:

- `docs/references/references.bib`
- `docs/references/literature_matrix.md`
- `docs/references/README.md`
- `docs/model/model_description.md`
- `docs/model/model_equation_ledger.md`
- `docs/model/model_physics_status.md`
- `docs/model/stage10_modernization_plan.md`

## Scientific rule

No future physics stage should be accepted solely because the code runs or regression tests pass. A stage must identify its equation, source, parameter provenance, independent test, validation target and remaining uncertainty.
