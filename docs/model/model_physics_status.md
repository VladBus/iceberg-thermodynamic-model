# Model Physics Block Status

**Date:** 2026-10-29
**Current repository stage:** **Stage 11 — FROZEN** research artifact (D-51, tag `stage11-final-frozen`, source `386c850`); **Stage 12 — active** (offline/prescribed GLORYS12 + ERA5 voxel iceberg; Stage 12.1 reconnaissance complete, no reader yet). The Stage 11 prognostic ocean is **not production-validated**: the N=24 30-day no-tide run is bounded (0 NaN, max U 1.999 m/s, CFL 0.518) but **N² fails** (min −0.01639 s⁻², 9,813 interfaces < −1e−6), **real tides/30-day tide validation are absent** (synthetic M2 only), **90-day** runs are unvalidated (T-38), the **production scheduler** is BLOCKED (T-39), and **N=1** is diagnostic only. Freeze record: `../STAGE11_FREEZE.md`. EOS-80 remains the runtime default.
**Ocean EOS statement:** the prognostic ocean uses **UNESCO EOS-80** by default from Stage 11.8B (`src/eos80_unesco.f90`; `EOS_MODE` unset → EOS80). Legacy Eckart remains available as an explicit fallback (`EOS_MODE=LEGACY`, bit-identical historical path). D-29/D-47 promotion is valid for the N=1 30-day matrix; production scheduler stays BLOCKED (T-39). Iceberg side uses freezing-point only (table row "Full seawater EOS" below refers to the iceberg module).
**Production baseline:** Stage 10.13 (low-flow closure behind `low_flow_closure_enabled`; OFF = Stage 10.12/10.10 legacy unchanged); Stage 10.19 adds the env-gated production iceberg connection (inert by default); Stage 10.20 adopts the full-coverage ERA5 Jan file for production gates (`src/param.f90` default path NOT changed); Stage 10.21 adds CA/EOS f32-precision research switches (`STAGE1021_CA_F64`, `STAGE1021_CA_MIX`, `STAGE1021_CA_SCOPE`, `STAGE1021_CA_EPS`) — all OFF by default, production bit-identical (KEEP_CURRENT); Stage 10.22 adds Block-200 stability-audit diagnostic switches (`STAGE1022_DIAG`, `STAGE1022_FREEZE_RO`, `STAGE1022_FREEZE_THERMAL_WIND`, `STAGE1022_FREEZE_TS`, `STAGE1022_FREEZE_RO_DOWNSTREAM`; env names `_FREEZE_RO`/`_FREEZE_TS`/`_FREEZE_RO_DOWNSTREAM`/`_FREEZE_THERMAL_WIND` + `_DIAG`) — all OFF by default, production bit-identical (KEEP_CURRENT); Stage 11.4-D32 adds the ERA5 nearest-edge coverage fallback in `era5_wind()` (loader-only production fix, Jan bit-identical); Stage 11.4-D33 fixes Ocean Baseline 11.x (Jan30/Apr29/Jul30/Oct30, 0 NaN); Stage 11.3C adds `STAGE113_DT/DT1` measurement-only timestep override (defaults = legacy 3600/120); Stage 11.3C.1 adds mm2/mm3 scaling (active only with override) + `s112_cfl_dist` percentiles (DIAG-gated)
**FPM test targets:** 77 (fpm auto-discovery of `test/*.f90` with a top-level `program`; count as of 2026-10-29). The full `fpm test` battery exits 0; 68 programs report `STOP 0` locally and the remainder skip when the gitignored data fixtures (`KOORD.DAT`, real grid) are absent. CI (`.github/workflows/ci.yml`) runs the auto-discovered battery + Python validation checks.
**Stage 12.2 ocean-source switch (2026-10-29, D-52):** `iceberg_forcing` gained an offline/prescribed **GLORYS12 reanalysis** forcing path via new modules `src/reanalysis_reader.f90` + `src/ocean_provider.f90`, selected by env **`OCEAN_SOURCE=reanalysis|model` (default `model` → Stage 11 prognostic ocean unchanged/bit-identical)**. Reader decodes packed int16 (`raw*scale_factor+add_offset`, `_FillValue`→NaN), does bilinear(lat,lon)+linear(non-uniform depth, clamp)+linear(time) interpolation, converts `so`→mass fraction (÷1000) and clips `siconc` to [0,1]; NaN=land/below-seafloor (corner-weight renormalisation, no zero-fill); out-of-range lat/lon/time → `ok=.false.`; no two-way coupling (ocean does not feel the iceberg). One-way, offline. Tests `test_reanalysis_reader` (9/9), `test_ocean_provider` (4/4), `test_iceberg_forcing_reanalysis` (4/4) pass locally, SKIP without the gitignored `.nc`. Report: `docs/validation/stage12.2_reanalysis_reader.md`. Voxel thermal core (12.3) not started.
**Stage 12.3 voxel thermal core switch (2026-10-30, D-53):** new `src/voxel_iceberg.f90` + `src/voxel_thermal_solver.f90` (per-voxel `T`/`φ`: finite-volume explicit conduction + enthalpy phase change; Stefan forced-convection ocean melt basal/lateral + air-surface sensible/latent melt; geometric erosion `φ<φ_min`; Archimedes waterline/draft/areas), integrated in `src/iceberg_thermodynamics.f90` behind env **`VOXEL_ENABLED=true|false` (default false → bulk prism thermodynamics bit-identical)**; `VOXEL_NX/NY/NZ`, `VOXEL_DX/DY/DZ`, `VOXEL_T_INIT`, `VOXEL_PHI_INIT`, `VOXEL_PHI_MIN` configurable. One-way/offline (ocean & atmosphere unperturbed by melt, D-51); prism `state` still drives drift (full voxel↔geometry feedback = Stage 12.4). Open items (spec): `γ_S`/salt boundary layer, `Tf(S,p)` at depth, relative-flow `u_rel`, cavity/spray zones, water freezing. Tests `test_voxel_thermal_solver` (7), `test_voxel_iceberg` (8), `test_voxel_integration` (6) green in CI (synthetic forcing, no `.nc`); full battery STOP 0=74. Report: `docs/validation/stage12.3_voxel_thermal_core.md`.
**Stage 12.4 CN + three-equation switch (2026-10-31, D-54/D-55):** voxel conduction is now **Crank–Nicolson** (`ICEBERG_THETA=0.5`, θ=1 = backward Euler) solved by **PCG+Jacobi** (tol `ICEBERG_CG_TOL=1e-10`), with **Rannacher** (2 BE steps after geometry change); explicit path retained via `VOXEL_THERMAL_SCHEME=explicit`. Boundary conditions are in the matrix (submerged Dirichlet `T_B`; exposed sensible Robin + explicit `Q_net`; **no Ga** — `Q_net` already contains net LW/SW/latent). 3D `h_norm` per face fixed (12.3 defect #1); melt cap `VOXEL_MELT_CAP=0.20` with clip counter; removal transfers sensible heat and records flushed mass/energy. Submerged melt uses the **three-equation** interface (`γ_T=KT·u_rel`, `γ_S=KS·u_rel`, `S_B(m)`, `T_B=Tf(S_B,P_f)`, `F(m)` bisection; `m≥0`, no accretion) with per-depth `ocean_profile` forcing and `u_rel` including `state%u,v`. `VOXEL_ENABLED` remains default OFF → bulk path bit-identical. Tests: A‑T1…A‑T9 + B‑T1…B‑T8 (CI-safe). Report: `docs/validation/stage12.4_crank_nicolson_stefan.md`.
**Stage 12.5 voxel-geometry drift (2026-10-31, D-56):** when `VOXEL_ENABLED=ON`, `iceberg_dynamics` uses the voxel **mass**, Archimedes **draft**, **wind A_sail** (= total exposed voxel surface, PDF §13.3) and **water A_sub_proj** (projected submerged silhouette perpendicular to the depth-averaged relative current, PDF §13.2) instead of the prism formulas. OFF (default) → prism path bit-identical. `A_perp`/`A_sub_proj` via `voxel_iceberg_get_frontal_area` (whole vs submerged silhouette; 45° cube = 14142 m², not 7071). Metacentric estimate `GM=BM−BG` (I_wp=L_eff W_eff³/12) reported, no capsize dynamics. Report: `docs/validation/stage12.5_voxel_geometry_drift.md`.
**Stage 12.6a real(8) + lat/lon + iceberg_run (2026-10-31, D-57):** `iceberg_state` migrated to **real(8)** (x,y,u,v,L,W,H,lat,lon,T_surface,T_ice,time,mass,volume); generic real4/real8 interfaces keep `app/main.f90` and legacy tests compiling. When `OCEAN_SOURCE=reanalysis`, `latitude/longitude` are authoritative (`dlat=v·dt/R`, `dlon=u·dt/(R cosφ)`; `model_coords_to_latlon` blocked); model mode keeps x/y. New standalone `iceberg_run` (second `[[executable]]`): offline GLORYS12 (+optional ERA5) Lagrangian trajectory, IBCAO-derived bathymetry via `coup1`+`latlon_to_model_coords`, NetCDF output, SKIP without data. Report: `docs/validation/stage12.6a_drift_latlon_iceberg_run.md`.
**Local status:** 10.12 Fortran 21/21 + Python 35/35 PASS; 10.13 Fortran 23/23 + Python/Fortran comparison 56/56 PASS; 10.14 Python 177/177 PASS; 10.15 TEST_11 7/7 PASS + diagnostics 7/7 checks PASS (30-day real-forcing trajectory); **10.15.1 audit 28/28 PASS; 10.15.2 fix: `iceberg_test_bilinear_axis_regression` 13/13 PASS (FAILS pre-fix, PASSES post-fix), TEST_11 re-run exit 0 with 0 coordinate jumps, corr(implied geo, reported) = 0.988; 10.16: `iceberg_test_drift_dynamics` 16/16 PASS + `test_stage10_16_drift_scaling.py` 13/13 PASS — T-07 PARTIALLY EXPLAINED (Coriolis-limited equilibrium, analytic match 0.1 %, no source change); 10.17: `iceberg_test_10p17_melt_budget` 47/47 PASS + `iceberg_test_10p17_90day` 7/7 PASS + `test_stage10_17_melt_budget.py` 40/40 PASS — melt budget internally consistent (M ≡ ρ_i·L·W·H, closure 5e-4 %), lateral legacy melt dominates 96.8 %, findings diagnostics-only, NO physics change; 10.18A: `test_lateral_melt_parameterizations.py` 458/458 PASS + `stage10_18a_lateral_melt.py` EXIT 0 — reference layer reproduces production exactly; legacy constant ≡ forced-convection side melt at U_eq ≈ 0.30 m/s; velocity-dependent literature variants give 30-day ΔM 1.3–3.6 % (vs 15.4 %) — lateral dominance formulation-dependent; NO production physics change; 10.18B: `test_observational_constraint.py` 62/62 PASS + `stage10_18b_observational_constraint.py` EXIT 0 — curated 17-case observational dataset; directly comparable N=5 (lab only); quiescent lab melt requires buoyant/plume term; legacy over-predicts cold low-ΔT; OPTION E + KEEP_CURRENT; NO production physics change; **10.18C: `test_stage10_18c_observations.py` 61/61 PASS + `stage10_18c_existing_observations.py` EXIT 0 — reanalysis with methodological corrections (RH80 = one lab fit; C_eff_lab/C_eff_submarine separated; Moyer19 = u_ice); FIELD velocity-resolved cases = 0; velocity dependence NOT IDENTIFIABLE; geometry/side-basal/wave NOT CONSTRAINED; OPTION D/E + KEEP_CURRENT; NO production physics change**; **10.18D: `test_stage10_18d_per_iceberg.py` 26/26 PASS + `stage10_18d_per_iceberg.py` EXIT 0 — Enderlin23 per-iceberg population retrieved (USAP-DC 10.15784/601679, MD5 verified) and analyzed (743 icebergs, 15 sites): regional maxima reproduce paper (WAP/WAIS max 1.1–1.3× of ~50/~40 m/a; EAIS/EAP p95 5.2/3.6 vs ~5 m/a); Thwaites 24 m/a/°C consistent per-iceberg (76 % of 167 bergs imply TF in 0.2–1.6 °C); legacy exceeds 99.6 % (TF=1.5) / 88 % (TF=0.6) of observed per-iceberg melt (median 14×/5.6×); velocity-dependent variants bracket observed medians; per-iceberg C_eff_submarine median 1.56e-7 = 0.16× production (range 0.08–0.33×); ADCP-equipped campaign designed; OPTION D refined + KEEP_CURRENT; NO production physics change**; **10.19: production gates 1d/7d/30d EXIT 0 — `app/main.f90` now runs the iceberg module behind `ICEBERG_PRODUCTION=true` (default OFF → legacy bit-identical); `get_ocean_profile` NaN-guard (`ok=.false.` on NaN — explicit detection of the known zombie state); forensic: day_00 clean (0 % NaN) → first NaN in Block 210 at III=2 of day 1 (Block 200 ~25 m/s geostrophic spike from EN4 thermal-wind init) → day_01 56.5 % NaN (142,081/251,370 cells; T clamped at 273.1 K) → iceberg start cell 15/18 levels NaN → **CASE C BLOCKER** with **CASE D root cause** (T-03 family; NOT introduced by this stage); iceberg `steps executed : 0` with explicit warnings (guarded, not silent); offline real-forcing path (TEST_11 family) fully validated; **D-17: KEEP_CURRENT physics + env-gated integration**; next = ocean-init stabilization stage (acceptance: 30-day gate `steps executed = 720`); NO production physics change (only NaN-guard in `src/`)**; **10.20: ocean-init stabilization — data-level fix adopted** (fullcov ERA5 Jan file, 124 slices): 3-day `ICEBERG_PRODUCTION=true` gate PASS (36 steps, 0 NaN), 30-day gate `steps executed : 55` — acceptance (360) NOT met; residual instability characterized (CA guard saturates days 1+: maxiter=1001, resid 1.1921E-07 = 2⁻²³ float32 EOS quantization), physics fix out of scope; NO production physics change; **10.21: `test_stage10_21_precision.py` 13/13 + `test_stage10_21_convective_adjustment.py` 18/18 PASS — T-01 closed** (CA guard saturation = float32 EOS quantization floor, NOT convective-physics instability; 6 experiments A0/EXP-A/B15/B24/C/D behind `STAGE1021_*` switches, all OFF default → bit-identical legacy verified); **eliminating the CA residual does NOT stabilize the ocean** (ALL closures bit-identical days 1–4, ALL diverge density-first mid-day-5; 30-day gates A0=55/A=57/B15=57/B24=51/C=56/D=52, acceptance NOT met → root cause = upstream Block-200 geostrophic spike / Block-210 Thomas solver, T-03 family; next = approved ocean-init stabilization physics stage); NO production physics change; D-19 KEEP_CURRENT (0.9e-7 threshold retained); two doc defects corrected (EOS header X/RO ranges, param.f90 z/dz); full fpm battery exit 0 (55 SUCCESS, 0 FAILED); all 16+ Python test suites PASS; strict `-Wall -Wextra -fcheck=all` build clean; `git diff --check` clean; **10.22: `test_stage10_22_block200_audit.py` 300/300 PASS (2026-09-25) — Block-200 stability audit closeout: causal chain ISOLATED at step/block granularity (CA/EOS float32 density corruption day 4 s1 → first ρ-NaN day 5 s6 → Block 200 transmitter → Block 210 amplifier), Block-210 Thomas pivots negative BY CONSTRUCTION (100 %, piv_min 1.0 — NOT pathology), 4 stabilizer levers restore physical validity 30/30 (worst rel 4.213e-6) but DIAGNOSTIC-ONLY (KEEP_CURRENT), production bit-identical under default-OFF `STAGE1022_*` gates (daily-diagnostics md5 `1ef13cb4…`); full fpm battery PASS (59 targets incl. `check.f90` + `drift_scaling_*` + 10.17 battery targets, STOP 0, 0 FAILED); no Fortran test added in 10.22; `git diff --check` clean **11.1: seasonal 7-day runs (Jan/Apr/Jul/Oct) + 30-day frozen control PASS; seasonal dependence established; frozen-ocean 30 days stable (ro 0.0075–0.0082 g/cm³); production physics UNCHANGED** ...
**Stage 10.7 report:** `docs/archive/stage11/stage10.7_basal_melt_validation.md`
**Stage 10.8.1 report:** `docs/archive/stage11/stage10.8.1_python_validation.md`
**Stage 10.8.2 report:** `docs/archive/stage11/stage10.8.2_observational_validation.md`
**Stage 10.9 report:** `docs/archive/stage11/stage10.9_calibration_assessment.md`
**Stage 10.10 report (incl. 10.10.1 correction):** `docs/archive/stage11/stage10.10_three_equation_interface.md`
**Stage 10.11.3 report:** `docs/archive/stage11/stage10.11.3_natural_convection_physics_audit.md`
**Stage 10.11 report:** `docs/archive/stage11/stage10.11_natural_convection.md`
**Stage 10.11.2 report:** `docs/archive/stage11/stage10.11.2_natural_convection_audit.md`
**Stage 10.12 report:** `docs/archive/stage11/stage10.12_internal_thermal_evolution.md`
**Stage 10.13 reports:** `docs/archive/stage11/stage10.13_diffusion_limited_low_flow_design_note.md` (Phase A), `docs/archive/stage11/stage10.13_phase_b_results.md` (Phase B), `docs/archive/stage11/stage10.13_phase_c_results.md` (Phase C)
**Stage 10.14 report:** `docs/archive/stage11/stage10.14_three_equation_rescoring.md`
**Stage 10.15 report:** `docs/archive/stage11/stage10.15_operational_demonstration.md`
**Stage 10.15.1 report:** `docs/archive/stage11/stage10.15.1_trajectory_continuity_audit.md`
**Stage 10.15.2 report:** `docs/archive/stage11/stage10.15.2_coordinate_mapping_bilinear_fix.md`
**Stage 10.16 report:** `docs/archive/stage11/stage10.16_drift_dynamics_t07_investigation.md`
**Stage 10.17 report:** `docs/archive/stage11/stage10.17_melt_thermodynamic_budget_audit.md`
**Stage 10.19 report:** `docs/archive/stage11/stage10.19_production_runtime_coupling_recovery.md`
**Stage 10.20 report:** `docs/archive/stage11/stage10.20_ocean_initialization_numerical_stabilization.md`
**Stage 10.21 report:** `docs/archive/stage11/stage10.21_convective_precision_stabilization.md`
**Stage 10.22 report:** `docs/archive/stage11/stage10.22_ocean_density_thermal_wind_block200_audit.md`
**Stage 11.1 report:** `docs/archive/stage11/stage11.1_ocean_stability_seasonal_initial_conditions.md`

## Classification

| Code  | Meaning                                                                                       |
| ----- | --------------------------------------------------------------------------------------------- |
| **A** | Physics/implementation confirmed for the current scope; no changes required                   |
| **B** | Working approximation with scientific limitations; further validation or modernization needed |
| **C** | Modern physical formulation implemented and audited                                           |
| **D** | Outdated/erroneous formulation to be removed                                                  |
| **E** | Planned new physics                                                                           |

## Current status

| Block                                | Current formulation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |                        Status |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------: |
| Geometry                             | Rectangular prism; prognostic L/W/H                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |                             A |
| Position                             | Prognostic x/y; diagnostic lat/lon; moving forcing by x/y                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |                           A/B |
| Dynamics                             | Wind drag, water drag, Coriolis, pressure gradient                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |                             B |
| Real grid                            | IBCAO V5.2-derived 133×105 grid; 132×104 active; DX=DY=13.89 km                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |                             A |
| ERA5 forcing                         | u10/v10/t2m/d2m/tcc/msl/snowfall; spatial interpolation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |                             B |
| EN4 forcing                          | Temperature/salinity profiles with draft interpolation/extrapolation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |                             B |
| Sea-ice initialization               | OSI-SAF SIC + C3S CS2SMOS SIT, 2020-01-01                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |                             B |
| Solar geometry                       | Astronomical declination/EOT approximation following Spencer 1971                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |                             C |
| Shortwave attenuation                | Rayleigh + water vapour + aerosol + cloud parameterization                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |                             B |
| Sensible heat                        | Neutral bulk transfer, fixed coefficient                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |                           C/B |
| Latent heat                          | Neutral bulk transfer + ice saturation from Murphy & Koop 2005                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |                           C/B |
| Surface temperature                  | Prognostic T_surface with finite effective heat capacity                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |                             B |
| Internal temperature                 | Prognostic two-node lumped interior (Stage 10.12): T_ice via explicit Euler, q_cond = 2·K_ICE·(T_s−T_i)/H, q_bot basal sensible sink, clamp [−100, 0]°C; switch `thermal_evolution_enabled` fully gates the stage (OFF = bit-identical legacy, F.1–F.4); Fortran 21 + Python 35 checks                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |                             C |
| Phase change                         | Explicit melt/sublimation/deposition partition and latent heat                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |                             B |
| Freezing point                       | EOS-80/UNESCO pressure-dependent freezing-point equation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |                             C |
| Ocean heat transfer                  | Relative flow; laminar/turbulent flat-plate Nu correlation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |                             B |
| Basal melt                           | `m_basal = gamma_T * max(T-Tf,0)/(rho_ice*Lf)` (independently audited in Stage 10.7; independent Python layer in `python/validation/`, Stage 10.8.1; observational validation vs published melts, Stage 10.8.2; Stage 10.9: scalar coefficient **not identifiable** across the 10.8.2 sources — no calibration made)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |                             B |
| Lateral melt                         | Depth-averaged thermal forcing; legacy/approximate closure `m_l = C_LATERAL·⟨ΔT⟩_D` (C_LATERAL = 1e-6 m/(s·K)), velocity-independent, full-height half-perimeter update; **10.18A (B)**: formula correctly implemented; constant ≡ forced-convection side melt at U_eq ≈ 0.30 m/s vs simulated 0.005–0.027 m/s → lateral dominance (96.8 %) formulation-dependent; **10.18B (B)**: observational dataset; lab quiescent melt requires buoyancy/free-convection term; lab ΔT^1.5 nonlinear; legacy over-predicts cold low-ΔT; **10.18C (B)**: methodological corrections (RH80 = one lab fit, C_eff_lab vs C_eff_submarine separate, Moyer19 = u_ice not u_rel); **FIELD velocity-resolved cases = 0** (no public paired melt+ΔT+U_rel); velocity dependence NOT IDENTIFIABLE; geometry/side-basal/wave NOT CONSTRAINED; legacy compatible with aggregate effective thermal sensitivities (not validated); OPTION D/E — bounds only; **10.18D (B)**: Enderlin23 per-iceberg population (743 icebergs, retrieved — 10.18C gap closed); regional maxima reproduce paper; Thwaites 24 m/a/°C consistent per-iceberg; **legacy exceeds 99.6 % (TF=1.5) / 88 % (TF=0.6) of observed per-iceberg melt**; velocity-dependent variants bracket observed medians; per-iceberg C_eff_submarine median 0.16× production; ADCP-equipped campaign designed; OPTION D refined — per-iceberg bounds; velocity dependence still NOT IDENTIFIABLE | B (research audit + observational constraint; production unchanged) |
| Three-equation interface             | H&J99/J2010 closure; velocity-scale gamma_T=K_T·U, gamma_S=K_S·U (K_T=1.1e-3, K_S=3.1e-5); Eq. III corrected: `rho_w gamma_S (S_w - S_B) = rho_i m S_B` with `rho_i/rho_w = 910/1028` (Stage 10.10.1); separately selectable; conduction to T_i=-10 (model-selected constant, NOT from H&J99); independently validated (Fortran 25 + Python 65 checks, cross-language contract)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |                             C |
| Natural convection                   | Horizontal-plate correlation (operative turbulent `0.15·Ra^(1/3)` from Lloyd & Moran 1974, NOT Fujii 1973) + Churchill 1977 mixing; double-diffusive Ra with thermal/haline buoyancy; L_char = iceberg length L (correlation scale is A/p); Ra cap 1e10; gamma_T_nat, gamma_S_nat added to forced convection via Churchill n=3 mixing; separately selectable as THREE_EQUATION_NATURAL; independently validated (Fortran 23 + Python 70 checks). **Stage 10.11.3 audit (B):** cap always active (uncapped Ra=5.7e19) → Nu pinned at 323.17, haline/Le term numerically inert, beta_T/beta_S inert, laminar branch latent; zero-flow m=1.4e-3 m/day is 7-700x BELOW the observed quiescent band (does NOT close the 10.8.2 gap); haline sign is opposite to the physical stabilizing role; coefficient attribution corrected; real mechanism is double-diffusive (Martin & Kauffman 1977; Keitzl et al. 2016; Middleton et al. 2021). Production physics UNCHANGED |                             B |
| Low-flow closure (Stage 10.13)       | Research parameterization, OFF by default (`low_flow_closure_enabled`): diffusion-limited sublayer δ*S = clip(√(κ_S·t), 1e-4, 5e-2) m + double-diffusive enhancement f=2.5 (criterion R*ρ > 1/Le & Re_b < 1, Middleton 2021); smooth cosine blend of γ_T/γ_S into the three-equation solve; U=0 → 0.107 m/day (T=2°C/S=35 PSU, in observed band); forced branch bit-identical at high U; legacy OFF verified; Fortran 23 + Python/Fortran comparison 56 checks; t_scale/f_dc not calibrated                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | C (research parameterization) |
| Full seawater EOS                    | Not implemented; freezing point only                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |                             E |
| TEOS-10                              | Not implemented                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |                             E |
| Independent observational validation | Basal melt: 10.8.2 set scored against bulk (10.8.2), low-flow (10.13 Phase B) and 3eq/3eq+natural closures (Stage 10.14: point metrics + quiescent gap; no calibration). Full coupled trajectory validation: not yet complete | E (coupled trajectory) |

## Stage 10.6 ocean-side heat transfer

For relative speed `U_rel`, the implementation computes

`Re = U_rel * L_char / nu`

and selects the canonical flat-plate branch:

- `Re < 5e5`: `Nu = 0.664 Re^0.5 Pr^(1/3)`;
- `Re >= 5e5`: `Nu = 0.037 Re^0.8 Pr^(1/3)`;
- `gamma_T = Nu*k/L_char`.

The expanded length exponents are therefore `L_char^(-0.5)` and `L_char^(-0.2)`, respectively. The production code uses `L_char = L` as a pragmatic characteristic length because iceberg orientation is not prognosed.

This is a **flat-plate forced-convection approximation**, not a geometry-specific iceberg derivation. At `U_rel = 0`, forced-convection transfer is zero; natural convection is not included. Weeks & Campbell (1973) and FitzMaurice & Stern (2018) are retained as comparison/validation literature and are not used to claim that the flat-plate correlation is uniquely correct for icebergs.

## Key accepted limitations

1. The current iceberg has no orientation, so the streamwise characteristic length is approximated by `L`.
2. The heat-transfer correlation is inherited from canonical boundary-layer theory rather than derived specifically for a rectangular iceberg.
3. Natural convection is absent at zero relative flow on the bulk forced path; the selectable `THREE_EQUATION_NATURAL` scheme provides only a cap-determined floor (see limitation 11).
4. Lateral melt remains an approximate legacy closure and does not yet use the full three-equation ice-ocean interface formulation (the three-equation closure is implemented for the basal path; Stage 10.10). **Stage 10.18A research audit (B):** the legacy formula `m_l = C_LATERAL·⟨ΔT⟩_D` is implemented correctly, but its constant coefficient is equivalent to forced-convection side melt at **U_eq ≈ 0.30 m/s** (implied γ_T = 304 W/(m²·K)) while the simulated relative velocity at the draft is 0.005–0.027 m/s — a factor 10–60; literature-based velocity-dependent side-melt formulations give 30-day mean lateral melt 0.013–0.052 m/day (5–20× below the legacy 0.26 m/day) — the lateral dominance (96.8 %) is **formulation-dependent**. **Stage 10.18B observational constraint (B):** a curated 17-case observational dataset (RH80 lab DIRECT; Sermilik/Antarctic INDIRECT) shows (i) quiescent lab melt (0.04–1.6 m/day) requires a nonzero-at-U=0 buoyant/plume term (forced-convection-only variants fail), (ii) the lab temperature dependence is nonlinear (ΔT^1.5) — the linear legacy over-predicts low-ΔT melt by up to 3.6× and exceeds the observed total submarine melt in 3/4 Antarctic cold-shelf cases, (iii) the observational C_eff distribution (N=9, median 0.54× production, range 0.28–1.06×; Thwaites slope 24 m/a/°C = 0.76×) brackets the production constant without uniquely determining it, (iv) velocity dependence is qualitatively supported (Antarctic shear statement) but not field-quantified, (v) geometry (full-height vs submerged) and wave erosion are **NOT CONSTRAINED** by available observations. **Decision: OPTION E** (insufficient discrimination) + **production KEEP_CURRENT**; no production physics change; research alternatives live in `python/validation/lateral_melt.py` + `python/validation/observational_constraint.py`; next: Stage 10.18C targeted observational design. **Stage 10.18D per-iceberg upgrade (B):** the Enderlin23 individual-iceberg dataset was retrieved (USAP-DC 10.15784/601679 via direct POST; MD5 verified) and analyzed at iceberg level (743 observations, 15 sites): the legacy C_LATERAL exceeds 99.6 % (TF = 1.5 °C) / 88 % (TF = 0.6 °C) of observed per-iceberg melt (median ratio 14×/5.6×); the velocity-dependent literature variants bracket the observed medians; the per-iceberg C_eff_submarine median is 1.56e-7 m/(s K) = 0.16× production (region range 0.08–0.33×); the Thwaites 24 m/a/°C relationship is consistent per-iceberg (76 % of 167 icebergs imply TF within 0.2–1.6 °C). Velocity dependence remains NOT IDENTIFIABLE (no U_ocean in any public dataset) — the ADCP-equipped Schild21-style campaign design is the velocity-resolved prerequisite. **Decision: OPTION D refined** (per-iceberg bounds) + **production KEEP_CURRENT**; no production physics change.
5. The EOS-80 implementation computes freezing point only; it is not a full EOS-80/TEOS-10 density equation of state.
6. Some shortwave attenuation constants require stronger literature provenance/sensitivity documentation.
7. Independent observational validation of the full coupled thermodynamic evolution remains a future task.
8. Iceberg latitude/longitude are diagnostic and updated from x/y each step (`model_coords_to_latlon`); they are not independent prognostic variables.
9. Three-equation closure (Stage 10.10/10.10.1) previously used a constant internal ice temperature `T_i = -10` in the conduction term of Eq. II (model-selected, NOT from H&J99); **Stage 10.12 replaces the constant with prognostic `state%T_ice`** (two-node lumped interior, explicit Euler, switch `thermal_evolution_enabled` — fully gated in `iceberg_thermodynamics_step`, OFF is bit-identical legacy verified by test block F.1–F.4; see `docs/archive/stage11/stage10.12_internal_thermal_evolution.md` §4.1). Eq. III salt balance was corrected in Stage 10.10.1 from `gamma_S (S_w - S_B) = m S_B` to `rho_w gamma_S (S_w - S_B) = rho_i m S_B` (MOM6/PISM/MITgcm/H&J99 Eq.4 convention); the correction is documented in `docs/archive/stage11/stage10.10_three_equation_interface.md` (no separate 10.10.1 report). The `K_T`/`K_S` convention is U-based (Jenkins et al. 2010 Table 2) rather than a melt-driven `u*`-based Stanton. Natural convection at zero relative flow exists only on the selectable `THREE_EQUATION_NATURAL` scheme (Stage 10.11); the bulk forced path still has zero transfer at U=0 (see Stage 10.13 low-flow closure for the diffusion-limited alternative).
10. Natural convection (Stage 10.11; audited in Stage 10.11.3, classification B). The closure uses a horizontal-plate correlation with a double-diffusive Rayleigh number and Churchill (1977) mixed-convection mixing. Stage 10.11.3 audit findings: (a) the operative turbulent coefficient `0.15*Ra^(1/3)` is from Lloyd & Moran (1974), not Fujii et al. (1973) (which is a theoretical laminar uniform-heat-flux study with `Nu ~ Ra^(1/5)`); (b) the Rayleigh cap `1e10` is ALWAYS active for realistic bergs (uncapped anchor `Ra=5.7e19`), so `Nu` is pinned at 323.17 and the laminar branch/transition (`Ra=1e7`, 113% discontinuity) are latent; (c) in the capped regime the haline term (including `Le=100`) and the values of `beta_T`/`beta_S` are numerically inert (dropping the haline term reproduces the same `m`); (d) the haline term is carried with a positive sign although meltwater freshening is gravitationally stabilizing — the physical minus sign gives `Ra<0 -> Nu=0 -> m=0`; (e) the characteristic length is `state%L`, whereas the source correlations use `L* = A/p`; (f) zero-flow melt is `m = 1.4e-3 m/day`, **7-700x below** the observed quiescent band 0.01-1 m/day, so Stage 10.11 did NOT close the 10.8.2 gap (the earlier "consistent with 0.01-1 m/day" claim was incorrect and is removed); (g) the real mechanism is double-diffusive / diffusion-limited convection (Martin & Kauffman 1977; Keitzl et al. 2016; Middleton et al. 2021), which the closure does not represent. Gayen et al. (2016) remains context only (vertical ice face). Production physics is unchanged by 10.11.3; the recommended follow-up is a future diffusion-limited low-flow parameterization. See `docs/archive/stage11/stage10.11.3_natural_convection_physics_audit.md`.
11. Low-flow closure (Stage 10.13) is a **research parameterization** behind `low_flow_closure_enabled` (OFF by default): t_scale = 1 day dominates the quiescent melt (order-of-magnitude sensitivity), f_dc = 2.5 is not calibrated, κ_S follows the Le=100 repo convention (4.4% below the Python reference 1.5e-9), and the three-equation interface freshening reduces the coupled m vs the far-field Python m_low. It does not claim universal validation. See `docs/archive/stage11/stage10.13_phase_c_results.md` §§14–15.

## Verification policy

Internal tests establish implementation and conservation identities. They do not establish observational validity. Each future physical modernization must provide: literature basis, equation/parameter provenance, independent analytical tests, regression tests, and an external validation target where applicable.

## Stage 11.7E.4 — sea ice

`STAGE117E_NETCDF_SEAICE` (default OFF) selects the NetCDF sea-ice reader;
OFF is bit-identical to legacy. Real Jan-2020 OSI-SAF/C3S is connected and
B (ON vs legacy-real) is bit-identical for 7 days. No physics or EOS change.

## Stage 11.7E.4.1 — audit closure + diagnostic foundation

Phase 0: 6 documentation/metrics corrections applied (sea-ice units, 25.72 m
thickness investigation, documentation sync, decision D-32, sea-ice provenance,
env-gated reader FATAL). Phase 1–3 were STUBS (superseded by 11.8.0.0:
homogeneous column returned NOT_COMPUTED; snowfall used the processed 6-h
spacing, a misread). Phase 4: ocean diagnostic plan for 11.8 (T0–T6 ladder).
11.7E.5 deferred. No physics/EOS change. Regression: targeted tests PASS,
strict build clean.

## Stage 11.8.0.0 — diagnostic contract correction (real red tests)

Real Fortran homogeneous-column test executes production `convect_column`:
LEGACY and EOS80 both PASS with ΔT = ΔS = 0, 1 iteration, exit 0. The prior
"FAIL expected" premise was false — a perfectly homogeneous column is stable;
the CA defect requires a weak inversion. Snowfall source metadata confirms (SUPERSEDED by Stage 11.8.0.0.1: status downgraded to INFERRED_12H, then corrected by v2 to hourly/3600, then to
UNCERTAIN in 11.8.0 T0 - valid_time spacing is sampling frequency, not
accumulation period; see T-19)
hourly accumulation (T-19 v2: R=1.009; `GRIB_stepType=accum`); divisor 3600 is
correct and unchanged (processed 6-h spacing is interpolation). Sea-ice
provenance now records the actual source: ON = netcdf + manifest version/MD5;
OFF = legacy_1_*.ice + NONE. `sit` is clarified as HST*sic (area-weighted
contribution). The 25.72 m day-1 max is per-category `hice`, not `sit`; it is
a thermodynamic-growth defect (category 1 reaches 4.03 m vs HMAX 0.3 m), not
a unit/aggregation error. Ocean stabilization gate N-15 / D-29 / D-33
documented. No physics/EOS change; snowfall divisor changed only in T3-CORRECTIVE-3 (T-19 v2).

## Stage 11.8.0.0.1 — T2 tests + snowfall status correction

T2 diagnostics now GENUINELY fail (non-zero exit) on invariant violation; the homogeneous-column test is reclassified as a SMOKE control (stable in both EOS modes: dT=dS=0, 1 iteration). The weak-inversion core test (`convect_column`, production) verifies heat/salt conservation (0.0 rel error), confined mixing (LEGACY: exactly levels 2-3 -> 3.95) and stability; under EOS-80 the in-situ density criterion masks the inversion (nmix = 0) — a documented 11.8 finding, not fixed here. Snowfall period: T-19 v2 CDS probe (24 hourly fields, no step) gives R=1.009 -> HOURLY; divisor changed 43200 -> 3600 (Stage 11.8.0 T3-CORRECTIVE-3). CI restructured (Fortran steps in the fpm job; Python-job data-dependent tests self-SKIP explicitly). No physics/EOS change; snowfall divisor changed only in T3-CORRECTIVE-3 (T-19 v2).

## Stage 11.8.0 T0 — data & units verification (no changes)

Snowfall: T-19 RESOLVED by the v2 CDS probe — 24 hourly fields, no `step`,
R=1.009 -> hourly accumulation; divisor 3600 (T3-CORRECTIVE-3). The old
`step=12` artifact conclusion is invalid. EN4: shipped seasonal products carry a legacy shadowed
z metadata grid (values read by index; actual depths are the model's) ->
T-20; Jan rebuild contains sub-freezing cells -> T-22; initial-state density
inversions (up to ~1e-3 g/cm3-anomaly scale) quantified as T2-tier load.
ERA5: Jan product covers the model with >=1.28 deg margins; April lacks
0.15 deg to the south (8 cells D32-clamped) -> T-21; nearest-time selection
and cyclic-longitude behaviour documented; H-2: ERA5 wind unrotated to the
EPSG:3996-rotated grid flagged for T4. Full report:
`docs/validation/stage11.8.0_T0_data_units_verification.md`.

## Stage 11.8.0 T1 — ERA5 forcing contract (no changes)

Verified against the production reader: bilinear spatial interpolation is
exact on a linear field (max error 0.0) with correct decreasing-latitude flip
and reject/accept edge behaviour; the longitude wrap is **partially correct
only** (170 E -> 180.0; latent, 0 production cells affected; T-23). Temporal
selection is nearest-record with clamping and midpoint-tie-earlier, gaps take
the nearest record (T-24; axis PASS). **Wind rotation: the grid is rotated
(X median 50.2 deg from east, max 81.3) and `era5_wind` applies NO
geographic->grid rotation -> H-2 CONFIRMED CRITICAL for T4.** T-21 accepted
as a 0.072 % limitation. Report:
`docs/validation/stage11.8.0_T1_forcing_contract_verification.md`.

## Stage 11.8.0 T2 — CA/EOS core diagnostics (no changes)

Homogeneous column: dT=dS=0 with both the f32 and f64-core paths in both EOS
modes (no false convection). Weak inversion: mixed with exact algorithmic
conservation (real64 reference heat 0, salt 1.3e-16; production state is
float32-limited — T-27). **A-1 CONFIRMED: CA compares IN-SITU density at the
local pressure; there is no potential-density criterion. Under EOS-80 a
potential-density-unstable column can be in-situ stable and is left unmixed
(T-25, critical).** T-23 longitude wrap formalized with a narrow-file red
test (east-of-file query returns the western edge; fix = edge-clamping).
Report: `docs/validation/stage11.8.0_T2_ca_eos_core_diagnostics.md`.

## Stage 11.8.0 T3-PREP — EN4 data corrected (data only)

All four seasonal EN4 initial products were regenerated with the corrected
builder: z_model_m matches the model DATA z (600 m) and Jul/Oct rebuilds now
exist (T-20 FIXED — the shipped data had been produced on a different pipeline,
up to 7.5 degC from a rebuild at the same indices). A UNESCO Tf(S,p) clamp
(p ≈ z_m, +1e-5 degC f32 margin, salinity unchanged) removes the sub-freezing
initial cells (T-22 FIXED; clamped: Jan 12,589 / Apr 2,525 / Jul 0 / Oct 553;
0 cells below Tf everywhere). EN4 T0 and T3-PREP verification are CLEAN.
No physics/EOS change; CA/T-25, T-23 and H-2 were NOT fixed.
Report: `docs/validation/stage11.8.0_T3-PREP_en4_data_correction.md`.

## Stage 11.8.0 T3 — rest state (no forcing): UNSTABLE

With all external forcing disabled and zero initial velocity, the corrected
EN4 ocean does not stay at rest: LEGACY reaches Umax 3.86 / Vmax 5.91 m/s and
EOS-80 4.48 / 4.71 m/s within 30 days (no NaN); kinetic energy grows x911-
x1128; heat/salt drift 0.6-1.5 %. CA statistics differ by two orders of
magnitude between the modes yet the early growth is nearly identical, so the
blow-up is not CA-driven. Drivers: **T-28** (934 wet levels loaded as 0 degC
from the product/runtime mask gap), **T-29** (advection writeback zeroes the
T/S boundary row/column - 1,341 cells from day 1), plus the T-03 core
pressure-gradient instability. T-25 remains critical but is not the T3
driver. New metrics baseline: `docs/wiki/stages/stage11/evidence/t3_rest_result.json`.
Report: `docs/validation/stage11.8.0_T3_rest_state_diagnostic.md`.

## Stage 11.8.0 T3-CORRECTIVE — T-28/T-29 fixed, rest still UNSTABLE

The EN4 product now matches the runtime mask (143,422 wet levels; builder
uses `build/grid_dump_kt1.dat`; reader FATALs on mismatch/unfilled cells) and
the FCT advection no longer zeroes the T/S boundary row/column (writeback
restricted to the interior; red/green Fortran test). In the 30-day zero-forcing
re-run the interface defects are gone, S drift falls from 3.4 to 0.43/0.31 PSU
and heat/salt conservation improves ~26x/6x, yet the current still grows to
3.9-4.7 m/s (KE x674-737). EOS-80's CA converges (guard 0) with nearly the
same growth, so the remaining driver is the core T-03 pressure-gradient
instability, not CA/T-25 or the fixed interface defects. T4 remains NO-GO;
next is T3-CORRECTIVE-2. Report:
`docs/validation/stage11.8.0_T3-CORRECTIVE_mask_advection_fix.md`.

## Stage 11.8.0 T3-CORRECTIVE-2 — T-03 root cause: CA density writeback -> PGF

Diagnostic only. The rest-state growth is not a PGF-stencil error (surface
double-count 1.5e-5) and not boundary-only. `RO` is not prognostic: `eos_diag()`
runs only at init/final, so the density used by Block 200 is refreshed only by
convective adjustment. `FREEZE_RO` (CA mixes T/S but does not write RO) bounds
the flow at 0.20 m/s / 6.1e13 J in both LEGACY and EOS-80; the baselines grow to
3.9-4.7 m/s / 6.8-8.1e15 J. CA-induced Delta-RO reaches 8.26 kg/m3 and its PGF
work share grows from 7.9 % to 99.6 %. The initial thermal-wind state (0.283 m/s,
transport 0.144 m/s) is the seed; the SW 600-m clamped boundary/topography
localises it; dt=1800 is bounded (0.53 m/s), dt=3600 exponential. T-25 is
revised: EOS-80 CA convergence does not exonerate the RO writeback. T4 NO-GO;
T3-CORRECTIVE-3 (fix) requires D-33. Report:
`docs/validation/stage11.8.0_T3-CORRECTIVE-2_t03_diagnosis.md`.

## Stage 11.8.0 T3-CORRECTIVE-3 — T-19 fixed, E1–E3 tested, T3b fails

**T-19:** v2 CDS probe (24 hourly validity times, no `step`) gives
R=mean(12:00)/mean(all 24)=**1.00898** -> hourly accumulation; the 43200 s
divisor is superseded by **3600 s**. Hourly records are summed to 6-h windows;
merged April/Jan products regenerated; tests CONFIRMED_1H / 120/120.

**E1/E2/E3 (all OFF default):** `STAGE118_RO_PROGNOSTIC` recomputes RO after CA
before B200 (CA skips local writeback) — no effect because CA already rewrites
RO for every wet column; `STAGE118_CA_POTENTIAL` compares both levels at the
lower-level pressure — no effect in LEGACY (Eckart pressure-independent),
EOS80-only; `STAGE118_CA_F64_N2` uses real64 differences and N² < -1e-6 —
reduces CA mixings 7.08e6 -> 61,454/day and guard 1001 -> 0, but does not
stabilize. **T3b:** Umax 3.902 m/s, KE15 1.641e14 J, KE30 8.696e15 J,
ratio 52.98 (acceptance <2.0) -> FAIL. E6 sponge reduces the peak only
(3.71 -> 1.71 m/s at extreme damping); balanced init also fails. The remaining
instability is the coupled T/S-advection + density-refresh system at 13.89 km /
dt=3600 (T-33). T4 NO-GO; T3-CORRECTIVE-4 required. Report:
`docs/validation/stage11.8.0_T3-CORRECTIVE-3_fixes.md`.

## Stage 11.8.0 T3-CORRECTIVE-4 — Numerical stabilization (T3b PASS)

Grid Δx=13.89 km vs first baroclinic Rossby radius 2.36 km (ratio 0.17):
baroclinic eddies are unresolved; T3b cannot reach a perfect rest state.
Numerical compromise: **dt=1800 s + Laplacian Ah=10000 m²/s** (switch
`STAGE118_LAPLACIAN_VISC`, default OFF; Ah via `STAGE118_AH`), with E1+E2+E3,
no sponge. Result: max |U| **0.147 m/s**, max |V| 0.103 m/s, KE15 3.899e13 J,
KE30 2.216e13 J, KE30/KE15 **0.568** -> PASS under revised bound <5.0. dt=1800
alone 0.517/1.112; dt=900 0.278/1.275; Ah=5000/10000/20000 all pass. The added
dissipation is a compromise that damps physical eddies as well as numerical
noise; the state is bounded/drifting, not resolved baroclinic dynamics. Report:
`docs/validation/stage11.8.0_T3-CORRECTIVE-4_numerical_stabilization.md`.

## Stage 11.8.0 T4-PREP — H-2 and T-23 fixed

**H-2:** `STAGE118_WIND_ROTATION` (default OFF) rotates ERA5 geographic wind
to the rotated grid using alpha from KOORD.DAT FI/DL; mean 50.06°, median
50.18°, range 14.02–81.28°; 20-cell angular error 2.8e-14°; Fortran OFF/ON
1-day interior vector error 3.45e-4 m/s. **T-23:** `STAGE118_LON_CLAMP`
(default OFF) replaces cyclic wrap with edge clamping; narrow 10–70E test
75E→70E (ON) vs 10E (OFF); T1 spatial/temporal PASS with ON. Both switches
OFF by default are bit-identical legacy. T3 with both ON unchanged
(max |U| 0.147 m/s, KE30/KE15 0.568). **T4 GO.** Report:
`docs/validation/stage11.8.0_T4-PREP_wind_rotation_lon_clamp.md`.

## Stage 11.8.0 T4 — First forced run (PASS)

30-day ERA5-forced run with rotation/clamp ON, dt=1800, Ah=10000, E1+E2+E3,
LEGACY. No NaN/Inf. max |U| 0.970 m/s, max |V| 0.598 m/s, KE0/15/30
4.645e13/4.408e14/6.699e14 J, KE30/KE15 **1.520** (<10). T/S drift
0.311 °C/0.229 PSU; volume 0, salt 8.319e-4, heat 5.228e-3 (forced cooling
≈−3.94 W/m²; flux closure not archived, T-34). Ekman day 15 mean −40.4°,
61.4 % right; day 30 geostrophic (+22°). Mean wind work +3.805e10 W;
mean Laplacian dissipation 7.48e9 W. T4 vs T3: KE ×30.2, max |U| +0.824 m/s.
**T5 GO.** Report: `docs/validation/stage11.8.0_T4_wind_forcing.md`.

## Stage 11.8.0 T5 — 90-day FAIL, April PASS, T-34 CLOSED

90-day January forced run (all T4 switches) is bounded to day 45, then explodes
by day 60: KE30 6.704e14 → KE60 1.178e19 J (ratio 17,568), Umax 488 m/s, CA
input inversion 2.50e2; SIGFPE at day 61. April 30-day is stable
(max |U| 0.866 m/s, KE30/KE15 1.541, seasonal KE ratio 0.752, max-U ratio
0.893); April Ekman right-turning not observed at day 15. T-34 CLOSED
(physical, tentative): 30-day heat drift implies −3.94 W/m² (Jan) and
−9.81 W/m² (Apr), plausible Arctic cooling; volume 0, salt <1e-3. 180-day
skipped because 90-day failed. **T6 NO-GO; T5-CORRECTIVE required.** Report:
`docs/validation/stage11.8.0_T5_time_stepping_stability.md`.

## Stage 11.8.0 T5-CORRECTIVE — no storm-safe Δt/Ah configuration

90-day January Q1 search with all T4 switches: config1 dt900/Ah20000 FPE
after day63 (Umax 1361 m/s); config2 dt900/Ah30000 first NaN day67; config3
dt600/Ah30000 first NaN day70; exploratory config4 dt600/Ah50000 first NaN
day74. Storm peak 2020-03-16 18 UTC, max wind 26.86 m/s, model τmax 0.609 Pa.
Stronger dissipation only delays the collapse, so the failure is not a simple
ocean momentum CFL/Ah limit. No chosen configuration; T5 April baseline
remains the stable seasonal reference. **T6 NO-GO; T5-CORRECTIVE-2 required.**
Report: `docs/validation/stage11.8.0_T5-CORRECTIVE_storm_safe.md`.

## Stage 11.8.0 T5-CORRECTIVE-2 — storm root cause

Config1 (dt900/Ah20000) 75-day detailed diagnostics: first RO<0 day29, first
S<0 day46 (−7.55 PSU), T>10 °C day57, collapse days63-65 (T max 532 °C, S min
−9,859 PSU, RO min −2.9e7). Negative cells start at the surface near the
lateral boundary and spread along it; boundary max |U| exceeds interior
days60-64. CA nmix remains ~3e5/day (no spike); CA inversions grow only after
T/S corruption. Wind work 20-64 GW vs dissipation 24-102 GW. Q1 wind peak
2020-03-16/day75 is **after** collapse; failure is cumulative.
**Root cause: MULTIPLE — ADVECTION_ERROR primary, BOUNDARY_REFLECTION
amplifier, CA secondary.** Reference originals absent. T6 NO-GO;
T5-CORRECTIVE-3 (monotone/positive salinity advection + boundary). Report:
`docs/validation/stage11.8.0_T5-CORRECTIVE-2_diagnostics.md`.

## Stage 11.8.0 T5-CORRECTIVE-3 — monotone + sponge (FAIL on RO)

Original/current advection is FCT with Zalesak limiter; reference BCs are
no-gradient with no radiation/sponge. Implemented `STAGE118_MONOTONE_ADVECTION`
(hard S positivity/no-new-max and T∈[−2,30] safety net) and
`STAGE118_SPONGE_BOUNDARY` (5 cells, α=1/day). Tests PASS. 90-day Config1:
no NaN, max |U| 1.141, KE90/KE60 0.975, S≥0, T∈[−2,30], but **RO min −24.24
and 3,187 RO<0 cells** at day90 -> FAIL. April 30-day PASS (KE30/KE15 1.530,
max |U| 0.853). Hard caps create nonphysical S=0/T=30 density; not a valid
density fix. **T6 NO-GO; T5-CORRECTIVE-4 required.** Report:
`docs/validation/stage11.8.0_T5-CORRECTIVE-3_monotone_advection.md`.

## Stage 11.8.0 T5-CORRECTIVE-4 — density repair (FAIL)

Hard T caps removed; `STAGE118_DENSITY_REPAIR` (default OFF) adjusts T or S
minimally to make RO≥0 after advection, before CA. Test: RO −0.0242→+2.39e-4,
S 0→0.0326 → PASS. 90-day Config1: repair adjusts ~139,620 cells/day, but
CA/B200 recreate negative density (day65 RO −416), NaN day69, max |U| 34,027
→ FAIL. April 30-day with repair PASS (KE30/KE15 1.530, max |U| 0.853,
RO min 0). Iceberg .docx files absent; voxel PDF has only ice-conduction
stability, no ocean density guidance. **ACCEPT LIMITATION: 30-day forced runs
only; T6 NO-GO.** Report:
`docs/validation/stage11.8.0_T5-CORRECTIVE-4_density_repair.md`.

## Stage 11.8.0 T6-SEASONAL — 30-day validation + production retest

T5 chain closed with accepted limitation T-38 (90-day storm instability;
30-day Jan/Apr/Jul/Oct validated). July PASS: max |U| 0.542, KE30/KE15 0.827,
RO 0, no NaN. October PASS: 0.690, 2.152, RO 0, no NaN. Production scheduler
30/30 days, 720/720 fire-steps PASS: max |U| 0.494, KE30/KE15 1.480, RO 0,
no NaN — historical 55/360 blocker resolved for 30-day. EOS80 production
10-day smoke PASS (0.405, RO 0). 11.8A matrix GO (16 cells; spec
`docs/validation/stage11.8A_matrix_plan.md`); matrix not started.
Report: `docs/validation/stage11.8.0_T6-SEASONAL_validation.md`.

## Stage 11.8B — EOS-80 runtime default (BREAKING CHANGE)

- `EOS_MODE` unset/empty now selects **EOS80**; `EOS_MODE=LEGACY` is the
  explicit fallback. Unknown values select EOS80 with a warning.
- Default verification: default = explicit EOS80 = matrix EOS80 (32/32 NetCDF
  files MD5-identical); LEGACY fallback = matrix LEGACY (32/32 identical).
- Matrix: 8/8 N=1 cells PASS with the corrected absolute-density gate (T-41).
- Production scheduler: NOT changed; T-39 BLOCKED (ice/cadence artifact).
- Migration: `docs/MIGRATION_GUIDE_EOS80_DEFAULT.md`.
- Audit: `docs/validation/stage11.8B_runs_inventory.md`,
  `docs/wiki/stages/stage11/evidence/reproducibility_audit.json`.

## References

See `docs/references/references.bib` and `docs/references/literature_matrix.md`. The private `work_references.bib` is a PDF-location aid and is intentionally not committed.
