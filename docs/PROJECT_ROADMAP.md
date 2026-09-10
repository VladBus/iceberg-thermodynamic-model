# Project Roadmap

**Updated:** 2026-09-10
**Current scientific stage:** Stage 10.9 — Calibration Assessment of the Basal-Melt Coefficient
**Current status:** C — validation insufficient for robust calibration

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

## Immediate next step

### Stage 10.10 — three-equation ice-ocean interface (and natural-convection floor)

Stage 10.9 (`docs/validation/stage10.9_calibration_assessment.md`) assessed
whether the production heat-transfer coefficient could be calibrated against
the 10.8.2 observational set and concluded **NO scalar coefficient is
identifiable**: the two independent sources require ~8.3x different
coefficients (NJ80 0.286, KW84 1.418), the NJ80 observation scales as dT^1.73
while the closure is dT^1.0 (functional-form, not scale, mismatch), and the
natural-convection branch is structurally zero for any finite coefficient.
The stage also corrected two 10.8.2 claims (basal-plane-dominance and
submarine≈basal are aspect-ratio-dependent, not universal) and Crossref-verified
all seven named literature DOIs. No production coefficient was changed.

Priority for the next stage (refreshed after 10.9):

1. **Three-equation ice-ocean interface** (Holland & Jenkins 1999; Jenkins
   et al. 2010, melt-driven Stanton; buoyancy-informed per FitzMaurice & Stern
   2018), re-scoring the 10.8.2 set as the acceptance criterion; the
   `Γ_T/Γ_S` Stanton convention (open risk from Stage 10.7) must be confirmed
   independently. Recalibration of the current scalar coefficient is explicitly
   NOT recommended — ruled out by 10.9.
2. natural convection at low relative flow (melt plumes) — largest structural
   gap by 10.8.2, confirmed uncalibratable by 10.9;
3. atmospheric stability corrections if external validation demonstrates
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