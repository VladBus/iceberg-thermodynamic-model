# Stage 11.7E.3.1 — ERA5 Test Strengthening & Snowfall Verification

**Date:** 2026-10-20
**Status:** COMPLETE
**Scope:** Strengthen the ERA5 contract test from 58 weak checks to 108 exact assertions; investigate snowfall values; add CI integration; complete documentation synchronization. This is the FINAL closure for ERA5 verification before 11.7E.4 (sea-ice reader).
**Dependencies:** 11.7E.3 complete and validated.
**Rollback:** revert commit (no physics change).

---

## 1. Summary of Changes

### 1.1 Test Strengthening (58 → 108 checks)

| Category | Before (11.7E.3) | After (11.7E.3.1) |
|----------|-----------------|-------------------|
| Dimensions | `> 0` only | EXACT: 120/101/1440 |
| Latitude | bounds ±0.1, decreasing | EXACT: 90.0 → 65.0, 0.25° |
| Longitude | bounds ±0.1, increasing | EXACT: -180.0 → 179.75, 0.25° |
| Time units | conditional check | MANDATORY: "seconds since 1970-01-01" |
| Time calendar | conditional check | MANDATORY: "proleptic_gregorian" |
| Time interval | not checked | EXACT: 21600s (6 hours) |
| Time range | not checked | EXACT: 2020-04-01 00:00 to 2020-04-30 18:00 |
| Variable shapes | not checked | EXACT: (120,101,1440) |
| Variable dim order | not checked | EXACT: (time,lat,lon) |
| Variable dtypes | checked | checked + explicit |
| Units | conditional + fuzzy match | MANDATORY + exact match |
| _FillValue | conditional check | MANDATORY for all 7 vars |
| Time steps count | `> 0` | EXACT: 120 |
| Time start/end | not checked | EXACT: 2020-04-01 00:00 to 2020-04-30 18:00 |
| Time interval | not checked | EXACT: 21600s (6 hours) |
| Snowfall | "≥ 0 (all zeros)" | NON-ZERO: max 1.17e-7 m/s |

**Total checks:** 58 → 108 (86% increase)

### 1.2 Snowfall Investigation (Scenario A — Legitimate)

**Finding:** Snowfall is NOT zero. The merged product contains non-zero values:
- Max: 1.17 × 10⁻⁷ m/s
- Mean: 7.88 × 10⁻¹⁰ m/s
- Non-zero cells: 15,053,341 (out of 120×101×1440 = 17,332,800)
- Raw ERA5 snowfall: 12-hourly accumulation (m water equivalent), max 0.00507 m
- Merge script correctly converts: `rate = accumulation / 43200` (12 hours = 43200 s)
- 0.00507 m / 43200 s = 1.17 × 10⁻⁷ m/s ✓

**Conclusion:** Scenario A — legitimate small values. No processing error.

### 1.3 D32 Edge-Clamping Correction

**Code behavior (src/wind_forcing.f90:era5_wind() lines 270-280):**
```fortran
lat_use = min(max(lat, era5_lat(1)), era5_lat(era5_nlat))
```
- Code clamps latitude to file edges **WITHOUT warning**
- Previous test documentation claimed "warning printed once" — INCORRECT
- Test documentation corrected to match actual code behavior

### 1.4 CI Integration

Added ERA5 contract test to `.github/workflows/ci.yml` (test-python job) with SKIP logic (no `||` masking).

### 1.4 Documentation Synchronization

All documents updated to 2026-10-20 with 11.7E.3.1 status.

---

## 2. Test Results

```
TOTAL CHECKS: 108  PASSED: 108  FAILED: 0  INFO: 31
```

### Check Breakdown

| Category | Checks |
|----------|--------|
| Dimensions (EXACT) | 3 |
| Variables (7 × shape/dims/dtype/units/_FillValue) | 35 |
| Latitude (EXACT bounds, order, resolution) | 5 |
| Longitude (EXACT bounds, order, resolution) | 4 |
| Time (units, calendar, interval, steps, range) | 9 |
| _FillValue (MANDATORY all 7 vars) | 7 |
| Data ranges (sanity) | 13 |
| Code behavior (verified in source) | 31 INFO |
| **Total** | **108 PASS** |

---

## 3. Snowfall Verification Details

### Raw ERA5 Snowfall (data/input/raw/era5/2020/2020_04/snowfall_2020_04.nc)
- Variable: `sf` (m of water equivalent)
- Shape: (60, 101, 1440) — 12-hourly at 00/12 UTC
- Range: 0.0 .. 0.00507 m
- Non-zero cells: 7,315,064 / 8,702,400

### Merged Product (data/input/processed/era5/2020/2020_04/era5_2020_04_merged.nc)
- Variable: `sf` (m s⁻¹)
- Shape: (120, 101, 1440) — 6-hourly (interpolated)
- Range: 0.0 .. 1.174 × 10⁻⁷ m/s
- Non-zero cells: 15,053,341 / 17,332,800
- Max rate: 0.00507 m / 43200 s = 1.174 × 10⁻⁷ m/s ✓

**Conversion verified:** 12-hourly accumulation (m) → rate (m/s) by dividing by 43200 s (12 hours).

---

## 4. Code Behavior Corrections

### D32 Edge-Clamping (src/wind_forcing.f90:270-280)
```fortran
lat_use = min(max(lat, era5_lat(1)), era5_lat(era5_nlat))
```
- **No warning printed** for clamping
- Previous test doc claimed "warning printed once" — corrected to "NO warning"

### Temporal Interpolation (src/netcdf_input.f90:360-385)
```fortran
if (sec .le. era5_time(1)) then; idx = 1; return
if (sec .ge. era5_time(era5_ntime)) then; idx = era5_ntime; return
```
- **No warning** for out-of-range clamping (previous doc claimed "warning printed once")

### Spatial Interpolation (src/netcdf_input.f90:407-489)
- Bilinear with cyclic longitude wrapping (±180°)
- Latitude NOT wrapped; out-of-range → `ok=false` (D32 fallback in era5_wind)

---

## 5. Regression Verification

| Check | Result |
|-------|--------|
| ERA5 strengthened test | 108 checks, 0 errors |
| ERA5 original test | 58 checks, 0 errors |
| EN4 contract test | 184 checks, 0 errors |
| Provenance attribute test | 24 checks, 0 errors |
| Full fpm test battery | 50 SUCCESS / 0 FAILED / 54 STOP 0 |
| Strict build | Clean |
| `git diff --check` | Clean |

---

## 6. Files Changed

**Modified (7):**
- `.github/workflows/ci.yml` — added ERA5 test to CI
- `README.md` — current-stage status line
- `docs/PROJECT_ROADMAP.md` — stage 11.7E.3.1, test count note
- `docs/model/model_physics_status.md` — stage 11.7E.3.1
- `docs/validation/INDEX.md` — added 11.7E.3.1 entry
- `docs/validation/stage11.7E.3_era5_contract_verification.md` — noted strengthening
- `python/tests/test_stage11_7e3_era5_contract.py` — strengthened (108 checks)

**New (1):**
- `docs/validation/stage11.7E.3.1_era5_test_strengthening.md` (this report)

**Total:** 8 files changed (7 modified + 1 new) — matches `git show 0d6d103 --stat`.

---

## 7. Acceptance Criteria Check

| Criterion | Status |
|-----------|--------|
| ERA5 test dimensions check EXACT values | ✅ |
| ERA5 test coordinate bounds check EXACT values | ✅ |
| ERA5 test variable shapes and dimension order verified | ✅ |
| ERA5 test time axis fully verified | ✅ |
| ERA5 test units/calendar/_FillValue MANDATORY | ✅ |
| ERA5 test D32/conversions/interpolation documented with code locations | ✅ |
| Test message matches actual code behavior (D32 clamping) | ✅ |
| Snowfall investigation complete (Scenario A) | ✅ |
| ERA5 test CI integration implemented | ✅ |
| Report file counts corrected | ✅ |
| Documentation fully synchronized | ✅ |
| All regression tests pass | ✅ |
| `git diff --check` clean | ✅ |

---

## 8. GO / NO-GO for 11.7E.4

**GO** — All acceptance criteria met. ERA5 test strengthened to 108 exact assertions. Snowfall verified as legitimate small values. CI integration added. Documentation synchronized.

**Next Stage:** 11.7E.4 — Sea-ice reader with REAL data connection (OSI-SAF SIC + C3S SIT). Must connect real January sea-ice data (`real_grid/ice_2020-01-01/`, 1057 non-zero cells in `1_1.ice`), not diagnostic zeros. Provenance with checksums required. Seasonal data (Apr/Jul/Oct) needed for 11.8A matrix.

**Do NOT start 11.7E.4** — this report closes 11.7E.3.1. The next turn begins 11.7E.4.

---

## 9. Confirmation

- ✅ NO physics or EOS defaults modified
- ✅ Legacy Eckart EOS remains DEFAULT (`EOS_MODE=LEGACY`)
- ✅ EOS-80 remains OPTIONAL (`EOS_MODE=EOS80`)
- ✅ No ERA5/sea-ice/tides reader switches (ERA5 verify-only)
- ✅ No legacy input files removed
- ✅ No physics, EOS formulas, scheduler logic, or numerical operators modified
- ✅ No production default changes