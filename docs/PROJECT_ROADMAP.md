# Project Roadmap

**Updated:** 2026-09-11
**Current scientific stage:** Stage 10.11 — Natural Convection Basal Melt / Low-Flow Closure
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
| 10.11 | Natural convection basal melt: double-diffusive Ra (Fujii et al. 1973) + Churchill 1977 mixing; L_char = iceberg length L; Ra cap 1e10; gamma_T_nat, gamma_S_nat added to forced via Churchill n=3 mixing; U=0 -> m=1.6e-8 m/s (0.001 m/day); U=0.1 -> natural adds 0.1%; U=1 -> forced dominates 99.9%; Fortran 15 checks, Python 70 checks, cross-language contract | Complete; classification C; production updated; all tests PASS |

## Immediate next step

### Stage 10.11 — natural convection basal melt / low-flow closure (DONE)

Stage 10.11 implemented a physically-motivated natural-convection closure for the three-equation ice-ocean interface, addressing the largest structural gap identified in Stage 10.8.2 (zero melt at zero flow).

- **Physics**: Natural convection from a horizontal ice base (facing downward) driven by combined thermal and haline buoyancy. Double-diffusive Rayleigh number:
  `Ra_eff = g * L^3 / (nu * alpha) * [beta_T * (T_w - T_B) + beta_S * (S_w - S_B) * Le]`
  with `beta_T = 3.0e-5 1/K`, `beta_S = 7.8e-4 1/PSU`, `Le = 100`.
  Characteristic length = iceberg length L (horizontal scale of convection cells; Gayen et al. 2016 LES).
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

- **Effect**: At `U_rel = 0`, finite melt rate `~1.6e-8 m/s` (0.001 m/day) for typical Arctic conditions (`T_w=2°C`, `S_w=34.5 PSU`, `L=100m`, `D=50m`). At `U_rel = 0.1 m/s`, natural convection adds ~0.1% to forced convection. At `U_rel = 1 m/s`, forced convection dominates (>99.9%).

- **Validation**: Fortran test `iceberg_test_10p11_natural_convection` (15 checks) + Python `test_three_equation_natural.py` (70 checks) including zero-flow, low-flow continuity, mixed-convection regime, Ra/Nu scaling, salt/heat balance identities, and cross-language contract (`m = 1.638e-8 m/s` at `U_rel=0`, `T_w=2°C`, `S_w=34.5 PSU`, `L=100m`, `D=50m`). Strict `-Wall -Wextra -fcheck=all` build clean.

- **Report**: `docs/validation/stage10.11_natural_convection.md`.

Priority for the next stage (after 10.11):

1. **internal thermal evolution of the iceberg** (replaces the constant `T_i`
   conduction term of Eq. II);
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