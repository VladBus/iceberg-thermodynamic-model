# Stage 11.8.0 T1 — Forcing Contract Verification (ERA5 Interpolation & Wind)

**Status:** COMPLETE
**Date:** 2026-10-23
**Base commit:** `e57521b` (Stage 11.8.0 T0)
**Scope:** T1 ladder rung — verification only. No physics/EOS/scheduler/operator
change; no production data modified; no forcing code changed.

Every number below comes from the **production reader** (`netcdf_input.f90`):
the Fortran harness `test/test_era5_interp_harness.f90` self-generates
synthetic ERA5-like NetCDF files and calls `era5_open`, `era5_bilinear2d`
and `era5_find_time_index` directly.

---

## 1. Phase 0 — documentation review

T0 report / KNOWN_ISSUES (T-20, T-21, T-22) / ROADMAP consistency checked — no
contradictions found. `model_physics_status.md` advanced to T1 and T0 findings
referenced. This report and the KNOWN_ISSUES updates below are the only
documentation changes.

---

## 2. Phase 1 — Spatial interpolation (production code): **WARNING**

**Method (documented from `era5_bilinear2d`):** bilinear interpolation on the
regular lat/lon grid; latitude flipped at read time if the file is decreasing;
latitude outside the file → `ok=.false.` (no extrapolation; the D32
nearest-edge clamp lives in `era5_wind`); longitude normalized by ±360 with a
cyclic (dateline) neighbour node; weights clamped to [0,1].

**Synthetic test** (6 lat 70→60 decreasing × 8 lon −180→135 step 45 ≈ global
circular axis × 3 times; `u10 = 10 + 0.5·lat + 0.1·lon`, linear → bilinear must
be exact):

| Check | Result |
|---|---|
| Interior probes (4 points, incl. flipped-latitude coordinates) | **max abs error 0.0** (machine precision) — PASS |
| Latitude flip at open | `era5_lat(1)=60`, `era5_lat(6)=70` — PASS |
| Latitude outside range (80 N, 55 N) | both rejected (`ok=false`) — PASS |
| Latitude edge nodes (70 N, 60 N) | both accepted — PASS |
| **Dateline wrap probe** (global axis; query 170 E; nodes 135→180) | **actual 180.0 vs expected 170.0 → error 10.0°** — **WARNING (latent bug L-1)** |

**Wrap finding (T-23):** the ±360 normalization runs the two loop passes only
once, so a query east of the last node lands *outside* the grid
(−190° → binary search pins column 1), and the weight clamp then returns the
first-node value instead of interpolating across the dateline. **Production
impact is nil today**: T0 found 0 model cells outside the ERA5 longitude
ranges (Jan bbox 7–77.5 E; Apr global, model 8.7–76.2 E), so the branch is
never exercised. Documented, **not fixed** in T1.

**Overall spatial status: WARNING** (interior/edges PASS; wrap latent).

---

## 3. Phase 2 — Temporal selection (production code): **PASS**

**Method (documented from `era5_find_time_index`):** nearest record with
clamping — `sec ≤ t(1)` → 1, `sec ≥ t(n)` → n, otherwise binary search and the
nearer neighbour; an exact midpoint tie selects the **earlier** record. No
temporal interpolation, no smoothing.

Harness file A = 3 records at 0/6/12 h; file B = 0/6/**24** h (24 h hole).

| Scenario | Expected | Actual | Status |
|---|---|---|---|
| exact 0 h / 6 h / 12 h | 1 / 2 / 3 | 1 / 2 / 3 | PASS |
| between, 1 h | 1 | 1 | PASS |
| between, 4 h | 2 | 2 | PASS |
| exact midpoint, 3 h (tie) | 1 (earlier) | 1 | PASS |
| before range, −1 h | clamped 1 | 1 | PASS |
| after range, +1 h past end | clamped 3 | 3 | PASS |
| gap file, 12 h | 2 (nearest 6 h) | 2 | PASS |
| gap file, 15 h (tie 6 h/24 h) | 2 (earlier) | 2 | PASS |
| gap file, 21 h | 3 (nearest 24 h) | 3 | PASS |
| time axis | strictly increasing, seconds since 1970-01-01 | monotonic, t(1)=1577836800 | PASS |

**Overall temporal status: PASS.** Nearest-time behaviour is recorded as
**T-24** (6-hourly fields held constant up to 3 h; relevant to the T5 time
tier). Production data have uniform 6-hourly axes with no gaps (T0), so the
gap branch is a documented behaviour, not an active defect.

---

## 4. Phase 3 — Wind rotation (preliminary for T4): **CRITICAL**

**Grid orientation** (derived from the model lat/lon field over 11,067 wet
cells; X = +j = u axis, Y = +i = v axis):

| Quantity | min | median | mean | max |
|---|---|---|---|---|
| grid X axis angle from east | 14.0° | **50.2°** | 50.1° | 81.3° |
| grid Y axis angle from east | 8.7° | 39.9° | 40.0° | 76.2° |
| X–Y orthogonality | — | 90.02° (p5–p95: 89.99–90.05) | — | — |

The grid **is rotated** (EPSG:3996-derived polar stereographic). **Rotation is
required**, but `era5_wind` assigns `windx1 = u10×100`, `windy1 = v10×100`
directly as grid components (and builds `tx1/ty1` from those components) with
**no geographic→grid rotation**; the legacy FI1DL1 path instead rotated an
observed angle via sin/cos. Wind forcing is therefore misaligned by the local
grid-convergence angle (median ~50°, up to 81°).

**Status: CRITICAL for T4**; H-2 upgraded from "preliminary" to **CONFIRMED**.
NOT fixed in T1 (T4 owns the wind tier).

---

## 5. Phase 4 — T-21 (April south margin): ACCEPTED LIMITATION

| Quantity | Value |
|---|---|
| Wet cells south of the April file edge (65.0 N) | **8 / 11,067 = 0.072 %**; lat 64.85–65.00 |
| Clamped edge vs next interior row | Δu ≤ 2.25 m/s (cell 2: −0.87 vs −1.47), Δv ≤ 2.25 m/s (cell 1: 7.49 vs 9.74), ΔT ≤ 0.80 °C, ΔP ≤ 42 Pa |
| Domain means (edge row vs next row) | u 1.65 vs 1.58, v 0.67 vs 0.69, T −11.68 vs −11.95 °C |

The clamped values are physically typical of the surrounding edge and the
affected area is 0.07 % of the wet domain → **Option C: accepted limitation**
(T-21 status updated). No download or code change made.

---

## 6. Phase 5 — Regression and verification

| Check | Result |
|---|---|
| Full `fpm test` (clean targets) | exit 0 — **57/57** STOP-0 (56 + interpolation harness), 0 FAIL/ERROR-STOP |
| New: `test_era5_interp_harness` (named target) | PASS (spatial WARNING / temporal PASS) |
| ERA5 contract | 120/120 |
| Sea-ice/tides | 33 checks, 0 errors |
| Provenance | 28/28 |
| Ice coverage | 16/16 |
| Sea-ice provenance | 8/8 |
| Snowfall (T-19) | CONFIRMED_12H |
| EN4 initial (T0) | ISSUES_FOUND (T-20/T-22, unchanged) |
| ERA5 coverage (T0) | ISSUES_FOUND (T-21 accepted) |
| Spatial interpolation driver | WARNING (interior/edges PASS, wrap latent) |
| Temporal interpolation driver | PASS |
| Wind rotation driver | CRITICAL (H-2 confirmed for T4) |
| Strict build | exit 0 |
| `git diff --check` | clean |
| GitHub Actions | green (watched on the pushed commit) |

---

## 7. T1 summary and GO/NO-GO

| Contract element | Verdict |
|---|---|
| Bilinear spatial interpolation (interior, flipped latitude) | **PASS** (exact) |
| Latitude out-of-range / edge handling | **PASS** (reject / accept; D32 downstream) |
| Longitude wrap | **WARNING** (latent L-1/T-23; unreachable in production today) |
| Temporal selection (exact/between/tie/clamp/gap) | **PASS** (nearest-time; T-24 documented) |
| Time-axis consistency | **PASS** |
| Wind rotation | **CRITICAL** (H-2 confirmed; T4 fix) |
| T-21 April margin | **ACCEPTED LIMITATION** (0.072 %) |

**GO for Stage 11.8.0 T2 (CA/EOS core diagnostics).**
Carried constraints: **T-20 and T-22 MUST be resolved before T3 (Rest)** —
they corrupt the initial ocean state; H-2 must be fixed in T4; T-23 is latent
until a dateline/global forcing query is introduced.

## 8. Confirmations

- No physics, EOS formula, scheduler, or numerical operator modified;
  `EOS_MODE=LEGACY` remains default.
- No production forcing/data files modified; the synthetic NetCDF files are
  generated under `build/` by the harness.
- Snowfall divisor unchanged (43200, T-19-confirmed).
- T2–T6 not implemented; 11.7E.5/Stage 12 not started.
