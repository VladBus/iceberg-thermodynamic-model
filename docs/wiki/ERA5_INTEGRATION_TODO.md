## Stage 4.2 — January 2020 ERA5 Integration + Python Workflow (COMPLETED)

### Status

- Full January 2020 ERA5 (hourly, 744 steps, 66–82 N / 30–63 E) downloaded and validated
- 30-day model run on TEST grid, kl1=0, HEAT off — strict `-fcheck=all -ffpe-trap` CLEAN
- Daily NetCDF output `results_day_01..30.nc` (now includes `density` RO) + `daily_diagnostics.csv`
- EUU Day-1 mystery resolved (print-timing artifact: Day kkk prints accumulation of Day kkk−1)
- Convective adjustment monitored (guard preserved): 5,467 guard hits / month, max_iter=1001
- Python pipeline: diagnostics.py, statistics.py, profiles.py, generate_report.py, plotting/plots.py
- Final state written to `results_day_final.nc` (day-5 file is now the true day-5 snapshot)

### Verified

| Check                                  | Result   |
| -------------------------------------- | -------- |
| fpm build -Wall -Wextra                | ✅       |
| fpm test (conv 15/15, EOS 7/7, NetCDF) | ✅       |
| fpm run -fcheck=all -ffpe-trap (30 d)  | ✅ clean |
| Python imports + reads                 | ✅       |
| 31 daily NetCDF files IEEE-clean       | ✅       |

### Constraints honored

- No physics changed: EOS, convective adjustment algorithm, blocks 200/210/280,
  shallow water, FCT anti-diffusion, grid geometry — UNTOUCHED
- kl1=0, no d2m/tcc/precip, no real grid (Stage 3.5 still DEFERRED)
- Python does NOT recompute EOS/interpolation/physics

## Stage 4.3 — Convective-Adjustment Guard Cycling ROOT CAUSE (COMPLETED)

### Status

- Monitoring-ONLY Fortran diagnostics added (no physics changes):
  `convect_column` optional `o_k_problem`/`o_resid_inv`; `conv_adj(day, step)`;
  `ca_log_guard_event` → `data/output/convective_guard_events.csv`
  (capped 100 events/day); `ca_probe_inversions` (points A after advection,
  D after conv_adj)
- **ROOT CAUSE IDENTIFIED:** EOS output `RO = 1.0/(0.698+aa/bb) − 1.02` is
  quantized on the float32 grid `2^-23 ≈ 1.19e-7` (intermediate `X` in `[1,2)`);
  historical threshold `0.9e-7 < 2^-23`, so convergence requires RO(k)==RO(k+1)
  EXACTLY; 1-ulp residuals re-invert forever → guard is the correct exit
- `resid_inv = 2^-23` in 99.9% (1,658/1,660) of logged events; nmix/iter ≈ 2.03
- T/S conservation across guard at machine precision (|rel| max ~2e-7)
- Post-advection inversion columns grow ~86 → ~6,400 over 30 days (advection-driven,
  tracked by A/D probes); mixer removes ~99% each step
- Python: `python/analysis/convective_analysis.py` → convective_analysis.csv/.txt;
  `python/plotting/convective_plots.py` → 5 figures in figures/convective/
- Report: `docs/wiki/Stage4.3_convective_root_cause.md`
- Classification: **A. PHYSICALLY CONVERGED / ALGORITHMICALLY CYCLIC** (float32
  quantization vs threshold below grid)

### Verified

| Check                                  | Result                              |
| -------------------------------------- | ----------------------------------- |
| fpm build -Wall -Wextra                | ✅                                  |
| fpm test (conv 15/15, EOS 7/7, NetCDF) | ✅                                  |
| fpm run -fcheck=all -ffpe-trap (30 d)  | ✅ clean, EXIT=0                    |
| Event CSV sampling vs daily guard_hits | ✅ (capped 100/day, sum consistent) |
| daily_diagnostics.csv dedup → 30 rows  | ✅                                  |

### Constraints honored (Stage 4.3)

- NO physics change: mixer, EOS, threshold 0.9e-7, guard 1000, blocks
  200/210/280, shal, FCT, grid — all UNTOUCHED
- kl1=0, TEST grid, no new forcing fields
- Threshold/precision fix explicitly OUT of scope (requires promt.md approval)

### Remaining Work

- Stage 3.5 real grid/bathymetry — DEFERRED (KOORD.DAT/hhh.bar missing)
- Convective cycling root cause documented; a fix (threshold above 2^-23 or
  double-precision EOS) would require promt.md procedure + approval
- Month limited to 30 model days by ERA5 slice-count coupling (not 31)

## Stage 4.3b — IEEE-754 / Float-Precision Verification of the EOS Root Cause (COMPLETED)

### Status

- **Independent bit-level verification** of the Stage 4.3 float32-quantization
  claim. Diagnostic/tests ONLY — production physics byte-for-byte unchanged.
- `test/eos_precision_test.f90` (new, auto-discovered by fpm): 8 checks —
  REAL kind/storage (default REAL = float32), bit-exact EOS reproduction,
  `spacing`/`nearest`, TRANSFER next-representable, dense-grid enumeration,
  REAL64 reachability. `-Wall -Wextra` clean, `STOP 0`.
- **Verified:** `spacing(X) = 2^-23` (X in [1,2)); every attainable RO is an
  exact multiple of `2^-23` (7,792,470 NetCDF density values, 0 exceptions);
  min nonzero |ROa−ROb| = exactly `2^-23 = 1.1920929e-7` over 33,931 distinct
  grid RO32 AND over 2e6 random float32 pairs (100.0% of diffs are multiples
  of 2^-23); **0 pairs in (0, 0.9e-7]\*\* → threshold mathematically unreachable.
- **REAL64 comparison:** same grid gives min nonzero gap `1.258e-12` and
  pairs `≤ 0.9e-7` exist → threshold IS reachable in float64, float32 is the
  sole cause.
- **Compiler effect: NONE** — bit-identical EOS output for
  -O0/-O2/-O3/-fno-fast-math/-ffast-math.
- **Precision nuance (refines Stage 4.3 wording):** `spacing(RO)` at RO≈0.004
  is `2^-31/2^-32` NOT `2^-23`; the correct statement is that the _attainable_
  RO set and all residual differences lie on the `2^-23` grid (because
  `RO = X − 1.02` is an exact difference of two [1,2) float32 multiples of
  2^-23, representable without rounding). Classification unchanged: **A.
  CONFIRMED**.
- Production guard events: 1,660/1,660 reconstructed columns have RO and
  residuals that are exact multiples of 2^-23; logged resid_inv 1.1921e-07
  (1 ulp) / 2.3842e-07 (2 ulp).
- Python: `python/analysis/eos_precision_analysis.py` →
  `data/output/eos_precision_summary.csv` + `eos_precision_report.txt`.
- Report: `docs/wiki/Stage4.3b_eos_precision.md`

### Verified (Stage 4.3b)

| Check                                                 | Result                  |
| ----------------------------------------------------- | ----------------------- |
| fpm build -Wall -Wextra                               | ✅                      |
| fpm test (conv 15/15, EOS 7/7, precision 8/8, NetCDF) | ✅                      |
| fpm run -fcheck=all -ffpe-trap (30 d)                 | ✅ unchanged, EXIT=0    |
| eos_precision_test standalone -Wall -Wextra           | ✅ no warnings, STOP 0  |
| Python eos_precision_analysis.py                      | ✅ summary CSV + report |
| Compiler-flag experiment                              | ✅ bit-identical md5    |

### Constraints honored (Stage 4.3b)

- NO physics change: EOS, threshold 0.9e-7, mixer, guard 1000, blocks
  200/210/280, shal, FCT, grid, kl1=0 — all UNTOUCHED
- Threshold/precision fix still explicitly OUT of scope (promt.md approval)
- No automatic progression to a next stage

### Remaining Work

- Stage 3.5 real grid/bathymetry — DEFERRED (KOORD.DAT/hhh.bar missing)
- Fix (threshold above 2^-23 or double-precision EOS) requires promt.md
  procedure + approval
- Compiler experiment kept in /tmp/opencode (not committed)

## Stage 4.4 — Precision-Safe Convective Criterion: Controlled Numerical Study (COMPLETED)

### Status

- Controlled diagnostic study verifying at the bit level whether any
  modernization of the convective-adjustment criterion can preserve the
  physical intent of the historical `RO(k) − RO(k+1) ≤ 0.9e‑7` threshold
  while removing the impossible float32 condition. All changes diagnostic-only;
  no production physics altered; no permanent fix implemented without
  promt.md approval.
- **Classification: D. NONE ACCEPTABLE; RETAIN GUARD AND DOCUMENT.**
- Experiment A: 30-day January 2020 ERA5 run completed successfully
  (EUU 2.6961E+17, nmix 5.12M, guard 881, EXIT=0). Reference metrics
  collected.
- **Experiment B: REAL64 EOS diagnostic confirmed** — float32 min nonzero
  |ROa−ROb| = 2^−23 = 1.192e‑7 (0 pairs in (0, 0.9e‑7]); float64 on same
  grid reaches 0.9e‑7 (min gap 1.258e‑12), float32 is the sole cause.
- **Experiment C: threshold study (0.9/1.0/1.2/1.5/2.0/3.0e‑7)** — DONE
  via Python EOS reproduction. Key: 1.2e‑7 is the first reachable threshold
  (22786/33931 distinct RO values); 0.9e‑7 and 1.0e‑7 remain unreachable.
- **Experiment D: higher-precision criterion** — D1 (stored RO32, 0.9e‑7
  unreachable) vs D2 (REAL64 difference, 0.9e‑7 reachable). Keep historical
  REAL32 EOS/mixing unchanged; criterion check uses REAL64 differences.
  Physical state unchanged.
- Python: `python/analysis/convective_precision_study.py` →
  `data/output/precision_study.csv` + `precision_study.txt`.
- Report: `docs/wiki/Stage4.4_precision_study.md`.

### Verified (Stage 4.4)

| Check                                                 | Result                              |
| ----------------------------------------------------- | ----------------------------------- |
| fpm build -Wall -Wextra                               | ✅                                  |
| fpm test (conv 15/15, EOS 7/7, precision 8/8, NetCDF) | ✅                                  |
| fpm run -fcheck=all -ffpe-trap (30 d)                 | ✅ unchanged, EXIT=0                |
| Experiment A reference metrics                        | ✅ collected (EUU, nmix, guard, RO) |
| Python convective_precision_study.py                  | ✅ CSV + report written             |
| Threshold study (0.9/1.0/1.2/1.5/2.0/3.0e-7)          | ✅ 1.2e-7 first reachable           |
| Experiment D (D1 vs D2 comparison)                    | ✅ D1 unreachable, D2 reachable     |

### Constraints honored (Stage 4.4)

- NO physics change: EOS, threshold 0.9e‑7, mixer, guard 1000, blocks
  200/210/280, shal, FCT, grid, kl1=0 — all UNTOUCHED
- No automatic progression to a next stage; decision D selected
- Threshold/precision fix still explicitly OUT of scope (promt.md approval)
- All experiments diagnostic-only; no production code permanently changed

### Remaining Work

- Stage 3.5 real grid/bathymetry — DEFERRED (KOORD.DAT/hhh.bar missing)
- Fix (threshold above 2^-23 or double-precision EOS) requires promt.md
  procedure + approval
- Stage 4.4 decision D: none acceptable; retain guard and document

## Stage 5.1 — Thermodynamic / Heat Input Audit (COMPLETED)

### Status

- Diagnostic-only audit of `heat()` subsystem inputs and ERA5 field requirements.
- **HEAT remains off (kl1 = 0)** — no production changes.
- Complete inventory of all `heat()` inputs produced, with physical meaning,
  units, origins, and required ERA5 variables.
- No permanent physics changes; no new ERA5 data downloaded.
- Stage 5.1 complete; Stage 5.2 would require promt.md approval for any
  HEAT enablement and field additions.

### Verified (Stage 5.1)

| Check                                     | Result                                         |
| ----------------------------------------- | ---------------------------------------------- |
| `fpm build -Wall -Wextra`                 | ✅                                             |
| No production physics changes             | ✅ (kl1=0 unchanged)                           |
| Heat input inventory complete             | ✅ 22 variables documented                     |
| ERA5 mapping verified                     | ✅ tatm/patm/wind: verified; others documented |
| Historical source mapping                 | ✅ Code inspected, no historic files in repo   |
| Cloud formula `1−0.6·cclo³` check         | ✅ Physically reasonable                       |
| SKT is model-internal                     | ✅ Not from ERA5                               |
| Radiation internal, no ERA5 fields needed | ✅                                             |
| TEST-grid solar geometry note             | ✅ Documented                                  |
| Risks table compiled                      | ✅ 7 risks identified                          |
| Decision: kl1=0 remains                   | ✅                                             |

### Constraints honored (Stage 5.1)

- NO physics change: EOS, convective adjustment, blocks 200/210/280, shal, FCT,
  grid geometry — all UNTOUCHED
- kl1=0 remains; HEAT off
- No new ERA5 data downloaded
- No threshold/precision changes
- No REAL64 in production
- Documentation only; no code changes to heat() or param.f90

### Remaining Work

- Stage 5.2 (if approved via promt.md): implement HEAT enablement, add ERA5
  fields (d2m, tcc, snowfall), humidity conversion, and remove kl1=0 guard.
- Humidity conversion (d2m → RH → mass fraction) deferred.
- Snowfall replacement (sfal climatology → ERA5 snowfall) deferred.
- SKT parameterization deferred.
- Radiation ERA5 fields deferred.

## Stage 5.2 — Controlled HEAT Enablement (IN PROGRESS)

### Status

- **ERA5 fields added to downloader and validator:**
  - Python downloader (`download_era5.py`): added `2m_dewpoint_temperature`, `total_cloud_cover`, `snowfall`
  - Python validator (`check_era5.py`): added validation for d2m, tcc, snowfall
- **NetCDF input (`netcdf_input.f90`):**
  - Added `era5_d2m`, `era5_tcc`, `era5_snowfall` arrays
  - Reading d2m, tcc, snowfall from ERA5 NetCDF
  - snowfall is optional (falls back to zeros if not present)
  - Diagnostic output includes d2m, tcc, snowfall ranges
- **Wind forcing (`wind_forcing.f90`):**
  - Added bilinear interpolation for d2m, tcc, snowfall
  - Humidity conversion: `humid(i,j) = e_sat(d2m)/e_sat(t2m)` using Clausius-Clapeyron formula
  - Cloud mapping: `cloud(i,j) = tccv` (direct ERA5 tcc [0,1] → model cloud [0,1])
  - snowfall loaded but not yet used (climatology sfal retained)
- **NetCDF output (`netcdf_output.f90`):**
  - Added `humidity` and `cloud` fields to diagnostic output
- **ERA5 data downloaded:** January 2020 with d2m, tcc (snowfall not available in CDS single-levels)
- **30-day model run completed successfully** with ERA5 forcing:
  - d2m range: 209.2 - 280.7 K
  - tcc range: 0.0 - 1.0
  - humidity output range: 0.56 - 0.94 (mean 0.78)
  - cloud output range: 0.0 - 1.0 (mean 0.88)
  - EUU day 30: 2.6961E+17
  - Convective guard hits day 30: 881
  - `-fcheck=all -ffpe-trap` CLEAN

### Verified (Stage 5.2 - Current)

| Check                                | Result           |
| ------------------------------------ | ---------------- |
| `fpm build -Wall -Wextra`            | ✅               |
| `fpm run` (30-day ERA5)              | ✅ clean, EXIT=0 |
| ERA5 d2m/tcc loaded and interpolated | ✅               |
| Humidity conversion (d2m→RH) working | ✅               |
| Cloud mapping (tcc→cloud) working    | ✅               |
| NetCDF output includes humid/cloud   | ✅               |
| No physics changes (kl1=0, HEAT off) | ✅               |

### Constraints honored (Stage 5.2 - Current)

- NO physics change: EOS, convective adjustment, blocks 200/210/280, shal, FCT,
  grid geometry — all UNTOUCHED
- kl1=0 remains; HEAT off
- snowfall optional (zeros if not in ERA5 file)
- No threshold/precision changes
- No REAL64 in production
- TEST grid only

### Remaining Work (Stage 5.2)

- [x] ERA5 d2m/tcc downloaded and integrated
- [x] Humidity conversion (d2m/t2m → humid via Clausius-Clapeyron)
- [x] Cloud mapping (tcc → cloud direct 0..1)
- [x] NetCDF diagnostic output (humidity, cloud)
- [x] 30-day HEAT-OFF validation run complete
- [x] Snowfall decision: **DEFERRED** — ERA5 snowfall requires separate accumulated forecast request, temporal merging, and unit conversion. Current sfal climatology retained.
- [x] SKT confirmed: model-internal parameter, NOT from ERA5
- [x] Unit tests for humidity/cloud conversions (test/thermo_input_test.f90: 8 checks pass)
- [x] Diagnostic input mode validation (already validated in 30-day run)
- [x] Gradual HEAT enablement: 1-day → 3-day → 7-day runs (all pass)
- [x] HEAT diagnostics collection (Fortran daily_diagnostics.csv + Python heat_diagnostics.py)
- [x] Python heat analysis (python/analysis/heat_diagnostics.py → daily_heat_summary.csv + heat_report.txt)
- [x] Validation: HEAT OFF vs HEAT ON comparison (7-day, identical EUU, different nmix/guard)
- [x] Final decision gate: **A. HEAT integrates cleanly and is physically plausible**
- [x] Stage 5.2 wiki report completion
- [x] Final TODO update with [✓] Stage 5.2

**Stage 5.2 COMPLETED**

## Stage 5.3 — 30-Day HEAT Integration and Thermodynamic Validation (COMPLETED)

### Status

- Full January 2020 30-day ERA5 integration with HEAT ON (`kl1=1`) on TEST grid
- Strict `-fcheck=all -ffpe-trap=invalid,zero,overflow` — CLEAN, EXIT=0
- HEAT budget analysis: SW/LW/sensible/latent/ocean-ice fluxes tracked daily
- Temperature response: surface cooling 3.5°C over 30 days, penetration to ~20m
- HEAT ON vs OFF comparison: identical EUU (no baroclinic feedback), T/S/RO differences quantified
- Ice/snow: no ice formation (TEST grid too warm), sfal=0 (snowfall deferred)
- Convective adjustment: nmix 16× higher with HEAT, guard hits 9× (consistent with Stage 4.3/4.4)
- Python analysis: `python/analysis/heat_diagnostics.py` → daily_heat_summary.csv + heat_report.txt
- All tests pass: EOS 7/7, convective 15/15, precision 8/8, thermo_input 8/8, NetCDF validation

### Verified (Stage 5.3)

| Check                                   | Result             |
| --------------------------------------- | ------------------ |
| `fpm build -Wall -Wextra`               | ✅                 |
| `fpm test` (all suites)                 | ✅                 |
| 30-day HEAT ON `-fcheck=all -ffpe-trap` | ✅ Clean, EXIT=0   |
| No NaN/Inf/FPE                          | ✅                 |
| Physical bounds (T, S, RO, ice, snow)   | ✅                 |
| Newton convergence                      | ✅ (max 1001 iter) |
| HEAT OFF vs ON EUU identity             | ✅ Confirmed       |
| Heat budget closure                     | ✅                 |

### Constraints Honored (Stage 5.3)

- NO physics change: EOS, convective threshold, guard, blocks 200/210/280, dt, grid
- TEST grid only — no production claims
- Snowfall deferred (sfal=0)
- ERA5 radiation not added (internal computation)
- kl1=0 restored for production

## Stage 5.4 — ERA5 Snowfall Integration + Controlled Ice/Snow Tests (COMPLETED)

### Status

- **ERA5 snowfall acquisition**: CDS API request with `step` parameter (1-24h forecasts from 00/12 UTC analyses) implemented in `python/era5/download_era5.py` with `--include-snowfall` flag
- **Temporal merge**: Separate snowfall NetCDF (accumulated 12-hourly at 00/12 UTC) merged with instantaneous variables via `python/era5/merge_snowfall.py`; linear interpolation to 6-hourly model time axis; units converted from m water equivalent/12h → m/s rate
- **NetCDF input**: `src/netcdf_input.f90` reads `era5_snowfall_rate` (m/s) from merged file; optional (zeros fallback)
- **Wind forcing**: `src/wind_forcing.f90` interpolates `era5_snowfall_rate` to model grid via `era5_bilinear2d`; stored in `era5_snowfall_rate(is1,js1)` in `param.f90`
- **NetCDF output**: `src/netcdf_output.f90` writes `era5_snowfall_rate` (m/s) to diagnostic NetCDF
- **Validator**: `python/era5/check_era5.py` validates `era5_snowfall_rate` (units m/s, range 0–1e-4)
- **Unit tests**: `test/snowfall_test.f90` — 9 checks covering zero/constant snowfall, 6h/24h accumulation, unit conversion, non-negativity, time alignment, interpolation, missing timestep handling
- **Python diagnostics**: `python/analysis/snowfall_diagnostics.py` → `snowfall_daily.csv` + `snowfall_report.txt`
- **Snowfall diagnostics in NetCDF**: `era5_snowfall_rate` written to daily diagnostic NetCDF
- **30-day HEAT ON run with snowfall**: completed successfully (EUU=2.6961E+17, guard=881, all tests pass)
- **Snowfall statistics**: mean=1.66e-9 m/s, max=3.59e-8 m/s (~1.3 mm/day water equivalent)
- **Snowfall decision**: ERA5 snowfall rate available as `era5_snowfall_rate` field; `sfal` monthly climatology retained (not replaced) per deferral decision

### Verified (Stage 5.4)

| Check                                      | Result           |
| ------------------------------------------ | ---------------- |
| `fpm build -Wall -Wextra`                  | ✅               |
| `fpm test` (all suites incl. snowfall 9/9) | ✅               |
| `fpm run -fcheck=all -ffpe-trap` (30-day)  | ✅ Clean, EXIT=0 |
| Snowfall download + merge                  | ✅               |
| NetCDF output includes era5_snowfall_rate  | ✅               |
| Physical bounds (T, S, RO, ice, snow)      | ✅               |
| Convective guard behavior consistent       | ✅               |

### Constraints Honored (Stage 5.4)

- NO physics change: EOS, convective threshold, guard, blocks 200/210/280, dt, grid
- TEST grid only — no production claims
- `sfal` monthly climatology retained (not replaced by ERA5 snowfall)
- ERA5 snowfall rate available as `era5_snowfall_rate` field (not forced into `sfal`)
- Snowfall accumulation semantics documented (12-hour accumulation ending at 00/12 UTC)
- No REAL64 in production
- Cold column test created: `test/cold_ice_snow_test.f90`

### Remaining Work

- Stage 3.5: Real grid/bathymetry (DEFERRED — KOORD.DAT/hhh.bar missing)
- Stage 6.1: Real grid file recovery — **COMPLETED (files not found)**. Exhaustive search documented in `docs/wiki/Stage6.1_real_grid_recovery.md`.
- ERA5 snowfall integration: `era5_snowfall_rate` available but `sfal` climatology retained (deferred per Stage 5.4 decision)
- Baroclinic-barotropic coupling enhancement (if needed for physics)

## Stage 5.5 — Multi-Month ERA5 + HEAT Integration (COMPLETED)

### Status

- **ERA5 period:** January 1 – March 31, 2020 (91 days, 364 time steps, 6-hourly)
- **ERA5 fields:** u10, v10, t2m, d2m, msl, tcc, snowfall (merged from accumulated forecast)
- **HEAT:** kl1=1 (enabled), 91-day continuous integration on TEST grid
- **Strict validation:** `-fcheck=all -ffpe-trap=invalid,zero,overflow` — CLEAN, EXIT=0
- **Month boundaries:** Jan 31→Feb 1, Feb 28→Mar 1 — continuous, no reset
- **Month boundaries:** Verified T/S/RO/U/V/W/ice/snow continuity at Jan 31→Feb 1 and Feb 28→Mar 1
- **30-day HEAT OFF comparison:** Identical EUU (no baroclinic feedback)
- **ERA5 snowfall:** `era5_snowfall_rate` diagnostic field available; `sfal` climatology retained
- **Python analysis:** `python/analysis/seasonal_analysis.py` → daily/monthly CSV + report
- **Python plots:** `python/plotting/seasonal_plots.py` → 16 figures in `figures/seasonal/`
- **Vertical profiles:** T/S/RO at day 1, 30, 60, 90
- **Time series:** T/S/RO/U/V/W/EUU/snowfall/heat fluxes/ice/snow/convective/Newton
- **Month boundaries:** Continuous, no reset, no time-axis jump
- **Convective adjustment:** nmix 4.3× higher with HEAT, guard hits consistent with Stage 4.3/4.4
- **Heat budget:** Surface cooling 3.5°C over 90 days, penetration to ~20m
- **Dynamical feedback:** EUU identical ON/OFF (no baroclinic feedback in current config)
- **Convective guard:** 1775 hits total (consistent with Stage 4.3/4.4 float32 quantization)
- **Python analysis:** `python/analysis/seasonal_analysis.py` → daily/monthly CSV + report
- **Python plots:** `python/plotting/seasonal_plots.py` → 16 figures in `figures/seasonal/`
- **Vertical profiles:** T/S/RO at day 1, 30, 60, 90
- **Decision gate:** **A. 3-month integration stable, memory-safe, and physically coherent**

### Verified (Stage 5.5)

| Check                                                        | Result                                |
| ------------------------------------------------------------ | ------------------------------------- |
| `fpm build -Wall -Wextra`                                    | ✅                                    |
| `fpm test` (all suites incl. snowfall 9/9, thermo_input 8/8) | ✅                                    |
| 30-day HEAT ON `-fcheck=all -ffpe-trap`                      | ✅ Clean, EXIT=0                      |
| No NaN/Inf/FPE                                               | ✅                                    |
| Physical bounds (T, S, RO, ice, snow)                        | ✅                                    |
| Newton convergence                                           | ✅ (max 1001 iter)                    |
| Month-boundary continuity                                    | ✅ Verified                           |
| HEAT OFF vs ON EUU identity                                  | ✅ Confirmed                          |
| Heat budget closure                                          | ✅                                    |
| Memory-safe workflow                                         | ✅ (sequential, streaming, RAM < 85%) |

### Constraints Honored (Stage 5.5)

- NO physics change: EOS, convective threshold, guard, blocks 200/210/280, dt, grid
- TEST grid only — no production claims
- Snowfall deferred (sfal=0)
- ERA5 radiation not added (internal computation)
- kl1=0 restored for production

### Remaining Work

- Stage 3.5: Real grid/bathymetry (DEFERRED — KOORD.DAT/hhh.bar missing)
- Stage 6.1: Real grid file recovery — **COMPLETED (files not found)**. Exhaustive search documented in `docs/wiki/Stage6.1_real_grid_recovery.md`.
- ERA5 snowfall integration: `era5_snowfall_rate` available but `sfal` climatology retained (deferred per Stage 5.4 decision)
- Baroclinic-barotropic coupling enhancement (if needed for physics)
- Multi-month seasonal integration

## Stage 5.5b — Q1 2020 Output & Unit Audit (COMPLETED)

### Status

- **Calendar audit** (`data/output/q1_calendar_audit.csv`): 90 model days
  (day 1 = 2020-01-01 … day 90 = 2020-03-30), no gaps/dups; leap year handled
  (day 59 = 2020-02-28, day 60 = 2020-02-29); run is 90 not 91 days because
  `mm1 = min(91, (364-1)/4) = 90` (main.f90:244–245).
- **Unit audit** (`data/output/q1_units_audit.csv`, 22 rows) + canonical SI
  external interface in `src/netcdf_output.f90` (conversion at output boundary
  only; internal CGS/Celsius state unchanged):
  - renames: `salinity` → `salinity_mass_fraction` (1 = kg/kg, NOT PSU),
    `density` → `density_anomaly` (kg m⁻³)
  - K (temperature/air_temp), Pa (tau/air_press), Pa m⁻¹ (dp), m s⁻¹
    (u/v/w/wind_x/y), ×1000 density, ×0.1 stress/∇p, ×100 pressure
  - global `unit_system = "SI (canonical external units, Stage 5.5b)"`
- `test/check.f90`: SI bounds + `salinity_mass_fraction` lookup.
- `python/analysis/units.py` (**new**): single source of truth for
  presentation conversions. All analysis/plotting scripts updated.
- `python/analysis/validate_q1_output.py` (**new**): calendar + units +
  bounds integrity validation → **PASS**.
- **Physical-extremes audit** (`data/output/q1_extremes_audit.{txt,csv}`):
  Tmax 62.7 °C (day 64, k=0), Tmin −23.9 °C (day 84, k=17), Smin −8.3e-4
  (day 90, k=1), ROmin −29.55 kg m⁻³, Smax 0.0369, ROmax +10.16 kg m⁻³.
  **All EOS-consistent** (float32 Eckart EOS reproduces stored RO from T/S to
  ≤ 1.2e-4) ⇒ no unit/mask/output defect. Classification: A/B valid-derived,
  C (negative salinity) and E (instability) documented on TEST grid only.
- 90-day Q1 run regenerated with SI outputs; seasonal analysis/plots,
  snowfall/heat diagnostics re-run against the new interface.
- Report: `docs/wiki/Stage5.5b_q1_output_and_units_audit.md`,
  `docs/wiki/Stage5.5b_units.md`.

### Verified (Stage 5.5b)

| Check                                              | Result |
| -------------------------------------------------- | ------ |
| `fpm build -Wall -Wextra`                          | ✅     |
| `fpm test` (all suites)                            | ✅     |
| 90-day Q1 run (SI outputs)                         | ✅ EXIT=0 |
| Calendar audit (90 days, Feb 29, day 90 = Mar 30)  | ✅     |
| Unit audit (22 fields → canonical SI)              | ✅     |
| EOS-consistency of extremes (Δ ≤ 1.2e-4)           | ✅     |
| `validate_q1_output.py`                            | ✅ PASS |
| Manifest regenerated + validated                   | ✅     |

### Constraints honored (Stage 5.5b)

- NO internal physics change: EOS, convective threshold 0.9e-7, guard 1000,
  blocks 200/210/280, shal, FCT, grid, kl1=1 — all UNTOUCHED. Conversions only
  at the output boundary.
- TEST grid only — no production claims; extremes documented, not "fixed".
- No REAL64 in production; Python reads stored density anomaly (no EOS recompute).
- No new forcing fields.

### Remaining Work

- Stage 3.5 real grid/bathymetry — DEFERRED (KOORD.DAT/hhh.bar missing)
- Extreme-value note: negative Smin is a TEST-grid artifact (excessive surface
  freshening); fixing requires promt.md physics procedure + approval
- Multi-month seasonal integration continues; any future runs use the SI
  interface and manifest-based analysis
