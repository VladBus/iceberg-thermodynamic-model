# Stage 11.8A Matrix Specification — Seasonal EOS × Scheduler

**Status:** COMPLETE — **8/8 N=1 cells PASS after T-41 gate correction**; **D-29 PROMOTED** (N=1 scope).
**Date:** 2026-10-26
**Config:** validated Stage 11.8 standard set (see below).

## Dimensions

| Axis | Values |
|---|---|
| EOS | LEGACY (primary), EOS80 (secondary) |
| Scheduler | N=1 legacy, PRODUCTION_STALE (24 fires/day ×24 passes, Δt_sub=150 s, shal 1×/day) |
| Season | Jan, Apr, Jul, Oct |
| Duration | 30 days per cell |

**Cells:** 2 EOS × 4 seasons = **8 N=1 cells** executed. The production
column is **BLOCKED**: Phase-1 analysis found a scheduler ice/cadence artifact
(production +65 % extent, −269 W/m² implied cooling); production runs are
diagnostic only until a scheduler fix. **Production scheduler ice climatology
is not validated; D-29 is based on N=1 only.**

## Standard configuration

`STAGE113_DT=1800`, `STAGE118_LAPLACIAN_VISC=ON`, `STAGE118_AH=10000`,
`STAGE118_RO_PROGNOSTIC=ON`, `STAGE118_CA_POTENTIAL=ON`,
`STAGE118_CA_F64_N2=ON`, `STAGE118_WIND_ROTATION=ON`,
`STAGE118_LON_CLAMP=ON`, `STAGE118_MONOTONE_ADVECTION=ON`,
`STAGE118_SPONGE_BOUNDARY=ON` (α=1/day), `STAGE118_DENSITY_REPAIR=ON`;
`EOS_MODE=LEGACY` or `EOS80` per cell; initial EN4 season; ERA5 season;
30 days; N=1 or production scheduler.

## Metrics and gates per cell

- NaN/Inf count (gate: 0).
- max |U|, |V|, |W|; KE day 0/15/30; KE30/KE15 (<5).
- T/S/RO bounds; **absolute density > 1.0 g/cm³** and S ≥ 0. Raw
  `density_anomaly` is kg/m³ and may be slightly negative for brackish water;
  it is a diagnostic, not a gate (T-41 correction).
- Conservation: volume 0; salt <1e-3; heat interpreted via T-34 surface-flux
  closure (not a literal zero-drift target).
- CA nmix + guard hits.
- Sea-ice: extent, volume, mean thickness where connected.
- Production cells: 720/720 fire-steps (360/360 canonical 12-step days).

## D-29 decision rule

EOS80 is promoted to default **only if**:
1. all EOS80 cells pass the gates;
2. EOS80 is demonstrably equivalent or better than LEGACY on a documented
   metric;
3. there is no interaction pathology with the production scheduler.
**Outcome:** all EOS80 cells pass the corrected absolute-density gate; EOS80 is
equivalent on dynamics and uses fewer CA mixings → **D-29 PROMOTED for N=1**
(T-41 gate correction, D-47). Production scheduler remains BLOCKED (T-39);
the runtime default is declared in Stage 11.8B. D-28 (Stage 12 gate) is
unchanged.

## Sea-ice data caveat

- January: real OSI-SAF/C3S sea ice connected via the 11.7E.4 reader.
- April/July/October: seasonal OSI-SAF/C3S ice initializations are still
  missing; those cells use the legacy January-derived/diagnostic `1_*.ice`
  initialization. Matrix ice diagnostics for Apr/Jul/Oct are therefore
  **not OSI-SAF-validated**; do not overclaim seasonal ice validation.

## Storage budget

- One 30-day run: ~**299 MB** (`t6s_jul_legacy`, `t6s_oct_legacy`,
  `t6s_jan_production`).
- 16 cells ≈ **4.8 GB**; EOS80 production 10-day smoke was 113 MB →
  ~0.34 GB per 30-day cell, total still <6 GB.
- Disk free: **857 GB**; existing `data/runs` inventory is 44.08 GB
  (ARCHIVE 40.5 GB, TEMPORARY 2.7 GB; ~29.7 GB potential savings pending
  user approval). **No data deletion/archival is performed.**

## Current validation coverage

| Season | N=1 LEGACY | Production LEGACY | EOS80 |
|---|---|---|---|
| Jan | **PASS** | **BLOCKED (T-39)** | **PASS** |
| Apr | **PASS (extended boundary)** | BLOCKED (T-39) | **PASS** |
| Jul | **PASS** | BLOCKED (T-39) | **PASS (T-41 corrected)** |
| Oct | **PASS** | BLOCKED (T-39) | **PASS** |

Phase 2 complete: **8/8 cells PASS** under the corrected absolute-density
gate. Production column BLOCKED (T-39); **D-29 PROMOTED** for N=1; EOS80
remains excluded from production until 11.8B. See
`stage11.8A_phase2_seasonal_results.md`.
