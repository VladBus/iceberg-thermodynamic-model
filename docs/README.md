# Project Documentation — Map

This page is the entry point to all documentation. From here you can descend
from general to specific: rules → model → validation → history.

## Navigation chain

```
README.md (root)
 └─ docs/README.md                    ← you are here
     ├─ ../RULES.md                   development process
     ├─ ../KNOWN_ISSUES.md            current known issues
     ├─ ../CHANGELOG.md               history of significant changes
     │
     ├─ model/README.md               current model specification
     │   ├─ model_description.md      narrative description
     │   ├─ model_physics_status.md   physics block status
     │   ├─ model_equation_ledger.md  equations and conventions
     │   └─ stage10_modernization_plan.md — Stage 10 modernization plan
     │
     ├─ validation/INDEX.md           active validation (Stage 10)
     │
     ├─ wiki/README.md                historical archive
     │   └─ wiki/INDEX.md             index of stages 3–10
     │
     ├─ DECISIONS.md                  key decisions journal
     ├─ PROJECT_ROADMAP.md            project plan and stage status
     ├─ data_sources.md               external data products: sources, retrieval, units
     └─ references/                   bibliography, literature matrix
```

## Documentation layers

| Layer             | Where                                      | What to look for                                                 |
| ----------------- | ------------------------------------------ | ---------------------------------------------------------------- |
| Working rules     | `AGENTS.md`, `RULES.md`, `STYLE.md` (root) | how to change the project, style, constraints                    |
| Current model     | `docs/model/`                              | how the model works now: physics, equations, status, limitations |
| Active validation | `docs/validation/`                         | current-stage reports (Stage 10), design notes, test results     |
| History           | `docs/wiki/`                               | archive of completed stages 3–10, forensic audits, references    |
| Decisions         | `docs/DECISIONS.md`                        | why the model is structured the way it is                        |
| Navigation        | `docs/README.md`, directory indexes        | how to move from general to specific                             |

## Principles

1. **One fact — one authoritative source.** Current physics status —
   `model/model_physics_status.md`; equations — `model/model_equation_ledger.md`;
   rules — `RULES.md`; decisions — `DECISIONS.md`; known issues —
   `KNOWN_ISSUES.md`. Other documents link, they do not copy.
2. **Living documents are current.** `docs/model/`, `README.md`, `AGENTS.md`,
   `KNOWN_ISSUES.md` are updated whenever the model changes.
3. **History is not rewritten.** `docs/wiki/` is an immutable archive; later
   stages add links and records in `DECISIONS.md`, but do not edit old reports.
