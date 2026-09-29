# Stage 11.3A — Ocean Core Architecture Audit (main.f90 execution graph)

Frozen 2026-09-29. Commit scope: `app/main.f90` (1564 lines) + `src/` (34 files
post-D33) as of D33 (`156d52f`). AUDIT ONLY — no code, physics, data, or date
changes. All line numbers refer to `app/main.f90` unless stated.

## 1. Complete execution graph

### 1.1 Initialization phase (lines 120–531)

| Block (lines) | Call | Purpose | Inputs | Outputs | Units | Status |
|---|---|---|---|---|---|---|
| 124–137 | `setup_run_dirs()` | CLI (`run_id`, `[era5_file]`) → run dirs | CLI args | `run_*_dir` paths | — | PRODUCTION |
| 139–153 | — | Calendar + flags: `god/mes/den/hour`, `kl1=1`, `forcing_mode=ERA5` | hardcoded | `nat()`, flags | — | PRODUCTION (date: see §3) |
| 155–219 | — | Grid/time/physics constants: `dt1=120`, `dt=3600`, `dx=13.89e6 cm`, `mm1=91`, `mm2=12`, `mm3=30`, `ah/aht/ahs=7.5e6`, `g=981`, `c1–c17` | hardcoded | constants | CGS | PRODUCTION |
| 221–244 | — | Tidal harmonics read (`GRM2`: amp1/faz1…, `qq` M2/S2/K1/O1) | `GRM2` (MISSING → zeros) | `amp*/faz*`, `qq` | mixed | ZERO-FORCING (see §4) |
| 255–259 | `datte()` | Astronomical tidal arguments from `nat()` (1998-04-16) | `nat()` | `v00/om/fff` (tide_forcing) | deg/hr | LEGACY (effect null: amps=0) |
| 261–266 | `coup1()`, `ikuv()` | Grid coupling + masks (IKUV) | `KOORD.DAT` (FATAL if missing), `hhh.bar` (synthetic fallback) | `fi/dl/kt1/idx/idy`, masks | m/deg | PRODUCTION |
| 268–280 | — | Legacy pressure read (`DAV4_5.98` → `p`) | `DAV4_5.98` (MISSING → `p=0`) | `p` (dead under ERA5) | — | LEGACY/DEAD |
| 282–329 | `redis()` | Ice init (`1_1..1_5.ice` → `an1`; `wice1`=hst·an1; cleanup) | `1_*.ice` files | `an1/wice1/hsnow` | SI (m) | PRODUCTION |
| 332 | `init_ocean()` | Synthetic ocean fallback fields | hardcoded | `t1/s1/u2/v2` (overwritten by EN4 below) | CGS/°C | LEGACY (superseded) |
| 335–430 | `ca_configure`, `eos_configure`, `eos_diag`, `s22_*` | CA/EOS precision matrix (10.21), B200 audit switches (10.22), CFL init (11.2) | env (all default OFF) | config + initial `ro` | mixed | EXPERIMENTAL (OFF) / ACTIVE_DIAGNOSTIC |
| 438–473 | `era5_open/diag`, `era5_wind` | ERA5 open, day-count clamp (`mm1`), initial wind/pressure | ERA5 NetCDF (CLI or `param`) | `tx1/ty1/dpx1/dpy1/windx1…`, `start_sec` | CGS + SI mix | PRODUCTION (incl. D32 fallback) |
| 481 | `init_thermal_wind()` | Thermal-wind velocity init from `ro` | `ro`, `dpx/dpy` | `u2/v2` drift | cm/s | PRODUCTION |
| 499 | `write_nc(day_00)` | Day-0 snapshot | state | `results_day_00.nc` | SI (CF) | PRODUCTION |
| 515–531 | `iceberg_init()` | Iceberg init at (61,37)≈75N,30E | `ICEBERG_PRODUCTION` (default OFF) | `ib_state` | mixed | EXPERIMENTAL (OFF) |

EN4 ocean T/S enters via `initial_ocean_reader` (`ICEBERG_OCEAN_INIT_FILE`;
Stage 7.7; T [°C], S mass fraction).

### 1.2 Time loop structure

`mmmm`(1..mm5=1) → `lll`(1..mm4=1) → `kkk`(kkb..mm1, `nday1==91` exit, line 555)
→ `iii`(1..mm2=12, hourly `dt=3600`) → `jjj`(1..mm3=30, `dt1=120` ice microsteps).
NOTE: `mm2=12` covers 12 h/day of thermodynamics (header comment; legacy cadence).

### 1.3 Physics sequence per `iii` (with diagnostics)

1. Wind interp `era5_wind()` (576) or legacy `wind1()` (583, dead path).
2. `heat()` (628, kl1=1) → `redis()` (632). [Stage 8.6 C/D captures.]
3. Ice dynamics `jjj`-loop (656–749): `stress()` (662) → hht-guard → solver
   (738-739) → boundary copies (742–748).
4. `adv2d()` ×2 per category (758/764: AN1, WICE1) → `redis()` (769).
5. W from continuity (790+) with vertical-CFL probe (878).
6. `advs()` (902) / `advt()` (905) with BEFORE/BETWEEN scans.
7. `conv_adj()` (923) with BEFORE/AFTER scans + F capture.
8. Optional predictor-corrector / thermal-wind rebalance blocks (942–953,
   env-gated, default OFF).
9. Block 200 3D-momentum (~986–1072, with s22 sandwich/budget when enabled).
10. Block 210 vertical viscosity/Thomas (~1105–1242).
11. `shal()` shallow-water barotropic (1256) + Block 280 (~1316).
12. END_step scans/timeseries (1322–1326); iceberg_step per `iii` when enabled
    (1363–1397, `get_ocean_profile` NaN-guarded per 10.19).
13. Daily `write_nc(day_file)` (1418) + `write_daily_diagnostics` (1419);
    final `results_day_final.nc` (1456); `s112_finalize` (1446);
    `ca_stats` report (1514).

### 1.4 Roles count (Luna's "10+ roles" confirmed)

Configuration, calendar, legacy I/O, grid/masks, ice init, ocean init,
ERA5 forcing, tidal init, CA/EOS experiments, audit switches, diagnostics
(8.6/10.22/11.2), time-loop orchestration, ice thermo/dynamics/advection,
ocean advection/CA/momentum/viscosity/barotropic, W continuity, iceberg
coupling, NetCDF output, run manifests. Modernization direction: extract
forcing/IO/calendar/diagnostics out of `main` (11.3B–11.3E proposals, §7).

## 2. Legacy file inventory

| File | Purpose | Used? | Replacement plan |
|---|---|---|---|
| `GRM2` | Tidal harmonic amps/phases on hydro grid | NO (missing → zeros; tides null) | REPLACE (modern tidal DB, e.g. Arctic tidal inverse model) or REMOVE with explicit no-tide decision |
| `DAV4_5.98` | Legacy pressure field → `p` | NO (dead under ERA5; `wind1()` never called) | REMOVE (after confirming `p` unused outside legacy path) |
| `FI1DL1.DAT` | Legacy wind-grid input (`wind_forcing.f90:79`) | NO (missing → zeros; ERA5 path active) | REMOVE (same condition as above) |
| `1_1..1_5.ice` | Initial ice-category areas | YES (symlinks → `data/input/generated/real_grid/`) | CONVERT TO NETCDF (with month-resolved fields; currently January-only state reused for all months) |
| `KOORD.DAT` | Model grid lat/lon (FI/DL, list-directed) | YES (FATAL STOP if missing) | KEEP AS-IS short-term; CONVERT TO NETCDF long-term (single source with bathymetry) |
| `hhh.bar` | Land/sea mask + depth index (KT1) | YES (synthetic-basin fallback if missing) | KEEP AS-IS (regenerable via `python/grid/build_real_grid_inputs.py`) |

## 3. Date/time audit (1998-04-16)

- `god=1998.0/mes=4.0/den=16.0/hour=0.0` (140–143) → `nat(1..4)` (145–148) →
  `datte()` (255) → astronomical tidal arguments (`v00/om/fff`) used ONLY by
  `shal()` boundary tides, whose amplitudes are ZERO (GRM2 missing). Net
  effect of the date today: NULL.
- ERA5/EN4 time indexing does NOT use `god`: `start_sec=era5_time(1)`,
  `mm1` clamped by file coverage; model calendar is `nday/nday1` counters.
- Verdict: historical artifact (legacy 1998 hindcast setup). Safe to keep
  while tides are null; any tidal reactivation (11.3D) must replace it with
  the run-year date (dynamic, from ERA5/EN4). DO NOT touch in 11.3A.

## 4. Zero-forcing inventory

| Forcing | State | Impact | Modern replacement |
|---|---|---|---|
| Tides (amp/faz) | ZERO (GRM2 missing) | No tidal elevation/currents; boundary `shal()` tide terms null | Arctic tidal inverse model; needs date fix (§3) |
| Surface waves | ABSENT (no code path at all) | No wave radiation stress / Stokes drift / wave-ice break-up (iceberg wave erosion explicitly out of scope since 10.18A) | ERA5 wave fields (swh, mwd) — new parameterization stage |
| Legacy wind (`wind1`, `p`, FI1DL1) | ZERO/dead (ERA5 active) | None (ERA5 covers) | Already replaced by ERA5; remove dead path in 11.3B |
| ERA5-skipped edge cells | FIXED in D32 (nearest-edge) | Was Day-1 zombie; now edge-persistent | Done; consider full-domain ERA5 expansion file for elegance |

## 5. Module classification

- PRODUCTION (29): advection (2d/3d_s/3d_t), barotropic_dynamics,
  convective_adjustment, equation_of_state, grid_coupling, grid_masks,
  ice_deform, ice_redis, ice_stress, iceberg×6, initial_conditions,
  initial_ocean_reader, netcdf_input, netcdf_output, param, run_config,
  shallow_water, smooth_filter, thermal_wind_init, thermodynamics,
  tide_forcing (wired, null input), wind_forcing.
- LEGACY_IO: none as separate modules (legacy reads inline in `main` /
  `wind_forcing` — a modernization target).
- DIAGNOSTIC → promotion verdicts: `stage86_diagnostics` (8.6 divergence
  tracker: PROMOTE — always-on cheap health, already called via
  `capture_state`); `stage112_cfl_diagnostics` (PROMOTE the FIRST_INVALID scan
  as permanent guardrail; keep CFL matrix env-gated); `stage1022_diagnostics`
  (KEEP env-gated — deep B200 audit, not every-run material).
- EXPERIMENTAL: CA/EOS f64 matrix (10.21, OFF), B200-freeze family (10.22,
  OFF), predictor-corrector + thermal-wind rebalance (env-gated), iceberg
  coupling (10.19, OFF), low_flow/natural-convection/three-equation switches
  inside `iceberg_thermodynamics` (OFF, per 10.10–10.13).
- ARCHIVED: D24–D31 forensic modules (removed in D33).

## 6. Output architecture assessment

Per-file dims: `x/y (133/105)`, `depth/depth_w (18/19)`, `ice_category (5)`;
2D aux `latitude/longitude`; `water_column_levels`; 3D `temperature (K)`,
`salinity_mass_fraction`, `density_anomaly`, `u/v/w (m/s)`; per-category
`snow_depth/ice_thickness/ice_concentration`; surface `wind_speed/x/y`,
`tau_x/...`, `humidity`, `era5_snowfall_rate`; CF-1.10 metadata (per AGENTS.md).
Gaps for GIS export: NO time dimension (time in filename only), no
grid-mapping variable, no run-provenance global attributes. Needed: unlimited
`time` dim + `grid_mapping` + global attrs (run_id, forcing file, git hash,
switches) — proposal for 11.3E. Category-resolved ice already present.

## 7. Recommendations for 11.3B–11.3E

- 11.3B (init/forcing hygiene): remove dead legacy paths (`wind1`, DAV4/FI1DL1
  readers, `init_ocean` synthetic shadow), `1_*.ice` → NetCDF with monthly fields.
- 11.3C (timestep sensitivity, original 11.3 matrix): now unblocked (11.x
  baselines fixed in D33).
- 11.3D (tides or explicit no-tide): GRM2 decision + dynamic date; waves need
  separate scoping.
- 11.3E (output/GIS): time dim + grid_mapping + provenance attrs; keep
  per-category ice.
- Cross-cutting: promote 8.6 + FIRST_INVALID to permanent guardrails; keep
  10.21/10.22 matrices env-gated; `main.f90` role extraction (forcing/IO/
  calendar modules) as opportunistic refactoring, never mixed with physics.
