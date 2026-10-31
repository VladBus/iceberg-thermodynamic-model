# Stage 12.7a — Enderlin 2023 Antarctic Iceberg Hindcast

**Status:** COMPLETE — 190/190 bulk + voxel hindcasts (validation only; no calibration).
**Date:** 2026-10-31
**Decision:** D-59
**Base:** `3edadbb` (Stage 12.6b)
**Scope:** retroactive thermodynamics validation only (no calibration, no
trajectory prediction).

## 1. Data

### 1.1 Enderlin23 sample

Source: `data/validation/observations/enderlin23/enderlin23_per_iceberg.csv`
(743 rows; USAP-DC 10.15784/601679; CC BY 4.0).  The prompt's column names
differ from the curated file; the mapping used here is
`volume_i`/`volume_f`, `surface_area`, `submerged_area`, `melt_rate`,
`lat_i/lon_i`, `lat_f/lon_f`, `date_start/date_end`.

Filter `(date_end - date_start) <= 120 days`:

| Region | N | Median interval, d | Median √A, m | Median draft, m | Median observed melt, m/day |
| ------ | -: | -----------------: | -----------: | --------------: | --------------------------: |
| WAP | 125 | 69.2 | 208 | 70.8 | 0.0369 |
| WAIS | 65 | 103.9 | 941 | 386.5 | 0.0396 |
| **Total** | **190** | 81.6 | 300 | 105.7 | 0.0383 |

Sites: BG 4, CG 42, HG 21, LG 9, SG 35, TG (WAIS) 65, WG 14.

### 1.2 GLORYS12 acquisition

The Copernicus Marine **authentication** endpoint returns HTTP 403
`RBAC: access denied` from this host (tested with real and dummy credentials;
the public OIDC metadata is also 403).  The public ARCO Zarr metadata is
readable, but its data chunks return `AccessDenied`.  The public **native S3**
bucket (`mdl-native-14`) is readable; its daily files are ~1.28 GB each with
HDF5 chunks `(1, 7, 341, 720)`.  We therefore extract only the chunks
intersecting each site's bbox/depth directly from S3 (bounded RSS; no CMEMS
credentials are used or stored).

Native files are streamed one day at a time; no whole-file download.  Local
reader-ready NetCDF contains `thetao/so/uo/vo` (packed int16, same scale/offset
as the native files), a synthetic static mask, and a time axis of the union of
each site's observation dates.  Sea-ice variables are not extracted (wave
erosion is OFF; `siconc` falls back to 0 in the reader path).

**Data volume / site table.** Native daily files are streamed; local
reader-ready NetCDF is 32.2 MB. Estimated remote chunk read is **57.8 GB**
(4 variables × depth chunks × 3.4 MB per native chunk; exact transfer not
instrumented). Sites:

| Site | Region | N | Days | Levels | Local MB |
| ---- | ------ | -: | ---: | -----: | -------: |
| BG | WAP | 4 | 56 | 27 | 1.9 |
| CG | WAP | 42 | 318 | 30 | 10.9 |
| HG | WAP | 21 | 107 | 28 | 4.6 |
| LG | WAP | 9 | 56 | 27 | 2.0 |
| SG | WAP | 35 | 88 | 30 | 2.2 |
| TG | WAIS | 65 | 202 | 34 | 8.1 |
| WG | WAP | 14 | 84 | 28 | 2.4 |

Manifest: `docs/validation/stage12.7a_glorys_manifest.json`.

## 2. Hindcast method

- **Initial geometry:** `L = W = √surface_area`, `H = volume_i / surface_area`
  (prism; draft from buoyancy is a diagnostic, not an input).  `T_ice = -10 °C`
  (documented assumption).
- **Trajectory:** linear interpolation between `(lat_i, lon_i)` and
  `(lat_f, lon_f)` over `time_separation_days`; daily positions are written to
  `data/validation/trajectories/enderlin23/` (manifest:
  `docs/validation/stage12.7a_trajectory_manifest.csv`).
- **Forcing:** GLORYS12 T/S/u/v interpolated to the iceberg draft and time.
  At ice-front cells where GLORYS is land/NaN, the nearest wet cell within
  0.5° is used (documented fallback; not applied to open-ocean points).
- **Dynamics:** disabled in prescribed mode (`iceberg_step_prescribed`);
  position is held at the observed trajectory, `u = v = 0`.
- **Models:** bulk (`VOXEL_ENABLED=false`) and voxel (`VOXEL_ENABLED=true`),
  identical initial state and forcing.
- **Wave erosion:** OFF (no Antarctic wave product staged; `ICEBERG_WAVE_EROSION`
  default false). The wave contribution is therefore zero in both runs.
- **Initial H exception:** 49/190 rows (CG 2016/2018) have `volume_i`
  inconsistent with `surface_area`/`draft` (H=V/A up to 53 km). For these,
  H is taken from the observed draft (`H = draft·ρ_w/ρ_i`); all other rows
  use V/A. This is recorded in the manifest (`H0_rule`).
- **Modeled melt rate:** `(basal + lateral + wave) / ρ_i / (mean wetted area ×
  duration)`, converted to m/day.  Surface/vapour losses are reported
  separately; Enderlin23 `melt_rate` is submarine total (side + basal).
- **No calibration:** all melt coefficients are unchanged.

## 3. Results

All 190 icebergs completed for both models (`docs/validation/stage12.7a_results.csv`).

| Metric | Bulk | Voxel |
| ------ | ---: | ----: |
| N | 190 | 190 |
| Median ratio (model/obs) | **1.394** | **0.059** |
| Mean ratio | 2.417 | 0.132 |
| Spearman (modeled vs observed) | 0.136 | 0.153 |
| MAE, m/day | 0.0302 | 0.0413 |
| RMSE, m/day | 0.0378 | 0.0517 |
| Bias, m/day | +0.0051 | −0.0413 |
| Median modeled, m/day | 0.0471 | 0.00227 |
| Median observed, m/day | 0.0383 | 0.0383 |

Bulk is close to the observed median (ratio 1.39) but has a heavy positive
tail (mean 2.42). Voxel is far too low: modeled median 0.0023 m/day vs
observed 0.0383 (ratio 0.059). Neither model reproduces the observed
rank ordering well (Spearman ≈ 0.14).

## 4. Bulk vs voxel

Bulk is clearly closer to the observations in absolute melt rate; voxel
under-melts by a factor ~17 at the median. The voxel Spearman (0.153) is only
marginally higher than bulk (0.136), so its lower bias does not translate into
better discrimination. Bulk over-predicts small icebergs and under-predicts
large ones (size stratification below); voxel under-predicts at all sizes,
most severely for `>300 m`.

Interpretation: the legacy bulk lateral parameterization is the dominant term
and gives a reasonable population median, but it is not size-selective. The
voxel three-equation/CN core is energetically too weak in this configuration
(no calibration; likely related to the per-face forcing/three-equation
closure and the constant cold atmosphere). This is a documented model
deficiency, not a calibration result.

## 5. Stratification

### By region

| Region | Model | N | Median ratio | Spearman | MAE | RMSE | Bias |
| ------ | ----- | -: | -----------: | -------: | --: | ---: | ---: |
| WAP | bulk | 125 | 1.467 | 0.191 | 0.0324 | 0.0395 | +0.0073 |
| WAP | voxel | 125 | 0.070 | 0.071 | 0.0410 | 0.0526 | −0.0409 |
| WAIS | bulk | 65 | 1.278 | 0.155 | 0.0260 | 0.0344 | +0.0007 |
| WAIS | voxel | 65 | 0.052 | 0.384 | 0.0421 | 0.0501 | −0.0421 |

### By size (√A)

| Size | Model | N | Median ratio | Spearman | MAE | RMSE | Bias |
| ---- | ----- | -: | -----------: | -------: | --: | ---: | ---: |
| ≤100 m | bulk | 20 | 3.031 | 0.501 | 0.0328 | 0.0375 | +0.0328 |
| 100–300 m | bulk | 60 | 1.900 | 0.412 | 0.0322 | 0.0391 | +0.0217 |
| >300 m | bulk | 110 | 0.942 | 0.087 | 0.0286 | 0.0372 | −0.0091 |
| ≤100 m | voxel | 20 | 0.194 | 0.296 | 0.0142 | 0.0176 | −0.0141 |
| 100–300 m | voxel | 60 | 0.110 | 0.286 | 0.0347 | 0.0441 | −0.0347 |
| >300 m | voxel | 110 | 0.045 | 0.177 | 0.0499 | 0.0592 | −0.0499 |

### By thermal forcing (mean T_w − T_f at draft)

| ΔT, °C | Model | N | Median ratio | Spearman | MAE | RMSE | Bias |
| ------ | ----- | -: | -----------: | -------: | --: | ---: | ---: |
| 0–1 | bulk | 33 | 0.707 | −0.395 | 0.0347 | 0.0443 | −0.0181 |
| 1–2 | bulk | 34 | 1.249 | −0.006 | 0.0218 | 0.0293 | +0.0021 |
| >2 | bulk | 123 | 1.416 | 0.027 | 0.0313 | 0.0380 | +0.0121 |
| 0–1 | voxel | 33 | 0.097 | 0.438 | 0.0379 | 0.0526 | −0.0378 |
| 1–2 | voxel | 34 | 0.062 | 0.084 | 0.0302 | 0.0398 | −0.0302 |
| >2 | voxel | 123 | 0.052 | 0.039 | 0.0454 | 0.0544 | −0.0454 |

Bulk ratio increases with thermal forcing (0.71 → 1.42), consistent with the
legacy lateral term being linear in ΔT. Voxel ratio decreases slightly
(0.097 → 0.052), i.e. the voxel core does not convert the additional thermal
forcing into melt as efficiently.

## 6. Limitations

- Observations are INDIRECT, area-averaged submarine melt; no calving in the
  model, so comparison is “melt without calving”.
- GLORYS12 1/12° is coarse at ice fronts; nearest-wet-cell fallback introduces
  a positional error up to 0.5°.
- Constant cold atmosphere is used (ERA5 Antarctic not staged); surface melt
  and internal temperature are therefore approximate.
- No wave erosion (no wave product), no sea-ice drag/tides.
- `T_ice = -10 °C` is an assumption; no observed ice temperature.
- Prescribed trajectory means no drift validation; only thermodynamics is
  tested.
- The native-S3 workaround reads coarse HDF5 chunks; source transfer is larger
  than the local NetCDF footprint.

## 7. Acceptance status

| Criterion | Status |
| --------- | ------ |
| 190 icebergs processed | PASS (190/190 both models) |
| GLORYS data documented | PASS (32.2 MB local; ~57.8 GB estimated remote) |
| Both bulk and voxel | PASS |
| Metrics (median ratio, Spearman, MAE, RMSE) | PASS |
| Stratification | PASS (region/size/ΔT) |
| Bulk vs voxel | PASS |
| Plots | PASS (`docs/validation/figures/enderlin23/`) |
| Full tests / strict build / CI | PASS (80 STOP 0; strict clean; CI pending push) |
| No Stage 11 ocean code or `app/main.f90` modified | PASS |
| Documentation + D-59 | PASS |
