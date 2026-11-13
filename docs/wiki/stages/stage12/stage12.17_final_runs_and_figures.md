# Stage 12.17 — Form/skin drag correction and final 100^3 runs

**Date:** 2026-11-13  
**Status:** COMPLETED (drag correction, final runs, and figures archived; Stage 12.18 supersedes the run/figure details).
**Scope:** replace the skin-scale dynamic drag coefficients with literature form
and skin drag; stabilize the drag integration at `dt=3600 s`; run six final
100^3 cases (three source regions × 2020/2024); produce thesis figures. No
calibration beyond the approved drag correction; no new downloads.

## 1. Drag correction

### 1.1 Sources and coefficients

The previous `CD_AIR=1.3e-3` and `CD_WATER=2.0e-3` are skin-friction
magnitudes, not the form drag of vertical iceberg walls. The revised dynamics
uses:

| Term | Coefficient | Source |
| --- | ---: | --- |
| air form drag, vertical sail | 1.3 | Bigg et al. (1997) |
| water form drag, vertical keel | 0.9 | Bigg et al. (1997) |
| air skin drag, horizontal top | 2.2e-3 | Keghouche et al. (2009) |
| water skin drag, horizontal bottom | 5.5e-3 | Keghouche et al. (2009) |

Form drag is applied only to vertical projections; the horizontal top `L*W`
gets skin drag only. `CD_AIR`/`CD_WATER` are retained for bulk thermal transfer
and the low-flow `u_star` closure.

### 1.2 Numerical stability

With literature form drag the explicit drag at `dt=3600 s` is unstable (15 m/s
wind produced NaN). The update now linearizes each quadratic drag force about
the old relative velocity, `K=|F_old|/|u_rel_old|`, and solves a 2x2 implicit
system with Coriolis. For `K=0` it reduces exactly to the previous semi-implicit
Coriolis step. The reported force components are the linearized forces at the
new state, so the momentum budget closes for the implicit step.

### 1.3 Verification

`test/iceberg_test_drift_force_balance.f90` (9/9 PASS):

| Case | Model | Analytic | Ratio |
| --- | ---: | ---: | ---: |
| 100 m cube, wind 7 m/s | 0.101414 | 0.102678 | 1.45% of wind |
| 100 m cube, wind 15 m/s | 0.220812 | 0.223880 | 1.47% of wind |
| 100 m cube, current 0.1 m/s | 0.085531 | 0.085568 | 85.5% of current |
| 50 m cube, current 0.1 m/s | 0.092421 | 0.092481 | 92.4% of current |
| 100 m cube, current, no Coriolis | 0.098522 | — | 98.5% of current |

The 100 m current case is the exact Coriolis-limited solution (85.6%), not a
90% criterion; the 50 m cube meets the >=90% current-following check. A
50^3/30 d run at 79.5N 45E drifts 407 km (mean 0.157 m/s) with 8.9% mass loss.

### 1.4 Sensitivity to Ca and Cw (±30%)

50^3/30 d at 79.5N 45E, 2020; all runs reached 30 d.

| Case | Mass loss [%] | Path [km] | Mean speed [m/s] |
| --- | ---: | ---: | ---: |
| base (Ca=1.3, Cw=0.9) | 8.92 | 407 | 0.157 |
| Ca +30% | 8.63 | 467 | 0.180 |
| Ca -30% | 7.89 | 336 | 0.130 |
| Cw +30% | 8.14 | 354 | 0.136 |
| Cw -30% | 9.94 | 479 | 0.185 |

## 2. Final 100^3 runs

Three source regions, same points for 2020 and 2024, selected from GLORYS
cells with depth >150 m and at least 3 cells from land:

| Source | Point | Depth [m] | Distance to land [cells] |
| --- | --- | ---: | ---: |
| Novaya Zemlya | 78.0N 55.0E | 223 | 29 |
| Svalbard/Storfjord approach | 76.5N 22.75E | 193 | 11 |
| Franz Josef Land | 80.5N 45.0E | 389 | 6 |

The NZ and FJL points survived a 30-day 100^3 screening with the corrected
drag. The Svalbard point is the best available compromise: 2024 completes the
30-day screen, while 2020 grounds after 3.2 d; the closer coastal cells (e.g.
77.0N 58.0E, 76.5N 20.5E, 80.9167N 52.0E) grounded or left the valid GLORYS
ocean within 1.5-15 days and are retained as preliminary evidence.

Setup: `100x100x100`, `dx=1 m`, 100 m cube, 366 days requested, `dt=3600 s`,
strict-ocean, `--stop-on-grounding`, float32 3D snapshots every 10 days
(`T`, `phi`, `S_B`). Estimated wall 1.6–1.8 h per full run, ~10 h total;
snapshot volume ~12 MB each, ~37 per run, ~444 MB per run (~2.7 GB total).

Results (final runs ended by the stated stop; partial runs are not annual):

| Source | Year | Days | Mass loss [%] | t50 [d] | Final point | Stop |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| NZ | 2020 | 161 | 60.5 | 121.3 | 76.51N 61.57E | grounded |
| NZ | 2024 | 50 | 30.6 | — | 80.47N 49.66E | strict-ocean |
| SV | 2020 | 11 | 9.7 | — | 76.33N 16.77E | grounded |
| SV | 2024 | 56 | 78.7 | 23.7 | 79.83N 12.36E | strict-ocean |
| FJL | 2020 | 327 | 100.0 | 134.5 | 75.64N 35.50E | melted away |
| FJL | 2024 | 118 | 67.3 | 60.0 | 80.19N 32.01E | strict-ocean |

The corrected drag makes the icebergs reach shallow banks or leave the valid
GLORYS ocean much sooner than the old drift. The runs are therefore
grounding/strict-ocean-limited trajectories, not complete 365-day references;
the maps show the available duration and stop reason. Path lengths are 172 km
(SV 2020) to 2771 km (FJL 2020); net displacements are 159-582 km.

## 3. Figures

Per-run directories are `figures/stage12.17/<SOURCE>_<YEAR>/` and contain:
track colored by day, track colored by melt rate in **m/day** (the previous
12.16 m/s label is corrected), time series (mass, draft/freeboard, melt
components, water T/S, drift/current, wind), 3D T/phi/S_B snapshots, phi/T
evolution GIFs, and a track GIF. `figures/stage12.17/final_summary_map.png`
shows mass loss and t50; `validation_summary.png` combines convergence,
Enderlin scatter/ratio-vs-size, and energy closure. All PNGs are 200-220 dpi;
GIFs are <1 MB each.

## 4. Limitations for the thesis

- Capsize/roll and buoyant rise are not modelled; waves are off.
- Grid convergence remains `p≈0.711` with a `3.75%` 100^3 error.
- Enderlin has Spearman 0.16 and a strong size-dependent ratio; the model gives
  the right mean level but not the between-iceberg spread.
- Drift is not validated against observed tracks; the form/skin coefficients
  are literature values, not calibrated.
- The model removes melt mass without subtracting its sensible enthalpy
  (diagnostic energy closure only).
- Strict-ocean and grounding stops can end a run before 365 days; partial runs
  are reported with their available duration.

## 5. Verification

- Drag test: 9 checks, 0 errors.
- Sensitivity runs: 5/5 completed 30 d.
- Final runs: 6/6 launched sequentially; results and partial-stop flags in §2.
- Strict build RC 0; full `fpm test` 82 STOP 0, 0 failures; docs links 0
  broken; `git diff --check` RC 0.

## 6. Files

- Report: this file.
- Code: `src/iceberg_types.f90`, `src/iceberg_dynamics.f90`,
  `src/voxel_iceberg.f90`, `test/iceberg_test_drift_force_balance.f90`,
  `app/iceberg_run.f90`.
- Scripts: `scripts/stage12.17_final_100cube.sh`,
  `python/analysis/stage12.17_figures.py`,
  `python/analysis/stage12.17_summary.py`.
- Figures: `docs/wiki/stages/stage12/figures/stage12.17/`.
- Evidence: `docs/wiki/stages/stage12/evidence/stage12.17/`.
