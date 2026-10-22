# Stage 11.8.0.0 — Diagnostic Contract Correction (Real Red Tests)

**Status:** COMPLETE
**Date:** 2026-10-22
**Base commit:** `8d4343d` (Stage 11.7E.4.1)
**Scope:** diagnostic correction only — no physics, EOS, scheduler, or snowfall-divisor change.

---

## 1. Objective

Replace the Stage 11.7E.4.1 stubs with real, executable diagnostics:

- the homogeneous-column test now calls the production Fortran
  `convective_adjustment::convect_column` core and reports measured ΔT/ΔS;
- the snowfall period is determined from the **source** ERA5 GRIB metadata,
  not the processed 6-hourly time axis;
- sea-ice provenance is read from the actual source file, not hardcoded;
- `sit` semantics are clarified and the ice-coverage test checks physical
  thresholds;
- the 25.72 m day-1 maximum is investigated and classified;
- the ocean stabilization gate is documented in the roadmap / known issues /
  decisions.

---

## 2. Phase 0 — Documentation and numbering corrections

| # | Correction | Result |
|---|------------|--------|
| 0.1 | Decision numbering | Confirmed actual IDs: **D-30 = eos_diag dispatcher**, **D-31 = EN4 fallback**, **D-32 = sea-ice switch**. Corrected the 11.7E.4.1 report misattribution (it had D-30/D-31 swapped). Added **D-33 = physics change policy** (legacy-frozen vs stage11-physics branches). |
| 0.2 | Outdated −20.07 g/cm³ | Replaced in `stage11.8.0_ocean_diagnostic_plan.md` with the historical-artifact clarification (Stage 11.1/11.4: sentinel/unit artifact of overwritten runs; current Day-0 files do not exhibit −20.07). Added T0 task to verify current seasonal T/S fields/units (2020-01/04/07/10). |
| 0.3 | Roadmap | Added Stage 11.8.0.0; marked 11.7E.5 **DEFERRED** (null-tides no scientific value; not blocked by 11.7F); clarified 11.7F dependency = “all readers switched OR explicitly deferred with justification”; current-stage pointer updated. |
| 0.4 | Report file count | Corrected 11.7E.4.1 report from “14 files” to the actual **17 files, +1174/−16** (commit `8d4343d`). |

Additional Phase 5 documentation completed here: `KNOWN_ISSUES.md` N-15
(ocean stabilization gate), `DECISIONS.md` D-29 (EOS-80 promotion requires
gate + seasonal matrix + observations) and D-33, roadmap “Stage 11.8
Prerequisite: Ocean Stabilization”.

---

## 3. Phase 1 — Real homogeneous-column test (T2 core)

**Files:**
- `test/test_homogeneous_column.f90` (production Fortran test; fpm target
  `test_homogeneous_column`)
- `python/tests/ocean/test_homogeneous_column.py` (driver; runs both EOS modes)

**What it actually does:** initializes T = 4.0 °C and S = 0.035 (35 PSU) at all
18 levels, calls `convect_column` from the production
`convective_adjustment` module, and measures the actual changes. The EOS mode
is selected through the existing `EOS_MODE` environment variable
(`eos80_configure`).

**Actual result (2026-10-22):**

| EOS mode | ΔT max | ΔS max | CA iterations | nmix | guard | status | process exit |
|----------|--------|--------|---------------|------|-------|--------|--------------|
| LEGACY (Eckart) | 0.0 | 0.0 | 1 | 0 | false | **PASS** | 0 |
| EOS80 (UNESCO) | 0.0 | 0.0 | 1 | 0 | false | **PASS** | 0 |

**Correction of the original premise:** a perfectly homogeneous column is
statically stable even with EOS-80 pressure dependence (constant T/S gives
monotonically increasing density with depth). Convective adjustment correctly
does nothing. The previous expectation that this test would FAIL was a false
premise; the CA defect requires a **weak real inversion** (the T2
analytical-mixing test in the 11.8.0 plan), not a homogeneous column. This is
recorded so the 11.8 red-test target is not misdirected.

Outputs: `data/validation/homogeneous_column_result.json`,
`homogeneous_column_fortran_LEGACY.json`, `homogeneous_column_fortran_EOS80.json`.

---

## 4. Phase 2 — Snowfall accumulation period (source metadata)

**Source examined:** `data/input/raw/era5/2020/2020_01/snowfall_2020_01_fullcoverage.nc`

Evidence:
- `GRIB_stepType = "accum"`
- `GRIB_stepUnits = 1`
- source `valid_time` has **62 times** for January, spacing **43200 s = 12 h**
- `sf` units = `m of water equivalent`; max = `0.0039649 m` per 12 h
- `startStep` / `endStep` / `stepRange` attributes are not present in the CDS
  NetCDF output; the 12 h period is established from the source time spacing
  and the accumulated-forecast type.

**Verdict: `CONFIRMED_12H` (SUPERSEDED by Stage 11.8.0.0.1 → INFERRED_12H;
step-range attributes are absent and the download script's hourly-step request
conflicts with the 12-hourly artifacts — see KNOWN_ISSUES T-19).** The divisor
`43200` in `python/era5/merge_snowfall.py` was **not changed**.

The processed merged file has 6-hourly spacing because `merge_snowfall.py`
interpolates onto the instantaneous ERA5 grid; that spacing is **not** the
accumulation period. The Stage 11.7E.4.1 “6 h mismatch” finding was based on
that artifact and is corrected here.

Output: `data/validation/snowfall_period_result.json`.

---

## 5. Phase 3 — Sea-ice provenance (actual source)

**Code changes:**
- `python/ice/build_seaice_nc.py` writes `manifest_version` and
  `source_manifest_checksum` (MD5 of the manifest file) into
  `seaice_initial.nc`.
- `src/netcdf_seaice_reader.f90`:
  - OFF → `seaice_reader_mode = "legacy"`,
    `seaice_source_file = "legacy_1_*.ice"`,
    `manifest_version = "NONE"`, `manifest_checksum = "NONE"`.
  - ON → reads `manifest_version` (fallback `dataset_version`) and
    `source_manifest_checksum` from the actual NetCDF file; records
    `seaice_reader_mode = "netcdf"` and the actual path.

**Verified in model output (day_00):**

| Mode | reader_mode | source_file | manifest_version | manifest_checksum |
|------|-------------|-------------|------------------|-------------------|
| ON | `netcdf` | `data/input/processed/ice/seaice_initial.nc` | `OSI-450-b CDR v3.1 / CS2SMOS v1.1` | `c3ca0b1ec8c03398fa7c6ad84b4cd466` |
| OFF | `legacy` | `legacy_1_*.ice` | `NONE` | `NONE` |

`test_seaice_provenance.py`: **8/8 checks pass**. `test_provenance_attributes.py`
now also verifies the four legacy attributes (28 checks total, all pass).

---

## 6. Phase 4 — SIT semantics, ice coverage, and the 25.72 m maximum

**SIT semantics:** `sit` is the **area-weighted thickness contribution**
`HST × sic`, not a single-category thickness. The builder now writes:

- `long_name = "Sea ice thickness contribution per category (thickness x concentration)"`
- `comment = "Area-weighted thickness contribution HST*sic, NOT single-category thickness; sum over categories is the column-equivalent ice thickness [m]."`

**Strengthened ice-coverage test:** 16/16 checks pass:

- max total concentration = `1.00000003` (float32; within `1 + 1e-6`)
- cells with ice = `4402 / 13965`
- max `sit` contribution = `1.58752 m` (HST max = 2.5 m)
- total ice volume = `4.502e+11 m³`
- per-category `sit` maxima: `[0.15488, 0.38792, 0.94268, 1.58752, 0.82000] m`
- `sit == HST*sic` for every category (float32 tolerance)
- legacy source non-zero (max concentration `0.9923`)

**25.72 m investigation:** the day-1 model output `ice_thickness` per-category
maxima are `[4.0268, 0.6944, 1.0118, 1.6952, 25.7246] m` (overall 25.725 m).
This field is `hice = wice1/anp` (per-category actual thickness), **not**
`sit`; the initial `sit` max is only `1.5875 m`. Therefore 25.72 m is not a
`sit` unit/aggregation error. It is a thermodynamic-growth defect: `wice1`
grows while the category area `anp` stays small, so `hice` exceeds the
physical category bound (category 1 reaches 4.03 m vs HMAX 0.3 m; category 5
reaches 25.72 m, within its nominal 50 m cap but physically implausible for
Arctic sea ice). Documented as a target for the 11.8 thermodynamic work; not
fixed here.

Output: `data/validation/ice_coverage_result.json`.

---

## 7. Phase 5 — Ocean stabilization gate

- `docs/PROJECT_ROADMAP.md`: new “Stage 11.8 Prerequisite: Ocean
  Stabilization” section — current 55/360 steps, mandatory full 360-step
  no-NaN gate, diagnostic ladder T0–T6, 365-day acceptance.
- `KNOWN_ISSUES.md`: **N-15** ocean stabilization gate; N=1 stability does
  not prove production viability.
- `docs/DECISIONS.md` **D-29**: EOS-80 promotion requires (a) the ocean gate,
  (b) the 11.8A seasonal matrix, (c) physical validation against observations.
- **D-33**: two-branch physics-change policy (`legacy-frozen` /
  `stage11-physics`) with explicit decision gate.

---

## 8. Phase 6 — CI integration

`.github/workflows/ci.yml` now runs:

- `fpm test --flag "-I/usr/include" --target test_homogeneous_column`
- `python python/tests/ocean/test_homogeneous_column.py`
- `python python/tests/ocean/test_snowfall_period.py`
- ice-coverage and sea-ice-provenance diagnostics when the local data bundle
  is present; otherwise an **explicit** `SKIP: ... data absent` message (not a
  silent skip).

No `||` error masking was added.

---

## 9. Phase 7 — Regression and verification

| Check | Result |
|-------|--------|
| `test_stage11_7e3_era5_contract.py` | 120/120 pass, 0 failed, 32 info |
| `test_seaice_tides_nc.py` | 33 checks, 0 errors (negative checksum case expected) |
| `test_provenance_attributes.py` | 28/28 pass (incl. 4 sea-ice legacy attrs) |
| `test_homogeneous_column.py` | LEGACY PASS ΔT=0 ΔS=0 exit 0; EOS80 PASS ΔT=0 ΔS=0 exit 0 |
| `test_snowfall_period.py` | CONFIRMED_12H; divisor unchanged |
| `test_ice_coverage.py` | 16/16 checks pass |
| `test_seaice_provenance.py` | 8/8 checks pass |
| Full `fpm test --flag "-I/usr/include"` | exit 0; 0 FAIL/ERROR STOP lines |
| Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`) | exit 0 |
| `git diff --check` | clean |

---

## 10. Deliverables

- `test/test_homogeneous_column.f90`
- `python/tests/ocean/test_homogeneous_column.py` (real driver)
- `python/tests/ocean/test_snowfall_period.py` (source metadata)
- `python/tests/ocean/test_ice_coverage.py` (thresholds + 25.72 m investigation)
- `python/tests/ocean/test_seaice_provenance.py`
- `data/validation/homogeneous_column_result.json`
- `data/validation/homogeneous_column_fortran_LEGACY.json`
- `data/validation/homogeneous_column_fortran_EOS80.json`
- `data/validation/snowfall_period_result.json`
- `data/validation/ice_coverage_result.json`
- `data/validation/snowfall_period_result.json`
- this report

---

## 11. GO/NO-GO for 11.8.0

**GO for Stage 11.8.0** (diagnostic ladder T0–T6 implementation).

Carried constraints:
- ocean stabilization gate: 55/360 steps before NaN; full 360-step no-NaN
  required before 11.8A;
- Jan-only real sea ice; Apr/Jul/Oct missing;
- `EOS_MODE=LEGACY` remains default; EOS-80 optional (D-29);
- snowfall divisor **not changed** (43200 confirmed correct from source);
- 11.7E.5 (tides) remains deferred.

**No physics, EOS formula, scheduler, numerical operator, or snowfall-divisor
change was made in this stage.**
