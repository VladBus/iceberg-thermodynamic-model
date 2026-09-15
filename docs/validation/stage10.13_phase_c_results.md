# Stage 10.13 — Phase C Results: Production Integration of the Low-Flow Closure

**Status**: Phase C COMPLETE (production integration, selectable, OFF by default).
**Baseline commit**: `8bc1216` (Phase B results); HEAD uncommitted working tree at time of writing.
**Date**: 2026-09-15
**Commit/push**: not performed by agent (per Phase C policy).

Epistemic labels: `[source]` verified publication; `[repo]` production-consistent;
`[analytic]` derived here; `[inferred]` reasonable interpretation; `[unresolved]` open.

---

## 1. Objective

Integrate the Phase-B hybrid low-flow closure (diffusion-limited sublayer +
double-diffusive enhancement + smooth transition to forced flow) into the
production Fortran basal-melt path behind an explicit switch, OFF by default,
preserving legacy behavior and the three-equation interface.

## 2. Starting point

Phase B (`8bc1216`): research prototype `python/validation/low_flow.py`
(167 analytical checks PASS; 270-point sweep: hybrid 246/270 in the observed
band; 10.8.2 re-scoring: quiescent rows 5/5 in band). Accepted for controlled
integration.

## 3. Production implementation

| File | Change |
|---|---|
| `src/iceberg_types.f90` | named constants + regime codes + switch `low_flow_closure_enabled` (OFF) + setter; 14 diagnostic fields; 7 pure helper functions (`low_flow_delta_s`, `low_flow_density_ratio`, `low_flow_reynolds_b`, `low_flow_richardson_star`, `low_flow_enhancement`, `low_flow_blend_weight`, `low_flow_regime_value`) |
| `src/iceberg_thermodynamics.f90` | `compute_basal_melt`: optional `diag` arg + low-flow branch in the THREE_EQUATION scheme; new `solve_three_equation_interface_low_flow` (Picard iteration over γ_low, blended γ, then existing 3eq solver); `solve_three_equation_interface`: legacy zero-flow guard preserved, new optional `allow_zero_flow` (low-flow passes `.true.`) |
| `fpm.toml` | registered `iceberg_test_10p13_low_flow` |

Reused existing constants (NOT duplicated): `THERMAL_CONDUCTIVITY` (→κ_T),
`LEWIS_NUMBER=100` (→κ_S), `KINEMATIC_VISCOSITY`, `THERMAL_EXPANSION_COEFF`,
`HALINE_CONTRACTION_COEFF`, `CP_SEAWATER`, `CD_WATER`, `VON_KARMAN`, `GRAVITY`,
`THREE_EQ_KT/KS`, `RHO_ICE_WATER_RATIO`, `MELT_RATE_MIN`.

## 4. Mathematical formulation

```
delta_S = clip(max(delta_min, sqrt(kappa_S * t_scale)), delta_max)     [m]
kappa_T = THERMAL_CONDUCTIVITY/(rho_w c_w);  kappa_S = kappa_T/LEWIS_NUMBER
k_w     = rho_w c_w kappa_T
R_rho   = alpha_T dT / (beta_S dS_psu)                     (Middleton)
Re_b    = eps/(nu N^2),  eps = (sqrt(C_D_w) U)^3/(k_vK delta_S),  N^2 = g beta_S dS_psu/delta_S
w*      = (g alpha_T kappa_T dT)^(1/3);  Ri* = g beta_S dS_psu delta_S / w*^2
f       = LOW_FLOW_F_DC (=2.5)  if (R_rho > 1/Le AND Re_b < 1), else 1
w       = cosine smoothstep(U; U_low, U_high)
gamma_T_low = f k_w (L_f + c_i max(T_B - T_i, 0)) / (delta_S rho_w c_w L_f)   [m/s]
gamma_S_low = gamma_T_low (K_S/K_T)
gamma_T_eff = (1-w) gamma_T_low + w gamma_T_forced      (same for S)
m           = solve_three_equation_interface(gamma_T_eff, gamma_S_eff)   [m/s]
```
dS_psu uses the regularized `S_w − dS_floor_psu` (Python-reference convention);
the 3eq solver's own interface freshening (S_B → ~16 PSU at low U) reduces the
interfacial dT — this is the established 3eq behavior (present in the forced
branch too) and is the main systematic difference vs the Python far-field m_low.

## 5. Parameter values (all named, with units)

| Constant | Value | Units |
|---|---|---|
| `LOW_FLOW_TIME_SCALE_S` | 86400.0 | s (research parameter; dominant sensitivity) |
| `LOW_FLOW_DELTA_MIN_M` | 1.0e-4 | m |
| `LOW_FLOW_DELTA_MAX_M` | 5.0e-2 | m (staircase cap) |
| `LOW_FLOW_F_DC` | 2.5 | — (range 2.0–3.1 `[source]`) |
| `LOW_FLOW_DS_FLOOR_PSU` | 1.0e-2 | PSU |
| `LOW_FLOW_U_LOW / U_HIGH` | 1.0e-3 / 1.0e-2 | m/s |
| `LOW_FLOW_MAX_ITER` / `LOW_FLOW_TOL` | 4 / 1e-6 | — |
| κ_T / κ_S (derived) | 1.371e-7 / 1.371e-9 | m²/s (Le=100 repo convention) |

## 6. Regime logic

```
U → regime → closure → three-equation solution

U >= U_high            → w=1 → forced (γ = γ_forced)             regime 1
U_low < U < U_high     → 0<w<1 → blended γ                       regime 4
U <= U_low, DC active  → w=0, f=2.5 → γ_low(DC)                 regime 3
U <= U_low, no DC      → w=0, f=1 → γ_low(diffusion-limited)    regime 2
dT <= 0                → m=0 (outer delta_t guard)               regime 5 (unreachable in production)
switch OFF             → legacy path unchanged                   regime 0
```

## 7. Three-equation coupling

The low-flow branch modifies ONLY the effective transfer coefficients
γ_T/γ_S; the existing `solve_three_equation_interface` (H&J99/J2010, EOS-80
freezing point, mass-conserving salt balance) remains the governing solver.
Blending at the transport level (not final melt rates) is the Phase-C
decision: it keeps T_B/S_B/m mutually consistent (single solve), avoids
double counting, and reduces to the exact forced branch at w=1
(verified bit-identical). A minimal Picard loop (≤4 iterations, tolerance
1e-6 relative on m) updates the conduction term in γ_low; deterministic
fallback to the forced branch on NaN; convergence flag in diagnostics.

## 8. Numerical safeguards

No velocity floor (ε ∝ U³ → 0 at U=0, Phase-B decision preserved); δ_S floored
`[δ_min, δ_max]`; dS floored; γ ≤ 0 → m=0; NaN fallback; non-negative m by
construction; `allow_zero_flow` scoped to the low-flow path only (legacy
zero-flow contract of the shared solver unchanged).

## 9. Diagnostics (new fields in `iceberg_diagnostics`)

`low_flow_enabled`, `low_flow_active`, `low_flow_regime` (0–5), `low_flow_u_rel`,
`low_flow_re_b`, `low_flow_ri_star`, `low_flow_r_rho`, `low_flow_delta_s`,
`low_flow_delta_t`, `low_flow_f`, `low_flow_gamma_t`, `low_flow_gamma_s`,
`low_flow_iter`, `low_flow_converged`. Defined (zero/legacy values) even when
the switch is OFF.

## 10. Test results

| Suite | Result |
|---|---|
| Fortran focused `iceberg_test_10p13_low_flow` | **23/23 PASS** (A legacy OFF, B U=0 activation, C transition smoothness, D forced preservation, E DDC criterion, F bounds, G 3eq consistency, H CMP output, I determinism) |
| Python reference `test_low_flow.py` | 167/167 PASS (unchanged) |
| Python/Fortran comparison | **56/56 PASS** (10 points; f, regime, δ_S <10%, m at low flow <0.05 m/day abs) |
| Full Fortran battery | **exit 0** (10p10 25/0, 10p11 23/0, 10.12 21/0, 10.13 23/0, all others pass; ice_init_test graceful SKIP) |
| Python regression suites | 7/7 PASS (65+70+44+229+212+35+167 checks) |
| Build / strict build | PASS / PASS (0 warnings, 0 errors) |

## 11. Python-vs-Fortran comparison

`python/validation/low_flow_fortran_comparison.py` — 56 checks on 10 points:
f and regime match exactly; δ_S rel. diff 4.4% (κ_S convention: repo Le=100
gives 1.371e-9 vs Python 1.5e-9 — documented systematic); m at U≤1e-3 within
0.05 m/day absolute (interface freshening reduces the Fortran 3eq m vs the
Python far-field m_low — documented; e.g., P1: 0.1065 vs 0.1414 m/day).
High-U: Fortran ON == OFF asserted inside the Fortran test (forced
preservation); cross-language high-U comparison not applicable (Python hybrid
uses the bulk forced closure — a different validated formulation).

## 12. Legacy OFF comparison

Verified: OFF → `compute_basal_melt` takes the exact legacy branch
(bit-identical to the reference `solve_three_equation_interface` call at
U=0.1, rel < 1e-6; A.1); diagnostics defined; 10p10 B.1 legacy zero-flow
contract restored via `allow_zero_flow` default `.false.`.

## 13. Forced-flow preservation

Verified: at U=0.1 (above `U_high`), low-flow ON == OFF **bit-identical**
(D.1); regime=forced (D.2); full battery (incl. 10p10 25/0 and 10.12 21/0)
passes unchanged.

## 14. Known limitations

1. t_scale (1 day) is a research parameter; dominant sensitivity (Phase B:
   ×15 over 1 h–10 d) `[unresolved]`.
2. f_dc = 2.5 fixed (2.0–3.1 range); not calibrated.
3. κ_S convention (Le=100 derived) differs 4.4% from the Python reference
   κ_S = 1.5e-9 — repo-consistent, documented.
4. Interface freshening reduces the 3eq-coupled m vs the Python far-field m_low
   (~25–30% at U=0) — inherent to the three-equation salt balance at low γ_S;
   documented systematic difference.
5. γ_S = γ_T·(K_S/K_T) convention inherited; DC flux-ratio alternative
   `[unresolved]`.
6. EOS-80 α/β constant; `[unresolved]` state-dependent variant.
7. Low-flow applies only in the `BASAL_MELT_SCHEME_THREE_EQUATION` scheme
   (natural-convection scheme unchanged; selecting NATURAL + low-flow leaves
   the low-flow branch inactive — documented behavior).
8. T_B/S_B iteration limited to the conduction term (γ_low is dT-independent
   by construction); full outer 3eq iteration deferred.

## 15. Scientific interpretation

Stage 10.13 is a **research parameterization**, not universal physics. The
production hybrid (a) provides a finite, physically motivated quiescent melt
in the observed band (U=0 → 0.107 m/day at T=2°C/S=35 PSU vs the 10.11
cap-floor 1.4e-3), (b) preserves the three-equation interface and the forced
branch exactly, (c) is OFF by default. It does NOT claim validation: the
matching of RH80 lab observations within factor 1.1–2.2 (Phase B) is not
fitted, and the dominant uncertainty (t_scale) is exposed, not hidden.

## 16. Files changed

- `src/iceberg_types.f90` (+180)
- `src/iceberg_thermodynamics.f90` (+152/−5)
- `fpm.toml` (+4)
- `test/iceberg_test_10p13_low_flow.f90` (NEW)
- `python/validation/low_flow_fortran_comparison.py` (NEW)
- `docs/validation/stage10.13_phase_c_results.md` (NEW — this file)
- `docs/PROJECT_ROADMAP.md` (status update)

## 17. Commit information

Not committed by agent (per Phase C policy). Suggested message:
`stage10.13: integrate low-flow closure (diffusion-limited + DDC) behind switch, OFF by default`.