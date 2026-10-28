# Stage 11.11.2 — Heat-Source Forensics & Synthetic Tide

**Status:** PARTIAL / **NO-GO for Stage 12**.
**Date:** 2026-10-27
**Base:** `242f14b`

## Phase 1 — First hot-cell appearance

Existing N=24 30-day thermodynamic run:
- First T≥20°C: **day 10**, cell **k=0, i=1, j=93**
  (80.61°N, 19.53°E).
- T=**30.00°C**, S=**40.00 PSU** (both hard caps).
- Day 9 at the same cell: T=7.86°C, S=26.03 PSU.
- Day 0: T=−1.33°C, S=34.07 PSU.
- No hot cells on days 0–9.

Spatial pattern is a **lateral boundary/surface strip**, consistent with the
Sonnet P4 boundary-surface warning.

## Phase 2 — Sponge/climatology audit (H1/H2/H3)

- Sponge climatology is copied from the **initial T/S in °C**, not Kelvin:
  the boundary cell starts at −1.33°C, not 271–303.
- `t_clim` is allocated and initialized before use; no uninitialized-array
  failure was observed.
- Sponge indexing is consistent `(i,j,k)`; no transposition evidence.
- **H1 rejected**, **H2 rejected**, **H3 not supported**.

## Phase 3 — Flux/solver/OBC audit (H4/H5)

- Air temperature at the hot cell is Arctic (−14 to −15°C); no warm-air
  forcing.
- Heat-flux clipping is active; no direct >500 W/m² path was found.
- Boundary T/S advection has no separate source; the hot cell is at the
  surface boundary strip.
- Iterative post-flux potential-density mixing changes the 10-day behavior:
  the 10-day synthetic-tide control reaches **max T=12.61°C**, not 30°C.
- The exact source remains a boundary-surface heat/CA interaction, not a
  Kelvin/index bug. No new clipping/smoothing band-aid was added here.

## Phase 4 — Verification

- N=24 10-day with synthetic tides and iterative mixing:
  - 0 NaN;
  - max U **1.992 m/s**;
  - T −1.94…12.61°C;
  - S 23.38…35.40 PSU.
- **N² still fails:** min **−0.01639 s⁻²**, **9,813** wet interfaces
  <−1e−6. Iterative CA did not satisfy the physical stratification gate.
- 30-day tide validation not completed.

## Phase 5 — Synthetic tides

- M2 generated: amplitude **0.5 m**, period **12.42 h**, phase 0…π.
- Fortran NetCDF reader loads the synthetic file.
- Schema test (`test_tide_propagation.f90`) PASS.
- True 2D propagation/phase-speed validation and 30-day tidal signal remain
  **not validated**.

## Decision

**Stage 12: NO-GO.** N² remains unstable and the 30-day tide gate is
incomplete. N=1 remains diagnostic only.
