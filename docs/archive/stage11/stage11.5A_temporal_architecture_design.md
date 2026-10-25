# Stage 11.5A — Ocean Time-Integration Architecture Audit & Design

Frozen 2026-09-30. AUDIT + DESIGN ONLY (one benign duplicate-check removal
in `netcdf_output.f90`, no behavior change). Line numbers: `app/main.f90`
at 11.4.1 (`c6846b9`).

## 1. Current architecture timeline (one model day)

`do iii = 1, mm2` (624→909) → per-iii: snapshot → `heat(DT)` → `redis()` →
ice dynamics (mm3 × DT1) → `adv2d` AN1/WICE1 → `redis()` → W recompute.
Then once/day (stale `iii=mm2+1`): scans → `advs/advt(DT)` → `conv_adj` →
B200(`DT`) → B210(`DT`) → `shal()` → B280 → scans → `iceberg_step` →
`write_nc`. Forcing: `era5_wind` daily per `kkk` (612); wind STRESS linearly
interp per-iii (`b=mm2−iii+2`); `tatm/patm/humid/wind` daily-frozen (ice
thermo sees no diurnal cycle; ERA5 3-hourly slices aliased to daily).
Output: daily `.nc` + per-iii CSV diagnostics.

## 2. Physical consistency analysis

- CORE FINDING: ocean integrates 1×DT/day (1 h/day at DT=3600) while ice
  integrates mm2×DT (12 h legacy, 24 h scaled). The ocean is dynamically
  YOUNG: "day 30" ≈ 30 ocean-hours + 720 ice-hours. All seasonal runs and
  validations to date share this property (self-consistent, never
  trajectory-validated vs observations — per physics_status limitation 7).
- Conservation: no ice–ocean heat/salt closure audit exists at mismatched
  cadences (surface T/S updated 24×/day by heat, advected 1×/day). Open item.
- Stability: unaffected (CFL measured fine); splitting error is first-order
  in the ice–ocean coupling interval (1 day for ocean state).
- Standard practice (NEMO/MITgcm/MOM6/CICE): ocean and ice step TOGETHER
  (ice subcycled WITHIN the ocean step) — ours is INVERTED (ice steps more
  often than ocean). No modern precedent for 1/day ocean with hourly ice.

## 3. Target options

- A (full substepping: ocean pass inside `iii`): coherent 24 h/day both;
  24× ocean cost; full re-baseline. PROS: correct cadence, converges with
  ice. CONS: expensive, high validation burden.
- B (selective: advs/advt/CA per-iii, B200/B210/shal daily): balances cost;
  CONS: split-brain state (advected but unadjusted momentum), complex sync.
- C (multi-rate: ocean dt_ocean=DT/N substeps): flexible; CONS: needs
  coupling interpolation machinery, largest implementation.
- D (keep): document 1 h/day as accepted limitation. CONS: blocks any
  trajectory validation forever; EOS-80/voxel work inherits the distortion.

## 4. Recommendation: phased A (11.5B–11.5D)

- Phase 0 (done, this doc): audit + design.
- Phase 1 (11.5B): `STAGE113_MM2` override experiment — separate ice-cadence
  vs ocean-dt response WITHOUT moving code (measurement only).
- Phase 2 (11.5C): prototype ocean-inside-`iii` behind env flag (OFF default);
  validate FIRST_INVALID + battery + 11.x baselines process review.
- Phase 3 (11.5D): promote + re-baseline all seasons + re-run EOS-80 matrix
  on the new cadence; update ledger/inventory docs.
- Validation per phase: OFF bit-identity → guardrail scans → EUU/ro/CA
  process review → full battery. Risks: 24× ocean cost (mitigate: keep
  DT=3600, profile first); baseline invalidation (mitigate: phased flags).
- NEXT: 11.5B (MM2 experiment). EOS-80 (11.4) and inputs (11.6) unaffected
  in design (orthogonal choices preserved).

## 5. Documentation cleanup summary (this stage)

- Removed duplicated vacuous `w_velocity` status check
  (`netcdf_output.f90`, Luna's finding — the check re-tested beta's status
  under a wrong label; no behavior change).
- Alpha/beta unit attrs verified (`g cm-3 K-1`, `g cm-3`, active-EOS FD
  documented in attrs).
