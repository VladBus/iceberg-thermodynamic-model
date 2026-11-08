# Stage 12.10 — Voxel Thermodynamic Boundary Improvement

**Status:** COMPLETE (2026-11-08)
**Scope:** face-specific thermal boundary conditions, minimal cavity
classification, mass-budget verification, voxel diagnostics, and 3D output.
**Not a calibration or observational-validation stage.**

## 1. What changed

### 1.1 Face-specific boundary conditions

`voxel_iceberg_step_profile` no longer averages the three-equation interface
temperature over the faces of a voxel. For every exposed submerged face it
stores

- local interface temperature `T_B,f`;
- local melt rate and local face area;
- local face depth and `h_norm`;
- the face-specific heat/mass contribution.

`solve_cn` assembles each face separately into the diagonal and right-hand
side. The reconstructed face temperature is therefore the boundary value used
by the CN matrix on that face, not a voxel-mean value.

### 1.2 Cavity / exterior connectivity

The old `empty_or_outside` test treated any empty neighbour as an exchange
surface. A six-neighbour flood fill now classifies empty cells connected to the
domain exterior:

- `open_mask(i,j,k)` — empty cell connected to the exterior;
- `open_face(i,j,k,f)` — solid face adjacent to an exterior-empty cell.

Isolated internal cavities have `open_mask=.false.` and their solid walls do
not receive ocean/atmosphere fluxes. A channel connected to the exterior is
open and receives the normal face boundary condition. This is a minimal
connectivity classification, not a cavity-resolved spray/circulation model.

### 1.3 Mass and energy diagnostics

- The mass-loss components `basal + lateral + surface + flush` are checked
  against the change of voxel mass.
- `sensible_energy` and accumulated `flushed_energy` are written to the
  time-series NetCDF.
- The existing clamp, `VOXEL_MELT_CAP`, `VOXEL_PHI_MIN`, and `flush_voxel`
  paths were retained; no coefficient was changed.
- The current `c_ice=2100 J/(kg K)` remains a documented model choice; the
  literature value `2009 J/(kg K)` is recorded as a sensitivity/parameter
  question, not silently substituted.

### 1.4 Diagnostic draft and geometry

When `VOXEL_ENABLED=ON`, `iceberg_run` now reports the voxel mass and voxel
Archimedes draft instead of the prism estimate. `voxel_model_step` also uses
the voxel draft for the next forcing interpolation. The prism state remains a
separate legacy bookkeeping path.

### 1.5 Spatial output and plotting

`iceberg_run` writes up to three snapshots to `<run>_voxel.nc` with

- `T(i,j,k)`, `phi(i,j,k)`, `open_mask(i,j,k)`, `tb_face(i,j,k,f)`;
- mass and draft per snapshot;
- time-series `sensible_energy` and `flushed_energy`.

The plotting utility is
[`python/analysis/plot_voxel_results.py`](../../../../python/analysis/plot_voxel_results.py).
It produces shape, temperature sections, `phi`, time-series, and energy plots
from saved NetCDF only.

## 2. Numerical verification

Tests added/extended:

- face-specific one-face Dirichlet steady state;
- two different face temperatures (weighted solution, not an averaged `T_B`);
- symmetric equal-face case;
- solid cube: 600 exterior faces;
- isolated cavity: no additional exchange area;
- connected channel: classified as open;
- mass-loss component closure;
- existing CN, Stefan, air-balance, drift, and integration suites.

Key results:

```text
A-T1 adiabatic energy drift                 1.58e-10
A-T3 temporal order ratio                   3.996 (~2nd order)
face-BC one face                            T = -2.00000 C
face-BC two faces                           T = -2.80000 C (expected -2.80000)
isolated cavity                             closed, external area unchanged
connected channel                           open, exchange area increases
mass budget                                 dm = melt + flush
flush mass/energy accounting                removed voxel counted once
```

The strict `fpm build` (`-Wall -Wextra -fcheck=all -ffpe-trap=...`) exits 0.
The full `fpm test` battery exits 0 (81 programs report `STOP 0`; the
gitignored-data cases skip cleanly). FPM configuration was not modified; only
test programs were extended.

## 3. Short real-data experiments

Configuration: 100 x 100 x 100 m iceberg, `8 x 8 x 8` voxels (12.5 m cells),
`dt=3600 s`, 10 days, Barents Sea point `76.5 N, 20.0 E`.
GLORYS12 daily profiles and, for run C, ERA5 daily atmosphere were used.

| Run | Forcing | Final mass [kg] | Final volume [m3] | Final draft [m] | Basal loss [kg] | Lateral loss [kg] | Sensible energy [J] |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B | GLORYS12 | 893,286,912 | 981,634 | 86.90 | 7.419e6 | 9.294e6 | -1.9036e13 |
| C | GLORYS12 + ERA5 | 893,203,328 | 981,542 | 86.89 | 7.579e6 | 9.217e6 | -1.8707e13 |

ERA5 changes the near-surface/interior temperature field: final minimum
temperature is about -10.30 C in C versus -12.97 C in B, and the mean over
solid voxels is -9.97 C versus -10.14 C. The total mass difference is small
over this short run; this is a demonstration, not a calibrated comparison.

## 4. Time-step sensitivity

Run B repeated with `dt=1800` and `dt=900` s:

| Comparison | Relative mass difference | Max |ΔT| [C] | Max |Δphi| |
| --- | ---: | ---: | ---: |
| 1800 vs 3600 s | 3.3e-5 | 0.0037 | 3.4e-4 |
| 900 vs 3600 s | 4.8e-5 | 0.0056 | 4.9e-4 |

For this short, weakly forced case the current CN time step is adequate; no
thermal subcycling was added. This does not validate long or strongly forced
runs.

## 5. Figures

Generated from run C (GLORYS12 + ERA5):

- [`figures/voxel_demo/voxel_shape_final.png`](figures/voxel_demo/voxel_shape_final.png)
- [`figures/voxel_demo/temperature_horizontal.png`](figures/voxel_demo/temperature_horizontal.png)
- [`figures/voxel_demo/temperature_vertical.png`](figures/voxel_demo/temperature_vertical.png)
- [`figures/voxel_demo/temperature_3d_final.png`](figures/voxel_demo/temperature_3d_final.png)
- [`figures/voxel_demo/phi_horizontal.png`](figures/voxel_demo/phi_horizontal.png)
- [`figures/voxel_demo/phi_3d_final.png`](figures/voxel_demo/phi_3d_final.png)
- [`figures/voxel_demo/time_series.png`](figures/voxel_demo/time_series.png)

Reproduction:

```bash
VOXEL_ENABLED=true VOXEL_NX=8 VOXEL_NY=8 VOXEL_NZ=8 \
VOXEL_DX=12.5 VOXEL_DY=12.5 VOXEL_DZ=12.5 \
fpm run iceberg_run --flag "-I/usr/include" -- \
  76.5 20.0 100 100 100 10 3600 /tmp/demo.nc \
  data/input/reanalysis/glorys/2020/glorys12_barents_2020_daily.nc \
  data/input/static/glorys_static_barents.nc \
  data/input/reanalysis/era5/2020/era5_2020_01_daily.nc

python python/analysis/plot_voxel_results.py \
  /tmp/demo.nc /tmp/demo.nc_voxel.nc --outdir /tmp/demo_plots
```

## 6. Boundaries and remaining limitations

- No calibration against Enderlin23 or other observations.
- The 10-day experiments are demonstrations, not validation of daily-forcing
  skill or seasonal behavior.
- The cavity treatment classifies exterior connectivity only; it does not
  resolve cavity circulation, spray, or melting inside connected cavities.
- `c_ice=2100` versus `2009 J/(kg K)` remains a parameter-provenance question.
- Wave erosion is not used: WAM files are on a native rotated grid and are not
  yet adapted to `wave_forcing.f90`.
- Dynamics remains the documented one-directional, depth-averaged,
  no-capsize approximation; only geometry consistency was checked here.
- Full 190-iceberg and year-long matrices were not rerun.
