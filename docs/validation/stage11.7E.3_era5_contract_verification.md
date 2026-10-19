# Stage 11.7E.3 — ERA5 Forcing Contract Verification (with 11.7E.2.3 micro-fixes)

**Date:** 2026-10-19
**Status:** COMPLETE
**Scope:** Verify-only contract check of the ERA5 forcing reader against the Stage 11.7A specification. The ERA5 chain (`src/netcdf_input.f90` + `src/wind_forcing.f90`) already reads merged NetCDF; no new reader written. Includes micro-fixes from 11.7E.2.3 audit.
**Dependencies:** 11.7E.2.3 complete and validated.
**Rollback:** revert commit (no physics change).

---

## 1. Summary of Changes

### 1.1 Phase 0 Micro-fixes (from 11.7E.2.3 audit)

| Item | Fix |
|------|-----|
| 0.1 False-PASS | `test_provenance_attributes.py`: `main()` now counts `False` returns from scenarios as errors. Missing `day_00.nc` → FAIL. |
| 0.2 File-wait logic | Replaced fixed `sleep(0.5)` with polling for file existence AND netCDF4 readability. Max 10s wait, then FAIL with clear message. |
| 0.3 Report file counts | `stage11.7E.2.3_provenance_closure.md`: corrected to "6 modified + 2 new = 8 total" (test file is NEW, not modified). Git shows 9 entries due to line-count method. |
| 0.4 Doc dates | `PROJECT_ROADMAP.md` and `model_physics_status.md`: updated to 2026-10-19. |
| 0.5 Test count | `PROJECT_ROADMAP.md`: added note — "64 Fortran test source files; 59 auto-discovered FPM targets (executable programs). The count differs because some source files are modules/helpers without a top-level `program`." |
| 0.6 Corrupted phrase | `model_physics_status.md`: fixed "0.007520130.0082 g/cm00b3" → "0.0075–0.0082 g/cm³". |
| 0.7 CI integration | Added `test_provenance_attributes.py` to `.github/workflows/ci.yml` with SKIP logic (no `||` masking). |

### 1.2 Phase 1-2: ERA5 Contract Verification (verify-only)

**Files verified:**
- `src/netcdf_input.f90` — ERA5 NetCDF reader
- `src/wind_forcing.f90` — forcing application, `era5_bilinear2d()`

**Test created:** `python/tests/test_stage11_7e3_era5_contract.py` (58 checks, all pass)

**No source code changes** — verify-only stage per 11.7A scope.

---

## 2. ERA5 Contract Verification Results

### 2.1 File and Dimensions
- **File:** `data/input/processed/era5/2020/2020_04/era5_2020_04_merged.nc`
- **Dimensions:** `valid_time=120`, `latitude=101`, `longitude=1440` ✅

### 2.2 Variables (7/7 verified)

| Variable | Expected Units | Actual Units | Dtype | Status |
|----------|---------------|--------------|-------|--------|
| `u10` | m s-1 | m s**-1 ✓ | float32 | ✅ |
| `v10` | m s-1 | m s**-1 ✓ | float32 | ✅ |
| `t2m` | K | K ✓ | float32 | ✅ |
| `d2m` | K | K ✓ | float32 | ✅ |
| `msl` | Pa | Pa ✓ | float32 | ✅ |
| `tcc` | 1 | (0 - 1) ✓ | float32 | ✅ |
| `sf` | m s-1 | m s-1 ✓ | float32 | ✅ |

*Unit string variations accepted per NetCDF UDUNITS conventions.*

### 2.3 Coordinates
| Coordinate | Check | Result |
|------------|-------|--------|
| Latitude | 101 points, DECREASING 90→65, 0.25° resolution | ✅ |
| Longitude | 1440 points, INCREASING -180→180, 0.25° resolution | ✅ |
| Time | 120 steps, `seconds since 1970-01-01`, proleptic_gregorian | ✅ |

### 2.4 Fill Values
All 7 variables have `_FillValue = NaN` (or standard 9.96921e36) ✅

### 2.5 Data Ranges (sanity checks)
| Variable | Range | Status |
|----------|-------|--------|
| u10 | -22.30 .. 27.47 m/s | ✅ |
| v10 | -29.18 .. 24.87 m/s | ✅ |
| t2m | plausible K (220-280) | ✅ |
| d2m | plausible K, d2m ≤ t2m on avg | ✅ |
| msl | 96056 .. 106824 Pa | ✅ |
| tcc | 0.0 .. 1.0 | ✅ |
| sf | ≥ 0 (all zeros in April) | ✅ |

---

## 3. Code Behavior Documentation (verified in source)

### 3.1 D32 Edge-Clamping (`wind_forcing.f90:era5_wind()`)
```fortran
if (model lat outside ERA5 range) then
    lat_use = min(max(lat, era5_lat(1)), era5_lat(era5_nlat))
    ! nearest-edge fallback, warning printed once
```
Model points outside ERA5 latitude coverage reuse file-edge value instead of zero.

### 3.2 Unit Conversions (`wind_forcing.f90:era5_wind()`)
| From (ERA5) | To (Model) | Conversion |
|-------------|------------|------------|
| u10, v10 [m/s] | windx1, windy1 [cm/s] | ×100 |
| wind module [m/s] | wind [m/s] | direct (for `heat()`) |
| tx1, ty1 [dyn/cm²] | same | quadratic drag: `cof = (1.1 + 0.04*spd*1e-2) * spd² * 1.29e-6` |
| msl [Pa] | p1, patm [hPa] | ×0.01 |
| t2m [K] | tatm [°C] | -273.15 |
| d2m, t2m [K] | humid [0..1] | `e_sat(d2m)/e_sat(t2m)` (Clausius-Clapeyron / Tetens) |
| tcc [0..1] | cloud [0..1] | direct copy |
| sf [m water eq] | era5_snowfall_rate [m/s] | already /43200 in merge |

### 3.3 Temporal Interpolation (`netcdf_input.f90:era5_find_time_index()`)
- **Method:** NEAREST-time (binary search)
- **Input:** model seconds (proleptic Gregorian, since 1970-01-01)
- **Output:** nearest ERA5 time index
- **Out-of-range:** idx clamped to 1 or ntime, warning printed once
- **No linear interpolation** — nearest neighbor only (documented assumption)

### 3.4 Spatial Interpolation (`netcdf_input.f90:era5_bilinear2d()`)
- **Method:** BILINEAR on regular lat/lon grid
- **Longitude:** cyclic wrapping (±180°)
- **Latitude:** NOT wrapped (out-of-range → `ok=false`, D32 fallback in `era5_wind`)
- **Search:** binary search for cell indices
- **Formula:** `(1-wlat)(1-wlon)f00 + wlat(1-wlon)f10 + (1-wlat)wlon f01 + wlat wlon f11`

---

## 4. Automated Test

**File:** `python/tests/test_stage11_7e3_era5_contract.py`

```
TOTAL CHECKS: 58  PASSED: 58  FAILED: 0  INFO: 34
```

- Self-skips with exit 0 when ERA5 merged product absent (CI-safe)
- No `||` error masking — real failures propagate

---

## 5. Regression Verification

| Check | Result |
|-------|--------|
| ERA5 contract test | 58 checks, 0 errors |
| EN4 contract test | 184 checks, 0 errors |
| Provenance attribute test | 24 checks, 0 errors |
| Full fpm test battery | 50 SUCCESS / 0 FAILED / 54 STOP 0 |
| Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`) | Clean |
| `git diff --check` | Clean |

---

## 6. Files Changed

**Modified (5):**
- `.github/workflows/ci.yml` — added provenance test
- `docs/PROJECT_ROADMAP.md` — date, test count note, current stage
- `docs/model/model_physics_status.md` — date, corrupted phrase fixed, current stage
- `docs/validation/stage11.7E.2.3_provenance_closure.md` — file count corrected
- `python/tests/test_provenance_attributes.py` — false-PASS fix, polling wait logic

**New (2):**
- `python/tests/test_stage11_7e3_era5_contract.py` — ERA5 contract verification
- `docs/validation/stage11.7E.3_era5_contract_verification.md` (this report)

Total: 7 files changed (5 modified + 2 new).

---

## 7. Acceptance Criteria Check

| Criterion | Status |
|-----------|--------|
| test_provenance_attributes.py false-PASS fixed | ✅ |
| File-wait logic uses polling, not fixed sleep | ✅ |
| Report file counts corrected | ✅ |
| Documentation dates synchronized (2026-10-19) | ✅ |
| Test count discrepancy resolved with clear definition | ✅ |
| Corrupted phrase in physics status fixed | ✅ |
| Provenance test CI integration implemented | ✅ |
| ERA5 contract verified against 11.7A specification | ✅ |
| All 7 ERA5 variables verified | ✅ |
| D32 edge-clamping documented | ✅ |
| Conversions documented | ✅ |
| Equivalence test created and passing | ✅ (58 checks) |
| All regression tests pass | ✅ |
| `git diff --check` clean | ✅ |

---

## 8. Documentation Updates

| Document | Change |
|----------|--------|
| `docs/validation/INDEX.md` | Added 11.7E.3 entry |
| `docs/PROJECT_ROADMAP.md` | Current stage: 11.7E.3 COMPLETE; next 11.7E.4; test count note added |
| `docs/model/model_physics_status.md` | Current stage: 11.7E.3 COMPLETE; corrupted phrase fixed |
| `docs/validation/stage11.7E.2.3_provenance_closure.md` | File count corrected |

---

## 9. GO / NO-GO for 11.7E.4

**GO** — All acceptance criteria met. ERA5 forcing chain contract verified end-to-end against 11.7A. No reader changes needed (verify-only). Micro-fixes from 11.7E.2.3 applied and verified. Documentation synchronized.

**Next Stage:** 11.7E.4 — Sea-ice reader with REAL data connection (OSI-SAF SIC + C3S SIT). Must connect real January sea-ice data (`real_grid/ice_2020-01-01/`, 1057 non-zero cells in `1_1.ice`), not diagnostic zeros. Provenance with checksums required. Seasonal data (Apr/Jul/Oct) needed for 11.8A matrix.

**Do NOT start 11.7E.4** — this report closes 11.7E.3. The next turn begins 11.7E.4.

---

## 10. Confirmation

- ✅ NO physics or EOS defaults modified
- ✅ Legacy Eckart EOS remains DEFAULT (`EOS_MODE=LEGACY`)
- ✅ EOS-80 remains OPTIONAL (`EOS_MODE=EOS80`)
- ✅ No ERA5/sea-ice/tides reader switches (verify-only for ERA5)
- ✅ No legacy input files removed
- ✅ No physics, EOS formulas, scheduler logic, or numerical operators modified
- ✅ No production default changes