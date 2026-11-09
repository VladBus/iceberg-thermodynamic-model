# Stage 12.12 — Voxel Resolution Recovery and Geometry Audit

**Status:** AUDIT COMPLETE (2026-11-08)
**Scope:** resolution diagnosis, geometry correction, voxel/prism consistency,
fallback-forcing transparency, and visualization checks. No new 100^3 annual
run was started. No commit/push.

## 1. Why Stage 12.11 used 8 x 8 x 8

The Stage 12.11 configurations explicitly set:

```text
voxel_grid=8x8x8
dx=12.5
dy=12.5
dz=12.5
```

The same values were passed through `VOXEL_NX/NY/NZ` and
`VOXEL_DX/DY/DZ` in the run commands. This was a fast test grid inherited from
the short demonstration runs, not the scientific target resolution. The target
from `Stage12_Iceberg_Transition.md` section 6.2 and the PDF is a 100 m cube at
1 m resolution: `100 x 100 x 100 = 1,000,000` voxels.

The code previously accepted `VOXEL_DX/DY/DZ` but silently used
`L/NX`, `W/NY`, `H/NZ` for initialization without an explicit consistency
check. That allowed a configuration file and a run to disagree about `dx`
without a clear failure. The audit adds:

- an explicit `NX*DX=L`, `NY*DY=W`, `NZ*DZ=H` check;
- actual NX/NY/NZ and DX/DY/DZ global attributes in the voxel NetCDF;
- the physical `L/W/H` in the same metadata.

## 2. Resolution experiments

All runs use the same 2020 ERA5/GLORYS forcing, 100 m cube, `dt=3600 s`, and
the same point `76.5 N, 20.0 E`. Runs were sequential.

| N | h [m] | 5 d mass loss | 30 d mass loss | 30 d T range [C] | 30 d phi mean | 30 d draft/freeboard [m] | 5 d time / RSS | 30 d time / RSS |
|---:|---:|---:|---:|---|---|---|---|---|
| 8 | 12.5 | 9.47e-3 | 4.15e-2 | -12.19 … -8.78 | 0.9585 | 89.00 / 11.00 | 6.1 s / 637 MB | 8.8 s / 651 MB |
| 20 | 5 | 9.32e-3 | 4.08e-2 | -10.99 … -4.71 | 0.9596 | 88.98 / 11.03 | 3.4 s / 640 MB | 11.3 s / 655 MB |
| 50 | 2 | 8.84e-3 | 3.96e-2 | -12.98 … -1.59 | 0.9668 | 88.98 / 11.02 | 13.7 s / 640 MB | 62.3 s / 677 MB |
| 100 | 1 | 8.48e-3 | 3.87e-2 | -13.26 … -1.57 | 0.9817 | 87.97 / 11.03 | 84.8 s / 738 MB | 479.6 s / 799 MB |

PCG behavior: maximum iteration counts were 2 (N=8/20), 3 (N=50), and 4
(N=100); maximum relative residuals were `~1e-10`. No solver failure occurred.

**Convergence status: WARNING.** Results are approaching, but not fully
converged: the 30-day mass loss changes by about 2.3% from 50 to 100 and by
about 6.6% from 8 to 100. The 100^3 run is a 1 m reference test, not yet a
production annual configuration.

The raw table and figure are under
`docs/wiki/stages/stage12/figures/stage12.12/resolution/`.

### Cost of a 100^3 year

Measured: 30 days at 100^3 = **479.6 s wall / 799 MB peak RSS**; 5 days =
84.8 s. A 365-day extrapolation is approximately **1.6 hours** at this
resolution and memory footprint, excluding I/O and restart overhead. This is
feasible on the current 8 GB WSL2 limit only as a single sequential run; it was
not started in this audit.

## 3. Geometry correction

The specification defines `phi` as an ice volume fraction, not a vertical
height. The corrected definitions are:

```text
z_bot = (k_bot - 1) * h
z_top = k_top * h
D     = z_wl - z_bot
F     = z_top - z_wl
```

where `k_top` is the highest layer with ice and `k_bot` is the lowest layer
with ice. `z_wl` is found from the cumulative `phi*V` according to (10.2)-(10.3).
The previous `(k-1+phi)*h` upper-surface expression was removed.

The `phi=0.5` top-layer test now expects `z_top=80 m`, not 75 m. The bottom
surface, draft, freeboard, and the `1 m / 100^3` geometry test are covered in
`test_voxel_iceberg.f90`.

**Assumption check:** no internal vertical gaps were found in the final
snapshots of the 2020, 2024, or 100^3 30-day runs. The specification's
no-vertical-cavity assumption holds for these saved states; if a future state
has a gap, the cumulative waterline formula is not valid and must be flagged.

## 4. Voxel/prism consistency

The voxel and legacy prism representations are **not interchangeable** during
long runs. Relative differences (voxel vs prism) in the saved annual output:

| Run | Mass median / max | Draft median / max | Freeboard median / max |
|---|---:|---:|---:|
| 2020 annual | 0.46% / 40.3% | 15.3% / 81.7% | 12.4% / 77.7% |
| 2024 annual | 0.16% / 100% | 12.4% / 118.9% | 15.6% / 107.5% |

The dynamics uses voxel mass/draft/drag areas when enabled, but prism `L/W/H`
bookkeeping continues separately; grounding and the legacy update path still
see the prism. This divergence is a **WARNING** for quantitative drift and
annual geometry. It was not rewritten in this audit; options are to make the
voxel state authoritative for all geometry, or to explicitly freeze/stop the
prism state when the voxel path is active. Both require a separate design
decision.

Figure: `figures/stage12.12/prism_consistency/prism_consistency.png`.

## 5. Temperature visualization and slice check

The original horizontal/vertical temperature discrepancy was Matplotlib offset
notation, not different arrays: the horizontal colorbar showed an offset
(`-9.999`) and small tick differences, while the vertical bar displayed `-10.0`
directly. The slices were consistent.

The checker now compares the actual horizontal `(nz=kc)` and vertical
`(ny=jc)` arrays, their dimensions, their intersection, and the original 3D
value. A synthetic field depending on all three coordinates is tested in
`python/tests/test_plot_voxel_results.py`, including rejection of a transposed
field.

For large grids, 3D views are block-downsampled to at most 32 cells per axis
and drawn without per-cell black edges. Horizontal/vertical sections retain
full resolution. Melt-out states now display an explicit zero-mass annotation.
`phi` remains visible as a separate 0–1 field.

## 6. Forcing fallback transparency

The 2020 Stage 12.11 365-day run had 3,154 warning lines. The corrected
366-day attempt produced 3,203 warning lines but **1,577 actual fallback
events**; multiple candidate cells are tested per event. The fallback CSV is
`data/validation/stage12.12/annual_2020_366/run.nc_fallback.csv`.

For each event it records time, iceberg coordinates, selected wet-cell
coordinates, distance, draft, interpolated T/S/u/v, and the reason. The events
are concentrated near the end of the 2020 trajectory, around
`76.83–76.84 N, 16.86–17.08 E`; median selected-cell distance is `0.0833°`
(about 5–9 km). The 2024 run had no such fallback in its completed portion.

No implicit forcing substitution is now invisible: the run writes a separate
CSV and the main NetCDF remains the primary data product.

## 7. Calendar and time coverage

Input data audit: 2020 and 2024 each have 12 months and 366 daily records for
ERA5 and GLORYS12; time coordinates are monotonic and unique.

Final saved annual states (8^3, for audit context only):

| Year | Records | Days | Final mass | Draft / freeboard |
|---|---:|---:|---:|---:|
| 2020 | 8,761 | 365.0 | 12,649,387 kg | 43.75 / 6.25 m |
| 2024 | 6,452 | 268.8 | 0 kg | 0 / 0 |

Output calendar check:

- 2020 requested 366 days; the run stopped at 365.0 days (8,761 hourly
  records) because no valid ocean profile remained within 0.5° at the final
  point. **FAIL for full 366-day calendar coverage.**
- 2024 requested 366 days; the body melted out at 268.8 days (6,452 records).
  **Not a full-year run by construction.**

Correct epoch/start-date values were used (`20200101`/1577836800 and
`20240101`/1704067200).

## 8. Testing and verification

```text
fpm build --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"
RC=0

fpm test --flag "-I/usr/include"
RC=0; 81 programs STOP 0

python tests/test_plot_voxel_results.py
SUCCESS
```

Documentation checks:

```text
check_docs_links.py --anchors: 57 files, 249 links, 0 broken, 0 anchor warnings
check_docs_links.py --all:    271 files, 250 links, 0 broken
git diff --check:             RC=0
```

The synthetic slice test is `python/tests/test_plot_voxel_results.py`
(`SUCCESS`).

## 9. Answers

1. **Can 1 m resolution be used for a full year on this hardware?**
   Technically likely yes: measured 100^3 cost is ~480 s for 30 days and
   ~800 MB RSS, extrapolating to ~1.6 h for a year. It has not been run; this
   is an estimate, not a demonstrated annual result.
2. **Do results converge spatially?**
   **Not fully.** 50 vs 100 differs by ~2.3% in 30-day mass loss; 8 vs 100 by
   ~6.6%. The 1 m grid is the reference direction, but resolution convergence
   is still a WARNING.
3. **How credible is the current melt-out?**
   **WARNING / not confirmed.** The 2024 melt-out is a model result at 8^3 and
   is strongly resolution-sensitive; the 2020 result is affected by land
   fallback and the voxel/prism split. Neither lifetime should be presented as
   a validated physical lifetime.
4. **What must be fixed before a full annual experiment?**
   Unify or explicitly gate voxel/prism geometry, resolve the land/fallback
   trajectory or justify a stable ocean point, choose a converged grid
   (likely 1 m or demonstrate acceptable coarse-grid error), close the full
   energy budget, and rerun a 366-day calendar-controlled experiment.
