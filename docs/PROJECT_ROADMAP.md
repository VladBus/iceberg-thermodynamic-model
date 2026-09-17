# Project Roadmap

**Updated:** 2026-09-17
**Current scientific stage:** Stage 10.15.1 — trajectory continuity and output integrity audit (real geographic-coordinate discontinuity identified — T-13; audit-only, source unchanged)
**Current status:** Stage 10.14 committed and pushed (`ca60c62`); Stage 10.15 committed and pushed (`472fe75`). Stage 10.15.1 (audit) complete (commit pending): model-space trajectory continuous and kinematically consistent, but geographic lat/lon has 8 real jumps (~0.17°) from transposed bilinear weights in `model_coords_to_latlon`/`bilinear_interp_3d` (T-13); corrected projection continuous (corr 0.988); 28 Python regression checks; fix deferred to a dedicated stage (source unchanged in the audit).

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
| 10.15.1  | Trajectory continuity and output integrity audit (follow-up to 10.15): model-space x/y continuous and kinematically consistent (implied speed == reported, corr 0.988); geographic lat/lon has **8 real jumps (~0.17°, ~19 km)** at model-cell crossings — root cause **transposed bilinear weights in `model_coords_to_latlon` / `bilinear_interp_3d`** (T-13); corrected projection continuous; 28 Python regression checks; existing Fortran coord tests miss the bug (node sampling + 0.2° tolerance; round-trip errors 0.064–0.179° only WARNING); audit-only — **source NOT changed**, fix deferred                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | **Complete**; classification: audit — real discontinuity identified; production UNCHANGED; commit pending |

## Immediate next step

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
