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
  of mean wind and T2m.  V1 is split into separate atmosphere and ocean 6×3
  matrices because the old 6×6 matrix was not readable.  5 PNG/PDF figures.
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


## 5. Visual audit and corrections

Contact sheets for A, B, V and G were inspected.  Defects found and corrected:

| Figure group | Defect | Correction |
| --- | --- | --- |
| A maps | Colorbar was drawn over the right panels; right column repeated y labels; scales clipped T/S/current extremes; vectors were nearly invisible | Dedicated outside cax, shared labels, masks, visible scales (T −2.1…20 °C, S 0…37 psu, speed 0…1 m s⁻¹), white vectors |
| B1 sections | Colorbar overlapped panel b/d; sections extended beyond the requested 70–82°N and 15–65°E ranges; T scale clipped 9.5 °C | Outside cax; exact section windows; T −2…10 °C; no vertical interpolation |
| B2 profiles | No 2020/2024 row labels; S/σθ tick labels touched; margins clipped x labels | Year labels, MaxNLocator(3), wider margins, shared depth axis |
| B3 profiles | Unweighted monthly means and equal-cell percentiles | Month-day and cos(latitude) weights in mean and 10–90 percentiles |
| V1 forcing | 6 × 6 matrix was unreadably dense | Split into two 6 × 3 figures: atmosphere and ocean |
| V2 annual cycle | Year annotation sat on the wind/T curves; equal-cell area mean | Year moved to clear corner; cos(latitude) area weighting |
| V3 maps | Colorbar over panels; T2m limit clipped 16.7 °C; right y labels | Outside cax; T2m −30…18 °C; single left latitude scale |
| G histograms | 2020/2024 used different bin edges | Shared bin edges per variable |
| All | `save_fig()` only checked the border | Added text-boundary check and PNG/PDF existence/size checks |

### Seasonal convention

Conventional meteorological DJF (previous December + January + February) cannot
be formed for 2020/2024 because December 2019/2023 is outside the acquired
period.  Panels are therefore labelled **cold (Jan+Feb+Dec)** and use January,
February and December of the same calendar year.  This is not claimed to be
conventional DJF.

Monthly mean fields are weighted by the number of days in each month.  Regional
area means and the B3 percentiles use `cos(latitude)` cell weights.  The A maps
are fields, not area means, so no area weighting is applied to the plotted field.

### Remaining limitations

- B2 uses the nearest wet GLORYS column; the selected column can change between
  months and the monthly selected coordinates are not saved separately.
- A map CSVs are decimated by stride 8 for repository size; the figures use the
  full field.
- Automated checks cover text outside the canvas, white borders, file presence
  and PNG width.  Text-overlap and colorbar placement remain manual visual
  checks from the contact sheets.
- The audit changes were committed separately after the visual review.


## 6. Stage 12.21b corrections

- **12.20 track speed:** the lower panel now uses displacement between adjacent daily
  track records divided by elapsed seconds, not the missing `ds.u/ds.v` columns.
  FJL_A_2020 mean is 0.100 m s⁻¹, matching 2771.7 km in 323.8 d.
- **Daily displacement audit:** `figures/stage12.20/final/track_speed_summary.csv`
  records maximum daily displacement, mean speed and any >100 km/day intervals.
  All eight runs have maximum daily displacement below 100 km/day; no gap-induced
  line break was needed. See the per-run `track_speed_audit.csv`.
- **12.20 labels:** water salinity is `psu`; ice fraction is `φ`; panel letters
  are outside the data areas.
- **12.21 maps:** land is `#d9d9d9`; sea ice is zero-filled over the GLORYS ocean
  mask; 100/500 m isobaths are shown with a common key; current and wind vectors
  have a single reference arrow; FJL bounds are 25–68°E, 74–83.5°N.
- **12.21 sections/profiles:** B1 T is −2…8 °C with an `extend` arrow, year labels
  are lower-left, and land is grey. B2 fixes one wet column per point/year and
  records its latitude/longitude/depth in the CSV and manifest.
- **12.21 V/G:** V1 has separate atmosphere/ocean matrices and wider spacing; V2
  uses ocean-only area means and shared row axes; V3 has wind vectors, isobaths,
  and the required scales; G1 uses relative frequency, common bins and N values.
- **PDF policy:** PDFs are ignored in git and archived in
  `data/validation/stage12.21/journal_pdf_vectors.zip`; only PNG/CSV remain in
  the repository figure tree. The figure directory is 59 MB after removing
  tracked PDFs; the PDF archive is 19 MB.

### Remaining limitations

- The B2 wet column is fixed per point/year, but the vertical mask still removes
  individual depth cells; no interpolation is used.
- A map CSVs are decimated by stride 8; the plotted field uses all grid cells.
- Automated checks cover text outside, white borders, output existence and PNG
  width. Text-overlap/colorbar placement is checked visually with contact sheets.
- No model runs, downloads, NetCDF changes or Fortran edits were made.
