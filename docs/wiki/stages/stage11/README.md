# Stage 11 — Archived Research Artifact

**Status:** **FROZEN** (D-51). Tag: `stage11-final-frozen` (source `386c850`).
Freeze record: [`../../../STAGE11_FREEZE.md`](../../../STAGE11_FREEZE.md).

Stage 11 modernized the prognostic ocean, EOS-80, forcing, and N>1 dynamics.
It reached a **numerically bounded** state but is **not a production-validated
ocean** (N² inversion, real-tide, and 90-day gates are unresolved). It is
therefore preserved as a reference artifact and Stage 12 uses reanalysis
forcing instead (D-51).

## What lives here

| Path | Contents |
|---|---|
| `evidence/` | 153 Stage 11 validation **JSON** artifacts (the numbers the reports cite: `t3c4_*`, `t5c*`, `matrix_*`, `obc_*`, `stratification_verification.json`, `n24_30day_*.json`, `tide_integration_test.json`, `reproducibility_audit.json`, …) |
| `figures/t3c2/` | diagnostic PNGs referenced by the T3-CORRECTIVE-2 forensics |

## What did NOT move

- Stage 11 **narrative reports** stay in place:
  - `docs/validation/stage11.*.md` — the 11.8.x active-report series,
  - `docs/archive/stage11/stage11.*.md` — the 11.0–11.7 forensic series,
  - top-level `docs/STAGE11_*.md` — summary/state/closure/freeze.
- The curated `data/validation/observations/` dataset stays in `data/validation/`
  (CI depends on it). `data/validation/` is otherwise reserved for **Stage 12**.

## Why archived now

Stage 11 was administratively closed (D-49), then physically validated as
partial (11.11–11.11.2), then frozen (D-51). Moving its raw JSON evidence into
the immutable wiki archive keeps `data/validation/` clean for Stage 12 while
preserving every number behind the reports. Document references were rewritten
from `data/validation/<name>.json` to
`docs/wiki/stages/stage11/evidence/<name>.json`.

## Known limitations (frozen, NOT solved)

- **N² stratification:** min −0.01639 s⁻², 9,813 wet interfaces < −1e−6 — FAIL.
- **Tides:** synthetic M2 only; no FES2014/TPXO; 30-day tide validation not run.
- **90-day forced runs:** not validated (T-38).
- **N=4:** unstable; only N=24 (30-day, no-tide) is bounded.
- **Production scheduler:** T-39 ice/cadence artifact — BLOCKED.
- **N=1:** diagnostic only, not the frozen baseline.

## How to reproduce

```bash
git checkout stage11-final-frozen
fpm test --flag "-I/usr/include"      # full battery, exit 0
```

The `evidence/` JSONs are result snapshots; individual reports describe the
gates they satisfy or fail.
