# Stage 11.7E.2.3 — Provenance Path Fix, CI Error Propagation & Final Sync

**Date:** 2026-10-18
**Status:** COMPLETE
**Scope:** Fix remaining provenance correctness bug (initialization_file recorded default path even when override used), remove CI error masking, add automated provenance attribute tests, complete documentation synchronization. This is the FINAL closure for EN4 provenance work before proceeding to ERA5 verification (11.7E.3).
**Dependencies:** 11.7E.2.2 complete and validated.
**Rollback:** revert commit (no physics change).

---

## 1. Summary of Changes

### 1.1 Code Changes (3 modified + 1 new)

| File | Change |
|------|--------|
| `src/initial_ocean_reader.f90` | Added module variable `actual_file_read` (character(len=512), save). Set to `'NONE'` at routine entry; set to actual opened path on successful `nf90_open` in both env-override and default branches. Updated two diagnostic print statements to report `actual_file_read` instead of `realistic_ocean_file`. |
| `src/initial_conditions.f90` | In success branch, pass `trim(actual_file_read)` to `prov_set_initialization()` instead of `trim(realistic_ocean_file)`. Now `initialization_file` records the ACTUAL path successfully read (override or default), not the constant. |
| `python/tests/test_provenance_attributes.py` | **NEW** Automated test verifying NetCDF global provenance attributes at day_00 output. 4 scenarios: (1) Default STRICT, (2) Override STRICT (symlink with different name), (3) FORCE_SYNTHETIC, (4) EOS-80. Self-skips with exit 0 when prerequisites absent (CI-safe). 24 checks, 0 failures. |
| `.github/workflows/ci.yml` | Removed `|| (echo SKIP; exit 0)` error masking from EN4 contract test step. Test now self-handles SKIP (exits 0 when no products found). |

### 1.2 Provenance Path Fix — Before vs After

| Scenario | `initialization_file` Before (11.7E.2.2) | After (11.7E.2.3) |
|----------|------------------------------------------|-------------------|
| STRICT, no override | `data/input/processed/ocean/initial_ts_2020-01-01.nc` (default constant) | `data/input/processed/ocean/initial_ts_2020-01-01.nc` (actual path = default) ✓ |
| STRICT, with override | `data/input/processed/ocean/initial_ts_2020-01-01.nc` (WRONG — default constant) | **Override path** (e.g., `data/input/processed/ocean/initial_ts_2020-01-01_override.nc`) ✓ |
| ALLOWED fallback | `NONE` | `NONE` (unchanged) |
| FORCE_SYNTHETIC | `NONE` | `NONE` (unchanged) |

**Key fix:** The `initial_ocean_reader` module now exposes the path it actually opened via `actual_file_read`. `initial_conditions.f90` uses this for provenance recording.

---

## 2. CI Error Masking Removal

**File:** `.github/workflows/ci.yml` (line 110-117)

**Before:**
```yaml
python python/tests/test_stage11_7e2_en4_contract.py || (
  echo "EN4 contract test SKIPPED (products not available in CI)"
  exit 0
)
```

**After:**
```yaml
python python/tests/test_stage11_7e2_en4_contract.py
```

**Rationale:** The test itself (lines 290-297) already handles missing products correctly:
- If `FILES_FOUND == 0`: prints "SKIP: no EN4 products available" and exits 0
- If `FILES_MISSING > 0` but some found: exits 1 (partial = failure)
- If all found and checks pass: exits 0

Removing the `||` interception lets real failures propagate. No other `||` masking patterns found in ci.yml.

---

## 3. Automated Provenance Attribute Tests

**File:** `python/tests/test_provenance_attributes.py` (NEW)

### 3.1 Test Scenarios

| Scenario | Env Overrides | Key Assertions |
|----------|---------------|----------------|
| 1. Default STRICT | `OCEAN_INIT_MODE=STRICT` | `init_source=EN4`, `init_file=default_rel`, `init_attempted=default_rel`, `mode_actual=EN4_REAL`, `eos_mode=LEGACY`, `scheduler_mode=N1_LEGACY` |
| 2. Override STRICT | `OCEAN_INIT_MODE=STRICT`, `ICEBERG_OCEAN_INIT_FILE=<symlink>` | `init_file=override_rel` (NOT default), `init_attempted=override_rel`, `mode_actual=EN4_REAL` |
| 3. FORCE_SYNTHETIC | `OCEAN_INIT_MODE=FORCE_SYNTHETIC` | `init_source=SYNTHETIC`, `init_file=NONE`, `init_attempted=SKIPPED_BY_MODE`, `mode_actual=SYNTHETIC` |
| 4. EOS-80 | `EOS_MODE=EOS80` | `eos_mode=EOS80` (other attrs same as default) |

### 3.2 Implementation Details

- Runs model binary directly (not via fpm) for speed; polls for `results_day_00.nc` (timeout 90s).
- Creates temporary symlink for override test (cleaned up after).
- Self-skips with exit 0 and clear message if: binary missing, KOORD.DAT/hhh.bar missing, EN4 file missing.
- Follows project test conventions: `PASS`/`FAIL`/`INFO` lines, summary `TOTAL CHECKS: N PASSED: N FAILED: N INFO: N`.

### 3.3 Results

```
TOTAL CHECKS: 24  PASSED: 24  FAILED: 0  INFO: 0
```

All 4 scenarios verified.

---

## 4. Documentation Synchronization

| Document | Change |
|----------|--------|
| `docs/PROJECT_ROADMAP.md` | Line 4: Current stage → 11.7E.2.3 COMPLETE. Line 6: Status updated. Stage 11.2 archive text (lines 395-411) prefixed with `> **HISTORICAL — SUPERSEDED:**` block. Added remediation note to Stage 11.9 closure criteria. |
| `docs/model/model_physics_status.md` | Line 4: Current stage updated to 11.7E.2.3 COMPLETE. |
| `docs/validation/stage11.7E.2.2_provenance_integrity.md` | Fixed section numbering (removed duplicate ##5, renumbered 6→11). Fixed code change count: "6 files + 1 new" → "4 modified + 1 new" (provenance.f90 was listed twice). |
| `docs/validation/INDEX.md` | Added 11.7E.2.3 entry (Phase 6.2). |

---

## 5. Regression Verification

| Check | Result |
|-------|--------|
| EN4 contract test | 184 checks, 0 errors (identical to 11.7E.2.2) |
| Provenance attribute test | 24 checks, 0 errors (new) |
| Full fpm test battery | 50 SUCCESS / 0 FAILED / 54 STOP 0 (identical to pre-change) |
| Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`) | Clean |
| `git diff --check` | Clean |
| Smoke tests (default + override STRICT, FORCE_SYNTHETIC, EOS-80) | All 4 scenarios verified via provenance test |

---

## 6. Files Changed

**Modified (7):**
- `.github/workflows/ci.yml`
- `docs/PROJECT_ROADMAP.md`
- `docs/model/model_physics_status.md`
- `docs/validation/stage11.7E.2.2_provenance_integrity.md`
- `src/initial_conditions.f90`
- `src/initial_ocean_reader.f90`
- `python/tests/test_provenance_attributes.py` (also modified — test file existed from this commit)

**New (1):**
- `docs/validation/stage11.7E.2.3_provenance_closure.md` (this report)

Total: 8 files changed (7 modified + 1 new).

---

## 7. Acceptance Criteria Check

| Criterion | Status |
|-----------|--------|
| `initialization_file` records ACTUAL path (including override) | ✅ |
| Smoke test with override path passes | ✅ (Scenario 2) |
| CI `||` masking removed for test steps | ✅ |
| CI behavior documented (SKIP in clean clone, FAIL on real errors) | ✅ |
| Provenance attribute test created and passing | ✅ (24 checks) |
| PROJECT_ROADMAP.md line 6 updated | ✅ |
| model_physics_status.md updated | ✅ |
| Stage 11.2 archive text marked SUPERSEDED | ✅ |
| Remediation note added for 11.8A failure case | ✅ |
| All regression tests pass | ✅ |
| `git diff --check` clean | ✅ |

---

## 8. Decisions Recorded

- **D-31 (reaffirmed):** Provenance metadata records actual state. `initialization_file` now correctly reflects override path. CI error masking removed per "fail fast" principle. Automated attribute tests added for regression protection.

---

## 9. GO / NO-GO for 11.7E.3

**GO** — All acceptance criteria met. The EN4 provenance chain is now correct end-to-end:
- `initialization_file` = actual path read (fixes the override-path bug)
- `initialization_attempted_file` = path attempted (for debugging)
- `initialization_mode_actual` = explicit mode outcome
- `eos_mode` / `scheduler_mode` = from actual module state
- CI propagates real failures
- Automated tests protect against regression
- Documentation synchronized

**Next Stage:** 11.7E.3 — ERA5 Forcing Reader (verify-only). The chain (`src/netcdf_input.f90` + `src/wind_forcing.f90`) already reads merged ERA5 NetCDF; verify variable/dimension/time contract against 11.7A, add explicit dimension verification only if a gap is found. **No physics change.**

**Do NOT start 11.7E.3** — this report closes 11.7E.2.3. The next turn begins 11.7E.3.

---

## 10. Confirmation

- ✅ NO physics or EOS defaults modified
- ✅ Legacy Eckart EOS remains DEFAULT (`EOS_MODE=LEGACY`)
- ✅ EOS-80 remains OPTIONAL (`EOS_MODE=EOS80`)
- ✅ No ERA5/sea-ice/tides reader switches
- ✅ No legacy input files removed
- ✅ No physics, EOS formulas, scheduler logic, or numerical operators modified
- ✅ No production default changes