# Stage 11.7E.2.1 — EN4 Contract Test Coverage Correction & OCEAN_INIT_MODE Fix

**Date:** 2026-10-18
**Status:** COMPLETE
**Scope:** Fix test coverage gaps and documentation inconsistencies identified in the 11.7E.2 audit. Make the verification match the claims.
**Dependencies:** 11.7E.2 complete and validated.
**Rollback:** revert commit (no physics change).

---

## 1. Summary of Changes

### 1.1 Code Changes (3 files)

| File | Change |
|------|--------|
| `src/initial_conditions.f90` | `OCEAN_INIT_MODE` renamed values: `STRICT` (default, FATAL on EN4 failure), `ALLOWED` (fallback to synthetic on EN4 failure), `FORCE_SYNTHETIC` (skip EN4 entirely). Default changed from `REAL` to `STRICT`. |
| `src/netcdf_output.f90` | Enhanced provenance metadata: `initialization_file`, `initialization_date`, `initialization_checksum`, `eos_mode` (LEGACY/EOS80), `scheduler_mode` (N=1/production) added as global NetCDF attributes. |
| `python/tests/test_stage11_7e2_en4_contract.py` | Complete rewrite: verifies ALL claimed fields (types, dimensions, coordinates, masks), proper wet cell counting via `water_column_levels`, explicit SKIP/FAIL behavior, check count reporting. |

### 1.2 OCEAN_INIT_MODE Behavior (Option B Implemented)

Three modes, verified working:

| Mode | Behavior | Default |
|------|----------|---------|
| `STRICT` | Read EN4, FATAL `stop 1` on failure (no fallback) | **YES** |
| `ALLOWED` | Read EN4, fallback to synthetic on failure with WARNING | No |
| `FORCE_SYNTHETIC` | Skip EN4 read entirely, always use synthetic with WARNING | No |

**Verification:**
- STRICT + missing file → FATAL with diagnostic ✅
- ALLOWED + missing file → WARNING + synthetic ✅
- FORCE_SYNTHETIC + missing file → WARNING + synthetic ✅
- STRICT + valid file → EN4 read successfully ✅
- FORCE_SYNTHETIC + valid file → skips EN4, uses synthetic ✅

---

## 2. Test Coverage Fixes (Phase 1)

### 2.1 Fields Now Verified (ALL claimed in report)

For EACH file (4 files × strict/shipped):
- ✅ Presence: `temperature_celsius`, `salinity_mass_fraction`, `density_anomaly_gcm3`, `wet_mask`, `water_column_levels`, `lat`, `lon`, `z_model_m`
- ✅ Data types: float32/float64/int8/int64 verified per variable
- ✅ Dimensions: (i=133, j=105, k=18) and per-variable dim tuples
- ✅ Coordinate ranges: lat ∈ [64,86], lon ∈ [5,80]
- ✅ `water_column_levels` used for bottom masking

### 2.2 Wet Cell Counting Correction

**Before:** Broadcast 2D `wet_mask` to all 18 levels → 199,206 "wet cells" per file (incorrect)
**After:** Use `water_column_levels` per column → **143,176 active 3D cells** per file (correct bottom masking)

Per-file counts now reported separately:
- Jan shipped: 143,176
- Apr shipped: 143,176
- Jan rebuild: 143,176
- Apr rebuild: 143,176

### 2.3 SKIP Behavior Fix

**Before:** Missing files → silent SKIP with exit 0
**After:**
- NO files found → "SKIP: no EN4 products available (expected in clean clone)" + exit 0
- PARTIAL files missing → "FAIL: partial EN4 products - N missing" + exit 1
- Files found → run ALL checks, report actual pass/fail counts

### 2.4 Check Count Reporting

**Output:** `FILES FOUND: 4  FILES MISSING: 0` / `TOTAL CHECKS: 172  PASSED: 172  FAILED: 0  INFO: 4`

---

## 3. Shipped File Verification (Phase 2)

**Default file path** (from `initial_ocean_reader.f90:26`): `data/input/processed/ocean/initial_ts_2020-01-01.nc`

**Status:** All 4 files present and verified:
- `initial_ts_2020-01-01.nc` (shipped, bilinear signature) ✅
- `initial_ts_2020-04-01.nc` (shipped, bilinear signature) ✅
- `initial_ts_2020-01-01_rebuild.nc` (STRICT compliant) ✅
- `initial_ts_2020-04-01_rebuild.nc` (STRICT compliant) ✅

**Report updated** to distinguish "Verified shipped files" vs "Verified rebuild files".

---

## 4. Documentation Cleanup (Phase 4)

### 4.1 KNOWN_ISSUES.md −20.07 Duplicates Removed
- Kept ONE historical note in "EN4 initial condition pathology" section
- Updated "Seasonal ocean stability" section to reference historical correction, current verified `ro_min = −0.02007`

### 4.2 INDEX.md Stale 11.2 Reference Fixed
- Stage 11.1 entry: "D-21: next = EN4 initial condition stabilization (Stage 11.2)" → "next = EN4 initial condition stabilization (Stage 11.2, pending)"
- Historical −20.07 clarified as unit conversion error

### 4.3 EOS-80 Wording Consistency

| Document | Fix |
|----------|-----|
| `model_description.md` §7.1 | "freezing-point calculation uses EOS-80 coefficients; complete EOS-80 density optional via `EOS_MODE=EOS80`; default LEGACY" |
| `KNOWN_ISSUES.md` N-09 | "EOS-80 density implemented as optional (`EOS_MODE=EOS80`); legacy Eckart default; TEOS-10 not implemented" |
| `DECISIONS.md` D-29 | Updated note: "11.7 now records `eos_mode` (LEGACY vs EOS80) as global NetCDF attribute" |

### 4.4 Provenance Enhancement (NetCDF Global Attributes)

Added to every output file:
- `initialization_file` — full path of EN4 input file
- `initialization_date` — file modification date (available/unavailable)
- `initialization_checksum` — MD5 of input file (available/unavailable)
- `eos_mode` — LEGACY or EOS80 (from `EOS_MODE` env)
- `scheduler_mode` — N=1 or production (from `STAGE115H_PRODUCTION` env)

---

## 5. Regression Verification (Phase 5)

| Check | Result |
|-------|--------|
| EN4 contract test (updated) | 172 checks, 0 errors, 4 INFO |
| Full fpm test battery | 50 SUCCESS / 0 FAILED / 54 STOP 0 |
| Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`) | Clean |
| `git diff --check` | Clean |
| OCEAN_INIT_MODE STRICT/ALLOWED/FORCE_SYNTHETIC | All 3 modes verified |

---

## 6. Acceptance Criteria Check

| Criterion | Status |
|-----------|--------|
| Test verifies ALL fields claimed in report | ✅ 172 checks |
| Wet cell count uses `water_column_levels` | ✅ 143,176 active 3D cells |
| Per-file and total active cell counts | ✅ Reported |
| SKIP behavior explicit (no silent PASS) | ✅ SKIP/FAIL distinction |
| Check count reported (X/Y/Z) | ✅ 172/172/0 |
| Shipped file verification status documented | ✅ 4/4 verified |
| OCEAN_INIT_MODE behavior clarified (Option B) | ✅ 3 modes verified |
| −20.07 duplicates removed | ✅ Single historical note |
| EOS-80 wording consistent | ✅ Across 3 docs |
| `initialization_source` enhanced with provenance | ✅ 5 new attrs |
| All regression tests pass | ✅ |
| `git diff --check` clean | ✅ |

---

## 7. Files Changed

**Modified (7):**
- `python/tests/test_stage11_7e2_en4_contract.py` (rewritten)
- `src/initial_conditions.f90` (OCEAN_INIT_MODE Option B)
- `src/netcdf_output.f90` (provenance enhancement)
- `KNOWN_ISSUES.md` (−20.07 dedup, EOS-80 N-09)
- `docs/validation/INDEX.md` (11.1 entry, 11.7E.2.1 entry)
- `docs/model/model_description.md` (EOS-80 §7.1)
- `docs/DECISIONS.md` (D-29 note update)

**New report:** `docs/validation/stage11.7E.2.1_test_coverage_correction.md` (this file)

---

## 8. Decisions Recorded

No new decisions (D-31 already recorded in 11.7E.2). D-29 note updated to reflect `eos_mode` now recorded in NetCDF output.

---

## 9. GO / NO-GO for 11.7E.3

**GO** — All acceptance criteria met. Test coverage now matches report claims, OCEAN_INIT_MODE behavior is explicit and verified, documentation is consistent, and provenance is enhanced.

**Next Stage:** 11.7E.3 — ERA5 Forcing Reader (verify-only). The chain (`src/netcdf_input.f90` + `src/wind_forcing.f90`) already reads merged ERA5 NetCDF; verify variable/dimension/time contract against 11.7A, add explicit dimension verification only if a gap is found. **No physics change.**

**Do NOT start 11.7E.3** — this report closes 11.7E.2.1. The next turn begins 11.7E.3.