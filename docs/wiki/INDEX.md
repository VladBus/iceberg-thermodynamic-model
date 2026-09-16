# Wiki Index — Historical Materials by Stage

Statuses: **ARCHIVED** (stage materials completed and not edited).

General rules: reports are not rewritten retroactively; the current model
state is in `docs/model/`; decisions — in `docs/DECISIONS.md`; active Stage 10
reports — in `docs/validation/INDEX.md`.

## Stages

| Stage | Directory         | Files      | Content                                                                                                                                                                                |
| ----- | ----------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3     | `stages/stage03/` | 5          | 3D-momentum restoration (Stage 3.3), baroclinic–barotropic coupling (3.4), real model grid (3.5)                                                                                       |
| 4     | `stages/stage04/` | 5          | ERA5 on the TEST grid (4.1), January 2020 (4.2), convective-cycle root cause (4.3), EOS float32 precision (4.3b), precision study (4.4)                                                |
| 5     | `stages/stage05/` | 7          | Heat-input audit (5.1), HEAT enablement (5.2), monthly validation (5.3), snowfall (5.4), multi-month integration (5.5), Q1/units audit (5.5b)                                          |
| 6     | `stages/stage06/` | 12         | Real-grid recovery (6.1), Barents domain (6.2), data cleanup (6.2–6.3), calendar semantics (6.3b), units (6.4), ERA5 data (6.5–6.7)                                                    |
| 7     | `stages/stage07/` | 18         | Snow/ice and dynamics stability (7.1–7.4), real grid and ice initialization (7.5–7.6C), ocean forensics and stabilization (7.7–7.7C), spin-up and geostrophic initialization (7.8–7.9) |
| 8     | `stages/stage08/` | 8          | EN4 preprocessing (8.0), energy instability (8.1), thermal-wind correction (8.2), spin-up (8.3), operator splitting (8.4–8.6), legacy iceberg module reconstruction (8.7)              |
| 9     | `stages/stage09/` | 12 + plots | Lagrangian iceberg model: reconstruction (9.1–9.2), verification and calibration (9.3), core and forcing-pipeline corrections (9.4A–9.4C.2); diagnostic plots `plots_stage9.4b/`       |
| 10    | `stages/stage10/` | 3          | Early Stage 10 reports completed before active documentation moved to `docs/validation/`: 10.4.2, 10.4.2.1, 10.5                                                                       |

## Topics

| File                             | Topic                              |
| -------------------------------- | ---------------------------------- |
| `topics/ERA5_download.md`        | ERA5 download and conversion       |
| `topics/Fortran_dependencies.md` | Fortran dependencies (fpm, netcdf) |
| `topics/Python_environment.md`   | Conda environment, tools, LSP      |

## Live TODO

- `ERA5_INTEGRATION_TODO.md` — local ERA5 integration journal (not in Git).

## Links to current documentation

- Current physics status: `../model/model_physics_status.md`
- Equations and conventions: `../model/model_equation_ledger.md`
- Active validation: `../validation/INDEX.md`
- Decisions: `../DECISIONS.md`
- Project plan: `../PROJECT_ROADMAP.md`

## Commits

Links to specific commits are present inside individual reports (fields
`Git Baseline`, `Files changed`). The overall stage history is in
`CHANGELOG.md` (repository root).

## Historical reference notes

See `docs/wiki/README.md` — some archived reports reference files that are no
longer present (`promt.md`, `experiment_design.md`); these references are
preserved as part of the historical record.
