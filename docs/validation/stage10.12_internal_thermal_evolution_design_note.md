# Stage 10.12 — Phase A Design Note: Prognostic Internal Thermal Evolution

**Status**: DRAFT — Phase A complete, awaiting review before Phase B implementation
**Baseline commit**: db0524e (stage10.11.3)
**Date**: 2026-09-14
**Oracle consultation**: bg_29f63d05 — **TIMED OUT** after 30 min; decision fixed explicitly in this note per spec rules

---

## 1. Audit Summary (Phase A requirement §4)

### 1.1 Existing thermal state variables

| Variable                             | Location                                   | Current meaning                                                     | Units    | Must change in 10.12?                |
| ------------------------------------ | ------------------------------------------ | ------------------------------------------------------------------- | -------- | ------------------------------------ |
| `T_ICE = -10.0`                      | `iceberg_types.f90:261`                    | constant interior ice temperature for basal closure conduction term | °C       | YES — becomes initial condition only |
| `state%T_surface`                    | `iceberg_types.f90:432`                    | prognostic surface skin temperature (0.5 m effective layer)         | °C       | KEEP — atmospheric boundary          |
| `H_EFF = 0.5`                        | `iceberg_types.f90:44`                     | effective surface layer thickness                                   | m        | KEEP — surface skin capacity         |
| `C_ICE = 2100`                       | `iceberg_types.f90:43`                     | ice specific heat capacity                                          | J/(kg·K) | KEEP — shared constant               |
| `T_surface` in `iceberg_diagnostics` | `iceberg_types.f90:371`                    | diagnostic output                                                   | °C       | KEEP                                 |
| `t_ice_in` argument                  | `iceberg_thermodynamics.f90:475, 492, 615` | passed to 3eq solvers as interior temp                              | °C       | SOURCE becomes `state%T_ice`         |

### 1.2 Energy flow diagram (current)

```
ATMOSPHERE → Q_surface = Q_nonlatent + Q_LH
    ↓
SURFACE SKIN (0.5 m, C_s = ρ_i c_i H_EFF)
    ├─ if T_surface < 0:  Q_surface → sensible heating of skin
    ├─ if crossing 0:     excess → surface melt
    └─ if T_surface = 0:  Q_surface → surface melt
    ↓
LATERAL MELT: bulk correlation m_l = C_LATERAL ⟨ΔT⟩_D  (no energy accounting)
    ↓
GEOMETRY UPDATE: H,L,W shrink; mass = ρ_i L W H
    ↓
OCEAN → three-equation basal closure
    Q_ocean = ρ_w c_w γ_T (T_w - T_B)
    =
    m_basal [ρ_i L_f + ρ_i c_i max(T_B - T_i, 0)]  ← T_i = T_ICE = -10 (CONSTANT)
```

**Missing**: No prognostic interior temperature; no energy coupling between surface skin and interior; no advective enthalpy removal when ice melts.

### 1.3 Timestep order (`iceberg_step`)

```
1. iceberg_compute_geometry          (geometry from state)
2. iceberg_compute_buoyancy
3. iceberg_check_grounding
4. iceberg_thermodynamics_step
     a. compute_basal_melt    ← uses T_ICE constant
     b. compute_lateral_melt
     c. compute_surface_melt  ← updates T_surface
5. iceberg_update_geometry            ← H,L,W updated using melt rates
6. iceberg_compute_geometry
7. disappearance check
8. grounding check
9. iceberg_dynamics_step
10. position update
11. time/mass balance
```

---

## 2. Physical Constraints (preliminary audit §5)

| Quantity                     | Value                                            | Implication                                                                       |
| ---------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------- |
| `κ_i = k_i/(ρ_i c_i)`        | 1.15×10⁻⁶ m²/s                                   | thermal diffusivity of ice                                                        |
| `sqrt(κ_i·dt)`               | 0.064 m (dt=3600s)                               | diffusive length per step                                                         |
| Diffusion time τ=H²/κ_i      | 10 d (H=1m), 1005 d (H=10m), 2.75×10⁵ d (H=100m) | interior decoupled from surface over 90-day run                                   |
| Biot number (ocean coupling) | ≫ 1 (200–200,000)                                | internal conduction limits basal heat flux                                        |
| **Lumped-model validity**    | Bi ≫ 1, τ ≫ run                                  | **single-node interior is an effective parametrization, not a physical solution** |

**Must document**: the interior temperature is an _effective bulk parameterization_; full profile not resolved; double-diffusive physics not represented.

---

## 3. Candidate Comparison (Phase A requirement §6)

| Criterion              | A: Single bulk node     | B: Interior active layer | C: Two-node (skin+interior) | D: Multi-layer |
| ---------------------- | ----------------------- | ------------------------ | --------------------------- | -------------- |
| Minimal change         | ✓                       | ~                        | ~                           | ✗              |
| No hidden tuning       | ~ (h_eff?)              | ✓ (h_eff=H-H_EFF)        | ✓ (d=H/2 derived)           | ~              |
| Energy conservation    | hard (Q source?)        | hard (Q source?)         | ✓ (conservative coupling)   | ✓              |
| Surface closure change | possibly                | possibly                 | yes (q_cond sink on skin)   | yes            |
| Matches physics        | poor (no skin coupling) | fair                     | good                        | best           |
| Regression safety      | switch OFF              | switch OFF               | switch OFF (q_cond=0)       | complex        |
| **Chosen**             |                         |                          | **C (two-node)**            |                |

**Decision**: **Variant C (two-node, energy-conserving)** with explicit conduction coupling `q_cond = 2 k_i (T_s − T_i)/H`. Rationale:

- Physically correct: skin↔interior conduction is the only energy pathway between atmosphere and interior
- No hidden parameters: `d = H/2` derived from layer-center separation (H_EFF + H_int)/2 = H/2 where H_int = H − H_EFF
- Conservative: `q_cond` leaves skin, enters interior; basal sensible `q_bot` exits interior
- Switch OFF ⇒ `q_cond=0`, `T_i = T_ICE_INIT` ⇒ bit-identical legacy
- Matches spec flow: `Q_surface → T_surface → q_cond → T_ice → basal closure → melt`

---

## 4. Chosen Design — Variant C (Two-Node, Conservative)

### 4.1 Definitions

| Symbol   | Meaning                                      | Units    | Formula / value                     |
| -------- | -------------------------------------------- | -------- | ----------------------------------- |
| `T_s`    | surface skin temperature (`state%T_surface`) | °C       | prognostic, existing                |
| `T_i`    | interior bulk temperature (`state%T_ice`)    | °C       | **new prognostic**                  |
| `H`      | total thickness                              | m        | `state%H`                           |
| `H_EFF`  | surface skin thickness                       | m        | 0.5 (constant, `iceberg_types`)     |
| `H_int`  | interior thickness                           | m        | `max(H − H_EFF, H_MIN_INT)`         |
| `C_s`    | skin capacity per area                       | J/(m²·K) | `ρ_i c_i H_EFF`                     |
| `C_i`    | interior capacity per area                   | J/(m²·K) | `ρ_i c_i H_int`                     |
| `k_i`    | ice thermal conductivity                     | W/(m·K)  | 2.2 (new constant)                  |
| `q_cond` | skin→interior conduction                     | W/m²     | `2 k_i (T_s − T_i) / H`             |
| `q_bot`  | interior→base sensible flux                  | W/m²     | `m_basal ρ_i c_i max(T_B − T_i, 0)` |
| `q_top`  | interior→skin conduction                     | W/m²     | `−q_cond` (equal/opposite)          |

### 4.2 Interior ODE (explicit forward Euler)

```
C_i  dT_i/dt = q_cond − q_bot
T_i^{n+1} = T_i^n + dt (q_cond^n − q_bot^n) / C_i^n
```

where:

- `C_i^n = ρ_i c_i H_int^n`
- `q_cond^n = 2 k_i (T_s^n − T_i^n) / H^n`
- `q_bot^n = m_basal^n · ρ_i · c_i · max(T_B^n − T_i^n, 0)`
- `m_basal^n`, `T_B^n` from `compute_basal_melt` using `T_i^n`

### 4.3 Surface skin coupling (energy-conserving)

At start of step n:

```
q_cond^n = 2 k_i (T_s^n − T_i^n) / H^n     [W/m², + = skin → interior]
Q_surface_eff^n = Q_surface^n − q_cond^n   [W/m²]
```

`compute_surface_melt` receives `Q_surface_eff` (or `q_cond` as additional sink) and runs **unchanged partition formulas** with reduced net energy. This is a _lagged_ explicit coupling; energy conserved to O(dt).

### 4.4 Step ordering (modified thermodynamics_step)

```
4a. compute_basal_melt(state, dt, ..., T_ice=state%T_ice)
    → m_basal, q_bot = m_basal * ρ_i * c_i * max(T_B - T_ice, 0)
4b. compute_lateral_melt
4c. q_cond = 2*k_i*(state%T_surface - state%T_ice)/state%H
    Q_eff = Q_surface - q_cond
    compute_surface_melt(state, atmos, diag, q_net, m_surface, dt, ..., q_internal_exchange=q_cond)
    → T_surface updated with Q_surface - q_cond
4d. C_i = RHO_ICE * C_ICE * max(H - H_EFF, H_MIN_INT)
    T_ice_new = T_ice + dt * (q_cond - q_bot) / C_i
    clamp T_ice_new to [T_ICE_MIN, T_ICE_MAX]
    state%T_ice = T_ice_new
```

Then geometry update uses m_basal, m_lateral, m_surface (unchanged).

### 4.5 Switch

```fortran
logical, save :: thermal_evolution_enabled = .true.
contains
subroutine set_thermal_evolution(enabled)
    logical, intent(in) :: enabled
    thermal_evolution_enabled = enabled
end subroutine
```

- When `.false.`: `q_cond = 0`, `compute_basal_melt` receives `T_ICE_INIT`, interior not updated → bit-identical legacy.
- Default: `.true.` (new production behavior). Regression tests call solvers directly with literals → unaffected.

**Implementation status (Stage 10.12 audit round):** the step-level gate is
implemented exactly as specified here — at OFF the step skips
`compute_iceberg_conductive_coupling`, calls `compute_surface_melt` WITHOUT
the optional `q_internal_exchange` argument (no subtraction), skips the
interior update, and defines the 10.12 diagnostics explicitly
(`t_ice = state%T_ice`, `dT_ice_dt = 0`, `c_eff_int = rho_i*c_i*H_EFF`,
`t_ice_bound = .false.`). Bit-identical legacy verified by test block
F.1–F.4 (surface budget bitwise-equal to a legacy call). Initial delivery
gated only the 3eq solver arguments — found and fixed before commit.

### 4.6 Temperature bounds

| Bound                | Value                                                                                                                        | Justification |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------- |
| `T_ICE_MAX = 0.0`    | physical melting point; interior cannot exceed melt temp; excess energy → internal melt (not modeled, documented limitation) |
| `T_ICE_MIN = -100.0` | broad numerical guard; coldest polar ice ~ -40 to -60 °C; -100 is a non-binding safety net                                   |

When clamped: set `diag%t_ice_bound = .true.` (new diagnostic flag).

### 4.7 Initial condition

```
T_ICE_INIT = -10.0  ! °C, model assumption (legacy)
iceberg_init:
    state%T_surface = T_ICE_INIT
    state%T_ice     = T_ICE_INIT
```

`T_ICE_INIT` is a _documented initial condition parameter_ (not a constant temperature). Renamed from `T_ICE` → `T_ICE_INIT` in `iceberg_types.f90`; `T_ICE` removed from public export.

### 4.8 Removed-ice enthalpy (Approach 1 — documented limitation)

When geometry shrinks (`H`, `L`, `W` decrease), the interior capacity `C_i = ρ_i c_i H_int` decreases. Temperature `T_i` is intensive and **held constant** during geometry update. The enthalpy of removed ice (`ρ_i c_i T_i ΔV`) is **not tracked** — documented as a known energy non-closure (Approach 1). No double counting with basal/surface schemes.

---

## 5. Procedure Architecture

New/Modified procedures in `iceberg_thermodynamics.f90`:

```
compute_iceberg_thermal_capacity(state)        ! → C_i, C_s
compute_iceberg_conductive_coupling(state, q_cond)  ! q_cond = 2*k_i*(T_s - T_i)/H
update_iceberg_internal_temperature(state, dt, q_cond, q_bot, diag)
```

`compute_surface_melt` signature change:

```fortran
subroutine compute_surface_melt(state, atmos, diag, q_net, m_surface, dt,
                                year, month, day, hour, q_internal_exchange)
    real, intent(in), optional :: q_internal_exchange
    ! Q_surface_eff = Q_surface - present(q_internal_exchange)? q_internal_exchange : 0.0
```

---

## 6. Diagnostics (new in `iceberg_diagnostics`)

| Field         | Units    | Moment                | When off                      |
| ------------- | -------- | --------------------- | ----------------------------- |
| `t_ice`       | °C       | after interior update | `T_ICE_INIT`                  |
| `dT_ice_dt`   | K/s      | after interior update | 0                             |
| `c_eff_int`   | J/(m²·K) | after capacity calc   | `ρ_i c_i H_EFF` (legacy skin) |
| `q_cond`      | W/m²     | after coupling        | 0                             |
| `q_bot`       | W/m²     | after basal           | 0                             |
| `t_ice_bound` | logical  | after clamp           | .false.                       |

---

## 7. Test Matrix

### 7.1 Fortran unit test: `test/iceberg_test_10p12_thermal_evolution.f90`

| ID   | Description                                  | Expected                           |
| ---- | -------------------------------------------- | ---------------------------------- |
| A.1  | Zero q_cond, zero q_bot → T_i constant       | `T_i(t) = T_0`                     |
| A.2  | Positive q_cond, zero q_bot → linear warming | `T_i = T_0 + q·t/C_i`              |
| A.3  | Negative q_cond, zero q_bot → linear cooling | `T_i = T_0 - q·t/C_i`              |
| A.4  | `T_i → 0` clamp                              | `T_i ≤ 0`                          |
| A.5  | `T_i → -100` clamp                           | `T_i ≥ -100`                       |
| A.6  | C_i varies with H                            | `dT/dt ∝ 1/H`                      |
| A.7  | H → H_MIN_INT                                | `C_i` bounded, no div/0            |
| A.8  | Negative/zero C_i guard                      | no NaN/Inf                         |
| A.9  | dt=0                                         | no update                          |
| A.10 | Large dt stability                           | no NaN/Inf, bounded                |
| A.11 | Repeatability                                | bit-identical repeated run         |
| A.12 | Units & signs                                | all J, m, s, K consistent          |
| A.13 | Basal coupling                               | `q_bot = m ρ_i c_i max(T_B-T_i,0)` |
| A.14 | Surface OFF switch                           | surface path unchanged             |
| A.15 | No double-count                              | energy balance to O(dt)            |
| A.16 | `T_i < T_B` case                             | sensible term active               |
| A.17 | `T_i = T_B` case                             | sensible term = 0                  |
| A.18 | `T_i > T_B` case                             | sensible term = 0 (max)            |
| A.19 | Switch OFF → legacy                          | bit-identical                      |

### 7.2 Python independent test: `python/tests/test_internal_thermal_evolution.py`

- Analytic check: `T(t) = T_0 + Q/C · t` for constant Q, no bounds
- Piecewise check for clamped case
- Vary dt, C_i, Q signs
- Compare relative error vs analytic

### 7.3 Regression (Phase A §14.3)

```
fpm test --flag "-I/usr/include" iceberg_test_10p10_three_equation       (25/25)
fpm test --flag "-I/usr/include" iceberg_test_10p11_natural_convection  (23/23)
conda run -n iceberg-thermodynamic-model python python/tests/test_three_equation.py            (65)
conda run -n iceberg-thermodynamic-model python python/tests/test_three_equation_natural.py    (70)
conda run -n iceberg-thermodynamic-model python python/tests/test_basal_melt_validation.py     (44)
conda run -n iceberg-thermodynamic-model python python/tests/test_observational_validation.py  (229)
conda run -n iceberg-thermodynamic-model python python/tests/test_calibration_assessment.py    (212)
```

Plus new controlled thermal-evolution test with fixed forcing.

---

## 8. File Changes (Phase A §8)

### 8.1 Production source (`src/`)

| File                         | Change                                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `iceberg_types.f90`          | add `T_ICE_INIT`, `T_ICE_MIN`, `T_ICE_MAX`, `K_ICE`, `H_MIN_INT`; rename `T_ICE` → `T_ICE_INIT`; add `T_ice` to `iceberg_state`; add diagnostics fields; add `thermal_evolution_enabled`, `set_thermal_evolution`                                                                                          |
| `iceberg_thermodynamics.f90` | modify `compute_surface_melt` signature (optional `q_internal_exchange`); add `compute_iceberg_thermal_capacity`, `compute_iceberg_conductive_coupling`, `update_iceberg_internal_temperature`; modify `compute_basal_melt` to accept `t_ice_in` from state; update `iceberg_thermodynamics_step` ordering |
| `iceberg.f90`                | `iceberg_init` initializes `T_ice = T_ICE_INIT`; `iceberg_step` calls new interior update after surface melt                                                                                                                                                                                               |
| `iceberg_geometry.f90`       | no logic change (geometry update unchanged)                                                                                                                                                                                                                                                                |

### 8.2 Tests

| File                                            | Status           |
| ----------------------------------------------- | ---------------- |
| `test/iceberg_test_10p12_thermal_evolution.f90` | NEW (19+ checks) |

### 8.3 Python validation

| File                                              | Status |
| ------------------------------------------------- | ------ |
| `python/tests/test_internal_thermal_evolution.py` | NEW    |

### 8.4 Documentation

| File                                                       | Update                               |
| ---------------------------------------------------------- | ------------------------------------ |
| `docs/validation/stage10.12_internal_thermal_evolution.md` | NEW (full report)                    |
| `docs/model/model_equation_ledger.md`                      | add §10.4 internal thermal evolution |
| `docs/model/model_physics_status.md`                       | add row, update limitations          |
| `docs/model/stage10_modernization_plan.md`                 | mark 10.12 complete                  |
| `docs/PROJECT_ROADMAP.md`                                  | update next stage priority           |
| `docs/references/references.bib`                           | add k_i source if new                |
| `docs/references/literature_matrix.md`, `citation_map.md`  | add 10.12 entries                    |
| `AGENTS.md`                                                | add Stage 10.12 summary              |

---

## 9. Limitations (explicit per spec)

| Limitation                                      | Status                                                     |
| ----------------------------------------------- | ---------------------------------------------------------- |
| Lumped two-node model (Bi ≫ 1)                  | **documented** as effective parametrization                |
| Thermal diffusion time ≫ run length for large H | **documented**; interior barely responds                   |
| No internal melt when T_i = 0                   | **documented**; clamp at 0, excess energy discarded        |
| Removed-ice enthalpy not tracked (Approach 1)   | **documented** as known non-closure                        |
| Lagged coupling (q_cond from step n)            | O(dt) energy error; documented                             |
| No double-diffusive physics                     | **documented**; separate future stage                      |
| Ice thermal conductivity k_i = 2.2 W/(m·K)      | model parameter (literature range 2.0–2.3); not calibrated |

---

## 10. Oracle Consultation Status

**Oracle task bg_29f63d05**: TIMED OUT after 30 min (system-reminder: error). Per spec §17: "Если среда не позволяет получить отдельное подтверждение архитектуры, допускается продолжить только после явной фиксации решения в отчёте." Decision fixed explicitly above (Variant C, lagged conservative coupling).

---

## 11. Phase A Complete — Ready for Review

**No production code changed**. All equations, bounds, switch, tests, file list, and limitations explicitly documented above. Ready for review before Phase B implementation.

---

**Next step upon approval**: Phase B implementation per this design note → tests → docs → regression → commit/push.
