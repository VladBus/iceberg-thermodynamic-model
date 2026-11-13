# Stage 12.18 — Final 50 m runs with grounded-in-place melting and thesis figures

**Date:** 2026-11-13  
**Status:** COMPLETED  
**Scope:** produce full lifetime/mass-loss maps for three source regions and two
years, add an opt-in grounded-in-place mode, and correct the 3D/summary figures.
The 12.17 physics (literature form/skin drag, semi-implicit drag) is unchanged;
12.17 documentation/results are preserved except the header status.

## 1. What changed relative to 12.17

| Aspect | 12.17 | 12.18 |
| --- | --- | --- |
| Body / grid | 100 m cube, 100^3 / 1 m | 50 m cube, 50^3 / 1 m |
| Starts | 3 approach points, 1 each/year | 6 coastal points (2 per source), both years |
| Runs | 6 | 12 |
| Grounding | `--stop-on-grounding` | opt-in `--grounded-in-place` |
| Forcing when stranded | strict stop | nearest valid GLORYS cell within 0.5° |
| End of forcing | treated as a stop | normal completion at 365/366 d |
| 3D figures | scatter T/S, no fixed axes | surface voxels + central slices/shell, axes in m |
| Summary map | mass loss + t50 | 2020/2024 panels, mass loss + t99 |
| Lifetimes | 11–327 d partial | 224–366 d; 6 melt-outs, 6 end-of-forcing |

Physics not changed: drag coefficients, semi-implicit drag/Coriolis, thermodynamics,
energy ledger, Enderlin metrics, convergence, and 12.17 results.

## 2. Grounded-in-place mode

`--grounded-in-place` keeps the body at its grounding position, continues
thermodynamics, and takes the ocean profile from the nearest valid GLORYS cell
within 0.5° when the primary point is land/missing. The first grounding and the
selected forcing cell are written to `run.nc_grounded.csv` and printed to the
log. Default remains the old stop-on-grounding/strict-ocean behaviour.

The mode is a documented assumption: it represents a grounded, melting iceberg,
not free drift. It does not move the body or add sea-ice/ground contact physics.

## 3. Final runs

50 m cube, 50^3 voxels at 1 m, 366 days requested, ERA5+GLORYS12 daily,
`--grounded-in-place`, `--strict-ocean`, float32 snapshots every 10 days.
Starts (all depth > draft + 55 m; draft 44.3 m):

| Tag | Source | Point | Depth [m] |
| --- | --- | --- | ---: |
| NZ1 | Novaya Zemlya | 75.5N 57.0E | 115 |
| NZ2 | Novaya Zemlya | 76.5N 58.0E | 122 |
| SV1 | Svalbard east | 76.5N 20.5E | 162 |
| SV2 | Svalbard east | 77.58N 19.0E | 154 |
| FJL1 | Franz Josef Land | 80.9167N 52.0E | 323 |
| FJL2 | Franz Josef Land | 81.0N 55.0E | 105 |

Results (mass loss at end of run; t50/t99 from daily mass):

| Run | Days | Mass loss [%] | t50 [d] | t99 [d] | Stop |
| --- | ---: | ---: | ---: | ---: | --- |
| NZ1 2020 | 282 | 99.9 | 45.3 | 268.8 | melted |
| NZ1 2024 | 366 | 95.8 | 215.5 | — | end of forcing |
| NZ2 2020 | 224 | 99.7 | 174.5 | 220.7 | melted |
| NZ2 2024 | 244 | 99.7 | 196.5 | 238.9 | melted |
| SV1 2020 | 302 | 99.7 | 194.5 | 277.9 | melted |
| SV1 2024 | 329 | 99.9 | 162.9 | 280.3 | melted |
| SV2 2020 | 366 | 88.3 | 214.4 | — | end of forcing |
| SV2 2024 | 269 | 99.7 | 210.8 | 266.7 | melted |
| FJL1 2020 | 366 | 91.6 | 210.5 | — | end of forcing |
| FJL1 2024 | 366 | 91.2 | 236.6 | — | end of forcing |
| FJL2 2020 | 366 | 96.5 | 192.1 | — | end of forcing |
| FJL2 2024 | 366 | 84.6 | 235.4 | — | end of forcing |

## 4. Figure fixes

- 3D axes are labelled in metres with fixed full-domain limits on every panel
  and day; no cell-index labels.
- Whole cube is the default; cut-away is a separate row.
- phi uses Blues (darker = more ice), T uses YlOrRd (white/cream cold, red warm),
  S_B uses Greens; one shared colorbar per row.
- T is shown as surface voxels plus central x-z and y-z slices; S_B only on the
  boundary shell. No T/S scatter.
- GIFs use fixed axes, calendar date and remaining-mass percentage in every
  frame; frames are read one snapshot at a time.
- The summary map has separate 2020/2024 panels, start markers and stop-reason
  markers, “mass loss by end of run (N d)”, and t99.

## 5. Limitations for the thesis

- No capsize/roll and no buoyant rise; waves are off.
- Grid convergence remains `p=0.711` with a `3.75%` 100^3 error; 12.18 uses a
  50 m body on 50^3, not the 100^3 reference.
- Enderlin: Spearman 0.16 and a strong size-dependent ratio; the model gives the
  mean level but not the between-iceberg spread.
- Drift is not validated against observed tracks. Grounded-in-place is an
  assumption, and the NZ/SV start points are approximations away from the coast.
- Mass loss and lifetimes are offline, one-way, and not calibrated.
- The in-place forcing cell can be up to 0.5° away; the run may stop when no
  valid cell is found within that radius.

## 6. Verification

- Strict `fpm build`: RC 0.
- `fpm test`: 82 STOP 0, 0 failures; drift test 9/9.
- `check_docs_links`: 0 broken; `git diff --check`: RC 0.
- Data/NetCDF/snapshots remain under `data/validation/stage12.18/` and are not
  committed.

## 7. Files

- Code: `app/iceberg_run.f90` (`--grounded-in-place`, grounded CSV, `grounded`
  variable, snapshot mass), `python/analysis/stage12.17_figures.py`,
  `python/analysis/stage12.18_summary.py`, `scripts/stage12.18_final_50m.sh`.
- Figures: `docs/wiki/stages/stage12/figures/stage12.18/`.
- Evidence: `docs/wiki/stages/stage12/evidence/stage12.18/`.
