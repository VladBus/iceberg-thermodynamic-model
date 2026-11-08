# Stage 12.11 — Final Audit, Visualization Corrections and 2020/2024 Readiness

**Status:** AUDIT COMPLETE (2026-11-08)
**Scope:** verification and small corrections; no physical calibration, no new
downloads, no WAM adaptation, no commit/push.
**Data:** local ERA5/GLORYS12 only; 2020 and 2024; 2026 was not considered.

## 1. Git and code state

The audit started from published `main` at `e85fcdc`; the worktree was clean.
Changes made here remain uncommitted. The code changes are limited to the
voxel boundary/geometry diagnostics, the `iceberg_run` output, tests, data
preparation utilities, and visualization.

## 2. Face-specific boundaries and cavities

**PASS.** The Stage 12.10 face-specific `T_B,f` path remains intact. The CN
matrix uses one local temperature, area, and `h_norm` per exposed submerged
face; no voxel-mean `T_B` is used.

**PASS.** The six-neighbour flood fill (`open_mask`/`open_face`) excludes
isolated cavities while keeping exterior-connected channels open.

A strict `-fcheck=all` run found an existing non-short-circuit bounds bug in the
CN assembly: `phi(ii,jj,kk)` was evaluated even when `kk=0`. It is now guarded
explicitly. This was a real memory-safety bug, not a visualization issue.

## 3. Mass and energy

**PASS for mass.** Voxel cumulative losses (`basal + lateral + surface + flush`)
close against the change of voxel mass. The annual runs close to
`3.1e-8` (2020) and `5.2e-9` (2024) relative error; the control runs are of the
same order. `flush_voxel` mass and sensible/latent accounting is tested once.

**WARNING for energy.** `sensible_energy` and `flushed_energy` are diagnostics;
a complete phase-change/latent/boundary energy-conservation audit has **not**
been performed. Do not claim full energy conservation.

## 4. Visualization corrections

The apparent horizontal/vertical temperature inconsistency was **not** a data
or indexing inconsistency. The horizontal colorbar used Matplotlib offset
notation above the bar (`-9.999` offset + `-0.0002…` ticks), while the vertical
bar showed `-10.0` directly. The underlying slices are the same field.

**PASS.** All temperature plots now:

- use one shared `Normalize(vmin,vmax)` for horizontal, vertical, and 3D views;
- mask inactive voxels (`phi <= 0.01`);
- use an explicit colorbar format (no hidden offset);
- run a slice-consistency assertion at the shared center point.

**PASS.** `voxel_shape_final.png` remains the binary active-voxel silhouette;
`phi_horizontal.png` and `phi_3d_final.png` show partial melting with a
0–1 color scale. The figures are visually distinct and reproducible.

**WARNING — freeboard/vertical position.** Freeboard is now computed from the
actual remaining solid top and the waterline, not from the initial grid height.
Draft is measured from the lowest remaining solid cell. However, the voxel grid
is not vertically repositioned as the bottom melts; strong bottom erosion can
therefore leave an over-submerged body with zero freeboard. This is a model
limitation, not a plotting issue.

## 5. Data audit

Local files only; no downloads.

| Product | 2020 | 2024 | Status |
| --- | --- | --- | --- |
| ERA5 monthly | 12/12; 366 daily records | 12/12; 366 daily records | PASS |
| ERA5 annual merge | 366 records; 7 variables | 366 records; 7 variables | PASS |
| GLORYS12 monthly | 12/12; 366 annual records | 12/12; 366 annual records | PASS |
| GLORYS12 annual | 366 records | merged from monthly locally | PASS / metadata warning |
| WAM | native rotated grid | native rotated grid | NOT READY for `wave_forcing.f90` |

All monthly time coordinates are monotonic and unique. The Barents coverage is
`lat 63–86`, `lon 5–80`. ERA5 variables and units are present. GLORYS annual
files are readable but their annual-merge metadata lacks per-variable `units`
attributes; the original monthly files have the expected units. This is a
provenance/metadata warning, not a reader failure.

The audit JSON is `docs/validation/stage12.11_data_audit.json`.

## 6. Control runs

Configuration: 100 m cube, 8×8×8 voxels (12.5 m), `dt=3600 s`, 5 days, same
point `76.5 N, 20.0 E`.

| Year | Result |
| --- | --- |
| 2020 | PASS: 121 records, no NaN, mass 909,920,512 → 901,299,584 kg |
| 2024 | PASS: 121 records, no NaN, mass 909,888,384 → 895,197,632 kg |

Both controls loaded annual GLORYS/ERA5, produced finite T and phi in [0,1],
passed mass-budget closure, wrote NetCDF/CSV, and produced the seven plots.

## 7. Annual runs

Same configuration; 365 days for 2020 and 366 days requested for 2024.

| Year | Records / duration | Final mass | Final draft / freeboard | Result |
| --- | --- | ---: | --- | --- |
| 2020 | 8,761 / 365.0 d | 12,649,387 kg | 43.75 m / 0.00 m | **WARNING** |
| 2024 | 6,452 / 268.8 d | 0 kg | 0 / 0 | **WARNING: melt-out before year end** |

### 2020

The run reaches 365 days without NaN and with a closed voxel mass budget, but
the trajectory produces **3,154** `reanalysis point not ocean` fallback
warnings and ends at `76.84 N, 16.86 E`. It is not a publication-quality annual
forcing experiment. The final body has only upper-layer ice; freeboard is zero
under the fixed vertical grid.

### 2024

The voxel body melts out at **268.8 days**; the new zero-mass guard stops the
run before dynamics divides by zero. This is a valid melt-out/lifetime
demonstration, but it is **not a 366-day annual experiment**. The final
snapshots and fields are empty by construction.

## 8. Time-step sensitivity

Five-day 2020 comparison with the final code:

| Comparison | Relative Δmass | Max ΔT | Max Δphi |
| --- | ---: | ---: | ---: |
| dt 1800 vs 3600 s | 7.7e-5 | 0.029 °C | 3.2e-3 |
| dt 900 vs 3600 s | 1.5e-4 | 0.044 °C | 5.2e-3 |

No subcycling was added. This is a short-run check, not a long-run accuracy
proof.

## 9. Figures and data products

Annual figures are in
[`figures/stage12.11/2020/`](figures/stage12.11/2020/) and
[`figures/stage12.11/2024/`](figures/stage12.11/2024/). The cross-year
comparison is
[`comparison_2020_2024.png`](figures/stage12.11/comparison/comparison_2020_2024.png).
Key examples:
[2020 time series](figures/stage12.11/2020/time_series.png),
[2020 vertical T](figures/stage12.11/2020/temperature_vertical.png),
[2020 forcing](figures/stage12.11/2020/forcing_time_series.png),
[2024 time series](figures/stage12.11/2024/time_series.png),
[2024 final shape](figures/stage12.11/2024/voxel_shape_final.png).

NetCDF, CSV, configurations, and logs are under
`data/validation/stage12.11/{2020,2024}/{control,annual}/`, including:

- `run.nc`, `run.nc_voxel.nc`;
- `csv/time_series.csv`, `csv/snapshots.csv`;
- `config.txt`, `run.log`;
- `figures/`.

## 10. Tests

```text
fpm build --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"
RC=0

fpm test --flag "-I/usr/include"
RC=0; 81 programs STOP 0
```

Documentation checks and final diff checks are run after the report edits.

## 11. Readiness answers

1. **2020 full-year readiness:** **WARNING / not publication-ready.** It runs a
   full 365 days, but 3,154 land/no-data fallback warnings and the fixed
   vertical grid make the result unsuitable for a quantitative annual claim
   without a trajectory/domain correction or a documented, justified point
   selection.
2. **2024 full-year readiness:** **NO for a 366-day experiment.** The body melts
   out at 268.8 days. It can be used as a melt-out/lifetime case, not as a
   full-year comparison.
3. **Remaining limitations:** fixed vertical coordinates; land/no-data forcing
   fallback; WAM format not integrated; no full energy audit; uncalibrated
   transfer coefficients; no observational validation; prism/voxel geometry
   bookkeeping remains separate.
4. **Thesis use:** implementation audit, visualization, control experiments,
   and the 2024 melt-out demonstration are usable with explicit caveats. Do
   not claim a validated full-year 2020/2024 forcing experiment, quantitative
   annual melt/drift, full energy conservation, or observational skill.
