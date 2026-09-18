# Stage 10.17 — Iceberg Melt and Thermodynamic Budget Audit

**Date:** 2026-09-18
**Status:** COMPLETED (audit; no physical correction)
**Branch:** `main`
**Baseline commit:** `d48c9de` (user README update; contains Stage 10.16 `b4d62bf`)
**Resulting commit:** (Stage 10.17, pushed to `origin/main`)

---

## 14.1 Scope

This stage is:

- an **audit of the existing melt and thermodynamic-budget calculations** (basal,
  lateral, surface, vapor; mass–volume–geometry consistency; component budget;
  thermal/energy budget);
- a **follow-up to Stage 10.16** (drift investigation; melt is assessed
  separately, without mixing with drift dynamics);
- focused on the questions: *how does the model melt, is mass/geometry internally
  consistent, which mechanism dominates, is the observed mass loss numerically
  stable and physically interpretable, what evidence is still required before
  long-term use*;
- **not** a calibration stage;
- **not** observational validation;
- **not** a new-physics stage (no parameterization was introduced or changed);
- **not** production-path integration;
- **not** ocean NaN/zombie stabilization.

No physical equation, default configuration, or melt parameterization was
modified. Two Fortran tests, two Python files, and one live test extension
were added (diagnostics only).

## 14.2 Baseline

| Item | Value |
| --- | --- |
| Branch | `main` |
| HEAD at start | `d48c9de` (user README commit: banner/shields/docs) |
| `origin/main` | `d48c9de` (HEAD == origin/main; clean working tree) |
| Stage 10.16 | `b4d62bf` present; **T-07 PARTIALLY EXPLAINED**, OPEN |
| T-13 | RESOLVED (Stage 10.15.2 `93b8554`) |
| Drift formulation | unchanged by Stage 10.16 (no source correction) |
| Operational 30-day case | `iceberg_test_11_30day_offline` (ERA5 Q1, EN4 init, IBCAO grid) |
| Production defaults | `basal_melt_scheme = FORCED_CONVECTION` (bulk Stage 10.6), `thermal_evolution_enabled = .true.`, `low_flow_closure_enabled = .false.` |

## 14.3 Existing implementation

Source-level map of the melt machinery (all SI; T in °C, S in kg/kg):

| Process | File / function | Inputs | Formula / algorithm | Output | Units |
| --- | --- | --- | --- | --- | --- |
| Basal melt (production default: bulk) | `iceberg_thermodynamics.f90` → `compute_basal_melt`; transfer coeff in `iceberg_types.f90` → `ocean_heat_transfer_coeff` | T(S,z), S(z) at draft, u_ice/v_ice, L | ΔT = max(T(D)−Tf(D),0); U_rel at draft; Re = U_rel·L/ν; Nu = 0.037·Re^0.8·Pr^(1/3) (turb) / 0.664·Re^0.5·Pr^(1/3) (lam, Re<5e5); γ_T = Nu·k/L; m_b = γ_T·ΔT/(ρ_i·L_f); guard m<1e-12 → 0 | m_basal | m/s |
| Basal melt (3-equation, selectable) | `solve_three_equation_interface` (+`_natural`, `_low_flow`) | T_w, S_w, depth, U_rel, γ_T=K_T·U_rel, γ_S=K_S·U_rel | Bisection on F(m) = ρ_w c_w γ_T(T_w−T_B(m)) − m(ρ_i L_f + ρ_i c_i(T_B−T_i)) with S_B = γ_S S_w/(γ_S + (ρ_i/ρ_w)m) | m_basal, T_B, S_B | m/s, °C, kg/kg |
| Lateral melt (legacy, always on) | `compute_lateral_melt` | ⟨ΔT⟩_D from `depth_averaged_thermal_forcing` | m_l = C_LATERAL·⟨max(0,T−Tf)⟩_D; C_LATERAL = 1e-6 m/(s·K) (h ≈ 304 W/(m²·K)); **no velocity dependence** | m_lateral | m/s |
| Surface melt | `compute_surface_melt` | ERA5 atmos, T_surface, solar geometry | Q_nonlatent = SW_abs+LW_down+LW_up+SH; Q_LH = m_vapor·L_S; Q_surface = Q_nonlatent+Q_LH (−q_cond if thermal evolution); prognostic T_surface with phase-change split; m_s = max(Q_surface,0)/(ρ_i·L_f) at T=0 | m_surface, T_surface, q_surface, m_vapor | m/s, °C, W/m², kg/(m²·s) |
| Vapor flux | `compute_surface_melt` | ρ_air, C_E=1.5e-3, U, q_air−q_sat_ice | m_vapor = ρ_air·C_E·U·(q_air−q_sat_ice); applied to H (sublimation −/deposition +) | m_vapor | kg/(m²·s) |
| Geometry update | `iceberg.f90` → `iceberg_update_geometry` | m_*, m_vapor, pre-melt L,W,H | H −= dt·(m_b+m_s−m_vapor/ρ_i); L −= dt·m_l; W −= dt·m_l; clamp ≥ 0 | L,W,H | m |
| Mass | `iceberg_compute_geometry` | L,W,H | M = ρ_i·L·W·H; D = H·ρ_i/ρ_w | mass, draft | kg, m |
| Component mass loss | `iceberg_update_geometry` | pre-melt geometry, m_* | dM_b = ρ_i·L·W·dt·m_b; dM_l = ρ_i·(H·W+L·H)·dt·m_l; dM_s = ρ_i·L·W·dt·m_s; dM_v = −L·W·dt·m_v | diag%*_mass_loss | kg |
| Internal temperature (Stage 10.12, default ON) | `iceberg_types.f90` → `compute_iceberg_conductive_coupling`, `update_iceberg_internal_temperature` | T_surface, T_ice, H, m_basal, T_B | q_cond = 2·K_i·(T_s−T_i)/H; C_int·dT_i/dt = q_cond − q_bot; q_bot = m_b·ρ_i·c_i·max(T_B−T_i,0); clamp [T_ICE_MIN,T_ICE_MAX] | T_ice | °C |

Constants: ρ_i=910, ρ_w=1028, L_f=3.34e5 J/kg, c_i=2100 (surface layer) /
2009 (3eq), H_EFF=0.5 m, K_i=2.2 W/(m·K), Pr=13.8, ν=1.82e-6 m²/s,
k=0.56 W/(m·K), Re_crit=5e5, C_H=C_E=1.5e-3, L_S=2.835e6 J/kg,
MELT_RATE_MIN=1e-12 m/s, MIN_THICKNESS=1 m.

Time integration: explicit Euler on H, L, W with dt in seconds; melt rates are
**local dimensional rates** (m/s) applied to areas; no double-dt, no
m/s→m/day confusion inside the model (m/day appears only in output columns).

## 14.4 Mass–volume–geometry consistency

Reconstructed independently from the extended 30-day trajectory (720 steps):

- Reported mass `M_kg` vs `ρ_i·L·W·H`: **max relative difference 1.49e-5**
  (float32 print precision of the CSV; mean 5.8e-6) — mass and geometry are
  mutually consistent.
- Model-internal budget (TEST_11 check 6): |(M0−M_f) − Σ diag%total_mass_loss|/M0
  = **5.13e-4 %** — the model's own per-step component bookkeeping closes the
  integrated budget to 0.0005 %.
- Independent reconstruction from the CSV (component sum using step-sampled
  geometry): residual 1.3e-3 relative — a sampling artifact (CSV does not
  expose per-step `diag%*_mass_loss`; reconstruction uses post-step geometry
  instead of pre-melt), not an inconsistency of the model.
- Per-step geometry update verified in controlled experiments: `dL = −dt·m_l`,
  `dW = −dt·m_l`, `dH = −dt·(m_b + m_s − m_vapor/ρ_i)` exactly reproduce the
  state evolution (B5/B6 checks).

**Interpretation:** mass, volume, and geometry form one consistent bookkeeping
chain (M ≡ ρ_i·L·W·H by construction; geometry update and mass-loss components
are derived from the same pre-melt quantities).

## 14.5 Melt-component budget

30-day real-forcing TEST_11 (identical physics to Stage 10.15.2/10.16 — all 15
shared trajectory columns byte-identical):

| Component | Mean rate [m/day] | Area convention | Volume loss [Mt] | Mass loss [Mt] | Fraction of total |
| --- | --- | --- | --- | --- | --- |
| Basal | 0.0166 (max 0.0483) | L·W | 4.16 | 4.16 | **2.96 %** |
| Lateral | 0.2597 (max 0.2599, near-constant) | (H·W + L·H) full height | 135.96 | 135.96 | **96.83 %** |
| Surface | 0.0006 (max 0.0220; 39/720 steps) | L·W | 0.17 | 0.17 | 0.12 % |
| Vapor (sublimation) | −5.0e-6 kg/(m²·s) mean | L·W | — | 0.12 | 0.08 % |
| **Total** | | | | **140.29 (sum) / 140.22 (observed)** | 100 % |

- **Lateral melt dominates completely** (96.8 %) and is nearly constant
  (0.2597–0.2599 m/day): m_l = C_LATERAL·⟨ΔT⟩_D with ⟨ΔT⟩_D = 3.008 K constant
  (EN4 ocean at the trajectory position is uniform: T_draft = +1.902 °C,
  Tf = −1.983 °C, ΔT = 3.885 K; the 0.26 m/day implies
  ⟨ΔT⟩_D = 0.2597e-3/1e-6 = 3.0 K — consistent).
- Basal melt is small (0.017 m/day mean) because U_rel at the draft is tiny
  (0–0.027 m/s; drift is Coriolis-limited per Stage 10.16) and the bulk
  γ_T ∝ U_rel^0.5/^0.8 is small at these speeds.
- Surface melt occurs only on ~5.4 % of steps (39/720), when the winter
  atmosphere (Jan–Feb 2020) delivers net positive energy; max 0.022 m/day.
- Vapor is a small net sublimation loss (0.08 %).

## 14.6 Controlled experiments

`test/iceberg_test_10p17_melt_budget.f90` (47 checks, all PASS), synthetic
ocean/atmosphere, 100 m cube unless noted; outputs in
`data/output/stage10.17/*.csv`.

| Exp | Configuration | Result | Interpretation |
| --- | --- | --- | --- |
| A | T ≡ Tf exactly, cold air | m_b = m_l = m_s = 0; M conserved (vapor-only H drift) | No artificial melt; vapor bookkeeping in H verified |
| B | ΔT = 2 K, U = 0.1 m/s, cold air | m_b = 0.0697 m/day (ref 0.06967), m_l = 0.1728 (ref 0.1728), m_s = 0 | Bulk formula and lateral legacy formula match independent float64 references (rel < 5e-4) |
| C | ΔT = 0, warm air 285 K | m_b = m_l = 0; surface melt active; T_surface pinned at 0 °C; m_s·ρ_i·L_f = q_surface | Ocean/atmosphere decoupling correct; surface energy closure exact |
| D | ΔT = 2 K, U = 0 (ice at rest) | m_b = 0 (bulk guard), m_l = 0.1728 m/day | Lateral melt is **velocity-independent** (documented legacy simplification) |
| E | U = 0.004…0.08 m/s | m ∝ U^0.5 (laminar), m ∝ U^0.8 (turbulent), exact | Re-based transition and exponents implemented correctly |
| F | ΔT = 1/2/4 K | m_b, m_l ∝ ΔT exactly (1:2:4) | Thermal driving linear in both closures |
| G | t2m = 250…285 K, T_surface = 0 | No melt ≤ 276 K; melt at 278+; monotone | Winter Arctic surface-energy threshold reproduced |
| H | L = 10/50/100/200 m | m_b ∝ L^-0.2 (turbulent); m_l size-independent; fractional loss ∝ 1/L | Geometry scaling follows implemented formulas |
| I | dt = 1800/3600/7200 s | dM within 1.7e-5 (1800 vs 3600), < 1.7e-5 (7200 vs 3600); closure < 2.6e-5 | Melt integration is dt-insensitive; explicit Euler adequate |
| J | Thermal evolution ON/OFF | OFF: T_ice ≡ −10 °C, dT/dt = 0; ON: T_ice evolves (cooling by basal sensible flux, bounded); solver matches analytic q_cond = 0.44 W/m² | Switch fully gates internal temperature; solver correct |
| K | 30-day synthetic stress (case B) | budget closure 2.2e-7; mass monotone; geometry positive; loss 12.0 % | Long integration numerically stable |

## 14.7 Thermal/energy budget

Available terms (all in W/m² unless noted):

| Term | Present | Formula | Closure status |
| --- | --- | --- | --- |
| Surface: SW absorbed, LW down/up, SH, LH | yes | Q_surface = SW_abs+LW_down+LW_up+SH+Q_LH | **exact** at steady melt: m_s·ρ_i·L_f = Q_surface (verified in C and in 37/39 real-forcing melt steps; the 2 remaining steps are T_melt crossings where part of the flux warms the skin — consistent with the implemented phase-change split) |
| Surface: latent (sublimation/deposition) | yes | Q_LH = m_vapor·L_S | bookkept in Q_surface; mass effect applied to H |
| Basal: ocean heat flux | yes | Q_b = γ_T·ΔT | **exact**: Q_b = m_b·ρ_i·L_f by construction (verified B) |
| Internal: conduction q_cond | yes | q_cond = 2·K_i·(T_s−T_i)/H | solver verified analytically (J5/J6) |
| Internal: basal sensible q_bot | yes | q_bot = m_b·ρ_i·c_i·max(T_B−T_i, 0) | C_int·dT_i/dt = q_cond − q_bot verified (J5); q_bot cools T_ice (J3) |
| Lateral: implied heat flux | yes | m_l·ρ_i·L_f = 304·⟨ΔT⟩_D W/(m²·K) | implied h ≈ 304 W/(m²·K) matches design note (γ = h/(ρ_i L_f) = 1e-6) |
| Internal 3D temperature field | **no** | two-node lumped only | documented simplification (Stage 10.12) |
| Ocean seasonal evolution | **no** | EN4 initial state, time-invariant | limitation (offline forcing) |

Unavailable/unresolved:

- `diag%q_cond` and `diag%q_bot` are **never assigned** in
  `iceberg_thermodynamics_step` (fields exist in `iceberg_diagnostics`; the
  local values are used by the solver but not exported). Diagnostic gap, no
  physics impact.
- `diag%q_net_surface` is dimensionally inconsistent: `q_net = q_surface −
  m_surface·ρ_i·L_f/dt` mixes W/m² with W/(m²·s) (the `/dt` is spurious; the
  correct residual is `q_surface − m_surface·ρ_i·L_f`). Diagnostic defect, no
  physics impact (numerically q_net ≈ q_surface).

## 14.8 Real-forcing TEST_11

Repeated 30-day run with the extended diagnostics harness (same physics:

- Command: `fpm test --flag "-I/usr/include" iceberg_test_11_30day_offline`
- Exit code: 0; runtime ≈ 2 s (dominated by grid/EN4/ERA5 initialization)
- 720 rows; trajectory unchanged: **all 15 pre-existing CSV columns
  byte-identical** to Stage 10.16 (`data/output/stage10.16/test11_stage10.16_trajectory.csv`)
- Mass 909.80 → 769.58 Mt (−15.41 %); L/W 100 → 92.21 m; H 100 → 99.47 m
- Melt (control): basal max 0.0483, lateral max 0.2599, surface max 0.0220 m/day
- New diagnostics: T_draft = 1.902 °C const, Tf_draft = −1.983 °C,
  ΔT = 3.885 K const, u_rel_draft 0–0.027 m/s, q_surface −221…+231 W/m²,
  T_surface −12.5…0 °C, T_ice −10.06…−10.00 °C, m_vapor −2.5e-5…+2.2e-5 kg/(m²·s)
- Warnings/skips: none (test-level); pre-existing `IEEE_DENORMAL` note only.

**The melt-dynamics investigation does not alter the operational trajectory.**

## 14.9 Findings

| # | Finding | Classification | Evidence | Affected code | Changed |
| --- | --- | --- | --- | --- | --- |
| F1 | Lateral melt dominates (96.8 %) via legacy constant C_LATERAL = 1e-6 m/(s·K), velocity-independent, applied over the full height H | expected model simplification (documented legacy Stage 9.1 §14) | controlled experiments B/D/F/H; budget table | `compute_lateral_melt`, `iceberg_update_geometry` | no |
| F2 | Lateral-area convention inconsistent: production update erodes full height ((H·W+L·H), incl. freeboard), while module docs and the unused helpers `compute_mass_budget`/`melt_volume_rates` define lateral area as submerged 2(L+W)·D → lateral volume loss ~H/D = 1.13× the submerged-area convention (~13 % of lateral mass loss ≈ 12.6 % of total) | confirmed inconsistency (production vs own documentation/dead helpers); physical concern: water-driven melt applied to the sail | source audit; dead-code check (helpers never called) | `iceberg_geometry.f90` (helpers), `iceberg.f90` (update) | no |
| F3 | `q_net_surface` dimensional defect (÷dt) | confirmed implementation error (diagnostic only; no physics impact) | source audit (line 1247) | `iceberg_thermodynamics.f90` | no |
| F4 | TEST_11 CSV is not valid CSV: comma header + Fortran fixed-width whitespace rows | confirmed output-format defect (minor; all consumers must handle) | file inspection | `iceberg_test_11_30day_offline.f90` | no (documented; extended columns keep the same style) |
| F5 | `diag%q_cond`/`diag%q_bot` never populated | confirmed diagnostic gap | source audit (no assignment) | `iceberg_thermodynamics.f90` | no |
| F6 | Sign/comment mismatches for vapor: `iceberg_diagnostics%vapor_mass_loss` doc says "neg = sublimation" but code makes it positive for loss; Stage 10.3 comment "no mass change from sublimation" contradicts Stage 10.4 implementation | documentation issues | source audit | `iceberg_types.f90`, `iceberg_thermodynamics.f90` comments | no |
| F7 | `C_BASAL` dead parameter (basal uses bulk/3eq schemes; only comments + commented-out test reference it) | code hygiene | grep | `iceberg_types.f90` | no |
| F8 | Lateral melt erodes the above-water sail at the water-driven rate (F2's physics consequence): possible double counting with surface processes | plausible concern requiring further evidence | F2 analysis | geometry update | no |
| F9 | Surface melt nearly absent in Q1 (39/720 steps, max 0.022 m/day) | physical (cold winter atmosphere); not an error | trajectory data | — | no |
| F10 | Ocean state time-invariant (EN4 initial T/S, climatological U/V) | pre-existing limitation of the offline forcing | forcing architecture | `get_ocean_profile` | no |
| F11 | 90-day diagnostic run: −42.2 % mass; lateral erosion linear (0.259 m/day) → L would reach ~1 m in ~380 days under constant-ocean forcing | limitation / interpretation: annual extrapolation **premature**; demonstrates need for seasonal ocean state | 90-day run | — | no |

## 14.10 Scientific interpretation

- **Reliable as a software artifact:** mass ≡ ρ_i·L·W·H bookkeeping (max 1.5e-5
  print-precision deviation); per-component geometry update; budget closure
  (5e-4 % over 30 days); melt-rate scalings (U^0.5/U^0.8, ΔT-linear, L^-0.2,
  1/L) exactly match the implemented formulas; dt-insensitivity; thermal
  switch gating.
- **Physically plausible but not validated:** lateral melt 0.26 m/day is within
  the commonly cited range for iceberg lateral erosion in warm water, but the
  constant-coefficient legacy formula (C_LATERAL, no velocity dependence, full
  height) is a deliberate simplification — no observational comparison exists.
- **Cannot yet be inferred:** absolute accuracy of melt rates; annual mass loss;
  melt under seasonal ocean warming (ocean state frozen at January);
  partitioning between submerged vs sail lateral erosion (F2/F8).
- **Dominant component:** lateral (96.8 %) — trustworthy only as "the model's
  lateral legacy formula is the main mass-loss driver"; its constant rate makes
  the mass loss nearly linear in time.
- **Long-term extrapolation:** premature. The 90-day run is an operational
  demonstration of the Q1 atmosphere cycle only.

## 14.11 Limitations

- No observational comparison of melt rates (offline model, no calibration —
  per scope).
- Offline forcing: ERA5 atmosphere (Q1 2020), EN4 initial T/S and climatological
  U/V held constant in time; ocean seasonal cycle absent; IBCAO bathymetry only
  used for grounding.
- Thermal initialization: uniform T_ice = −10 °C, two-node lumped thermal model
  (Stage 10.12); no 3D temperature field.
- Ocean NaN/zombie behavior of the Eulerian model remains open (Stage 8 family);
  it does not affect this offline iceberg module but blocks coupled
  demonstrations.
- Production executable does not run the iceberg module (Stage 10.15 finding);
  production-path integration remains open.
- Budget-reconstruction residual of 1.3e-3 in the Python layer is a CSV sampling
  artifact (per-step `diag%*_mass_loss` not exported).
- Uncertainty in melt parameterizations (bulk vs 3-equation vs natural
  convection; legacy lateral) is not quantified here; 3-equation schemes are
  validated separately (Stages 10.10–10.14) but are not the production default.
- A 30-day (or 90-day) run cannot establish annual accuracy; the 90-day run uses
  an ocean state frozen at 2020-01-01.

## 14.12 Next stage

Based on the evidence:

- The melt machinery is internally consistent; **no confirmed physical error
  requires correction**. The main scientific concerns (F2/F8 — lateral area
  convention and sail erosion; F11 — long-run behavior) are modeling-choice
  questions, not bugs.
- Recommended next stage: **Stage 10.18 — extended operational demonstration**
  (or, if the user prefers, a dedicated stage to re-evaluate the lateral-melt
  parameterization — e.g., velocity-dependent and submerged-area formulations —
  as an explicitly approved physics change). The audit does not predeclare a
  correction.

---

## Test battery (Stage 10.17)

| Suite | Result |
| --- | --- |
| `iceberg_test_10p17_melt_budget` (new, Fortran) | PASS (47/47) |
| `iceberg_test_10p17_90day` (new, Fortran) | PASS (7/7) |
| `iceberg_test_11_30day_offline` (extended diagnostics) | PASS (7/7; 15 shared CSV columns byte-identical to 10.16) |
| Full fpm battery | 49 PASSED, 0 FAILED, 1 SKIP (pre-existing run-context test requiring `fpm run`) |
| `test_stage10_17_melt_budget.py` (new, Python) | PASS (40/40) |
| All other Python suites (10.10–10.16) | PASS (9 suites, 612 checks) |
| `py_compile` (changed Python files) | OK |
| `git diff --check` | CLEAN |
| Markdown audit | 0 issues |

## Outputs (gitignored)

`data/output/stage10.17/`: 12 plots (`mass_timeseries`, `geometry_timeseries`,
`melt_components_timeseries`, `cumulative_mass_loss`, `component_mass_loss`,
`mass_geometry_consistency`, `thermal_forcing_timeseries`,
`relative_velocity_vs_melt`, `temperature_vs_melt`, `melt_budget_closure`,
`timestep_sensitivity`, `size_sensitivity`), `stage10.17_summary.json`,
`mass_geometry_budget.csv`, `melt_component_budget.csv`, `thermal_budget.csv`,
`synthetic_melt_experiments.csv`, `timestep_sensitivity.csv`,
`size_sensitivity.csv`, `temperature_sensitivity.csv`,
`velocity_sensitivity.csv`, `test11_stage10.17_trajectory.csv` (extended copy),
`test11_90day_stage10.17_trajectory.csv`, `reproducibility.log`.