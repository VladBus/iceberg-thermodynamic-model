# Stage 10 — Physics Modernization Plan

**Updated:** 2026-09-11
**Current stage:** 10.11 (natural-convection basal melt / low-flow closure; production updated)
**Current classification:** C — correction validated; production updated; all tests PASS

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
- Order-of-magnitude agreement with in-repo three-equation estimate (St·u*, St=0.011 commented): factor ≈1.8 at U=0.1 m/s; observed submarine-melt band 0.01–1 m/day reproduced.
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
- **Report**: `docs/validation/stage10.10.1_three_equation_interface.md`.

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

## Next modernization sequence

Priority candidates after 10.11:

1. internal thermal evolution of the iceberg (replacing the constant `T_i`
   conduction term of Eq. II);
2. improved treatment of iceberg-specific ocean heat transfer, including
   re-scoring the 10.8.2 set against the three-equation + natural-convection closure with the
   10.8.2 acceptance criterion;
3. improved atmospheric stability/transfer treatment if validation demonstrates a material need;
5. modern seawater thermodynamics, including a full EOS-80/TEOS-10 pathway,
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
