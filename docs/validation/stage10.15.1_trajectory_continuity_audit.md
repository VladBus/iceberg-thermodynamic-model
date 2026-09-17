# Stage 10.15.1 — Trajectory Continuity and Output Integrity Audit

**Classification: Trajectory continuity audit completed — real discontinuity
identified (coordinate-conversion bug in `model_coords_to_latlon` /
`bilinear_interp_3d`)**
**Production physics changed: NO**
**Default configuration changed: NO**
**Source code changed: NO (diagnostics + documentation only)**

This stage is a narrow technical audit of the Stage 10.15 trajectory output.
It is a follow-up to Stage 10.15, **not** a new physical modernization,
**not** calibration, **not** observational validation, and **not** proof of
correct iceberg drift physics.

| Item | Value |
| ---- | ----- |
| Stage | 10.15.1 (trajectory continuity and output integrity audit) |
| Branch / HEAD | `main` @ `472fe75` (Stage 10.15 committed and pushed) |
| Audited CSV | `data/output/stage10.15/test11_trajectory.csv` (raw Fortran output: `data/output/diagnostics/stage9.3/test11_trajectory.csv`) |
| New audit script | `python/analysis/stage10.15_1_trajectory_audit.py` |
| New regression tests | `python/tests/test_stage10_15_1_trajectory_audit.py` (28 checks) |
| Output bundle (gitignored) | `data/output/stage10.15_1/` |

---

## 1. Scope

Stage 10.15.1 answers one question: **is the Stage 10.15 trajectory a
continuous computational output, and does its visualization faithfully
represent the underlying data?** Specifically, whether the unusual appearance
of the trajectory figure (local colored clusters connected by long thin gray
lines) is:

1. only a plotting artifact;
2. a data-ordering or segmentation problem;
3. a real coordinate discontinuity;
4. a real numerical or physical trajectory problem;
5. an output-generation problem.

This stage does not introduce physical parameterizations, does not calibrate,
does not change production defaults, does not enable the low-flow closure, and
does not rewrite historical reports. It does not silently hide discontinuities
or remove suspicious data.

## 2. Provenance

- Stage 10.15 report: `docs/validation/stage10.15_operational_demonstration.md`
  (original report — **kept unchanged**; this audit is a dated follow-up).
- Stage 10.15 diagnostic script: `python/analysis/stage10.15_diagnostics.py`.
- Audited CSV (exact): `data/output/stage10.15/test11_trajectory.csv`
  (131,127 bytes, 720 data rows + header; identical bytes to the raw TEST_11
  output `data/output/diagnostics/stage9.3/test11_trajectory.csv`, written by
  `test/iceberg_test_11_30day_offline.f90` `save_trajectory_csv`).
- Plotting script (original figure): `python/analysis/stage10.15_diagnostics.py`
  `make_plots` fig1 (`ax.scatter` colored by time + `ax.plot(..., "k-")` in
  file order).
- Grid used by the reverse projection: `data/input/generated/real_grid/KOORD.DAT`
  (`fi`/`dl` arrays, 133×105 nodes, Fortran column-major).
- Coordinate conversion source: `src/iceberg_forcing.f90`
  (`model_coords_to_indices`, `model_coords_to_latlon`, `bilinear_interp_3d`,
  `get_ocean_profile`).
- Roadmap / known issues: `docs/PROJECT_ROADMAP.md`,
  `KNOWN_ISSUES.md` (T-07 drift anomaly, T-12 symlinks).

## 3. Input

| Item | Value |
| ---- | ----- |
| Input file | `data/output/stage10.15/test11_trajectory.csv` |
| Rows | 720 (header + 720 data rows) |
| Time interval | dt = 1 h (3600 s), `time_h` = 1.0 … 720.0 h |
| Coordinate columns | `x_m`, `y_m` (model coordinates, m); `lat_deg`, `lon_deg` (geographic, deg) |
| Velocity columns | `u_ms`, `v_ms` (m/s) |
| Other columns | `L_m`, `W_m`, `H_m`, `M_kg`, `mb_mday`, `ml_mday`, `ms_mday` |
| Model configuration | TEST_11 offline harness: `basal_melt_scheme = BASAL_MELT_SCHEME_FORCED_CONVECTION` (0), `thermal_evolution_enabled = .true.`, `low_flow_closure_enabled = .false.`; dt = 3600 s |
| Forcing period | ERA5 2020-01 (Q1), 6-hourly, real (`era5_2020_0103_barents_expanded_merged.nc`, 364 slices); EN4 initial T/S; IBCAO real grid |
| Run duration | 30 days (720 hourly steps) |

## 4. Audit methodology

All checks are deterministic and implemented in
`python/analysis/stage10.15_1_trajectory_audit.py`; thresholds are explicit
and classed (see §5 and the script header).

### 4.1 Timestamp checks

- expected row count = 720; steps strictly monotonic 1…720;
- duplicate timestamps = 0; time interval constant (1 h);
- total duration 720 h.

### 4.2 Coordinate ordering and continuity

- finiteness and domain membership of `lat_deg`/`lon_deg`
  (lat ∈ [60, 90], lon ∈ [−20, 100] — existing Stage 10.15 convention);
- consecutive-row differences `|Δlat|`, `|Δlon|`; discontinuity flag when
  either exceeds **0.05°** (justification: the corrected formula has max
  step 0.0007° lat / 0.0034° lon — the 0.05° threshold is >10× the corrected
  maximum and ≈1 grid cell, ~0.12–0.17°);
- consistency of coordinate order with time order (row `k` is step `k`);
- dateline handling: not applicable (lon ∈ [29.7, 30.3]).

### 4.3 Displacement and implied-speed calculation

- model-space displacement: `dist = hypot(Δx_m, Δy_m)`;
- implied model speed: `v_impl = dist / (3600 s)`;
- geographic (great-circle) implied speed computed from the **corrected**
  coordinates with the haversine formula (proper local-distance
  approximation; degrees are never compared with metres directly);
- comparison with reported speed `hypot(u_ms, v_ms)`;
- max displacement, max implied speed, max |implied − reported| per interval.

### 4.4 Reverse-projection reproduction (root-cause test)

The exact Fortran formulas were reproduced in Python:

- `model_coords_to_indices`: `j_idx = floor(x/DX)+1` (j ↔ X),
  `i_idx = floor(y/DX)+1` (i ↔ Y), DX = 13890 m;
- `model_coords_to_latlon` **as written** (bilinear over the four cell
  corners, with weights `wx` on the i index and `wy` on the j index);
- the **corrected** index-consistent formula (x-weight `wx` on the j index,
  y-weight `wy` on the i index — matching the declared j↔X, i↔Y mapping).

The CSV lat/lon was compared against the as-written reproduction
(tolerance 1e-3°) and the corrected reproduction was checked for continuity.

### 4.5 Plotting-segmentation inspection

The original figure code was inspected (`stage10.15_diagnostics.py` fig1):
it plots **one** `ax.plot(lon, lat, "k-")` over **all** points in file order,
plus a scatter colored by time. There is no segmentation, no grouping, no
color-array reordering, no start/end table, and no second trajectory. The
gray lines are therefore the single polyline connecting consecutive file
rows; they faithfully connect whatever the lat/lon columns contain.

### 4.6 Threshold classes

| Class | Checks | Thresholds |
| ----- | ------ | ---------- |
| Hard data-integrity | row count, monotonic time, duplicates, constant dt, finiteness, domain, mass monotone, geometry positive, melt non-negative, length consistency | as defined in the script (`EXPECTED_ROWS`, `DT_HOURS`, `MASS_MONO_EPS`, …) |
| Diagnostic warnings | coordinate jumps, implied-vs-reported mismatch, displacement anomalies | `JUMP_DEG=0.05°`, `SPEED_MISMATCH_MS=0.01`, `DISP_JUMP_M=5000` |
| Model plausibility | speed band, melt bound | `SPEED_BAND=(0.005, 0.5)` m/s, `MELT_MAX_MDAY=5.0` (existing TEST_11 conventions) |

A warning is **not** classified as a failure unless the criterion is an
established project convention.

## 5. Results

| Item | Value |
| ---- | ----- |
| Rows | 720 (all valid; no missing, no duplicates) |
| Time | strictly monotonic, dt = 1 h constant, 720 h total — **PASS** |
| Coordinates finite / in domain | PASS (lat 74.828–75.161, lon 29.744–30.314) |
| CSV vs as-written `model_coords_to_latlon` | **match to 1.44e-5°** — the CSV faithfully encodes the Fortran projection |
| Coordinate jumps (> 0.05°) | **8**: steps 2, 58, 83, 180, 384, 599, 608, 622 |
| Max coordinate jump | **0.1702° lat, 0.1779° lon (~19 km)** — while x/y move only ~40 m in those steps |
| Max implied speed from x/y | 0.0276 m/s (== max reported 0.0276 m/s) |
| Max |implied − reported| (x/y) | **0.0040 m/s** — model-space kinematics consistent |
| Geographic implied speed (as-written lat/lon) | 5.44 m/s spikes; corr(reported) = **0.029** — inconsistent |
| Geographic implied speed (corrected lat/lon) | max 0.0275 m/s; corr(reported) = **0.988**; max mismatch 0.004 m/s — consistent |
| Corrected formula continuity | **continuous**: max step 0.00072° lat / 0.00338° lon; **0 jumps** |
| Anomalous intervals (> 5 km/step) | 0 (in x/y) |
| Thermodynamics | mass finite, geometry positive, mass monotone non-increasing, melt finite/non-negative/bounded — all PASS |
| Gray lines in fig1 | **real coordinate discontinuities**, faithfully rendered (see §6) |
| Trajectory continuous? | x/y (model coordinates): **YES**. Geographic columns: **NO** (8 jumps) — but a corrected reverse projection is continuous |

All 28 regression checks PASS; the single expected "failure" is the
coordinate-jump check itself, which is the audited finding (the audit
script's summary JSON records it as the classification, not as a hidden
error).

## 6. Root cause

**Classification: real trajectory discontinuity (geographic coordinates),
caused by a coordinate-conversion bug — transposed bilinear weights in
`model_coords_to_latlon` and `bilinear_interp_3d`.**

### Evidence

1. The model-space trajectory (x/y) is **continuous and kinematically
   self-consistent**: implied speed from x/y equals the reported speed to
   0.004 m/s (corr 0.988 with corrected geography); max speed 0.0276 m/s is
   within the model's own plausible band.
2. The geographic columns contain **8 real jumps of ~0.17°** (~19 km) at
   exactly the steps where the iceberg crosses a model-cell boundary
   (i_idx/j_idx changes). In those steps x/y move by only ~40 m — a 19 km
   jump is physically impossible for the reported velocity.
3. A Python reproduction of the **as-written** Fortran formula reproduces the
   CSV to 1.44e-5° (float32 noise) — the output generation is faithful; the
   bug is upstream in the formula itself.
4. The **corrected** (index-consistent) formula removes all 8 jumps and
   makes the implied geographic speed match the reported speed
   (corr 0.988, max mismatch 0.004 m/s) — the corrected geography is the
   physically consistent one.

### The bug

In `src/iceberg_forcing.f90`:

- `model_coords_to_indices` maps **j ↔ X** (`j_idx = floor(x/DX)+1`) and
  **i ↔ Y** (`i_idx = floor(y/DX)+1`);
- the bilinear weights are `wx = (x − x_j)/(x_j2 − x_j1)` (X-direction)
  and `wy = (y − y_i)/(y_i2 − y_i1)` (Y-direction);
- but `bilinear_interp_3d` (and the identical inline formula in
  `model_coords_to_latlon`) applies `wx` to the **i** index and `wy` to the
  **j** index:

```fortran
! as written (transposed cross terms):
val = wx1*wy1*arr(i1, j1, k) + wx*wy1*arr(i2, j1, k) &
    + wx1*wy*arr(i1, j2, k) + wx*wy*arr(i2, j2, k)

! index-consistent (x-weight on j, y-weight on i):
val = wx1*wy1*arr(i1, j1, k) + wx*wy1*arr(i1, j2, k) &
    + wx1*wy*arr(i2, j1, k) + wx*wy*arr(i2, j2, k)
```

The two cross terms are swapped. Inside a cell the transposed formula still
returns a smooth surface, but **at cell boundaries the stencil switches to a
different corner set, producing a discontinuity of ~one grid cell** (~0.1–0.9°
in lat/lon, here ~0.17°). The iceberg in TEST_11 oscillates around model
coordinates x≈500 km, y≈833 km — i.e., near the i=60/61 and j=36/37 cell
boundaries — and crosses them 8 times in 30 days, producing exactly the 8
observed jumps.

### Secondary effects (same bug, same source)

- `bilinear_interp_3d` is also used by `get_ocean_profile` for ocean
  T/S/u/v interpolation at the iceberg position → the ocean forcing is
  interpolated with the same transposed weights (sub-cell mirroring + cell
  jumps of the ocean-field gradient magnitude).
- `state%latitude/longitude` feed `get_atmos_forcing` (ERA5 interpolation)
  and the Coriolis parameter in `iceberg_step` → the atmosphere is sampled
  at the jumped geographic position; the Coriolis term uses a jumped
  latitude (f-error ~0.2% at 0.17° — minor).

### Why the existing tests did not catch it

- `iceberg_test_coord_mapping` (TEST 1) samples **exactly at grid nodes**
  (wx=wy=0), where the transposed and correct formulas coincide — error 0.
  TEST 4 (trajectory round-trip) does expose **0.132° lat / 0.152° lon**
  errors but only prints a WARNING and the pass criterion is the loose
  0.2°/0.1° round-trip tolerance; `n_errors` stays 0 → PASSED.
- `iceberg_test_coord_roundtrip` reports MAX LAT ERROR 0.064° / MAX LON
  ERROR 0.179° but accepts them as "within model grid resolution" (0.2°).
- TEST_11 checks continuity of mass/geometry/NaN but **never checks
  coordinate continuity** (a ~19 km jump passes "no NaN, in domain").
- The Stage 10.15 diagnostics checked lat/lon domain and speed from **u/v**,
  not from coordinates, so the mismatch (corr 0.03) was invisible.

This audit adds Python regression coverage that **does** detect the
transposition (28 checks), independent of the Fortran suite.

## 7. Changes

| File | Change | Affects |
| ---- | ------ | ------- |
| `python/analysis/stage10.15_1_trajectory_audit.py` | NEW — deterministic audit script (checks + per-step CSV + corrected trajectory CSV + 9 figures + summary JSON) | diagnostics only |
| `python/tests/test_stage10_15_1_trajectory_audit.py` | NEW — 28 regression checks (synthetic formula regression + real-output audit) | tests only |
| `docs/validation/stage10.15.1_trajectory_continuity_audit.md` | NEW — this report | documentation |
| `docs/validation/INDEX.md`, `docs/PROJECT_ROADMAP.md`, `KNOWN_ISSUES.md` (T-13), `CHANGELOG.md` | updated | documentation |

**Unchanged:** `src/`, `app/`, `test/`, `fpm.toml`, all historical reports,
`docs/validation/stage10.15_operational_demonstration.md` (original Stage
10.15 report preserved; the corrected figure is linked from this report).

**Why the source is not changed in this stage:** the fix is a one-line-pair
swap in `bilinear_interp_3d`/`model_coords_to_latlon`, but it changes model
behavior (geographic coordinates, ocean forcing positions, atmospheric
sampling position). Per the stage mandate (audit only; no production change),
the correction is deferred to a dedicated stage (see §11) with its own
regression tests and a re-run of TEST_11. This audit's corrected trajectory
CSV is a **diagnostic reconstruction** (what the projection would report with
index-consistent weights for the same x/y), explicitly **not** a new model
run.

## 8. Limitations

Explicitly preserved distinctions:

- **A continuous trajectory is not automatically a physically accurate
  trajectory.** The x/y trajectory is continuous and self-consistent, but
  the Stage 10.15 drift amplitude remains governed by the known T-07 drift
  anomaly (wind ratio 0.13 % vs 1–2 %).
- **A bounded speed is not proof of correct drift physics.** Reported speeds
  are within the plausible band by construction of the TEST_11 check.
- **A successful test harness is not equivalent to production integration.**
  The trajectory is produced by the offline test program; `app/main.f90`
  still does not run the iceberg module (Stage 10.15 §8).
- **T-07 remains unresolved** — this audit did not address drift physics.
- **Observational comparison is still not performed** — and per Part VIII
  policy, the geographic-coordinate defect must be fixed before the
  trajectory can be used for trajectory-level observational validation.
- The corrected trajectory is a Python-side reconstruction of the reverse
  projection only; it does not re-run the model and does not correct the
  (transposed) ocean-forcing interpolation used inside the run.

## 9. Classification

**Trajectory continuity audit completed — real discontinuity identified.**

Primary category: **C — real trajectory discontinuity** (in the geographic
coordinate columns), with the root cause traced to the source:
**coordinate-conversion / interpolation bug (transposed bilinear weights) in
`model_coords_to_latlon` and `bilinear_interp_3d`** (`src/iceberg_forcing.f90`).

Secondary classification: the Stage 10.15 figure is **not** a plotting
artifact in the sense of incorrect plotting code — the polyline faithfully
renders the lat/lon columns. The gray connecting lines are the real jumps;
the figure's only shortcoming is that it does not mark the discontinuities
as breaks. The plotting code is otherwise correct (chronological order,
no segmentation, no reordering, no artificial connectors).

Not claimed: validated; production-ready; physically confirmed;
observationally validated.

## 10. Reproducibility

```bash
# 1. Regenerate audit outputs (deterministic; requires the Stage 10.15 CSV
#    and KOORD.DAT):
conda run -n iceberg-thermodynamic-model \
    python python/analysis/stage10.15_1_trajectory_audit.py

# 2. Regression tests:
conda run -n iceberg-thermodynamic-model \
    python python/tests/test_stage10_15_1_trajectory_audit.py

# 3. (Reference) Fortran tests that demonstrate the missed bug:
rm -rf build && fpm test --flag "-I/usr/include" iceberg_test_coord_mapping
fpm test --flag "-I/usr/include" iceberg_test_coord_roundtrip
```

Outputs (gitignored): `data/output/stage10.15_1/audit_summary.json`,
`audit_per_step.csv` (per-interval dt/Δlon/Δlat/displacement/implied speed/
reported speed/mismatch/jump flag), `corrected_trajectory.csv`,
`plots/fig1…fig9.png` (original reproduction; chronological with breaks;
corrected continuous; points-only; start/end markers; anomaly segments;
implied-vs-reported speed; time-step length; CSV-vs-corrected lat/lon).

## 11. Recommended next step

1. **Fix the transposed bilinear weights** in `bilinear_interp_3d` and
   `model_coords_to_latlon` (`src/iceberg_forcing.f90`) in a dedicated
   minimal stage (one-line-pair swap each), with: (a) Fortran regression
   tests that sample **interior** cell points (not only nodes) and assert
   round-trip/continuity within ~1e-3°; (b) the Python audit tests as a
   cross-check; (c) a re-run of TEST_11 and regeneration of the Stage 10.15.1
   corrected trajectory as the authoritative geographic output; (d) a
   documented re-check of ocean-forcing positions (`get_ocean_profile` uses
   the same function).
2. Until the fix lands, the Stage 10.15 geographic trajectory must **not**
   be used for trajectory-level scientific claims or observational
   comparison (the model-space x/y trajectory remains usable for
   kinematics-only checks).
3. After the fix: re-assess T-07 drift anomaly and only then consider
   trajectory-level observational validation (unchanged from Stage 10.15
   §11 recommendations).

No new physical parameterization is proposed by this stage.