# Stage 12.8 — Barents Sea 2020 Matrix Experiments

**Status:** COMPLETE (24/24 voxel runs) — **with documented forcing fallbacks**.
**Date:** 2026-11-01
**Decision:** D-63
**Base:** `5bedc1c` (Stage 12.7c)

## 1. Data and deviations from the brief

CMEMS authentication remains geo/IP-blocked (HTTP 403 `RBAC: access denied`).
The requested **daily** 2020 GLORYS subset (~23 GB) and full-year ERA5 could not
be acquired. To keep the matrix reproducible and memory-bounded on the 8 GB
host, the following fallbacks were used and are **not** equivalent to the
brief:

| Input | Requested | Used | Why |
| ----- | --------- | ---- | --- |
| GLORYS12 | 365 daily files, 63–86°N/5–80°E/0–600 m | **18 monthly means** (2020-01…2021-06), 306 MB, packed NetCDF | CMEMS auth blocked; native daily S3 chunks would be ~100 GB |
| ERA5 | 12 monthly files, full year | **constant atmosphere** (`u10=v10=0`, `T=253.15 K`) | only Jan–May/Jul/Oct present; no full-year merge |
| WAM | optional 8 GB | **skipped** | no product; 403/absent |
| Bathymetry/start depth | IBCAO | IBCAO grid; GLORYS ocean-mask check | selected points must be valid in both |

Monthly means are assigned to the **first day of each month** so a Jan-1/Jul-1
start is inside the reader interval. This is a documented approximation.

## 2. Start points

The nominal brief coordinates are too shallow for S500 (draft ≈458 m) and some
are land/ice-shelf in GLORYS. Selection required **IBCAO depth ≥480 m and a
valid GLORYS ~500 m temperature**:

| Point | Nominal | Actual | Depth | Nominal depth |
| ----- | ------- | ------ | ----: | ------------: |
| P1 Franz Victoria Trough | 77.0N 55.0E | **82.924N 55.006E** | 600 m | 210 m |
| P2 Svalbard shelf edge | 77.5N 20.0E | **81.316N 21.204E** | 553 m | 122 m |
| P3 Central Basin/FJL | 80.0N 50.0E | **82.642N 50.407E** | 495 m | 83 m |

Manifest: `docs/validation/stage12.8_start_points.json`.

## 3. Matrix

- 4 sizes (50, 100, 200, 500 m cubes) × 2 seasons (Jan 1 / Jul 1 2020) ×
  3 points = **24 voxel runs**, 365 days, `dt=3600`.
- `VOXEL_ENABLED=ON`; free-convection floor from 12.7c; wave erosion OFF.
- **24/24 completed**, total wall 639 s, peak RSS 363 MB.
- Manifest: `docs/validation/stage12.8_matrix_manifest.csv`.
- No complete melt-out; S50/S100/S200 P2 ends at ~6.5 % of initial volume;
  S500 P2 at ~15 %.

## 4. Results

### 4.1 Drift

Start-to-end great-circle drift **1.2–6.3 km/year** (path 1.2–6.9 km).
Mean by size/season:

| Season | S50 | S100 | S200 | S500 |
| ------ | --: | ---: | ---: | ---: |
| Jan | 5.13 | 2.94 | 2.36 | 1.84 km |
| Jul | 4.06 | 3.08 | 2.74 | 1.72 km |

This is a **lower bound / numerical artifact**, not a physical Barents drift
prediction: wind is zero (constant atmosphere), forcing is monthly-mean, and
the legacy semi-implicit Coriolis solver damps velocity (`A=1+(f·dt)²`; Stage
9.3/10.16). Daily forcing, real ERA5 wind, and a revised Coriolis treatment are
required before quantitative drift claims.

### 4.2 Lifetime

Only the warm Svalbard point P2 reaches 90 % melt within a year:

| Size | Jan t50 / t90, d | Jul t50 / t90, d |
| ---- | ---------------: | ---------------: |
| S50 | 139 / 231 | 37 / 60 |
| S100 | 130 / 244 | 46 / 79 |
| S200 | 205 / 270 | 65 / 120 |
| S500 | 259 / — | 120 / — |

P1/P3 (cold, low ΔT) do not reach 90 % melt; final volume fractions are
0.15–0.59. Summer melting is much faster at P2 (t90 60–120 d vs 231–270 d);
S500 never reaches t90. `docs/validation/figures/barents2020/lifetime_heatmap.png`
uses t90 with 365 d for “not reached”.

### 4.3 Melt components

Lateral melt dominates in every run: **55–83 %** of submarine mass loss
(mean ≈65 %); basal is 17–45 %; surface and wave are **zero** (constant cold
atmosphere; no WAM). The breakdown is stable across sizes/seasons, with the
lateral fraction largest for S500 (71–83 %).

### 4.4 met.no comparison (indicative)

For S100 at P2, the model gives 3-day submarine melt of **1.39 m (Jan)** and
**0.27 m (Jul)**. The met.no reference quoted in the transition document is
~5 m in 3 days for a 100 m iceberg. The model is lower, consistent with no
wind/wave forcing, monthly means, and the voxel low-flow/large-berg lower
bound. No calibration was applied.

## 5. Figures

`docs/validation/figures/barents2020/`:

- `drift_map_Jan.png`, `drift_map_Jul.png` — trajectories colored by day and
  speed; IBCAO depth contours, land mask, 15 % sea-ice contour.
- `volume_Jan.png`, `volume_Jul.png` — V(t)/V0 for 4 sizes × 3 points; t50/t90
  markers.
- `melt_budget_Jan.png`, `melt_budget_Jul.png` — stacked cumulative basal/
  lateral/surface/wave mass loss for S100 at 3 points.
- `lifetime_heatmap.png` — t90 by size and season (mean of 3 points).

Results: `docs/validation/stage12.8_results.csv`,
`stage12.8_summary.json`.

## 6. Structural limits

- **Monthly-mean GLORYS**, not daily; **constant atmosphere** (no ERA5 wind);
  no WAM, no sea-ice drag, no tides, no calving/capsizing.
- Drift is dominated by numerical Coriolis damping and zero wind; treat it as
  a lower bound only.
- Voxel under-melts large/low-ΔT icebergs (12.7c); S500 lifetimes are
  therefore upper bounds.
- The start points were shifted far north to satisfy both IBCAO depth and the
  GLORYS ocean mask; the nominal southern shelf points are not usable for
  S500.

## 7. Acceptance status

| Criterion | Status |
| --------- | ------ |
| Daily GLORYS 2020, 365 files, ~23 GB | **NOT MET** — 18 monthly means, 306 MB |
| ERA5 2020, 12 months, ~4 GB | **NOT MET** — constant atmosphere |
| WAM 2020 | SKIPPED (documented) |
| 3 start points depth ≥150/440 m | PASS (actual 495–600 m; nominal shifted) |
| 24 voxel hindcasts | PASS (24/24) |
| WAM sensitivity | SKIPPED |
| 4 visualization types | PASS (7 figures) |
| Report with findings/limits | PASS (this report) |
| Tests / strict build / CI | PASS (81/81; strict clean; CI pending push) |
| No Stage 11 ocean code / `app/main.f90` | PASS |

## 8. GO / NO-GO for Stage 12.9 (thesis writing)

**GO for thesis writing/defense preparation**, provided the matrix is presented
as a **monthly-forcing/constant-atmosphere fallback demonstration**, not as the
requested daily-forcing Barents validation. The workflow, 24-run matrix,
figures, and structural limits are reproducible and documented.

**NO-GO for quantitative daily-forcing Barents drift/lifetime claims** until
daily GLORYS, full-year ERA5, WAM, and a corrected drift/Coriolis treatment are
available.
