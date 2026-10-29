# Current Model Documentation

This directory describes **how the model works now**. The documents here are
living: they are updated whenever the model changes and are not a historical
archive. History lives in `docs/wiki/`.

## Authoritative sources (one fact — one source)

| Document                        | What type of information it covers                                                                             |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `model_description.md`          | integral narrative description: formulation, components, data, processes, numerical implementation             |
| `model_physics_status.md`       | status of every physics block: implemented/experimental/limitations; what is on by default, what is selectable |
| `model_equation_ledger.md`      | mathematical specification: equations, variables, units, sign conventions, coefficients, EOS, code links       |
| `numerical_scheme_inventory.md` | authoritative (Stage 11.3C forensic) inventory of the actual numerical schemes                                |
| `stage10_modernization_plan.md` | Stage 10 modernization plan and journal (**historical** — Stage 10 complete)                                   |

## Current development status

- **Stage 11 — FROZEN** research artifact (D-51, tag `stage11-final-frozen`;
  see `../STAGE11_FREEZE.md`). The prognostic ocean is **not** a
  production-validated ocean (N²/tides/90-day gates unresolved).
- **Stage 12 — active**, offline/prescribed **GLORYS12 + ERA5** forcing for a
  voxel iceberg (D-51); see `../STAGE12_PREPARATION.md` and
  `../REANALYSIS_DATA_PLAN.md`. No Stage 12 Fortran reader written yet
  (Stage 12.1 reconnaissance complete).

## Related directories

- Active Stage 12 validation reports: `../validation/INDEX.md`
- Historical stage reports 3–11: `../wiki/INDEX.md`
- Key decisions: `../DECISIONS.md`
- Current known issues: `../../KNOWN_ISSUES.md`

## Maintenance rules

- When physics/code changes, update `model_physics_status.md` (status,
  switches, limitations) and `model_equation_ledger.md` (equations); update
  `model_description.md` for substantial changes.
- The current state is determined by code and tests, not by old reports.
- If a later stage overturns a conclusion of an old report, the old report
  stays unchanged; the correction goes here and in `../DECISIONS.md`.
