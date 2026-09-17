# Stage 10.15.2 — Coordinate Mapping and Bilinear Interpolation Fix

**Classification: Coordinate mapping and bilinear interpolation fix
completed — regression-tested and operationally re-run**
**Production physics changed: YES (coordinate conversion / interpolation
weights only — no physical parameterization, no calibration, no default
change)**
**Default configuration changed: NO**

This stage is a targeted correctness fix of the coordinate/indexing and
bilinear interpolation error identified in Stage 10.15.1. It is **not** a new
physical modernization, **not** calibration, **not** observational validation,
and **not** production-path integration.

| Item | Value |
| ---- | ----- |
| Stage | 10.15.2 (coordinate mapping and bilinear interpolation fix) |
| Branch / HEAD | `main` @ `d1bfc30` (Stage 10.15.1 committed and pushed) |
| Affected source | `src/iceberg_forcing.f90` (`bilinear_interp_3d`, `model_coords_to_latlon`) |
| New regression test | `test/iceberg_test_bilinear_axis_regression.f90` (13 checks; FAILS pre-fix, PASSES post-fix) |
| Corrected test | `test/iceberg_test_artificial_forcing.f90` (expectations fixed to the correct convention) |
| New comparison script | `python/analysis/stage10.15_2_compare.py` |
| Output bundle (gitignored) | `data/output/stage10.15_2/` (pre-fix preserved under `pre_fix/`) |

---

## 1. Scope

Stage 10.15.2:

- fixes the transposed bilinear interpolation weights in
  `model_coords_to_latlon` and `bilinear_interp_3d` (the root cause of the
  Stage 10.15.1 geographic-coordinate discontinuities);
- ensures model-coordinate → geographic-coordinate conversion is continuous;
- ensures grid-based forcing (ocean T/S/u/v, atmospheric lookup position,
  Coriolis latitude) is sampled at the correct spatial location;
- protects the correction with regression tests (analytical fields,
  boundary continuity, trajectory continuity);
- repeats the real 30-day TEST_11 run with identical forcing/configuration;
- documents pre-fix vs post-fix results.

It does **not**: introduce physical parameterizations, calibrate, change
production defaults, enable the low-flow closure, rewrite historical reports,
or redesign the ocean model.

## 2. Initial state

| Item | Value |
| ---- | ----- |
| Baseline commit | `d1bfc30` (Stage 10.15.1), branch `main`, clean working tree, `origin/main == HEAD` |
| Stage 10.15.1 findings | 8 real geographic-coordinate jumps (~0.17°, ~19 km) at model-cell boundary crossings; x/y trajectory continuous and kinematically consistent; suspected cause: transposed bilinear weights |
| Affected source files (verified directly) | `src/iceberg_forcing.f90`: `bilinear_interp_3d` (lines 179–189), `model_coords_to_latlon` (lines 237–299) |
| Also verified NOT affected | `netcdf_input.f90` `era5_bilinear2d` (wlat↔ilat, wlon↔jlon — correct); `wind_forcing.f90` (reads node values `fi(i,j)`/`dl(i,j)` directly — correct); `interp_at_draft`, `depth_averaged_thermal_forcing` (vertical-only); `latlon_to_model_coords` (nearest-node search, no weights) |
| Existing tests covering the area | `iceberg_test_artificial_forcing` (embedded the SAME transposed expectation — corrected in this stage), `iceberg_test_coord_mapping`, `iceberg_test_coord_roundtrip` (node sampling + 0.2° tolerance — do not detect the bug), `iceberg_test_forcing_interp_sensitivity` |

## 3. Root cause

### 3.1 Actual index convention (verified from source)

- Stage 7.6A grid builder (`python/grid/build_ibcao_grid.py` header):
  *"model X axis runs along array j (east); model Y axis runs along array i
  (north); therefore longitude varies with j and latitude with i"*.
- `model_coords_to_indices` (`src/iceberg_forcing.f90`): `j_idx =
  floor(x/dx)+1` (x → j), `i_idx = floor(y/dx)+1` (y → i).
- `model_coords_to_latlon` uses `x_j1 = (j1-1)*dx`, `y_i1 = (i1-1)*dx` —
  consistent: node j-index is the X direction, node i-index is the Y direction.
- `fku(i,j) = omega*sin(fi(i,j)/57.3)` (grid_coupling) — fi is latitude at
  node (i,j).
- KOORD.DAT stores `fi`/`dl` as (IS1, JS1) column-major; `fi(i,j)` = latitude
  of node (i,j), `dl(i,j)` = longitude of node (i,j).

**Established convention:** `i` ↔ Y ↔ latitude-like, `j` ↔ X ↔
longitude-like; `wx` (X-weight) must interpolate **along j**; `wy` (Y-weight)
must interpolate **along i**.

### 3.2 Incorrect weight-to-index association

Both `bilinear_interp_3d` and the inline formula in `model_coords_to_latlon`
had the cross terms transposed:

```fortran
! as written (WRONG — pre-fix):
val = wx1*wy1*arr(i1, j1) + wx*wy1*arr(i2, j1)   ! wx paired with i (Y)!
    + wx1*wy*arr(i1, j2) + wx*wy*arr(i2, j2)     ! wy paired with j (X)!

! corrected (post-fix):
val = wx1*wy1*arr(i1, j1) + wx*wy1*arr(i1, j2)   ! wx along j (X)
    + wx1*wy*arr(i2, j1) + wx*wy*arr(i2, j2)     ! wy along i (Y)
```

### 3.3 Affected functions

| Function | Use | Effect of the bug |
| -------- | --- | ----------------- |
| `bilinear_interp_3d` | ocean T/S/u/v in `get_ocean_profile` | ocean forcing interpolated at a position mirrored across the cell diagonal; artificial jumps at cell boundaries |
| `model_coords_to_latlon` | `state%latitude/longitude` in `iceberg_step` | geographic position jumped ~1 cell at boundary crossings; feeds `get_atmos_forcing` (ERA5 lookup) and the Coriolis parameter `f = 2Ω sin(latitude)` |

### 3.4 Why the bug produced cell-scale jumps

Inside a cell the transposed formula is smooth, but the interpolation stencil
changes at cell boundaries (`i_idx`/`j_idx` switch). Because the weights then
read from a different corner set, the interpolated value jumps by about one
grid cell's field variation (~0.1–0.9° in lat/lon; here ~0.17°).

### 3.5 Why node-only tests failed to detect it

- `iceberg_test_coord_mapping` TEST 1 samples exactly at grid nodes
  (wx=wy=0), where both formulas coincide (error 0); TEST 4 round-trip
  (latlon→coords→latlon) uses nearest-node snapping — the transposition is
  invisible at nodes.
- `iceberg_test_artificial_forcing` embedded the **same transposed
  expectation** (it computed the exact value with wx on the i/lat index) —
  it validated the buggy formula against itself.
- The 0.2° round-trip tolerance is broader than the 0.17° jump — a WARNING
  was printed but the suite still passed.

## 4. Correction

| File | Change |
| ---- | ------ |
| `src/iceberg_forcing.f90` | `bilinear_interp_3d`: cross terms swapped (wx→j, wy→i) + convention comments; `model_coords_to_latlon`: same swap for lat and lon + convention comments |
| `test/iceberg_test_artificial_forcing.f90` | expectations corrected: `lat = lat(i1) + wy*0.1`, `lon = lon(j1) + wx*0.1`; edge test tolerance relaxed 1e-6 → 1e-5 (float32 precision at magnitude ~30, consistent with tests 2/5) |
| `test/iceberg_test_bilinear_axis_regression.f90` | NEW (13 checks, see §5) |
| `python/analysis/stage10.15_1_trajectory_audit.py` | post-fix contract: CSV must match the corrected formula; transposed formula is now a regression oracle that must NOT match; classification updated |
| `python/tests/test_stage10_15_1_trajectory_audit.py` | updated to the post-fix contract (0 jumps; CSV == corrected formula) |
| `python/analysis/stage10.15_2_compare.py` | NEW comparison script (pre/post summary JSON, per-step CSV, 5 figures) |

**Unchanged physics:** melt parameterizations, drag coefficients, Coriolis
formulation (only its latitude input is now correct), turbulence closures,
thermal equations, low-flow closure, defaults, time step, constants, forcing
datasets, initial iceberg state. **No production default changed.** The
synthetic TEST grid (`grid_mode=TEST` in `coup1`) has its own transposed
fi/dl definition (fi∝j, dl∝i) — TEST-ONLY, documented, not a production
path, left unchanged.

## 5. Regression tests

### 5.1 New test: `iceberg_test_bilinear_axis_regression.f90` (13 checks)

| # | Check | Analytical basis | Pre-fix | Post-fix |
| - | ----- | ---------------- | ------- | -------- |
| 1 | exact-node property | F(i1,j1) at wx=0,wy=0 | PASS | PASS |
| 2 | constant-field property | F≡7 at any weights | PASS | PASS |
| 3 | X-only field varies with wx | F=0.1(j−1): value = 0.1(j1−1+wx) | **FAIL** (0.67 vs 0.63) | PASS |
| 4 | X-only field invariant to wy | same field, wy=0.7 vs 0.4 | **FAIL** | PASS |
| 5 | Y-only field varies with wy | F=0.1(i−1): value = 0.1(i1−1+wy) | **FAIL** | PASS |
| 6 | Y-only field invariant to wx | same field, wx=0.3 vs 0.2 | **FAIL** | PASS |
| 7 | linear X+Y field exact | F=0.1(i−1)+0.2(j−1) | **FAIL** (1.77 vs 1.73) | PASS |
| 8 | 3D layer k=2 exact | +5.0(k−1) offset | **FAIL** | PASS |
| 9 | 3D layer k=3 exact | +10.0 offset | **FAIL** | PASS |
| 10 | boundary continuity (pure function) | left/right limits at j-boundary | **FAIL** (0.65 vs 0.75) | PASS |
| 11 | latlon at node ok | real grid | PASS | PASS |
| 12 | trajectory continuity across j-boundary | real grid, x crosses 500040 m | **FAIL** (0.170° step) | PASS (5.3e-5°) |
| 13 | i-boundary crossing continuity | real grid, y crosses 833400 m | **FAIL** (0.170° step) | PASS (9.2e-5°) |

**Pre-fix failure evidence:** with the source temporarily reverted
(`git stash push src/iceberg_forcing.f90`), the test reports
`FAILURE: BILINEAR AXIS REGRESSION FAILED` — 10 errors, including the exact
0.170° trajectory jumps; with the fix restored it reports
`SUCCESS: BILINEAR AXIS REGRESSION PASSED` — 13/13. This demonstrates the
test detects the old bug and validates the fix.

### 5.2 Corrected test: `iceberg_test_artificial_forcing.f90`

Passes 5/5 post-fix (the expectations now use the correct wx↔lon/j,
wy↔lat/i association; the test would fail on the pre-fix formula).

### 5.3 Python regression: `test_stage10_15_1_trajectory_audit.py` (29 checks)

Post-fix contract PASS: CSV == corrected formula (1.3e-5°), 0 jumps,
geographic trajectory continuous, implied geographic speed matches reported
speed (corr 0.988).

## 6. Operational rerun (TEST_11, 30 days, real forcing)

| Item | Value |
| ---- | ----- |
| Command | `fpm test --flag "-I/usr/include" iceberg_test_11_30day_offline` |
| Inputs | ERA5 `era5_2020_0103_barents_expanded_merged.nc` (364 slices); EN4 `initial_ts_2020-01-01.nc`; IBCAO grid (KOORD.DAT/hhh.bar); same config as Stage 10.15 (`basal_melt_scheme=0`, `thermal_evolution_enabled=.true.`, `low_flow_closure_enabled=.false.`) |
| Run duration | 30 days, dt=3600 s, 720 steps |
| Exit code | 0 |
| Runtime | ~40 s wall clock (within the full battery) |
| Output files | `data/output/diagnostics/stage9.3/test11_trajectory.csv` (raw), `data/output/stage10.15/test11_trajectory.csv` (bundle copy), `data/output/stage10.15_2/test11_trajectory_post_fix.csv` |
| Trajectory rows | 720 |
| Coordinate ranges | lat 74.9969–75.0676 °N, lon 29.7553–30.1417 °E (post-fix) |
| Speed | max reported 0.0271 m/s; max implied geographic 0.0269 m/s |
| Melt max [m/day] | basal 0.0483, lateral 0.2599, surface 0.0220 |
| Mass | 909.8 → 769.6 Mt (−15.41 %) |
| Geometry | L/W 100 → 92.21 m, H 100 → 99.47 m |
| Warnings | none (no NaN, no land warnings, budget error 0.002 %) |

The output is generated from the corrected model run (not post-processing
reconstruction). The model-space x/y trajectory is nearly identical to
pre-fix (11.43 vs 11.45 km straight, 25.96 vs 26.04 km path) — expected,
because the coordinate bug mainly corrupted the geographic columns and the
forcing-position mirroring was sub-cell.

## 7. Pre-fix / post-fix results

| Metric | Pre-fix | Post-fix |
| ------ | ------- | -------- |
| Coordinate jumps (>0.05°) | **8** (steps 2, 58, 83, 180, 384, 599, 608, 622) | **0** |
| Max Δlat / Δlon per step | 0.1702° / 0.1779° | 0.0007° / 0.0034° |
| Max geographic step | 19,586 m | 97 m |
| Max implied geographic speed | 5.44 m/s (impossible) | 0.0269 m/s |
| Max reported speed | 0.0276 m/s | 0.0271 m/s |
| corr(implied geo, reported) | 0.029 | **0.988** |
| Max |implied−reported| (x/y) | 0.0040 m/s | 0.0040 m/s |
| Displacement (straight/path) | 11.45 / 26.04 km | 11.43 / 25.96 km |
| Mass change | −15.41 % | −15.41 % |
| Final L / H | 92.21 / 99.47 m | 92.21 / 99.47 m |
| Melt max (basal/lateral/surface) | 0.0489 / 0.2600 / 0.0219 m/day | 0.0483 / 0.2599 / 0.0220 m/day |

**Forcing:** the correction changes the sampled forcing position. The
geographic columns (ERA5 lookup position via `get_atmos_forcing` and the
Coriolis latitude) are corrected; ocean T/S/u/v are interpolated at the
index-consistent position. The observed thermodynamic differences are tiny
(basal melt −1.2 %, lateral −0.03 %, surface +0.6 %, mass identical to 3
significant figures) because the ocean/atmospheric fields vary slowly over
the sub-cell offset and the lateral melt (constant ~0.26 m/day, depth-
averaged ΔT) dominates. This is an **expected secondary consequence of
corrected spatial sampling**, not a physics change.

**T-07 drift anomaly:** unchanged. `drift_scaling_wind` (0.04–0.12 % with
Coriolis vs 1–2 % literature) and `drift_scaling_current` (0.13–1.24 % vs
2–5 %) reproduce the pre-fix archived numbers exactly (the drift tests
prescribe lat/lon directly and do not exercise the corrected interpolation
path). **T-07 remains OPEN.**

## 8. Limitations

- Continuous coordinates do **not** prove correct drift physics (T-07
  remains; drift amplitude is still governed by the known drag/Coriolis
  anomaly).
- The corrected interpolation does **not** resolve T-07 automatically —
  drift-scaling diagnostics are unchanged.
- Test-harness execution is **not** production-executable integration —
  `app/main.f90` still does not run the iceberg module (Stage 10.15 §8).
- **No observational validation** was performed in this stage.
- The ocean NaN/zombie state (Stage 8 family, full-model runs) is a separate
  issue, **not** affected by this fix.
- **No calibration** was performed.
- The synthetic TEST grid (`grid_mode=TEST`) retains its own transposed
  fi/dl definition — TEST-ONLY; production uses the real grid.
- The corrected trajectory replaces the Stage 10.15.1 corrected
  reconstruction as the authoritative geographic output; the historical
  Stage 10.15/10.15.1 reports are preserved unchanged, and the new corrected
  run is referenced from this report.

## 9. Classification

**Coordinate mapping and bilinear interpolation fix completed —
regression-tested and operationally re-run.**

**Confirmed by tests:** correct analytical interpolation (constant, X-only,
Y-only, X+Y fields); correct axis association; continuity across cell
boundaries; corrected coordinate conversion; successful repeated 30-day run;
0 coordinate jumps; implied geographic speed matches reported speed
(corr 0.988).

**Supported operationally:** the model runs with the corrected source;
corrected trajectory and time series are generated; outputs are
reproducible (deterministic audit + comparison scripts).

**Not established by this stage:** absolute drift accuracy; agreement with
observations; correctness of all ocean physics; correctness of the
production executable path; resolution of T-07; universal validity of the
drift model; production readiness.

## 10. Reproducibility

```bash
# 1. Build + focused tests
rm -rf build
fpm test --flag "-I/usr/include" iceberg_test_bilinear_axis_regression
fpm test --flag "-I/usr/include" iceberg_test_artificial_forcing
fpm test --flag "-I/usr/include" iceberg_test_coord_mapping
fpm test --flag "-I/usr/include" iceberg_test_coord_roundtrip

# 2. Repeat the 30-day run (post-fix)
fpm test --flag "-I/usr/include" iceberg_test_11_30day_offline

# 3. Python audit (post-fix contract)
conda run -n iceberg-thermodynamic-model python python/analysis/stage10.15_1_trajectory_audit.py
conda run -n iceberg-thermodynamic-model python python/tests/test_stage10_15_1_trajectory_audit.py

# 4. Pre/post comparison
conda run -n iceberg-thermodynamic-model python python/analysis/stage10.15_2_compare.py
```

Outputs (gitignored): `data/output/stage10.15_2/` — `comparison_summary.json`,
`per_step_comparison.csv`, `test11_trajectory_post_fix.csv`,
`pre_fix/` (pre-fix CSV + Stage 10.15 summary + Stage 10.15.1 audit summary
+ 10.15.1 plots), `plots/fig1..fig5` (pre-vs-post trajectory, geographic
step size, reported-vs-implied speed, x/y trajectory, mass comparison).

## 11. Next steps (unchanged from Stage 10.15.1 §11, now unblocked)

1. The geographic trajectory is now trustworthy for continuity purposes;
   the next scientific question is whether the corrected spatial sampling
   changes the drift behavior — **drift-scaling re-investigation (T-07)**
   with the corrected code is the immediate next step (this stage shows the
   T-07 numbers are unchanged, so the investigation must focus on drag/
   Coriolis formulation, not interpolation).
2. Production-path integration of the iceberg module remains open.
3. Ocean initialization stabilization (NaN/zombie) remains open.
4. Only after T-07 is understood: trajectory-level observational comparison.

No new physical parameterization is proposed by this stage.