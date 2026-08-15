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

- [~] Implement `netcdf_input.f90` module
- [~] Read NetCDF dimensions (valid_time, latitude, longitude)
- [~] Read latitude / longitude (and verify order / direction)
- [~] Read time (seconds since 1970-01-01, proleptic_gregorian)
- [~] Read u10
- [~] Read v10
- [~] Read msl
- [~] Read t2m

## Time interface

- [ ] Define forcing time interface
- [ ] Define model time -> ERA5 time mapping
- [ ] Document time strategy: nearest / linear temporal interpolation
      DECISION (first version): nearest-time, explicit assumption.

## Spatial interpolation

- [ ] Implement ERA5 -> model interpolation (bilinear, 4 nearest nodes)
- [ ] Handle longitude periodicity (±180°, dateline)
- [ ] Handle ERA5 missing values (3.4028235e38 must never reach model arrays)
- [ ] Handle land/model masks (do not interpolate into ghost/land points)

## Coordinate arrays FI/DL

- [ ] Verify model coordinate arrays FI/DL
- [ ] Add TEST grid mode if real KOORD.DAT unavailable
- [ ] Explicitly document synthetic grid (TEST ONLY, do not use in production)
      NOTE: `dl(i,j)` is currently NEVER assigned anywhere (stays 0.0);
      `fi` is synthetic 66..82N in grid_coupling.f90.

## Forcing connection

- [ ] Connect u10/v10 to wind forcing (wind, windx, windy)
- [ ] Preserve existing wind-stress parameterization (tx/ty quadratic law)
- [ ] Preserve msl pressure-gradient forcing (dpx/dpy) independent of wind
- [ ] Connect t2m -> tatm (K -> degC)
- [ ] Connect msl -> patm (Pa -> hPa)

## Model review

- [ ] Review thermodynamics forcing (tatm/patm/wind/cloud/humid/sfal usage table)
- [ ] Review grid masks
- [ ] Review coupling

## netcdf_output.f90

- [ ] Improve netcdf_output.f90 (diagnostic interface)
- [ ] Add CF-style metadata (units, long_name, coordinates, time)
- [ ] Add diagnostic forcing fields (u10_model, v10_model, t2m_model, msl_model,
      windx, windy, tx, ty, dpx, dpy)

## Validation / regression tests

- [ ] Add test run using era5_test.nc
- [ ] Validate ranges (wind, temperature, pressure, stress, pressure gradient)
- [ ] Validate no NaN
- [ ] Validate no missing-value contamination
- [ ] Validate wind direction (sin/cos, sign, X/Y order, model i/j orientation)
- [ ] Validate pressure gradient
- [ ] Visual comparison ERA5 original vs model-grid field

## Comparison / documentation

- [ ] Compare ERA5 forcing against legacy forcing
- [ ] Document differences
- [ ] Document assumptions (incl. CONFLICT entries if any)

## Final

- [ ] Full build
- [ ] Full regression test (era5_test.nc, small run)
