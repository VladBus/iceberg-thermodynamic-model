# Stage 11.5C.3 — T/S-Held Control and B200 Input/Gain Regression

Frozen (date). PURELY FORENSIC + diagnostic. No physics, EOS, CA,
advection, ice-dynamics, or numerical-scheme change; no MAX/MIN guards or
NaN clamps; B200/B210/txic/shal/CA/EOS untouched; production defaults
unchanged. Implementation: NEW module `src/stage115c3_ts.f90` + 13 call
sites in `app/main.f90` (use/init/gate-entry/2×B200/8×temporal-seq; all
env-gated, default OFF → early return).

## 1. Instrumentation (all OFF-default)

- `STAGE115C3_FREEZE_TS`: snapshot ONLY t1/s1 (3D, all k) at first
  gate-fire of day; restore each gate entry. Ice
  (hice/hsnow/an1/ans/u/v/txic) evolves FREELY — pure advectand-leg test
  (11.5C.2 FREEZE_HEAT froze ice too — NOT pure).
- `STAGE115C3_B200_REGRESSION`: B200 before/after at (112,17,9) +
  (112,18,9): U,V,RO,ΔRO (vs day-start RO), dRO/dx,dRO/dy, DPX,DPY,
  txic,tyic,ans,UP2,VP2 → ΔU,ΔV,gain,cell-ΔE →
  `b200_regression_112_17_9.csv` / `_112_18_9.csv` (columns exactly per
  spec). TW-proxy = c1·H·|∇hRO| (c1=981, H=map1, dx=1.389e6 — provenance
  param.f90:30, main.f90 c1=g/roc; NOT the true B200 integral —
  documented proxy; calibrated: TW×3600 s ≈ observed per-pass ΔU).
- `STAGE115C3_TEMPORAL_SEQ`: after each of the 8 substep checkpoints:
  |U|,|ΔRO|,TW-proxy,last-B200-gain (carry-forward, 0.0 pre-first-B200) →
  `temporal_sequence_*.csv` per cell (columns per spec).
- Field-architecture finding (code audit): advs reads S2 (fluxes) + S1
  (predictor base) and WRITES S2 (`advection_3d_s.f90:263`); CA operates
  on T2/S2 (`convective_adjustment.f90:418-419,454-455`). T2/S2 are the
  ocean prognostic fields; T1/S1 are heat outputs + predictor scratch.
  Freezing T1/S1 ≠ freezing ocean thermodynamics (limits TASK 1 — honest
  boundary below).

## 2. TASK 1/4 — Matrix (April N=24, realistic EN4 init, /tmp rebuilt+guarded)

| Exp | Setup | First event | Day-end maxU (d1→d3) |
|---|---|---|---|
| A ctrl | TRACE only | d3 s1 AFTER_CA RO=Inf (112,17,9) single cell — 4th deterministic reproduction | 316 → 4.8e7 → zombie |
| B TS-freeze | +FREEZE_TS+GAIN+REG+SEQ | d16 s14 AFTER_CA RO=Inf (106,15,6) single cell | d1 316 / d2 4.82e7 — IDENTICAL to A (4 digits) |
| C normal+diag | +GAIN+REG+SEQ | d3 s1, same as A (5th reproduction) | ≡A |

- Spec criterion (5 days): B is UNSTABLE at normal pace → **T1/S1
  evolution is NOT the fast-mode source**. Days-1–2 bit-level identity
  (316/4.82e7) proves the t1/s1 leg carries NOTHING of the growth phase
  (consistent with §1: advective fluxes from S2 + blown U dominate the
  predictor base).
- Kill delayed d3→d16: recorded honestly; both trajectories are
  nonphysical garbage from day 2 (maxU 4.8e7), and kill-timing inside
  blown state is chaotic-variance class (cf. D partial-vs-rerun) —
  NOT claimed as therapeutic effect.
- Subtractive logic vs 11.5C.2-C2 (full ice+thermo freeze BOUNDS
  momentum): C2's active ingredient is NOT t1/s1 (no-op here) NOR
  txic/tyic/ans (no-op in 11.5C.1) → it lies in the JOINT ice-state set
  {hice,hsnow,an1,wices,hices,u,v} evolving together — exact leg
  UNISOLATED (candidates: B210 surface-gain set by hht denominator with
  evolving ice; heat k=1 forcing stationarity; ice-dynamics trajectory).
  Proposed single-field freezes (ice-u/v only; hice/ans only) for 11.5D.

## 3. TASK 2/3 — Regression + temporal order (C run, event cell)

- Phase 1 (d1): |U| 0→154 with |ΔRO| 0→1.5e-4 (flat), TW 3e-5→2.6e-2.
  U leads by 3–4 orders → **Variant B (U first)**.
- Phase 2 (d2s12→s24): |ΔRO| 5e-3→8.7e-3, TW 0.11→0.45 → B200 pass:
  |U| 361→4.57e6 (gain ×12641), |ΔRO|→3.3e-2 → **Variant A locally
  (RO/TW threshold → gain detonation)**. AFTER_B280 further ×4.8.
  Threshold character: TW-proxy ~O(0.5–3) [cm/s²] × 3600 s ≈ observed
  kick — calibrated, not fitted.
- Quiet-cell control (B run seed, blowup elsewhere): gain 0.2–2.2
  uncorrelated with flat dRO/TW (4e-5/3e-4); log-correlations over 696
  passes: gain-dRO 0.35, gain-TW 0.36, gain-txic 0.33, gain-UP2 0.19,
  gain-DPX −0.22 — weak (690 quiet passes dilute); top gains coincide
  with max |dRO|. No linear master variable → threshold/nonlinear
  detonation (**Variant D character**).
- UP2 background ramp 1e3→1e5 (barotropic spin-up, all runs) — present
  but uncorrelated with gain (0.19); Scenario C (barotropic-driven)
  NOT supported as primary (B280 imprint is co-amplifier, 11.5C.2).
- Two-phase synthesis: phase-1 linear ramp (repeated quasi-steady
  B200+B280 increments, 24 passes vs legacy 1 — FORCING-cadence effect,
  needs evolving ice-state per §2) → phase-2 advective T/S corruption →
  RO/TW threshold → B200 gain explosion → CA RO=Inf → B200 spreads Inf.
  = **Variant B globally → Variant A locally, i.e. Variant D with
  resolved order.**

## 4. TASK 5 — Classification: **Variant D (two-phase B→A)**

- Variant A alone: NO (U leads globally day 1 with RO flat).
- Variant B alone: NO (RO/TW threshold gates the explosion; freezing
  joint ice-state bounds phase 1).
- Variant C alone: NO (UP2-gain correlation 0.19; shal dE≡0).
- Variant D: YES — ordered two-phase feedback (phase-1 cadence ramp
  needs joint ice-state evolution; phase-2 RO-gated B200 detonation).
  B200 remains the dominant ENERGY injector (11.5C.2: +3.9e6/pass) but
  "primary generator" counterfactually is the JOINT evolution — no
  single field/operator is THE switch. Consequence: single-point fixes
  (txic clamp, t1/s1 damping, B200-only review) are predicted
  INSUFFICIENT; 11.5D must address the coupling STRUCTURE (explicit
  sequential ice→heat→ocean splitting at 24×/day).

## 5. Implications for 11.5D (promotion still BLOCKED)

1. Do NOT promote N=24 (unchanged).
2. Next forensic (diagnostic-only, proposed): single-field freezes
   (ice-u/v only; hice/ans only) to isolate C2's active ingredient;
   T2/S2-held run is MEANINGLESS (freezes the ocean itself — noted so
   nobody reruns this blind alley); B200-gain-vs-TW regression over the
   detonation window (quantify threshold).
3. Structural directions (NOT approved): substep-aware splitting
   (ice/heat/ocean co-stepping or CA-per-day), B200 thermal-wind review
   per RULES procedure.
4. Artifacts: runs `stage11.5C3_AprA_ctrl/AprB_tsfreeze/AprC_reg`
   (+`stage11.5C3_janOFF`); per-run trace/gain/energy/regression×2/
   temporal×2 CSVs; env as in 11.5C.2 §8 + STAGE115C3_*.

## 6. Files changed (this stage)

- NEW `src/stage115c3_ts.f90` (FREEZE_TS + B200 regression + temporal
  seq; OFF → early return).
- `app/main.f90`: `use`, `s115c3_init()`, `s115c3_gate_entry()`,
  2× `s115c3_b200`, 8× `s115c3_seq` (additive calls only; physics
  untouched).
- Docs: this file (NEW); `docs/validation/INDEX.md` (11.5C.3 row);
  `docs/PROJECT_ROADMAP.md` (11.5C.3 status).
- Verification: Jan OFF (`stage11.5C3_janOFF`, 30 d / 32 files)
  md5-identical to `stage11.5C_janOFF` across ALL 32 outputs (final
  binary, no env); full fpm battery (see commit validation).
