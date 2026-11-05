# Current Model Documentation

This directory describes **how the model works now**: physical formulations,
equations, units, switches, and numerical schemes. It contains no stage plans
or historical reports. History lives in `docs/wiki/`.

## Authoritative sources (one fact — one source)

| Document                        | What type of information it covers                                                                             |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `model_description.md`          | integral narrative description: formulation, components, data, processes, numerical implementation             |
| `model_physics_status.md`       | status of every physics block: implemented/experimental/limitations; what is on by default, what is selectable |
| `model_equation_ledger.md`      | mathematical specification: equations, variables, units, sign conventions, coefficients, EOS, code links       |
| `numerical_scheme_inventory.md` | inventory of the numerical schemes currently implemented |

## Current development status

- **Stage 11 — FROZEN** research artifact (D-51, tag `stage11-final-frozen`;
  see `../wiki/stages/stage11/STAGE11_FREEZE.md`). The prognostic ocean is **not** a
  production-validated ocean (N²/tides/90-day gates unresolved).
- **Stage 12 — active**, offline/prescribed reanalysis forcing for a voxel
  iceberg (D-51). Stage 12.8's Barents matrix is the latest completed validation
  stage; 12.9a daily-forcing acquisition is in progress and 12.9b thesis writing
  is GO with fallback labeling. Do not infer quantitative daily-forcing
  validation from the fallback runs. See
  `../references/reanalysis_data_plan.md` and
  `../validation/INDEX.md`.

## Related directories

- Active Stage 12 validation reports: `../validation/INDEX.md`
- Historical stage reports: `../wiki/INDEX.md`
- Key decisions: `../DECISIONS.md`
- Current known issues: `../../KNOWN_ISSUES.md`

## Maintenance rules

- When physics/code changes, update `model_physics_status.md` (status,
  switches, limitations) and `model_equation_ledger.md` (equations); update
  `model_description.md` for substantial changes.
- The current state is determined by code and tests, not by old reports.
- If a later stage overturns a conclusion of an old report, the old report
  stays unchanged; the correction goes here and in `../DECISIONS.md`.
