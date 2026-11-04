# Stage Report Archive

`docs/wiki/` is the permanent archive of completed stage reports, evidence, and
cross-stage historical notes. It is not a working directory. Start at
`INDEX.md`, then open the relevant `stages/stageXX/README.md`.

## Lifecycle

1. Unfinished validation work stays in `docs/validation/`.
2. When a stage is complete, move its final report and curated evidence to
   `docs/wiki/stages/<stage>/` and update that stage's index.
3. Superseded plans, local operational notes, and obsolete non-stage material
   belong in `docs/archive/` if they retain historical value.
4. Model physics, equations, and current formulation status belong in
   `docs/model/`; citations and data assumptions belong in `docs/references/`.

Do not rewrite archived scientific conclusions. Correct a stale conclusion in
current documentation and link to the later decision or report.

## Stage folders

- `stages/stage03/` through `stages/stage10/` contain completed historical work.
- `stages/stage11/` contains all Stage 11 reports and evidence. Stage 11 is
  frozen as a research artifact; it is not a production-validated ocean. Its
  authoritative freeze record is in that folder.
- `stages/stage12/` contains completed reports/evidence through Stage 12.8.
  Stage 12.9 remains unfinished; its acquisition is in progress and its active
  manifests stay in `docs/validation/` until the work closes.

## Cross-stage topics

`topics/` contains stable reference notes for Fortran dependencies and the
Python environment. These are not substitutes for the current data contract in
`docs/references/` or the current work index in `docs/validation/`. The old ERA5
download note was moved to `docs/archive/ERA5_download.md`.

## Related indexes

- All archived stages: `INDEX.md`.
- Current Stage 12.9 workspace: `../validation/INDEX.md`.
- Current model description: `../model/README.md`.
- Current assumptions and data sources: `../references/README.md`.
- Superseded plans and provenance: `../archive/README.md`.
- Full documentation map: `../README.md`.
