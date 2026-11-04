# Historical Stage Archive

`docs/wiki/stages/` is the permanent archive for completed stage reports and
their curated evidence. Current work does not belong here until its stage closes.

## Stages

| Stage | Directory | Contents |
| --- | --- | --- |
| 3 | `stages/stage03/` | Momentum restoration, coupling, and real-grid work |
| 4 | `stages/stage04/` | ERA5 integration, EOS precision, and convective-cycle investigations |
| 5 | `stages/stage05/` | Heat input, snowfall, and multi-month validation |
| 6 | `stages/stage06/` | Grid recovery, domain, calendar, units, and ERA5 records |
| 7 | `stages/stage07/` | Snow/ice, real grid, and ocean initialization |
| 8 | `stages/stage08/` | EN4, ocean stability, and legacy iceberg reconstruction |
| 9 | `stages/stage09/` | Lagrangian iceberg model reconstruction and verification |
| 10 | `stages/stage10/` | Iceberg thermodynamics modernization, audits, and observational studies |
| 11 | `stages/stage11/` | Frozen Stage 11 reports, freeze record, evidence, and figures |
| 12 | `stages/stage12/` | Completed Stage 12 reports and evidence through Stage 12.8 |

Every stage folder has a `README.md` with its report index and scope.

## Stage 11 freeze

Stage 11 is a **frozen research artifact**, not a production-validated ocean.
Its N², real-tide, 90-day, and production-scheduler validation gates remain
unresolved. The authoritative record is
`stages/stage11/STAGE11_FREEZE.md`; the consolidated summary is
`stages/stage11/SUMMARY.md`.

## Stage 12 status

Completed reports and evidence through Stage 12.8 are archived in
`stages/stage12/`. Stage 12.9 daily-forcing acquisition was resumed on
2026-11-04 and is in progress; active manifests remain in `docs/validation/`.
Do not start additional downloads unless explicitly requested. Stage 12.8
fallback-forcing results are exploratory lower bounds, not daily-forcing
validation.

## Cross-cutting topics

`topics/` contains stable historical notes for Fortran dependencies and the
Python environment. The old ERA5 download note is archived at
`docs/archive/ERA5_download.md`. Stage reports remain in their stage folders
rather than being duplicated here.

## Current documentation

- Current physics and equations: `docs/model/README.md`.
- Current validation work: `docs/validation/INDEX.md`.
- Data sources and assumptions: `docs/references/README.md`.
- Superseded plans and provenance: `docs/archive/README.md`.
- Full documentation map: `docs/README.md`.
