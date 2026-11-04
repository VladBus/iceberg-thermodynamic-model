# Documentation Map

This directory follows a short lifecycle: **working validation → completed
stage archive → long-term archive**. Start here, then use the directory index
closest to the document you need.

## Current sources of truth

| Need | Authoritative document |
| --- | --- |
| Current Stage 12.9 work and pause status | `validation/INDEX.md` |
| Current physics, switches, and limitations | `model/model_physics_status.md` |
| Equations, units, and sign conventions | `model/model_equation_ledger.md` |
| Model narrative | `model/model_description.md` |
| Current decisions | `DECISIONS.md` |
| Current issues and technical constraints | `../KNOWN_ISSUES.md` |
| Data products and literature provenance | `references/data_sources.md` and `references/README.md` |
| Reanalysis product/data contract | `references/reanalysis_data_plan.md` |
| Production vs legacy I/O policy | `LEGACY_IO_POLICY.md` |

The Stage 11 research artifact is frozen. Its boundary and limitations are in
`wiki/stages/stage11/STAGE11_FREEZE.md`; it is not a production-validated ocean.

## Documentation areas

| Directory | Role | Entry point |
| --- | --- | --- |
| `model/` | Current physical and mathematical model description only | `model/README.md` |
| `references/` | Literature, data products, provenance, and formulation premises | `references/README.md` |
| `validation/` | Temporary work for the active, unfinished validation stage only | `validation/INDEX.md` |
| `wiki/stages/stageXX/` | Completed stage/commit reports and their curated evidence | `wiki/INDEX.md` and each stage's `README.md` |
| `wiki/topics/` | Cross-stage historical reference notes | `wiki/README.md` |
| `archive/` | Superseded plans and records with no active operational role | `archive/README.md` |

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
