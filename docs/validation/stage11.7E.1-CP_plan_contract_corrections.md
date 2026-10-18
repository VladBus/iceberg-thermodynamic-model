# Stage 11.7E.1-CP — Plan & Contract Corrections (pre-E.2 Audit and Fixes)

Frozen 2026-10-18. Correction and audit stage: closes the structural and
documentation issues identified in the Stage 11.7E audit BEFORE any further
reader switches. NO new reader switched (11.7E.2–E.5 NOT started); NO
production physics change; NO change to the EOS default (EOS_MODE=LEGACY
stays default, D-29); no scheduler/numerical-operator changes; no legacy
input files removed; no real sea-ice data connected to production; no new
data acquired. Default path (`STAGE117E_NETCDF_GRID` unset) bit-identical.

Spec (evidence copy): `data/runs/stage117e1cp_evidence/stage117e1cp_spec.txt`.
Base commit: `67928fa` (Stage 11.7E).

## 1. Roadmap restructuring (spec Phase 1)

`docs/PROJECT_ROADMAP.md`:

- Stage renamed: "11.7E" → **11.7E.1 — Grid/Depth Codes Reader Switch**
  (scope clarified: switches the SOURCE of grid coordinates FI/DL and
  depth codes KT1 from KOORD.DAT/hhh.bar to `grid.nc`; the model still
  derives ht/map1 with the existing `coup1()` algorithm — final
  bathymetry.nc fields are NOT read by the model).
- Explicit sub-stages added, each with Scope / Acceptance criteria /
  Dependencies / Rollback:
  - **11.7E.2** — Ocean Initial Reader (verify if needed; per audit the
    reader ALREADY reads NetCDF).
  - **11.7E.3** — ERA5 Forcing Reader (verify if needed; per audit the
    chain ALREADY reads NetCDF).
  - **11.7E.4** — Sea-Ice Reader Switch (legacy `1_*.ice` →
    `seaice_initial.nc`; real January data available from this audit,
    NOT connected before E.4).
  - **11.7E.5** — Tides Reader Switch (null-tides constants →
    `tides.nc`).
- 11.7F dependencies corrected: depends on **ALL of 11.7E.1–E.5** passing
  **PLUS an explicit production-default decision**; legacy removal is NOT
  automatic after a reader switch — legacy files must remain available
  for rollback until 11.7F explicitly removes them after full validation.

## 2. Ocean/ERA5 reader audit (spec Phase 2, Luna issue #3)

| Source | Reader | Format | Contract Match | Action Needed |
|--------|--------|--------|----------------|---------------|
| grid/bathy | `src/netcdf_grid_reader.f90` | NetCDF (`grid.nc`) | Yes (11.7E.1) | Done |
| ocean_init | `src/initial_ocean_reader.f90` | NetCDF — EN4 passthrough `initial_ts_2020-*.nc` | Yes (11.7A; dims via dimids i/j/k, axis-order-independent) | None — E.2 verify-only |
| forcing_era5 | `src/netcdf_input.f90` + `src/wind_forcing.f90` | NetCDF — merged CDS files | Yes (11.7A; `valid_time|time`, `latitude`, `longitude`; u10/v10/t2m/msl/d2m/tcc/sf; storage (nlat,nlon,ntime); lat-decreasing flip handled) | None — E.3 verify-only |
| seaice_init | thermodynamics (legacy text `1_*.ice`) | Legacy text | Yes (11.7D contract) | Switch needed (E.4) |
| tides | shallow_water (null-tides constants) | Legacy constants | Yes (11.7D contract) | Switch needed (E.5) |

Details:

- **ocean_init** (`src/initial_ocean_reader.f90`, written Stage 7.7): reads
  `initial_ts_2020-*.nc` via env `ICEBERG_OCEAN_INIT_FILE`; variable
  contract `temperature_celsius` / `salinity_mass_fraction`; dimensions
  resolved via `dimids` (axis-order-independent — no transpose issue);
  synthetic fallback when file absent; range checks (T [-10, 40] °C,
  S [-0.002, 0.1], NaN reject). This is why E.2 became verify-only.
- **forcing_era5** (`src/netcdf_input.f90`, consumed by `wind_forcing.f90`):
  reads merged ERA5 NetCDF from `data/input/processed/era5/...`; the D32
  nearest-edge fallback for edge cells is preserved (loader-only, no
  physics change).

## 3. Sea-ice data audit (spec Phase 3, Luna observation)

- Production placeholders `data/input/generated/real_grid/1_*.ice`:
  all-zero diagnostic (T-16). Verified: `1_1.ice` nonzero values = **0**.
- **Real January data EXISTS**: `data/input/generated/real_grid/ice_2020-01-01/`
  (produced by `python/ice/build_initial_ice.py`, functional). Verified:
  `1_1.ice` nonzero values = **1057** (vs 0 placeholder).
- Provenance (`reconstruction_metadata.json`):
  - SIC: OSI-SAF CDR v3.1 — `data/input/raw/ice/osisaf/ice_conc_nh_ease2-250_cdr-v3p1_202001011200.nc`
    (variable `ice_conc`, %, 25 km EASE2 432×432).
  - SIT: C3S CS2SMOS v1.1 — `data/input/raw/ice/c3s_sit/ice_thickness_nh_ease2-125_cs3smos-v1p1_20200101.nc`
    (variable `sea_ice_thickness`, m, ~12.5 km EASE2 864×864).
  - Category thicknesses [0.2, 0.4, 0.95, 1.6, 2.5] m; `ans_min_gate` 0.005;
    area/volume conservation contracts recorded.
- NOT connected to production (E.4 scope per spec). Seasonal (Apr/Jul/Oct)
  data still needed for 11.8A — recorded.

## 4. T-18 correction (spec Phase 4, Luna issue #4)

- **Verdict: standard netCDF-Fortran CDL→Fortran dimension-order
  convention, NOT a libnetcdff bug.** The reader already transposes
  back explicitly; the earlier "transpose quirk" wording was incorrect.
- Probe evidence (libnetcdff **4.9.3**, Feb 2026; binaries
  `probe117e.f90`, `probe3.f90`, outputs `probe_outputs.txt`):
  - `grid.nc` `kt1_raw` CDL dims (i=133, j=105): Fortran READ (105,133)
    st=0; reversed READ (133,105) fails with NETCDF_EEDGE st=-57.
  - `dimids` are reported in Fortran order (k=18, j=105, i=133); 3-D
    variables read as (18,105,133) — exactly matching Python ground truth.
- `KNOWN_ISSUES.md` T-18 rewritten: "Verified Python/C ↔ Fortran axis
  mapping in NetCDF reader", with the note that **new readers must verify
  dimensions explicitly, not assume buffer shape**.
- **Explicit dimension verification added** to `src/netcdf_grid_reader.f90`:
  `s117e_check_dims` queries each variable's dimensions and checks the
  Fortran view (j=js1, i=is1) against expectations; any deviation →
  `s117e_fatal_msg` FATAL with rollback hint. Applied to `kt1_raw`, `lon`,
  `lat`. Negative path verified by explicit branch inspection (not
  triggered on valid `grid.nc`).
- Post-edit re-verification: Jan ON/OFF NDIFF=0 over 32 nc files
  (`phase4_verify_summary.txt`).

## 5. Sea-ice test precheck fix (spec Phase 5, Luna issue #5)

`python/tests/test_seaice_tides_nc.py`:

- `_precheck_inputs()` now requires **ALL FIVE** `1_1.ice…1_5.ice` in the
  ACTUAL directory they are read from (`data/input/generated/real_grid/`).
  Root-level symlinks do NOT satisfy the check. Missing files → SKIP
  (exit 0) with the explicit list of absent files. `grid_dump_*.dat` is
  NOT checked (the test does not read it).
- Verified 4/4 cases (`phase5_6_verify_summary.txt`):
  nothing→rc 0; root-only→rc 0; one missing (`1_5.ice`)→rc 0 with explicit
  missing list; all five present→rc 2 (proceed).

## 6. Sea-ice manifest validation fix (spec Phase 6, Luna issue #6)

`python/ice/build_seaice_nc.py`:

- Schema validation BEFORE use: required fields `source_type`,
  `dataset_name`, `version`, `date`, `spatial_extent`, `temporal_coverage`.
  Any missing → `source = INCOMPLETE_MANIFEST` (SCIENTIFIC is never
  assigned without a complete manifest).
- `source_type="scientific"` additionally requires non-empty
  `dataset_name`, `version`, `date`.
- Manifest-to-input cross-check: if `input_checksums` are present in the
  manifest they are verified → mismatch gives `source = CHECKSUM_MISMATCH`;
  if absent, a `checksum_note` attribute records that integrity was not
  verified. `--manifest` CLI override added.
- Test verifies provenance attributes read back from the NetCDF
  (`source`, `sea_ice_status`, `checksum_note`) plus the
  incomplete-manifest case → `INCOMPLETE_MANIFEST` status. Python test
  now **25/25** (5 new provenance checks supersede the spec's 20/20
  expectation).

## 7. Rollback documentation (spec Phase 7, `docs/validation/stage11.7E_grid_bathymetry_reader_switch.md`)

- §6 **Rollback procedure**: `unset STAGE117E_NETCDF_GRID` → legacy path;
  no file moves, no rebuild needed (runtime switch; code paths coexist).
- §7.1 **Scope clarification**: grid/depth codes, not final bathymetry.
- §7.2 **Prerequisites for enabling NetCDF mode**: `grid.nc` must exist
  (built by `python/grid/build_grid_nc.py`); `bathymetry.nc` is a
  validated artifact, not read at runtime; missing `grid.nc` with the
  switch ON → FATAL with rollback hint (no silent fallback).
- §7.3 **Prerequisites for clean clone**: legacy files (KOORD.DAT,
  hhh.bar, 1_*.ice) are gitignored — run the README/AGENTS.md preparation
  steps and create root symlinks manually; NetCDF-mode inputs are
  unversioned as well — build them before enabling the switch.

## 8. Updated scope for 11.7E.2 (from audit findings)

Ocean-initial reader is ALREADY NetCDF — E.2 is **verify-only**:

- Verify the variable/dimension contract against 11.7A (EN4 passthrough);
  add explicit dimension verification only if a gap is found.
- Acceptance: contract verified (or gaps closed); Jan/Apr regression
  NDIFF=0; no physics change.
- Rollback: none applicable (no new behavior path); revert the commit if
  verification changes code.

## 9. Regression and verification (spec Phase 9 — actual counts)

| Check | Result | Evidence |
|-------|--------|----------|
| `fpm test` battery | **50 SUCCESS / 0 FAIL** | `data/runs/stage117e1cp_battery.log` |
| Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`) | clean, "Project compiled successfully" | `data/runs/stage117e1cp_strict.log` |
| Jan bit-identity (fresh): JANOFF ≡ stage11.5C_janOFF ≡ JANON | 32/32 files md5 IDENTICAL | `117e1cp_phase9_verify_final.txt` |
| Apr bit-identity (fresh): APROFF ≡ stage11.5D1_AprLegacy ≡ APRON | 31/31 files md5 IDENTICAL | `117e1cp_phase9_verify_final.txt` |
| NaN scan APROFF + APRON | 31 files each, 899 float vars, NaN_total = 0 | `117e1cp_phase9_nan_scan.txt` |
| Python test (with fixes) | **TOTAL CHECKS: 25 ERRORS: 0** (spec said 20/20 — superseded by +5 provenance checks) | `117e1cp_phase9_python_test.log` |
| `git diff --check` | clean | — |

Coexistence proof: OFF ≡ ON ≡ pre-edit ≡ baseline on both seasons — the
switch, the dim-check addition, and the precheck/manifest fixes changed
nothing in model output.

## 10. Acceptance checklist (spec)

1. Roadmap restructured: 11.7E → 11.7E.1, E.2–E.5 listed, F dependencies
   corrected — DONE (§1).
2. Ocean/ERA5 reader audit complete with findings table — DONE (§2).
3. Sea-ice data audit complete (real data existence documented) — DONE (§3).
4. T-18 description corrected (axis mapping, not library bug) — DONE (§4).
5. NetCDF grid reader verifies dimensions explicitly — DONE (§4).
6. Sea-ice test precheck checks ALL five files — DONE (§5).
7. Sea-ice manifest validation enforces complete schema — DONE (§6).
8. Test verifies provenance attributes — DONE (§6, 25/25).
9. Rollback documentation includes prerequisites for clean clone — DONE (§7).
10. All regression tests pass — DONE (§9).
11. GO/NO-GO for E.2 explicit with justified scope — DONE (§11).

## 11. GO/NO-GO for 11.7E.2

**GO — 11.7E.2 (verify-only).** Justification: ocean-initial reader
already reads NetCDF with an axis-order-independent contract; the only
E.2 work is contract verification against 11.7A (plus explicit dimension
verification if a gap is found), which is low-risk and does not switch
any source. No blocker found. Do NOT start 11.7E.2 in this stage.

## 12. Files + confirmation

- New: this report.
- Modified: `docs/PROJECT_ROADMAP.md` (restructure), `KNOWN_ISSUES.md`
  (T-18), `docs/validation/INDEX.md` (CP row),
  `docs/model/model_physics_status.md` (stage reference), `README.md`
  (current stage), `docs/validation/stage11.7E_grid_bathymetry_reader_switch.md`
  (§6/§7 amendments), `python/tests/test_seaice_tides_nc.py` (precheck +
  provenance checks), `python/ice/build_seaice_nc.py` (manifest
  validation), `src/netcdf_grid_reader.f90` (explicit dim verification).
- NO physics or production defaults modified: EOS stays LEGACY default
  (D-29); no reader switched beyond 11.7E.1 (already committed); no
  legacy files removed; sea-ice data NOT connected; no data acquired;
  default path bit-identical (§9).

Evidence directory: `data/runs/stage117e1cp_evidence/`
(`117e1cp_phase9_verify_final.txt`, `117e1cp_phase9_nan_scan.txt`,
`117e1cp_phase9_python_test.log`, `phase4_verify_summary.txt`,
`phase5_6_verify_summary.txt`, `probe_outputs.txt`, md5 snapshots,
spec copy). Battery/strict logs: `data/runs/stage117e1cp_battery.log`,
`data/runs/stage117e1cp_strict.log`.
