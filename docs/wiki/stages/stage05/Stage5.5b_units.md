# Stage 5.5b — Unit Audit: Canonical SI External Interface

## 1. Purpose

The external NetCDF interface (`src/netcdf_output.f90`) and the Python
analysis/plotting scripts must speak one unambiguous unit system. Internal
model state is CGS hydrodynamics / Celsius thermodynamics (historical Dmitriev–
Nesterov model). **Internal physics is unchanged** — conversions happen only at
the output boundary and in presentation-layer Python (`python/analysis/units.py`).

## 2. Canonical external unit baseline

| Quantity               | Canonical SI unit           | Internal unit | Conversion at output boundary  |
| ---------------------- | --------------------------- | ------------- | ------------------------------ |
| length                 | m                           | cm            | `×0.01`                        |
| time                   | s                           | s             | —                              |
| temperature            | **K**                       | °C            | `+273.15`                      |
| velocity (U/V/W, wind) | **m s⁻¹**                   | cm s⁻¹        | `×0.01`                        |
| wind stress τ          | **Pa**                      | dyn cm⁻²      | `×0.1` (1 dyn/cm² = 0.1 Pa)    |
| pressure gradient ∇p   | **Pa m⁻¹**                  | hPa km⁻¹      | `×0.1` (1 hPa/km = 0.1 Pa/m)   |
| pressure               | **Pa**                      | hPa           | `×100`                         |
| density anomaly        | **kg m⁻³**                  | g cm⁻³        | `×1000` (anomaly ρ−1.02 g/cm³) |
| salinity               | **1** (kg/kg mass fraction) | 1             | — (NOT PSU)                    |
| humidity, cloud        | **1**                       | 1             | —                              |
| snowfall rate          | **m s⁻¹** (water equiv.)    | m s⁻¹         | —                              |

## 3. Variable inventory (as written by `src/netcdf_output.f90` after Stage 5.5b)

| NetCDF variable          | Internal array            | Canonical units              | Physical meaning                              | Absolute/Anomaly |
| ------------------------ | ------------------------- | ---------------------------- | --------------------------------------------- | ---------------- |
| `temperature`            | `t2(i,j,k)`               | K                            | sea water temperature                         | absolute         |
| `salinity_mass_fraction` | `s2(i,j,k)`               | 1 (kg/kg)                    | salinity, mass fraction                       | absolute         |
| `density_anomaly`        | `ro(i,j,k)`               | kg m⁻³                       | **density anomaly** ρ−1.02 g/cm³ (Eckart EOS) | **anomaly**      |
| `u_velocity`             | `u2(i,j,k)`               | m s⁻¹                        | ocean velocity, model X (j index)             | absolute         |
| `v_velocity`             | `v2(i,j,k)`               | m s⁻¹                        | ocean velocity, model Y (i index)             | absolute         |
| `w_velocity`             | `w(i,j,k)`                | m s⁻¹                        | vertical ocean velocity                       | absolute         |
| `wind_speed`             | `wind(i,j)`               | m s⁻¹                        | wind speed magnitude                          | absolute         |
| `wind_x` / `wind_y`      | `windx/windy(i,j)`        | m s⁻¹                        | wind velocity components                      | absolute         |
| `tau_x` / `tau_y`        | `tx/ty(i,j)`              | Pa                           | surface wind stress components                | absolute         |
| `dp_x` / `dp_y`          | `dpx/dpy(i,j)`            | Pa m⁻¹                       | sea-level pressure gradient                   | absolute         |
| `air_temp`               | `tatm(i,j)`               | K                            | air temperature (ERA5 t2m)                    | absolute         |
| `air_press`              | `patm(i,j)`               | Pa                           | atmospheric pressure (ERA5 msl)               | absolute         |
| `humidity`               | `humid(i,j)`              | 1                            | relative humidity (from d2m/t2m)              | absolute         |
| `cloud`                  | `cloud(i,j)`              | 1                            | total cloud cover (ERA5 tcc)                  | absolute         |
| `era5_snowfall_rate`     | `era5_snowfall_rate(i,j)` | m s⁻¹                        | ERA5 snowfall water-equivalent rate           | absolute         |
| `latitude` / `longitude` | `fi/dl(i,j)`              | degrees_north / degrees_east | grid geography                                | absolute         |
| `depth` / `depth_w`      | `z(k)` / derived          | m                            | level centers / W boundaries                  | absolute         |
| `water_column_levels`    | `kt1(i,j)`                | 1                            | active level count (mask)                     | absolute         |

## 4. Key scientific decisions

1. **`density` → `density_anomaly`, units `g cm-3` → `kg m-3` (×1000).**
   The Eckart EOS in `src/equation_of_state.f90` returns `RO = 1/(0.698+aa/bb) − 1.02`,
   i.e. the _anomaly_ relative to 1.02 g/cm³. Naming it `density` with `g cm-3`
   was misleading. It is now exported as `density_anomaly` in kg m⁻³
   (`RO[g/cm3] × 1000`). Python must never recompute EOS — it reads the stored
   anomaly (comment retained on the attribute).
2. **`salinity` → `salinity_mass_fraction`, units kept `1`.**
   Model S ≈ 0.033–0.035 is a **mass fraction** (≈33–35 g/kg), not PSU. The
   new name makes this unambiguous. No numeric change.
3. **`temperature` / `air_temp` → K.** Internal °C preserved; only boundary
   conversion (`+273.15`). All Python presentation converts back to °C via
   `units.temperature_k_to_c`.
4. **Velocities → m s⁻¹.** Internal cm s⁻¹ (`×0.01`). Components remain
   model-grid, NOT geographic eastward/northward (comment retained on
   `u_velocity`/`v_velocity`).
5. **Stress → Pa, pressure gradient → Pa m⁻¹, pressure → Pa.** Standard SI;
   `1 dyn/cm² = 0.1 Pa`, `1 hPa/km = 0.1 Pa/m`, `1 hPa = 100 Pa`.
6. **Global metadata:** `unit_system = "SI (canonical external units, Stage 5.5b)"`
   added to every output file; `Conventions = CF-1.10` retained.

## 5. Implementation

- `src/netcdf_output.f90`: local SI buffers (`t_k`, `ro_kgm3`, `u_ms`, …)
  computed from internal arrays right before `nf90_put_var`. Internal `param`
  state is never modified. Variable names + attributes updated.
- `python/analysis/units.py`: single source of truth for all presentation
  conversions (`temperature_k_to_c`, `velocity_mps_to_cmps`, `stress_pa_to_dyncm2`,
  `density_anomaly_kgm3_to_gcm3`, `salinity_mass_fraction_to_gkg`, …). All
  analysis/plotting scripts import from here; no hard-coded factors elsewhere.
- `test/check.f90`: bounds converted to SI (temp/air_temp in K, τ in Pa,
  ∇p in Pa m⁻¹, p in Pa, velocities in m s⁻¹) and variable renamed to
  `salinity_mass_fraction`.

## 6. Verification

- `fpm build -Wall -Wextra` ✅
- `fpm test` (conv 15/15, EOS 7/7, snowfall 9/9, thermo_input 13/13, EOS
  precision 8/8, NetCDF validation) ✅
- 90-day Q1 run regenerated: every `results_day_*.nc` and
  `results_day_final.nc` now carries canonical SI units and
  `unit_system` global attribute.
- `python/analysis/validate_q1_output.py`: calendar (90 days, Feb 29, day 90 =
  2020-03-30) + units (all 22 fields) + bounds sanity → **PASS**.
- Extremes audit: all extreme T/S/RO values reproduced exactly by the float32
  Eckart EOS from the stored T/S ⇒ **no unit-conversion artifact** (see
  `docs/wiki/stages/stage05/Stage5.5b_q1_output_and_units_audit.md`).

## 7. Non-changes

- No internal physics changed. `kl1=1` HEAT, convective-adjustment guard,
  EOS float32, threshold `0.9e-7`, blocks 200/210/280, `shallow_water` are all
  untouched.
- `sfal(12)` climatology (model-internal) retained; `era5_snowfall_rate`
  exported separately in m s⁻¹.
- TEST grid remains `grid_mode_test`; no production/Arctic claims.
