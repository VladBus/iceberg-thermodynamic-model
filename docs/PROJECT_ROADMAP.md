# Project Roadmap

**Updated:** 2026-09-10
**Current scientific stage:** Stage 10.7 — Independent Basal Melt Validation Complete
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

## Immediate next step

### Stage 10.8 — observational validation / calibration and next closure

Stage 10.7 completed the independent analytical-literature audit of basal melt (`docs/validation/stage10.7_basal_melt_validation.md`). The next target should be selected from a scientifically defined problem, not from an implementation gap.

Priority order:

1. Observational validation of basal/lateral melt against public iceberg catalogues, mooring/CTD data and laboratory benchmarks (hard mortality/melt metrics), plus the minimal Python validation layer (tolerance 1e-3).
2. Scientific assessment and, if justified, implementation of a three-equation ice-ocean interface formulation based on Holland & Jenkins (1999) and Jenkins et al. (2010), with independent confirmation of the Γ_T/Γ_S Stanton convention (open risk from Stage 10.7).
3. Iceberg-specific ocean heat-transfer improvements, including natural convection and geometry/orientation effects.
4. Atmospheric stability corrections if external validation demonstrates material bias.

## Longer-term physics

The following are explicit roadmap items and are **not** part of Stage 10.7:

- full seawater thermodynamics / EOS-80 density pathway;
- TEOS-10 thermodynamic framework;
- improved iceberg orientation and geometry;
- advanced ocean-side turbulence and plume physics;
- observationally constrained melt parameterization;
- independent multi-case validation of complete trajectories.

## Scientific infrastructure

A future Python analysis/visualization layer should support reproducible diagnostics, maps, time series, uncertainty/sensitivity analysis and comparison with observations. It should remain a validation/research layer and should not silently duplicate production physics.

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