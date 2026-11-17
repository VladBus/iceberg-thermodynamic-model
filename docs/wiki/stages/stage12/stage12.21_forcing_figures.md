# Stage 12.21 — Forcing and region figures

**Status:** COMPLETE (figure pass; no model runs)
**Date:** 2026-11-17
**Scope:** English figure set from the existing ERA5/GLORYS12 data for 2020 and
2024; no climatology, waves, station comparison or interannual difference.

## 1. Data and regions

The requested path `data/input/processed/reanalysis/...` is empty on this
machine.  The existing complete files are under
`data/input/reanalysis/glorys/{2020,2024}/` (monthly, daily means) and
`data/input/reanalysis/era5/{2020,2024}/` (monthly, daily means); these were
used.  GLORYS12 is `GLOBAL_MULTIYEAR_PHY_001_030`, 1/12°, native 32 levels,
surface and 100 m maps use the nearest native levels 0.494 m and 92.326 m.
ERA5 fields are daily means; units are converted at plotting time.

Regions (track envelope plus 2.5°):

| Region | Latitude | Longitude |
| --- | --- | --- |
| BARENTS | 63–86°N | 5–80°E |
| FJL | 72.5–85°N | 25–48°E |
| NZ | 71–83°N | 40–71°E |

The six 12.20 tracks are read explicitly from
`data/validation/stage12.20/final/<run>/run.nc`; no glob of model output.

## 2. Blocks

- **Block 0:** Stage 12.20 panels re-rendered in English from existing data.
  Russian originals are preserved in
  `figures/stage12.20/final/ru/`; English panels are in `final/`.
- **A:** GLORYS12 maps at 0.5 m and 100 m for current speed/vectors, temperature
  and salinity, annual/DJF/JJA, 2020 and 2024.  Sea-ice concentration is present
  in GLORYS12 and is shown as an additional map.  21 PNG/PDF figures.
- **B:** January/July sections at 40°E (70–82°N) and 76°N (15–65°E), 0–500 m
  on native levels; profiles at FJL_A, NZ_A, NZ_B and Barents-1 for DJF/JJA
  0–300 m; BARENTS mean profiles with 10–90 percentile bands.  `sigma_0` uses
  the project's UNESCO EOS-80 density at p=0.  10 PNG/PDF figures.
- **V:** ERA5/GLORYS12 forcing along the six 12.20 tracks (T2m, wind, MSL,
  surface water T/S/current), the BARENTS annual cycle, and winter/summer maps
  of mean wind and T2m.  4 PNG/PDF figures.
- **G:** histograms over track samples and a descriptive statistics table
  (CSV + LaTeX tabular).  1 figure + table.

All PNG are 300 dpi and each figure has a vector PDF and a data CSV beside it.
The common manifest is `figures_manifest.csv` (file, variable, source, period,
level/depth, aggregation method, region).  PDF pcolormesh layers are rasterized
inside the vector file to keep the files usable.

## 3. Validation and caveats

- Observed ranges in the track samples: water T −2.33…+5.84 °C, S
  33.88–35.07 psu, current ≤0.909 m s⁻¹, air T −28.65…+8.27 °C.
  Water T has a small lower excursion below the requested −2 °C (−2.33 °C); it
  is recorded, not clipped.  The other ranges are inside the requested limits.
- Some GLORYS profiles contain a single masked depth cell; no vertical
  interpolation was applied.  Land and shallow cells remain masked.
- WAM/waves, climatological normals, station comparisons and interannual
  differences were intentionally not produced.
- No Fortran model code or model run was touched; fpm was not run.

## 4. Outputs

`figures/stage12.21/A`, `B`, `V`, `G`; Block 0 in
`figures/stage12.20/final` with Russian copies in `final/ru/`.  The manifest is
the source of truth for file/field/level provenance.
