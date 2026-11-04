# Stage 11.8.0 T0 — Data and Units Verification (Snowfall, EN4, ERA5)

**Status:** COMPLETE
**Date:** 2026-10-23
**Base commit:** `ba447c7` (Stage 11.8.0.0.1)
**Scope:** first rung of the T0–T6 diagnostic ladder — verification only.
No data files were corrected, no physics/EOS/scheduler/operator changed,
the snowfall divisor 43200 was NOT changed (T-19 closed by proof, not patch).

---

## 1. Phase 0 — documentation fixes (5 items)

1. `stage11.8.0_ocean_diagnostic_plan.md` §3: the instruction "snowfall
   divisor 3600s" **removed**; replaced by "divisor change ONLY after T-19
   confirms the accumulation period from source GRIB metadata or the CDS
   probe".
2. Same plan: T2 gate expanded to **all three** required tests —
   homogeneous smoke + weak-inversion core + 1e-12 analytical mixing.
3. `model_physics_status.md`: the 11.8.0.0 "confirms 12-h" wording annotated
   as SUPERSEDED (downgrade history to UNCERTAIN, then resolution here).
4. `PROJECT_ROADMAP.md`: completed-commit range extended to `ba447c7`;
   test counters reconciled **66 files / 66 targets** with the counting
   method documented (all `test/*.f90` now contain `program`; the historic
   64/59 split came from former helper modules).
5. `KNOWN_ISSUES.md` T-19: "only self-consistent interpretation" replaced by
   "cadence does not establish the accumulation interval — source step
   metadata or CDS parameters required" (then resolved in §2 below).

---

## 2. Phase 1 — Snowfall accumulation period (T-19): RESOLVED CONFIRMED_12H

**Static artifact analysis** (all raw `snowfall_2020_*.nc`): `stepType=accum`,
`dataType=fc`, exactly 2 records/day at 43200 s spacing, **no** step-range or
forecast-reference attributes survived cfgrib encoding → strict status
**UNCERTAIN** (spacing is sampling frequency only). Climatology cross-check:
domain-mean January snowfall would be 3.2 mm/month (12-h reading) vs
38.7 mm/month of *snow alone* (1-h reading, implausible vs 15–45 mm total
precipitation climatology) — corroborating but not confirming.

**Live CDS reproduction** (`python/tests/ocean/t19_cds_probe.py`, same
63–90 N / 7–77.5 E bbox, 0.25° grid, 2020-01-15; permitted under the T0
scope for T-19 resolution):

| Comparison | Result |
|---|---|
| artifact(15 Jan 12:00) vs `step=["12"]` request | **max diff 0.0 m (bit-identical)**, sum ratio 1.0 |
| artifact vs sum of `step 1..24` request fields in (00Z,12Z] | CDS collapses the multi-step request to the same single record per valid time; identical field |

**Verdict:** every stored record is the **12-hour accumulation window ending
at its valid_time**; the divisor `43200` in `python/era5/merge_snowfall.py`
is **CONFIRMED CORRECT from source**. T-19 CLOSED 2026-10-23. The divisor was
never changed. Evidence: `docs/wiki/stages/stage11/evidence/snowfall_period_result.json`
(status `CONFIRMED_12H`, basis: live probe) +
`docs/wiki/stages/stage11/evidence/t19_cds_probe.json`.

`test_snowfall_period.py` now: strict evidence hierarchy (step attributes →
CONFIRMED; forecast_reference_time → INFERRED; spacing only → UNCERTAIN;
source file absent → SKIP), `GRIB_stepUnits` honoured (no hours assumption),
monthly-integral sanity check, probe integration.

---

## 3. Phase 2 — EN4 initial T/S: ISSUES_FOUND (71/95 PASS, 0 FAIL, 16 WARNING)

`python/tests/ocean/test_en4_initial_verification.py` (all 4 seasons + Jan
clamp/smooth/rebuild + Apr rebuild variants; 95 checks):

| Check | Result |
|---|---|
| Dimensions (133,105,18), required vars | **PASS** all files |
| Wet columns == 11067 | **PASS** all files |
| Product level cells == 143176 (model reads 143422 post-smoothing — documented 11.7B.1/11.7E.2 distinction) | **PASS** |
| `wet_mask` identical across seasons | **PASS** |
| T==0 / S==0 inside wet cells | **0 / 0** every file — **PASS** (no sentinel zeros) |
| Units/ranges (degC, mass fraction) | PASS except Jan `_rebuild` **WARNING**: T down to −3.28 °C (below any plausible EN4 surface value; see T-22) |
| Supercooling T<Tf(S) (model formula −54·S) | shipped Jan/Apr: **0**; Jul 527 / Oct 662 cells, all by <0.5 °C; clamp variants ≤7158 (all <0.5 °C); **Jan `_rebuild`: 13,671 cells, 6,768 by >0.5 °C → new finding T-22** |
| Density inversions (Eckart f32, > 0.9e-7) | every file has thousands–tens of thousands of inverted interfaces (max residual 1.9e-4…9.7e-4). Expected for raw EN4 (this is exactly the load CA carries; ties to the 10.21/10.22 guard-saturation story). **WARNING**, quantified, not corrected |
| **Vertical grid z_model_m vs model DATA z** | **all 4 shipped seasonal products carry the legacy shadowed grid** [2.5,5,7.5,…,550] instead of [2.5,5,10,…,600] m; the Fortran reader **ignores z_model_m and reads levels by index**, so product metadata mislabels the depth of every level (offset up to 50 m); `_rebuild` variants (Jan, Apr) match correctly; **no rebuild exists for Jul/Oct** → new finding **T-20** |

Seasonal availability: all four shipped seasons present → the 11.8A "seasonal
gap" is NOT missing-files but the z-grid defect + missing Jul/Oct rebuilds.

---

## 4. Phase 3 — ERA5 coverage: ISSUES_FOUND (10/13 PASS, 0 FAIL, 3 WARNING)

`python/tests/ocean/test_era5_coverage_verification.py`; model wet-cell domain
from `stage11.7E_JANOFF` day_00: lat [64.85, 84.96], lon [8.72, 76.22].

| Product | south | north | west | east | Verdict |
|---|---|---|---|---|---|
| Jan `era5_2020_01_fullcoverage_merged.nc` (lat 63–90, lon 7–77.5) | +1.85° | +5.04° | +1.72° | +1.28° | **PASS** (all ≥1°) |
| Apr `era5_2020_04_merged.nc` (lat 65–90, global lon) | **−0.15°** | +5.04° | inf | inf | **WARNING** — south margin unmet; **8 model cells beyond the file edge rely on the D32 nearest-edge clamp** |

Other checks (PASS): uniform 6-hourly time axes (no gaps) for both products;
0 model cells outside the longitude ranges (the ±360 wrap code exists and is
correct per T-18 convention, but never exercised by the domain); latitude
out-of-range → not-ok → D32 clamp documented; time selection is
**nearest-time** (`era5_find_time_index`, no temporal interpolation — H-4
noted for T1/T5); longitude-edge behaviour documented.

**H-2 wind rotation (preliminary, documented for T4):** `era5_wind` copies
u10/v10 (×100) directly into `windx1/windy1` as GRID components with no
geographic→grid rotation, while the grid is EPSG:3996-derived (rotated) and
the legacy FI1DL1 path rotated an observed angle by the grid sin/cos. Not a
confirmed magnitude yet (needs T4 runs), but a standing hypothesis —
recorded in KNOWN_ISSUES (H-2 row). **NOT fixed in T0.**

---

## 5. Phase 4 — Regression and verification

| Suite | Result |
|---|---|
| `fpm test` (clean rebuild) | exit 0 — **56/56** STOP-0, 0 FAIL/ERROR-STOP |
| Strict build (Wall/Wextra/fcheck/ffpe) | exit 0 |
| ERA5 contract | 120/120 |
| Sea-ice/tides builders | 33 checks, 0 errors |
| Provenance attributes | 28/28 |
| Ice coverage | 16/16 |
| Sea-ice provenance | 8/8 |
| Homogeneous smoke driver | LEGACY+EOS80 PASS (dT=dS=0, exit 0) |
| Weak-inversion core driver | LEGACY PASS (mix {2,3}), EOS80 PASS (mask documented) |
| Snowfall period | CONFIRMED_12H (probe), divisor unchanged |
| EN4 initial verification | 71 PASS / 16 WARNING / 0 FAIL → T-20/T-22 recorded |
| ERA5 coverage verification | 10 PASS / 3 WARNING → T-21 + H-2 recorded |
| `git diff --check` | clean |
| GitHub Actions | green on the pushed commit (watched) |

---

## 6. T0 verdict → findings feed the ladder

| Finding | ID | Ladder step |
|---|---|---|
| Snowfall divisor confirmed correct (12-h windows) | T-19 CLOSED | none needed |
| Shipped EN4 products carry legacy shadowed z grid; Jul/Oct lack rebuilds; reader ignores z_model_m | **T-20 OPEN** | T0-corrective (11.8): rebuild Jul/Oct + reader z-verify or documented acceptance |
| Jan `_rebuild` has 13,671 sub-Tf cells (6,768 by >0.5 °C) | **T-22 OPEN** | pipeline fix with salt conservation (11.8 core/data) |
| Initial-state density inversions at 1e-4 scale across seasons | documented | CA/EOS core evidence for T2 (already known 10.21) |
| April ERA5 south margin −0.15° (8 clamped cells) | **T-21 OPEN** | T1 (forcing contract): extend domain ≥1° |
| Wind rotation unapplied in ERA5 mode | **H-2 documented** | T4 (measure before any change) |
| Nearest-time selection, no temporal interpolation | documented | T1/T5 consideration |

**GO for Stage 11.8.0 T1** (forcing contract verification), with T-20/T-22
data corrections scheduled as the next diagnostic rung (they gate the
T3/T4 tiers more than T1 does).

## 7. Confirmations

- No physics/EOS/scheduler/numerical-operator changes; `EOS_MODE=LEGACY`
  default untouched.
- Snowfall divisor **not changed** (43200 — now confirmed correct).
- No production data files modified; downloads limited to the two-day
  CDS probe reproduction permitted for T-19.
- 11.7E.5, T1–T6 implementation and Stage 12 not started.
