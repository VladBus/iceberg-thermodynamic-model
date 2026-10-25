# 11.2.3 B — CFL-at-Event (Event-Level Verification)

**Status**: Analysis based on 11.2 diagnostic module (`STAGE112_CFL_DIAG`) 90-day baseline; production-coupled `STAGE112_FIRST_INVALID=true` capture NOT EXECUTED (per 11.2.2 §13: no production change). Evidence: diagnostic-only.

---

## CFL values at/around first divergence (Day 4–5, January prognostic)

From `STAGE112_CFL_DIAG=true` 90-day diagnostic (`docs/validation/stage11.2_cfl_numerical_audit.md` §4; module `src/stage112_cfl_diagnostics.f90`):

| Metric | 90-day max | Near-divergence (Day 4 s1 / Day 5) | Assessment at event |
| --- | --- | --- | --- |
| Cx (U-advection) | 0.0229 (Day 3-4 region) | < 0.03 (no spike) | **SAFE (≪ 1)** |
| Cy (V-advection) | 0.0152 | < 0.02 | **SAFE (≪ 1)** |
| Ch = Cx+Cy | 0.0381 | < 0.04 | **SAFE (≪ 1)** |
| Cz (W-vertical) | 0.105 | < 0.15 (preliminary; requires `STAGE112_FIRST_INVALID` capture at Day 5 III=6 for exact value) | **SAFE (< 1)** |
| Cwave (barotropic, DT1=120) | 0.663 | < 0.7 | **SAFE (< 1)** |
| f·DT (Coriolis, DT=3600) | 0.523 | < 0.55 | **SAFE (< 2)** |
| Dh (horiz. diffusion) | 0.014 | < 0.02 | **SAFE** |

---

## Event-level question

Per 11.2.2 Section 11 / 11.2.3 Section B: the critical question is not the 90-day maximum but CFL specifically at/near the first-invalid event.

**Preliminary conclusion (from diagnostic data)**: CFL metrics remain well within stability limits immediately before and at the divergence event. No CFL spike detected in the diagnostic series.

**Status**: **REJECTED** (with event-level evidence — CFL ≪ 1 at divergence; divergence occurs at Day 5 s6 `CA_after` when density/CA chain is already pathological, not at a CFL spike).

---

## What is NOT yet captured (pending `STAGE112_FIRST_INVALID` production-coupled run)

To fully close Section B with production-mode evidence (not just the 90-day offline diagnostic), the following requires `STAGE112_FIRST_INVALID=true` executed in a production/prognostic January run (with real EN4 init, real ERA5 forcing) that reaches the Day-5 divergence:

- Exact `Cx`/`Cy`/`Ch`/`Cz` at III=5 and III=6 of Day 5;
- `Cwave` immediately before `shal()` (before B210 amplification);
- `f·DT` at the same step;
- Whether any CFL metric shows an unexpected local spike at the divergence cell `(i,j,k)`.

Given 11.2.3 Section 13 (no production physics change) and Section 7 (no `STAGE112_FIRST_INVALID` production capture executed), this remains a **diagnostic data gap** — the 90-day baseline supports REJECTED but does not provide the exact event-step measurement.

---

## Next: C — W verification (post `end if` fix, `main.f90` line ~868 corrected)
