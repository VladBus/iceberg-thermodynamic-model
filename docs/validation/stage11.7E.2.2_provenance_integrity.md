# Stage 11.7E.2.2 — Provenance Integrity & Contract Synchronization

**Date:** 2026-10-18
**Status:** COMPLETE
**Scope:** Fix provenance integrity issues identified in the 11.7E.2.1 audit. The current implementation recorded misleading or incorrect metadata that could compromise scientific traceability.
**Dependencies:** 11.7E.2.1 complete and validated.
**Rollback:** revert commit (no physics change).

---

## 1. Summary of Changes

### 1.1 Code Changes (6 files + 1 new)

| File | Change |
|------|--------|
| `src/provenance.f90` | **NEW** Shared module for initialization provenance state. Records actual initialization state (`initialization_source`, `initialization_file`, `initialization_attempted_file`, `initialization_mode_actual`). Provides pure getters for `netcdf_output`. Moved `upper_ascii` here. |
| `src/initial_conditions.f90` | Records actual provenance via `prov_set_initialization()`: `EN4_REAL`, `EN4_FALLBACK_SYNTHETIC`, `SYNTHETIC`, `EN4_FAILED_FATAL`. Enum validation for `OCEAN_INIT_MODE` (STRICT/ALLOWED/FORCE_SYNTHETIC). Tracks attempted file path. |
| `src/netcdf_output.f90` | Reads provenance from `provenance` module (not re-parsed env). Uses `equation_of_state:get_active_eos_mode()` and `stage115h_production:get_active_scheduler_mode()`. Removed `get_file_info` and `upper_ascii`. New attributes: `initialization_file`, `initialization_attempted_file`, `initialization_mode_actual`, `eos_mode`, `scheduler_mode`. |
| `src/equation_of_state.f90` | Added `get_active_eos_mode()` pure function returning `LEGACY` or `EOS80` from actual `eos80_mode` state. |
| `src/stage115h_production.f90` | Added `get_active_scheduler_mode()` pure function returning `N1_LEGACY` or `PRODUCTION_STALE` from actual `s115h_prod` state. |
| `src/provenance.f90` | **NEW** Shared provenance module (see above). |

### 1.2 Provenance Attributes — Before vs After

| Attribute | Before (11.7E.2.1) | After (11.7E.2.2) |
|-----------|-------------------|-------------------|
| `initialization_source` | `EN4` / `SYNTHETIC` | `EN4` / `SYNTHETIC` (unchanged) |
| `initialization_file` | Env var or default (misleading for FORCE_SYNTHETIC) | **Actual file successfully read**, or `NONE` |
| `initialization_date` | `"available"` / `"unknown"` | **REMOVED** (was misleading) |
| `initialization_checksum` | `"available"` / `"unavailable"` | **REMOVED** (was misleading) |
| `initialization_attempted_file` | — | **NEW**: Path actually attempted (for debugging) |
| `initialization_mode_actual` | — | **NEW**: `EN4_REAL`, `EN4_FALLBACK_SYNTHETIC`, `SYNTHETIC`, `EN4_FAILED_FATAL` |
| `eos_mode` | Re-parsed `EOS_MODE` env | **From actual `eos80_mode` state** |
| `scheduler_mode` | Re-parsed wrong env (`STAGE115H_PRODUCTION`) | **From actual `s115h_prod` state** |

---

## 2. OCEAN_INIT_MODE Behavior (Option B — Verified)

| Mode | Behavior | Verified |
|------|----------|----------|
| `STRICT` (default) | Read EN4, FATAL `stop 1` on failure | ✅ |
| `ALLOWED` | Read EN4, fallback to synthetic on failure with WARNING | ✅ |
| `FORCE_SYNTHETIC` | Skip EN4 entirely, always synthetic with WARNING | ✅ |

**Enum validation:** Invalid values → FATAL with clear error listing valid values.

---

## 3. Provenance Per Mode — Verified

| Scenario | `initialization_source` | `initialization_file` | `initialization_attempted_file` | `initialization_mode_actual` |
|----------|------------------------|----------------------|--------------------------------|------------------------------|
| STRICT + valid EN4 | `EN4` | actual path | actual path | `EN4_REAL` |
| STRICT + missing EN4 | (model stops) | `NONE` | attempted path | `EN4_FAILED_FATAL` |
| ALLOWED + valid EN4 | `EN4` | actual path | actual path | `EN4_REAL` |
| ALLOWED + missing EN4 | `SYNTHETIC` | `NONE` | attempted path | `EN4_FALLBACK_SYNTHETIC` |
| FORCE_SYNTHETIC | `SYNTHETIC` | `NONE` | `SKIPPED_BY_MODE` | `SYNTHETIC` |

**All 5 scenarios verified via smoke tests.**

---

## 4. EN4 Contract Test Strengthening (Phase 3)

**File:** `python/tests/test_stage11_7e2_en4_contract.py`

| Enhancement | Implementation |
|-------------|----------------|
| Active 3D cell count assertion | `check(total_active == 143176)` |
| `water_column_levels` range check | `check(wcl.min() >= 0 and wcl.max() <= 18)` |
| `wet_mask` ↔ `water_column_levels` consistency | `check(wet_mask == (wcl > 0))` |
| Core variable presence check | Early return with clear error if any missing |
| Check count reporting | `TOTAL CHECKS: 184  PASSED: 184  FAILED: 0  INFO: 4` |

**Result:** 184 checks (was 172), 0 errors, 4 INFO.

---

## 5. Documentation Synchronization

| Document | Change |
|----------|--------|
| `README.md` | Updated current stage to 11.7E.2.2; OCEAN_INIT_MODE docs updated |
| `docs/DECISIONS.md` (D-31) | Updated to reflect STRICT/ALLOWED/FORCE_SYNTHETIC, provenance fix, enum validation |
| `docs/PROJECT_ROADMAP.md` | Current stage: 11.7E.2.2 COMPLETE |
| `KNOWN_ISSUES.md` | Stage 11.1 entry marked SUPERSEDED; −20.07 clarified |
| `docs/validation/INDEX.md` | Added 11.7E.2.2 entry |
| `.github/workflows/ci.yml` | Added EN4 contract test (SKIPs if products absent) |

---

## 5. Regression Verification

| Check | Result |
|-------|--------|
| EN4 contract test | 184 checks, 0 errors |
| Full fpm test battery | 50 SUCCESS / 0 FAILED / 54 STOP 0 (identical to pre-change) |
| Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`) | Clean |
| `git diff --check` | Clean |
| Smoke tests (STRICT/ALLOWED/FORCE_SYNTHETIC) | All verified |
| Provenance attributes per mode | All 5 scenarios correct |

---

## 6. Files Changed

**Modified (11):**
- `.github/workflows/ci.yml`
- `KNOWN_ISSUES.md`
- `README.md`
- `docs/DECISIONS.md`
- `docs/PROJECT_ROADMAP.md`
- `docs/validation/INDEX.md`
- `python/tests/test_stage11_7e2_en4_contract.py`
- `src/equation_of_state.f90`
- `src/initial_conditions.f90`
- `src/netcdf_output.f90`
- `src/stage115h_production.f90`

**New (2):**
- `src/provenance.f90`
- `docs/validation/stage11.7E.2.2_provenance_integrity.md` (this report)

---

## 7. Acceptance Criteria Check

| Criterion | Status |
|-----------|--------|
| `initialization_source/file/mode_actual` reflect ACTUAL model state | ✅ |
| FORCE_SYNTHETIC records `initialization_file = "NONE"` | ✅ |
| ALLOWED fallback records correct attempted/actual files | ✅ |
| `initialization_date/checksum` removed (were misleading) | ✅ |
| `eos_mode` read from actual EOS module state | ✅ |
| `scheduler_mode` read from actual scheduler state | ✅ |
| `OCEAN_INIT_MODE` enum validation rejects unknown values | ✅ |
| EN4 test asserts computed metrics (cell count, level range) | ✅ |
| EN4 test handles incomplete files gracefully | ✅ |
| Documentation synchronized | ✅ |
| CI integration (SKIP if products absent) | ✅ |
| All regression tests pass | ✅ |
| `git diff --check` clean | ✅ |

---

## 8. Decisions Recorded

- **D-31 (updated):** Silent EN4 synthetic fallback removed; OCEAN_INIT_MODE = STRICT/ALLOWED/FORCE_SYNTHETIC; provenance metadata records actual state; enum validation added; provenance module created.

---

## 9. GO / NO-GO for 11.7E.3

**GO** — All acceptance criteria met. Provenance metadata now accurately reflects actual model state, OCEAN_INIT_MODE behavior is explicit and verified, test coverage is comprehensive, documentation is synchronized.

**Next Stage:** 11.7E.3 — ERA5 Forcing Reader (verify-only). The chain (`src/netcdf_input.f90` + `src/wind_forcing.f90`) already reads merged ERA5 NetCDF; verify variable/dimension/time contract against 11.7A, add explicit dimension verification only if a gap is found. **No physics change.**

**Do NOT start 11.7E.3** — this report closes 11.7E.2.2. The next turn begins 11.7E.3.

---

## 9. Confirmation

- ✅ NO physics or EOS defaults modified
- ✅ Legacy Eckart EOS remains DEFAULT (`EOS_MODE=LEGACY`)
- ✅ EOS-80 remains OPTIONAL (`EOS_MODE=EOS80`)
- ✅ No ERA5/sea-ice/tides reader switches
- ✅ No legacy input files removed
- ✅ No physics, EOS formulas, scheduler logic, or numerical operators modified
- ✅ No production default changes