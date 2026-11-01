# Stage 12.7b — Autonomous Voxel Air Balance

**Status:** COMPLETE (energy closure <1%; voxel decoupled from bulk Q_net).
**Date:** 2026-11-01
**Decision:** D-61
**Base:** `65c97f9`

## 1. Motivation

Before 12.7b, exposed voxel faces used `atmos_Q = diag%q_net_surface` from the
legacy bulk surface balance. That coupled the voxel model to bulk
thermodynamics and made an autonomous voxel energy budget impossible. The bulk
model is now archived for regression (D-61), so the voxel must compute its own
atmospheric fluxes.

## 2. Implementation (PDF §7.1–7.10)

New `voxel_air_flux_components` in `src/voxel_thermal_solver.f90`:

```text
SW_abs = (1 - α_ice) · SW_down · χ_sky          χ_sky = 1 (horizontal), 0.5 (vertical)
LW_net = ε σ (T_air⁴ − T_s⁴) + (1 − ε) LW_down
SH     = ρ_air c_p C_H U (T_air − T_s)
LH     = ρ_air L_s C_E U (q_air − q_sat(T_s))
```

- `T` is converted to K inside; `q_sat` uses the Tetens ice formula
  (`610.78 Pa`, `21.875`, `7.66`).
- The matrix uses a first-order linearization around `T^n`:
  `Q(T) ≈ Q0 + (dQ/dT)(T−T^n)`, with `dLW/dT = −4εσT³`,
  `dSH/dT = −ρ c_p C_H U`, and `dLH/dT` from a finite-difference
  `dq_sat/dT`. The derivative is added to the diagonal and `Q0 − dQ/dT·T^n`
  to the RHS (Robin BC).
- `SW_down`, `LW_down`, `T_air`, `q_air`, `ρ_air`, `U`, `p_atm` are computed in
  `compute_atmos_inputs` in `src/iceberg_thermodynamics.f90` from the existing
  solar/atmospheric parameterizations. The voxel no longer reads
  `diag%q_net_surface`; `voxel_model_step` passes `atmos_Q = 0` and
  `autonomous_air=.true.`.
- Legacy callers/tests that omit the optional arguments keep the old
  `atmos_Q + h_s(T_air−T)` path.

## 3. Test — `test/test_voxel_air_balance.f90`

Case: `T_s=−10 °C`, `T_air=0 °C`, `U=5 m/s`, `SW=200 W/m²`, `LW=300 W/m²`,
`q_air=0.003`, `ρ_air=1.3 kg/m³`.

| Component | Value (W/m²) |
| --------- | -----------: |
| SW_abs | 60.000 |
| LW_net | 51.435 |
| SH | 97.890 |
| LH | 38.901 |
| **Total** | **248.227** |
| Analytical total | 248.227 |

Relative closure error `< 1e-6` (requirement <1%). A 1-voxel CN step with the
same forcing warms from −10.000 to −9.749 °C (`converged=.true.`, 1 PCG
iteration), confirming the Robin boundary is active.

## 4. Integration and limitations

- `VOXEL_ENABLED` remains default OFF for regression; science runs must set it
  ON explicitly.
- No atmospheric stability correction (neutral `C_H/C_E`), no wave/sea-spray,
  no sea-ice concentration in the voxel. `χ_sky` is a simple horizontal/
  vertical split.
- The bulk code still computes its own surface balance for the legacy path;
  that result is not used by the voxel.
- Bulk thermodynamics is **ARCHIVED**: all new science runs use
  `VOXEL_ENABLED=ON`; bulk is retained only for regression tests.

## 5. Artifacts

- Source: `src/voxel_thermal_solver.f90`, `src/voxel_iceberg.f90`,
  `src/iceberg_thermodynamics.f90`
- Test: `test/test_voxel_air_balance.f90`
- Decisions: D-61
- Related audit: `docs/validation/stage12.7.audit_voxel_melt.md`
