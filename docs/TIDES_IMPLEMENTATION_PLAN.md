# Tides Implementation Plan (Stage 11.10 → Stage 12)

**Status:** PLAN + RED TEST; tide forcing is **not yet integrated**.
**Date:** 2026-10-27
**Current state:** `data/input/processed/tides/tides.nc` is explicitly
**null-tides** (all amplitudes/phases zero; `tidal_status = null-tides`).
The legacy `GRM2` reader is not a production source.

## Objective

Provide a UTC-phase, SI-unit tidal boundary forcing on the model grid for
M2, S2, K1, O1 (optionally N2, K2, P1, Q1), applied at **every barotropic
step** in `shal()`.

## Data source

- Preferred: FES2014 NetCDF (or TPXO) amplitudes/phases.
- Required constituents: M2, S2, K1, O1; optional N2, K2, P1, Q1.
- Store on the model grid in `data/input/processed/tides/tides.nc`:
  - `constituent_name(const)`
  - `amplitude(const, j, i)` [m]
  - `phase(const, j, i)` [radians, UTC-referenced]
  - `qq(const)` [radians per barotropic step]
  - `reference_dt1_seconds`
  - provenance attributes: source, version, extraction checksum, timestamp.

## Implementation steps

1. Python extractor: `python/tides/extract_fes2014.py`
   - read FES2014/TPXO constituents;
   - bilinear/nearest interpolation to model `lon/lat` from `grid.nc`;
   - convert amplitude to metres and phase to radians;
   - write `tides.nc` with provenance and CF-1.10 attributes.
2. Fortran reader: replace the legacy `GRM2` block in `app/main.f90` with a
   NetCDF `tides.nc` reader; no env gate.
3. Forcing: compute the tidal elevation/velocity boundary phasor from
   `amplitude`, `phase`, and UTC model time; add to the barotropic forcing.
4. **Call cadence:** apply tidal boundary forcing in `shal()` on every
   barotropic step (`iii` loop), not in the daily ocean update.
5. Stability: run a synthetic 1 m M2 boundary experiment; verify phase speed
   `sqrt(gH)` and no boundary reflection with the OBC implementation.
6. Real-data validation: compare coastal tide-gauge/altimetry phase and
   amplitude before enabling tides by default.

## Red test

`python/tests/test_tide_propagation.py` is the red test for the target
behavior. It currently exits **RED** because `tides.nc` is null-tides and the
Fortran integration is absent. It is intentionally **not wired into CI** until
the real tide reader/forcing lands.

## Acceptance

- Nonzero M2/S2/K1/O1 amplitudes in `tides.nc`;
- UTC phase advances correctly with model time;
- 1 m M2 boundary wave propagates with phase speed ≈ `sqrt(gH)`;
- no reflection/amplification with the OBC;
- N=24 stability gate passes with tides enabled.
