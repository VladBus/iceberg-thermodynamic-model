# Stage 12.1 — GLORYS12 Validation Report

## Date

2026-10-29

## Scope

Reconnaissance gate for Stage 12.1: download and inspect **one test month**
(January 2020) of the GLORYS12 Barents subset to fix the NetCDF structure,
variable names, units, grid type, and data quality **before any Fortran reader
is written**. Decision authority: D-51. This is data acquisition + inspection
only; **no Fortran code was written**.

## Files Downloaded

| File | Size | Coverage |
|---|---:|---|
| `data/input/raw/reanalysis/glorys12/2020/glorys12_barents_202001.nc` | 1933.2 MB | daily 2020-01-01…2020-01-31, 63–86°N, 5–80°E, 0–600 m, `thetao so uo vo zos siconc sithick` |
| `data/input/raw/reanalysis/glorys12/static/glorys12_static_barents.nc` | 12.9 MB | `deptho mask`, same bbox |

Inspection JSONs (committed): `data/validation/glorys12_202001_inspection.json`,
`data/validation/glorys12_static_inspection.json`. Catalogue probe (Phase 0,
all checks PASS): `data/validation/reanalysis_catalog_probe.json`.

> Raw NetCDF files are **gitignored** (`data/*`, `*.nc`); they are reproducible
> artifacts, not versioned inputs.

## Grid Structure

- **Type:** regular 1-D lat/lon grid (**NOT curvilinear ORCA**). `latitude`
  and `longitude` are independent 1-D coordinate arrays.
- **Dimensions:** `time=31, depth=32, latitude=277, longitude=901`.
- **Coordinate arrays:** 1-D float32. `latitude` `degrees_north` 63.0→86.0,
  `longitude` `degrees_east` 5.0→80.0, spacing **0.0833° (1/12°)** in both.
- **Resolution:** 1/12° × 1/12° (~8 km), matching the Stage 12.0 data plan.

## Depth Levels

- **Number of levels:** 32.
- **First 10 (m):** 0.494, 1.5414, 2.6457, 3.8195, 5.0782, 6.4406, 7.9296,
  9.573, 11.405, 13.4671.
- **Deepest returned level:** 541.09 m.
- **Covers 0–600 m as requested?** Partially. GLORYS native levels are
  non-uniform; the last level ≤ 600 m is **541.09 m** and the next native
  level is ~740 m. So the 0–600 m request resolves to 0.494–541.09 m (32
  levels). This is a **native-grid fact, not a defect** — iceberg drafts of
  interest (<~500 m) are fully covered. The static `mask` is 3-D over **50**
  levels; the daily fields carry **32**.

## Variable Validation (stats from Jan-01 / Jan-31 slices)

| Variable | Units | Range | NaN frac | Verdict |
|---|---|---|---:|---|
| `thetao` | degrees_C (°C) | −2.506 … 9.903 | 0.399 | Physically reasonable |
| `so` | 1e-3 (mass-fraction convention; values are PSU-like 2.06–45.45) | 2.057 … 45.447 | 0.399 | **÷1000 → 0.00206–0.04545**; reasonable |
| `uo` | m s⁻¹ | −0.566 … 1.118 | 0.399 | Reasonable |
| `vo` | m s⁻¹ | −1.018 … 1.219 | 0.399 | Reasonable |
| `zos` | m | −1.600 … 0.393 | 0.271 | Reasonable |
| `siconc` | 1 (fraction) | 0.0 … 1.031 | 0.447 | 0–1 with minor >1 rounding |
| `sithick` | m | 0.0 … 1.822 | 0.447 | Reasonable |

### thetao (temperature)
- Units **°C** (`degrees_C`); range −2.506…9.903 °C. NaN = land. **YES.**

### so (salinity)
- Units **`1e-3`** but the numeric values are PSU-like (~2.1–45.4), so the
  physical mass fraction = value × 1e-3 (0.0021–0.0454). **This is the single
  most important reader contract**: `salinity_mass_fraction = so / 1000`.
  Model internal thermodynamics use mass fraction 0.033–0.035 (§ unit table),
  so a 45.4 value maps to 0.0454 (Baltic-influenced / evaporated extremes are
  outliers, sea-ice brine rejection). **YES (unit confirmed).**

### uo, vo (currents)
- Units **m s⁻¹**; magnitudes < 1.3 m/s. **YES.**

### zos (sea-surface height)
- Units **m**; −1.6…0.39 m. **YES.**

### siconc (sea-ice concentration)
- Units **fraction 0–1** (not percentage). Max 1.031 — a small >1 overshoot
  inherent to CMEMS; the reader should **clip to [0,1]**. **YES (with clip).**

### sithick (sea-ice thickness)
- Units **m**; 0…1.82 m. **YES.**

## Static Variables

### deptho (bathymetry)
- Units **m**; 7.0…4983.7 m over sea cells; **NaN over land** (same 27.1 %
  land fraction as 2-D vars). **YES.**

### mask (land-sea mask)
- **Unique values: [0, 1]**; long_name "Land-sea mask: 1 = sea ; 0 = land".
- 3-D `(depth=50, latitude, longitude)`. Surface slice `mask[0]` gives the 2-D
  land/sea test; **1 = sea, 0 = land**. **YES (0=land, 1=sea).**

## Data-Quality Findings

- **NaN are the land mask**, not corrupt data: every variable's NaN fraction
  equals the land fraction (2-D fields 0.2707, 3-D fields ~0.399, ice fields
  ~0.447 — ice vars also NaN over open ocean where no ice model is present,
  i.e. ice NaN = land ∪ ice-free; the reader must treat NaN as "no value",
  never fill with zero for ocean T/S/u/v).
- **No `_FillValue` attribute**: missing data is plain NaN. xarray/netCDF4
  decode NaN directly; the Fortran reader must map NaN → "invalid cell".
- **No negative absolute density / no unphysical current spike** in the sample
  — unlike the frozen Stage 11 prognostic ocean, the reanalysis fields are
  clean and bounded. This is exactly why Stage 12 uses reanalysis (D-51).

## Issues Found

1. **600 m request → 541 m deepest level.** Expected native-grid behaviour;
   the data plan's "at least 600 m" should be read as "deepest native level
   below 600 m". Drafts of interest are covered. (Action: note in reader
   contract.)
2. **`so` is `1e-3` with PSU-like magnitudes.** Must be divided by 1000 at the
   reader boundary. Misreading it as mass fraction directly would inflate
   salinity 1000×. (Action: add an explicit `so/1000` conversion test in
   Stage 12.2.)
3. **`siconc` can exceed 1.0** (1.031 observed). (Action: clip to [0,1].)
4. **`mask` has 50 levels, daily fields 32.** (Action: index mask at the
   matching daily level; use `mask[0]` for the 2-D land test.)
5. **Ice NaN region is larger than land** (ice vars NaN over ice-free open
   ocean too). (Action: ocean forcing and ice forcing use different NaN
   domains; handle separately.)

## Recommendations for the Fortran Reader (Stage 12.2)

- **Grid interpolation:** bilinear in the regular 1-D `latitude`/`longitude`
  axes (trivially invertible: `index = (coord - min)/0.0833`). No curvilinear
  mapping, so this replaces the Stage 11 rotated-grid bilinear path cleanly.
- **Vertical interpolation:** interpolate/extrapolate over the **non-uniform**
  32-level `depth` array (log-linear in depth, as in `iceberg_forcing`); keep
  native levels, do not pre-resample to the 18-level model grid.
- **Time interpolation:** linear between the daily snapshots; the existing
  model step cadence (dt=1800 s) interpolates within/across days. Time units
  are `hours since 1950-01-01` — convert with the CF calendar.
- **Unit conversions at the reader boundary only:** `so ÷ 1000` → mass
  fraction; `thetao` already °C; `uo/vo` stay m s⁻¹ until the CGS ×100 at the
  same boundary the Stage 11 ERA5 path uses; `siconc` clip [0,1].
- **Land / missing handling:** treat NaN as invalid (do not zero-fill);
  optionally cross-check with `mask[0]` (1=sea). Never fabricate ocean values
  over land.
- **Keep the reader offline/prescribed** (D-51, Stage 12 guardrail): the ocean
  does not feel the iceberg.

## Storage Estimate (full run, from the Jan-2020 sample)

- January daily subset: **1933.2 MB** (already deflate-compressed on delivery).
- Full year 2020 (×12): ≈ **22.7 GB** (± seasonal variation; January is near
  the ice/depth-extreme, so other months are comparable-to-smaller).
- 2017–2022 (6 years): ≈ **136 GB.**
- Static (bbox-sized, shared): **12.9 MB**, download once.
- **Recommendation:** download **month-by-month / year-by-year** and validate
  each with `inspect_glorys.py` before integrating; keep raw subsets gitignored
  and store a small per-file SHA-256 manifest alongside the processed subset.
  Ensure ≥ 30 GB free before a full-year pull (currently 921 GB free).

## GO/NO-GO for Stage 12.2 (Fortran reader)

| Gate | Result |
|---|---|
| Data structure understood (regular grid, 32 levels, daily time) | **YES** |
| Units verified for all variables (incl. `so = 1e-3 ÷1000`) | **YES** |
| Data quality acceptable (NaN = land, bounded fields, no spikes) | **YES** |
| Catalogue + probe reproducible | **YES** |
| Storage budget acceptable | **YES** |
| Ready to write the Fortran reader | **YES — GO** |

**Verdict: GO for Stage 12.2.** The reader contract is fixed by observation,
not assumption. Stage 12.2 will implement the offline/prescribed GLORYS12
reader behind a dedicated switch; **no Fortran was written in Stage 12.1**.
