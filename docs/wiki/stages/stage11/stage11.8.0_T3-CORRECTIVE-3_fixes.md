# Stage 11.8.0 T3-CORRECTIVE-3 — Fixes, T-19 v2, and Process Hygiene

**Status:** COMPLETE — fixes implemented behind OFF-by-default D-33 switches;
**T3b still FAILS**, T4 remains NO-GO.
**Date:** 2026-10-25
**Base:** `8d40cc0` (T3-CORRECTIVE-2)
**Scope:** E1 prognostic RO, E2 potential-density CA, E3 float64/N² CA
threshold, T-19 snowfall v2, T3 criteria revision, EUU diagnostic, living state
file and documentation archive. No production default was changed.

---

## 1. T-19 snowfall — v2 probe and divisor fix (FIXED)

The v1 probe used `step` ranges; CDS collapsed the multi-step request, so its
12-hour conclusion was invalid. The v2 probe (`python/tests/ocean/t19_cds_probe.py`)
requests **2020-01-15, 24 hourly validity times, no `step` parameter** and
compares the 12:00 field with the mean of all 24 fields:

| quantity | value |
|---|---|
| mean 12:00 spatial snowfall | 5.4868e-5 m |
| mean of all 24 hourly fields | 5.4379e-5 m |
| **R = mean(12:00) / mean(all 24)** | **1.00898** |
| verdict | **HOURLY_ACCUMULATION** |
| recommended divisor | **3600 s** |

If the field were a 12-hour accumulation, R would be ~12; it is ~1.009.
`docs/wiki/stages/stage11/evidence/t19_cds_probe_v2.json`; v1 JSON is marked `INVALID_V1`.

**Code fix:** `python/era5/merge_snowfall.py` now uses
`SNOWFALL_ACCUMULATION_PERIOD_S = 3600.0`; hourly raw records are summed over
each 6-hour model window `/21600 s`, while coarse 00/12 artifacts are converted
`/3600` and interpolated. April and January merged products were regenerated
(`sf` max ~1.1-1.4e-6 m/s, plausible rates). `test_snowfall_period.py` now
reports **CONFIRMED_1H**; `test_stage11_7e3_era5_contract.py` passes **120/120**
(hourly assertions); the Fortran `snowfall_test` uses 1 h/3600 s.

## 2. E1 — prognostic RO (`STAGE118_RO_PROGNOSTIC`, default OFF)

- `src/stage118_physics_switches.f90` adds the D-33 switches.
- `src/equation_of_state.f90:eos_update_ro()` recomputes RO from T2/S2 for all
  wet cells (silent; LEGACY/EOS80/f64 dispatch).
- `app/main.f90` calls it after `conv_adj` and before Block 200 when the switch
  is ON; `convective_adjustment.f90` suppresses its local RO writeback in that
  case.
- **Measured effect: none (bit-identical day-1 output).** `conv_adj` already
  writes RO for **every wet column** after T/S mixing, not only mixed columns;
  `eos_update_ro()` is therefore redundant. The T3-CORRECTIVE-2 statement that
  RO is only updated inside CA for mixed columns was too narrow. The switch is
  retained as a contract/experiment but does not fix T3b.

## 3. E2 — potential-density CA (`STAGE118_CA_POTENTIAL`, default OFF)

In both `convect_column` and `convect_column_f64`, the stability test compares
both levels at the **same reference pressure** (the lower level's pressure,
`p = z(k+1)·0.01` dbar):

```
rho_pot1 = eos_density(T_k,   S_k,   p_{k+1})
rho_pot2 = eos_density(T_k+1, S_{k+1}, p_{k+1})
```

This removes the compressibility artifact of T-25. **Measured effect in
LEGACY: none** — the legacy Eckart EOS is pressure-independent, so in-situ and
potential densities are identical; the switch is only meaningful with EOS80.
EOS-80 + all switches also remained unstable (Umax 3.849 m/s,
KE30/KE15 49.3).

## 4. E3 — real64 CA differences + N² threshold (`STAGE118_CA_F64_N2`, default OFF)

When ON, both CA kernels use `eos_density_f64` for the stability difference
(and potential density if E2 is ON) and replace the historical
`0.9e-7 g/cm³` threshold with the physical criterion

```
N² = -(g/ρ0)·(ρ_upper - ρ_lower)/(z_lower - z_upper) < -1e-6 s⁻²
```

(equivalently, mix only when the potential-density inversion is strong enough).
The T/S mixing arithmetic and the stored state remain float32; T-27 is
addressed only for the **criterion**, not for the stored state.

**Measured effect:** CA mixings drop sharply (day 2: **61,454** vs 7,083,949;
guard hits 0 vs 1001), but the flow still grows. Day 30: Umax **3.902 m/s**,
Vmax **5.410 m/s**, KE15 **1.641e14 J**, KE30 **8.696e15 J**,
**KE30/KE15 = 52.98**. E1+E2+E3 equals E3 alone.

## 5. E6 — boundary sponge (fallback, tested, not used)

`STAGE118_BOUNDARY_SPONGE` (default OFF) implements Rayleigh damping in an
8-cell boundary band (τ=1 day). It was tested because E1–E3 failed:

| configuration | Umax (m/s) | KE15 (J) | KE30 (J) | KE30/KE15 |
|---|---|---|---|---|
| E1+E2+E3 | 3.902 | 1.641e14 | 8.696e15 | 52.98 |
| + sponge width 8, τ=1 d | 3.714 | 1.500e14 | 6.990e15 | 46.6 |
| + sponge width 12, τ=6 h | 2.983 | 1.163e14 | 3.542e15 | 30.5 |
| + sponge width 20, τ=1 h | 1.705 | 4.822e13 | 8.719e14 | 18.1 |

The sponge reduces the peak but **does not produce a plateau**; it is an
amplifier mitigation, not the root fix. It remains OFF and was not used for the
T3b verdict.

## 6. T3 rest criteria (revised)

- **T3a — pure rest:** homogeneous T/S, real bathymetry; criterion
  `max |U| < 1e-6 m/s`, no PGF. Documented; not executed here (requires a
  homogeneous EN4-format product).
- **T3b — adaptation:** real EN4 T/S, zero forcing, zero initial velocity;
  criterion `max |U| < 0.5 m/s`, `KE30/KE15 < 2.0`, no exponential growth.
  The T3-CORRECTIVE-2 absolute `|U| < 0.01 m/s` criterion was physically wrong
  (geostrophic adjustment yields ~0.2–0.3 m/s) and is superseded.

## 7. T3b result after E1–E3 (FAIL)

Run `t3c3_all` (30 days, zero forcing, corrected EN4, `EOS_MODE=LEGACY`):
max |U| **3.902 m/s**, max |V| **5.410 m/s**, KE day 15 **1.641e14 J**,
KE day 30 **8.696e15 J**, **ratio 52.98** (acceptance < 2.0) → **FAIL**.
E1 alone and E2 alone are bit-identical to the baseline (E1 redundant, E2
inactive in LEGACY); E3 is the only active change and does not stabilize.
A balanced-initial-state diagnostic (`STAGE118_T3_KEEP_TW`) also failed
(Umax 3.998 m/s, KE30/KE15 50.4). Data: `docs/wiki/stages/stage11/evidence/t3c3_fix_results.json`,
`t3c3_experiments.json`.

**Interpretation:** the remaining instability is the **coupled T/S
advection + density-refresh system** at 13.89 km / Δt=3600 s, not a simple
stale-RO or in-situ-CA bug. Freezing T/S or RO bounds the flow, but that is not
a physical fix. E1–E3 do not meet T3b; E6 only masks the boundary peak.
**T4 remains NO-GO; T3-CORRECTIVE-4 is required** (dissipation, boundary
radiation, time-step/CA sub-cycling, or resolution/initialization study).

## 8. EUU diagnostic (T-31)

`app/main.f90` now prints a correct **3D kinetic energy** diagnostic each day
(`KE3D(J)`, erg→J) in addition to the historical barotropic `EUU` accumulator.
Example: day 2 `KE3D = 9.356e12 J` (nonzero), while `EUU` remains 0 because
the barotropic transports are zero in the rest state. The misleading
"EUU=0" line is no longer the only energy diagnostic.

## 9. Process hygiene

- `docs/STAGE11_STATE.md` created (84 lines) with T-01…T-33 status, current
  commit, next step.
- **69 historical Stage 11.0–11.7 reports moved** from `docs/validation/` to
  `docs/archive/stage11/`; `docs/validation/` now contains only the active
  Stage 11.8 reports and INDEX. Links in `INDEX.md` and living docs were
  rewritten to the archive paths.
- `KNOWN_ISSUES.md`, `PROJECT_ROADMAP.md`, `model_physics_status.md`,
  `README.md`, `DECISIONS.md` updated (T-19 v2, T-25/E2, T-30/T3b, T-31,
  T-32/E1, new T-33).

## 10. Regression and safety

| Check | Result |
|---|---|
| Full `fpm test` | **60/60**, exit 0 |
| Strict build | exit 0 |
| ERA5 contract (hourly) | **120/120** |
| Snowfall period | **CONFIRMED_1H** |
| EN4 T0 / T3-PREP / mask | CLEAN / CLEAN / CLEAN (8/8) |
| ERA5 coverage / spatial / temporal / wrap | ISSUES (T-21/H-2 expected) / WARNING / PASS / RED_CONFIRMED (T-23) |
| T2 homogeneous/weak/conservation/compressibility | PASS / PASS / PASS / CRITICAL_CONFIRMED |
| Advection boundary | PASS |
| Default legacy bit-identity | 1-day rest output md5 identical to `t3c_legacy_canonical` |
| `git diff --check` | clean |

No physics default changed: all E1–E3/E6/T3-KEEP switches are OFF by default;
`EOS_MODE=LEGACY` remains default. T-23/H-2 untouched; T4–T6 not started; no
`data/runs/` data deleted.
