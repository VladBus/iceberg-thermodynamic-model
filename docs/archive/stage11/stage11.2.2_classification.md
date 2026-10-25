# Stage 11.2.2 — Causal Instability Classification (D-20 / D-21 closure)

**Status**: Diagnostic classification based on B (CA audit), C (density quant), D (timeline) with concrete evidence from `convective_adjustment.f90`, `build_initial_ts.py`, audit reports (`stage10.21_*`, `stage10.22_*`, `stage11.1_*`, `stage11.2_*`).
**Constraint (per 11.2.2 report)**: NO physics changes; NO production modification; classification only.

---

## Classification of major hypotheses (per Section 16 of 11.2.2 report)

### 1. CA guard as root cause of complete ocean instability
**Status: REJECTED**
- Evidence (B audit): float32 2⁻²³ (1.19e-7) > eps_density (0.9e-7) explains CA guard saturation (1000 iters) — STRONGLY SUPPORTED for CA mechanism.
- Evidence (C audit): float32 ULP (1.19e-7) ≪ ro_min (-20.07) → float32 CANNOT explain the zombie-state density inversion.
- Evidence (D timeline): Day 0 EN4 already has ro_min = -20.07 (Apr/Jul/Oct) → crash Day 1, before CA can act as primary cause; Jan (ro_min = 0.0) survives 4 days → CA acts as downstream symptom, not root trigger.
- Evidence (10.22 audit): eliminating CA residual (f64 EOS, raised thresholds) does NOT stabilize ocean — ALL closures diverge density-first mid-day-5 (A0=55, C=56 steps executed vs acceptance 360).
- Evidence (11.2 audit): CFL ≪ 1 at all times — instability NOT CFL-driven.
- **Conclusion (per Section 12 of 11.2.2)**: CA guard = symptom, NOT cause. REJECTED as root-cause explanation of zombie state.

### 2. Float32 EOS quantization as CA-guard mechanism
**Status: STRONGLY SUPPORTED**
- Evidence (`convective_adjustment.f90` line 60-63): 2⁻²³ ≈ 1.19e-7 > 0.9e-7.
- Evidence (line 121, `eckart_ro`): float32 EOS evaluation.
- Evidence (`convect_column_f64`, lines 295, 318-323): f64 EOS + f64 mixing eliminates guard (line 351-352: "guard_hit ожидаемо всегда FALSE" in f64 path).
- Evidence (10.21 audit): f64 experiments (EXP-A: 147-238 iters, guard 0 days 1-4) confirm quantization is the CA-residual floor.
- **Caveat**: Only explains CA residual; does NOT explain zombie-state divergence (see #1). Per 11.2.2 Section 4/13: do NOT switch EOS in production without full stability verification.

### 3. Float32 EOS quantization as complete ocean-instability root cause
**Status: PLAUSIBLE BUT UNPROVEN (for zombie-state chain beyond CA)**
- Evidence (C audit): float32 explains CA residual (STRONGLY SUPPORTED) but CANNOT explain ro_min = -20.07 (REJECTED for initial-condition pathology).
- Evidence (D timeline): zombie chain is CA/EOS density corruption (T-01) → thermal-wind transmission (B200) → amplification (B210) → NaN/Inf. Float32 contributes to the initial density corruption (ρ-flip diag 10.4M cells day 3 per 10.22) but does NOT fully account for the -20.07 initial state.
- Evidence (10.22): all f64 closures (A/C/D) still diverge → float32 removal does NOT eliminate the upstream Block-200/210 chain.
- Evidence (11.2 CFL audit): CFL ≪ 1 at instability event → conventional CFL violation REJECTED.
- **Classification**: PLAUSIBLE for CA-residual component; UNPROVEN (partially REJECTED for initial-state component) as complete zombie-state explanation.

### 4. Density → thermal wind → Block 200 transmission → velocity
**Status: CONFIRMED (causal chain isolated)**
- Evidence (10.22 audit, D-20): replay experiments a2 (freeze_thermal_wind) confirm Block 200 is TRANSMITTER (ro-phase-only metrics fail; momentum metrics PASS — worst rel 2.954e-1 d9).
- Evidence (D timeline): Day 5 s6: first NaN `CA_after ro_nan=198` at `F_after_conv` (CA block) → B200 transmits density/thermal-wind to momentum (`u2/v2_nan=333`) → B210 amplifies (rhs_max 1.12608E+16 → zombie 142,081).
- Evidence (11.2 audit): vertical CFL Cz = 0.105 < 1; horizontal CFL Ch = 0.038 < 1 — no CFL violation at event.
- **Conclusion**: Chain confirmed; source is upstream of CA (density/thermal-wind), not CA itself.

### 5. CA guard saturation (1000 iterations) as indicator of numerical instability
**Status: STRONGLY SUPPORTED**
- Evidence (10.21 audit): CA guard hits = all wet cells from day 6; maxiter = 1001; resid_inv = 1.1921E-07 = 2⁻²³.
- Evidence (11.2.2 Section 5/2): CA must be understood — convergence criterion (`resid < eps_density`), mixing algorithm (volume-weighted T/S averaging), update sequence (bottom-up scan), guard mechanism (`iter > 1000`), residual inversion tracking.
- Evidence (`convective_adjustment.f90`): guard is structural (line 204: `if (iter_count .gt. 1000) exit`); residual tracking available (`o_resid_inv`, line 148, 232-237).
- **Note**: Per 11.2.2 Section 2/5: do NOT increase iteration limits without understanding convergence criteria.

### 6. Block 210 amplification (Thomas solver)
**Status: CONFIRMED (structural, not pathology)**
- Evidence (10.22 audit): Thomas pivots negative by construction (`a1 = -1+a+b < 0`; piv_neg = piv_cnt = 100 %; piv_min = 1.0 — line 309 of audit; Section 2/3).
- Evidence (D timeline): B210 rhs_max 1.12608E+16, den_min 7.05833E-04 → amplification of B200-transmitted NaN into full zombie state (142,081 cells).
- Evidence (10.20 audit): density-first divergence (NaN at `CA_after` day 5 s6, 0 NaN in U/V/T/S at instant — B210 amplifies downstream).
- **Note**: Per 11.2.2 Section 6: negative pivots are structural, NOT a bug requiring correction.

### 7. CFL violation at instability onset
**Status: REJECTED**
- Evidence (11.2 audit): all explicit CFL metrics ≪ 1 (Cx=0.023, Cy=0.015, Ch=0.038, Cz=0.105, Cwave=0.663, f·DT=0.523, Dh=0.014).
- Evidence (11.2.2 Section 11): must verify CFL specifically at first-invalid event (not 90-day global max); preliminary 90-day data shows no significant CFL spike.
- Evidence (11.1 audit): seasonal dependence (Jan 4 days, Apr/Jul/Oct Day 1) is consistent with EN4 initial-state pathology, not CFL sensitivity.
- **Conclusion**: Conventional explicit-operator CFL violation REJECTED as trigger.

### 8. Timestep size (DT/DT1) as causal factor
**Status: UNPROVEN / PENDING (11.3 deferred)**
- Evidence (11.2 audit): timestep sensitivity matrix (5 experiments B–E) defined but NOT EXECUTED (default `STAGE113_*` switches OFF; `DT`/`DT1` hardcoded in `main.f90`: dt1=120.0, dt=3600.0).
- Evidence (11.2.2 Section 14): Stage 11.3 deferred until CA/density ambiguity resolved.
- Evidence (AGENTS.md): `STAGE113_*` environment mechanism not implemented.
- **Conclusion**: PENDING — deferred per 11.2.2 Section 14; not yet tested.

### 9. EN4 initialization pathology (initial state)
**Status: STRONGLY SUPPORTED**
- Evidence (11.1 audit): Apr/Jul/Oct EN4 initial state has `ro_min = -20.07 g/cm³` (pre-existing); frozen-ocean control (30 d stable, ro 0.0075–0.0082) proves atmosphere alone does NOT cause crash.
- Evidence (10.20 audit): full-coverage ERA5 file adopted (`era5_2020_01_fullcoverage_merged.nc`, 124 slices) — CASE C resolved (3-day gate PASS); residual instability (CA guard, density-first divergence) remains UNFIXED.
- Evidence (`python/ocean/build_initial_ts.py`): nearest-neighbor interpolation + vertical piecewise-linear regridding (`vertical_regrid` line 151-201; `eckart_ro` line 121); identical `ro_min = -20.07` across seasons suggests systematic processing error, not seasonal oceanography.
- **Note**: Per 11.2.2 Section 13: EN4 fix is NOT executed (no physics change; `docs/validation/stage11.4_en4_stabilization.md` = SETUP ONLY).

---

## Final recommendation (per 11.2.2 Sections 13–16)

**No production physics change at this stage.** Classification completed; diagnostic evidence sufficient for controlled-stage decision. Recommended order:

1. **A/I (CSV/CFL-at-event)** — verify diagnostic output integrity and compute CFL at first-invalid event (confirms/rejects 11.2 global conclusion).
2. **H (timeline)** — formalize timeline with first-invalid events (Day/III coordinates, variable names).
3. **G (W verification)** — confirm corrected W produces finite, physically ordered values (post-`end if` fix at `main.f90:868`).
4. **E/F (wind_max/euu)** — trace `wind_max` and `euu` definitions in `main.f90`; establish physical/mathematical meaning.
5. **11.3 timestep sensitivity** — deferred; requires approved physics-stage decision.
6. **11.4 EN4 stabilization** — deferred; requires approved physics-stage decision (D-21 from 11.1; `docs/validation/stage11.4_en4_stabilization.md` = SETUP).
