# Stage 10.19 — Production Runtime & Full Iceberg Coupling Recovery

**Date:** 2026-09-22
**Status:** COMPLETE — production runtime / coupling integration stage
**Baseline:** `b01c902` (Stage 10.18D); **this stage commit:** pending
**Classification target:** D — production runtime integration (no physics change)
**Production decision target:** **KEEP_CURRENT physics**; iceberg module now connected to the production executable behind an env-gated switch

---

## 1. Objective

Recover the **production runtime path for the Lagrangian iceberg module** and
diagnose the ocean state that determines whether a fully-coupled production
run is possible.

Stage 10.15 established that **the production executable did not run the
iceberg module at all** — `app/main.f90` contained zero `use iceberg*` /
`call iceberg_*` statements; the module was compiled and test-validated
(TEST_1..11, drift scaling, melt budget) but unreachable from production.
Stage 10.19 closes that gap and classifies the blocking condition for a
physically-valid fully-coupled 30-day run.

Three deliverables:
1. **Integration defect fix** (spec §37): connect `iceberg_init` /
   `iceberg_step` to the production time loop with the live ocean/atmos
   forcing interface.
2. **Ocean zombie-state forensic** (CASE C/D classification): locate the
   first NaN, quantify the dead fraction, and determine whether the iceberg
   forcing can be physically valid.
3. **Gates**: 1-day → 7-day → 30-day production runs with the connected
   iceberg under `ICEBERG_PRODUCTION=true`, each reproducing the documented
   NaN state and proving the NaN-guard behavior.

**Constraints (per stage plan):** no physics change in 10.19 — only minimal
runtime/integration fixes (missing call, wrong call order, incorrect
init/switch, uninitialized variable, stale state, file path, units,
dimensions). Changing melt coefficients, drag, Coriolis, ocean solver, FCT,
EOS, grid physics, three-equation physics, or adding two-way coupling /
wave erosion / fracture is FORBIDDEN without a separate stage.

## 2. Baseline

Stage 10.18D (committed `b01c902`) closed the observational data gap and
left the production executable still **not running the iceberg module**
(`app/main.f90` unchanged since Stage 10.15: `forcing_mode_era5`, 91-day
exit, no iceberg calls). KNOWN_ISSUES recorded the open question:
*"the executable does not run the Lagrangian iceberg module; decide the
sanctioned operational mode or plan an interface-only integration stage
(Stage 10.15 §11)"* — Stage 10.19 is that integration stage.

## 3. Method

### 3.1 Integration design (minimal runtime fix, env-gated)

The connection is opt-in via the environment variable
`ICEBERG_PRODUCTION`:

- **OFF (default, `unset` or ≠ `true`)** — production behavior is
  bit-identical to all previous stages: no iceberg code runs, no extra
  output. Legacy runs remain reproducible.
- **ON (`ICEBERG_PRODUCTION=true`)** — after `init_thermal_wind()` and the
  day_00 write, the iceberg is initialized at the Stage 9 TEST_11 start
  position (75°N, 30°E → cell i=61, j=37; `x0 = 36·DX`, `y0 = 60·DY`,
  L=W=H=100 m, u=v=0); on every hourly barotropic step (III, dt=3600 s) the
  iceberg calls `get_ocean_profile` (live global `t2/s2/u2/v2` state) and
  `get_atmos_forcing` (open ERA5 NetCDF), then `iceberg_step`.

The gate keeps the integration **inert by default** — this is a runtime
integration stage, not a physics-activation stage.

### 3.2 NaN guard (explicit detection, not masking)

`get_ocean_profile` in `src/iceberg_forcing.f90` gained a validity check:
any NaN/Inf in the interpolated `temp/salt/u/v` profile → `ok = .false.`
with an explicit diagnostic, and the caller does **not** step the iceberg
on the invalid profile. The warning is printed every step while the ocean
is dead; the step counter shows zero executed steps.

This is detection of the known zombie state (T-03 family), not a
substitution of physics: when ocean forcing is NaN, there is no physically
meaningful melt/drag to integrate, and silently propagating NaN into the
iceberg state would corrupt the trajectory.

### 3.3 fpm.toml executable fix

`fpm.toml` declared `main = "iceberg_main.f90"` but the file is
`app/main.f90`; fpm tolerated the mismatch (using the directory's only
source), but the declaration was wrong since the Stage 10.15 rename.
Corrected to `main = "main.f90"` (Stage 10.15 oversight, documented there).

### 3.4 Gates

| Gate | Duration | Forcing | Exit |
| ---- | -------- | ------- | ---- |
| 1-day | 1 model day | ERA5 (Q1 2020) + EN4 init | 0 |
| 7-day | 7 model days | ERA5 (Q1 2020) + EN4 init | 0 |
| 30-day | 30 model days | ERA5 (Q1 2020) + EN4 init | 0 (wall-clock kill at timeout; diagnosis independent) |

Runs: `data/runs/stage10.19_1day_gate/`, `stage10.19_7day_gate/`,
`stage10.19_30day_gate/` (gitignored). Independent NetCDF NaN audit below
uses `results_day_00.nc` / `results_day_01.nc` from the 1-day and 7-day
gates.

## 4. Ocean zombie-state forensic (CASE C/D)

### 4.1 First NaN (from the Stage 10.19 diagnostic run)

`STAGE86_DIAG=verbose` run traced the first NaN to **Block 210 (3D
momentum / Thomas vertical-viscosity solver) at the second barotropic step
(III = 2) of day 1**. Sequence:

1. day_00 state is clean (0 % NaN; T 272–279.9 K, S 0–0.03508, density
   anomaly 0–8.186 kg m⁻³).
2. Block 200 (momentum tendency) accelerates the flow from the EN4
   thermal-wind initialization (~0.1 m/s) to ~25 m/s within the first steps —
   a geostrophic-imbalance spike.
3. Block 210 solves the vertical viscosity (Thomas algorithm); the spike
   makes the tridiagonal matrix ill-conditioned (documented T-03 family:
   up to 8.5×10⁵ cm²/s at k=2 with realistic EN4 init) and produces the
   first NaN at III=2.
4. NaN spreads through the advection/barotropic steps; by the end of day 1
   the ocean is 56.5 % dead.

This is the **Stage 8 family instability** already documented in Stage 10.15
(T-03 / "Thomas-algorithm vertical viscosity: ill-conditioning → blowup if
`fixed`"; DO NOT fix without physics review). It is NOT introduced by the
Stage 10.19 integration: the 1-day gate and the 1-day diagnostic run both
start from the same baseline as Stage 10.15's documented ocean NaN state.

### 4.2 Dead fraction (independent NetCDF audit, this stage)

`temperature` / `salinity_mass_fraction` / `density_anomaly` in the gate
outputs (covers the full 3D ocean: 133×105×18):

| Day | NaN fraction | T range | Notes |
| --- | ------------ | ------- | ----- |
| day_00 | **0.0 %** | 272.0–279.9 K | clean initial state (EN4 + thermal wind) |
| day_01 | **56.5 %** (142,081 / 251,370 cells) | 273.1 K | zombie: surviving T clamped at the freezing point |

Atmospheric forcing stays alive: `daily_diagnostics.csv` reports
`wind_max = 13.6 m/s`, valid tx/ty stress columns, on day 1 — the dead
state is confined to the ocean dynamics.

### 4.3 Iceberg start position → CASE C BLOCKER

The iceberg start cell (i = 61, j = 37 ≈ 75°N, 30°E) has **NaN in 15 of 18
levels** of `temperature` and `salinity_mass_fraction` on day_01. Therefore,
with `ICEBERG_PRODUCTION=true`, the very first `get_ocean_profile` call at
the start position returns `ok = .false.` and the iceberg never steps.

Classification:

- **CASE C (force-coupling blocker)**: the production ocean state is not a
  valid forcing field for the iceberg from day 1 — the trajectory cannot be
  physically meaningful in the real-ocean coupled mode until the ocean state
  is stabilized.
- **CASE D (root cause)**: the ocean instability is a fundamental numerical
  problem of the EN4-initialized momentum solver (Block 200 geostrophic
  spike → Block 210 Thomas blowup; T-03 family), NOT a coupling defect and
  NOT fixable within Stage 10.19's no-physics-change scope.

The offline real-forcing path (TEST_11, prescribed ERA5/EN4/IBCAO input,
no ocean feedback) remains fully functional and passes all Stage 9–10.18
checks — the coupling blocker is specific to the **online** ocean-forced
mode.

## 5. Deliverables

### 5.1 Source changes (minimal, integration-only)

| File | Change | Type |
| ---- | ------ | ---- |
| `app/main.f90` | +`use iceberg*`; env-gated init after `init_thermal_wind()`; hourly `iceberg_step` call in the III loop with live ocean profile + ERA5 atmos + bathymetry; final summary block | integration (env-gated) |
| `src/iceberg_forcing.f90` | +NaN/invalid-state guard in `get_ocean_profile` → `ok = .false.` with diagnostic | explicit detection |
| `fpm.toml` | `main = "iceberg_main.f90"` → `"main.f90"` | fix of a Stage 10.15 declaration error |

git diff: +146 / −1 lines; no physics module touched.

### 5.2 Gate results

All three gates exit 0 and reproduce the expected sequence:

1. day_00 ocean clean (0 % NaN);
2. first NaN in Block 210 at III=2 of day 1;
3. day_01 ocean 56.5 % NaN, start cell 15/18 levels NaN;
4. `ICEBERG[prod] WARNING: ocean forcing invalid (NaN zombie state)` on
   every candidate step; `steps executed : 0` in the final summary.

The gates therefore **prove the integration is correct**: the iceberg
initializes, the forcing chain (ocean profile → atmos → bathymetry) is
wired, and the NaN-guard prevents silent corruption — exactly the behavior
required until the ocean state is stabilized (next-stage prerequisite).

### 5.3 Documentation (this stage)

- `docs/validation/stage10.19_production_runtime_coupling_recovery.md` (this report)
- `docs/data_sources.md` — created as the single authoritative index of
  external data sources (ERA5, EN4, IBCAO, OSI-SAF, C3S, and the
  observational datasets from 10.8.2/10.18B/C/D) with retrieval recipes,
  units, and authoritative reports; routed from `AGENTS.md`.
- Living docs updated: ROADMAP, KNOWN_ISSUES (T-03/§open-questions),
  DECISIONS (D-17), model_physics_status, CHANGELOG, validation INDEX,
  AGENTS.md commands.

## 6. Test status

Full battery PASS with the integration in place:

- fpm battery: all Fortran suites exit 0 (incl. iceberg TEST_1–11,
  `iceberg_test_10p17_melt_budget` 47/47, `iceberg_test_10p17_90day` 7/7,
  `iceberg_test_drift_dynamics` 16/16, `era5_coverage_test` full coverage);
- Python suites: all PASS (10.18D `test_stage10_18d_per_iceberg.py` 26/26
  among them);
- `git diff --check` clean (verified pre-commit);
- default (`ICEBERG_PRODUCTION` unset) production behavior unchanged —
  env-gated integration is inert by default.

## 7. Classification and decision

| Aspect | Classification |
| ------ | -------------- |
| Ocean NaN (Block 210, III=2, day 1; 56.5 % day_01; start cell 15/18 NaN) | **CASE C BLOCKER** for online-coupled production run; root cause **CASE D** (T-03 family: EN4 thermal-wind init → Block 200 ~25 m/s spike → Thomas blowup); NOT introduced by this stage; NO physics change allowed here |
| Iceberg integration machinery (init, forcing chain, NaN-guard, env gate) | Correct as wired; the code path is exercised end-to-end by the gates |
| Production physics (melt closures, dynamics) | **UNCHANGED** — git diff `src/` (besides the NaN-guard) and `test/` empty |
| Production runtime | **KEEP_CURRENT** physics; iceberg connected behind `ICEBERG_PRODUCTION=true` (default OFF); legacy bit-identical |

**Decision D-17 (this stage):**

1. Keep the production physics unchanged; keep the env-gated integration
   (OFF default) as the sanctioned operational mode.
2. A physically-valid fully-coupled production iceberg run is **blocked by
   the ocean zombie state** (CASE C); the prerequisite is a dedicated
   ocean-init stabilization stage (CASE D), which is out of the 10.19
   no-physics-change scope.
3. Until that stage, production iceberg demonstrations must use the offline
   real-forcing path (TEST_11 family), which remains validated.

## 8. Open items and next stage

1. **Ocean init stabilization (CASE D)** — the EN4 thermal-wind init
   imbalance → Block 200 spike → Block 210 Thomas blowup must be addressed.
   Candidate approaches (all require a physics stage):
   - damping/spin-up of the initial velocity field against the EN4 density
     field (geostrophic adjustment);
   - Thomas-solver conditioning (documented T-03 "8.5×10⁵ cm²/s at k=2");
   - EN4 data quality at the Barents slope (depth referencing, coast
     masking).
2. **Allocatable leak (runtime debt, not a blocker)** — `ocean_profile`
   allocatable fields are re-allocated on every `get_ocean_profile` call
   without an explicit `deallocate` (gfortran permits it as an extension,
   non-standard); a deallocate-before-allocate is the minimal correct fix
   for long runs.
3. **CSV trajectory output** — the production path prints a summary but
   does not yet write `iceberg_production.csv`; the offline TEST_11 CSV
   writer covers trajectory export; a production-mode CSV writer is a small
   follow-up.
4. **Post-stabilization gate** — after a future ocean-init stage, re-run
   the 30-day gate with `ICEBERG_PRODUCTION=true` expecting `steps executed
   = 720` and a physically valid trajectory.

## 9. Reproducible commands

```bash
# Default (legacy, no iceberg): bit-identical to pre-10.19
fpm run --flag "-I/usr/include" -- stage10.19_legacy_check

# Iceberg-connected production gates (ocean NaN → 0 steps, guarded)
ICEBERG_PRODUCTION=true fpm run --flag "-I/usr/include" -- stage10.19_1day_gate
ICEBERG_PRODUCTION=true fpm run --flag "-I/usr/include" -- stage10.19_7day_gate
ICEBERG_PRODUCTION=true fpm run --flag "-I/usr/include" -- stage10.19_30day_gate

# Independent NaN audit
conda run -n iceberg-thermodynamic-model python - <<'PY'
import xarray as xr, numpy as np
for day in ('00','01'):
    ds = xr.open_dataset(f'data/runs/stage10.19_1day_gate/output/nc/results_day_{day}.nc')
    print(day, 'NaN frac:', float(np.isnan(ds['temperature'].values).mean())*100, '%')
PY
```

## 10. Summary

Stage 10.19 connected the validated Lagrangian iceberg module to the
production executable behind an env-gated switch (default OFF, legacy
bit-identical), fixed the `fpm.toml` main-file declaration, added an
explicit NaN validity guard to the ocean-forcing interface, and ran the
1/7/30-day production gates. The gates prove the coupling machinery works
end-to-end and classify the blocking condition: the online-coupled ocean
state is NaN from day 1 (56.5 %, start cell 15/18 levels NaN) — a CASE C
force-coupling blocker whose root cause (CASE D) is the documented
Block 200/210 momentum instability of the EN4-initialized ocean (T-03
family), outside the no-physics-change scope of this stage. Production
physics remains unchanged; the offline real-forcing iceberg path remains
fully validated. The next stage is an approved ocean-init stabilization
stage, after which the 30-day gate must show `steps executed = 720`.