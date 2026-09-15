# Stage 5.5b — Q1 2020 Output & Unit Audit Report

## 1. Scope

Post-processing integrity audit of the January–March 2020 run (91-day ERA5
forcing, HEAT ON on the TEST grid) with three deliverables:

1. **Calendar audit** — exact model-day → calendar-date mapping across the
   leap year boundary (Jan 31 → Feb 29 → Mar 30).
2. **Unit audit** — full inventory of internal vs. external units and the
   standardization of the NetCDF interface to canonical SI units.
3. **Physical-extremes audit** — location, wet/dry status, EOS-consistency
   verification, and classification of the extreme T/S/RO values.

Run manifest: `data/output/run_manifest_2020_Q1_HEAT_ON.json` (90 days,
validated, PASS). All analysis uses the manifest — never a bare glob of
`results_day_*.nc` (AGENTS.md §8b).

## 2. Calendar audit

Output: `data/output/q1_calendar_audit.csv`.

- **90 model days** (day 1 = 2020-01-01 … day 90 = 2020-03-30).
- Model-day → date = `start + (day-1)` days. No duplicates, no gaps.
- **Month counts:** January 31 days, **February 29 (leap year 2020)**, March 30 days.
- **Day 59 = 2020-02-28**, **Day 60 = 2020-02-29** (leap day present — model
  stays on Gregorian calendar across the boundary).
- **Day 90 = 2020-03-30** — the run is 90 not 91 days because the model caps at
  `mm1 = min(91, (era5_ntime-1)/nperday)` = `(364-1)/4` = 90 (main.f90:244–245).
  The last ERA5 slice is used as forcing on the final model day; there are no
  leftover unused slices.
- All 90 files `results_day_01.nc … results_day_90.nc` exist and are
  IEEE/CF-clean; `results_day_final.nc` is a copy of the day-90 state.

## 3. Unit audit

Output: `data/output/q1_units_audit.csv` (22 rows), plus
`docs/wiki/stages/stage05/Stage5.5b_units.md` for the full rationale.

The model is internally CGS hydrodynamics / Celsius thermodynamics (historical
Dmitriev–Nesterov). The external NetCDF interface now exports **canonical SI**,
converting only at the output boundary — internal state is byte-for-byte
unchanged.

| Variable | Internal | NetCDF (after 5.5b) |
|---|---|---|
| temperature | °C | **K** (`+273.15`) |
| air_temp | °C | **K** (`+273.15`) |
| salinity → `salinity_mass_fraction` | mass fraction 0.033–0.035 | **1 (kg/kg)** — NOT PSU |
| density → `density_anomaly` | g cm⁻³ anomaly (ρ−1.02) | **kg m⁻³** (`×1000`) |
| u/v/w_velocity | cm s⁻¹ | **m s⁻¹** (`×0.01`) |
| wind_x/y | cm s⁻¹ | **m s⁻¹** (`×0.01`) |
| tau_x/y | dyn cm⁻² | **Pa** (`×0.1`) |
| dp_x/y | hPa km⁻¹ | **Pa m⁻¹** (`×0.1`) |
| air_press | hPa | **Pa** (`×100`) |
| humidity, cloud | fraction 0–1 | 1 |
| era5_snowfall_rate | m s⁻¹ water equiv. | m s⁻¹ |
| latitude/longitude | degrees | degrees |
| depth / depth_w | cm | m (`×0.01`) |

### Verification

- `fpm build -Wall -Wextra` clean; `fpm test` all suites pass (conv 15/15,
  EOS 7/7, snowfall 9/9, thermo_input 13/13, EOS precision 8/8, NetCDF
  validation suite).
- 90-day run regenerated; every `results_day_*.nc` + `results_day_final.nc`
  carries the `unit_system = "SI (canonical external units, Stage 5.5b)"`
  global attribute and SI unit attributes.
- `python/analysis/validate_q1_output.py` — **PASS**: calendar (90 days,
  Feb 29, day-90 = 2020-03-30) + units (all 22 fields) + bounds sanity.
- All Python analysis/plotting consumes the SI interface and converts to
  presentation units via `python/analysis/units.py` (single source of truth).

## 4. Physical-extremes audit

Output: `data/output/q1_extremes_audit.{txt,csv}`.

Method: for each of the 90 daily files, scan full-volume wet cells (kt1 > k),
mask land/fill, find global min/max of T, S, RO. For each extreme verify
(i) location (day/i/j/k), (ii) fully-wet column vs. boundary, (iii)
**EOS-consistency** — recompute `density_anomaly` from stored T/S with the
float32 Eckart EOS and require agreement with the stored RO (rule out unit /
rounding artifacts).

### Extreme values (canonical SI)

| Extreme | Value | Location | Classification |
|---|---|---|---|
| Tmax | 335.823 K (62.7 °C) | day 64, i=10, j=89, k=0 (2.5 m) | **E instability** |
| Tmin | 249.217 K (−23.9 °C) | day 84, i=114, j=67, k=17 (600 m) | **E instability** |
| Smin | −8.34e-4 | day 90, i=16, j=89, k=1 | **C mask/measure** |
| Smax | 3.694e-2 (36.9 g/kg) | day 90, i=118, j=68, k=17 | **A valid** |
| ROmin | −29.55 kg m⁻³ | day 90, i=16, j=89, k=0 | **B derived** |
| ROmax | +10.16 kg m⁻³ | day 90, i=118, j=68, k=17 | **A valid** |

Classification key: **A** valid physical state, **B** derived-consistent,
**C** mask/measure, **D** output bug, **E** instability, **F** physics artifact.

### EOS-consistency results

| Case | T (°C) | S | RO_stored | RO_EOS | Δ |
|---|---|---|---|---|---|
| Tmax cell | +62.673 | 0.028636 | −17.926 kg m⁻³ | −17.926 | 9.5e-7 |
| Smin cell | +14.649 | −0.000834 | −21.485 kg m⁻³ | −21.485 | 4.8e-7 |
| Tmin cell | −23.933 | 0.036688 | +8.655 kg m⁻³ | +8.655 | 1.2e-4 |
| Smax cell | −7.200 | 0.036943 | +10.161 kg m⁻³ | +10.161 | 0.0 |

All Δ within float32 rounding ⇒ **every extreme is a genuine stored T/S state,
exactly reproduced by the model EOS. No unit-conversion artifact.**

### Interpretation

- **Tmax 62.7 °C at 2.5 m (day 64, 79.7°N, 32.5°E, fully-wet column):** a
  surface hot layer that persists ~day 63–65 (62.5 → 62.7 → 56.8 °C). It is
  adjacent to the northern land edge (j+1 = land) and is a real model state
  under HEAT ON. Unphysical for 79.7°N but consistent with the historical
  surface-heating parameterization on the synthetic TEST grid. Classified
  **E** (thermodynamic instability/localized surface heating) — not a unit,
  mask, or output bug.
- **Tmin −23.9 °C at 600 m (day 84):** deep-cell cooling far below the
  salinity freezing point (≈ −1.98 °C at S=0.0367). Transient (day 83 −22.0 °C,
  day 85 −11.8 °C). EOS-consistent ⇒ real state produced by deep-layer heat
  flux on the TEST grid. Classified **E**.
- **Smin −8.34e-4 (negative salinity):** physically impossible sign; occurs at
  the same column family as ROmin, driven by excessive surface freshening on
  the TEST grid. Classified **C** (measurement/mask concern — negative mass
  fraction must not be interpreted as physical), documented, not fixed (physics
  change forbidden without promt.md).
- **Smax / ROmax (deep, day 90):** brine-enriched bottom water; **A** valid.
- **ROmin −29.55 kg m⁻³:** EOS consequence of T=43.7 °C / S≈0 at the surface —
  **B** derived-consistent (density is a derived diagnostic, so the extreme
  inherits the T/S state).

**Bottom line:** extremes are genuine model states on the synthetic TEST grid,
all EOS-consistent, correctly reported in canonical SI. None indicates a unit
conversion, masking, or output-write defect. They must NOT be used for
production/Arctic claims (TEST grid only).

## 5. Changed files

| File | Change |
|---|---|
| `src/netcdf_output.f90` | Canonical SI output buffers, renames (`salinity_mass_fraction`, `density_anomaly`), K/Pa/m s⁻¹ unit attributes, `unit_system` global attr |
| `test/check.f90` | SI bounds, `salinity_mass_fraction` lookup, rescaled sign-alignment thresholds |
| `python/analysis/units.py` | **new** — central presentation-unit conversions |
| `python/analysis/validate_q1_output.py` | **new** — calendar + units + bounds integrity validation |
| `python/analysis/{seasonal_analysis,profiles,snowfall_diagnostics,heat_diagnostics,convective_analysis,eos_precision_analysis,convective_precision_study}.py` | canonical SI names + units.py conversions; `profiles.py` now manifest-based |
| `python/plotting/{plots,seasonal_plots,convective_plots}.py` | canonical SI names + conversions |
| `data/output/q1_calendar_audit.csv`, `q1_units_audit.csv`, `q1_extremes_audit.{txt,csv}` | **new** audit artifacts |
| `docs/wiki/stages/stage05/Stage5.5b_units.md` | **new** — full unit inventory + rationale |

## 6. Verification matrix

| Check | Result |
|---|---|
| `fpm build -Wall -Wextra` | ✅ |
| `fpm test` (conv 15/15, EOS 7/7, snowfall 9/9, thermo 13/13, precision 8/8, NetCDF) | ✅ |
| 90-day Q1 run (SI outputs) | ✅ EXIT=0 |
| Calendar audit (90 days, Feb 29, day 90 = Mar 30) | ✅ |
| Unit audit (22 fields → canonical SI) | ✅ |
| EOS-consistency of all extremes | ✅ (Δ ≤ 1.2e-4) |
| `validate_q1_output.py` | ✅ PASS |
| Python scripts compile + run | ✅ |
| Manifest regenerated + validated | ✅ PASS |

## 7. Constraints honored

- **No internal physics changed** — conversions only at the output boundary.
- EOS, convective threshold 0.9e-7, 1000-iteration guard, blocks 200/210/280,
  shallow water, FCT, grid — untouched.
- TEST grid only — no production claims. Extremes documented, not "fixed".
- kl1=1 HEAT as in Stage 5.5; no new forcing fields.
- No REAL64 in production; Python does not recompute EOS (reads stored anomaly).