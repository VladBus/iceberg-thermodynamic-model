# Stage 11.11 — Physical Validation & Tide Integration

**Status:** **PARTIAL / NO-GO for Stage 12** — RO and S/T limits verified;
N=24 thermodynamic run stable; N² still negative at 4,627 wet interfaces;
FES2014 atlas absent, so real tides are not implemented.
**Date:** 2026-10-27
**Base:** `5ddf414`

## Phase 1 — Physical correctness

### RO_min units
`RO_min = -11.736` is a **kg/m³ anomaly** (`rho[g/cm³] − 1.02`, ×1000),
not g/cm³. At the minimum wet cell (k=0,i=103,j=25; 66.59°N,42.57°E):
- T=30.00 °C, S=16.94 PSU;
- **ρ_abs = 1008.264 kg/m³** (1.008264 g/cm³).
All wet cells have absolute density >1000 kg/m³. Evidence:
`data/validation/ro_min_verification.json`.

### S=0 at T<0
Wet-cell audit found **0** cells with S<0.1 PSU and T<0. The S=0 values in the
full file are dry/ghost cells, not liquid ocean. `STAGE1110_PHYSICAL_LIMITS`
now guards S<0.1/T<0 if it ever occurs; current run already passes:
`data/validation/physical_limits_test.json`.

### Stratification
Potential-density N² using EOS-80 at a common reference pressure:
- N² min = **−0.01568 s⁻²**;
- **4,627** wet interfaces below −1e-6 (of 142,246).
**FAIL** — this remains a real physical-validation issue, concentrated near
the surface/boundary after hard T/S clipping. Evidence:
`data/validation/stratification_verification.json`.

## Phase 2 — Tides
- `data/input/processed/tides/tides.nc` is **null-tides** (all amplitudes and
  phases zero; `tidal_status=null-tides`).
- No FES2014/TPXO atlas exists locally; no download credentials/data were
  available. The extraction script was **not fabricated** and no synthetic
  “FES” dataset was substituted.
- The existing `test_tide_propagation.py` remains intentionally RED, and the
  prior plan is retained in `docs/TIDES_IMPLEMENTATION_PLAN.md`.
- Therefore tidal forcing is **NOT implemented** and the 0.5–1.0 m boundary
  signal is **not demonstrated**.

`data/validation/n24_30day_final_with_tides.json` records
`tides_available=false` and references the no-tide stable run; it is **not**
claimed as a tide validation.

## Phase 3 — Final ocean validation (no tides)
The stable N=24 30-day run (`obc_n24_thermo_30d`) has:
- 0 NaN, max U 1.999 m/s, CFL 0.518;
- T −1.94…30 °C, S 0…37.05 PSU;
- KE decays after day 10.
It does **not** include tides and N² fails the requested threshold.
Evidence: `data/validation/n24_30day_thermo_rewrite_results.json`.

## Phase 4-5 — Regression/docs
- Full `fpm test`: **67/67**.
- Strict build: exit 0.
- N=1 diagnostic with new switches OFF: 1-day, 0 NaN.
- `git diff --check`: clean.
- No EOS/iceberg code changed; no data deleted.

## GO/NO-GO for Stage 12
**NO-GO.** Two blockers remain: real FES2014/TPXO tidal forcing is absent, and
N² is below −1e-6 at 4,627 wet interfaces. Stage 12 implementation must not
start until these are resolved or explicitly accepted as limitations.
