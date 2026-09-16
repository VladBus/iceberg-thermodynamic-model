# Wiki — Historical Project Archive

## What this is

`docs/wiki/` is the historical archive of reports, decision records, and
results of specific development stages. It is the **memory of the project**:
documents here are not edited retroactively and are not rewritten to match the
current model state.

## How Wiki differs from other documentation layers

| Directory           | Role                      | What is stored here                                                                               |
| ------------------- | ------------------------- | ------------------------------------------------------------------------------------------------- |
| `docs/model/`       | **Current specification** | how the model works now; equations, physics status, limitations; updated on every model change    |
| `docs/validation/`  | **Active validation**     | reports of the stages currently in progress (currently Stage 10); design notes; test results      |
| `docs/wiki/`        | **Historical archive**    | completed stages, forensic audits, old reports, commit-specific materials, tooling references     |
| `docs/DECISIONS.md` | **Decisions journal**     | short records of "why the model is structured this way", connecting history and the current model |

## Why archived documents are not rewritten

If a later stage overturns or refines a conclusion of an old report:

1. the old report stays unchanged (historical evidence);
2. the current state is recorded in the living documentation (`docs/model/`, `KNOWN_ISSUES.md`);
3. when needed, a record is added to `docs/DECISIONS.md`.

Only obvious technical navigation fixes (broken paths, links) may be corrected
in archived files, provided they do not change the scientific content.

## Historical reference notes

Some archived reports contain references to files that are no longer present
in the repository:

- `promt.md` — the original process-rules file (removed; its content now
  lives in `RULES.md`);
- `experiment_design.md` — referenced by Stage 8.7, never present in the
  repository.

These references are preserved because the reports are immutable historical
records. They should not be interpreted as links to currently available
project documentation. Where a historical link can be repaired without
changing the meaning of the report, this is optional and has not been applied.

## How to search materials

### By stage

Reports are organized by stage directories in `docs/wiki/stages/`:

- `stage03/` — 3D-momentum restoration, convective convergence, real grid
- `stage04/` — ERA5 integration, EOS precision, convective-cycle root cause
- `stage05/` — heat input, snowfall, multi-month integration, units
- `stage06/` — real grid and Barents domain, calendar semantics, ERA5 data
- `stage07/` — snow/ice, dynamics stability, IBCAO real-grid reconstruction, real ice and ocean initialization
- `stage08/` — EN4 ocean initialization, thermodynamic correction, spin-up, legacy iceberg module
- `stage09/` — minimal Lagrangian iceberg model: reconstruction, verification, calibration
- `stage10/` — early Stage 10 reports (10.4.2, 10.4.2.1, 10.5); the remaining Stage 10 reports are active and live in `docs/validation/`

Each stage directory has a `README.md` with an index and summary.

### By topic

`docs/wiki/topics/` — cross-cutting topics not tied to a single stage:

- `topics/ERA5_download.md` — ERA5 download;
- `topics/Fortran_dependencies.md` — Fortran dependencies;
- `topics/Python_environment.md` — conda environment and tools.

### Live TODO

`docs/wiki/ERA5_INTEGRATION_TODO.md` — local working journal (intentionally
not tracked by Git), referencing archived stage reports 4–6.

## How archived reports relate to the current model

- Current equations and physics status: `docs/model/model_equation_ledger.md`,
  `docs/model/model_physics_status.md`.
- Active validation reports: `docs/validation/INDEX.md`.
- Decisions explaining the current architecture: `docs/DECISIONS.md`.
- Known issues: `KNOWN_ISSUES.md` (repository root).

Full navigation: `README.md` → `docs/README.md`.
