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
| `stage10_modernization_plan.md` | Stage 10 modernization plan and journal (active work stage)                                                    |

## Related directories

- Active Stage 10 validation reports: `../validation/INDEX.md`
- Historical stage reports 3–10: `../wiki/INDEX.md`
- Key decisions: `../DECISIONS.md`
- Current known issues: `../../KNOWN_ISSUES.md`

## Maintenance rules

- When physics/code changes, update `model_physics_status.md` (status,
  switches, limitations) and `model_equation_ledger.md` (equations); update
  `model_description.md` for substantial changes.
- The current state is determined by code and tests, not by old reports.
- If a later stage overturns a conclusion of an old report, the old report
  stays unchanged; the correction goes here and in `../DECISIONS.md`.
