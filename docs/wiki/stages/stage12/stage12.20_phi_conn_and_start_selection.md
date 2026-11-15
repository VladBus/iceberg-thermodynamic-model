# Stage 12.20 — phi_conn, final 100³ references and thesis figures

**Date:** 2026-11-16
**Status:** COMPLETE with documented limitations
**Scope:** connectivity threshold, final 100³ 2020/2024 references with 10-day
snapshots, figures, Svalbard negative result and thesis limitations.

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

| Name | Source | Year | Start | Days | Mass loss | t50 | t90 | t99 | Calved | Path km | Stop / replacement |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| FJL_A_2020 | FJL | 2020 | 80.5N 45E | 323.8 | 99.999% | 135.5 | 224.2 | 285.9 | 0.104 Mt | 2772 | melted |
| NZ_A_2020 | NZ | 2020 | 75.5N 57E | 78.7 | 42.52% | — | — | — | 0 | 1182 | strict ocean |
| NZ_B_2020 | NZ | 2020 | 78N 55E | 161.0 | 60.53% | 122.2 | — | — | 0 | 1828 | grounded |
| FJL_A_2024 | FJL | 2024 | 80.5N 45E | 117.5 | 67.32% | 61.0 | — | — | 0 | 1351 | strict ocean |
| NZ_A_2024 | NZ | 2024 | 75N 53.583E | 197.1 | 87.24% | 32.9 | — | — | 0 | 2086 | grounded; fallback |
| NZ_B_2024 | NZ | 2024 | 73.083N 59.167E | 38.2 | 84.14% | — | — | — | 0 | 417 | strict ocean; fallback |

NZ_B_2024 stopped before 60 d after two fallbacks; no further substitute was
used. D2/D4/D5 from 12.19 are **Barents-1/Barents-2/Barents-3** in the
documentation: central-Barents open-water extras at ~40E, not Svalbard.

## 6. Figures

`figures/stage12.20/final/<run>/` contains `snapshots_3d.png`, `profiles.png`
(with erf overlay), `time_series.png` with no W/H or track inset, `track.png`,
and `evolution_phi.gif`/`evolution_T.gif` (400 ms frames, 1500 ms last frame,
fixed size/colorbars). Common `map_2020_2024.png`, `mass_curves.png` and
`summary.csv` are at the top level. GIFs use `run.nc_snap_*.nc`.

## 7. Limitations for the thesis

No capsize/roll; no solar radiation; waves off; no sea ice; no support/overhang
or calving mechanics beyond disconnected high-phi components; detached pieces
are not tracked (lifetime is the main body). Drift is not observationally
validated. 100³ resolution remains unresolved (`p=0.711`, 3.75% error against
the Richardson limit). Enderlin current-code median ratio 0.540, Spearman 0.16
with a size trend; start selection was done in the model because offline drift
uses 0.5 m currents, not the 88 m draft. No Svalbard 100³ reference exists.

## 8. Verification

Strict build RC 0; `fpm test` 83 `STOP 0`, drift 9/9; layout checks in
`python/tests/test_stage12_20_figures.py`; docs links and `git diff --check`
checked before the figure commit. Data are under `data/validation/stage12.20/`
and not in git.
