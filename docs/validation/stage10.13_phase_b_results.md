# Stage 10.13 — Phase B Results: Diffusion-limited / double-diffusive low-flow closure (research prototype)

**Status**: Phase B complete (independent research prototype; NOT production).
**Baseline commit**: `acb9c7a` (Stage 10.13 Phase A design note)
**Date**: 2026-09-15
**Production code**: UNCHANGED (verified — no src/test/CI modifications from this phase).
**Commit policy**: no commit/push in Phase B.

Epistemic labels: `[source]` verified publication; `[repo]` production-consistent;
`[analytic]` derived here; `[inferred]` reasonable interpretation; `[unresolved]` open.

---

## 1. Status and commit baseline

- Phase B of Stage 10.13, research-only. HEAD `acb9c7a` (remote matches).
- Python prototype + analytical tests + coarse sweep + 10.8.2 re-scoring completed.
- Fortran production untouched; existing test suites NOT re-run (no source change).

## 2. Scope

- Independent implementation of the Phase A candidate C (hybrid closure).
- Mechanism separation (A pure diffusion / B DDC enhancement / C hybrid /
  D Stage 10.11 baseline) kept explicit in code and reporting.
- No calibration, no parameter fitting, no Ra_max change, no Fortran.

## 3. Changed files (Phase B)

| File | Status |
|---|---|
| `python/validation/low_flow.py` | NEW — prototype core (8 API functions + params + diagnostics) |
| `python/tests/test_low_flow.py` | NEW — analytical tests A–K (167 checks) |
| `python/validation/low_flow_sweep.py` | NEW — coarse sweep, CSV + figures |
| `python/validation/low_flow_scoring.py` | NEW — 10.8.2 re-scoring (reuses `observational_validation`) |
| `docs/validation/stage10.13_phase_b_results.md` | NEW — this document |
| Generated (gitignored under `data/`): `data/output/diagnostics/stage10.13/sweep.csv`, `fig_*.png` | NOT committed |

## 4. Prototype API

- `compute_density_ratio(t_w,t_b,s_w,s_b,params) -> (R_rho, dT, dS, warnings)`
  — Middleton convention `R_rho = alpha_T dT/(beta_S dS)`; dT<=0 → 0; dS floored
  at `dS_floor_psu` (explicit, warned).
- `compute_convective_velocity(t_w,t_b,params) -> w*` — `w* = (g alpha_T kappa_T dT)^(1/3)` `[analytic]`.
- `compute_richardson_star(...) -> (Ri*, w*, warnings)` — `Ri* = g beta_S dS delta_S / w*^2`; NO velocity floor.
- `compute_reynolds_b(u_rel,s_w,s_b,delta_s,params) -> Re_b` — `eps/(nu N^2)`, `eps = u_*^3/(k_vK delta_S)`;
  no floor: `Re_b -> 0` at U=0 naturally (design decision from test B.7).
- `compute_diffusive_sublayer(t,params) -> (delta_S, warnings)` — `max(delta_min, sqrt(kappa_S t))`,
  optional staircase cap; explicit time parameter.
- `compute_diffusive_melt_rate(t_w,t_b,delta_s,params) -> m_d [m/s]` — `k_w dT/(delta_S rho_i L_f)`.
- `compute_ddc_enhancement(r_rho,re_b,ri_star,params) -> (f, bounds)` — DC criterion
  `R_rho > kappa_S/kappa_T AND Re_b < 1` `[source: Middleton21]`; f in [1, f_dc_max=3.1];
  optional `ri_star` conjecture mode (sensitivity-tested).
- `compute_hybrid_low_flow(...) -> LowFlowResult` — full diagnostics + regime.
- `compute_hybrid_melt_rate(t_w,s_w,u,l_char,depth,params,t_b=None,s_b=None)
  -> (m_hybrid, low, m_forced, w, gamma_T_low, gamma_S_low)` — forced branch =
  `basal_melt.basal_melt_rate` (reference-compatible with 10.8.2 scoring);
  blending `w = cosine smoothstep over [u_trans_lo, u_trans_hi]`.
- `compute_effective_gammas(...) -> (gamma_T_low, gamma_S_low)` — inverts 3eq Eq. II;
  `gamma_S = gamma_T (K_S/K_T)` (convention; flux-ratio alternative `[unresolved]`).

## 5. Equations used (design note 7; NOT production)

```
delta_S = clip(max(delta_min, sqrt(kappa_S t)), cap)         [m]
m_d     = k_w max(T_w-T_B,0) / (delta_S rho_i L_f)           [m/s]
k_w     = rho_w c_w kappa_T  (~0.572 W/(m K))
f       = 1 or f_dc (2.5) when DC active; bounded [1, 3.1]
m_low   = f m_d
m_hyb   = w(U) m_forced + (1-w(U)) m_low,  w = 0.5-0.5cos(pi t)
```

## 6. Dimensionless numbers

| Group | Formula | Value (baseline) |
|---|---|---|
| Le | kappa_T/kappa_S | 100 (range 93–110) `[unresolved]` |
| R_rho | alpha_T dT/(beta_S dS) | 0.3 (dS=0.5 PSU) … 15 (dS=0.01 PSU) |
| Ri* | g beta_S dS delta_S / w*^2 | ~2.9 |
| Re_b | eps/(nu N^2) | 0 at U=0; >1 for U ≳ 8.5e-3 m/s |
| w* | (g alpha_T kappa_T dT)^(1/3) | ~4.4e-4 m/s |

## 7. Assumptions

- Local linear alpha_T/beta_S constants `[repo]` (EOS-80 variant `[unresolved]`).
- Sublayer growth law `(kappa_S t)^(1/2)` `[source: Middleton21]`; staircase cap `[inferred]`.
- Baseline diagnostic time 1 day; explicit parameter.
- dS floor 0.01 PSU for R_rho/N^2 regularization `[inferred]` (sensitivity-tested).
- T_B/S_B defaults: T_B = Tf(S_w, depth), S_B = S_w − dS_floor (quiescent limit) `[inferred]` —
  full 3eq iteration with gamma_low deferred to Phase C.
- No velocity floor anywhere (ε∝U³→0 at U=0) — decision from test B.7.

## 8. Parameter ranges (sweep)

T_w ∈ [1,8] °C; S_w ∈ [30,35] PSU; U ∈ [0, 0.1] m/s (6 pts); t ∈ [1 h, 10 d] (3 pts);
depth = L_char = 100 m draft convention as in 10.8.2 scoring. Grid 270 points (coarse).

## 9. Analytical tests (167/167 PASS)

Blocks A–K per spec: zero driving, zero velocity (incl. no-floor check B.7),
small-U continuity, sublayer growth (sqrt law, cap), positive melt, dT<=0,
enhancement bounds + diagnostics, forced preservation (hybrid == forced at U=0.5,
== basal_melt reference), transition continuity (max log10 jump 0.39 on fine grid),
parameter sensitivity (Le 93/100/110, K_S/K_T, delta_min, f_dc, time),
dimensional checks (m m/s, delta m, gamma m/s, q W/m², unit-closure identity).

## 10. Sweep design

Coarse grid (270 pts); four variants per point; NaN/Inf/negative scan; regime
counts; observed-band coverage; continuity on a fine U sub-grid
(0.1×–20× transition window).

## 11. Main results (m/day)

| Variant | min | median | max | in-band 0.01–1 |
|---|---|---|---|---|
| Stage 10.11 baseline | 9.5e-4 (cap floor) | 2.4e-2 | 1.02 | 135/270 |
| pure diffusive | 1.2e-2 | 8.3e-2 | 0.70 | 270/270 |
| DDC-enhanced | 1.2e-2 | 1.3e-1 | 1.74 | 246/270 |
| hybrid | 1.5e-2 | 1.3e-1 | 1.74 | 246/270 |

NaN/Inf: 0; negative: 0; max log10 jump (hybrid, fine grid): 0.66 (OK < 1).
Regime map: DC active for U ≤ 3e-3 m/s; diffusion-limited/f-forced above
(Re_b = 1 crossing at U ≈ 8.5e-3 m/s, inside the blending window — f-step
damped by (1−w) ≤ 0.07).

## 12. Comparison with Stage 10.11

- U=0: baseline floor 1.4e-3 (cap-determined, below band); hybrid 0.04–0.68
  (t-dependent) — in band. **The 10.11.3 gap is closed structurally** (mechanism,
  not Ra_max): 246–270/270 in band vs 135/270.
- U≥1e-2: hybrid == forced == baseline behavior (no regression).
- Mechanism separation: pure diffusive alone reaches the band (270/270) but
  underestimates the RH80 lab obs by 1.5–5.6×; DDC enhancement (2.5×) brings
  the ratio to 1.1–2.2× — consistent with MK77's ~2× and Keitzl's 2.5–3.1× `[source]`.

## 13. Stage 10.8.2 re-scoring

**u>0 rows (n=4, KW84+NJ80):** hybrid == baseline exactly (w=1, forced preserved)
— RMSE 0.108, bias +0.083 (unchanged). The pure/ddc columns there are
low-flow-branch diagnostics at forced conditions, NOT candidates; do not read
their lower RMSE as an improvement.

**Quiescent rows (n=5, RH80):**

| id | obs | 10.11 | pure | ddc/hybrid |
|---|---|---|---|---|
| RH_0C | 0.043 | 0 | 0.028 | 0.069 |
| RH_2C | 0.133 | 0 | 0.056 | 0.140 |
| RH_5C | 0.319 | 0 | 0.099 | 0.247 |
| RH_10C | 0.730 | 0 | 0.170 | 0.426 |
| RH_18C | 1.586 | 0 | 0.285 | 0.711 |

Gap closure: baseline 0/5 in band; pure/ddc/hybrid 5/5 in band; ddc/hybrid
within factor 1.1–2.2 of observations (t=1 d, NO calibration).
Not fitted validation: parameters are literature/repo values only.

## 14. Sensitivity

| Parameter | Range | Effect on m_low (U=0, dT≈3.9) | Note |
|---|---|---|---|
| Le | 93–110 | +9% | kappa_S/kappa_T threshold shift |
| K_S/K_T | 0.01–0.05 | gamma_S only | salt-flux convention `[unresolved`] |
| t_scale | 1 h–10 d | ×15 (0.68 → 0.044) | **dominant**; time-dependence `[unresolved]` |
| f_dc | 2.0–3.1 | ±25% | bounded, literature range `[source]` |
| dS_floor | 0.01–0.5 PSU | R_rho 15→0.3 (both > threshold) | DC stays active `[inferred]` |

## 15. Limitations

- Lumped/prototype: no time-dependent sublayer in production form; 1-day
  diagnostic time is a choice (`[unresolved]` time-dependence handling in 1-h timestep).
- Freshwater-based Keitzl scaling transferred to seawater — explicit assumption
  `[inferred]`; seawater evidence from MK77/Middleton (geometry consistent).
- Constant alpha_T/beta_S; EOS-80 variant deferred.
- T_B/S_B defaults are quiescent-limit estimates; full 3eq iteration in Phase C.
- no calibration claim: match within 1.1–2.2× obs; not a fit.

## 16. Acceptance criteria vs Phase C gate

| Criterion | Status |
|---|---|
| deterministic prototype | PASS |
| focused tests pass | PASS (167/167) |
| no NaN/Inf on sweep | PASS (0) |
| no negative melt in domain | PASS (0) |
| m→0 as dT→0 | PASS |
| finite at U=0 | PASS (physical, band) |
| forced branch preserved | PASS (hybrid == forced at w=1) |
| transition continuous | PASS (log10 jump 0.66 < 1) |
| f bounded & justified | PASS [source] |
| new params have units/ranges | PASS |
| Le/K_S-K_T/delta_S/time uncertainties documented | PASS |
| not a numerical fit | PASS (literature/repo values only) |
| 10.11 comparison explicit | PASS (gap closed structurally) |
| freshwater-to-seawater transfer flagged | PASS (documented) |
| Phase C formula decision | **CONDITIONAL** (see 17) |
| Phase C open questions list | see 18 |

## 17. Recommendation for Phase C

**Conditional GO for Fortran integration of the hybrid low-flow branch**, with
the explicit requirement to resolve (or explicitly freeze) before/at Phase C:
(a) the time-scale/delta_S representation (growing sublayer vs staircase cap —
the dominant sensitivity, ×15); (b) T_B/S_B iteration through the 3eq interface
with gamma_low; (c) the f_dc enhancement value (2.5 baseline, range 2.0–3.1).
Phase C should implement the selectable scheme with OFF = legacy bit-identity
(per Stage 10.12 pattern) and re-run the full battery + strict build; the
Stage 10.11 Ra-natural branch remains selectable and unchanged.

If (a) is deemed too uncertain, the safer path is **Phase C-deferred**: document
the time-dependent sublayer as out of scope for the 1-h timestep model and
integrate only the steady/1-day-diagnostic form with explicit flag — decision
needs the owner.

## 18. Unresolved questions (carry to Phase C / next phase)

1. Steady vs growing sublayer in 1-h timestep — dominant sensitivity `[unresolved]`.
2. Staircase cap value (0.05 m) `[inferred]`.
3. gamma_S flux-ratio (DC flux ratio vs K_S/K_T) `[unresolved]`.
4. alpha_T/beta_S EOS-80 state-dependence in R_rho `[unresolved]`.
5. Le baseline 100 vs Middleton 110 `[unresolved]` (sensitivity +9%).
f. epsilon/w* closure at finite U (buoyancy-driven w* `[inferred]`).
7. 3eq iteration with gamma_low (T_B/S_B self-consistency) `[unresolved]`.

**Found documentation bug (not fixed, per policy):** `three_equation_natural.py`
`__main__` shows the return of `three_equation_basal_melt_natural` as
`(t_b, s_b, m)`; the actual return is `(m, t_b, s_b)` (verified by direct call).
The validation module was not modified; flagged for a separate doc fix.