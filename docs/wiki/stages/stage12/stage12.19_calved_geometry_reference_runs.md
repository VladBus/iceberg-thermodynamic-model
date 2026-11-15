# Stage 12.19 — Calved geometry, energy closure, diagnostic maps and 100³ references

**Date:** 2026-11-14  
**Status:** COMPLETE with documented limitations  
**Scope:** remove disconnected/calved voxel pieces from the main body, close the
mass/energy ledger for the 50³ control runs, produce the Stage 2 figure set, add
offline drift/melt diagnostics, and run six 100³ free-drift references.

## 1. What changed

| Part | Change | Result |
| --- | --- | --- |
| 12.19.1 | Six-face connectivity at `phi > phi_min`; largest component is the main body; disconnected parts are removed as calved | `voxel_iceberg_remove_calved`, calved events, main-mask hydrostatics |
| 12.19.2 | Energy residual uses **sensible-only** calved/flush enthalpy plus `L·m_surface`; total calved enthalpy remains an output reservoir | 50³ final residual 0.0195%/0.0166% (N=1h/6h), max 0.514% |
| 12.19.3 | Stage 2 figures: whole-model 3×5 phi matrix, profiles, time series/tracks, GIFs | `figures/stage12.19/` |
| 12.19.4 | Offline drift-only and stationary bulk-melt diagnostics | `stage3_drift_map.png`, `stage3_melt_stationary.png` |
| 12.19.5 | Six 100³ 2020 free-drift references with 60-day screening | `stage4_summary.png`; table below |

No canonical ocean/sea-ice physics, FCT, EOS precision, or the `hht` guard was
changed. The calving treatment is opt-in only when the voxel model is active.

## 2. Calved component and mass closure

`VOXEL_CONNECTIVITY_HOURS` controls the six-face connectivity check (default
1 h; 100³ references used 6 h). At each check, the largest connected solid
component is retained; all other solid components are removed and logged in
`run.nc_calved.csv` and the `calved_*` variables in `run.nc`.

Control case FJL2 2020 (50³, 50 m, N=6 h):

| Quantity | Value |
| --- | ---: |
| Calved mass | 4.286e6 kg |
| Calved events | 2 (3.75 Mt at 229.3 d; 0.54 Mt at 283.9 d) |
| Components at 270/365 d | 1 / 1 |
| Mass-balance residual | −1.29e-8 m0 |
| Max draft jump 239–243 d | 0.0150 m (was 11.1 m) |

The corrected main-body draft/freeboard on day 270 is 25.35/10.65 m; the old
plate-bearing state was 41.07/0.93 m. The mass curves of 12.18 and 12.19 are
**identical until 229.25 d**, the first calving; afterwards the difference is
calved mass plus the changed main-body melt geometry.

## 3. Energy closure

The pre-existing 12.18 365-day residual was already **−3.88%** (FJL2 2020;
FJL2 2024 −4.52%, FJL1 2020 −3.25%). The initial 12.19 run showed +1.33%
because the total calved enthalpy (latent-dominated) was used as a boundary
sink and surface latent heat was omitted. The corrected ledger is:

```text
residual = Q_boundary − Q_melt_sensible
           − [sensible(calved) + sensible(flushed) + L·m_surface]
```

The total calved enthalpy remains in `calved_energy_J` for provenance but is
**not** a boundary heat sink. Corrected results:

| Run | Final residual | Maximum | Status |
| --- | ---: | ---: | --- |
| FJL2 2020, N=1 h | +0.0195% | 0.514% | PASS (diagnostic) |
| FJL2 2020, N=6 h | +0.0166% | 0.514% | PASS (diagnostic) |

The closure is a **diagnostic ledger**, not a state-level energy-conservation
proof; the melt sensible enthalpy is still removed by the state update.

## 4. 12.17 late-plate check

All 12.17 snapshots were scanned at `phi > 0.01` with six-face connectivity.
FJL 2020 has three components only on **day 310** (main 1.01e6 kg; a 0.06e6 kg
lower piece; one isolated cell). Its t50/t99 are 135.2/285.8 d, both before the
plate; the 326-day endpoint tail is affected, but t50/t99 are not. FJL 2024,
NZ 2020/2024 and SV 2020/2024 had no disconnected components or vertical gaps.
12.17 files were not modified.

## 5. Stage 2 figures

- `figures/stage12.19/stage2_matrix_phi.png`: 3 rows (FJL1 2020, FJL2 2020,
  FJL2 2024) × 5 days (0/90/180/270/350), whole model, no cut-away, fixed
  0–50 m axes and one right-hand phi colorbar.
- Per-case `profiles.png`, `time_series.png`, `mass_balance.png`, and
  `evolution_phi.gif`/`evolution_T.gif` under the same directory.
- GIFs: 38 snapshots, 12.5 fps, 0.47–0.69 MB each.
- Profiles are ice-mean `T(z)`, horizontal-mean `phi(z)`, and y-mean `T(x)` at
  the mid-ice level; empty water columns are masked.

## 6. Offline Stage 3 diagnostics

These are **not** no-thermodynamics model runs. Drift is a diagnostic
`0.855·U_GLORYS(0.5 m) + 0.0145·U_ERA5(10 m)` with 6-hour steps; no Coriolis,
waves, sea ice, or thermodynamics. Twenty starts per source (±1.5°, depth
≥200 m, ≥8 cells from land) were used for 2020/2024.

| Year | Source | Mean path km | Median km | Mean speed m/s |
| --- | --- | ---: | ---: | ---: |
| 2020 | FJL | 993 | 377 | 0.159 |
| 2020 | NZ | 1041 | 399 | 0.171 |
| 2020 | SV | 1367 | 768 | 0.194 |
| 2024 | FJL | 1008 | 206 | 0.136 |
| 2024 | NZ | 303 | 170 | 0.228 |
| 2024 | SV | 719 | 434 | 0.167 |

Of 120 trajectories, 96 ended on land/shallow water, 21 on the domain boundary,
and only 3 reached 365 d. The map is in `stage3_drift_map.png`; per-start values
are in `evidence/stage12.19/stage3_drift_summary.csv` and the run CSVs.

Stationary 100 m bulk basal melt (30 d, 92.3 m level, `U_ice=0`) gives median
1.01/0.78 m for 2020 winter/summer and 0.93/0.91 m for 2024; p99 is 24.0/12.5
and 15.7/14.4 m. The shared-scale map is `stage3_melt_stationary.png`; numbers
are in `stage3_melt_seasonal.csv`. This is a bulk diagnostic, not a voxel run.

## 7. Stage 4 100³ free-drift references

The original six 2020 starts from 12.18 were screened for 60 d. Only NZ1 passed;
FJL1/FJL2 left valid ocean at 1.5/14.8 d, NZ2/SV1/SV2 grounded at 5.8/7.8/5.8 d.
The final set therefore uses the nearest verified free-drift starts, recorded in
`stage4_selection.csv`. All six passed the first-60-day check; no
`first_60d_grounded=True` remains.

| Tag | Source | Replaces | Days | Mass loss % | t50 d | t99 d | Path km | Net km | Stop |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| FJL_A | FJL | FJL1/FJL2 | 323.9 | 99.999 | 135.5 | 285.9 | 2773 | 569 | melted |
| NZ_A | NZ | NZ1 | 78.7 | 42.52 | — | — | 1182 | 330 | strict ocean |
| NZ_B | NZ | NZ2 | 161.0 | 60.53 | 122.2 | — | 1828 | 222 | grounded |
| Barents-1 (D2) | Barents | SV1 | 135.6 | 99.999 | 30.8 | 94.9 | 1976 | 540 | melted |
| Barents-2 (D4) | Barents | SV2 | 136.1 | 99.999 | 40.6 | 101.3 | 1849 | 591 | melted |
| Barents-3 (D5) | Barents | — | 187.1 | 99.999 | 43.6 | 168.1 | 2134 | 489 | melted |

All runs used 100³/1 m, 2020 daily GLORYS+ERA5, `--strict-ocean
--stop-on-grounding`, `dt=3600 s`, and no grounded-in-place mode. They are
reference trajectories, not a complete 365-day free-drift set: NZ_A and NZ_B
stop early by the documented controls.

## 8. Verification

- `fpm build` strict flags: RC 0; `fpm test`: 83 `STOP 0`, 0 failures; drift
  9/9; `test_voxel_calved` PASS.
- `check_docs_links.py --all`: 0 broken links; `git diff --check`: RC 0.
- Stage 2 fixed-run mass/energy checks: `evidence/stage12.19/stage2_checks.json`.
- Stage 4 summary: `stage4_summary.csv`; figure `stage4_summary.png`.

## 9. Limitations

- Calved/flushed enthalpy is a diagnostic; the state does not subtract melt
  sensible enthalpy, so this is not state-level energy conservation.
- Connectivity is six-face and grid-timed; thin bridges below one voxel or
  between checks are not resolved. N=6 h is a compromise, not a convergence
  study.
- Stage 2 uses the 50³/50 m diagnostic grid, not the 100³ reference.
- Stage 3 is offline and has no Coriolis/waves/sea-ice/thermodynamics; the
  stationary melt map is a bulk basal formula at a fixed level.
- Stage 4 starts are replacements because five original 2020 starts failed the
  60-day screen; the set is not the original six source/year cases and has no
  observational track validation.
- 100³ resolution remains unresolved (`p=0.711`; 3.75% error versus the
  Richardson limit in 12.14).

## 10. Files

- Code: `src/voxel_iceberg.f90`, `src/iceberg_thermodynamics.f90`,
  `app/iceberg_run.f90`, `test/test_voxel_calved.f90`.
- Analysis: `python/analysis/stage12.19_stage2_figures.py`,
  `stage12.19_stage3_drift.py`, `stage12.19_stage3_melt.py`,
  `stage12.19_stage4_summary.py`.
- Scripts: `scripts/stage12.19_stage2_case.sh`,
  `stage12.19_stage3_drift.py` runner files, `stage12.19_stage4_final.sh`.
- Figures: `figures/stage12.19/`.
- Evidence: `evidence/stage12.19/`.
- Decisions: D-78 (calved main body), D-79 (energy ledger), D-80 (Stage 4
  replacements).
