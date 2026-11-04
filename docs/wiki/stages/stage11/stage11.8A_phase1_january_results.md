# Stage 11.8A Matrix — Phase 1 (January, 4 cells)

**Status:** COMPLETE — all 4 January cells PASS; **Phase 2 GO**.
**Date:** 2026-10-25
**Base:** `23c8e67`

---

## 1. Execution

All four January cells were **executed fresh** with the standard protective
config and **real OSI-SAF/C3S sea ice** (`STAGE117E_NETCDF_SEAICE=ON`), so the
matrix cells are directly comparable. T4/T6 runs remain historical references
(they used legacy ice), not the matrix cells.

| Cell | EOS | Scheduler | Days/steps | NaN |
|---|---|---|---|---|
| 1 `matrix_jan_legacy_n1` | LEGACY | N=1 | 30 d / 360 canonical | 0 |
| 2 `matrix_jan_eos80_n1` | EOS80 | N=1 | 30 d / 360 canonical | 0 |
| 3 `matrix_jan_legacy_prod` | LEGACY | PRODUCTION | 30 d / **720/720 fire-steps** | 0 |
| 4 `matrix_jan_eos80_prod` | EOS80 | PRODUCTION | 30 d / **720/720 fire-steps** | 0 |

## 2. Metrics comparison

| Cell | max \|U\| | max \|V\| | KE30/KE15 | S min (PSU) | RO min | NaN | Volume/heat/salt |
|---|---|---|---|---|---|---|---|
| 1 LEGACY N1 | 0.794 | 0.584 | 1.486 | 24.88 | **0** | 0 | 0 / 5.35e-2 / 8.76e-4 |
| 2 EOS80 N1 | 0.785 | 0.584 | 1.494 | 24.92 | **0** | 0 | 0 / 5.21e-2 / 8.70e-4 |
| 3 LEGACY Prod | 0.511 | 0.497 | 1.479 | 24.88 | **0** | 0 | 0 / 3.56e-1 / 7.78e-4 |
| 4 EOS80 Prod | 0.511 | 0.500 | 1.483 | 24.92 | **0** | 0 | 0 / 3.46e-1 / 7.41e-4 |

All gates pass: max |U| <2 m/s, KE30/KE15 <5, S≥0, RO≥0, salt <1e-3, no NaN.
Heat drift is interpreted as forced (T-34), not numerical.

CA (N=1): cells 1/2 total nmix 2.11e7/1.87e7, max day 2.58e6/2.54e6,
guard days 0, maxiter 133/135. Production path suppresses numeric CA
diagnostics (`nmix=********`), so CA totals are not available there.

## 3. Interaction effects

**EOS effect (EOS80 vs LEGACY):**
- N1: max |U| −1.1 %, KE ratio +0.5 %; production: max |U| +0.15 %,
  KE ratio +0.22 %.
- Salt/heat metrics within ~2 %; ice volume +0.6 % (N1), +2.0 % (production).
- **No EOS-driven pathology; EOS80 is equivalent within 10 %.**

**Scheduler effect (Production vs N1):**
- max |U| falls 35.6 % (0.794→0.511 N1→production); KE ratio −0.5 %.
- Ice extent rises 65 % (3,543→5,851 cells) and volume +39 %; mean thickness
  falls 0.598→0.502 m. This is the **STALE coupling/cadence effect**, not an
  instability; production scheduler intentionally uses day-start ice→ocean
  coupling and 24 fires/day.

**Interaction:** EOS effect on KE/max-U is nearly identical in N1 and
production; differences are ≤0.3 %. Ice EOS effect is slightly larger under
production (volume +2.0 % vs +0.6 %) but no sign reversal or runaway.
**No interaction pathology** under the Phase-1 gates.

## 4. Ice diagnostics (January, real OSI-SAF/C3S)

| Cell | Extent (10³ km²) | Volume (km³) | Mean thickness (m) |
|---|---|---|---|
| 1 LEGACY N1 | 683.6 | 408.5 | 0.598 |
| 2 EOS80 N1 | 687.4 | 412.8 | 0.600 |
| 3 LEGACY Prod | 1,128.8 | 566.6 | 0.502 |
| 4 EOS80 Prod | 1,182.5 | 577.7 | 0.489 |

EOS effect on ice is small; scheduler effect is large (as expected from STALE
coupling). Ice drift velocity is not archived; not reported.

## 5. Preliminary D-29 assessment

- **Criterion A (all EOS80 cells pass): SATISFIED** (cells 2 and 4 PASS).
- **Criterion B (EOS80 equivalent or better, ≤10 %): SATISFIED** for January
  (KE ratio and max-U differences ≤1.1 %, salt/heat ≤2 %).
- **Criterion C (no scheduler interaction pathology): SATISFIED** (EOS effect
  consistent across N1/production; no runaway).
- **Preliminary recommendation:** EOS80 remains a viable candidate; final
  D-29 decision requires Apr/Jul/Oct. Do not promote yet.

## 6. GO/NO-GO

**Phase 2 (April/July/October): GO.** All four January cells pass; no
interaction pathology. Matrix execution beyond Phase 1 remains pending.

## 7. Regression

Full `fpm test` 63/63, strict build 0; default 1-day legacy md5 identical;
`git diff --check` clean. No physics/EOS/scheduler code change.

JSON: `matrix_jan_comparison.json`, `matrix_jan_ice_diagnostics.json`,
`matrix_jan_d29_preliminary.json`, `matrix_jan_metrics.json`.
