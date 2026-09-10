# Project Roadmap

**Updated:** 2026-09-10
**Current scientific stage:** Stage 10.8.2 — Observational Validation of the Basal-Melt Closure
**Current status:** B — PASS WITH LIMITATIONS

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

## Immediate next step

### Stage 10.9 — calibration (production coefficients) and/or three-equation closure

Stage 10.8.2 (`docs/validation/stage10.8.2_observational_validation.md`)
completed the observational validation pass: the production closure reproduces
the one forcing-anchored field rate (KW84, 0.70x within the reported range),
overestimates the NJ80 synthesis by factor 2.1-5.8 at reference parameters, and
cannot represent quiescent (laboratory) melt (5.7-7.3 orders gap; no
natural-convection branch). These are documented findings; no coefficient was
changed.

Priority for the next stage (unchanged ordering, refreshed after 10.8.2):

1. **Calibration of the turbulent heat-transfer coefficient** against the
   10.8.2 observational set (a production-coefficient change, therefore a
   separate stage requiring sign-off; the calibration would target the observed
   factor 0.7-5.8 spread), OR
2. assessment and implementation of a three-equation ice-ocean interface
   formulation based on Holland & Jenkins (1999) and Jenkins et al. (2010),
   with independent confirmation of the Γ_T/Γ_S Stanton convention (open risk
   from Stage 10.7);
3. natural convection at low relative flow (melt plumes) — quantified as the
   largest structural gap by 10.8.2;
4. atmospheric stability corrections if external validation demonstrates
   material bias.

## Longer-term physics

The following are explicit roadmap items and are **not** part of Stage 10.8.1:

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