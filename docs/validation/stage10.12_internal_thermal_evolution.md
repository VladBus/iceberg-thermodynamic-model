# Stage 10.12 — Validation Report: Prognostic Internal Thermal Evolution

**Classification**: C — production physics ADDED on a separately switchable path; two-node lumped interior implemented and independently validated (Fortran 17 + Python 35 checks).
**Baseline commit**: db0524e (stage10.11.3)
**Date**: 2026-09-15
**Design note**: `docs/validation/stage10.12_internal_thermal_evolution_design_note.md` (Phase A; Variant C chosen)

---

## 1. What was implemented

Prognostic interior temperature `state%T_ice` (°C) replaces the constant
`T_i = T_ICE_INIT = -10` inside the three-equation basal closure. Two-node
lumped model (design note §4, Variant C):

| Element | Formula | Units |
|---|---|---|
| Surface skin | `T_surface`, thickness `H_EFF = 0.5 m` (existing, Stage 10.2) | °C, m |
| Interior layer | `H_int = max(H − H_EFF, H_MIN_INT)`, `H_MIN_INT = 0.5 m` | m |
| Interior capacity | `C_int = ρ_i · C_ICE · H_int` | J/(m²·K) |
| Skin→interior conduction | `q_cond = 2·K_ICE·(T_surface − T_ice)/H`, `K_ICE = 2.2` | W/m² |
| Basal sensible sink | `q_bot = m_basal·ρ_i·CP_ICE_3EQ·max(T_B − T_ice, 0)` | W/m² |
| Interior ODE | `C_int·dT_ice/dt = q_cond − q_bot` | — |
| Update | explicit Euler + clamp `[T_ICE_MIN, T_ICE_MAX] = [−100, 0]` | °C |

Energy path per step (`iceberg_thermodynamics_step`): basal melt with
`T_ice` → lateral melt → `q_cond` computed → `compute_surface_melt` receives
`q_cond` as a skin sink (`Q_surface_eff = Q_surface − q_cond`) → `q_bot` from
interface temperature → `update_iceberg_internal_temperature`.

### Switch

`thermal_evolution_enabled` (default `.true.`, `set_thermal_evolution`).
**Fully gates Stage 10.12** in `iceberg_thermodynamics_step` (audit-round fix):
- ON: `q_cond` computed and subtracted from the surface budget
  (`q_internal_exchange` passed), `q_bot` from the interface temperature,
  interior updated by explicit Euler;
- OFF: `compute_iceberg_conductive_coupling` not called, `compute_surface_melt`
  invoked WITHOUT the optional argument (no subtraction), interior not updated
  (`state%T_ice` frozen), 10.12 diagnostics defined explicitly
  (`t_ice = state%T_ice`, `dT_ice_dt = 0`, `c_eff_int = rho_i*c_i*H_EFF`,
  `t_ice_bound = .false.`) — bit-identical legacy for BOTH bulk and
  three-equation paths (the 3eq solver arguments were already gated).

### New diagnostics (`iceberg_diagnostics`)

`t_ice`, `dT_ice_dt`, `c_eff_int`, `t_ice_bound` (logical clamp flag);
`q_surface` already carries the post-coupling value (Stage 10.4.2.1 field).

### Initial condition

`iceberg_init`: `state%T_ice = T_ICE_INIT = −10 °C` (documented initial-condition
parameter; `T_ICE` constant renamed `T_ICE_INIT`, legacy constant removed from
public export).

---

## 2. Files changed

### Production (src/)

| File | Change |
|---|---|
| `iceberg_types.f90` | constants `K_ICE`, `H_MIN_INT`, `T_ICE_INIT/MIN/MAX`; `T_ICE → T_ICE_INIT` rename; `T_ice` state field; 4 diagnostics fields; `thermal_evolution_enabled` + setter; `compute_iceberg_thermal_capacity`, `compute_iceberg_conductive_coupling`, `update_iceberg_internal_temperature` |
| `iceberg_thermodynamics.f90` | `compute_basal_melt(state, ...)` signature (reads `state%T_ice`, gated by the switch); Stage 10.12 block in `iceberg_thermodynamics_step` (q_cond → surface melt `q_internal_exchange`, q_bot, interior update); `compute_surface_melt` optional `q_internal_exchange` |
| `iceberg.f90` | `iceberg_init` initializes `T_ice` |

### Tests

| File | Status |
|---|---|
| `test/iceberg_test_10p12_thermal_evolution.f90` | NEW — 17 checks, 17/17 PASS |
| `python/validation/internal_thermal.py` | NEW — independent float64 replica |
| `python/tests/test_internal_thermal_evolution.py` | NEW — 35 checks, 35/35 PASS |
| Signature adaptation (mechanical `state` argument only): `iceberg_test_10p10_three_equation.f90`, `iceberg_test_10p11_natural_convection.f90`, `iceberg_test_10p7_basal_melt_validation.f90`, `iceberg_test_10p6_ocean_heat_transfer.f90`, `iceberg_test_7_vertical_temp_gradient.f90`, `iceberg_test_surface_energy_balance.f90` | UPDATED — no expected values changed |

### Build

| File | Change |
|---|---|
| `fpm.toml` | unused `stdlib` git dependency REMOVED (zero `use stdlib*` in the repo; eliminates network fetch + broken-partial-clone failure mode in fpm 0.13.0-alpha) |

### CI

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | Python suites `test_three_equation.py` (10.10/10.10.1 — pre-existing gap) and `test_internal_thermal_evolution.py` (10.12) registered; header target count 51 → 54 (fpm auto-discovery covers the new Fortran test). 6 Python suites + full fpm battery now under CI |

---

## 3. Validation results

### 3.1 Fortran unit test (21/21 OK, exit 0)

`fpm test iceberg_test_10p12_thermal_evolution --flag "-I/usr/include"`
(clean build; embedded-literal pattern, production functions called only for
the observed value):

- A.1–A.3 capacity: `C_int(50 m) = 94594496` (float32 of 94594500), `H_int`
  clamp to `H_MIN_INT`;
- B.1–B.4 `q_cond` = 0.44 W/m² (T_s=−5, T_i=−10, H=50), zero at equality,
  sign, 1/H scaling;
- C.1–C.8 explicit Euler: constant/zero fluxes, warming, cooling, BOTH clamps
  (0 °C with bound flag; −100 °C with bound flag), dt=0 no-op, large-dt
  stability (no NaN/Inf), repeatability;
- D.1–D.2 switch setter round-trip;
- E.1 unit/sign plausibility;
- F.1–F.4 OFF-switch legacy invariance (audit round): OFF → `state%T_ice`
  unchanged, 10.12 diagnostics defined at legacy values, surface budget
  bitwise equal to a direct `compute_surface_melt` call without the optional
  argument; ON → `q_cond` subtracted (Δq_net = 0.264 W/m² exactly) and
  interior updated.

**Test-side note (C.5):** the lower-clamp check uses
`q_cond = −30000 W/m²` — an artificially amplified diagnostic flux
(`C_int ≈ 9.46e7 J/(m²·K)` needs `q·dt ≈ 1·C_int` to cross the bound; the
original −1000 W/m² moved T only 0.038 K and did NOT reach −100). This is a
boundary unit test, not a physical scenario; documented in the test itself.

### 3.2 Python independent test (35/35 OK, exit 0)

`conda run -n iceberg-thermodynamic-model python python/tests/test_internal_thermal_evolution.py`

float64 replica (`python/validation/internal_thermal.py`) vs embedded literals:
capacity (exact 94594500.0; cross-language float32 anchor 94594496.0,
rel 4.2e-8), `q_cond` identities, clamps with flag, dt guards (0 and negative),
energy conservation `C_int·ΔT = (q_cond−q_bot)·dt` to 1e-6, basal flux coupling
(linear in `m_basal`, zero at `T_B ≤ T_ice`, magnitude ~60 W/m² for the
Stage 10.10 end-to-end melt anchor), realistic per-hour dT ≈ 0.04 K
(independently confirming the C.5 root cause above).

### 3.3 Cross-language contracts

| Quantity | Fortran (float32) | Python (float64) | Agreement |
|---|---|---|---|
| `C_int(50 m)` | 94594496.0 | 94594500.0 | 4.2e-8 rel (1 float32 ulp) |
| `q_cond` anchor | 0.44 | 0.44 | exact |
| lower clamp | −100.0 + bound | −100.0 + bound | exact |

---

## 4. Known limitations and open items

1. **Switch OFF gating — FIXED in the audit round (was: documented gap).**
   Initially `thermal_evolution_enabled = .false.` gated only the 3eq solver
   `T_ice` argument, while the step still computed `q_cond`, subtracted it from
   the surface budget, and updated the interior (non-legacy). The owner
   requested the fix before commit; the step now gates ALL of Stage 10.12
   (see §1 Switch). Legacy invariance is verified by test block F.1–F.4
   (surface budget bitwise-equal to a legacy `compute_surface_melt` call;
   interior frozen; diagnostics defined). One fpm 0.13.0-alpha caveat
   discovered during verification: incremental builds may link a STALE library
   after src edits (the gated step still ran the old unconditional code until
   `rm -rf build`) — always clean-rebuild before trusting a behaviour change.
2. **Lumped two-node parametrization.** Bi ≫ 1 (200–2·10⁵); diffusion time
   `τ = H²/κ_i` (κ_i ≈ 1.15e-6 m²/s) ranges 10 d (H=1 m) to 2.75e5 d (H=100 m)
   ≫ run length: the interior barely responds on a 90-day run — this is an
   effective bulk parametrization, not a resolved profile.
3. **Explicit Euler** — O(dt) energy error; stable for production dt
   (dT/hour ≈ 0.04 K at q=1000 W/m², H=50 m).
4. **No internal melt at `T_ice = 0`** — clamp at `T_ICE_MAX`, excess energy
   discarded (documented).
5. **Removed-ice enthalpy not tracked** (design note Approach 1): `T_ice` is
   intensive and held through geometry shrink; known energy non-closure.
6. **No double-diffusive / brine physics**; `K_ICE = 2.2 W/(m·K)` is a model
   parameter (literature 2.0–2.3), not calibrated.
7. **fpm 0.13.0-alpha target-scoped library**: iceberg modules compile under
   `fpm test` (target-driven); `fpm build` alone archives only modules
   reachable from `app/main.f90`. Not a code defect; clean `rm -rf build`
   before `fpm test` avoids stale-archive link failures.

---

## 5. Verification summary

| Suite | Result |
|---|---|
| Fortran `iceberg_test_10p12_thermal_evolution` | **21/21 OK, exit 0** (17 + F.1–F.4 OFF-switch; incl. post-whitespace-fix re-run) |
| **OFF-switch legacy-invariance test** | **PASS** (F.1–F.4: interior frozen, diag defined, surface budget bitwise == legacy, ON toggles) |
| Python `test_internal_thermal_evolution.py` | 35/35 OK, exit 0 |
| Full fpm battery (`fpm test --flag "-I/usr/include"`, clean build) | exit 0; no FAILURE/STOP 1/segfault; 10.12 (21/0), 10p10 (25/0), 10p11 (23/0), test_7, 10p6, 10p7, surface suites all pass; `ice_init_test` gracefully skips without KOORD.DAT |
| Python regression suites | 65 (10.10.1) + 70 (10.11) + 44 (10.8.1) + 229 (10.8.2) + 212 (10.9) = 620 checks, 0 errors |
| Strict build `fpm build --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"` | exit 0, 0 warnings |
| `git diff --check` | clean (one trailing-whitespace line in 10p10 test fixed) |
