# Stage 11.8A Phase 2 — N=1 Seasonal Matrix (all 8 cells)

**Status:** COMPLETE — **7/8 PASS**; D-29 **NOT PROMOTED**; Stage 11.9
**NO-GO at this time** (not started).
**Date:** 2026-10-26
**Base:** `e8de52e` (Phase 1-ANALYSIS)
**Scope:** N=1 scheduler only. Production scheduler remains **BLOCKED**
(T-39); no production cells were run.

---

## 1. Execution and forcing caveat

| Group | Cells | Days | Forcing / initial state | Verdict |
|---|---|---|---|---|
| January (Phase 1) | LEGACY/EOS80 × N=1 | 30 | Real OSI-SAF/C3S ice; ERA5 Jan | reuse, both PASS |
| April | LEGACY/EOS80 × N=1 | 30 | EN4 Apr; ERA5 Apr + boundary | both PASS |
| July | LEGACY/EOS80 × N=1 | 30 | EN4 Jul; ERA5 Jul | LEGACY PASS; **EOS80 FAIL** |
| October | LEGACY/EOS80 × N=1 | 30 | EN4 Oct; ERA5 Oct | both PASS |

All cells use the standard protective set: `STAGE113_DT=1800`,
`STAGE118_LAPLACIAN_VISC=ON`, `AH=10000`, `RO_PROGNOSTIC=ON`,
`CA_POTENTIAL=ON`, `CA_F64_N2=ON`, `WIND_ROTATION=ON`, `LON_CLAMP=ON`,
`MONOTONE_ADVECTION=ON`, `SPONGE_BOUNDARY=ON` (α=1/day),
`DENSITY_REPAIR=ON`; N=1 (no production env). N=1 therefore runs
**48 thermodynamic steps/day at dt=1800 s (1,440 steps over 30 days)**.

**April forcing extension:** the delivered `era5_2020_04_merged.nc` has only
120 six-hourly slices, so the model auto-limits to **29 days**. To execute the
required 30-day cell, one boundary slice (1 May 2020 00:00, persisted from
30 Apr 18:00) was appended to a derived 121-slice file
(`era5_2020_04_30day_extended_merged.nc`). This affects only the final forcing
boundary; the 29-day and four-slice preliminary runs are retained as
diagnostics, not matrix cells. No model code was changed.

## 2. Phase 1 — April (2 cells)

| Cell | max \|U\| | max \|V\| | KE30/KE15 | S min (PSU) | RO min | NaN | heat drift | salt drift | Ice extent / volume / thickness | PASS |
|---|---|---|---|---|---|---|---|---|---|---|
| LEGACY | 0.838 | 0.530 | 1.506 | 25.111 | 0 | 0 | 1.323e-2 | 7.281e-4 | 174,989 km² / 52.05 km³ / 0.297 m | **YES** |
| EOS80 | 0.843 | 0.531 | 1.507 | 25.049 | 0 | 0 | 1.036e-2 | 7.262e-4 | 208,946 km² / 58.44 km³ / 0.280 m | **YES** |

Both max \|U\| <2 m/s, KE30/KE15 <5, S≥0, RO≥0, volume exact, salt <1e-3,
no NaN. Ice is legacy January-derived/diagnostic, not OSI-SAF April.

## 3. Phase 2 — July (2 cells)

| Cell | max \|U\| | max \|V\| | KE30/KE15 | S min (PSU) | RO min | NaN | heat drift | salt drift | PASS |
|---|---|---|---|---|---|---|---|---|---|
| LEGACY | 0.542 | 0.549 | 0.827 | 21.908 | 0 | 0 | 4.865e-3 | 4.819e-4 | **YES** |
| EOS80 | 0.543 | 0.554 | 0.826 | 21.908 | **−2.504e-3** | 0 | 4.712e-3 | 4.849e-4 | **NO** |

EOS80 has **7 surface cells with RO<0** (minimum at 72.96 °N, 69.23 °E:
T=2.10 °C, S=25.03 PSU); the others are 72.96–74.63 °N / 69.23–75.69 °E.
No NaN, no runaway, max \|U\| 0.543; this is a small EOS-80 surface density
residual after CA/B200, not a stability failure. It nevertheless violates the
strict **RO≥0** gate (T-41). July ice extent is zero at day 30 in both cells.

## 4. Phase 3 — October (2 cells)

| Cell | max \|U\| | max \|V\| | KE30/KE15 | S min (PSU) | RO min | NaN | heat drift | salt drift | PASS |
|---|---|---|---|---|---|---|---|---|---|
| LEGACY | 0.690 | 0.451 | 2.152 | 25.013 | 0 | 0 | 2.619e-3 | 6.177e-4 | **YES** |
| EOS80 | 0.689 | 0.447 | 2.172 | 25.013 | 0 | 0 | 2.427e-3 | 6.108e-4 | **YES** |

Both pass; ice extent is zero at day 30. October has the largest KE ratio
(2.15–2.17), still below the 5 gate.

## 5. Comprehensive comparison (all 8 cells)

| Season | EOS | max \|U\| | max \|V\| | KE30/KE15 | S min (PSU) | RO min | NaN | PASS |
|---|---|---|---|---|---|---|---|---|
| Jan | LEGACY | 0.794 | 0.584 | 1.486 | 24.881 | 0 | 0 | YES |
| Jan | EOS80 | 0.785 | 0.584 | 1.494 | 24.915 | 0 | 0 | YES |
| Apr | LEGACY | 0.838 | 0.530 | 1.506 | 25.111 | 0 | 0 | YES |
| Apr | EOS80 | 0.843 | 0.531 | 1.507 | 25.049 | 0 | 0 | YES |
| Jul | LEGACY | 0.542 | 0.549 | 0.827 | 21.908 | 0 | 0 | YES |
| Jul | EOS80 | 0.543 | 0.554 | 0.826 | 21.908 | **−2.504e-3** | 0 | **NO** |
| Oct | LEGACY | 0.690 | 0.451 | 2.152 | 25.013 | 0 | 0 | YES |
| Oct | EOS80 | 0.689 | 0.447 | 2.172 | 25.013 | 0 | 0 | YES |

Volume conservation is exact (0) for every cell; salt drift is
4.82e-4–8.76e-4 (<1e-3); heat drift is 2.43e-3–5.35e-2 (forced, T-34, not a
zero-drift gate). **All 8 cells have no NaN; 7/8 pass the RO≥0 gate.**

## 6. EOS effect (EOS80 vs LEGACY, all four seasons)

| Season | max \|U\| effect | KE30/KE15 effect | CA nmix effect |
|---|---|---|---|
| Jan | −1.10 % | +0.52 % | −11.73 % |
| Apr | +0.56 % | +0.06 % | −24.95 % |
| Jul | +0.15 % | −0.18 % | −8.30 % |
| Oct | −0.19 % | +0.92 % | −6.40 % |
| **Mean** | **−0.14 %** | **+0.33 %** | **−12.85 %** |

Classification: max \|U\| and KE30/KE15 **equivalent** (|mean| ≤10 %); CA nmix
**improvement** (fewer mixings). EOS80 is dynamically equivalent to LEGACY
within the documented metric; the sole gate failure is the July surface RO
residual. **Criterion B is satisfied.**

## 7. Ice diagnostics

| Season | Source | LEGACY extent / volume / thickness | EOS80 extent / volume / thickness |
|---|---|---|---|
| Jan | **real OSI-SAF/C3S** | 683,558 km² / 408.49 km³ / 0.598 m | 687,417 km² / 412.78 km³ / 0.601 m |
| Apr | legacy diagnostic | 174,989 km² / 52.05 km³ / 0.297 m | 208,946 km² / 58.44 km³ / 0.280 m |
| Jul | legacy diagnostic | 0 / 0 / 0 | 0 / 0 / 0 |
| Oct | legacy diagnostic | 0 / 0 / 0 | 0 / 0 / 0 |

Only January is observationally initialized. April/July/October ice is
January-derived/diagnostic and **not OSI-SAF-validated**; July/October ice
extent is zero at day 30. Do not use these seasonal ice diagnostics as an
observational validation.

## 8. D-29 final decision

| Criterion | Result | Evidence |
|---|---|---|
| **A — all EOS80 cells pass gates** | **FALSE** | July EOS80 RO min −2.504e-3 (7 surface cells, T-41) |
| **B — EOS80 equivalent or better** | **TRUE** | mean max \|U\| −0.14 %, KE +0.33 %, CA −12.85 % |
| **C — no scheduler interaction pathology** | **TRUE for N=1** | Phase 1 no N=1 pathology; production interaction not assessable (T-39) |

**Verdict: NOT PROMOTED.** EOS80 remains optional; LEGACY Eckart stays the
default. The Stage 11 goal “EOS-80 in production” is recorded **NOT MET**
(honest closure per the D-29 rule), because the production scheduler is
blocked by T-39 and one EOS80 N=1 cell fails a strict gate.

Caveats:
- Decision is **N=1 only**; production ice climatology is not validated (T-39).
- Apr/Jul/Oct ice is diagnostic, not observational.
- 30-day runs only; 90-day runs are not validated (T-38).
- April uses one persisted boundary forcing slice to reach 30 days.

## 9. Stage 11.9 gate

**NO-GO at this time.** Stage 11.9 is **not started**. Reasons:

1. Acceptance is **7/8**, not 8/8; July EOS80 fails RO≥0 (T-41).
2. Stage 11.8B production release audit has not been performed.

T-39 (production scheduler ice/cadence) is future work and is **not a blocker
for N=1 closure**; production cells remain excluded.

No corrective code change was made. EOS80 may remain optional; the July
residual must be either adjudicated as an accepted EOS80 limitation or fixed
in a dedicated stage before any EOS80 promotion.

## 10. Regression and reproducibility

- Full `fpm test`: **63/63**, exit 0; no failures.
- Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=...`): exit 0.
- Default legacy 1-day md5: `915b1903…` identical to canonical.
- `git diff --check`: clean.
- CI: **GREEN** — Phase 2 run `40373305325` (both jobs success).

**No physics/EOS/scheduler code changed. No production scheduler cells run.**
