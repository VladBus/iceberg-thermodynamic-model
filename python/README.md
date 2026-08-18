# Python tools

Python tools are auxiliary utilities for the AARI Iceberg Thermodynamic Model.
Python does NOT perform model-grid interpolation or physical model calculations —
those belong to the Fortran model.

## Environment

```bash
conda run -n iceberg-thermodynamic-model python ...
```

## Run-aware analysis (Stage 6.2)

All outputs live under `data/runs/<run_id>/`. Analysis and plotting scripts take
`--run-id <run_id>` (or `--manifest <path>`); `python/analysis/run_context.py`
resolves paths from the run. **Never glob `data/output/results_day_*.nc`** —
always pass `--run-id`.

```bash
python python/analysis/run_manifest.py --run-id <run_id>            # manifest + validate
python python/analysis/validate_q1_output.py --run-id <run_id>      # calendar + SI units
python python/analysis/seasonal_analysis.py --run-id <run_id>
python python/analysis/heat_diagnostics.py --run-id <run_id>
python python/analysis/snowfall_diagnostics.py --run-id <run_id>
python python/analysis/profiles.py --run-id <run_id>
python python/analysis/convective_analysis.py --run-id <run_id>
python python/analysis/eos_precision_analysis.py --run-id <run_id>
python python/analysis/convective_precision_study.py --run-id <run_id>
python python/plotting/plots.py --run-id <run_id>
python python/plotting/seasonal_plots.py --run-id <run_id>
python python/plotting/convective_plots.py --run-id <run_id>
```

`--run-id 2020_Q1_test_heat_on` is the default when no run is specified.

## Unit tests

```bash
python python/tests/test_units_roundtrip.py   # SI -> presentation -> SI round trips
# or: python -m pytest python/tests/test_units_roundtrip.py -v
```

## ERA5 (download / validate / merge)

```bash
# Barents domain (default): "Barents Sea / Svalbard / Franz Josef Land iceberg-source domain"
conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py \
    --year 2020 --month 1 --include-snowfall

# Historical Arctic-wide:
conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py \
    --domain arctic --year 2020 --month 1

# Validate (reports lat/lon coverage vs named domain / requested area):
python python/era5/check_era5.py
python python/era5/check_era5.py --domain arctic data/input/raw/era5/2020/2020_01/era5_2020_01.nc
python python/era5/check_era5.py --area 90 10 70 70 <file>

# Merge snowfall into instantaneous variables:
conda run -n iceberg-thermodynamic-model python python/era5/merge_snowfall.py \
    data/input/raw/era5/2020/2020_01/era5_2020_01.nc \
    data/input/raw/era5/2020/2020_01/snowfall_2020_01.nc \
    data/input/processed/era5/2020/2020_01/era5_2020_01_merged.nc
```

## Directory layout

```
era5/       download_era5.py, check_era5.py, merge_snowfall.py
analysis/   run_context.py, run_manifest.py, units.py, validate_q1_output.py,
            seasonal_analysis.py, heat_diagnostics.py, snowfall_diagnostics.py,
            profiles.py, convective_analysis.py, eos_precision_analysis.py,
            convective_precision_study.py
plotting/   plots.py, seasonal_plots.py, convective_plots.py
tests/      test_units_roundtrip.py
```