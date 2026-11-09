# Documentation Map

This directory follows a short lifecycle: **working validation → completed
stage archive → long-term archive**. Start here, then use the directory index
closest to the document you need.

## Read order

```
README.md (project overview)
  └─ docs/README.md                         ← you are here
      ├─ model/README.md                    current physics, equations, status
      ├─ validation/INDEX.md                active, unfinished work only
      ├─ wiki/INDEX.md                      completed stage reports 3–12
      │   └─ wiki/stages/stageXX/README.md  index for one stage
      ├─ references/README.md               literature, data sources, provenance
      ├─ DECISIONS.md                       why a choice was made
      ├─ archive/README.md                  superseded plans and old records
      └─ ../KNOWN_ISSUES.md                 live issue/constraint index
```

## Current sources of truth

| Need | Authoritative document |
| --- | --- |
| Current active work (12.9b thesis; 12.9a acquisition and 12.10–12.13 model work complete) | [`validation/INDEX.md`](validation/INDEX.md) |
| Current physics, switches, and limitations | [`model/model_physics_status.md`](model/model_physics_status.md) |
| Equations, units, and sign conventions | [`model/model_equation_ledger.md`](model/model_equation_ledger.md) |
| Model narrative | [`model/model_description.md`](model/model_description.md) |
| Current decisions | [`DECISIONS.md`](DECISIONS.md) |
| Current issues and technical constraints | [`../KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) |
| Data products and literature provenance | [`references/data_sources.md`](references/data_sources.md) and [`references/README.md`](references/README.md) |
| Reanalysis product/data contract | [`references/reanalysis_data_plan.md`](references/reanalysis_data_plan.md) |
| Production vs legacy I/O policy | [`LEGACY_IO_POLICY.md`](LEGACY_IO_POLICY.md) |

The Stage 11 research artifact is frozen. Its boundary and limitations are in
[`wiki/stages/stage11/STAGE11_FREEZE.md`](wiki/stages/stage11/STAGE11_FREEZE.md);
it is not a production-validated ocean.

## Documentation areas

| Directory | Role | Entry point |
| --- | --- | --- |
| `model/` | Current physical and mathematical model description only | [`model/README.md`](model/README.md) |
| `references/` | Literature, data products, provenance, and formulation premises | [`references/README.md`](references/README.md) |
| `validation/` | Temporary work for the active, unfinished validation stage only | [`validation/INDEX.md`](validation/INDEX.md) |
| `wiki/stages/stageXX/` | Completed stage/commit reports and their curated evidence | [`wiki/INDEX.md`](wiki/INDEX.md) and each stage's `README.md` |
| `wiki/topics/` | Cross-stage historical reference notes | [`wiki/README.md`](wiki/README.md) |
| `archive/` | Superseded plans and records with no active operational role | [`archive/README.md`](archive/README.md) |

## Where documents go

- **Model physics and mathematics:** `model/`. Keep stage plans and reports out
  of this directory.
- **A stage is still active:** put only temporary working notes and manifests
  in `validation/`. Do not leave completed reports there.
- **A stage is complete:** move its report and curated evidence into
  `wiki/stages/<stage>/`, update that stage's `README.md` and `wiki/INDEX.md`,
  and remove only verified-regenerable temporary files.
- **A plan, audit, or instruction is obsolete:** move it to `archive/` if it
  still has historical value. Delete only confirmed duplicates or files with
  no unique information, provenance, or references.
- **Literature and data-source assumptions:** place them in `references/`, not
  in model descriptions or validation dumps.

## Documentation checks

Run these before committing a documentation change:

| Check | What to verify |
| --- | --- |
| Table shape | Header, separator, and every body row have the same number of columns. Escape `\|` inside a cell; never leave a blank line inside a table. |
| Links | Every relative link and referenced path resolves from the file that contains it. Update indexes in the same change as a move or rename. |
| Single source | The fact is not duplicated from an authoritative report; link to it instead. |
| Status | Update `KNOWN_ISSUES.md` when an issue opens, changes status, or closes; add a `DECISIONS.md` record when the reason for a choice changes. |
| History | Do not rewrite archived scientific conclusions; record corrections in the living source and link the later decision. |
| Whitespace | `git diff --check` is clean. |

Run `python scripts/check_docs_links.py` for current guidance, model,
references, validation, and Stage 12 reports. Use `--all` to include historical
report bodies and `--anchors` to check heading anchors. Local-only/gitignored
artifacts are reported separately.

## Repository-level guidance

| File | Purpose |
| --- | --- |
| `../AGENTS.md` | Short agent entry point, constraints, and resource limits |
| `../RULES.md` | Development, documentation, verification, commit, and archive rules |
| `../STYLE.md` | Code and Markdown conventions |
| `../README.md` | User-facing project overview |
| `../KNOWN_ISSUES.md` | Current known issues only |
| `../CHANGELOG.md` | Significant implementation and documentation history |

## Principles

1. One current fact has one authoritative source. Other documents link to it.
2. Keep current status concise; stage reports hold the details and evidence.
3. Preserve scientific history and provenance. Do not rewrite old conclusions;
   record corrections in current model documentation and `DECISIONS.md`.
4. Update incoming references and indexes whenever a document moves or is
   renamed. Do not use the archive or wiki as a substitute for current status.
5. Work within the WSL2 memory budget: avoid parallel downloads, builds,
   analyses, and broad repository scans. See `../RULES.md`.
