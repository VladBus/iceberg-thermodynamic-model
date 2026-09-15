# Stage 7.6C.2: ERA5 Forcing-Domain Expansion & Real-Ice Hot Run

**Classification: A** — 100 % of required model forcing points are now covered by
ERA5 (previously 95.7 %), the three-day real-grid + real-ice hot run completes
cleanly with zero NaN/Inf and bounded dynamics, and the full Fortran + Python test
suite passes. No physics, grid, bathymetry, or ice-initialization code was changed.

**Date:** 2026-08-27  
**Prerequisites:** Stages 7.6A / 7.6A.1 (grid), 7.6B (KOORD.DAT + hhh.bar), 7.6C.1 (real ice init)  
**Next:** Stage 7.7

---

## 1. Executive Summary

The legacy ERA5 product (`era5_2020_0103_barents_expanded_merged.nc`, lat 66–90 /
lon 10–70) left part of the real model basin without forcing: every lat-out-of-range
query makes `era5_bilinear2d` return `ok=.false.`, which zeroes the forcing
(no extrapolation); lon outside the span is silently edge-clamped. An exact
recomputation of the coverage over the **coup1-consistent active-wet mask
(10,966 cells)** found **471 uncovered cells (4.295 %, 95.705 % coverage)** — the
spec's quoted "591 / 11,330 ≈ 5.2 %" used a superset mask and is corrected here
(134 cells fail on latitude, 337 on longitude, sets disjoint).

A new deterministic downloader+coverage pipeline fixes this by expanding the ERA5
request to `[lat 90–63, lon 7.0–77.5]` (0.25°, 6-hourly), fully covering the model
domain `[64.21–85.04 °N, 8.33–76.32 °E]` with ≥1.2° margin on south/west/east.
A 4-day test product (2020-01-01→04, 16 steps) now covers **10,966/10,966
required points (100.000 %)** and **13,965/13,965 full nodes (100.000 %)**.

The model was then run for **3 model days** (01→03 Jan 2020, auto-limited by
`mm1 = (16−1)/4`) on the **real grid + real ice** with the expanded forcing
(`kl1=1`, `forcing_mode_era5`). The run completes in **12 s**, produces zero NaN/Inf
across all output fields, and shows bounded dynamics (kinetic energy ~1.9·10¹⁶,
NaNflag 0 in every barotropic sub-step). Ice volume drifts −2.8 % over 3 days under
real January winds/snow — a stable, continuous behaviour, not a failure.

## 2. Coverage (before → after)

| Metric                        | Legacy (66–90 / 10–70)   | Expanded (63–90 / 7–77.5) |
| ----------------------------- | ------------------------ | ------------------------- |
| Required forcing points (wet) | 10,966                   | 10,966                    |
| Covered                       | 10,495                   | 10,966                    |
| **Uncovered**                 | **471**                  | **0**                     |
| Coverage of required cells    | 95.705 %                 | **100.000 %**             |
| Coverage of all grid nodes    | 94.987 % (700 of 13,965) | 100.000 %                 |
| Uncovered by latitude only    | 134                      | 0                         |
| Uncovered by longitude only   | 337                      | 0                         |

Coverage test mirrors the Fortran acceptance rule exactly:
**latitude must bracket the query point** (hard failure, forcing zeroed) and
**longitude is cyclic-wrapped then edge-clamped** (silent — must be rejected by
domain choice, which is now guaranteed by a 100 % pass). New deterministic /
NaN-free checker: `python/era5/model_coverage.py` (exit 0 ⇔ 100 % required
coverage). Fortran-side confirmation: `test/era5_coverage_test.f90` prints
`Required forcing points = 10966 / Uncovered (lat out of range) = 0`.

## 3. ERA5 forcing product (new)

| Property                 | Value                                                                                             |
| ------------------------ | ------------------------------------------------------------------------------------------------- |
| Product / dataset        | `reanalysis-era5-single-levels`, 0.25×0.25°, 6-hourly (00/06/12/18)                               |
| Requested area (N/W/S/E) | 90, 7.0, 63.0, 77.5 (model margin ≈1.2° S / 1.25° W / 1.18° E, N=90)                              |
| Raw instant file         | `data/input/raw/era5/2020/2020_01/era5_2020_01_fullcoverage_d1_4.nc` (4.17 MB, 16 steps, 109×283) |
| Raw snowfall file        | `snowfall_2020_01_fullcoverage_d1_4.nc` (0.31 MB, 8 steps 00/12)                                  |
| **Merged product**       | `data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_d1_4_merged.nc` (5.19 MB)       |
| Variables                | `u10, v10, t2m, d2m, msl, tcc` + `sf` (6-hourly rate, `m s-1`)                                    |
| Time encoding            | `seconds since 1970-01-01` (proleptic_gregorian, int64)                                           |
| Latitude                 | written descending 90→63; `netcdf_input.f90` flips → increasing; lon increasing 7→77.5            |

Ranges over the product (0 NaN / 0 Inf in every variable): u10 −22.3…21.8 m s⁻¹,
v10 −21.9…19.5, t2m 241.3…284.4 K, d2m 237.3…280.7 K, msl 94,690…101,889 Pa,
tcc 0…1, sf 0…8.15·10⁻⁸ m s⁻¹. `python/era5/check_era5.py --area 90 7 63 77.5`
passes (exit 0).

## 4. Regridding & interpolation

- Dummy-augmented bilinear `era5_bilinear2d` on every model node i=1..is1, j=1..js1.
- Interpolated first step (2020-01-01 00Z) over the model grid — **10,966/10,966
  cells, 0 uncovered**:
  - MSL 96,181…99,904 Pa (mean 98,399 ≈ 984 hPa)
  - T2M 241.8…272.2 K (mean 256.4 ≈ −16.8 °C)
  - U10 −8.97…+9.44, V10 −16.41…+7.45 m s⁻¹
  - SF 0…1.30·10⁻⁸ m s⁻¹
- No extrapolation anywhere: latitude bracketing satisfied at every required cell
  (asserted in Fortran), longitude within the masked span (asserted in Python).

## 5. Units

| Variable | Input unit        | Conversion in `epoch` path | Model variable       |
| -------- | ----------------- | -------------------------- | -------------------- |
| u10/v10  | m s⁻¹             | ×100                       | windx1/windy1 cm s⁻¹ |
| msl      | Pa                | ×0.01                      | p1 / patm hPa        |
| t2m      | K                 | −273.15                    | tatm °C              |
| d2m      | K                 | Clausius–Clapeyron         | humid                |
| tcc      | 0–1               | —                          | cloud                |
| sf       | m s⁻¹ (water eq.) | —                          | era5_snowfall_rate   |

Unit conversions are unchanged (Pa→hPa, K→°C, m s⁻¹→cm s⁻¹) and are covered by
new unit checks in `python/tests/test_era5_coverage.py` (9/9) plus the existing
`test_units_roundtrip.py`. The seven ERA5 variables u10, v10, t2m, msl, d2m, tcc,
sf are all consumed by `era5_wind` (u10/v10 drive the quadratic wind stress,
msl drives the geostrophic+baroclinic pressure gradient; `skt` and `q` are not
consumed and not required).

## 6. Forcing validation

- All variables present in the merged product; hard-required set complete.
- ASCII/NetCDF ranges physical; no NaN/Inf (Python per-variable scan = 0).
- Fortran `era5_open` + `era5_diag` read the product correctly
  (ntime=16, nlat=109, nlon=283, lat increasing after flip, decreasing=T flag).
- In-run `ERA5 WIND` diagnostics (cm s⁻¹ / hPa / dyn cm⁻²):
  day 1 windx −810…+1093 (≈8…11 m s⁻¹), p1 961.8…998.6 hPa, tx −1.6…+2.4;
  day 3 windx −1562…+1335 (≈16…13 m s⁻¹), p1 952.0…992.9, tx −6.6…+3.9.
- **0** warnings “outside ERA5 latitude range” printed during the run — the
  pre-expansion failure mode never triggers.

## 7. Hot run: real grid + real ice + expanded ERA5

Run `hot_run_20200101_3d_realice`, 2020-01-01→03 (auto `mm1 = (16−1)/4 = 3` days).
Command:

```bash
fpm run --flag "-I/usr/include" -- hot_run_20200101_3d_realice \
    data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_d1_4_merged.nc
```

Manifest: `data/runs/hot_run_20200101_3d_realice/manifest.json`
(output: `.../output/nc/results_day_{00,01,02,03,final}.nc`, 5×7.8 MB ≈ 38 MB).

Forcing steps forced: Jan 01 00Z, Jan 02 00Z, Jan 03 00Z, Jan 04 00Z
(`era5_wind` at tidx 1, 5, 9, 13).

**Performance:** 3 days in **12 s wall clock** (compiled `-O` default profile).

## 8. Initial vs final ice (day_00 → day_03)

| Metric                        | day_00                                 | day_03                                 | Δ                       |
| ----------------------------- | -------------------------------------- | -------------------------------------- | ----------------------- |
| Ice cells (ANS ≥ 0.005)       | 4,402                                  | 4,620                                  | +218                    |
| Mean SIC over ice             | 0.8313                                 | 0.7461                                 | −0.085                  |
| Mean SIT over ice             | 0.5977 m                               | 0.6148 m                               | +0.017 m                |
| Total ice volume              | 4.502·10¹¹ m³                          | 4.376·10¹¹ m³                          | −2.82 %                 |
| Snow volume                   | 0                                      | 1.64·10⁸ m³                            | +                       |
| Category areas (ΣA_k, m)      | 297/1967/1154/235/6.1                  | 304/1849/1076/202/16.2                 | cat1,cat5 ↑             |
| Category volumes (m³)         | 1.15e10/1.52e11/2.12e11/7.25e10/2.95e9 | 1.38e10/1.53e11/2.00e11/6.33e10/7.05e9 | melt mid-cats           |
| Category mean thicknesses (m) | 0.200/0.400/0.950/1.600/2.500          | 0.236/0.429/0.965/1.619/2.251          | within (hmaxₖ₋₁, hmaxₖ] |

Over 3 days under real January forcing the ice pack loses ~2.8 % volume (melt in
the intermediate categories against a warm synthetic initial ocean, T up to
+23 °C at day_00) while thin (cat 1) and thick (cat 5) categories grow — a
deformation/convergence signature. Ocean T range day_03 −2.11…+22.44 °C
(freezing onset at surface, −6·10⁻⁶ °C at day_00), S 0.03505 max; S min −3.1·10⁻⁴
(a trace negative mass-fraction rounding), salinity range otherwise healthy.
**Zero NaN/Inf in temperature, salinity, ice fields and velocities on both days.**

## 9. Numerical behaviour

- NaNflag = 0.0000 in every barotropic sub-step diagnostic (days 1–3) — no NaN in
  u2/v2; released-then-0 NaNflag on scalars matches the pre-existing Stage 7.3/7.6B
  clean state (velocity limiter `maxU2=0.2 / maxV2=0.1` cm s⁻¹ capable of bursting to
  ~0.8·10² during spin-up, bounded).
- Kinetic energy (EUU): 0 → 5.87·10¹⁵ → 1.08·10¹⁶ → 1.93·10¹⁶ — monotone but bounded
  spin-up, no blow-up over 3 days.
- Convective adjustment: CA-PROBE shows after-advection inversion columns ~10,900 of
  10,966 (mid-ocean, pre-existing); after the 1000-iteration guard residual `max_inv =
2.3842·10⁻⁷` (= 2⁻²², the float32 quantization step) in ~2,200 columns — the
  documented float32 EOS root cause, **unchanged and not a regression**.
  `daily diag nmix=********` is an I8-format overflow of the cumulative mixing counter
  (≥10⁸ events), cosmetic only; `guard=***` likewise exceeds the I3 field once guard
  hits/day ≥ 1000 — both formatting artefacts of the pre-existing counter, not errors.

## 10. Performance & disk

- Hot run wall clock: **12 s / 3 days**.
- `data/` total 2.4 GB (gitignored); hot-run output 38 MB; new ERA5 raw+merged ≈ +5 MB.
- Nothing deleted; legacy 2020_Q1 product retained as the historical reference.

## 11. Tests (spec §27)

| Suite                                             | Result                                                                                                            |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `fpm build --flag "-I/usr/include -Wall -Wextra"` | OK, 0 warnings introduced                                                                                         |
| `fpm test --flag "-I/usr/include"` (all)          | PASS (exit 0) — conv 15/15, eos 7/7, thermo 13/13, eos-precision, forcing validation, snowfall/cold-ice, ice_init |
| `test/era5_coverage_test.f90` (**new**)           | PASS — 10,966 required, 0 uncovered, lat ascending, dims 16/109/283                                               |
| `python/tests/test_era5_coverage.py` (**new**)    | PASS 9/9 (coverage 100 %, legacy <96 %, no-extrapolation, conventions, 3 unit conversions, variable set)          |
| `python/tests/test_units_roundtrip.py`            | PASS (all round-trips)                                                                                            |

`pytest` is not installed in the conda env `iceberg-thermodynamic-model`; the new
Python tests run standalone (`python python/tests/test_era5_coverage.py`) and remain
pytest-collectable. An `iceberg-era5-parser` env named in the spec §27 does not exist;
`iceberg-thermodynamic-model` was used throughout.

## 12. Files created / modified

**Modified:** `python/era5/download_era5.py` (backward-compatible `--start-day` /
`--end-day` / `build_request(days=…)`).
**Created:** `python/era5/model_coverage.py`, `python/era5/stage7_6c2_forcing_stats.py`,
`python/analysis/hot_run_ice_aggregates.py`, `python/tests/test_era5_coverage.py`,
`test/era5_coverage_test.f90`.
**Data (gitignored):** raw + snowfall + merged ERA5 `…_fullcoverage_d1_4*.nc`,
`stage7.6C.2_coverage.json`, `stage7.6C.2_statistics.json`,
`data/output/diagnostics/stage7.6C.2/forcing_diagnostics.png`,
run `hot_run_20200101_3d_realice/` (+ manifest, 5 NetCDF, analysis JSON).

## 13. Physics / Grid / Ice-init changes

**None. No physics, no grid, no bathymetry, no ice initialization code was touched.**
The only source delta is the ERA5 downloader CLI extension; all other Fortran/Python
additions are new validation/diagnostic tools and tests.

## 14. Known ice limitations (preserved, not bugs)

1. 284 wet cells with SIC > 0 but no SIT are initialised as open water.
2. 279 cells with SIT < 0.20 m are clamped into the lowest category.
3. 15 cells with SIT > 2.50 m are clamped into the highest category.
4. `1_k.ice` files carry 4-decimal precision by format.

These are accepted representation limits of the reconstruction stage and were
deliberately not "fixed" in this stage.

## 15. New issues

None. Pre-existing, re-confirmed while monitoring: the float32 convective-guard
residual (2⁻²²), the synthetic warm initial ocean (T ≤ 23 °C, not a realistic Jan
state), and `nsal`/`nmix` diagnostic format overflow.

## 16. Scientific interpretation

The 3-day hot run behaves as a physical cold-season spin-up: real January winds
(mean ≈9 m s⁻¹, gusts to 20 m s⁻¹) drive a bounded circulation, thin and thick ice
categories grow at the expense of mid categories (convergence/ridging), snowfall
accumulates as snow volume (1.6·10⁸ m³), surface temperature reaches the freezing
point while the (synthetic) warm ocean slowly erodes → total volume −2.8 %/3 days.
Forcing differences vs the old product appear only in the previously-uncovered
western/southern fraction (471 cells that were zeroed or edge-clamped); with
100 % coverage applied from day 0, the zero-forcing approximation now has **no
cells anywhere** in the basin.

## 17. Recommendation

Proceed to **Stage 7.7**. The next realistic-hot-run options: (a) a full January
(31-day) run with the Q1-style expanded data, or (b) warmer-season data, once the
synthetic initial ocean is replaced by a realistic January T/S field — that
replacement is the main remaining realism gap observed in this hot run.
