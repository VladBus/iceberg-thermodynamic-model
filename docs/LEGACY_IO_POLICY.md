# Legacy I/O Policy (Stage 11.10)

**NetCDF is the production source of truth.**

| Input | Production source |
|---|---|
| Grid / masks | `data/input/processed/grid/grid.nc` |
| Initial ocean T/S | `data/input/processed/ocean/initial_ts_*.nc` |
| Atmospheric forcing | `data/input/processed/era5/**/*merged.nc` |
| Sea ice | `data/input/processed/ice/seaice_initial.nc` |
| Tides | `data/input/processed/tides/tides.nc` (currently null-tides; see plan) |

`KOORD.DAT`, `hhh.bar`, `1_*.ice`, `GRM2` and the legacy `.DAT` readers are
**not production inputs**. They may remain in source for offline regression
fixtures, but no root-level symlinks are required and no production env gate
selects them. Stage 11.10 removed the root symlinks and made NetCDF grid/sea-ice
the default production path.

The legacy branches in `grid_coupling.f90` are unreachable when the NetCDF
readers are active; removal into a dedicated `src/legacy_io/` package is a
future cleanup, not a production dependency.
