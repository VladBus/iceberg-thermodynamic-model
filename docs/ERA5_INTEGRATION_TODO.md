# ERA5 Integration TODO

Status symbols:
- `[x]` done
- `[~]` in progress
- `[ ]` pending

## Build / dependencies

- [x] Inspect current NetCDF dependencies
- [x] Add NetCDF-Fortran support to build (`fpm.toml`: `link=["netcdff"]`, `external-modules=["netcdf"]`)
- [x] Verify `fpm build --flag "-I/usr/include"` works

## netcdf_input.f90

- [x] Implement `netcdf_input.f90` module
- [x] Read NetCDF dimensions (valid_time, latitude, longitude)
- [x] Read latitude / longitude (and verify order / direction)
- [x] Read time (seconds since 1970-01-01, proleptic_gregorian)
- [x] Read u10
- [x] Read v10
- [x] Read msl
- [x] Read t2m

## Time interface

- [x] Define forcing time interface
- [x] Define model time -> ERA5 time mapping
- [x] Document time strategy: nearest / linear temporal interpolation
      DECISION (first version): nearest-time, explicit assumption.

## Spatial interpolation

- [x] Implement ERA5 -> model interpolation (bilinear, 4 nearest nodes)
- [x] Handle longitude periodicity (±180°, dateline)
- [x] Handle ERA5 missing values (3.4028235e38 must never reach model arrays)
- [x] Handle land/model masks (do not interpolate into ghost/land points)

## Coordinate arrays FI/DL

- [x] Verify model coordinate arrays FI/DL
- [x] Add TEST grid mode if real KOORD.DAT unavailable
- [x] Explicitly document synthetic grid (TEST ONLY, do not use in production)
      NOTE: `dl(i,j)` and `fi(i,j)` synthetic grid implemented in grid_coupling.f90.

## Forcing connection

- [x] Connect u10/v10 to wind forcing (wind, windx, windy)
- [x] Preserve existing wind-stress parameterization (tx/ty quadratic law)
- [x] Preserve msl pressure-gradient forcing (dpx/dpy) independent of wind
- [x] Connect t2m -> tatm (K -> degC)
- [x] Connect msl -> patm (Pa -> hPa)

## Model review

- [x] Review thermodynamics forcing (tatm/patm/wind/cloud/humid/sfal usage table)
- [x] Review grid masks
- [x] Review coupling

## netcdf_output.f90

- [x] Improve netcdf_output.f90 (diagnostic interface)
- [x] Add CF-style metadata (units, long_name, coordinates, time)
- [x] Add diagnostic forcing fields (windx, windy, tx, ty, dpx, dpy, tatm, patm)

## Validation / regression tests

- [x] Add test run using era5_test.nc
- [x] Validate ranges (wind, temperature, pressure, stress, pressure gradient)
- [x] Validate no NaN
- [x] Validate no missing-value contamination
- [x] Validate wind direction (sin/cos, sign, X/Y order, model i/j orientation)
- [x] Validate pressure gradient
- [x] Visual comparison ERA5 original vs model-grid field

## Comparison / documentation

- [x] Compare ERA5 forcing against legacy forcing
- [x] Document differences
- [x] Document assumptions (incl. CONFLICT entries if any)

## Final

- [x] Full build
- [x] Full regression test (era5_test.nc, small run)
