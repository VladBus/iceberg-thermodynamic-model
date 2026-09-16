# RULES.md — Development Process Rules

The main document on **how** the project is changed (what to do — in
`AGENTS.md`; style — in `STYLE.md`; current constraints — in `KNOWN_ISSUES.md`).

## General change workflow

1. **Before starting work, ALWAYS:**
   - read `AGENTS.md`, `docs/README.md`, current `git status`, recent commits, and all sources relevant to the current stage;
   - use the existing TODO/roadmap as the main project plan — do not create a new plan from scratch; sync the TODO with the actual repository state (the TODO is a living project journal);
   - use the available tools: repository-wide search, historical sources, version comparison, `git diff`, diagnostics, test runs, static analysis, documentation.
2. **Before changing physics:** find the historical algorithm, match it with the current arrays, check units and dimensions, determine the place in the time loop, and check the impact on existing modules.
3. **Do not change physical equations merely to pass tests.**

## Physics-change rules

- Every physical change MUST have: a literature basis, explicit equations, parameter provenance, independent tests, and a documented limitation statement.
- New physics enters behind a runtime feature switch; with the switch OFF the behavior MUST be bit-identical to the legacy path (verified by legacy-invariance tests).
- Separate production physics from experimental parameterizations; never present an experimental scheme as production.
- Do not "fix" known constraints without scientific justification: the convective threshold `0.9e-7` and float32 EOS, FCT anti-diffusion (`CDY*0`), Thomas-algorithm vertical viscosity, the `hht<0.01` guard — see `KNOWN_ISSUES.md`.
- Do not modify canonical ocean/sea-ice physics (Block 200/210/280, barotropic solver, EOS, grid, ERA5, bathymetry, thermodynamics) — see `AGENTS.md` (Constraints).

## Backward-compatibility requirements

- Preserve legacy interfaces unless an interface change is explicitly justified.
- Every switch: default OFF or an explicitly documented value; OFF = legacy (bit-identical).
- After any stage the full test battery MUST pass (exit 0).

## Fortran-change rules

- Always build with `-I/usr/include` (netcdf.mod lives in /usr/include, not in the fpm tree): `fpm build/test/run --flag "-I/usr/include"`.
- fpm 0.13.0-alpha: run `rm -rf build` before `fpm test` (clean rebuild).
- Strict build: `-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow` — 0 warnings.
- Never suppress type errors (in Python: no `as any`/`# type: ignore` equivalents without justification — see STYLE).
- Compare reals only via epsilon (`abs(x-y) < 1e-8`), never `==`.

## Python reference-model rules

- Python models in `python/validation/` are independent reference implementations for cross-language checks; do not silently tune them to match Fortran — document discrepancies.
- Tests: `python python/tests/test_<name>.py` MUST print `TOTAL CHECKS: N ERRORS: 0`.

## Test requirements

- Every physical block: independent analytical tests (not deriving both sides from the same production diagnostic), regression tests, and where applicable a cross-language contract (Fortran/Python).
- Report tests and scientific validation separately.
- Do not delete failing tests to pass; fix the root cause.
- Do not claim a stage is complete unless the materials confirm it.

## Validation requirements

- Internal tests establish implementation consistency and conservation identities; they do not establish observational validity.
- Each future physical modernization MUST provide: a literature basis, equation/parameter provenance, independent analytical tests, regression tests, and an external validation target where applicable.
- Observational validation MUST use exact product metadata (ERA5, EN4, IBCAO V5.2, OSI-SAF SIC CDR v3.1, C3S CS2SMOS SIT L4).

## Documentation requirements

- One fact — one authoritative source (see `docs/README.md`): physics status → `docs/model/model_physics_status.md`; equations → `docs/model/model_equation_ledger.md`; decisions → `docs/DECISIONS.md`; constraints → `KNOWN_ISSUES.md`.
- Living documents (`docs/model/`, `README.md`, `AGENTS.md`, `KNOWN_ISSUES.md`) are updated when the model changes.
- History is not rewritten: archived reports in `docs/wiki/` remain unchanged; when a later stage overturns a conclusion, add a link in the current document and a record in `docs/DECISIONS.md`.
- Important notes that might be lost due to context limits MUST be written to `docs/wiki/` or an appropriately named .md file.

## Stage-report format

Stage completion report template:

```
DONE
CHANGED
PHYSICS
TESTS
DIAGNOSTICS
ASSUMPTIONS
RISKS
TODO UPDATED
GIT
NEXT
```

Stage reports: in `docs/validation/` for active stages, in
`docs/wiki/stages/stageXX/` for completed stages.

## Conflict resolution

Conflicts (code vs history vs documentation vs previous decisions) are never
resolved silently: record the conflict, the source of each variant, and the
decision made (in the stage report and, when needed, in `docs/DECISIONS.md`).

## Commit rules

- Check `.gitignore` before committing (it blocks `opencode.jsonc`, `.opencode/`, `data/`, `*.nc`, `*.vtk`, `*.dat`, `*.bak`; exception — `data/validation/observations/`; `docs/wiki/ERA5_INTEGRATION_TODO.md` is intentionally outside Git).
- Never commit secrets: `~/.cdsapirc` (CDS credentials) — never in Git.
- Do not delete root-level symlinks `KOORD.DAT`, `hhh.bar` (required by the model, gitignored, point to `data/input/generated/real_grid/`).
- One commit per stage; check `git diff` and `git diff --check` before committing.
- Push only if it matches the current workflow.
- Do not commit/push unless the user explicitly requests it.

## Stage-completion criteria

1. All planned items done; TODO synced.
2. Full test battery exit 0; strict build clean.
3. Diagnostics clean on changed files.
4. Stage report created; living documentation updated.
5. `git diff --check` clean; separate commit ready (on request).

## Historical-document rules

- Do not delete historical materials from Git.
- Do not merge reports if the link to a stage/commit would be lost.
- Do not rewrite scientific conclusions in archived reports (only obvious navigational fixes are allowed).
- When archiving: check links, choose the target directory, update navigation and links, preserve the content.
