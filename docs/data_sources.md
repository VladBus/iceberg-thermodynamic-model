# Data Sources — External Input and Observational Products

This page is the **single authoritative index of external data products** used
by the model: forcing, initialization, grid, and observational validation
datasets. It exists so that humans and AI agents can answer "what does this
code reference, where does it come from, and how is it reproduced?" without
digging through stage reports.

One fact — one authoritative source: this page records *where* data comes
from and *how it is obtained*. Scientific discussion of each product lives in
the cited stage reports; the equation/unit conventions live in
`docs/model/model_equation_ledger.md`; bibliographic records live in
`docs/references/references.bib`.

---

## 1. Raw data products (input to the model)

| Product | Version / spec | Used for | Source (URL / DOI) | Local raw path | Regeneration / download | Units in model | Authoritative report |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ERA5 | ECMWF ERA5, hourly, single levels (u10, v10, msl, t2m, d2m, tcc, precip, sf) | Atmospheric forcing (wind, pressure, temperature, humidity, clouds, snowfall) | Copernicus Climate Data Store (CDS), `reanalysis-era5-single-levels`; requires `~/.cdsapirc` credentials | `data/input/raw/era5/2020/` | `python python/era5/download_era5.py --year 2020 --month 1` (see script header for domain variants) | u10/v10 m/s → ×100 → cm/s; msl Pa → ×0.01 → hPa; t2m K → −273.15 → °C | `docs/wiki/stages/stage06/Stage6.5_era5_barents_data.md`, `docs/wiki/stages/stage06/Stage6.5b_era5_forcing_impact.md`, `Stage6.6_snowfall_forcing.md` |
| EN4 | Met Office Hadley Centre EN4.2.2, monthly analysis (`g10`, 1°×1°, 42 levels) | Ocean initial T/S (2020-01-01) | `https://www.metoffice.gov.uk/hadobs/en4/` (yearly zips `EN.4.2.2.analyses.g10.YYYY.zip`) | `data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc` | documented in `docs/wiki/stages/stage07/Stage7.7_Ocean_Dataset_Selection.md` §2.1 | °C, PSU; converted to model salinity mass fraction 0.033–0.035 | `docs/wiki/stages/stage07/Stage7.7_Ocean_Dataset_Selection.md`, `Stage7.7_Realistic_Ocean_Initialisation.md` |
| IBCAO | IBCAO V5.2, 400 m bathymetry GeoTIFF, EPSG:3996 | Real model grid reconstruction (KOORD.DAT, hhh.bar) | NOAA/NCEI IBCAO v5.2 (GeoTIFF 400 m) | `data/input/raw/ibcao/ibcao_v5_2_2026_depth_400m.tiff` | `python python/grid/build_real_grid_inputs.py` | m (bathymetry); grid in EPSG:3996 | `docs/wiki/stages/stage07/Stage7.6A_IBCAO_real_grid_reconstruction.md` |
| OSI-SAF SIC | OSI-SAF Sea Ice Concentration CDR v3.1 (EASE2-250) | Real sea-ice initialization (2020-01-01) | EUMETSAT OSI-SAF `ice_conc_nh_ease2-250_cdr-v3p1` | `data/input/raw/ice/osisaf/ice_conc_nh_ease2-250_cdr-v3p1_202001011200.nc` | documented in `docs/wiki/stages/stage07/Stage7.6C.1_Real_ice_initialization.md` | fraction 0–1 | `docs/wiki/stages/stage07/Stage7.6C.1_Real_ice_initialization.md` |
| C3S CS2SMOS SIT | C3S (Copernicus) CS2SMOS Sea-Ice Thickness L4 combined v1.1 (EASE2-125) | Real sea-ice initialization (thickness) | CMEMS `ice_thickness_nh_ease2-125_cs3smos-v1p1` | `data/input/raw/ice/c3s_sit/ice_thickness_nh_ease2-125_cs3smos-v1p1_20200101.nc` | documented in `docs/wiki/stages/stage07/Stage7.6C.1_Real_ice_initialization.md` | m | `docs/wiki/stages/stage07/Stage7.6C.1_Real_ice_initialization.md` |

Merged/processed inputs (generated, **not** versioned in git):

| Processed product | Path | Derived from |
| --- | --- | --- |
| ERA5 merged NetCDF (model-ready) | `data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_d1_4_merged.nc` (also `era5_2020_0103_barents_expanded_merged.nc` default path) | raw ERA5 + merge/bilinear-interp pipeline (`netcdf_input.f90`; snowfall variable `sf`, units m s⁻¹) |
| EN4 initial T/S | `data/input/processed/ocean/initial_ts_2020-01-01.nc` (+ `_Tclamp*` variants) | raw EN4 + `initial_ocean_reader` pipeline (Stage 7.7) |
| Real grid | `data/input/generated/real_grid/` (KOORD.DAT, hhh.bar, reconstruction_metadata.json, `ice_2020-01-01/`) | IBCAO + `python/grid/build_real_grid_inputs.py` |

**Note:** `data/` (raw + processed + generated) is **gitignored** — it is
large and reproducible. Only curated observational CSV datasets (see §2) are
versioned, because regression tests and CI need them and they are small.

---

## 2. Versioned observational datasets (in git)

| Dataset | Purpose | File(s) in git | Source (DOI/URL) | Retrieval method | Tests |
| --- | --- | --- | --- | --- | --- |
| Stage 10.8.2 basal-melt observations | basal-melt validation (19 records) | `data/validation/observations/iceberg_basal_melt_observations.csv` + `_provenance.md` | literature records (see provenance) | manual curation from primary texts | `test_observational_validation.py` |
| Stage 10.18B lateral-melt observations | lateral-melt observational constraint (17 cases, 9 sources) | `data/validation/observations/iceberg_lateral_melt_observations*.csv` + `_provenance.md` | RH80, Enderlin14, Schild21, Enderlin23, Moyer19 (see provenance) | manual curation from fetched primary texts | `test_observational_constraint.py` |
| Stage 10.18C reanalysis | corrected observational reanalysis (18 rows, explicit independence/velocity classes) | `data/validation/observations/stage10.18c/{observations,sources}.csv` + `provenance.md` | same sources, methodological corrections applied | manual re-analysis | `test_stage10_18c_observations.py` |
| **Stage 10.18D per-iceberg Enderlin23** | per-iceberg melt/draft/geometry population (743 icebergs, 15 sites) | `data/validation/observations/stage10.18d/enderlin23_per_iceberg.csv` + `sources.csv` + `provenance.md` | **USAP-DC 10.15784/601679** (`Antarctic-iceberg-csvs.zip`), CC BY 4.0 | **direct HTTP POST** to the USAP-DC zip endpoint (page JS reCAPTCHA not enforced); inner zip MD5 `821bed51660957b65a896c42fb88a057`; raw archive **NOT** in git (see §3) | `test_stage10_18d_per_iceberg.py` |

---

## 3. Reproduction recipes (data acquisition)

### 3.1 Stage 10.18D Enderlin23 per-iceberg dataset

The raw archive (`Antarctic-iceberg-csvs.zip`, 54 per-observation CSVs) is
**not** in git (reproducible, ~400 kB, binary). To re-fetch it:

```bash
# 1. Open the dataset landing page to confirm availability:
#    https://www.usap-dc.org/view/dataset/601679
#    (DOI 10.15784/601679; CC BY 4.0; title "Remotely-sensed iceberg
#     geometries and meltwater fluxes"; Enderlin et al. 2022/2023)

# 2. Direct POST to the zip endpoint (no account, no reCAPTCHA on this route):
curl -sL -X POST \
  -d "dl_checkbox=https://www.usap-dc.org/dataset/usap-dc/601679/2023-04-04T19:54:46.1Z/Antarctic-iceberg-csvs.zip" \
  -o e23_outer.zip \
  "https://www.usap-dc.org/zip/usapdc_601679_download_20260920_192351.zip"

# 3. Unwrap the zip-in-zip and verify the checksum:
python - <<'EOF'
import zipfile, hashlib
outer = zipfile.ZipFile("e23_outer.zip")
data = outer.read("usapdc_601679/Antarctic-iceberg-csvs.zip")
assert hashlib.md5(data).hexdigest() == "821bed51660957b65a896c42fb88a057"
open("Antarctic-iceberg-csvs.zip", "wb").write(data)
zipfile.ZipFile("Antarctic-iceberg-csvs.zip").extractall("Antarctic-iceberg-csvs")
EOF
```

Then rebuild the derived per-iceberg CSV (the versioned file) with the
dataset builder (see `data/validation/observations/stage10.18d/provenance.md`
for the exact transformation; the script was a stage-local tool — the
derived CSV is the reproducible artifact).

### 3.2 ERA5

```bash
conda run -n iceberg-thermodynamic-model \
    python python/era5/download_era5.py --year 2020 --month 1
# CDS credentials: ~/.cdsapirc (NEVER commit; gitignored)
```

### 3.3 EN4

Documented in `docs/wiki/stages/stage07/Stage7.7_Ocean_Dataset_Selection.md`
§2.1 (yearly zip from metoffice.gov.uk, extract the January analysis file
`EN.4.2.2.f.analysis.g10.202001.nc`).

### 3.4 Real grid

```bash
python python/grid/build_real_grid_inputs.py
# creates data/input/generated/real_grid/{KOORD.DAT, hhh.bar,
# reconstruction_metadata.json, ice_2020-01-01/...};
# root-level symlinks KOORD.DAT / hhh.bar are NOT created automatically.
```

---

## 4. Unit conventions (quick reference)

| Domain | Units | Notes |
| --- | --- | --- |
| Hydrodynamics | CGS: dx cm, U/V cm/s, dt s, cof dyn/cm² | internal |
| Thermodynamics | SI: T °C, S mass fraction 0.033–0.035 (NOT PSU) | internal |
| NetCDF output | SI: temperature K, salinity_mass_fraction kg/kg, density_anomaly kg m⁻³ (ρ−1.02), u/v/w m/s, tau Pa, dp Pa/m | conversion only at `netcdf_output.f90` |
| ERA5 input | u10/v10 m/s → ×100 → cm/s; msl Pa → ×0.01 → hPa; t2m K → −273.15 → °C | conversion in forcing pipeline |
| Observations | melt m/day; thermal forcing °C; C_eff m/(s·K); draft m | Stage 10.18 series |

Full detail: `docs/model/model_equation_ledger.md`, `AGENTS.md` (Unit Systems).

---

## 5. Authoritative references per product

| Product | Stage report / document |
| --- | --- |
| ERA5 | `docs/wiki/stages/stage06/Stage6.5_era5_barents_data.md`, `Stage6.6_snowfall_forcing.md`; downloader `python/era5/download_era5.py` |
| EN4 | `docs/wiki/stages/stage07/Stage7.7_Ocean_Dataset_Selection.md`, `Stage7.7_Realistic_Ocean_Initialisation.md`; reader `src/initial_ocean_reader.f90` |
| IBCAO | `docs/wiki/stages/stage07/Stage7.6A_IBCAO_real_grid_reconstruction.md`, `Stage7.6B_Real_grid_input_reconstruction.md`; builder `python/grid/build_real_grid_inputs.py` |
| OSI-SAF SIC / C3S SIT | `docs/wiki/stages/stage07/Stage7.6C.1_Real_ice_initialization.md` |
| Observations 10.8.2 / 10.18B / 10.18C / 10.18D | `docs/validation/INDEX.md` (active Stage 10) + the per-stage provenance files in `data/validation/observations/` |

## 6. Policy notes

- `data/` is gitignored; only curated observational CSVs + provenance are
  versioned (they are small and required by tests/CI).
- CDS credentials (`~/.cdsapirc`) are never committed.
- Every observational value must be traceable to a fetched primary text or a
  documented derivation (`provenance.md` rule, Stage 10.18B/C/D).
- When adding a new data product: update this index, add a provenance entry,
  and (if the product enters tests) version the small derived CSV.