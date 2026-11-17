# Stage 12.20 — phi_conn, final 100³ references and thesis figures

**Date:** 2026-11-16
**Status:** CLOSED 2026-11-17 after final cosmetic pass; documented limitations remain
**Scope:** connectivity threshold, six final coastal 100³ 2020/2024 references at
identical start points in both years, with 10-day snapshots, figures, Svalbard
negative result and thesis limitations.

## 1. Physics decisions

- `VOXEL_PHI_CONN=0.3` is the default; six-face connectivity uses
  `phi >= 0.3`. The largest component is the main body; other high-phi
  components are calved.
- No support/overhang criterion is added. FJL2 2024's top plate is connected
  through `phi≈1` cells (one component at `phi_conn=0.99`), i.e. a real
  horizontal overhang, not a 1 % bridge. No defensible bending parameters are
  available, so the plate is a known limitation.
- t50 and t90 are primary lifetime metrics; t99 is reported with the overhang
  caveat. W/H and Weeks–Mellor are removed from figures; capsize is not
  evaluated.

## 2. Connectivity scan

| Case | Detached at 0.3 | First detached day |
| --- | ---: | ---: |
| FJL1 2020 | 1.82 Mt (17.7 %) | 330 |
| FJL2 2020 | none | — |
| FJL2 2024 | none | — |

The 100³ Stage 4 runs had only 2–3 `run.nc_voxel.nc` frames; they were rerun
with `run.nc_snap_*.nc` every 10 d for the final figures.

## 3. 50 m controls with phi_conn=0.3

| Case | t50 | t90 | t99 | Final mass | Calved | Energy final / max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FJL2 2020 | 193.06 | 257.50 | 316.75 | 0.558 % | 4.179 Mt | 0.0284 % / 0.514 % |
| FJL2 2024 | 236.38 | — | — | 15.377 % | 0 | −0.052 % / 0.654 % |

FJL2 2024 is unchanged from 12.19; FJL2 2020 changed only in the tail. The
FJL_A 50³/dx=2 m calibration differed from 100³ by ~16 km and 0.73 pp after
30 d; this is sufficient for start screening but final runs are 100³.

## 4. Start selection and Svalbard

Offline drift was rejected as a grounding screen: SV 2020 (76.4167N 21.75E)
and FJL 2024 (82.5N 53.5E) grounded after 175/241 s despite GLORYS depths
232.8/226.1 m, because the model uses IBCAO and the 88 m draft.

A 24-candidate 50³/dx=2 m 30-day screen found FJL/NZ survivors. **No valid
Svalbard start exists within 5–25E and the 1.5 h budget:** 76.4N/20.5E and
76.5N/22.4E grounded; 79N/10E and 80N/10E were strict-ocean. This is a result,
not substituted by central-Barents or grounded-in-place.

## 5. Final 100³ runs

All runs: 100³/1 m, free drift, `--strict-ocean --stop-on-grounding`, no
grounded-in-place, `VOXEL_PHI_CONN=0.3`, `VOXEL_CONNECTIVITY_HOURS=6`, snapshots
every 10 d.

| Set | Name | Source | Year | Start | Days | Mass loss | t50 | t90 | t99 | Calved | Path km | Stop / replacement |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| coastal | FJL_A_2020 | FJL | 2020 | 80.5N 45E | 323.8 | 99.999% | 135.5 | 224.2 | 285.9 | 0.104 Mt | 2772 | melted |
| coastal | NZ_A_2020 | NZ | 2020 | 75N 53.583E | 63.1 | 54.65% | 46.8 | — | — | 0 | 1173 | strict ocean |
| coastal | NZ_B_2020 | NZ | 2020 | 78N 55E | 161.0 | 60.53% | 122.2 | — | — | 0 | 1828 | grounded |
| coastal | FJL_A_2024 | FJL | 2024 | 80.5N 45E | 117.5 | 67.32% | 61.0 | — | — | 0 | 1351 | strict ocean |
| coastal | NZ_A_2024 | NZ | 2024 | 75N 53.583E | 197.1 | 87.24% | 32.9 | — | — | 0 | 2086 | grounded |
| coastal | NZ_B_2024 | NZ | 2024 | 78N 55E | 49.8 | 30.63% | — | — | — | 0 | 769 | strict ocean |


All three points are now identical in both years: FJL 80.5N 45E, NZ-A
75N 53.583E and NZ-B 78N 55E. The 2020 NZ-A was rerun at the 2024 NZ-A point
(63.1 d, strict stop); the 2024 NZ-B is the same 78N 55E point as 2020 (49.8 d,
strict stop). No Kara point and no year-specific replacement remain. Six
auxiliary Barents open-water runs (Barents-1/2/3 x 2020/2024) were explored but
are deliberately excluded from this final coastal set: they do not answer the
coastal reference question and would mix two populations in one map.

## 6. Figures

`figures/stage12.20/final/<run>/` contains `snapshots_3d.png`, `profiles.png`
with `T(z)` and `phi(z)` at five actual snapshot dates, `time_series.png`,
`track.png`, and `evolution_phi.gif`/`evolution_T.gif` (400 ms frames, 1500 ms
last frame, fixed size/colorbars). The full-width mid-depth `T(x)` transect is
omitted: with `kappa ~ 1.1e-6 m2/s` the one-year thermal skin is only ~6 m, so a
100 m transect is visually empty in the interior; `T(z)`/`phi(z)` carry the
useful profile information. Profiles use oceanographic depth (0 m at the top,
increasing downward) and the observed `T` range `0…−30 °C`; the old `−12 °C`
limit was clipping cold ice. `time_series.png` uses Russian labels and separate
red/blue axes for water `T` and `S` at draft. Common `map_2020_2024.png`, `mass_curves.png` and
`summary.csv` contain only the six coastal 100³ runs. The two 50 m controls are
kept out of those mixed figures and are summarised separately in
`controls_50m.png`; their per-run figures remain in `CTRL_FJL2_2020/` and
`CTRL_FJL2_2024/`. GIFs use `run.nc_snap_*.nc`.

## 7. Limitations for the thesis

No capsize/roll; no solar radiation; waves off; no sea ice; no support/overhang
or calving mechanics beyond disconnected high-phi components; detached pieces
are not tracked (lifetime is the main body). The final free-drift set uses
terminal grounding/strict-ocean stops. `--grounded-in-place` exists but is a
separate stranded-melt sensitivity: it holds the body at the grounding site,
continues thermodynamics and may refloat after melt, but does not resolve contact
mechanics and is not part of the paired free-drift set. Drift is not observationally
validated. 100³ resolution remains unresolved (`p=0.711`, 3.75% error against
the Richardson limit). Enderlin current-code median ratio 0.540, Spearman 0.16
with a size trend; start selection was done in the model because offline drift
uses 0.5 m currents, not the 88 m draft. No Svalbard 100³ reference exists.

## 8. Verification

Strict build RC 0; `fpm test` RC 0 (`STOP 0`), drift 9/9; layout checks in
`python/tests/test_stage12_20_figures.py` 3/3; docs links 286 checked,
0 broken; `git diff --check` clean. The eight T GIFs (six coastal plus two controls) have fixed 580x520 frames,
>=5 frames and non-empty warm-colour pixels; the six-row summary excludes the
two 50 m controls. Data are under `data/validation/stage12.20/` and not in git.

## Appendix A — raw diagnostics (2026-11-16)

### A1. T(x) from raw snapshots

CTRL_FJL2_2020 day 30, x=0..15, y=mid, z=mid:
`[-1.633, -4.211, -7.910, -9.137, -9.635, -9.851, -9.945, -9.981, -9.994, -9.998, -10, -10, -10, -10, -10, -10]`.
The 10–15 m core is −10 ± 0.0004 °C, inside the required ±0.05. NZ_B_2024 day 30 has the same core. Raw T never falls below the initial −10 °C at the boundary. The −12…−15 values seen in `profiles.png` are therefore a plotting/aggregation bug, not a model defect: use only columns with `phi > phi_min`, no low-phi water columns.

### A2. Draft/freeboard vs visible main body

CTRL_FJL2_2020 is grounded (`grounded=1`) at all four times.

| Day | h(phi>0.01) | h(phi>0.3) | draft | freeboard | draft+free | ratio |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 230 | 45 | 40 | 24.03 | 20.97 | 45.0 | 0.534 |
| 260 | 38 | 37 | 25.14 | 12.86 | 38.0 | 0.662 |
| 280 | 36 | 19 | 9.21 | 26.79 | 36.0 | 0.256 |
| 350 | 34 | 17 | 10.52 | 23.48 | 34.0 | 0.310 |

`draft+freeboard` equals the height at `phi>0.01`, not the high-phi visible core. The waterline uses all remaining solid cells, so low-phi fringe is counted as main body; the ratio is not hydrostatic because the body is grounded. No floating-body waterline defect is demonstrated by these numbers. Figures must not compare the high-phi silhouette with draft/freeboard without noting the low-phi fringe and grounding.

### A3. Stop causes

| Case | Stop position | GLORYS depth at nearest cell | Nearest valid cell | Cause |
| --- | --- | ---: | ---: | --- |
| NZ_A 2020 | 76.9998N 68.4625E | 47.6 m | 0 km | no primary ocean profile; strict stop |
| NZ_B 2020 | 76.511N 61.572E | 103.9 m | 0 km | IBCAO bank; grounded |
| FJL_A 2024 | 80.191N 32.010E | 7.0 m | 0 km | shallow bank, not data boundary (GLORYS lat 63–86, lon 5–80) |
| NZ_A 2024 | 74.873N 55.784E | 88.2 m | 0 km | depth ≈ draft; grounded |
| NZ_B 2024 | 80.4659N 49.6589E | 71.0 m | 0 km | no primary ocean profile; strict stop |

### A4. NZ_A 2024 first 40 days

Mean water T at draft 0.788 °C (range −1.04…2.25 °C); mean drift speed 0.098 m/s (max 0.684 m/s). Cumulative losses: basal 119.9 Mt, lateral 397.1 Mt, flush 4.6 Mt. Lateral melt dominates (~76%); the 56% loss is consistent with warm water plus fast drift, not a numerical artefact.

## Appendix B — Barents open-water auxiliary runs

These six 100³ runs were exploratory open-water checks, not part of the final
coastal six. They are retained as a separate result table because they show the
complete melt-out cycle; their figures were removed from `final/`. Data remain
local under `data/validation/stage12.20/barents/`, not in git.

| Case | Days | Mass loss | t50 | t90 | t99 | Path km | Stop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Barents_1_2020 | 135.6 | 99.999% | 30.8 | 67.6 | 94.9 | 1976 | melted |
| Barents_2_2020 | 136.1 | 99.999% | 40.6 | 74.7 | 101.3 | 1849 | melted |
| Barents_3_2020 | 187.0 | 99.999% | 43.6 | 119.7 | 168.1 | 2155 | melted |
| Barents_1_2024 | 205.4 | 99.999% | 27.8 | 108.2 | 175.4 | 2130 | melted |
| Barents_2_2024 | 197.4 | 99.999% | 36.7 | 123.8 | 161.0 | 2215 | melted |
| Barents_3_2024 | 365.0 | 99.999% | 34.7 | 126.8 | 188.1 | 2122 | end of forcing |

## Appendix C — track speed audit (12.21b)

The lower `track.png` panel now derives iceberg speed from adjacent daily
positions and elapsed time.  FJL_A_2020 gives a mean of `0.0997 m s⁻¹`, matching
the 2771.7 km / 323.8 d path.  Maximum daily displacement and any >100 km/day
intervals are listed in `figures/stage12.20/final/track_speed_summary.csv` and
the per-run `track_speed_audit.csv`.  All eight runs have maximum daily
displacement below 100 km/day, so no gap-induced line break was required.

## Appendix D — track/map cosmetic pass (12.20c)

Removed all inline isobath `clabel` calls from the track and summary maps; the
white-framed/cropped contour-label artifact is therefore absent. Both maps now
use a frame-free `Line2D`/`Patch` key (shoal fill, dashed 100 m, solid 500 m),
with no white key box; the track key is in the upper-left and the 100 km scale
bar remains lower-right. Shoal water (`depth < 100 m`) is a light grey-brown
fill keyed as `depth < 100 m (shoal; iceberg draft ≈ 88 m)`; the 100 m line is
thin dashed and the 500 m line solid. The bathymetric fill was removed from both
maps because a separate depth colorbar could not fit without crowding; the
white background and isobaths are retained. For FJL_A_2020 the final speed
sample (`mass = 0.0012%`, day 323.8) is omitted from the speed panel because it
is a residual-mass spike, not a physical drift speed; the track itself is kept.
