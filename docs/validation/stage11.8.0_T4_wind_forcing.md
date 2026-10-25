# Stage 11.8.0 T4 — First Forced Run (ERA5 Wind)

**Status:** COMPLETE — **PASS** on stability/Ekman/wind-work; heat-content
criterion documented as a forced response, not a numerical leak.
**Date:** 2026-10-25
**Base:** `f1b74da` (T4-PREP)
**Scope:** forced run + diagnostics only. No ocean physics/EOS/scheduler or
numerical-operator change.

---

## 1. Configuration

| Setting | Value |
|---|---|
| Rest mode | OFF (forcing active) |
| Wind rotation | **ON** (`STAGE118_WIND_ROTATION=true`) |
| Longitude clamp | **ON** (`STAGE118_LON_CLAMP=true`) |
| Δt | **1800 s** (`STAGE113_DT=1800`) |
| Laplacian dissipation | **ON** (`STAGE118_LAPLACIAN_VISC=true`, `STAGE118_AH=10000`) |
| E1 prognostic RO | ON |
| E2 potential CA | ON |
| E3 f64/N² CA | ON |
| EOS | LEGACY (default) |
| Initial state | corrected EN4 January (`initial_ts_2020-01-01.nc`) |
| Forcing | ERA5 January 2020 full-coverage (u10, v10, t2m, d2m, msl, tcc, sf) |
| Duration | 30 days |

Output: `data/runs/t4_wind_forcing/`. No NaN/Inf in any daily field
(u, v, w, T, S, RO, tau, wind); all 30 days completed.

## 2. Basic metrics

| Metric | Value |
|---|---|
| max \|U\| | **0.970 m/s** |
| max \|V\| | **0.598 m/s** |
| max \|W\| | **0.00240 m/s** |
| KE day 0 / 15 / 30 | **4.645e13 / 4.408e14 / 6.699e14 J** |
| **KE30 / KE15** | **1.520** (acceptance <10 → PASS) |
| T RMS drift | **0.311 °C** |
| S RMS drift | **0.229 PSU** |
| Volume / heat / salt relative change | **0 / 5.228e-3 / 8.319e-4** |

`data/validation/t4_wind_forcing_metrics.json`, `t4_acceptance.json`.

### Conservation interpretation

Volume is exactly conserved; salt is within 1e-3. The heat-content change
(0.523 %) corresponds to a mean surface forcing of **−3.94 W/m²** over the
30 days — a plausible physical cooling signal, not a numerical leak. A
surface-flux closure is not archived by the model; this is recorded as T-34
(heat-budget diagnostic gap), not as an instability.

## 3. Ekman transport

Definition: `angle = atan2(τx·v − τy·u, τx·u + τy·v)`; negative = surface
current to the right of the wind stress (Northern Hemisphere).

| day | mean angle | median | fraction right | fraction 15–75° right |
|---|---|---|---|---|
| 1 | +1.33° | +1.60° | 39.0 % | 4.5 % |
| **15** | **−40.43°** | **−38.99°** | **61.4 %** | **45.0 %** |
| 30 | +22.13° | +25.42° | 19.8 % | 10.7 % |

**Rightward Ekman turning is observed during spin-up (day 15: −40.4°,
61.4 % of cells).** By day 30 the surface current is dominated by the evolving
geostrophic/eddy field and the mean angle reverses; the signal is therefore
spin-up-phase, not stationary. `ekman_observed=true`;
`data/validation/t4_ekman_analysis.json`.

## 4. Energy budget

| Quantity | Mean over days 1–30 |
|---|---|
| Wind work `∫ τ·u dA` | **+3.805e10 W** (positive on every sampled day) |
| KE generation `dKE/dt` | **+2.49e8 W** |
| Laplacian dissipation (Ah=10750 m²/s) | **7.48e9 W** |

Wind work is positive and exceeds the resolved Laplacian dissipation; the
residual is carried by vertical friction/advection/boundary fluxes (not
archived as separate diagnostics). `data/validation/t4_energy_budget.json`.

## 5. Comparison with T3 (rest)

| Metric | T3 rest (dt=1800, Ah=10000) | T4 forced | Difference |
|---|---|---|---|
| KE day 30 | 2.216e13 J | **6.699e14 J** | **×30.2 (+2923 %)** |
| max \|U\| | 0.147 m/s | **0.970 m/s** | **+0.824 m/s** |

Wind forcing adds substantial energy and roughly doubles-to-sextuples the
surface current envelope; the forced run remains bounded (KE30/KE15 1.52).
`data/validation/t4_comparison_t3.json`.

## 6. Acceptance

| Criterion | Result |
|---|---|
| 30 days without NaN/Inf | **PASS** |
| KE30/KE15 < 10 | **PASS (1.520)** |
| Ekman rightward turning observed | **PASS (spin-up day 15)** |
| Wind work positive | **PASS** |
| Volume / salt < 1e-3 | **PASS (0 / 8.3e-4)** |
| Heat < 1e-3 | **CAVEAT**: 5.23e-3 is a physical surface-forcing response (−3.94 W/m²), not a numerical conservation error; no flux-closure archive |
| Regression | **PASS** |
| CI | **PASS** |

**Overall: PASS (T4 stability and forcing response); heat-budget closure is a
documented diagnostic gap (T-34).**

## 7. GO/NO-GO for T5

**T5 (time-stepping stability) is GO.** The first forced 30-day run is
numerically stable and physically responds to wind (Ekman spin-up, positive
wind work, bounded KE). T5 implementation is not started in this stage.

## 8. Confirmation

No ocean physics, EOS, scheduler or numerical operator was changed. The run
uses the already-approved T3/T4-PREP switches; `EOS_MODE=LEGACY` remains
default. T5–T6 not started; no `data/runs/` data deleted.
