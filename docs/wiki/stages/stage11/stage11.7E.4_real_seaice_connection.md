# Stage 11.7E.4 — Real Sea-Ice Connection

**Status:** COMPLETE (diagnostic/verification stage; no physics or EOS change)
**Switch:** `STAGE117E_NETCDF_SEAICE` (default OFF)
**Reader:** `src/netcdf_seaice_reader.f90`
**Builder:** `python/ice/build_seaice_nc.py`
**Artifact:** `data/input/processed/ice/seaice_initial.nc`

## 1. Scope

Connect the real January 2020 OSI-SAF SIC CDR (OSI-450-b v3.1) and C3S
CS2SMOS SIT product to the production sea-ice initialization path through an
env-gated NetCDF reader. The legacy `1_*.ice` path remains the default and is
not removed.

## 2. Data and manifest

- Real source: `data/input/generated/real_grid/ice_2020-01-01/1_1.ice` ..
  `1_5.ice`.
- Real manifest: `python/ice/seaice_source_manifest_real.json`
  (`source_type=scientific`, date `2020-01-01`, version
  `OSI-450-b CDR v3.1 / CS2SMOS v1.1`).
- Processed checksums and grid fingerprint are recorded in the manifest.
- NetCDF build: `wet cells=4402`, `total ice volume=2.334e+03 m3`,
  `max sic=0.9922999739646912`.
- The production manifest `python/ice/seaice_source_manifest.json` remains
  diagnostic; the real manifest is used explicitly for the real-data run.

## 3. Acceptance criteria (7-day window)

Forcing: `era5_2020_01_fullcoverage_gate7d.nc`.
Ocean init: `initial_ts_2020-01-01_rebuild.nc`.
Runs: `stage11.7E4_A7` (OFF, diagnostic zeros), `stage11.7E4_B7` (OFF, real
`1_*.ice`), `stage11.7E4_C7` (ON, real NetCDF).

| Criterion | Test | Result |
|---|---|---|
| A. Baseline reproduction | OFF zeros vs `stage11.7E_JANOFF`, days 0–7 | **PASS** — 0 differing variables on every day |
| B. Reader equivalence | ON real vs OFF real legacy, days 0–7 | **PASS** — 0 differing variables on every day |
| C. Scientific migration | ON real vs OFF zeros | **EXPECTED CHANGE** — real sea ice alters ice, T/S, density, velocity |

Criterion C day-1 maxima (ON vs OFF zeros): ice thickness `25.72 m`,
ice concentration `1.0`, temperature `2.141 °C`, salinity mass fraction
`0.01065`, density anomaly `8.581 kg m-3`, u `0.05545 m/s`, v `0.1248 m/s`.
The direction is consistent with adding real sea ice to a previously ice-free
initial state; this is a scientific change, not a numerics regression.

## 4. Defect found and fixed

The first B test failed: 15,477 ice-concentration cells and 11,606
ice-thickness cells differed, with thickness sums `5734.75` vs `4160.30 m`.
Root cause: the legacy Fortran reader reads one line per `i`
(`read (1,*) (an1(i,j,k), j=1,js1)`), so the text layout is `(IS1, JS1)`.
`read_ice_files()` was using `reshape((JS1, IS1)).T`, i.e. a transpose.

Fix: `reshape((IS1, JS1))`. After rebuilding the real NetCDF, B is
bit-identical for all 7 days. The test suite now writes builder outputs to a
temporary directory, so it cannot overwrite the production
`seaice_initial.nc`.

## 5. Ocean-stabilization gate

The production ocean remains unstable after `55/360` steps (NaN), as
documented in Stages 10.19–10.22 and 11.1–11.2. This stage does not fix that
blocker. The new roadmap section **Stage 11.8A Prerequisite: Production Ocean
Stabilization** records that a full 360-step no-NaN run is required before
11.8A seasonal validation. 11.7E.5 must not claim ocean-stable production.

## 6. Seasonal data gap

Only January 2020 real sea ice is local. April/July/October products were not
downloaded. 11.8A requires all four seasonal initial states; this remains an
explicit data gap.

## 7. Regression and constraints

- `python/tests/test_seaice_tides_nc.py`: **33 checks, 0 errors**.
- `python/tests/test_stage11_7e3_era5_contract.py`: **120 checks, PASS**.
- CI now fails if `python/tests/fixtures/era5_synthetic.nc` is missing.
- `fpm build --flag "-I/usr/include"`: PASS.
- No physics, EOS formula, scheduler, or numerical-operator change.
- `EOS_MODE=LEGACY` remains the default; EOS-80 was not promoted.
- Root `1_*.ice` symlinks remain diagnostic zeros and were restored after B.

## 8. Verdict

**GO for Stage 11.7E.5** (tides reader switch), with two carried constraints:
the ocean-stabilization gate (55/360) and the Jan-only seasonal data gap.
