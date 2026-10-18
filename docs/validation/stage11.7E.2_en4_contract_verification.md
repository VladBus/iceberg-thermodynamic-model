# Stage 11.7E.2 — EN4 Ocean-Initialization Contract Verification & Synthetic Fallback Elimination

**Date:** 2026-10-18
**Status:** COMPLETE
**Scope:** Verify the EN4 ocean-initialization variable/dimension contract against 11.7A; eliminate the silent synthetic T/S fallback from production; add `initialization_source` global output attribute.
**Dependencies:** 11.7E.1 complete and validated (grid/bathymetry reader switch; plan/contract corrections; T-18 reclassification; precheck + manifest validation fixes).
**Rollback:** revert commit (no new behavior path; synthetic remains available via explicit `OCEAN_INIT_MODE=SYNTHETIC`).

---

## 1. Summary of Changes

### 1.1 Code Changes (4 files)

| File | Change |
|------|--------|
| `src/initial_ocean_reader.f90` | `read_initial_ts` signature extended with optional `errmsg` (character(len=*), intent(out), optional). Failure reasons now explicit: env open, file not found, nf90_open, dim i/j/k + lengths, dims mismatch, get T/S, NaN, out-of-range. Docstring rewritten: no implicit fallback; `OCEAN_INIT_MODE` governs only on reader failure. |
| `src/param.f90` | Added `ocean_init_source` (character(len=16), default `'UNSET'`) after `era5_input_file` for output metadata. |
| `src/initial_conditions.f90` | `init_ocean()`: reads `OCEAN_INIT_MODE` (default `REAL`, case-insensitive via new `upper_ascii()`), calls `read_initial_ts(..., errmsg)`. Success → `ocean_init_source='EN4'` (drift 0.20/0.10 cm/s kept). Failure → if `SYNTHETIC`: explicit WARNING + `ocean_init_source='SYNTHETIC'` + synthetic fill; else `REAL`: FATAL `stop 1` with diagnostic (reason, expected file, `ICEBERG_OCEAN_INIT_FILE` override, synthetic test command, build product). Legacy "Warning: realistic ocean T/S unavailable, using SYNTHETIC fields" removed. |
| `src/netcdf_output.f90` | Global attribute `initialization_source = trim(ocean_init_source)` added to every output file. |

### 1.2 Design Decision (b) Confirmed by Smoke Tests

**Reader-first, mode-on-failure:** The EN4 reader is ALWAYS attempted first. `OCEAN_INIT_MODE` only matters when the reader fails.

- Smoke A: `REAL` default + missing file → FATAL + reason "nf90_open failed for ICEBERG_OCEAN_INIT_FILE=..." + guidance + STOP 1 (exit=1) ✅
- Smoke B: `OCEAN_INIT_MODE=SYNTHETIC` + missing file → WARNING printed, ran to day 49 (timeout) ✅
- Smoke C: `OCEAN_INIT_MODE=synthetic` (lowercase) + real file present → "read 143422 wet T/S cells" + ">>> Realistic ocean T/S applied" → EN4 wins (case-insensitive parse) ✅

No stray model processes.

---

## 2. EN4 Contract Verification (Phase 3)

**Tool:** `python/tests/test_stage11_7e2_en4_contract.py` (strict vs shipped families)
**Result:** rc=0, **TOTAL CHECKS: 56 ERRORS: 0 INFO: 4**
**Evidence:** `data/runs/stage117e2_evidence/en4_contract_check.txt`

### 2.1 Contract Findings

| Aspect | Specification | Verified |
|--------|---------------|----------|
| Dimensions | i=133, j=105, k=18 | ✅ |
| Wet mask | (i,j) int8 | ✅ |
| T/S/density_anomaly | (i,j,k) float32 | ✅ |
| Lat/Lon | (i,j) float64 | ✅ |
| z_model_m | (k,) float64 | ✅ |
| water_column_levels | (i,j) int64 | ✅ |
| Wet cells | 199,206 (Jan+Apr combined); 11,067 wet columns | ✅ |
| Range guards | T∈[−10,40] °C, S∈[−0.002,0.1] mass fraction | ✅ |
| Land/bottom fill | 0.0, never NaN | ✅ |
| Reader reads | 143,422 wet T/S cells from Jan | ✅ |

### 2.2 Shipped vs Rebuild Products

| Product | z_model_m | Dry cells | Status |
|---------|-----------|-----------|--------|
| `initial_ts_2020-01-01.nc` (Aug 30) | Bilinear: [2.5,5,7.5,12.5,17.5,25,40,50,62.5,75,100,125,175,225,275,350,450,550] | 52,164 nonzero | Documented valid (§11 11.4) |
| `initial_ts_2020-04-01.nc` (Sep 25) | Bilinear signature | 0 | Documented valid |
| `initial_ts_2020-01-01_rebuild.nc` (Oct 6) | **STRICT**: `DATA z`/100 = [2.5,5,10,15,20,25,30,40,50,75,100,150,200,250,300,400,500,600] | 0 | STRICT compliant |
| `initial_ts_2020-04-01_rebuild.nc` (Oct 6) | STRICT | 0 | STRICT compliant |

**Key Finding:** The 11.7A clause "z_model_m ≡ DATA z (cm→m) elementwise" is **false for shipped bilinear products** but **true for rebuild products**. The reader never reads `z_model_m` or `wet_mask` → **runtime contract unaffected**. Reported as INFO, not FAIL.

**Provenance:** `e735c51` (Stage 11.4 D-21 fix of `d_en4` metre units + `Z_M` shadowing) fixed it; regression introduced by `0b673ff` (2026-09-26 `zm = Z_M[k]*100.0`). `build_initial_ts.py` Z_CM = [250,500,1000,1500,2000,2500,3000,4000,5000,7500,10000,15000,20000,25000,30000,40000,50000,60000], Z_M = Z_CM/100 (line 73).

**Amendment:** Added to `docs/validation/stage11.7A_netcdf_contracts_preflight.md` (see Amendment §11.7E.2).

---

## 3. Regression Verification (Phase 6)

**Script:** `data/runs/scripts/117e2_verify.sh` (4 tags, fresh run IDs `stage117e2_<TAG>`)

| Tag | Env | ERA5 | Ocean Init | Status |
|-----|-----|------|------------|--------|
| JANOFF | `STAGE117E_NETCDF_GRID=false` | `era5_2020_01_fullcoverage_merged.nc` | `*_rebuild.nc` | INIT-OK, exit 0 |
| JANON | `STAGE117E_NETCDF_GRID=true` | `era5_2020_01_fullcoverage_merged.nc` | `*_rebuild.nc` | INIT-OK, exit 0 |
| APROFF | `STAGE117E_NETCDF_GRID=false` | `era5_2020_04_merged.nc` | `*_rebuild.nc` | INIT-OK, exit 0 |
| APRON | `STAGE117E_NETCDF_GRID=true` | `era5_2020_04_merged.nc` | `*_rebuild.nc` | INIT-OK, exit 0 |

**Comparison:** `data/runs/scripts/117e2_compare_vars.py` (variable-level bit-identity via numpy/netCDF4 against baselines `stage11.7E_<TAG>`)

- Files compared: 126 (JANOFF/JANON: 32 each; APROFF/APRON: 31 each — Apr ERA5 limits to 29 model days)
- Data mismatches: **0**
- Global attribute diffs: **0** unexpected; only new `initialization_source = "EN4"` (verified)
- Result: **PASS**

**Evidence:** `data/runs/stage117e2_evidence/variable_level_comparison.txt`

---

## 4. Full Test Battery

**Command:** `rm -rf build && fpm test --flag "-I/usr/include"`
**Result:** **50 SUCCESS / 0 FAILED / 54 STOP 0 / 0 STOP 1**
**Baseline comparison:** Identical to `data/runs/stage117e1cp_battery.log` (50/54/0)

---

## 5. Strict Build

**Command:** `rm -rf build && fpm build --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"`
**Result:** Project compiled successfully, no warnings-as-errors.

---

## 6. Git Diff Check

**Command:** `git diff --check`
**Result:** Clean (no whitespace errors).

---

## 7. Documentation Updates

- `docs/PROJECT_ROADMAP.md`: date 2026-10-18; 11.7E.2 COMPLETE; test count 64; sea-ice wording corrected; 11.7F moved after 11.8A/11.8B; 11.9 criteria expanded.
- `docs/model/model_description.md`: sea-ice bullet corrected; test count 64.
- `docs/model/model_equation_ledger.md`: test count 64 with as-of note.
- `AGENTS.md`: dead ref `stage11_modernization_plan.md` → `PROJECT_ROADMAP.md`; test count 64.
- `.github/workflows/ci.yml`: test count 64.
- `README.md`: current stage → 11.7E.2 COMPLETE, NEXT 11.7E.3.
- `docs/DECISIONS.md`: D-29 clarification (11.7 records `initialization_source` not `EOS_MODE`); D-31 added (fallback elimination).
- `KNOWN_ISSUES.md`: Production ocean stability blocker entry added (55/360 steps; N=1 stable ≠ viability).
- `docs/validation/stage11.7A_netcdf_contracts_preflight.md`: Amendment §11.7E.2 on shipped bilinear signature vs STRICT rebuild.
- `docs/validation/INDEX.md`: Stage 11.7E.2 row added.

---

## 8. Acceptance Criteria Check

| Criterion | Status |
|-----------|--------|
| EN4 contract verified vs 11.7A | ✅ 56 checks, 0 errors |
| Silent synthetic fallback removed | ✅ FATAL in REAL mode; explicit SYNTHETIC opt-in |
| `initialization_source` global attribute added | ✅ `EN4` / `SYNTHETIC` |
| Jan/Apr regression NDIFF=0 vs 11.7E baselines | ✅ 126 files, only new global attr |
| Battery 50/0 | ✅ |
| Strict build clean | ✅ |
| `git diff --check` clean | ✅ |
| No physics change | ✅ |

---

## 9. Decisions Recorded

- **D-29 (clarified):** EOS-80 stays OPTIONAL; 11.7 records `initialization_source` (EN4 vs SYNTHETIC) but NOT `EOS_MODE`; EOS default decision remains at 11.8A.
- **D-31 (new):** Silent EN4 synthetic fallback removed; EN4 failure is FATAL by default; synthetic only via explicit `OCEAN_INIT_MODE=SYNTHETIC`.

---

## 10. Next Stage

**Stage 11.7E.3 — ERA5 Forcing Reader (verify-only):** The chain (`src/netcdf_input.f90` + `src/wind_forcing.f90`) already reads merged ERA5 NetCDF; verify variable/dimension/time contract against 11.7A, add explicit dimension verification only if a gap is found. No physics change.

---

## GO / NO-GO for 11.7E.3

**GO** — All acceptance criteria met. No blockers. The EN4 contract is verified, the silent fallback is eliminated, regression is clean, and documentation is synchronized.

**Do NOT start 11.7E.3** — this report closes 11.7E.2. The next turn begins 11.7E.3.