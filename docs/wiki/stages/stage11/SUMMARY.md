# Stage 11 — Consolidated Historical Summary

> Stage 11 was administratively closed on 2026-10-27 and frozen as a research
> artifact on 2026-10-29. This summary combines the former `STAGE11_SUMMARY.md`
> and `STAGE11_FINAL_SUMMARY.md`; `STAGE11_FREEZE.md` is the authoritative
> record of scientific scope and limitations.

- **Frozen source:** `386c850`
- **Tag:** `stage11-final-frozen`
- **Decision:** D-51
- **Current status:** historical record only; Stage 12 is active.

## Achievements at freeze

- The T3-CORRECTIVE stabilization configuration (`dt=1800 s`, `Ah=10000 m²/s`)
  passed its bounded-state gate: max `|U|` 0.147 m/s and KE30/KE15 0.568.
- The N=1 30-day seasonal matrix passed for Jan/Apr/Jul/Oct. EOS-80 passed the
  8-cell seasonal matrix and became the runtime default; `EOS_MODE=LEGACY`
  remains the explicit fallback (D-29, D-47, D-48).
- The N=24 no-tide 30-day run completed with 0 NaN cells, max `|U|` 1.999 m/s,
  max CFL 0.518, and decaying kinetic energy after day 10. This is a bounded
  numerical result, not validation of an ocean climatology.
- Forcing audits covered wind rotation, longitude handling, snowfall, and
  30-day seasonal behaviour. The Stage 11.10 data/run cleanup was executed;
  its report records the retained inventory.

## Limitations retained by the freeze

- **Stratification fails:** N² minimum −0.01639 s⁻²; 9,813 wet interfaces are
  below −1e−6.
- **Tides are not validated:** only a 10-day synthetic M2 control was run; no
  real tidal product or 30-day tide validation is available.
- **Long runs are not validated:** the 90-day forced configuration remains an
  accepted limitation (T-38).
- **N=4 is unstable.** The bounded N=24 result does not establish stability for
  other scheduler settings.
- **Production scheduler validation remains blocked** by the T-39 ice/cadence
  artifact. N=1 is diagnostic only, not a production baseline.
- Only January has connected OSI-SAF/C3S sea-ice initialization; other seasonal
  cases are not observationally validated.

## Later work

Stage 12 changed iceberg forcing to offline/prescribed reanalysis products and
did not promote the Stage 11 prognostic ocean. Daily-forcing acquisition for
Stage 12.9 is incomplete and paused. See the current model status and validation
index outside this historical archive.

## Evidence and reports

- Freeze record: `docs/wiki/stages/stage11/STAGE11_FREEZE.md`.
- Closure checklist and administrative declaration: files in this directory.
- Detailed Stage 11 reports: the `stage11.*.md` files in this directory.
- Archived evidence: `evidence/`; diagnostic figures: `figures/`.
- Stage 11.9 final review: `docs/wiki/stages/stage11/stage11.9_final_review.md`.
