# Stage 6.3 — Deleted Files Report

## Summary

This document records every file deleted during Stage 6.3 source tree cleanup, with reason, replacement, and verification.

## Deleted Files

### 1. Source Code Backups

| Path                                | Size  | Reason                                                                                                                                                                                | Replacement                                                      | Verification                                       |
| ----------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------- |
| `src/convective_adjustment.f90.bak` | 19 KB | Stale backup from pre-Stage 4.2; missing `ca_reset`, `ca_stats`, `ca_probe_inversions`, `ca_log_guard_event`, `ca_probe_inversions` diagnostic infrastructure added in Stages 4.2/4.3 | `src/convective_adjustment.f90` (current, with full diagnostics) | `fpm build/test` PASS; convective diagnostics work |
| `test/experiment_b.f90.bak`         | 7 KB  | Stale backup of experimental REAL64 EOS diagnostic; no corresponding `experiment_b.f90` exists in test/                                                                               | `test/eos_precision_test.f90` (production diagnostic test)       | `fpm test` PASS (eos_precision_test included)      |

### 2. Legacy Python Analysis Scripts (Moved to Archive)

| Path                                 | Size | Reason                                                                                                                                                                       | Replacement                                                                                | Verification                                               |
| ------------------------------------ | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| `python/analysis/diagnostics.py`     | 3 KB | Legacy pipeline; hardcoded `data/output/` paths; replaced by run-aware `seasonal_analysis.py` which produces `seasonal_daily_summary.csv` and `seasonal_monthly_summary.csv` | `python/analysis/seasonal_analysis.py`                                                     | `--run-id 2020_Q1_test_heat_on` produces validated outputs |
| `python/analysis/statistics.py`      | 3 KB | Legacy pipeline; hardcoded `data/output/` paths; replaced by run-aware `seasonal_analysis.py` monthly summaries                                                              | `python/analysis/seasonal_analysis.py`                                                     | `--run-id 2020_Q1_test_heat_on` produces validated outputs |
| `python/analysis/generate_report.py` | 5 KB | Legacy pipeline; hardcoded `data/output/` paths; replaced by run-aware reporting in `seasonal_analysis.py` + `heat_diagnostics.py` + `snowfall_diagnostics.py`               | `python/analysis/seasonal_analysis.py` + `heat_diagnostics.py` + `snowfall_diagnostics.py` | All run-aware scripts produce validated outputs            |

**Note:** These 3 files were not permanently deleted — they were moved to `python/analysis/legacy/` for scientific provenance.

### 3. Generated Plotting Artifacts (25 PNG files)

All files under `python/plotting/figures/` (removed from Git tracking, deleted from filesystem):

| File                                           | Size   | Original Location                     | New Location                         |
| ---------------------------------------------- | ------ | ------------------------------------- | ------------------------------------ |
| `convective/guard_hits_evolution.png`          | 40 KB  | `python/plotting/figures/convective/` | `data/runs/<run_id>/output/figures/` |
| `convective/guard_nmix_kproblem.png`           | 46 KB  | `python/plotting/figures/convective/` | `data/runs/<run_id>/output/figures/` |
| `convective/guard_vs_scalars.png`              | 49 KB  | `python/plotting/figures/convective/` | `data/runs/<run_id>/output/figures/` |
| `convective/representative_profiles.png`       | 182 KB | `python/plotting/figures/convective/` | `data/runs/<run_id>/output/figures/` |
| `convective/residual_inversion.png`            | 33 KB  | `python/plotting/figures/convective/` | `data/runs/<run_id>/output/figures/` |
| `convective_stats.png`                         | 42 KB  | `python/plotting/figures/`            | `data/runs/<run_id>/output/figures/` |
| `daily_energy.png`                             | 51 KB  | `python/plotting/figures/`            | `data/runs/<run_id>/output/figures/` |
| `seasonal/density_time_series.png`             | 47 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/euu_time_series.png`                 | 48 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/heat_fluxes.png`                     | 56 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/salinity_time_series.png`            | 48 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/snowfall_rate.png`                   | 65 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/surface_salinity.png`                | 41 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/surface_temperature.png`             | 48 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/surface_temperature_time_series.png` | 41 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/surface_velocity.png`                | 63 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/temp_100m_time_series.png`           | 40 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/temp_20m_time_series.png`            | 37 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/u_max_time_series.png`               | 54 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/v_max_time_series.png`               | 47 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/vertical_density_profiles.png`       | 78 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/vertical_salinity_profiles.png`      | 76 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/vertical_temp_profiles.png`          | 72 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `seasonal/w_max_time_series.png`               | 59 KB  | `python/plotting/figures/seasonal/`   | `data/runs/<run_id>/output/figures/` |
| `surface_salinity.png`                         | 39 KB  | `python/plotting/figures/`            | `data/runs/<run_id>/output/figures/` |
| `surface_temperature.png`                      | 55 KB  | `python/plotting/figures/`            | `data/runs/<run_id>/output/figures/` |
| `surface_velocity.png`                         | 62 KB  | `python/plotting/figures/`            | `data/runs/<run_id>/output/figures/` |
| `vertical_profiles.png`                        | 197 KB | `python/plotting/figures/`            | `data/runs/<run_id>/output/figures/` |

**Total: 25 files, ~1.6 MB** — all generated scientific figures, now correctly written to per-run output directories.

## Git Commits

| Commit    | Message                                        | Files Affected                                         |
| --------- | ---------------------------------------------- | ------------------------------------------------------ |
| `1e565db` | Stage 6.3: Clean unused source and test files  | 5 files (legacy move, plotting fixes, backup removal)  |
| `54d9b18` | Stage 6.3: Remove generated plotting artifacts | 31 files (25 PNGs + 3 legacy scripts + 3 backup files) |

## Verification

All deletions verified by:

1. **Build**: `fpm build --flag "-I/usr/include -Wall -Wextra"` — PASS
2. **Tests**: `fpm test --flag "-I/usr/include"` — PASS (22 checks + validation suite)
3. **Strict run**: `fpm run --flag "-I/usr/include -fcheck=all -ffpe-trap=invalid,zero,overflow"` — PASS (smoke test, 1 day)
4. **Python validation**: `validate_q1_output.py --run-id 2020_Q1_test_heat_on` — PASS
5. **Run manifest**: `run_manifest.py --run-id 2020_Q1_test_heat_on` — PASS (90 files)
6. **All analysis scripts**: seasonal, heat, snowfall, profiles, convective, eos, precision — PASS
7. **All plotting scripts**: plots, seasonal_plots, convective_plots — PASS (output to run dir)
8. **SI round-trip test**: `test_units_roundtrip.py` — PASS
9. **Python imports**: all active scripts import cleanly

## Risk Assessment

| Deletion              | Risk                                   | Mitigation                                |
| --------------------- | -------------------------------------- | ----------------------------------------- |
| Backup .f90 files     | Low — were stale, not used in build    | Current production modules verified       |
| Legacy Python scripts | Low — moved to `legacy/`, not deleted  | Archived for provenance                   |
| Generated PNGs        | None — regenerated by plotting scripts | Plotting scripts tested, write to run dir |

## Provenance Note

The 3 legacy Python scripts (`diagnostics.py`, `statistics.py`, `generate_report.py`) were **not permanently deleted** — they were moved to `python/analysis/legacy/` to preserve scientific provenance of the analysis pipeline evolution (Stages 4.1–5.5a). They remain accessible for historical reference but are excluded from the active workflow.
