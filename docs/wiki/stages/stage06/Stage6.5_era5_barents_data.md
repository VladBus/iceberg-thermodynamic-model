# Stage 6.5 — ERA5 Barents Data Replacement + Unit/Plot Consistency Audit

**Generated:** 2026-08-19  
**Status:** Complete — Barents ERA5 data acquired, validated, and set as default forcing

---

## Executive Summary

Stage 6.5 replaced the historical Arctic-domain ERA5 forcing with the intended **Barents Sea research domain** (70–90°N, 10–70°E, expanded to 66–90°N to cover the TEST model grid). All validation passes. The external NetCDF interface remains canonical SI. Python presentation conversions are correct and delegated to `units.py`. No physics changes.

---

## 1. Data Acquisition

### Downloaded Files (Barents Expanded Domain: 66–90°N, 10–70°E)

| Month   | Instantaneous File                                                            | Snowfall File                                                                    | Merged File                                                                      |
| ------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 2020-01 | `data/input/raw/era5/2020/2020_01/era5_2020_01_barents_expanded.nc` (22.5 MB) | `data/input/raw/era5/2020/2020_01/snowfall_2020_01_barents_expanded.nc` (1.5 MB) | `data/input/processed/era5/2020/2020_01/era5_2020_01_barents_expanded_merged.nc` |
| 2020-02 | `data/input/raw/era5/2020/2020_02/era5_2020_02_barents_expanded.nc` (21.3 MB) | `data/input/raw/era5/2020/2020_02/snowfall_2020_02_barents_expanded.nc` (1.5 MB) | `data/input/processed/era5/2020/2020_02/era5_2020_02_barents_expanded_merged.nc` |
| 2020-03 | `data/input/raw/era5/2020/2020_03/era5_2020_03_barents_expanded.nc` (22.6 MB) | `data/input/raw/era5/2020/2020_03/snowfall_2020_03_barents_expanded.nc` (1.6 MB) | `data/input/processed/era5/2020/2020_03/era5_2020_03_barents_expanded_merged.nc` |

### Q1 Combined File

**Default model input:** `data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc`

- Time: 2020-01-01 00:00 to 2020-03-31 18:00 (364 steps, 6-hourly)
- Latitude: 66–90°N (97 points, decreasing)
- Longitude: 10–70°E (241 points, increasing)
- Variables: u10, v10, t2m, d2m, msl, tcc, sf (snowfall rate in m/s)

### Superseded Files (Archived)

Moved to `data/archive/superseded_barents/`:

- Original Barents-domain downloads (70–90°N only, did not cover model grid)
- Old merged files from those downloads

---

## 2. Domain Verification

### ERA5 Forcing Domain vs Model Grid

| Aspect                             | Value                                                                   |
| ---------------------------------- | ----------------------------------------------------------------------- |
| **ERA5 Forcing Domain (expanded)** | 66–90°N, 10–70°E (CDS area [90, 10, 66, 70])                            |
| **Model Grid (TEST mode)**         | 66–82°N, 30–63°E (synthetic, from param.f90)                            |
| **Original Barents domain**        | 70–90°N, 10–70°E — **did not cover model grid** (model extends to 66°N) |
| **Historical Arctic domain**       | 65–90°N, -180–180°E (previously used)                                   |

**Key finding:** The original Barents domain (70–90°N) was **insufficient** because the TEST model grid extends to 66°N. The expanded domain (66–90°N) fully covers the model grid.

### check_era5.py Validation Results

```
SPATIAL COVERAGE
  latitude : 66.00 .. 90.00 (decreasing=True)
  longitude: 10.00 .. 70.00
  expected domain: custom [area [90.0, 10.0, 66.0, 70.0]]
  domain coverage: OK
```

All variables: finite, correct units, within physical ranges.

---

## 3. ERA5 Variables & Units

### Raw ERA5 (Preserved Native Units)

| Variable | CDS Name                | Units           | Notes                  |
| -------- | ----------------------- | --------------- | ---------------------- |
| u10      | 10m_u_component_of_wind | m s-1           |                        |
| v10      | 10m_v_component_of_wind | m s-1           |                        |
| t2m      | 2m_temperature          | K               |                        |
| d2m      | 2m_dewpoint_temperature | K               |                        |
| msl      | mean_sea_level_pressure | Pa              |                        |
| tcc      | total_cloud_cover       | (0 - 1)         | Fraction               |
| sf       | snowfall                | m (water equiv) | 12-hourly accumulation |

### Merged File (Model-Ready)

| Variable | Units | Notes                                      |
| -------- | ----- | ------------------------------------------ |
| u10, v10 | m s-1 | 6-hourly                                   |
| t2m, d2m | K     | 6-hourly                                   |
| msl      | Pa    | 6-hourly                                   |
| tcc      | 1     | 6-hourly                                   |
| sf       | m s-1 | **Snowfall RATE** (accumulation / 43200 s) |

**Snowfall conversion verified:** Raw accumulation (m water equivalent per 12h) ÷ 43200 s = rate in m/s. Max rate ~5.6e-8 m/s (January Barents).

---

## 4. Unit Conversion Audit: NetCDF → Python Presentation

### Complete Trace for Key Variables

| Variable                   | NetCDF (SI) | Python units.py                  | Presentation Unit | Example (Day 01)                     |
| -------------------------- | ----------- | -------------------------------- | ----------------- | ------------------------------------ |
| **temperature**            | K           | `temperature_k_to_c()`           | °C                | 273.15 → 0.00 °C; 296.77 → 23.62 °C  |
| **air_temp**               | K           | `temperature_k_to_c()`           | °C                | 244.91 → -28.24 °C; 273.40 → 0.25 °C |
| **u_velocity**             | m/s         | `velocity_mps_to_cmps()`         | cm/s              | 0.1016 → 10.16 cm/s                  |
| **v_velocity**             | m/s         | `velocity_mps_to_cmps()`         | cm/s              | 0.1386 → 13.86 cm/s                  |
| **w_velocity**             | m/s         | `velocity_mps_to_cmps()`         | cm/s              | 4.3e-4 → 0.043 cm/s                  |
| **wind_x**                 | m/s         | `velocity_mps_to_cmps()`         | cm/s              | 9.46 → 946 cm/s                      |
| **wind_y**                 | m/s         | `velocity_mps_to_cmps()`         | cm/s              | 10.06 → 1006 cm/s                    |
| **density_anomaly**        | kg/m³       | `density_anomaly_kgm3_to_gcm3()` | g/cm³             | 4.50 → 0.00450 g/cm³                 |
| **salinity_mass_fraction** | 1 (kg/kg)   | none (plotted as-is)             | mass fraction     | 0.035 (35 g/kg)                      |
| **tau_x, tau_y**           | Pa          | plotted as-is                    | Pa                | -0.128 to 0.243 Pa                   |
| **dp_x, dp_y**             | Pa/m        | plotted as-is                    | Pa/m              | -5e-5 to 3.7e-5 Pa/m                 |
| **air_press**              | Pa          | `pressure_pa_to_hpa()`           | hPa               | 97109 → 971.1 hPa                    |
| **humidity, cloud**        | 1           | plotted as-is                    | fraction          | 0.42–1.00                            |
| **era5_snowfall_rate**     | m/s         | plotted as-is                    | m/s               | 0 to 2.8e-8 m/s                      |

**All conversions verified via `test_units_roundtrip.py` — PASS**

---

## 5. Plotting Scripts: Hardcoded Conversion Search

### Search Results

```bash
grep -rn "*100\|*0.01\|*1000\|/1000\|/100\|273.15\|ZERO_C_K" python/plotting/ python/analysis/ --include="*.py" | grep -v units.py
```

**Only one match (unrelated):**

- `python/analysis/convective_analysis.py:210: events['nmix'].mean()/1001` — normalization by iteration count, not unit conversion

### Conclusion

**All unit conversions are correctly delegated to `python/analysis/units.py`.** No hardcoded factors in plotting scripts. This satisfies the Stage 5.5b architecture.

---

## 6. Plot Data Path Verification

### Run Context Resolution

All plotting scripts use `run_context.resolve_run()`:

- Accept `--run-id` (default: `2020_Q1_test_heat_on`)
- Resolves to `data/runs/<run_id>/output/{nc,csv,txt,logs,figures}`
- No globbing without run identification

### Manifest Validation

```bash
python python/analysis/run_manifest.py --run-id 2020_Q1_test_heat_on
# Expected days: 90, Files in manifest: 90, Validation: PASS
```

### Figure Generation

Figures written to: `data/runs/2020_Q1_test_heat_on/output/figures/`

| Script                | Figures Produced                                                                               |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| `plots.py`            | surface_T/S/velocity, daily_energy, convective_stats, vertical_profiles                        |
| `seasonal_plots.py`   | All time series, vertical profiles, surface maps, heat fluxes, snowfall                        |
| `convective_plots.py` | Guard evolution, nmix/k_problem, guard vs scalars, residual inversion, representative profiles |

**All scripts run successfully and read current NetCDF data.**

---

## 7. Data Architecture Compliance

### Maintained Structure

```
data/
  input/
    raw/era5/YYYY/YYYY_MM/           # Raw CDS downloads (Barents expanded)
    processed/era5/YYYY/YYYY_MM/     # Merged monthly files
    processed/era5/2020/2020_Q1/     # Q1 combined (DEFAULT)
  runs/
    2020_Q1_test_heat_on/
      manifest.json
      output/
        nc/      # results_day_00.nc ... results_day_90.nc
        csv/     # daily_diagnostics, seasonal_daily_summary, etc.
        txt/     # Reports
        logs/
        figures/ # All generated plots
  archive/
    pre_cleanup/
    test/
    superseded_barents/              # Old Barents (70-90N) downloads
```

### NOT Restored (Correct)

- `data/output/` — empty (legacy, not used)
- `python/plotting/figures/` — does not exist (generated figures under run dir)

---

## 8. Cleanup Classification

| Item                                                                       | Classification | Action                             |
| -------------------------------------------------------------------------- | -------------- | ---------------------------------- |
| `data/input/raw/era5/2020/2020_01/era5_2020_01.nc` (Arctic)                | **KEEP**       | Historical/regression reference    |
| `data/input/raw/era5/2020/2020_02/era5_2020_02.nc` (Arctic)                | **KEEP**       | Historical/regression reference    |
| `data/input/raw/era5/2020/2020_03/era5_2020_03.nc` (Arctic)                | **KEEP**       | Historical/regression reference    |
| `data/input/raw/era5/2020/2020_01/snowfall_2020_01.nc` (Arctic)            | **KEEP**       | Historical/regression reference    |
| `data/input/raw/era5/2020/2020_02/snowfall_2020_02.nc` (Arctic)            | **KEEP**       | Historical/regression reference    |
| `data/input/raw/era5/2020/2020_03/snowfall_2020_03.nc` (Arctic)            | **KEEP**       | Historical/regression reference    |
| `data/input/processed/era5/2020/2020_Q1/era5_2020_0103_merged.nc` (Arctic) | **KEEP**       | Regression baseline                |
| Original Barents (70-90N) downloads                                        | **ARCHIVE**    | `data/archive/superseded_barents/` |
| Original Barents merged files                                              | **ARCHIVE**    | `data/archive/superseded_barents/` |
| `data/input/raw/era5/era5_test.nc`                                         | **ARCHIVE**    | `data/archive/`                    |
| `data/output/`                                                             | **DELETE**     | Already empty                      |
| `python/plotting/figures/`                                                 | **DELETE**     | Never recreated                    |

---

## 9. Test Results

| Test                 | Command                                              | Result             |
| -------------------- | ---------------------------------------------------- | ------------------ |
| Fortran build        | `fpm build -Wall -Wextra`                            | ✅ PASS            |
| Fortran tests        | `fpm test` (EOS 7/7, Convective 15/15, NetCDF)       | ✅ PASS            |
| Strict run (1 day)   | `fpm run -fcheck=all -ffpe-trap`                     | ✅ Clean start     |
| Unit round-trip      | `python/python/tests/test_units_roundtrip.py`        | ✅ PASS            |
| Q1 output validation | `python/analysis/validate_q1_output.py`              | ✅ PASS (0 errors) |
| Run manifest         | `python/analysis/run_manifest.py --validate`         | ✅ PASS (90 days)  |
| ERA5 domain check    | `python/era5/check_era5.py --area 90 10 66 70`       | ✅ PASS            |
| All plotting scripts | `python/plotting/*.py --run-id 2020_Q1_test_heat_on` | ✅ PASS            |

---

## 10. Physics Protection — Explicit Statement

**NO MODEL PHYSICS WAS CHANGED.**

Protected (unchanged):

- EOS (`equation_of_state.f90`)
- Convective threshold `0.9e-7`
- 1000-iteration convective guard
- Blocks 200/210/280
- FCT, advection, shallow water
- Tidal forcing, wind stress formulation
- Timestep, DX
- Synthetic TEST grid (66–82°N, 30–63°E)
- Initial conditions, physical constants
- Real-grid activation logic (KOORD.DAT, hhh.bar)

Changed (input data only):

- ERA5 forcing domain: Arctic → Barents expanded (66–90°N, 10–70°E)
- Default ERA5 input file updated in `src/param.f90:182`

---

## 11. Remaining Blockers

| Blocker                               | Status                                            |
| ------------------------------------- | ------------------------------------------------- |
| **CDS data availability**             | ✅ Resolved — Q1 2020 Barents expanded downloaded |
| **KOORD.DAT** (real grid coordinates) | ❌ Missing — real grid activation deferred        |
| **hhh.bar** (bathymetry/mask)         | ❌ Missing — real grid activation deferred        |
| **Real-grid activation**              | ❌ Deferred per Stage 3.5/6.1                     |

The model runs correctly with `grid_mode=TEST` (synthetic grid). Real grid requires authentic AARI archive files.

---

## 12. Git Status

### Files Modified (Committed)

1. `src/param.f90:182` — Updated default `era5_input_file` to Barents expanded Q1 merged file

### Files Not Tracked (Per .gitignore)

- All `data/` contents
- `docs/wiki/stages/stage06/Stage6.5_era5_barents_data.md` (this file)
- `docs/wiki/ERA5_INTEGRATION_TODO.md`
- Generated figures, NetCDF outputs, CSV diagnostics

---

## 13. Key Clarification: "Unchanged" Graphs

**Q:** "Why do plots look the same even though NetCDF units changed?"

**A:** The visual appearance is unchanged because:

1. NetCDF stores canonical SI (m/s, kg/m³, K)
2. Python reads SI values and applies **exact same presentation conversions** as before
3. `units.py` functions are unchanged and tested reversible
4. Axis labels correctly show presentation units (cm/s, g/cm³, °C)
5. The **physical data is identical** — only the external NetCDF metadata was already correct

The unit audit (Stage 6.4) confirmed the NetCDF interface was **already canonical SI**. Stage 6.5 only changed the **spatial coverage of input forcing**, not the unit architecture.

---

_Stage 6.5 complete — Barents ERA5 data acquired, validated, and operational._
