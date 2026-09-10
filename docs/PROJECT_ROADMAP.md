# Project Roadmap

**Updated:** 2026-09-10
**Current scientific stage:** Stage 10.10.1 — Mass/Salt Convention Correction in Three-Equation Interface
**Current status:** C — correction validated; production updated; all tests PASS

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

## Immediate next step

### Stage 10.10.1 — mass/salt convention correction in three-equation interface (DONE)

Stage 10.10.1 corrected the salt balance (Eq. III) in the three-equation ice-ocean interface from the equal-density reduction `gamma_S (S_w - S_B) = m S_B` to the physically consistent mass-conserving form `rho_w gamma_S (S_w - S_B) = rho_i m S_B`, which reduces to `S_B = gamma_S S_w / (gamma_S + (rho_i/rho_w) m)` with `rho_i/rho_w = 910/1028 = 0.8852...`. This matches the MOM6 `mom_ice_shelf`, PISM basal-melt, and MITgcm shelfice documented conventions, and Holland & Jenkins (1999) Eq. (4) (brine salt flux `rho_i M wB (S_I - S_B)`). The Stage 10.10 formulation implicitly set `rho_i/rho_w = 1`.

- **Production changes**: `src/iceberg_types.f90` (new constant `RHO_ICE_WATER_RATIO`), `src/iceberg_thermodynamics.f90` (three reduction expressions in `solve_three_equation_interface` + doc block rewrite); `python/validation/three_equation.py` (module docstring, `_s_interface` with optional `rho_ratio` defaulting to the new constant).
- **Effect**: canonical H&J99 anchor m increases from 9.4457e-9 to 1.0438e-8 m/s (+10.5%, amplified by near-zero thermal drive); production end-to-end m increases from 3.998e-6 to 4.067e-6 m/s (+1.7%); warm band 0.351 m/day (inside 0.01-1 m/day).
- **T_i = -10 degC attribution corrected**: model-selected constant internal temperature, NOT from H&J99 (H&J99 solve conduction explicitly). Docs updated.
- **Validation**: Fortran test extended to 25 checks (19+6 new density-reduction identity/limit/monotonicity checks); Python suite extended to 65 checks (46+19 new Stage 10.10.1 checks including salt-flux identity, freshwater-flux identity, limits, monotonicity, cross-language contract). All tests PASS. Strict `-Wall -Wextra -fcheck=all` build clean. `git diff --check` clean.
- **Report**: `docs/validation/stage10.10.1_three_equation_interface.md`.

Stage 10.9 (`docs/validation/stage10.9_calibration_assessment.md`) assessed whether the production heat-transfer coefficient could be calibrated against the 10.8.2 observational set and concluded **NO scalar coefficient is identifiable**: the two independent sources require ~8.3x different coefficients (NJ80 0.286, KW84 1.418), the NJ80 observation scales as dT^1.73 while the closure is dT^1.0 (functional-form, not scale, mismatch), and the natural-convection branch is structurally zero for any finite coefficient. The stage also corrected two 10.8.2 claims (basal-plane-dominance and submarine≈basal are aspect-ratio-dependent, not universal) and Crossref-verified all seven named literature DOIs. No production coefficient was changed.

**Stage 10.10 (Phase 1) resolved the first priority item:** the three-equation ice-ocean interface (Holland & Jenkins 1999; Jenkins et al. 2010 Table 2 velocity-scale `K_T = 1.1e-3`, `K_S = 3.1e-5`) is implemented as a separately selectable basal closure, with the bulk path physics unchanged (statements identical, re-indented into the scheme else-branch), and independently validated in Fortran (19 checks) and Python (46 checks) with a shared cross-language contract (H&J99 anchor `m = 9.4457e-9` m/s; production end-to-end `m = 3.998e-6` m/s). The `Γ_T/Γ_S` Stanton convention risk from Stage 10.7 is documented: the implemented constants are the **U-based** J2010 values, whereas the melt-driven `u*`-based Stanton (St = 0.011) is a different convention and remains an open question for calibration. Re-scoring the 10.8.2 set against the new closure is deferred by design (no calibration in 10.10).

Priority for the next stage (after 10.10.1):

1. **natural convection at low relative flow** (melt plumes) — the largest
   structural gap by 10.8.2, confirmed uncalibratable by 10.9; the new
   three-equation path retains the same `U_rel = 0 -> m = 0` limitation;
2. internal thermal evolution of the iceberg (replaces the constant `T_i`
   conduction term of Eq. II);
3. re-scoring the 10.8.2 observational set against the three-equation closure
   with the 10.8.2 acceptance criterion (after items 1-2);
4. atmospheric stability corrections if external validation demonstrates
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