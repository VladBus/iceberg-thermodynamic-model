# Stage 12.15 — Current-code Enderlin hindcast and 2020/2024 drift maps

**Date:** 2026-11-12  
**Status:** COMPLETE — 190/190 Enderlin hindcasts on the current code; no
calibration; drift-force diagnostics added; annual drift maps produced.  
**Scope:** Enderlin23 rerun with locally acquired Antarctic site forcing,
current-code metrics/strata, force-diagnostic CSV output, 2020/2024 100^3
trajectory maps. No physics or parameter changes.

## 1. Executive summary

| Item | Result |
| --- | --- |
| Enderlin23 rerun | **190/190 OK**, 0 skipped, wall 992 s, RSS 137 MB |
| Median model/observed ratio | **0.540** |
| Mean ratio | **1.081** |
| Spearman (model vs observed) | **0.156** |
| MAE / RMSE | **0.0287 / 0.0399 m/day** |
| Bias | **−0.0219 m/day** |
| Median modeled / observed | 0.0210 / 0.0383 m/day |
| Size strata, median ratio | ≤100 m **1.248** (n=20); 100–300 m **0.832** (n=60); >300 m **0.407** (n=110) |
| 2020 drift | path 192.0 km, net 36.9 km, mean **0.00607 m/s** |
| 2024 drift | path 168.2 km, net 68.7 km, mean **0.00532 m/s** |
| Force diagnostics | per-step wind/water/Coriolis/pressure/FK forces written to `run.nc_forces.csv` |

The Enderlin rerun is a validation baseline only. The 0.54 median ratio and
the monotonic size trend are not calibration targets; no coefficient was
changed. The low annual drift speed is consistent with the documented
Coriolis-limited equilibrium of a 100 m cube (Stage 10.16), not with a missing
wind force (see §5).

## 2. Inputs and provenance

The 12.14 rerun was blocked because the Antarctic GLORYS site files and
trajectories were absent. For 12.15 the seven local site files were acquired
(BG, CG, HG, LG, SG, TG, WG) and the 190-row trajectory manifest was built at
`data/validation/stage12.15/enderlin_trajectory_manifest.csv`. This was a
one-time local acquisition; no download is required by later stages.

- Model: `iceberg_run`, voxel thermodynamics, `--prescribed_trajectory`.
- Grid: default **8^3 / 12.5 m** test grid, not the 1 m science grid.
- Forcing: site GLORYS12 daily files and trajectory durations from Enderlin23.
- Metric: `(basal + lateral + wave) / rho_ice / (mean wetted area × seconds)`
  in m/day; surface/vapour losses are excluded, matching Enderlin23
  SUBMARINE_TOTAL.
- Results: `data/validation/stage12.15/enderlin_current2/enderlin23_hindcast_results.csv`.
- Metrics: `python/analysis/stage12.15_enderlin_metrics.py`.

## 3. Current-code metrics

| Metric | 12.7a voxel baseline | 12.15 current voxel |
| --- | ---: | ---: |
| N | 190 | 190 |
| Median ratio | 0.0593 | **0.540** |
| Mean ratio | 0.132 | **1.081** |
| Spearman | 0.153 | **0.156** |
| MAE [m/day] | 0.0414 | **0.0287** |
| RMSE [m/day] | 0.0518 | **0.0399** |
| Bias [m/day] | −0.0413 | **−0.0219** |
| Median modeled [m/day] | 0.00227 | **0.0210** |

The current code removes most of the 12.7a low bias, but the rank correlation
is still weak. The mean ratio above 1 is carried by a small number of
high-ratio cases (the distribution is heavy-tailed); the median remains below 1.

### 3.1 Size strata

| Surface-size bin | n | Median ratio | Mean ratio | Median observed | Median modeled |
| --- | ---: | ---: | ---: | ---: | ---: |
| ≤100 m | 20 | 1.248 | 2.280 | 0.0159 | 0.0159 |
| 100–300 m | 60 | 0.832 | 1.429 | 0.0354 | 0.0238 |
| >300 m | 110 | 0.407 | 0.674 | 0.0455 | 0.0200 |

### 3.2 Sites

| Site | n | Median ratio | Mean ratio | Median observed | Median modeled |
| --- | ---: | ---: | ---: | ---: | ---: |
| BG | 4 | 2.475 | 2.645 | 0.0145 | 0.0360 |
| CG | 42 | 0.470 | 1.057 | 0.0459 | 0.0229 |
| HG | 21 | 1.101 | 2.064 | 0.0097 | 0.0110 |
| LG | 9 | 1.112 | 1.686 | 0.0300 | 0.0360 |
| SG | 35 | 0.386 | 0.803 | 0.0521 | 0.0232 |
| TG | 65 | 0.446 | 0.696 | 0.0396 | 0.0189 |
| WG | 14 | 1.022 | 1.327 | 0.0497 | 0.0498 |

The melt partition is lateral-dominated at the median: basal 0.383, lateral
0.617, surface 0.0 of total submarine loss.

## 4. Drift maps 2020/2024

Existing 100^3 strict-ocean annual runs (`data/validation/stage12.14/`) were
post-processed without rerunning. Maps and daily series are in
`docs/wiki/stages/stage12/figures/stage12.15/maps/`.

| Year | Path [km] | Net displacement [km] | Mean speed [m/s] | Mean wind [m/s] | Mean current [m/s] |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 | 192.0 | 36.9 | 0.00607 | 6.62 | 0.0338 |
| 2024 | 168.2 | 68.7 | 0.00532 | 6.17 | 0.0189 |

The output contains `air_u10/v10` and `ocean_u/v_draft`, so the wind and
current forcing are present. The map script's force proxies are indicative
only (they use `a_wet` for both sail and submerged area and are not exact
force diagnostics): 2020 wind 1.37e9 vs ocean 2.65e7; 2024 wind 1.18e9 vs
ocean 6.82e6 (sums over daily records).

## 5. Why the drift is ~0.006 m/s

This is the known Stage 10.16 result, re-confirmed here for the annual runs:

- Wind is applied: `f_wind` is non-zero and of order 10^2–10^3 N for a 100 m
  cube; with zero current the model reaches 0.0020/0.0080/0.0180 m/s at
  5/10/15 m/s wind (wind ratio 0.04–0.12%).
- Coriolis is the limiter: the analytic discrete equilibrium is
  `u_eq = F_wind / (M f sqrt(1 + (f dt)^2))`; the water drag is negligible at
  that speed. With Coriolis disabled the same cube reaches 3.0–3.5% of wind.
- Sea ice does not suppress drift. `siconc` is read and written, and is used
  only by the optional wave-erosion closure; `iceberg_dynamics` has no
  sea-ice drag or concentration gate. No ice threshold exists in the drift
  path.
- Units are SI in the dynamics; no unit conversion defect was found.
- Current-only forcing gives a Coriolis-limited response, not full advection
  by the current (Stage 10.16 experiments C1/C2).

Therefore 0.006 m/s is **not** a missing-wind, sea-ice-suppression, or unit
bug. It is the documented low-order drift regime of the current physical
formulation; a literature-like 1–2% wind factor would require either a
different drag/mass regime or wind-driven ocean currents, which this offline
model does not have. No calibration was performed.

## 6. Code changes

`app/iceberg_run.f90` now writes `run.nc_forces.csv` with per-record
`u/v_ice`, `ocean_u/v`, `wind_u/v`, and the wind, water, Coriolis, pressure,
and Froude–Krylov force components. This makes the annual drift budget
auditable without rerunning; the 12.15 test case is
`data/validation/stage12.15/drift_force_test/`.

`python/validation/enderlin23_hindcast.py` now writes per-model basal,
lateral, surface, and wave mass losses, mean wetted area, and duration columns.
`python/reanalysis/download_cmems.py` gained an opt-in `--resume` path used to
complete the local site files.

## 7. Verification and limitations

- Hindcast: `190/190 OK`, 0 skipped, 992 s, RSS 137 MB.
- Metrics script and maps script completed without errors.
- The hindcast grid is 8^3 / 12.5 m; it is a test grid, not the 100^3 / 1 m
  science grid. The Enderlin metrics are therefore not a resolution-converged
  result.
- Trajectories are prescribed; drift dynamics are not tested by Enderlin.
- No calibration, no coefficient change, no new physics.
- The annual drift remains unvalidated against observed iceberg tracks. The
  force-proxy comparison is not a closure test; exact force components are
  available only in new runs with the force CSV.

## 8. Files

- Report: this file.
- Metrics: `docs/wiki/stages/stage12/figures/stage12.15/enderlin_metrics_current.csv`,
  `enderlin_comparison.csv`, `enderlin_scatter_current.png`.
- Maps: `figures/stage12.15/maps/drift_track_2020.png`,
  `drift_track_2024.png`, `melt_components_2020.png`,
  `melt_components_2024.png`, `summary_2020.json`, `summary_2024.json`.
- Scripts: `python/analysis/stage12.15_enderlin_metrics.py`,
  `python/analysis/stage12.15_maps.py`.
