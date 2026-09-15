# Project Roadmap

**Updated:** 2026-09-15
**Current scientific stage:** Stage 10.12 — Prognostic Internal Thermal Evolution
**Current status:** C — two-node lumped interior implemented and independently validated (Fortran 17 + Python 35 checks); production updated

## Completed foundation

- Legacy iceberg dynamics and thermodynamics integrated into the modern repository structure.
- Real model grid reconstructed from IBCAO V5.2: 133×105 nodes, 132×104 active cells, DX=DY=13.89 km.
- Real sea-ice initialization implemented for 2020-01-01 from OSI-SAF SIC CDR v3.1 and C3S CS2SMOS SIT L4 combined v1.1.
- ERA5 atmospheric forcing and EN4 ocean forcing integrated into the real-grid workflow.
- Stage 9 moving-iceberg and forcing audits completed.
- Stage 10.1–10.6 modernization blocks implemented and audited.
- CI aligned with the current 50-target test suite and current gfortran line-length requirements.
- Literature foundation established: 137-record repository bibliography, literature matrix, and scientific model description.

## Stage 10 status

| Stage | Subject | Status |
|---|---|---|
| 10.1.1 | Solar geometry | Complete |
| 10.1.2 | Atmospheric shortwave attenuation/cloud | Complete with documented limitations |
| 10.2 | Prognostic surface temperature | Complete with documented limitations |
| 10.3 | Modern sensible/latent atmospheric fluxes | Complete with documented limitations |
| 10.4 | Phase-change energy partition | Complete with documented limitations |
| 10.4.2.1 | Independent Q_surface output validation | Complete with methodological limitation |
| 10.5 | EOS-80 freezing point | Complete; classification B |
| 10.6 | Relative ocean flow and heat transfer | Complete |
| 10.6.1 | Independent heat-transfer audit + documentation correction | Complete; classification B |
| 10.7 | Independent basal-melt validation (analytical + literature) | Complete; classification B; 17 checks |
| 10.8.1 | Independent Python validation layer (`python/validation/`, 44 checks) | Complete; classification B |
| 10.8.2 | Observational validation of basal melt vs published observations (19-record dataset, 229 Python checks) | Complete; classification C (validation layer); production unchanged |
| 10.9 | Calibration assessment of the basal-melt coefficient (212 Python checks; no scalar identifiable from the 2-source set) | Complete; classification C; production unchanged |
| 10.10 | Three-equation ice-ocean interface (Holland & Jenkins 1999; Jenkins et al. 2010 Table 2), separately selectable; independently validated (19 Fortran + 46 Python checks, cross-language contract) | Complete; classification C; production physics added on selectable path, bulk path physics unchanged |
| 10.10.1 | Mass/salt convention correction: Eq. III from `gamma_S(S_w-S_B)=m S_B` to `rho_w gamma_S(S_w-S_B)=rho_i m S_B` with `rho_i/rho_w=910/1028`; MOM6/PISM/MITgcm/H&J99 Eq.4 convention; canonical anchor m 9.45e-9 -> 1.04e-8 (+10.5%), end-to-end m 3.998e-6 -> 4.067e-6 (+1.7%); T_i=-10 attribution corrected (model-selected, not H&J99); Fortran 25 checks, Python 65 checks, strict build clean | Complete; classification C; production updated; all tests PASS |
| 10.11 | Natural convection basal melt: double-diffusive Ra + Churchill 1977 mixing; L_char = iceberg length L; Ra cap 1e10; gamma_T_nat, gamma_S_nat added to forced via Churchill n=3 mixing; U=0 -> m=1.6e-8 m/s (0.001 m/day); U=0.1 -> natural adds only 2.2e-6% (NOT 0.1% as originally claimed — corrected in Stage 10.11.2); U=1 -> forced dominates 99.9999999%; Fortran 23 checks (delivered in Stage 10.11.2 audit; original claim of 15 checks was never delivered in 6a0014e), Python 70 checks, cross-language contract | Complete; classification C (10.11) / B (10.11.2 audit); production updated; all tests PASS |
| 10.11.3 | Deep scientific audit + sensitivity of the natural-convection closure: independent Python replica (tables A-J); cap always active (uncapped Ra=5.7e19) -> Nu pinned 323.17, haline/Le and beta_T/beta_S inert, laminar branch latent; haline sign opposite to physical (stabilizing) role; operative `0.15*Ra^(1/3)` attributed to Lloyd & Moran 1974 (not Fujii 1973); zero-flow m=1.4e-3 m/day is 7-700x below observed quiescent band (does NOT close the 10.8.2 gap); real mechanism double-diffusive (Martin & Kauffman 1977; Keitzl et al. 2016; Middleton et al. 2021); documentation corrected; production source diff ZERO | Complete; classification B; production UNCHANGED; all tests PASS |
| 10.12 | Prognostic internal thermal evolution: two-node lumped interior, prognostic `state%T_ice` replaces constant `T_i=-10` in Eq. II; `q_cond = 2*K_ICE*(T_s-T_i)/H` (K_ICE=2.2), `q_bot = m*rho_i*CP_ICE_3EQ*max(T_B-T_i,0)`, explicit Euler, clamp [-100,0]°C, switch `thermal_evolution_enabled` — fully gates the stage in the step (OFF = bit-identical legacy, verified by F.1–F.4); energy-conserving lagged skin coupling (`q_internal_exchange`); Fortran 21 + Python 35 checks, cross-language contract C_int(50 m); unused stdlib dependency removed from fpm.toml | Complete; classification C; production updated; all tests PASS |

## Immediate next step

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
- **Validation**: Fortran `iceberg_test_10p12_thermal_evolution` (17/17 PASS;
  the C.5 lower-clamp check uses an amplified diagnostic flux q = -30000 W/m²,
  documented in-test) + Python float64 replica `python/validation/internal_thermal.py`
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
   floor that does not reach the observed quiescent band;
2. re-scoring the 10.8.2 observational set against the three-equation + natural-convection closure
   with the 10.8.2 acceptance criterion;
3. improved atmospheric stability/transfer treatment if external validation demonstrates
   material bias.

## Longer-term physics

The following are explicit roadmap items and are **not** part of the 10.8/10.9 validation and calibration-assessment stages:

- full seawater thermodynamics / EOS-80 density pathway;
- TEOS-10 thermodynamic framework;
- improved iceberg orientation and geometry;
- advanced ocean-side turbulence and plume physics;
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