# Stage 6.2 — Barents Research-Domain Configuration

## Purpose

Configure the model's ERA5 forcing for a **Barents Sea / Svalbard / Franz Josef
Land iceberg-source domain** and introduce a **run-based data architecture** for
output isolation, with full project cleanup. No physics changes.

## The Domain

The new research rectangle is the "Barents Sea / Svalbard / Franz Josef Land
iceberg-source domain":

| Item | Value |
|---|---|
| CDS area `[north, west, south, east]` | `[90, 10, 70, 70]` |
| Latitude | 70–90 °N |
| Longitude | 10–70 °E |
| Covers | Barents Sea, Svalbard archipelago, Franz Josef Land, Novaya Zemlya, adjacent Arctic waters |
| Key | `barents` (default in `download_era5.py`) |

The historical Arctic-wide strip (`arctic`, `[90, -180, 65, 180]`) is preserved
for the Q1 2020 datasets and any legacy workflows.

**Important:** the ERA5 domain change does NOT change the model grid. The model
remains `grid_mode=TEST` (synthetic basin, `KOORD.DAT`/`hhh.bar` still missing;
real-grid transition deferred — Stage 3.5/6.1).

## Download

```bash
# Barents domain (new default):
conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py \
    --year 2020 --month 1 --include-snowfall

# Explicit:
conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py \
    --domain barents --year 2020 --month 1 --include-snowfall

# Historical Arctic-wide:
conda run -n iceberg-thermodynamic-model python python/era5/download_era5.py \
    --domain arctic --year 2020 --month 1

# Custom rectangle overrides --domain:
... --area 90 10 70 70 ...
```

Raw output layout (Stage 6.2):

```
data/input/raw/era5/YYYY/YYYY_MM/era5_YYYY_MM.nc
data/input/raw/era5/YYYY/YYYY_MM/snowfall_YYYY_MM.nc
```

## Validation

```bash
# Reports lat/lon coverage and checks against the named domain / CDS area:
python python/era5/check_era5.py                                   # default barents + default file
python python/era5/check_era5.py --domain arctic <file>            # historical datasets
python python/era5/check_era5.py --area 90 10 70 70 <file>         # custom
```

The validator reports `latitude`/`longitude` min/max and prints
`domain coverage: OK` or a `DOMAIN MISMATCH` list (wrap-aware for areas
crossing ±180).

## Merge Snowfall (if downloaded separately)

```bash
conda run -n iceberg-thermodynamic-model python python/era5/merge_snowfall.py \
    data/input/raw/era5/2020/2020_01/era5_2020_01.nc \
    data/input/raw/era5/2020/2020_01/snowfall_2020_01.nc \
    data/input/processed/era5/2020/2020_01/era5_2020_01_merged.nc
```

The Fortran reader expects the merged snowfall variable named `sf` (units
`m s-1`).

## Run-Based Data Architecture

```
data/
  input/raw/era5/YYYY/YYYY_MM/              raw monthly + snowfall
  input/processed/era5/YYYY/YYYY_MM/        merged (sf) per month
  input/processed/era5/2020/2020_Q1/        era5_2020_0103_merged.nc (default input)
  runs/<run_id>/
    manifest.json                           run metadata (see below)
    output/nc/                              results_day_XX.nc, results_day_final.nc
    output/csv/                             daily_diagnostics.csv + analysis CSVs
    output/txt/                             reports
    output/logs/                            run logs
    output/figures/                         PNGs
  archive/{legacy,test,pre_cleanup}/        retired artifacts
  output/                                   EMPTY (never written by new runs)
```

### Manifest contents (per run)

`run_id`, `description`, `start_date`, `end_date`, `expected_days`,
`file_pattern`, `base_dir`, `era5_period`, `era5_domain`, `grid_mode`,
`heat_state`, `snowfall_state`, `model_config`, `git_commit`, `generated_at`,
`status`, and the per-day `files[]` list.

```bash
python python/analysis/run_manifest.py --run-id <run_id>            # generate + validate
python python/analysis/run_manifest.py --run-id <run_id> --validate
```

### Run the model

```bash
fpm run --flag "-I/usr/include" -- <run_id> [era5_file]
# defaults: run_id=2020_Q1_test_heat_on,
#           era5_file=data/input/processed/era5/2020/2020_Q1/era5_2020_0103_merged.nc
```

All outputs go to `data/runs/<run_id>/output/...`; `convective_guard_events.csv`
also goes to the run csv dir.

## Python Run-Aware Analysis

`python/analysis/run_context.py` provides `resolve_run(run_id|manifest)` and
`add_run_args(parser)`. All analysis/plotting scripts accept
`--run-id <run_id>` (or `--manifest <path>`); paths are resolved from the run
context with per-file overrides still available.

```bash
python python/analysis/validate_q1_output.py --run-id 2020_Q1_test_heat_on
python python/analysis/seasonal_analysis.py --run-id 2020_Q1_test_heat_on
python python/plotting/seasonal_plots.py --run-id 2020_Q1_test_heat_on
...
```

**Never** glob `data/output/results_day_*.nc` — use the run manifest/context
(stale-file protection, AGENTS.md §8b).

## SI Round-Trip Unit Test (Stage 6.2 §14)

```bash
python python/tests/test_units_roundtrip.py
# or: python -m pytest python/tests/test_units_roundtrip.py -v
```

Verifies `SI -> presentation -> SI` reproduces originals within float64
tolerance for temperature, velocity, stress, pressure-gradient, pressure,
density-anomaly and salinity conversions.

## Verification Summary

| Check | Result |
|---|---|
| `fpm build -Wall -Wextra` | ✅ |
| `fpm test` (all suites incl. `check` on run dir) | ✅ |
| `fpm run -fcheck=all -ffpe-trap` (1-day smoke, ERA5 active) | ✅ Clean |
| `run_manifest.py` (Q1 90 days + smoke 1 day) | ✅ PASS |
| `validate_q1_output.py` | ✅ PASS |
| All run-aware analysis/plotting scripts | ✅ |
| `check_era5.py` domain coverage | ✅ |
| SI round-trip unit test | ✅ |
| Smoke output NetCDF validation suite | ✅ PASS |

## Constraints Honored

- **No physics changes**: EOS, convective threshold `0.9e-7`, 1000-iteration
  guard, blocks 200/210/280, `shal`, FCT anti-diffusion, `dt`, `DX`, TEST grid —
  untouched.
- `grid_mode=TEST` only; no production claims.
- NetCDF external interface stays canonical SI (Stage 5.5b); conversions only at
  the output boundary; presentation conversions via `units.py`.
- Barents-domain ERA5 has not yet been downloaded (CDS queue pending); the
  downloader/validator/defaults are ready.