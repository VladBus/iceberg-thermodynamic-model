# Stage 11 — Frozen Research Archive

Stage 11 is **FROZEN** as a research artifact (D-51, tag
`stage11-final-frozen`). It is not a production-validated prognostic ocean.
Stage 12 uses offline/prescribed reanalysis forcing instead. For current project
status, use `docs/validation/INDEX.md`; this directory is historical and should
not be treated as a working area.

> **Path note:** individual reports preserve their original wording, including
> paths used before this archive was consolidated. Use this README and
> `docs/wiki/INDEX.md` for the current locations; do not infer current workflow
> from paths written inside historical reports.

## Authoritative and summary documents

- `STAGE11_FREEZE.md` — authoritative freeze boundary, measured outcome, and
  unresolved physical gates.
- `SUMMARY.md` — consolidated historical summary of the former root-level
  `STAGE11_SUMMARY.md` and `STAGE11_FINAL_SUMMARY.md`.
- `STAGE11_CLOSURE_CHECKLIST.md` and `STAGE11_CLOSURE_DECLARATION.md` — the
  administrative closure record.
- `STAGE11_STATE_SNAPSHOT.md` — dated, superseded snapshot of the former living
  state document; do not use for current project status.
- `MIGRATION_GUIDE_EOS80_DEFAULT.md`, `OBC_N4_N24_AUDIT.md`,
  `TIDES_IMPLEMENTATION_PLAN.md`, and `DATA_RUNS_CLEANUP_REPORT.md` — stage
  records and technical notes associated with the Stage 11 closure.
- `stage11.*.md` — detailed reports for Stage 11.1 through Stage 11.11.2.
- `t5c*.md` — supporting literature/reference notes for the Stage 11.5C
  stability forensics.

## Evidence

- `evidence/` — Stage 11 JSON result snapshots cited by the reports.
- `figures/` — diagnostic figures generated for Stage 11 investigations.

## Freeze boundary

The N=24 no-tide 30-day run is bounded, but N², real-tide, 90-day, and
production-scheduler validation gates remain unresolved. Do not present Stage 11
as a validated ocean climatology or alter its frozen physics under the Stage 11
label. Full details and reproduction instructions are in `STAGE11_FREEZE.md`.
