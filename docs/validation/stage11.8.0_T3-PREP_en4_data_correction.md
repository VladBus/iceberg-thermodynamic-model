# Stage 11.8.0 T3-PREP — EN4 Data Correction (T-20 z-grid, T-22 supercooling)

**Status:** COMPLETE
**Date:** 2026-10-24
**Base commit:** `43db802` (Stage 11.8.0 T2)
**Scope:** DATA CORRECTION ONLY. No physics, CA algorithm, EOS, scheduler or
numerical operator was changed; `EOS_MODE=LEGACY` remains the default.
T-25 (CA in-situ density), T-23 (ERA5 wrap) and H-2 (wind rotation) were
**not fixed** — only scheduled.

---

## 1. Phase 0 — findings documented and correction plan added

- T2 findings confirmed in `KNOWN_ISSUES.md`: **T-25** (CA uses in-situ
  density; critical, **T2-CORRECTIVE before T6**), **T-27** (f64 core stores
  state in f32), **T-23** (wrap; **T1-CORRECTIVE before T4**), **H-2** (wind
  rotation; **T4**).
- `PROJECT_ROADMAP.md` now carries an explicit post-T2 correction plan
  (T2-CORRECTIVE / T1-CORRECTIVE / T4) with the D-33 branch decision required
  before any CA change.

---

## 2. Phase 1 — T-20 (EN4 z-grid): FIXED by regeneration (Option B)

**Diagnosis**
- Shipped products: `z_model_m = [2.5, 5, 7.5, 12.5, …, 550]` (18 levels,
  550 m bottom); model DATA z: `[2.5, 5, 10, 15, …, 600]` (18 levels, 600 m).
- The Fortran reader ignores `z_model_m` and reads by index, so the shipped
  data were interpreted at the wrong depths.
- **Decisive check:** shipped vs rebuilt T at identical indices differs by up
  to **7.5 °C** (level 1 alone: max 5.56 °C mean 1.46 °C) → the *data* were
  produced by a different (pre-fix) pipeline/grid, not merely mislabeled.
  → **Option A (metadata-only) rejected; Option B (regenerate) chosen.**

**Fix**
- Regenerated all four seasons with the corrected builder
  (`python/ocean/build_initial_ts.py`; canonical global `Z_M`, per-season
  target date and product metadata) and created `_rebuild` variants for all
  four seasons (Jul/Oct previously missing).
- Old products archived at
  `data/input/processed/ocean/archive_pre_T3PREP/` (forensics; data are
  gitignored, so no commit impact).
- `test/ocean_init_test.f90` regression anchors updated to the corrected
  reference product.

**Verification:** all 8 products (4 seasons × canonical/rebuild) have
`z_model_m == model DATA z` (600 m bottom); the reader's index read is now
correct by construction. Logged anchor values match the corrected file to
<1e-5.

---

## 3. Phase 2 — T-22 (supercooling): FIXED by physical clamp

**Cause:** EN4 analysis values below the seawater freezing point survive the
horizontal/vertical regrid (not a unit conversion error).

**Fix (in the builder):**
- Compute **UNESCO/Fofonoff–Millard Tf(S,p)**
  `Tf = (−0.0575 + 1.710523e−3·√S − 2.154996e−4·S)·S − 7.53e−4·p`
  with `S` in PSU and `p ≈ z_model_m` in dbar (1 dbar ≈ 1 m).
- Clamp `T ← max(T, Tf + 1e-5 °C)` in wet cells only; the 1e-5 margin prevents
  float32 storage from rounding a few ULP below Tf. **Salinity unchanged.**
- Default ON; escape flag `--no-clamp-below-freezing`. Applied to **all four
  seasons**; clamp counts and max clamp are recorded in the statistics JSON
  and the NetCDF global attributes.

**Cells clamped (from the builder):**

| Season | Cells clamped | Max clamp |
|---|---|---|
| Jan | **12,589** | **+1.407 °C** |
| Apr | 2,525 | +0.257 °C |
| Jul | 0 | 0 |
| Oct | 553 | +0.372 °C |

**Verification:** 0 cells below Tf(S,p) in all 8 corrected products; Jan
minimum T is now −1.962 °C (was −3.28 °C). This is a physical correction
(supercooled seawater is unstable and would freeze), not a numerical hack.

---

## 4. Phase 3 — verification and regression

New `python/tests/ocean/test_en4_data_correction.py` (61 checks): existence,
z-grid, 0 below Tf, no sentinel zeros, units, masks, per-season metadata,
rebuild≡canonical, cross-season mask identity → **CLEAN** (0 warnings).
`data/validation/en4_correction_result.json`.

T0 test updated (pressure-aware Tf, density inversions reclassified as
physical INFO): **CLEAN — 95 checks, 79 PASS, 16 INFO, 0 WARNING, 0 FAIL**
(previously ISSUES_FOUND). `data/validation/en4_initial_result.json`.

| Check | Result |
|---|---|
| Full `fpm test` (clean) | exit 0 — **59/59** STOP-0, 0 failures |
| `ocean_init_test` (corrected anchors) | PASS |
| Strict build | exit 0 |
| ERA5 contract | 120/120 |
| Sea-ice/tides | 33, 0 errors |
| Provenance (runs with corrected data) | 28/28 |
| Ice coverage / sea-ice provenance | 16/16 / 8/8 |
| Snowfall (T-19) | CONFIRMED_12H |
| EN4 T0 / T3-PREP correction | **CLEAN / CLEAN** |
| ERA5 coverage (T0) | unchanged (T-21 accepted; H-2 for T4) |
| T1 spatial/temporal/wrap | WARNING / PASS / RED_CONFIRMED |
| T2 homogeneous / weak / conservation / compressibility | PASS / PASS / PASS / CRITICAL_CONFIRMED (expected) |
| `git diff --check` | clean |
| GitHub Actions | green on the pushed commit |

**Note on baselines:** pre-T3-PREP model runs used the old (wrong-grid)
shipped products. Their trajectories are **not directly comparable** to runs
after this correction; the archived products are kept only for forensics.

---

## 5. GO/NO-GO for T3 (Rest)

**GO for Stage 11.8.0 T3 (Rest — ocean without wind/fluxes)**: the EN4
initial data are now physically valid and on the model grid for all four
seasons.

Carried gates:
- **T-25 (CA in-situ criterion)** — T2-CORRECTIVE, **before T6** (requires
  D-33 branch decision). T3 results must be interpreted with it in mind.
- **H-2 (wind rotation)** — **T4** blocker.
- **T-23 (ERA5 wrap)** — T1-CORRECTIVE, before T4.
- **T-27 (f32 state in f64 CA)** — documented; part of T2-CORRECTIVE scope.

## 6. Confirmations

- No physics, EOS formula, scheduler or numerical operator modified;
  `EOS_MODE=LEGACY` default untouched.
- T-25, T-23 and H-2 were **not** fixed (scheduled only).
- T3–T6 not started; 11.7E.5/Stage 12 not started.
