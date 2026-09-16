# Stage 10.15 — Operational End-to-End Demonstration

**Classification: Operational demonstration completed (with documented
limitations)**
**Production physics changed: NO**
**Default configuration changed: NO**

This stage demonstrates, with real repository-supported inputs, whether the
model executes end-to-end and produces interpretable outputs. It is **not** a
new physical modernization, **not** calibration, and **not** validation
against observations. The goal is the first honest, reproducible, interpretable
model result and the identification of the actual remaining bottleneck.

| Item | Value |
| ---- | ----- |
| Stage | 10.15 (operational demonstration; no physics change) |
| Branch / HEAD | `main` @ `ca60c62` (Stage 10.14 committed and pushed) |
| Run mode | (1) full-model `fpm run` (Eulerian ocean/sea-ice); (2) Lagrangian iceberg module via `iceberg_test_11_30day_offline` (real forcing, offline) |
| New diagnostics script | `python/analysis/stage10.15_diagnostics.py` |
| Output bundle (gitignored) | `data/output/stage10.15/` |
| ERA5 forcing | `data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc` (364 slices, 6-hourly, real) |
| EN4 ocean | `data/input/processed/ocean/initial_ts_2020-01-01.nc` (real) |
| Grid | IBCAO-derived 133×105 (132×104 active), DX=DY=13.89 km |
| Sea-ice init | OSI-SAF SIC + C3S CS2SMOS SIT → `1_1.ice`–`1_5.ice` (real) |

---

## 1. Scope

Stage 10.15 is:

- an **operational / end-to-end verification**: can the existing model be
  executed with real or repository-supported inputs and produce interpretable
  outputs?
- **not** a new physical modernization;
- **not** calibration (no coefficient was fitted);
- **not** validation against observations (no claim of observational
  agreement is made);
- **not** proof of universal physical correctness.

## 2. Provenance

- Roadmap: `docs/PROJECT_ROADMAP.md` (Stage 10.13/10.14 complete; longer-term
  items listed, none mandatory for this stage).
- Stage 10.14 report: `docs/validation/stage10.14_three_equation_rescoring.md`.
- Modernization plan: `docs/model/stage10_modernization_plan.md`.
- Known issues: `KNOWN_ISSUES.md` (T-12 symlinks; T-06/T-07 drift anomalies;
  N-08; Stage 8 ocean instability family).
- Run instructions: `README.md` (Quick start), `AGENTS.md` (Commands,
  Regeneration).
- Input generation: `python/grid/build_real_grid_inputs.py` (documented in
  `AGENTS.md`); ice init `python/ice/build_initial_ice.py`; ERA5 download
  `python/era5/download_era5.py`.

## 3. Initial state

| Item | Value |
| ---- | ----- |
| Commit before Stage 10.15 | `ca60c62` (Stage 10.14), branch `main` |
| Switches | `basal_melt_scheme = BASAL_MELT_SCHEME_FORCED_CONVECTION` (0); `thermal_evolution_enabled = .true.`; `low_flow_closure_enabled = .false.` (OFF by default, unchanged) |
| Input files at root | `KOORD.DAT`, `hhh.bar`, `1_1.ice`–`1_5.ice` **absent** (T-12) — created as symlinks to `data/input/generated/real_grid/` (documented operational step, all gitignored) |
| Forcing period | 2020-01 (Q1); run length controlled by ERA5 slice count (`mm1 = min(91, (ntime-1)/nperday)`) |
| Compiler / build | gfortran via fpm 0.13.0-alpha, `-I/usr/include` (netcdf.mod), netCDF link |
| Environment | Linux; conda env `iceberg-thermodynamic-model` for Python |

## 4. Operational dependency audit

| Component | Required file / command | Exists? | Status | Notes |
| --------- | ----------------------- | ------- | ------ | ----- |
| Build | `fpm build --flag "-I/usr/include"` | — | PASS | compiles; `fpm.toml` `main = "iceberg_main.f90"` vs actual `app/main.f90` — fpm resolves the executable anyway (smoke run works); naming mismatch noted |
| Full model run | `fpm run --flag "-I/usr/include" -- <run_id> [era5_file]` | — | PASS (operational) | runs 1 day (5 slices) and 7 days (29 slices); exit 0; **see §6 for ocean-field NaN finding** |
| ERA5 input | `data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc` | YES | PASS | 364 slices, 6-hourly; 259 model points outside ERA5 lat range get zeroed (warning, pre-existing) |
| EN4 input | `data/input/processed/ocean/initial_ts_2020-01-01.nc` | YES | PASS | 143,422 wet cells |
| Real grid | `data/input/generated/real_grid/KOORD.DAT`, `hhh.bar` | YES (dir) / root symlinks created | PASS | without root symlinks: FATAL STOP (grid_mode_real), SKIP in tests |
| Sea-ice init | `1_1.ice`–`1_5.ice` (+ `ice_2020-01-01/`) | YES (dir) / root symlinks created | PASS | ice init chain validated |
| Iceberg module (Lagrangian) | `src/iceberg*.f90`, driven by `test/iceberg_test_11_30day_offline.f90` | YES | PASS | **the only operational path that executes the Lagrangian iceberg model**; the production executable does NOT `use` iceberg modules |
| Trajectory output | `data/output/diagnostics/stage9.3/test11_trajectory.csv` (TEST_11 hardcoded path) | YES (fresh, this stage) | PASS | 720 hourly rows |
| Diagnostic script | `python/analysis/stage10.15_diagnostics.py` | YES (new) | PASS | checks + 7 figures + summary JSON |
| Output bundle | `data/output/stage10.15/` | YES (new, gitignored) | PASS | logs, CSV copy, summary, plots |

## 5. Commands (reproducible)

```bash
# 0. Operational prerequisite (documented in AGENTS.md, KNOWN_ISSUES T-12):
ln -sf data/input/generated/real_grid/KOORD.DAT KOORD.DAT
ln -sf data/input/generated/real_grid/hhh.bar   hhh.bar
for k in 1 2 3 4 5; do ln -sf data/input/generated/real_grid/1_$k.ice 1_$k.ice; done

# 1. Build + full test battery (clean rebuild)
rm -rf build
fpm test --flag "-I/usr/include"

# 2. Full-model smoke run (1 day; ERA5 slice count controls length)
fpm run --flag "-I/usr/include" -- stage10.15_smoke <5-slice-era5.nc>

# 3. Full-model 7-day run
fpm run --flag "-I/usr/include" -- stage10.15_day7 <29-slice-era5.nc>

# 4. Lagrangian iceberg 30-day run with real forcing (TEST_11)
fpm test --flag "-I/usr/include" iceberg_test_11_30day_offline

# 5. Diagnostics + figures + summary
conda run -n iceberg-thermodynamic-model python python/analysis/stage10.15_diagnostics.py
```

Truncated ERA5 slices for controlled run length are created from the full Q1
file with xarray (`isel(valid_time=slice(0,n))`): 5 slices → 1 day, 29 → 7
days, 121 → 30 days. Copies used for this stage are in
`/tmp/opencode/era5_slices/` (debug/test slices — **not scientifically
representative of the full Q1 forcing**; the full Q1 file is the production
input).

## 6. Results

### 6.1 Full model (`fpm run`) — Eulerian ocean/sea-ice

| Run | Duration (model) | Wall clock | Exit | Result |
| --- | ---------------- | ---------- | ---- | ------ |
| stage10.15_smoke | 1 day (5 slices) | ~2–3 min | 0 | day_00 clean; **day_01 3D ocean fields NaN** |
| stage10.15_day7 | 7 days (29 slices) | 3 m 15 s | 0 | day_01–07: NaN fraction constant at 56.5 % (142,081/251,370 cells) |

Findings:

- day_00 (initial state) is clean: T 272–279.9 K, S 0–0.03508, u/v nonzero
  small, no NaN; wind/tau/dp/air fields valid.
- day_01: `temperature`, `salinity_mass_fraction`, `density_anomaly` are NaN
  in **all** wet cells; `u/v_velocity` NaN in 52 %; `ice_thickness` NaN in all
  ice cells; `w_velocity` NaN in 56 %. Remaining non-NaN T is frozen at
  273.15 K.
- The NaN pattern is **stable** across days 1–7 (no growth, no crash, no
  divergence) — a "zombie" ocean state, consistent with the documented Stage 8
  EN4 initialization imbalance family
  (`docs/wiki/stages/stage08/Stage8.1_*`, `Stage8.2_*`; thermal-wind shear
  mismatch → NaN propagation via the Thomas solver; `KNOWN_ISSUES.md` T-03).
- Atmospheric forcing chain (wind, air temp, pressure, humidity, cloud, ERA5
  snowfall) is valid on all days — the atmospheric path works end-to-end.
- EUU ≈ 1.27–1.66e18 throughout — the documented Stage 8/9 kinetic-energy
  scale, not a new finding.
- `ca_guard` events fire (1000-iteration guard, T-01) — known behavior.
- ERA5 wind warning: 259 model points outside the ERA5 latitude range are
  zeroed — pre-existing domain-coverage note (the expanded `fullcoverage`
  file exists; the default Q1 file is the Barents-expanded one).

**Interpretation:** the Eulerian ocean model executes operationally (build,
init, loop, output, exit 0) but its 3D ocean state is **physically dead from
day 1** with the real EN4 initialization. This is a pre-existing scientific
limitation, not introduced by Stage 10.14/10.15, and not fixable without a
documented physics/initialization procedure (Stages 8.2–8.6 attempted
corrections; the imbalance remains).

### 6.2 Lagrangian iceberg module (TEST_11, real forcing, offline)

| Item | Value |
| ---- | ----- |
| Run | 30 days, dt = 3600 s, 720 hourly steps, exit 0 |
| Checks | 7/7 PASS (no NaN, positive geometry, mass decreased, drift speed plausible, melt plausible, budget closes, grounding logic) |
| Start position | 74.83 °N, 30.31 °E (model cell i=61, j=37; init lat=75, lon=30) |
| End position | 75.07 °N, 29.84 °E (day 30) |
| Displacement | 11.5 km straight-line, 26.0 km path over 30 days |
| Speed | max 0.028 m/s (2.8 cm/s) |
| Mass | 909.8 → 769.6 Mt (−15.4 % over 30 days) |
| Melt (max) | basal 0.049, lateral 0.260, surface 0.022 m/day |
| Geometry | L/W 100 → 92.2 m; H 100 → 99.5 m (lateral melt dominates; surface melt ~0 in January polar night) |

Physical/numerical checks (all PASS): no NaN in trajectory; geometry
positive; mass monotone non-increasing; lat in [74.8, 75.2] °N, lon in
[29.7, 30.3] °E (in domain); speed plausible; melt bounded.

**Important discrepancy (honest):** the fresh 30-day run does **not** match
the archived Stage 9.3 `test11_results.json` (final H = 28.96 m, surface melt
15.7 m/day, mass 232 Mt). The archived result predates the Stage 10
thermodynamic fixes (surface energy balance, latent heat corrections, Stage
10.1–10.6); the fresh run reflects current physics (H = 99.5 m, ms ≈ 0,
mass 770 Mt). The archived JSON is stale relative to current code; this
stage does not modify it (historical record), but flags the difference.

### 6.3 Test battery after the T-12 prerequisite

With root symlinks in place, all previously-skipped grid/input-dependent
tests now pass: `iceberg_test_11_30day_offline` (7), `ice_init_test`,
`ocean_init_test`, `era5_coverage_test` (full ERA5 coverage), TEST_3
(uniform current, 5), `drift_scaling_wind`, `drift_scaling_current`,
`param_sensitivity_30day` — all exit 0. The drift-scaling tables reproduce
the documented anomalies: wind-drift ratio ≈ 0.13 % (T-07, expected 1–2 %)
and current-drift ratio 0.3–1.2 % (expected 2–5 %) — **known, pre-existing,
not re-fixed here**.

## 7. Figures and tables

Generated under `data/output/stage10.15/plots/` (gitignored):

| Figure | Content |
| ------ | ------- |
| `fig1_trajectory_latlon.png` | 30-day iceberg trajectory map (lat–lon, colour = time) |
| `fig2_lat_vs_time.png` | latitude vs time |
| `fig3_lon_vs_time.png` | longitude vs time |
| `fig4_speed_vs_time.png` | drift speed vs time (cm/s) |
| `fig5_melt_vs_time.png` | basal/lateral/surface melt rates vs time |
| `fig6_mass_vs_time.png` | mass vs time (Mt) |
| `fig7_geometry_vs_time.png` | L/W/H vs time |

All figures carry title, axis labels, units, time range, run identifier
(TEST_11), and are model output (no observations plotted). Summary:
`data/output/stage10.15/stage10.15_summary.json`.

## 8. Limitations

- **The production executable does not run the Lagrangian iceberg model.**
  `app/main.f90` has no `use iceberg*`; the iceberg module is reachable only
  through test programs (`iceberg_test_11_30day_offline`). The Stage 10.15
  trajectory is therefore produced by the **test harness**, not by `fpm run`.
  This is the single most important operational finding.
- **Full-model ocean state is dead from day 1** (NaN, Stage 8 family) — the
  Eulerian component cannot yet serve as an ocean-forcing provider for the
  iceberg in coupled mode; the iceberg currently runs offline on prescribed
  EN4/ERA5 forcing.
- The trajectory result is **not validated against observations** (no
  iceberg-track dataset in this stage).
- Archived `test11_results.json` (Stage 9.3) disagrees with the fresh run
  (pre-Stage-10 physics) — historical record kept unchanged.
- Run-length control requires ERA5 truncation (no CLI day-count switch);
  debug slices are labelled, not scientifically representative.
- `fpm.toml` executable `main = "iceberg_main.f90"` does not match
  `app/main.f90` (fpm still builds the executable; cosmetic, not blocking).
- Wind/current drift ratios remain low vs literature (T-06/T-07) — known.
- 259 model points outside the default ERA5 domain are zeroed (pre-existing;
  the `fullcoverage` file is available as an alternative input).
- Observational comparison (10.8.2) applies to basal melt of the closure,
  not to this trajectory.

## 9. Scientific classification

**Operational demonstration completed (Lagrangian iceberg module, real
forcing, 30 days, reproducible) — with documented limitations.**

Not claimed: fully validated; production-ready; universally valid;
observationally confirmed; calibrated; operationally complete. Successful
execution does not prove physical accuracy; a stable numerical run does not
prove observational agreement; the produced trajectory does not prove
correct drift physics (speed ratio anomaly T-07 remains).

## 10. Files changed

- `python/analysis/stage10.15_diagnostics.py` (new, diagnostics only);
- `docs/validation/stage10.15_operational_demonstration.md` (this report);
- living docs updated: `docs/validation/INDEX.md`,
  `docs/model/model_physics_status.md`, `docs/PROJECT_ROADMAP.md`,
  `docs/model/stage10_modernization_plan.md`, `KNOWN_ISSUES.md`,
  `CHANGELOG.md`, `README.md` (stage line), `AGENTS.md` (commands).

**Unchanged:** `src/`, `app/`, `test/`, `fpm.toml`, `.github/workflows/`,
`data/` (only gitignored run outputs added), all historical reports.

## 11. Recommended next step (evidence-based)

From the actual evidence:

1. **Decide the iceberg coupling question** (single most limiting item): the
   Lagrangian iceberg currently has no production path. Either (a) document
   the test-harness run as the sanctioned operational mode, or (b) plan a
   dedicated integration stage that calls the existing `iceberg_step` from
   the main loop with prescribed ocean fields (no physics change, interface
   work only) — with its own design note and regression tests.
2. **Before any trajectory-level scientific use**, resolve or explicitly
   quantify the drift-speed anomaly (T-07: wind ratio 0.13 % vs 1–2 %) —
   the current trajectory amplitude is not interpretable as real drift
   without this.
3. The Eulerian ocean dead-state (Stage 8 family) blocks coupled forcing;
   a dedicated ocean-initialization stabilization stage is a prerequisite
   for coupled demonstrations, and is independent of the iceberg module.
4. Only after (1)–(3): trajectory-level observational comparison with a
   curated iceberg-track dataset (e.g., Arctic ice-berg positions) as its
   own validation stage.

No new physical parameterization is proposed by this stage.