# ERA5 download

## CDS API credentials

cdsapi uses:

~/.cdsapirc

The file is NOT stored in the repository.

Expected location:

/home/vlad/.cdsapirc

Never commit credentials to Git.

## Python environment

conda activate iceberg-thermodynamic-model

## Download

Full month (defaults: January 2020, area 66–90 N, 6-hourly):

python python/era5/download_era5.py

Full month, hourly, TEST-grid region (66–82 N / 30–63 E):

python python/era5/download_era5.py --year 2020 --month 1 \
 --area 82 30 66 63 \
 --time 00:00 01:00 ... 23:00 \
 --output data/input/raw/era5/era5_2020_01.nc

Full Arctic strip:

python python/era5/download_era5.py --year 2020 --month 1 \
 --area 90 -180 65 180

Options:
--year YYYY year (default 2020)
--month M month 1-12 (default 1)
--area N W S E spatial area (default [90, -180, 65, 180])
--time HH:MM ... hourly slices (default 00/06/12/18)
--output PATH output .nc (default data/input/raw/era5/era5_YYYY_MM.nc)

Downloaded fields: u10, v10, t2m, msl (native ERA5 units: m/s, K, Pa).

## Inspect / validate

python python/era5/check_era5.py
python python/era5/check_era5.py data/input/raw/era5/era5_2020_01.nc

Checks dimensions, time axis, spatial coverage, variable presence/units,
NaN/Inf and physical ranges.

## Raw data

Downloaded ERA5 files are stored in:

data/input/raw/era5/

Raw data are NOT committed to Git.

## Data flow

Copernicus CDS
↓
cdsapi
↓
raw NetCDF
↓
Fortran model (netcdf_input.f90 -> wind_forcing.f90)

## Current file

- era5_test.nc — legacy 12-slice test file (6-hourly, ~3 days)
- era5_2020_01.nc — full January 2020, hourly, 744 steps, 66–82 N / 30–63 E
  (used by the Fortran run; main.f90 opens this file)
