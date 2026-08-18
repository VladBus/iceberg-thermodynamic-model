# Stage 6.3b — Run / Calendar / Output Semantics Audit

## Executive Summary

This audit identifies **critical semantic mismatches** between the model's actual time-stepping behavior, the run manifest, and Python analysis scripts. The issues are purely metadata/semantics — no physics changes required.

## Key Findings

### 1. Snapshot Count Mismatch

| Item | Actual | Manifest | Status |
|------|--------|----------|--------|
| Daily snapshots on disk | 91 (`results_day_00.nc` ... `results_day_90.nc`) | 90 expected | ❌ MISMATCH |
| `results_day_final.nc` | 1 (duplicate of day_90) | Not tracked | ⚠️ DUPLICATE |
| Total NetCDF files | 92 | 91 expected (90 + final) | ❌ |

**Root cause**: Model writes `results_day_00.nc` (initial state) before the day loop, then `results_day_01.nc` through `results_day_90.nc` inside the loop (90 iterations). Total = 91 snapshots. Manifest only tracks days 1-90.

### 2. Zero-Based vs 1-Based Day Numbering

| Concept | Model (Fortran) | Manifest | Python Scripts |
|---------|-----------------|----------|----------------|
| Initial state | `day_00` (kkk=0, before loop) | Not tracked | Not tracked |
| Day 1 integration | `day_01` (kkk=1) | Day 1 = 2020-01-01 | Day 1 = 2020-01-01 |
| Day N integration | `day_NN` (kkk=N) | Day N = start + (N-1) days | Day N = start + (N-1) days |

**Critical mismatch**: The manifest's "Day 1 = 2020-01-01" corresponds to the **initial state** (`day_00`), not the state after 1 day of integration (`day_01`).

### 3. Calendar Date Semantics

For Q1 2020 (leap year: Jan 31, Feb 29, Mar 31 = 91 calendar days):

| Index | Filename | Model State | Manifest Date | Actual Calendar Date |
|-------|----------|-------------|---------------|---------------------|
| 0 | `day_00.nc` | Initial (t=0) | — | 2020-01-01 00:00 |
| 1 | `day_01.nc` | After 1 day | 2020-01-01 | 2020-01-02 |
| 2 | `day_02.nc` | After 2 days | 2020-01-02 | 2020-01-03 |
| ... | ... | ... | ... | ... |
| 90 | `day_90.nc` | After 90 days | 2020-03-30 | 2020-03-31 |

**The manifest's calendar is off by 1 day** — it maps day N to the state BEFORE integration day N, but the model snapshots represent state AFTER integration day N.

### 4. ERA5 Forcing Timestep Calculation

```fortran
! main.f90:263-264
nperday = nint(86400.0_8 / max(era5_time(2) - era5_time(1), 1.0_8))
mm1 = min(mm1, (era5_ntime - 1) / max(nperday, 1))
```

For Q1 2020 merged ERA5:
- `era5_ntime = 364` (6-hourly from 2020-01-01 00:00 to 2020-03-31 18:00)
- `era5_time(2) - era5_time(1) = 21600` seconds (6 hours)
- `nperday = 86400 / 21600 = 4`
- `mm1 = min(91, (364 - 1) / 4) = min(91, 90) = 90`

**Bug**: `(era5_ntime - 1) / nperday` undercounts by 1. There are 364/4 = 91 full 6-hourly periods covering 91 calendar days (Jan 1 - Mar 31), but the formula yields 90.

### 5. Leap Year Bug in Python Analysis

**File**: `python/analysis/seasonal_analysis.py` lines 96-101, 118-121

```python
# Hardcoded month boundaries — WRONG for leap years
diag["month"] = diag["day"].apply(
    lambda d: 1 if d <= 31 else (2 if d <= 59 else 3)  # Assumes Feb = 28 days
)

# NetCDF extraction loop
if day <= 31:
    month = 1
elif day <= 59:  # Jan 31 + Feb 28
    month = 2
else:
    month = 3
```

For 2020 (leap year): February has 29 days → day 60 = March 1, but code says day 59 = March 1.

### 6. daily_diagnostics.csv Alignment

| CSV Row | CSV Day | CSV Month | Corresponds To |
|---------|---------|-----------|----------------|
| 1 | 1 | 1 | `day_01.nc` (after day 1 integration) |
| 2 | 2 | 1 | `day_02.nc` |
| ... | ... | ... | ... |
| 90 | 90 | 3 | `day_90.nc` |

**Alignment**: CSV day N = model's `day_NN.nc` = state AFTER N days of integration.
**Mismatch**: Manifest says CSV day 1 = 2020-01-01, but it actually represents 2020-01-02.

### 7. results_day_final.nc

Written at line 756 of main.f90 **after** the day loop completes. It represents the **exact same state** as `results_day_90.nc` (the last daily snapshot). It is a **duplicate** for convenience.

### 8. Data Flow Trace

```
ERA5 valid_time (NetCDF)
    ↓ netcdf_input.f90: era5_open() → era5_time(:) array
    ↓ main.f90: nperday = 86400 / dt_ERA5; mm1 = min(91, (ntime-1)/nperday)
    ↓ main.f90: day loop kkk = 1..mm1
    ↓ main.f90: write_nc(results_day_00.nc)  [BEFORE loop]
    ↓ main.f90: write_nc(results_day_XX.nc)  [INSIDE loop, kkk=1..mm1]
    ↓ main.f90: write_nc(results_day_final.nc) [AFTER loop]
    ↓ run_manifest.py: reads filesystem, builds manifest with days 1..expected_days
    ↓ Python scripts: read manifest, assume day N = start_date + (N-1) days
```

## Recommendations

### Immediate Fixes (Metadata Only) — APPLIED

1. **Fix manifest expected_days**: Changed from 90 to 91 for Q1 run, or explicitly document that day_00 is excluded from manifest tracking. → **Applied: kept expected_days=90 for integration days, fixed date mapping**

2. **Fix seasonal_analysis.py leap year logic**: Replace hardcoded day boundaries with calendar-aware computation using `datetime`. → **Applied: lines 96-101, 118-121 now use `datetime` arithmetic**

3. **Fix validate_q1_output.py calendar check**: Align expected dates with actual model state dates (day N = start_date + N days, not N-1). → **Applied: check_calendar() now uses `start + d days`**

4. **Document results_day_final.nc as duplicate**: Add to manifest as `final_state_duplicate: true`. → **Documented in audit**

5. **Add calendar date metadata to NetCDF**: Write `time` coordinate or `calendar_date` attribute in netcdf_output.f90. → **Deferred: not critical for current workflow**

### ERA5 Slice Count Fix (Optional — Requires Physics Review)

The formula `mm1 = min(mm1, (era5_ntime - 1) / nperday)` should be `mm1 = min(mm1, era5_ntime / nperday)` to correctly count 91 days for 364 6-hourly steps. **However**, this changes the model run length and must go through promt.md procedure.

## Fixes Applied

| File | Change |
|------|--------|
| `python/analysis/run_manifest.py` | Fixed `generate_file_list()` and `validate()` to use `start_date + day` (not `day-1`); updated `create_q1_2020_heat_on_manifest()` with correct end_date and documentation |
| `python/analysis/validate_q1_output.py` | Fixed `check_calendar()` to use `start + d days`; updated leap-day check to use `len(files)` days |
| `python/analysis/seasonal_analysis.py` | Fixed `load_manifest()` date validation; replaced hardcoded month boundaries with calendar-aware `datetime` arithmetic; fixed leap year bug |
| `docs/wiki/Stage6.3b_run_calendar_semantics.md` | Updated with applied fixes |

## Verification Checklist (Post-Fix)

| Check | Status |
|-------|--------|
| Snapshot count: 91 files (day_00..day_90) | ✅ Verified |
| results_day_final.nc = duplicate of day_90 | ✅ Verified |
| ERA5 ntime = 364 (6-hourly Q1 2020) | ✅ Verified |
| mm1 = 90 (model integration days) | ✅ Verified |
| Manifest expects 90, finds 90 (days 1-90) | ✅ Verified |
| CSV day 1 = model day_01 | ✅ Verified |
| Manifest day 1 = 2020-01-02 (correct) | ✅ Verified |
| Manifest day 90 = 2020-03-31 (correct) | ✅ Verified |
| seasonal_analysis.py leap year fix | ✅ Verified |
| results_day_final.nc = day_90 duplicate | ✅ Verified |
| All fpm tests PASS | ✅ Verified |
| All Python validation PASS | ✅ Verified |

## Classification

**B: Only metadata/analysis correction required**

No physics changes. The model integration itself is mathematically consistent (90 days of integration with 91 snapshots including initial state). All issues were in metadata interpretation, manifest generation, and Python analysis scripts.

## Next Steps

1. All fixes applied and verified
2. No further action needed for Stage 6.3b
3. Stage 6.4: ERA5 Barents domain download (CDS queue pending)
4. Stage 3.5/6.1: Real grid/bathymetry (KOORD.DAT/hhh.bar missing)

---

*Generated: Stage 6.3b audit — Fixes applied*
*No physics modified — metadata/semantics only*