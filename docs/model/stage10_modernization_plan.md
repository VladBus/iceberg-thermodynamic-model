# Stage 10 — Physics Modernization Plan

**Updated:** 2026-09-17
**Current stage:** 10.15 (operational end-to-end demonstration; no physics change)
**Current classification:** C — Stage 10.14 is a verification stage (10.8.2 re-scoring, Python 177 checks; no calibration, production unchanged); Stage 10.15 is an operational demonstration (30-day real-forcing Lagrangian iceberg run, trajectory + diagnostics; full-model runs with the documented ocean NaN state); Stage 10.13 remains a research parameterization behind `low_flow_closure_enabled` (OFF = legacy unchanged)

## Purpose

Stage 10 replaces selected legacy thermodynamic closures with physically explicit formulations while preserving the legacy model's interfaces and regression behaviour wherever the new physics is not in scope. Every physics stage is required to have a literature basis, explicit equations, parameter provenance, independent tests, and a documented limitation statement.

## Completed stages

### 10.1 — Atmospheric shortwave radiation

**10.1.1 Solar geometry:** astronomical declination and equation-of-time approximation following Spencer (1971), UTC convention, longitude east-positive, polar-night handling.

**10.1.2 Atmospheric attenuation/cloud:** shortwave flux is assembled from solar zenith geometry, clear-sky attenuation, water vapour, aerosol and cloud terms. The current constants require stronger provenance/sensitivity documentation.

### 10.2 — Prognostic surface temperature

`T_surface` is prognostic with an effective surface heat capacity and explicit treatment of the transition to melting. Independent analytical tests were added; the discrete crossing treatment remains an identified validation target under extreme fluxes.

### 10.3 — Atmospheric sensible and latent heat

Neutral bulk-transfer formulation with fixed transfer coefficients, modern latent heat of sublimation and Murphy & Koop (2005) saturation vapour pressure over ice. The formulation is not yet stability-resolved.

### 10.4 — Phase-change partitioning

Surface energy is partitioned explicitly between non-latent heat, latent vapour flux and melt. Sublimation/deposition are represented through a prognostic atmospheric vapour mass diagnostic. Stage 10.4.2.1 added direct `Q_surface` diagnostics to remove a circular test dependency. The remaining limitation is that the vapour-flux physics itself still requires independent external validation.

### 10.5 — EOS-80 freezing point

The ocean freezing point is computed from the UNESCO/Fofonoff–Millard pressure-dependent equation. The function is used consistently at iceberg draft and in depth-dependent ocean thermal forcing. This is a freezing-point implementation only; a complete seawater density EOS is not implemented.

### 10.6 — Relative ocean flow and ocean-side heat transfer

Basal ocean-side heat transfer uses depth-dependent relative velocity between the iceberg and ocean current. The transfer coefficient is calculated from canonical flat-plate correlations with a laminar/turbulent transition at `Re = 5e5`. Stage 10.6.1 independently audited the formulation and corrected the documented length exponents.

## Stage 10.6.1 accepted limitations

- `L_char = L` is an approximation because iceberg orientation is not prognostic.
- Flat-plate correlations are not a geometry-specific derivation for an iceberg.
- Forced-convection transfer vanishes at zero relative speed; natural convection is not represented.
- Weeks & Campbell (1973) and FitzMaurice & Stern (2018) indicate that iceberg-specific melt behaviour can differ from simple flat-plate closures.
- Lateral melt remains a separate approximate closure.

## Stage 10.7 — Independent scientific validation of basal melt (DONE)

Independent scientific audit of the basal-melt chain (Re/Nu/γ_T/Tf/ΔT/m) with all expected values computed from embedded literals, not from production diagnostics. 17 independent checks (cases A–J) PASS; classification remains **B — PASS WITH LIMITATIONS**. Production Fortran unchanged. Findings:

- Formulation matches Weeks & Campbell (1973)/Eckert & Drake (1959) to float32 precision; `L_char = L` is supported by FitzMaurice & Stern (2018) for tabular icebergs.
- Turbulent branch (m ∝ U^0.8·L^−0.2·ΔT) is the realistic regime for Arctic icebergs (Re ≈ 5.5e5–2.7e8); laminar only for small bergs / weak flow.
- Order-of-magnitude agreement with in-repo three-equation estimate (St·u\*, St=0.011 commented): factor ≈1.8 at U=0.1 m/s; observed submarine-melt band 0.01–1 m/day reproduced.
- Documented limitations unchanged: no natural convection (m→0 at U_rel=0), `L_char=L` orientation approximation, no three-equation closure.

Validation report: `docs/validation/stage10.7_basal_melt_validation.md`. Test: `iceberg_test_10p7_basal_melt_validation` (17 checks).

## Stage 10.8.1 — Independent Python validation layer (DONE)

A minimal, pure-Python re-implementation of the production basal-melt chain
(EOS-80 Tf, `U_rel`, Re, Nu, `gamma_T`, `DeltaT`, `m_basal`) that is
mathematically independent of the Fortran code (no Fortran calling/import/
output parsing). Located in `python/validation/basal_melt.py`, with a 44-check
analytical suite in `python/tests/test_basal_melt_validation.py` (plain-Python
runner; pytest-compatible). Production Fortran unchanged; classification remains
**B — PASS WITH LIMITATIONS** (numerical consistency validated, not
observational validity). Cross-check reproduces the Stage 10.7 float32
reference `m = 1.5852e-6 m/s` (residual ≈ 2.8e-5, reference-digit rounding;
raw float32-vs-float64 ≈ 1.3e-7). Report:
`docs/validation/stage10.8.1_python_validation.md`.

## Stage 10.8.2 — Observational validation of basal melt (DONE)

Curated 19-record observational dataset of published, DOI-verified submerged
melt rates (lab-primary Russell & Head 1980; field-primary Keys & Williams
1984; synthesis Neshyba & Josberger 1980; remote-sensing Enderlin & Hamilton
2014, Enderlin et al. 2016/2023; context Orheim/Budd et al. — Rignot et al.
2010 explicitly excluded as calving not submarine). `python/validation/
observational_validation.py` evaluates the **production** closure bit-identical
to the 10.8.1 layer and reports:

- point metrics on the 4 forcing-anchored rows: RMSE 0.108, MAE 0.092,
  bias +0.083 m/day; KW84 reproduced within range (ratio 0.70); NJ80 synthesis
  overestimated by factor 2.1-5.8 (dT 8 -> 2 °C);
- natural-convection gap: quiescent-lab melt 0.04-1.59 m/day vs model 0.0 —
  5.7-7.3 orders above the model floor;
- inverse-U: Greenland fjord rates (0.16-0.5 m/day) reproducible at plausible
  U_rel 0.1-1.0 m/s (dT 2-4 °C);
- all comparable observations fall in the turbulent regime (Re > 5e5); laminar
  branch has no field anchor.

Checks: `python/tests/test_observational_validation.py` (15 blocks, 229
checks). Report: `docs/validation/stage10.8.2_observational_validation.md`.
Classification of the validation pass: **C (pass with documented systematic
limitations)**; production physics UNCHANGED. Reference metadata added to
`docs/references/references.bib` (Enderlin x3, Josberger, Keys, Neshyba,
Orheim, Schild) and `russefl-head` mis-keyed entry corrected (author, journal,
volume, DOI).

## Stage 10.9 — Calibration assessment of the basal-melt coefficient (DONE)

Source-aware identifiability study of whether the production turbulent
heat-transfer coefficient can be calibrated against the 10.8.2 observational
set. **Conclusion: NO scalar coefficient is identifiable** — inferred required
values span ~8.3x between the two independent sources (NJ80 0.286x, KW84 1.418x;
pooled geomean 0.427), the NJ80 observation scales as dT^1.73 while the closure
is dT^1.0 (functional-form mismatch, not a scale offset), and a scalar
multiplier times zero leaves the quiescent natural-convection branch exactly at
zero (structurally uncalibratable, 5.7-7.3 orders gap). Corrects two 10.8.2
claims (basal-plane-dominance, submarine≈basal) and qualifies three others
(KW84 range, NJ80 factor, inverse-U as basal proxy).

Checks: `python/validation/calibration_assessment.py` +
`python/tests/test_calibration_assessment.py` (20 blocks, 212 checks, A-T,
pure-Python). All 7 named literature DOIs Crossref-verified. Report:
`docs/validation/stage10.9_calibration_assessment.md`. Classification:
**C (validation insufficient for robust calibration)**; production physics
UNCHANGED. Next stage is the three-equation interface, not a coefficient retune.

## Stage 10.10 — Three-equation ice-ocean interface (DONE)

Implemented and independently validated. Separately selectable
`BASAL_MELT_SCHEME_THREE_EQUATION`; bulk path physics unchanged (statements identical, re-indented into the scheme else-branch).

- **Physics**: three-equation closure (Holland & Jenkins 1999; Jenkins et al.
  2010 Table 2). `gamma_T = K_T U_rel`, `gamma_S = K_S U_rel` with
  `K_T = 1.1e-3`, `K_S = 3.1e-5`; Eq. I `T_B = Tf(S_B,P)`, Eq. II
  `rho_w c_w gamma_T (T_w - T_B) = m rho_i (L_f + c_i max(T_B - T_i,0))`,
  Eq. III `gamma_S (S_w - S_B) = m S_B`; bisection with doubling upper bound.
  Constants `rho_w=1028`, `c_w=3974`, `c_i=2009`, `T_i=-10` (H&J99), `rho_i`,
  `L_f` production.
- **Diagnostics**: `t_interface`, `s_interface` added to the basal diagnostics.
- **Bug found & fixed during implementation**: local variable `latent_heat`
  shadowed the module constant `LATENT_HEAT` (Fortran case-insensitivity),
  corrupting Eq. II (m -> Infinity once `latent_heat` read as 0). Renamed the
  local to `l_heat`. Class: real implementation bug, no literature conflict.
- **Validation**: Fortran test `iceberg_test_10p10_three_equation` (19 checks,
  0 errors) + `python/validation/three_equation.py` /
  `python/tests/test_three_equation.py` (46 checks, 0 errors); cross-language
  contract: H&J99 anchor `m = 9.4457e-9` m/s and production end-to-end
  `m = 3.998e-6` m/s agree to rel < 1e-4 between Fortran float32 and Python
  float64; warm-ocean rate 0.345 m/day inside the observed 0.01-1 m/day band.
- **Remaining (documented)**: constant `T_i` conduction (internal thermal
  evolution deferred); natural-convection floor for the low-flow branch not
  implemented (the largest structural gap from 10.8.2); `K_T`/`K_S` are the
  U-based J2010 convention, the melt-driven `u*`-based Stanton (St = 0.011)
  remains an open convention question (Stage 10.9).
- **Report**: `docs/validation/stage10.10_three_equation_interface.md`.

## Stage 10.10.1 — Mass/salt convention correction in the three-equation interface (DONE)

Corrected the salt balance (Eq. III) from the equal-density reduction
`gamma_S (S_w - S_B) = m S_B` to the physically consistent mass-conserving
form `rho_w gamma_S (S_w - S_B) = rho_i m S_B`, which reduces to
`S_B = gamma_S S_w / (gamma_S + (rho_i/rho_w) m)` with `rho_i/rho_w = 910/1028
= 0.8852...`. This matches the MOM6 `mom_ice_shelf`, PISM basal-melt, and
MITgcm shelfice documented conventions, and Holland & Jenkins (1999) Eq. (4)
(brine salt flux `rho_i M wB (S_I - S_B)`). The Stage 10.10 formulation
implicitly set `rho_i/rho_w = 1`.

- **Production changes**: `src/iceberg_types.f90` (new constant
  `RHO_ICE_WATER_RATIO`), `src/iceberg_thermodynamics.f90` (three reduction
  expressions in `solve_three_equation_interface` + doc block rewrite);
  `python/validation/three_equation.py` (module docstring, `_s_interface`
  with optional `rho_ratio` defaulting to the new constant).
- **Effect**: canonical H&J99 anchor m increases from 9.4457e-9 to 1.0438e-8
  m/s (+10.5%, amplified by near-zero thermal drive); production end-to-end m
  increases from 3.998e-6 to 4.067e-6 m/s (+1.7%); warm band 0.351 m/day
  (inside 0.01-1 m/day).
- **T_i = -10 degC attribution corrected**: model-selected constant internal
  temperature, NOT from H&J99 (H&J99 solve conduction explicitly). Docs updated.
- **Validation**: Fortran test extended to 25 checks (19+6 new density-reduction
  identity/limit/monotonicity checks); Python suite extended to 65 checks
  (46+19 new Stage 10.10.1 checks including salt-flux identity, freshwater-flux
  identity, limits, monotonicity, cross-language contract). All tests PASS.
  Strict `-Wall -Wextra -fcheck=all` build clean. `git diff --check` clean.
- **Report**: `docs/validation/stage10.10_three_equation_interface.md`.

## Stage 10.11 — Natural-convection basal melt / low-flow closure (DONE)

Corrected the fundamental limitation of zero basal melt at zero relative flow by implementing a physically-motivated natural-convection closure for the three-equation ice-ocean interface.

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
  `gamma_S_eff = (gamma_S_forced^3 + gamma_S_nat^3)^(1/3)`
  where `gamma_T_forced = K_T * U_rel`, `gamma_S_forced = K_S * U_rel`.

- **Rayleigh number cap**: `Ra_max = 1e10` to avoid unphysical extrapolation of correlations beyond their validated range.

- **Selectable scheme**: `BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL` (runtime switch). The three-equation salt balance retains the Stage 10.10.1 density-weighted correction.

- **Production changes**: `src/iceberg_types.f90` (new constants, natural convection function), `src/iceberg_thermodynamics.f90` (new solver `solve_three_equation_interface_natural` with explicit coupling); `python/validation/three_equation_natural.py` + `python/tests/test_three_equation_natural.py` (70 checks).

- **Effect**: At `U_rel = 0`, finite melt rate `~1.6e-8 m/s` (0.001 m/day) for typical Arctic conditions (`T_w=2°C`, `S_w=34.5 PSU`, `L=100m`, `D=50m`). At `U_rel = 0.1 m/s`, natural convection contributes only `gamma_eff/gamma_forced - 1 = 2.18e-8` (≈2.2e-6 %, NOT ~0.1% as originally claimed — corrected in the Stage 10.11.2 audit). At `U_rel = 1 m/s`, forced convection dominates (>99.9999999%).

- **Validation**: Fortran test `iceberg_test_10p11_natural_convection` (23 checks, DELIVERED in the Stage 10.11.2 audit; the original Stage 10.11 delivery claimed 15 checks that were never written) + Python `test_three_equation_natural.py` (70 checks) including zero-flow, low-flow continuity, mixed-convection regime, Ra/Nu scaling, salt/heat balance identities, and cross-language contract (`m = 1.638e-8 m/s` at `U_rel=0`, `T_w=2°C`, `S_w=34.5 PSU`, `L=100m`, `D=50m`).

- **Report**: `docs/validation/stage10.11_natural_convection.md`.

## Stage 10.12 — Prognostic internal thermal evolution (DONE)

- **Classification**: C — production physics ADDED on a separately switchable path; two-node lumped interior implemented and independently validated (Fortran 21 + Python 35 checks).
- **Physics**: prognostic `state%T_ice` replaces the constant `T_i = -10` (now `T_ICE_INIT`, an initial condition) inside the three-equation Eq. II conduction term:
  `H_int = max(H - H_EFF, H_MIN_INT)`; `C_int = rho_i * C_ICE * H_int`;
  `q_cond = 2 * K_ICE * (T_surface - T_ice) / H` (K_ICE = 2.2 W/(m K));
  `q_bot = m_basal * rho_i * CP_ICE_3EQ * max(T_B - T_ice, 0)`;
  `C_int dT_ice/dt = q_cond - q_bot` (explicit Euler, clamp [-100, 0] °C).
  Energy-conserving lagged coupling: `q_cond` subtracted from the surface net
  flux inside `compute_surface_melt` (`q_internal_exchange`).
- **Switch**: `thermal_evolution_enabled` (default `.true.`, `set_thermal_evolution`). **Fully gates Stage 10.12 in the step** (audit-round fix): OFF skips `q_cond` computation/subtraction AND the interior update — bit-identical legacy for both bulk and 3eq paths; 10.12 diagnostics defined explicitly at OFF. Verified by test block F.1–F.4.
- **Diagnostics**: `t_ice`, `dT_ice_dt`, `c_eff_int`, `t_ice_bound`.
- **Validation**: Fortran `iceberg_test_10p12_thermal_evolution` (21/21 PASS — 17 original + OFF-switch legacy-invariance block F.1–F.4; C.5 lower-clamp check uses an amplified diagnostic flux q=-30000 W/m², documented in-test) + Python float64 replica `python/validation/internal_thermal.py` / `python/tests/test_internal_thermal_evolution.py` (35/35 PASS); cross-language contract `C_int(50 m) = 94594496 (float32) / 94594500 (float64)`.
- **Known limitations**: lumped parametrization (Bi ≫ 1, τ ≫ run); no internal melt at T_ice = 0 (excess energy discarded at clamp); removed-ice enthalpy not tracked; K_ICE not calibrated.
- **Report**: `docs/validation/stage10.12_internal_thermal_evolution.md` (design note: `docs/validation/stage10.12_internal_thermal_evolution_design_note.md`).
- **Build**: unused `stdlib` git dependency removed from `fpm.toml` (offline reproducibility).

## Stage 10.13 — Diffusion-limited / double-diffusive low-flow closure (DONE, Phases A–C)

- **Classification**: C — research parameterization integrated behind `low_flow_closure_enabled` (OFF by default); production physics on the three-equation path extended; forced branch bit-identical at high U; OFF = legacy.
- **Physics**: hybrid closure for the quiescent/low-flow end of the basal melt: diffusion-limited sublayer `delta_S = clip(sqrt(kappa_S * t_scale), 1e-4, 5e-2) m` with double-diffusive enhancement `f = 2.5` (Middleton et al. 2021 criterion `R_rho > 1/Le` & `Re_b < 1`); effective transfer coefficients blended via cosine smoothstep over U in [1e-3, 1e-2] m/s; the melt rate is obtained from the **unchanged** three-equation solve (`allow_zero_flow` scoped to this path; legacy guard `U<=0 -> m=0` preserved by default).
- **Switch**: `low_flow_closure_enabled` (default `.false.`, `set_low_flow_closure`); active only in the `THREE_EQUATION` scheme branch; OFF = legacy (verified).
- **Diagnostics**: `low_flow_enabled/active/regime/u_rel/re_b/ri_star/r_rho/delta_s/delta_t/f/gamma_t/gamma_s/iter/converged`.
- **Validation**: Fortran `iceberg_test_10p13_low_flow` (23/23 PASS; blocks A–I: legacy OFF, U=0 activation 0.107 m/day, transition smoothness, forced preservation bit-identical, DDC criterion, bounds, 3eq consistency, CMP output, determinism) + Python/Fortran comparison `python/validation/low_flow_fortran_comparison.py` (56/56 PASS) + Python prototype `python/tests/test_low_flow.py` (167/167 PASS); full fpm battery exit 0; strict build clean.
- **Known limitations**: t_scale = 1 day dominates quiescent melt (order-of-magnitude sensitivity); f_dc = 2.5 not calibrated; kappa_S Le=100 convention 4.4% below the Python reference; interface freshening reduces coupled m vs far-field m_low; research parameterization, not universal validation.
- **Reports**: `docs/validation/stage10.13_phase_c_results.md` (Phase C), `docs/validation/stage10.13_phase_b_results.md` (Phase B), `docs/validation/stage10.13_diffusion_limited_low_flow_design_note.md` (Phase A).

## Stage 10.14 — Re-scoring of the 10.8.2 observational set against the 3eq / 3eq+natural closures (DONE, verification-only)

- **Classification**: C — verification stage; no physics change, no calibration, no switch-default change; production UNCHANGED.
- **Purpose**: the roadmap item after 10.13 (re-scoring the 10.8.2 set against the three-equation + natural-convection closure with the 10.8.2 acceptance criterion). Applies the already-implemented 3eq (10.10/10.10.1) and 3eq+natural (10.11) closures to the curated 19-record observational set for the first time.
- **Results (u>0, n=4)**: teq point metrics RMSE 0.366 / MAE 0.277 / bias +0.277 vs bulk 0.108 / 0.092 / +0.083 — the 3eq closure does NOT reduce the systematic NJ80 bias (KW84 improves 0.70x → 1.09x; NJ80 worsens 5.8x → 11.7x at dT=2). Functional-form mismatch (obs ~ dT^1.73 vs dT^1.0, Stage 10.9) persists and is amplified.
- **Results (quiescent, n=5)**: bulk 0/5, teq 0/5 (gap persists for closures without a natural branch), teq_nat 5/5 in the observed band 0.01–1 m/day at the lab-block scale L=1 m (ratios 0.56–1.39). Scale analysis: at L=1 m Ra=4.6e9 < cap 1e10 → Nu unpinned; at L=100 m Ra=4.6e15 > cap → Nu pinned at 323.17, γ_T,nat 77x smaller → the 10.11.3 "zero-flow 1.4e-3 m/day, gap not closed" statement is **scale-specific** (iceberg scale), not a statement about the lab experiments that produced the RH80 data.
- **Validation**: `python/validation/three_equation_scoring.py` + `python/tests/test_three_equation_scoring.py` (177/177 PASS, blocks A–H); all 7 pre-existing Python suites unchanged (822 checks, 0 errors).
- **No new physics introduced**: the closures under test are the production 3eq / 3eq+natural schemes; this stage only scores them against the observations.
- **Report**: `docs/validation/stage10.14_three_equation_rescoring.md`.

## Stage 10.15 — Operational end-to-end demonstration (DONE, no physics change)

- **Classification**: operational demonstration with documented limitations; no physics change, no calibration, no switch-default change; production UNCHANGED.
- **Purpose**: prove whether the existing model executes end-to-end with real/repository-supported inputs and produces interpretable outputs; identify the actual remaining bottleneck (not a new physical modernization).
- **Results**: Lagrangian iceberg 30-day real-forcing run (TEST_11, 720 hourly steps): trajectory produced (74.83→75.07 °N, 30.31→29.84 °E), mass −15.4 %, melt bounded (basal 0.049 / lateral 0.260 / surface 0.022 m/day), 7/7 test checks + 7/7 diagnostics checks PASS. Full-model runs (1 day and 7 days, `fpm run`) exit 0; day_00 clean; 3D ocean fields NaN from day 1 (stable 56.5 %, T frozen at 273.15 K) — the documented Stage 8 EN4-init imbalance family, pre-existing, not introduced here.
- **Key operational findings**: (1) the production executable `app/main.f90` does NOT run the Lagrangian iceberg module (no `use iceberg*`); the iceberg model is reachable only through test programs; (2) the Eulerian ocean state is dead from day 1 with the real EN4 initialization, so coupled ocean-forcing for the iceberg is not yet possible (offline prescribed forcing only); (3) T-12 root-symlink prerequisite exercised — with symlinks, all previously-skipped grid-dependent tests PASS.
- **Diagnostics**: `python/analysis/stage10.15_diagnostics.py` (7 figures + summary JSON); output bundle `data/output/stage10.15/` (gitignored).
- **No new physics introduced**: this stage only executes and diagnoses the existing model.
- **Report**: `docs/validation/stage10.15_operational_demonstration.md`.

## Stage 10.16 — Drift dynamics and T-07 investigation (DONE, no physics change)

- **Classification**: controlled-experiment investigation; no physics change, no calibration; production UNCHANGED.
- **Result**: **T-07 PARTIALLY EXPLAINED** — the low wind-drift ratio (0.04–0.13 %) is the physically correct Coriolis-limited equilibrium u = F_wind/(M·f) of a 100-m cube (analytic match 0.1 %; ratio ∝ 1/L; C_Dw-independent); the 1–2 % reference implies a drag-limited regime or a wind-driven (Ekman) surface current absent from this offline model; secondary numerical damping 1/√(1+(f·dt)²) ≈ 0.89 at dt=3600 s documented; NO source correction.
- **Report**: `docs/validation/stage10.16_drift_dynamics_t07_investigation.md`.

## Stage 10.17 — Melt and thermodynamic budget audit (DONE, no physics change)

- **Classification**: audit; no physics change, no calibration; production UNCHANGED.
- **Result**: mass ≡ ρ_i·L·W·H (max 1.5e-5 rel), model budget closure 5e-4 % (30 d); **lateral legacy melt dominates 96.8 %** (C_LATERAL = 1e-6 m/(s·K), velocity-independent, 0.26 m/day); basal 3.0 %, surface 0.12 %, vapor 0.08 %; scalings verified; findings diagnostics-only (lateral full-height vs submerged convention in unused helpers; q_net_surface dimensional defect; unpopulated diag%q_cond/q_bot; TEST_11 CSV format); extended TEST_11 diagnostics (24 columns, 15 byte-identical); 90-day diagnostic run −42.2 % (Q1 atmosphere, ocean frozen at January — annual extrapolation premature).
- **Report**: `docs/validation/stage10.17_melt_thermodynamic_budget_audit.md`.

## Next modernization sequence

Priority candidates after 10.13/10.14:

1. improved treatment of iceberg-specific ocean heat transfer, including
   re-scoring the 10.8.2 set against the three-equation + natural-convection closure with the
   10.8.2 acceptance criterion — **Stage 10.14 complete (verification-only, see report)**;
2. improved atmospheric stability/transfer treatment if validation demonstrates a material need;
3. modern seawater thermodynamics, including a full EOS-80/TEOS-10 pathway,
   only as a dedicated future stage.

### Data and validation foundation

Real-data validation should preserve exact product/version metadata for ERA5, EN4, IBCAO V5.2, OSI-SAF SIC CDR v3.1 and C3S CS2SMOS SIT L4 combined v1.1. Observational iceberg tracks, melt observations and published benchmark cases should be incorporated before any further calibration attempt (Stage 10.9 concluded that the current scalar coefficient is not identifiable from the existing set).

### Future numerical/scientific infrastructure

A Python analysis/visualization layer should be developed as a validation and reproducibility tool, not as a replacement for the Fortran production model. A future literature matrix and bibliography remain the authoritative mapping from equations and parameters to sources.

## Rules for future stages

1. No calibration of TEST_11 to hide unexplained physical anomalies.
2. No production-physics changes without an explicit equation and source.
3. Independent analytical tests must not derive both sides from the same production diagnostic.
4. Regression tests and scientific validation must be reported separately.
5. Preserve the current legacy interface unless an interface change is explicitly justified.
6. Keep EOS-80/TEOS-10, advanced turbulence, iceberg orientation and Python validation as roadmap items until their own scientific scope is defined.

## Documentation references

- `docs/model/model_description.md` — narrative model description.
- `docs/model/model_equation_ledger.md` — mathematical specification.
- `docs/model/model_physics_status.md` — maturity/status of physical blocks.
- `docs/references/references.bib` — machine-independent bibliography.
- `docs/references/literature_matrix.md` — source-to-model mapping.
