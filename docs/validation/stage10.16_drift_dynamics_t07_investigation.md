# Stage 10.16 — Drift Dynamics and T-07 Investigation

**Classification: Drift-dynamics investigation completed — T-07 PARTIALLY
EXPLAINED (physical Coriolis-limited equilibrium; no source correction
justified)**
**Production physics changed: NO**
**Default configuration changed: NO**
**Source code changed: NO (diagnostics + tests only)**

This stage is a focused scientific and numerical investigation of the
existing iceberg drift dynamics and the open issue T-07. It is **not** a
calibration stage, **not** observational validation, **not** a new
melt-physics stage, and **not** production-path integration.

| Item | Value |
| ---- | ----- |
| Stage | 10.16 (drift dynamics and T-07 investigation) |
| Branch / HEAD | `main` @ `93b8554` (Stage 10.15.2 committed and pushed) |
| New Fortran test | `test/iceberg_test_drift_dynamics.f90` (16 checks: experiments A–K) |
| New Python test | `python/tests/test_stage10_16_drift_scaling.py` (13 checks, analytic expectations) |
| New analysis script | `python/analysis/stage10.16_drift_analysis.py` (10 figures + summary JSON) |
| Output bundle (gitignored) | `data/output/stage10.16/` |

---

## 1. Scope

Stage 10.16 investigates why the model's drift amplitude is substantially
lower than the reference ranges used by the project (wind 1–2 %, current
2–5 %). The goal is to determine, reproducibly and honestly, whether the low
drift is caused by physics, units, or numerical integration — and what
evidence is required before changing the physical formulation. It does not
introduce new physical equations, does not calibrate, and does not compare
with observations as if the model were validated.

## 2. Baseline

| Item | Value |
| ---- | ----- |
| Baseline commit | `93b8554` (Stage 10.15.2), branch `main`, clean tree, `origin/main == HEAD` |
| Relevant previous findings | T-13 (coordinate interpolation) fixed in 10.15.2; geographic trajectory now continuous; drift-scaling numbers unchanged after the coordinate fix |
| Current T-07 wording | "Wind-drift ratio 0.08% (with Coriolis) vs literature 1–2%; current-drift ratio 0.13–1.24% vs 2–5% — needs C_D calibration" (`KNOWN_ISSUES.md` T-07, `docs/wiki/stages/stage09/Stage9.3_Scientific_Verification_and_Calibration.md`) |
| Measured (re-verified this stage) | wind+Coriolis 0.04–0.12 %; wind no-Coriolis 2.98–3.45 %; current+Coriolis 0.13–1.24 % |

## 3. Existing implementation

### 3.1 Source files

- `src/iceberg_dynamics.f90` — main drift routine `iceberg_dynamics_step`,
  `compute_wind_force`, `compute_water_force` (Method A),
  `compute_water_force_method_b` (Method B), semi-implicit Coriolis solver.
- `src/iceberg.f90` — orchestrator: `iceberg_step` (geometry → grounding →
  thermodynamics → dynamics → position update), `iceberg_init`.
- `src/iceberg_forcing.f90` — `depth_integrated_currents` (profile
  integration), `get_ocean_profile` (ocean T/S/u/v interpolation).
- `src/iceberg_types.f90` — constants and state.

### 3.2 Equations as implemented (SI units)

| Term | Formula (as implemented) | Units | Notes |
| ---- | ------------------------ | ----- | ----- |
| Mass | `M = ρ_ice·L·W·H` = 9.1e8 kg | kg | 100 m cube |
| Wind force | `F_wind = ½·ρ_a·C_Da·A_sail·|V10−u|·(V10−u)` | N | `A_sail = L·W + 2(L+W)·freeboard` = 14,591 m² |
| Water force (A) | `F_water,x = Σₖ ½·ρ_w·C_Dw·(W·Δz_k)·|u_k−u|·(u_k−u)` | N | side area per layer; x-force uses `W·Δz`, y-force uses `L·Δz` |
| Water force (B) | `F_water = ½·ρ_w·C_Dw·A_wet·|U_avg−u|·(U_avg−u)` | N | test-only (TEST_4 comparison) |
| Coriolis | `F_cor = M·f·(−v, u)`, `f = 2Ω·sin(φ)` | N | f = 1.418e-4 s⁻¹ at 76.5°N; M·f = 1.29e5 kg/s |
| Pressure gradient | `F_pres = −M/ρ_w·∇η` | N | 0 in offline runs |
| Semi-implicit solve | `u_new = (u + dt·F_x_noncor/M + dt·f·v)/A`, `A = 1+(f·dt)²` | — | v analogously; **missing `dt²·f·F_y/M` cross terms of the exact implicit scheme** |
| Position update | `x += dt·u`, `y += dt·v` | m | explicit Euler |

Constants: ρ_ice = 910, ρ_w = 1028, ρ_a = 1.225 kg/m³; C_Da = 1.3e-3,
C_Dw = 2.0e-3; Ω = 7.292e-5 s⁻¹. All internal computations SI; conversions
only at forcing/output boundaries.

### 3.3 Key structural facts

- **Velocity is absolute** (ocean-relative via drag, not an added current);
  current enters **through the water drag** relative velocity only.
- Wind velocity enters **through the wind drag** relative velocity
  (`V10 − u`), not as an added speed.
- Water drag Method A uses **side area only** (W·draft for x, L·draft for y),
  not the bottom area (L·W) and not the full wetted area — a documented
  modeling choice; Method B exists for comparison.
- Coriolis uses `state%latitude` (corrected in 10.15.2).
- Time step 3600 s; explicit Euler position update; semi-implicit Coriolis
  with damping factor A.

## 4. Controlled experiments (A–K)

All experiments: 100×100×100 m berg (unless size experiment), cold
ocean/atmosphere (melt disabled), 30-day runs, dt = 3600 s (unless timestep
experiment). Outputs: `data/output/stage10.16/`.

| Exp | Configuration | Result | Interpretation |
| --- | ------------- | ------ | -------------- |
| A | Zero wind, zero current | u = v = 0 exactly | no artificial acceleration |
| B1 | Wind 10 m/s +X, Coriolis ON (76.5°N) | final speed **0.00801 m/s** (ratio 0.080 %) | Coriolis-limited equilibrium |
| B2 | Wind 10 m/s +X, Coriolis OFF (equator) | final speed **0.345 m/s** (ratio 3.45 %) | drag-limited equilibrium |
| C1 | Current 0.1 m/s +X, Coriolis ON | final speed **0.000625 m/s** (ratio 0.62 %) | Coriolis-limited current response |
| C2 | Current 0.1 m/s +X, Coriolis OFF | final speed **0.072 m/s** (ratio 72 % after 30 d) | current-following; τ ≈ 11.6 d (u/U = t/(t+τ) — matches) |
| D | Wind 10 m/s + current 0.1 m/s, Coriolis ON | final speed 0.0086 m/s | combined; dominated by wind term |
| E | Wind +X vs +Y | components rotate consistently (90°) | direction handling correct |
| F | Current +X vs +Y | components rotate consistently (90°) | direction handling correct |
| G | Coriolis ON vs OFF (wind 10 m/s) | 0.008 vs 0.345 m/s (**43× suppression**) | Coriolis is the dominant limiting term |
| H | dt = 1800 / 3600 / 7200 s | 0.00872 / 0.00801 / 0.00629 m/s | equilibrium speed depends on dt via damping factor √A |
| I | L = 10/30/100/300 m (wind) | ratios 0.78 / 0.27 / 0.08 / 0.027 % | **ratio ∝ 1/L** (Coriolis-limited signature) |
| I | L = 10/100/300 m (current) | ratios 5.93 / 0.62 / 0.11 % | same ∝ 1/L signature |
| J | C_Dw perturbed 2e-3 → 1e-3 (temporary rebuild, reverted) | wind+Coriolis ratio **unchanged** (0.04/0.08/0.12 %); no-Coriolis ratio ×√2 (0.0458/0.0341 = 1.34) | Coriolis-limited speed independent of C_Dw — decisive |
| K1–K3 | Force signs | water pushes with current, wind pushes with wind, water brakes faster-than-current berg | sign/direction correct |
| K4 | Acceleration scale | ~1.3e-6 m/s² ≈ F/M | units consistent |

## 5. Force balance (B1 equilibrium, wind 10 m/s + Coriolis)

| Term | Magnitude at equilibrium | Role |
| ---- | ------------------------ | ---- |
| Wind drag | 1161 N | driving |
| Water drag | **0.58 N** | negligible at the equilibrium speed |
| Coriolis | 1034 N | **balances the wind** |
| Mass | 9.1e8 kg | inertia |
| Acceleration | ~1e-7 m/s² (≈ 0) | equilibrium |

**The equilibrium is Coriolis-limited, not drag-limited.** At u ≈ 0.008 m/s
the water drag is only 0.58 N (quadratic in the tiny relative velocity),
while the Coriolis force M·f·u ≈ 1.29e5·0.008 ≈ 1030 N matches the wind
force. The analytic discrete equilibrium of the implemented scheme is:

```
u_eq = F_wind / (M·f·√(1 + (f·dt)²))
```

with the continuous limit (dt→0) `u_eq = F_wind/(M·f) = 1161/1.29e5 =
0.009 m/s` (ratio 0.09 %). The measured 0.00801 m/s matches the discrete
analytic value 0.00802 m/s to 0.1 %.

## 6. T-07 status: **PARTIALLY EXPLAINED**

**The observed low wind-drift ratio (0.04–0.13 %) is the physically correct
Coriolis-limited equilibrium of the implemented momentum balance for a
100-m cube iceberg** — verified by:

1. **Analytic match**: u_eq = F_wind/(M·f·√(1+(f·dt)²)) predicts 0.00802 m/s;
   measured 0.00801 m/s (< 0.1 % error).
2. **Size scaling**: ratio ∝ 1/L (0.78 % → 0.027 % for 10 → 300 m) — the
   Coriolis-limited signature (u ∝ F_wind/(M·f) ∝ A_sail/M ∝ L²/L³ = 1/L).
3. **Drag independence (exp J)**: halving C_Dw leaves the wind+Coriolis
   ratio unchanged — the water drag is irrelevant at this equilibrium.
4. **Force balance**: at equilibrium wind ≈ Coriolis ≫ water drag.
5. **No-Coriolis control**: without Coriolis the ratio is 3.45 %, matching
   the analytic drag-limited value √(ρ_a·C_a·A_sail/(ρ_w·C_w·A_side)) =
   3.45 % — the drag law itself is correct; Coriolis is the limiter.

**Why the reference (1–2 %) does not apply:** the literature wind-factor
range assumes either (a) a drag-limited regime (small mass or weak
Coriolis — e.g., sea ice or small bergs), or (b) a wind-driven surface
current (Ekman) mechanism, in which the wind drives the *ocean* and the
berg follows the current. This offline model has neither: the wind acts
directly on the sail of a very massive berg (M·f = 1.29e5 kg/s), and the
ocean current is prescribed (EN4), not wind-generated. The current-driven
ratio (0.13–1.24 % vs the 2–5 % reference) is likewise Coriolis-limited:
u ≈ F_water/(M·f) = ½ρ_w·C_Dw·A_side·U²/(M·f), analytic 0.71 % vs measured
0.62 % at U = 0.1 m/s (with the √A damping factor).

**Secondary numerical factor (documented, not the primary cause):** the
semi-implicit Coriolis solver's equilibrium depends on dt through the
damping factor 1/√(1+(f·dt)²): 0.89 at dt = 3600 s (11 % suppression),
0.70 at dt = 7200 s (30 %). This is the same family as the documented 8 %
Coriolis period error (T-06); it contributes ~11 % to the low ratio at the
standard dt, not the factor-10+ discrepancy. The exact implicit scheme would
also include `dt²·f·F_y/M` cross terms, which are currently absent — a
minor O((f·dt)²) correction, not the primary cause.

**Confidence:** high (analytic match < 0.1 %; three independent signatures:
size scaling, drag independence, force balance). **Changed:** nothing (no
source correction justified — the model is self-consistent; changing the
drag law or adding a wind-driven current would be a new physical mechanism
requiring a separate approved stage).

## 7. Real-forcing run (TEST_11, 30 days)

| Item | Value |
| ---- | ----- |
| Command | `fpm test --flag "-I/usr/include" iceberg_test_11_30day_offline` |
| Inputs | identical to Stage 10.15.2 (ERA5 Q1 364 slices, EN4, IBCAO, same config, dt = 3600 s) |
| Exit code | 0 |
| Runtime | ~15 s |
| Trajectory rows | 720 |
| Coordinates | lat 74.997–75.066 °N, lon 29.755–30.142 °E |
| Speed | max 0.0271 m/s |
| Displacement | 11.43 km straight, 25.96 km path |
| Mass | 909.8 → 769.6 Mt (−15.41 %) |
| Dimensions | L/W 100 → 92.21 m, H 100 → 99.47 m |
| Melt (control only) | basal max 0.0483, lateral max 0.2599, surface max 0.0220 m/day |
| Warnings / skips | none |

**Difference vs Stage 10.15.2:** none — the trajectory CSV is
**byte-identical** (md5 `04c90ca1...`) to the 10.15.2 post-fix run, as
expected (no physics changed in 10.16). The drift investigation does not
alter the operational trajectory; melt values are recorded as control
variables only (not a melt validation).

## 8. Tests

| Suite | Result | Notes |
| ----- | ------ | ----- |
| `iceberg_test_drift_dynamics` (new, Fortran, 16 checks) | **PASS** | experiments A–K incl. force signs, acceleration scale, rotation consistency |
| `test_stage10_16_drift_scaling.py` (new, 13 checks) | **PASS** | analytic expectations: drag-limited ratio 3.45 %, Coriolis-limited B1 0.00802, size ∝ 1/L, dt damping √A, current response, trajectory integrity |
| Full fpm battery | **PASS** (exit 0, 49 PASSED, 0 FAILED, 1 SKIP) | SKIP is the pre-existing run-context test requiring `fpm run` output (unrelated) |
| All 12 Python suites | **PASS** | incl. 10.15.1 audit 29/29 |
| `py_compile` (changed Python) | PASS | |
| `git diff --check` | CLEAN | |
| Markdown audit (changed docs) | 0 issues | |

## 9. Plots and outputs

`data/output/stage10.16/` (gitignored):

| File | Content |
| ---- | ------- |
| `plots/force_balance_timeseries.png` | B1 wind/water/Coriolis forces (log scale) — shows Coriolis ≈ wind ≫ water |
| `plots/wind_only_response.png` | B1 vs B2 u/v/speed |
| `plots/current_only_response.png` | C1 vs C2 u/v/speed + current reference |
| `plots/combined_forcing_response.png` | D u/v/speed |
| `plots/timestep_sensitivity.png` | H: speed vs dt + continuous-limit reference |
| `plots/size_sensitivity.png` | I: wind/current ratios vs L + 1/L reference |
| `plots/drift_scaling_comparison.png` | T-07 wind ratios + expected band |
| `plots/trajectory_pre_post_stage10.16.png` | TEST_11 corrected trajectory |
| `plots/speed_timeseries.png` | TEST_11 speed + 24 h rolling mean |
| `plots/relative_velocity_timeseries.png` | B1 relative wind/water speeds |
| `stage10.16_summary.json` | mechanism, experiments, force balance, T-07 status |
| `force_balance_timeseries_<case>.csv` | per-step forces/velocities (B1, B2, C1, C2, D) |
| `synthetic_experiments.csv` | machine-readable experiment table |
| `timestep_sensitivity.csv`, `size_sensitivity.csv` | H and I tables |
| `drift_scaling_comparison.csv` | wind/current scaling measured values |
| `test11_stage10.16_trajectory.csv` | 30-day trajectory (identical to 10.15.2) |

All plots have titles, axis labels, units, legends where needed, raw series
(no hidden filtering; optional labelled rolling mean only in
`speed_timeseries.png`). The trajectory plot follows the 10.15.1/10.15.2
convention (lon–lat, color by time, start/end markers).

## 10. Limitations

- Drift ratios are **not** observational validation — the experiments use
  idealized constant forcing; real-ocean conditions (spatial/temporal
  variability, wind-driven surface currents, waves, sea ice) are absent.
- Synthetic experiments isolate implementation behavior; a controlled
  forcing field is not equivalent to real ocean conditions.
- Continuous coordinates (10.15.2) do not prove correct drift physics.
- Melt accuracy is **not** assessed in this stage (melt was disabled in
  experiments; TEST_11 melt values are control variables only).
- Production executable integration remains open (`app/main.f90` does not
  run the iceberg module).
- Ocean NaN/zombie behavior remains open (Stage 8 family, full-model runs).
- The literature 1–2 % wind factor is stated as context, not as a validated
  model target; the project's reference range itself is scale/mechanism
  dependent and should be re-qualified in `KNOWN_ISSUES.md`.
- The semi-implicit Coriolis scheme's dt-dependent damping (√A) and the
  missing `dt²·f·F_y/M` cross terms are documented as minor numerical
  effects; correcting them would change results by ≤ ~11 % at dt = 3600 s
  and is not required to explain T-07.

## 11. Next stage

**Stage 10.17 — Iceberg Melt and Thermodynamic Budget Audit** (separate
stage, not merged into 10.16) will investigate:

- basal, lateral, and surface melting;
- mass and geometry consistency;
- thermal and energy budgets;
- sensitivity to temperature and relative velocity;
- seasonal melt behavior.

T-07 is partially explained; a physical correction (e.g., adding a
wind-driven surface current, or re-qualifying the reference ranges) requires
a separate approved stage with its own evidence. The next step after 10.17
remains production-path integration and ocean-init stabilization.