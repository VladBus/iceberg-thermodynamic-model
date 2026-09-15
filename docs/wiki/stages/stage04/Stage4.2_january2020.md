# Stage 4.2 — January 2020 ERA5 Integration + Python Analysis Workflow

## Overview

**Status:** COMPLETED

Full-month January 2020 ERA5 integration on the TEST grid with a Python
data-acquisition / analysis / visualization pipeline.

**Constraint honored:** Stage 3.5 (real grid) remains DEFERRED. All physics,
EOS, convective adjustment algorithm, FCT anti-diffusion, and grid geometry
are UNCHANGED. `kl1=0` (HEAT off) preserved.

### Inputs

- **ERA5:** full January 2020, **hourly** (744 time steps), area 66–82°N /
  30–63°E (`data/input/raw/era5/era5_2020_01.nc`, 41.1 MB)
- **Fields:** `u10`, `v10`, `t2m`, `msl` (native ERA5 units: m/s, K, Pa)
- **Grid:** `grid_mode=TEST` — synthetic flat basin. NOT a production ocean.
- **HEAT:** NOT enabled (`kl1=0`).

### Run

- **Duration:** 30 model days (auto-limited to `(era5_ntime-1)/nperday`
  = `(744-1)/24` = 30 days).
- **Command:** `fpm run --flag "-I/usr/include"` and strict
  `-fcheck=all -ffpe-trap=invalid,zero,overflow` — both clean.
- **Model day indexing:** `mm1 = min(60, 30) = 30`, `nday1==42` exit never hit.
- **Daily output:** `results_day_01.nc` … `results_day_30.nc` (per-day NetCDF
  snapshots, now including the `density` (RO) variable), plus
  `results_day_00.nc` (initial) and `results_day_final.nc` (final state).
  The previous hardcoded `results_day_05.nc` final write was renamed to
  `results_day_final.nc` so the day-5 daily snapshot is preserved.
- **Daily diagnostics:** `data/output/daily_diagnostics.csv` — one row per day:
  U/V/W/T/S/RO min/max/mean, wind max, tau_x/y min/max, dp_x/dp_y min/max,
  kinetic energy EUU, convective adjustment counters.

## EUU Analysis (Day 1 = 0 mystery — RESOLVED)

**Root cause: print-timing artifact, not a physics bug.**

In `main.f90` the line

```fortran
print *, "Day:", kkk, " Month:", lll, " Kin.Energy(EUU)=", euu
```

executes at the **START** of each model day, **before** the day's dynamics run,
and is immediately followed by `euu = 0.0`. `euu` accumulates squared
barotropic transport during the day inside `shal()` (`euu = euu + uup*uup`,
`shallow_water.f90:216,298`).

Therefore:

- the value printed for **Day kkk is actually the accumulation from Day kkk−1**;
- **Day 1 prints 0** because nothing has been accumulated yet;
- the Stage 4.1 value printed as "Day 2 EUU = 9.618e15" is really **Day 1's**
  kinetic energy.

The new daily diagnostics read `euu` at the **end** of each day, so
`daily_diagnostics.csv` reports the correct same-day EUU
(e.g. Day 1 EUU = 9.6181e15 — exactly the value the old print attributed to
Day 2). No formula changed; this is a reporting-order clarification.

### EUU monthly behavior (January 2020, TEST grid)

| Quantity | Value                     |
| -------- | ------------------------- |
| EUU min  | 9.6181e15 cm²/s² (day 1)  |
| EUU max  | 3.0435e17 cm²/s² (day 28) |
| EUU mean | 1.6430e17 cm²/s²          |

EUU grows steadily from day 1 (~1e16) to days 20–28 (~3e17) as barotropic
circulation spins up under ERA5 wind forcing; it is a sum over grid of
squared barotropic transports, NOT physical kinetic energy.

## Physical Diagnostics (TEST grid, kl1=0, January 2020)

| Variable    | min                      | max     | Notes                                  |
| ----------- | ------------------------ | ------- | -------------------------------------- |
| U (cm/s)    | −40.7                    | +36.1   | blocks 200/210/280                     |
| V (cm/s)    | −38.4                    | +34.1   |                                        |
| W (cm/s)    | −8.1e-2                  | +1.1e-1 |                                        |
| T (°C)      | −0.13                    | +25.8   | initial synthetic profile; ocean cools |
| S (mass fr) | 0.03237                  | 0.03502 | 0.033–0.035 band                       |
| RO (g/cm³)  | 1.85e-3                  | 8.16e-3 | Eckart EOS anomaly                     |
| wind max    | 19.07 m/s                |         | from u10/v10                           |
| tau_x       | −8.07 … +7.41 dyn/cm²    |         |                                        |
| tau_y       | −8.18 … +6.45 dyn/cm²    |         |                                        |
| dp_x / dp_y | −1.0e-3 … +1.0e-3 hPa/km |         |                                        |

No FPE / NaN / Inf under strict run. All daily NetCDF files pass the IEEE
and ERA5-fillValue checks in `test/check.f90`.

## Convective Adjustment Monitoring (guard NOT changed)

Per AGENTS constraints the 1000-iteration guard is preserved and the algorithm
is untouched. Monitoring only (counters added in `convective_adjustment.f90`):

| Metric                      | January total |
| --------------------------- | ------------- |
| total nmix                  | 42,513,769    |
| max iterations/day          | 1001          |
| guard hits (total)          | 5,467         |
| affected columns/day (mean) | 39,588        |

Guard hits increase with time (0 on day 1 → 881 on day 30), i.e. mixing
demand grows as the synthetic ocean evolves under ERA5 wind. This confirms the
known cyclic-mixing issue documented in Stage 3.3a — NOT to be fixed here.

## Python Environment

`environment.yml` and `requirements.txt` were reduced to **direct
dependencies only** (no `file:///home/conda/...` build paths, no transitive
freeze). Direct deps: `python=3.12`, `cdsapi`, `xarray`, `netCDF4`, `numpy`,
`pandas`, `matplotlib`. Env: `iceberg-thermodynamic-model`
(`/home/vlad/miniconda3/envs/iceberg-thermodynamic-model`). No venv inside
the repo. CDS credentials remain only in `~/.cdsapirc` (never committed).

## ERA5 Data

- `python/era5/download_era5.py` — CLI downloader (`--year --month --area
--time --output`), defaults January 2020 hourly for the TEST-grid region.
- `python/era5/check_era5.py` — CLI validator (dims, time axis, coverage,
  units, NaN/Inf, physical ranges).
- Downloaded file: `data/input/raw/era5/era5_2020_01.nc` (hourly, 744 steps,
  66–82°N / 30–63°E, validated OK). Raw data are NOT committed.

## Python Analysis

| Script                               | Reads                   | Writes                  |
| ------------------------------------ | ----------------------- | ----------------------- |
| `python/analysis/diagnostics.py`     | `daily_diagnostics.csv` | `daily_summary.csv`     |
| `python/analysis/statistics.py`      | `daily_summary.csv`     | `monthly_summary.txt`   |
| `python/analysis/profiles.py`        | `results_day_XX.nc`     | `vertical_profiles.csv` |
| `python/analysis/generate_report.py` | diag + stats            | `monthly_report.txt`    |
| `python/plotting/plots.py`           | daily NC + CSV          | 6 standardized PNGs     |

Python only reads/aggregates/plots — no EOS, no interpolation, no physics.
RO/density is read from the model output (`density` variable), NOT recomputed.

### Figures (`python/plotting/figures/`)

- `surface_temperature.png`, `surface_salinity.png`, `surface_velocity.png`
  (day 30)
- `daily_energy.png` (EUU vs day)
- `convective_stats.png` (guard hits / affected columns vs day)
- `vertical_profiles.png` (horizontal-mean T/S profiles)

## Tests

| Check                                       | Result                   |
| ------------------------------------------- | ------------------------ |
| `fpm build -Wall -Wextra`                   | ✅ Pass                  |
| `fpm test` (convective 15/15)               | ✅ Pass                  |
| `fpm test` (EOS 7/7)                        | ✅ Pass                  |
| `fpm test` (NetCDF, `results_day_final.nc`) | ✅ Pass                  |
| `fpm run -fcheck=all -ffpe-trap` (30 days)  | ✅ Clean, no FPE/NaN/Inf |
| Python imports + reads (xarray/netCDF4)     | ✅ Pass                  |
| All 31 daily NetCDF files IEEE-clean        | ✅ Pass                  |

## Limitations

- TEST synthetic grid — NOT a real basin; no production claims.
- `grid_mode=real` still requires `KOORD.DAT`/`hhh.bar` (Stage 3.5, DEFERRED).
- HEAT off (`kl1=0`); no d2m/tcc/precip fields.
- Convective adjustment guard hits grow with time — known unresolved cyclic
  mixing on deep columns (documented, not fixed per constraints).
- Month covers 30 model days (ERA5 slice-count limit of the time coupling),
  not 31 calendar days.
- `results_day_05.nc` is now the day-5 daily snapshot; the final state is in
  `results_day_final.nc`.

## Documentation

- `docs/wiki/stages/stage04/Stage4.2_january2020.md` — this report
- `docs/wiki/topics/Python_environment.md` — updated (direct deps)
- `docs/wiki/topics/ERA5_download.md` — updated (CLI usage, hourly file)
- `docs/wiki/ERA5_INTEGRATION_TODO.md` — Stage 4.2 status
- `AGENTS.md` — updated architecture/commands/validation table

## Git

Small logical commits (see commit log):

1. Python environment cleanup + ERA5 workflow CLI
2. Fortran January run + daily diagnostics + convective counters
3. Python analysis modules
4. Python plotting
5. Documentation + report

---

**Stage 4.2 complete:** 30-day January 2020 ERA5 run on the TEST grid with
clean strict validation, EUU Day-1 mystery resolved, per-day NetCDF + CSV
diagnostics, and a full Python analysis/plotting/report pipeline. Real grid
(Stage 3.5) and HEAT remain DEFERRED.
