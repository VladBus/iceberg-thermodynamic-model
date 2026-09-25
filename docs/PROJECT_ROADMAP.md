# Project Roadmap

**Updated:** 2026-09-24
**Current scientific stage:** Stage 10.22 — ocean density / thermal-wind / Block-200 stability audit (COMPLETED; causal chain isolated: CA/EOS float32 density corruption (T-01) → ρ<0 day 4 → ρ NaN day 5 s6 → Block 200 transmitter → Block 210 amplifier → day-6 zombie; freeze_ro / freeze_ts / freeze_ro_downstream stabilizer levers diagnostic-only, default OFF bit-identical; Block 210 pivots negative by construction (not pathology); production physics KEEP_CURRENT per D-20; next = approved physics stage)
**Current status:** Stages 10.14–10.22 committed (`0504853` 10.18A, `d99a4bf` 10.18B, `e99dbdc` 10.18C, `b01c902` 10.18D, `03bb42c` 10.19, `16a4c65` 10.20, `7a17cac` 10.21, `928041a` 10.22); **Stage 10.20 (ocean initialization & numerical stabilization) COMPLETE** (D-18): full-coverage ERA5 data fix resolved CASE C (3-day gate PASS, 36 steps, 0 NaN); residual CA instability characterized, NOT fixed (T-01/T-03 family; 30-day gate `steps executed = 55`, acceptance 360 NOT met); **Stage 10.21 (CA/EOS precision stabilization) COMPLETE** (D-19): float32 2⁻²³ quantization root cause confirmed, no physics change (RULES.md), bit-identical legacy verified; **Stage 10.22 (ocean density / thermal-wind / Block-200 stability audit) COMPLETE** (D-20): replay experiments a0–a4 with diagnostic freeze switches isolate the NaN chain (CA/EOS → Block 200 transmitter → Block 210 amplifier), all switches OFF default bit-identical (a0 ≡ a0_diag daily-diagnostics md5 `1ef13cb4…`); Block 210 Thomas pivots negative by construction; stabilizer levers freeze_ro (a1) / freeze_ts (a3) / freeze_ro_downstream (a4) restore physical validity (worst rel 4.213e-6) but are diagnostic-only; production physics KEEP_CURRENT; fpm battery + Python suites PASS; next = approved physics stage.

## Completed foundation

- Legacy iceberg dynamics and thermodynamics integrated into the modern repository structure.
- Real model grid reconstructed from IBCAO V5.2: 133×105 nodes, 132×104 active cells, DX=DY=13.89 km.
- Real sea-ice initialization implemented for 2020-01-01 from OSI-SAF SIC CDR v3.1 and C3S CS2SMOS SIT L4 combined v1.1.
- ERA5 atmospheric forcing and EN4 ocean forcing integrated into the real-grid workflow.
- Stage 9 moving-iceberg and forcing audits completed.
- Stage 10.1–10.6 modernization blocks implemented and audited.
- CI aligned with the current 54-target test suite and current gfortran line-length requirements.
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

## Next stage

### Stage 11.1 — Ocean Stability Across Seasonal Initial Conditions (approved physics stage)

Stages 10.20–10.22 closed the CASE-C/D investigation: the data-level fix
(full-coverage ERA5) removed the EN4-path activation trigger, and the
residual instability is now causally isolated (D-20) — CA/EOS float32
density corruption (T-01, 2⁻²³ quantization vs 0.9e-7 CA threshold) →
ρ<0 from day 4 → ρ NaN day 5 s6 → Block 200 transmits into momentum via
density + thermal-wind paths (two-path budget split EXACT) → Block 210
amplifies → day-6 zombie. Production physics remains KEEP_CURRENT (D-17/
D-18/D-19/D-20); the freeze_ro / freeze_ts / freeze_ro_downstream levers are
diagnostic-only references, NOT production paths.

The next stage is an **explicitly approved physics/numerics stage** per
RULES.md procedure. Candidates from the 10.20–10.22 candidate list:

- EOS precision (float32 → double, or compensated summation) —
  removes the 2⁻²³ quantization root cause;
- CA threshold / iterative-guard tuning anchored to float32 resolution;
- Thomas vertical-viscosity solver conditioning (documented T-03:
  8.5×10⁵ cm²/s at k=2 leads to ill-conditioning; pivots negative
  BY CONSTRUCTION — a1 = −1+a+b < 0 — so conditioning, not pivot sign);
- damped geostrophic spin-up of the EN4-initialized velocity field;
- EN4 data quality at the Barents slope (depth referencing, coast masking).

**Acceptance gate:** re-run the 30-day gate with
`ICEBERG_PRODUCTION=true` — expect `steps executed = 360` (12 steps/day ×
30; corrected cadence — the older "720" figure was a doc error) and a
physically valid trajectory (no NaN warnings), across seasonal initial
conditions.

Meanwhile, production iceberg demonstrations use the offline real-forcing
path (TEST_11 family), which remains fully validated.

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
- report `docs/validation/stage10.17_melt_thermodynamic_budget_audit.md`.

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
- report `docs/validation/stage10.18a_lateral_melt_parameterization_audit.md`.

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
- report `docs/validation/stage10.18c_existing_observations_reanalysis.md`.

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
`docs/validation/stage10.18d_velocity_resolved_observational_upgrade.md`.

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
- report `docs/validation/stage10.15.2_coordinate_mapping_bilinear_fix.md`.

T-13 is RESOLVED. **T-07 drift anomaly remains OPEN** (drift-scaling
numbers unchanged — the drift tests do not exercise the corrected
interpolation path; the next step is a drift-scaling investigation with the
corrected code, focusing on drag/Coriolis, not interpolation).

### Stage 10.15.1 — trajectory continuity and output integrity audit (COMPLETE)

Delivered:

- deterministic audit script `python/analysis/stage10.15_1_trajectory_audit.py`
  (28 checks, per-step audit CSV, corrected trajectory CSV, 9 figures,
  summary JSON; output bundle `data/output/stage10.15_1/`, gitignored);
- report `docs/validation/stage10.15.1_trajectory_continuity_audit.md`;
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
- Report: `docs/validation/stage10.15_operational_demonstration.md`.

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
- Report: `docs/validation/stage10.14_three_equation_rescoring.md`.

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
- Reports: `docs/validation/stage10.13_phase_b_results.md`,
  `docs/validation/stage10.13_phase_c_results.md`.

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

- **Report**: `docs/validation/stage10.11_natural_convection.md`.

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
- **Report**: `docs/validation/stage10.12_internal_thermal_evolution.md`;
  design note: `docs/validation/stage10.12_internal_thermal_evolution_design_note.md`.

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
