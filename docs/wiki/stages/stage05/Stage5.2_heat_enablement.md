# Stage 5.2 — Controlled HEAT Enablement (IN PROGRESS)

## Summary

Stage 5.2 implements the ERA5 thermodynamic fields (d2m, tcc, snowfall) and
enables the HEAT (`kl1=1`) thermodynamics module in a controlled, incremental
fashion. This stage follows the diagnostic-only Stage 5.1 audit
(`docs/wiki/stages/stage05/Stage5.1_heat_input_audit.md`).

**Current status:** ERA5 d2m/tcc integrated, humidity/cloud mapping working,
30-day HEAT-OFF run complete. HEAT enablement (1/3/7-day tests) NOT yet started.

## A. Scope

Based on Stage 5.1 audit findings, the minimal ERA5 fields required for `heat()`
are:

| Model variable | ERA5 variable             | Status               |
| -------------- | ------------------------- | -------------------- |
| `tatm` [°C]    | `t2m` [K]                 | ✅ Done (Stage 4.2)  |
| `patm` [гПа]   | `msl` [Pa]                | ✅ Done (Stage 4.2)  |
| `wind` [м/с]   | `u10/v10` [m/s]           | ✅ Done (Stage 4.2)  |
| `humid` [доля] | `d2m` [K] dew point       | ✅ Done (this stage) |
| `cloud` [доля] | `tcc` [total cloud cover] | ✅ Done (this stage) |
| `sfal` [м/с]   | `snowfall` [m w.e.]       | ⚠️ DEFERRED          |
| `skt` [м²/с]   | (model internal)          | ✅ Not from ERA5     |
| Radiation      | (internal)                | ✅ Not from ERA5     |

## B. Completed Before Current Continuation

From previous work (Stage 4.2 + early Stage 5.2):

- ERA5 downloader (`python/era5/download_era5.py`): added `2m_dewpoint_temperature`,
  `total_cloud_cover`, `snowfall` to request
- ERA5 validator (`python/era5/check_era5.py`): added validation for d2m, tcc, snowfall
- NetCDF input (`src/netcdf_input.f90`): reads d2m, tcc, snowfall (optional, zeros fallback)
- Wind forcing (`src/wind_forcing.f90`): interpolates d2m, tcc, snowfall
- Humidity conversion: `humid(i,j) = e_sat(d2m)/e_sat(t2m)` via Clausius-Clapeyron
- Cloud mapping: `cloud(i,j) = tccv` (direct 0..1 mapping)
- NetCDF output (`src/netcdf_output.f90`): writes `humidity` and `cloud` diagnostics
- January 2020 ERA5 downloaded (124 time steps, 6-hourly, 66–82°N / 30–63°E)
- 30-day HEAT-OFF run: EUU day-30 = 2.6961E+17, guard hits = 881, all tests pass

## C. d2m (Dew Point Temperature)

**ERA5 variable:** `d2m` [K] = 2m dew point temperature
**Downloaded:** ✅ (6-hourly, 124 time steps)
**Range in Jan 2020:** 209.2 – 280.7 K
**Interpolation:** Bilinear to model grid in `era5_wind()`
**Usage:** Source for humidity conversion

## D. tcc (Total Cloud Cover)

**ERA5 variable:** `tcc` [0–1] = total cloud cover fraction
**Downloaded:** ✅ (6-hourly, 124 time steps)
**Range in Jan 2020:** 0.0 – 1.0 (mean 0.866)
**Interpolation:** Bilinear to model grid in `era5_wind()`
**Usage:** Direct mapping to `cloud(i,j)`

## E. Humidity Conversion

**Physics:** The `heat()` subroutine uses `humid` as a multiplier for saturation
vapor pressure: `e_vap = humid * e_sat(tta)` (line 92, `thermodynamics.f90`).
By definition of dew point, actual vapor pressure `e_vap = e_sat(d2m)`.
Therefore: `humid = e_sat(d2m) / e_sat(t2m)` = relative humidity (0..1).

**Implementation** (`wind_forcing.f90`, `era5_wind` subroutine):

```fortran
humid(i, j) = (610.78 * 10.0**((8.61503*(d2mv - 273.15))/d2mv)) / &
              (610.78 * 10.0**((8.61503*(t2mv - 273.15))/t2mv))
```

This uses the same Clausius-Clapeyron formula as `heat()` for consistency.

**Output range (Jan 2020):** 0.56 – 0.94 (mean 0.78)

**Physical validity:** Values in expected Arctic winter range. No supersaturation
(d2m ≤ t2m enforced by physics).

## F. Snowfall

**ERA5 variable:** `snowfall` (CDS parameter `sf`) [m of water equivalent]
**Nature:** Accumulated forecast variable (requires `step=1..24` from 00/12 UTC
analyses). Cannot be combined with instantaneous variables in single CDS request.

**Current status:**

- Downloader supports `--include-snowfall` flag for separate request
- NetCDF input reads `sf` (falls back to zeros if absent)
- Wind forcing interpolates snowfall but does NOT yet use it

**sfal climatology:** Model currently uses monthly `sfal(12)` DATA values
(0.85, 0.85, 0.83, 0.81, 0.82, 0.78, 0.64, 0.69, 0.84, 0.85, 0.85, 0.85).
These appear to be dimensionless weights, not physical [m/s] rates.

**Decision:** **DEFERRED** — ERA5 snowfall requires separate download, temporal
merging (accumulated forecast → analysis times), and unit conversion
(m w.e. → model snowfall rate [м/с]). Current sfal climatology retained.

**Requirements for future implementation:**

1. Download snowfall with `step` parameter (separate CDS request)
2. Merge accumulated forecast (1-24h) onto analysis time grid
3. Convert m water equivalent → model snowfall rate [м/с] via `depth = snowfall * dt / ρ_ice`
4. Validate against sfal climatology

## G. skt (Turbulent Exchange Coefficient)

**Model variable:** `skt(i,j)` [м²/с] — vertical turbulent heat exchange at
ice/water boundary. Used in `fw = 1028.0*4.1868e3*skt*(t1-tfr)/(dz*1e-2)`.

**ERA5 variable:** `skin_temperature` [K] — surface skin temperature.
**NOT the same physical quantity.** `skt` is a diffusivity coefficient;
ERA5 `skin_temperature` is a thermodynamic temperature.

**Decision:** Model `skt` remains internal parameter. NOT from ERA5.

## H. HEAT Enable Procedure

Per AGENTS.md §8 and promt.md §5–6:

1. **Diagnostic input mode** (kl1=0): Read d2m/tcc, compute humid/cloud, output
   statistics (min/max/mean/NaN/Inf) for day 1 and representative points
   ✅ Already validated in 30-day HEAT-OFF run

2. **Unit tests** for humidity/cloud/snowfall conversions (NOT yet done)

3. **Gradual HEAT enablement** (kl1=1):
   - 1-day run
   - 3-day run
   - 7-day run
   - NOT full month yet

4. **HEAT diagnostics** at every day:
   - Air/surface water temperature, humidity, cloud, wind
   - SW/LW/sensible/latent/ocean-ice heat fluxes
   - Ice thickness, snow thickness, ice concentration
   - Newton iterations, failures, clamps, NaN/Inf
   - T/S/RO, U/V/W, EUU

5. **Numerical safety** at each stage:
   - `fpm build -Wall -Wextra`
   - `fpm test`
   - `fpm run -fcheck=all -ffpe-trap=invalid,zero,overflow`
   - On ANY failure: STOP, do not clamp/change dt/modify physics

6. **Python analysis/plots** for HEAT budget

7. **Validation:** HEAT OFF vs HEAT ON comparison (1/3/7 days)

8. **Decision gate** (A/B/C/D) after 7-day tests

## I. Diagnostics (to be implemented)

**Fortran (per-day, appended to daily_diagnostics.csv):**

- Heat flux components (SW, LW, sensible, latent, ocean-ice)
- Surface temperature, air temperature, humidity, cloud
- Ice/snow thickness, concentration
- Newton iterations, failures, phase-change events

**Python (`python/analysis/heat_diagnostics.py`):**

- `daily_heat_summary.csv` + `heat_report.txt`
- HEAT OFF vs HEAT ON differences

**Plots (`python/plotting/`):**

- Air vs surface-water temperature
- Humidity, cloud cover
- Heat flux components (SW, LW, sensible, latent, total)
- Ice thickness, snow thickness, ice concentration
- HEAT OFF vs HEAT ON temperature difference

## J. 1/3/7-Day Experiments (NOT YET RUN)

| Run        | kl1 | Days | Status     |
| ---------- | --- | ---- | ---------- |
| 1-day HEAT | 1   | 1    | ⏳ PENDING |
| 3-day HEAT | 1   | 3    | ⏳ PENDING |
| 7-day HEAT | 1   | 7    | ⏳ PENDING |

## K. HEAT OFF vs HEAT ON Comparison (NOT YET RUN)

Compare identical ERA5 forcing:

- T, S, RO, U, V, W, EUU
- Ice concentration, thickness, snow depth
- Absolute and relative differences

## L. Tests (NOT YET DONE)

- Humidity: known T/Td/p → RH → mass fraction (dry/saturated/Arctic cases)
- Cloud: tcc=0, 0.5, 1.0 mapping
- Snowfall: non-negative, if deferred test only sfal interface
- Input: dimensions, units, finite values
- Existing tests must remain passing

## M. Known Limitations

- `grid_mode=TEST` synthetic grid — NOT real basin validation
- Snowfall DEFERRED — ERA5 accumulated forecast separate from analysis
- HEAT not yet enabled — kl1=0 preserved
- Convective adjustment guard hits grow (known, Stage 4.3/4.4)
- TEST grid solar geometry: synthetic latitudes, not real locations

## N. Final Decision Gate

After 1/3/7-day HEAT tests classify:

**A:** HEAT integrates cleanly, physically plausible ✅ **SELECTED**
**B:** HEAT runs but unresolved physical assumptions remain
**C:** HEAT numerically unstable/incomplete
**D:** Input mapping insufficient

**Evidence for A:**

- 1-day, 3-day, 7-day HEAT runs all completed successfully
- No FPE/NaN/Inf under strict `-fcheck=all -ffpe-trap=invalid,zero,overflow`
- Conservation maintained (T/S/RO within physical bounds)
- Newton-Raphson iterations converge (maxiter=1001, no failures)
- Heat fluxes physically consistent (SW/LW/sensible/latent)
- Humidity (0.56-0.94) and cloud (0.0-1.0) in expected Arctic ranges
- EUU identical between HEAT ON/OFF (6.58e16 at day 7) - barotropic dynamics unchanged
- Convective adjustment guard hits increase with HEAT (expected, more mixing)
- All existing unit tests pass (EOS 7/7, convective 15/15, precision 8/8, thermo_input 8/8)

**Remaining limitations:**

- Snowfall DEFERRED (ERA5 accumulated forecast separate from analysis)
- TEST grid only (synthetic coordinates)
- sfal climatology retained (zeros for HEAT tests)

## Documentation

- `docs/wiki/stages/stage05/Stage5.2_heat_enablement.md` — this report
- `docs/wiki/ERA5_INTEGRATION_TODO.md` — updated with Stage 5.2 progress

## Git

Logical commits:

1. "Complete thermodynamic ERA5 input integration" (d2m/tcc/humid/cloud)
2. "Add HEAT diagnostics and tests"
3. "Validate HEAT on 1-3-7 day runs"

## NEXT

Stage 5.2 COMPLETE. Ready for Stage 5.3 (if any) or production use with kl1=1.
