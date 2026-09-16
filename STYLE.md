# STYLE.md — Code and Documentation Conventions

Conventions matching the actual state of the repository. Tools: `fprettify`
and `fortls` (Fortran), ruff-like care (Python), standard Markdown.

## Language Policy

- Root-level operational documentation is written in English.
- Current model specifications and navigation indexes are written in English.
- Historical scientific reports retain their original language.
- Historical reports must not be translated or rewritten solely for language
  consistency.
- New cross-project documentation should use English.
- New comments about physical assumptions, numerical limitations, and
  domain-specific reasoning should preferably use Russian when consistent
  with the existing source-code convention.
- Technical comments, code identifiers, procedure names, test names, and
  filenames use English.
- Existing source-code comments must not be mechanically translated.
- Do not mix language-policy changes with source-code changes.

## Fortran

- Standard: Fortran 2008/2018 (modules, `intent`, `optional`).
- Formatting: 4-space indentation; fprettify-compatible style (line length within gfortran CI requirements; no truncation beyond necessity).
- Naming: `snake_case` for variables and procedures; `UPPER_SNAKE` for constants (e.g., `C_BASAL`, `LATENT_HEAT`, `THREE_EQ_KT`); `snake_case` for derived types (e.g., `iceberg_state`).
- Comments: explain physical meaning and units; Russian comments are permitted where consistent with the existing code; do not leave "dead" commented-out code without justification.
- Modules: public entities via `public` lists; `use` only with `only:`.
- Real comparisons: epsilon (`abs(x - y) < 1e-8`), never `==`; land-mask `8888.0` checks via epsilon.
- Units: internal model units are CGS for hydrodynamics and SI for thermodynamics (see `AGENTS.md` §Unit Systems); conversion happens only at the NetCDF output boundary.
- Do not suppress warnings; the strict build (`-Wall -Wextra -fcheck=all -ffpe-trap`) MUST be clean.

## Python

- Python 3 (conda environment `iceberg-thermodynamic-model`).
- Naming: `snake_case`; constants — `UPPER_SNAKE`.
- Docstrings: module docstrings explain purpose and conventions (see `python/validation/three_equation.py`, `low_flow.py`).
- Type annotations where appropriate; no `as any`-style suppression or error suppression without explicit justification.
- Tests in `python/tests/` use bootstrap imports (`sys.path.insert(0, ...)` pointing at `python/validation/`); LSP "could not be resolved" errors for such imports are a known false positive — do not "fix" them.
- Tests MUST print `TOTAL CHECKS: N ERRORS: 0`.
- Environment: conda environment outside the repository; do not create venv/.venv/env inside the repo.

## Markdown

- Headings: `#` for the document, `##` for sections, `###` for subsections.
- Tables: pipe tables with aligned columns; every data row MUST have the same number of columns as the header; escaped pipes inside code spans are allowed.
- Code/formulas: inline formulas in backticks or fenced blocks; equations in `docs/model/model_equation_ledger.md` — monospace blocks with units stated.
- Links: relative paths inside the repository; for reports — full relative path from the root (`docs/validation/...`).
- Language: living navigation and model documents in English; reports may remain in their original language; status keywords are uniform (ACTIVE/COMPLETED/DRAFT/ARCHIVED).
- Do not create empty documents just to match a tree; do not split integral scientific reports.

## Report naming

- Stage reports: `docs/validation/stage<NN>[_<substage>]_<topic>.md` (active) and `docs/wiki/stages/stage<NN>/Stage<NN>...md` (archived).
- Design notes: `stage<NN>_<topic>_design_note.md`.
- Indexes: `docs/validation/INDEX.md`, `docs/wiki/INDEX.md`, `README.md` (directories).

## Report conventions

- Every report: stage title, status/classification, date, Git baseline (when known), sections "Physics/Validation/Files changed/Known limitations".
- State the A/B/C classification (see `docs/model/model_physics_status.md`).
- Source references: file and, where useful, lines/symbols.
- For every new physical block: literature basis (link to `docs/references/references.bib`), equations, parameter provenance, limitations.

## Conventions strength

- **MUST / MUST NOT** — mandatory rules (process, safety, compatibility); violations block completion.
- **SHOULD / MAY** — recommendations and options; deviations should be justified.
- Rules in this document are MUST-level unless explicitly marked SHOULD/MAY.
