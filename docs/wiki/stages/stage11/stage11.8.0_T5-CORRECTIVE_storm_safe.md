# Stage 11.8.0 T5-CORRECTIVE — Storm-Safe Configuration Search

**Status:** **FAIL — no prescribed configuration completes 90 days.**
**Date:** 2026-10-25
**Base:** `651385a` (T5)
**Scope:** numerical configuration search only. No ocean physics/EOS/scheduler
or numerical-operator change.

---

## 1. Configuration search (90-day January, Q1 ERA5)

All runs keep wind rotation, longitude clamp, E1+E2+E3, LEGACY.

| Config | Δt (s) | Ah (m²/s) | days | first NaN | max \|U\| | KE30 (J) | KE60 (J) | KE90 (J) | KE60/KE30 | KE90/KE60 | Result |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 900 | 20000 | 63 | — (FPE after 64) | **1361.5** | 5.237e14 | 6.410e14 | — | 1.224 | — | **FAIL** |
| 2 | 900 | 30000 | 90 | **67** | **4.402e7** | 5.198e14 | 6.105e14 | 5.007e10 | 1.174 | 8.2e-5 | **FAIL** (NaN) |
| 3 | 600 | 30000 | 90 | **70** | **4.020e7** | 4.892e14 | 5.255e14 | 5.007e10 | 1.074 | 9.5e-5 | **FAIL** (NaN) |
| 4 (exploratory) | 600 | 50000 | 90 | **74** | **2.455e5** | 4.861e14 | 5.220e14 | 5.007e10 | 1.074 | 9.6e-5 | **FAIL** (NaN) |

- Config 1 is stable through day 63 (Umax 0.91 m/s) but explodes at day 62–63
  (day 63 KE 1.98e20 J, Umax 1361 m/s) and hits SIGFPE after day 63.
- Configs 2–4 complete 90 calendar days only because the code continues after
  the state collapses: first NaN appears at day **67/70/74**, after which
  T/S/RO/velocity are invalid and KE is meaningless. They do **not** meet the
  no-NaN or max-|U|<5 criteria.
- **No configuration passes.** Stronger Ah (30000, 50000) and smaller Δt delay
  the failure by only a few days; the storm instability is not controlled by
  ocean momentum dissipation/CFL alone.

Outputs: `t5c_config1_results.json` … `t5c_config4_results.json`,
`t5c_summary.json`.

## 2. Storm event

From Q1 ERA5, the peak wind is **2020-03-16 18:00 UTC**:

| Quantity | Value |
|---|---|
| max wind speed (domain) | **26.86 m/s** |
| max u10 / v10 | 24.57 / 20.43 m/s |
| model max \|τ\| at day 69 | **0.609 Pa** |
| model response day 65→69 | Umax 0.53→239.1 m/s, KE 4.88e14→**1.96e18 J** |
| day 70 | first NaN (config 3); day 74 config 4 |

The failure develops during the March storm, not during the January spin-up.
`docs/wiki/stages/stage11/evidence/t5c_storm_analysis.json`.

## 3. Seasonal validation

No configuration passed the 90-day gate, so there is **no chosen
configuration** and the “April with chosen configuration” requirement cannot
be satisfied. The T5 April baseline (Δt=1800, Ah=10000) was already stable:
KE30/KE15 **1.541**, max |U| 0.866 m/s, seasonally consistent with January.
`t5c_april_results.json` records this baseline as the seasonal reference only.

## 4. Trade-offs / interpretation

The prescribed Δt/Ah search does not find a storm-safe setting:

- Δt=900/Ah=20000: best early stability, but still explosive at day 63.
- Δt=900/Ah=30000 and Δt=600/Ah=30000: only delay the first NaN to day 67/70.
- Δt=600/Ah=50000: delays to day 74; still fails; stronger dissipation damps
  physical eddies without removing the storm instability.
- The failure is therefore **not a simple ocean momentum CFL/Ah limit**; the
  next stage must isolate the storm-time CA/advection/thermodynamic path
  (and possibly the ice/atmosphere coupling) before another configuration is
  promoted.

## 5. Acceptance

| Criterion | Result |
|---|---|
| 90-day run without NaN/Inf | **FAIL** (no config) |
| KE90/KE60 < 5 | not meaningful (invalid state; values 8e-5–1e-4 after NaN) |
| max \|U\| < 5 m/s | **FAIL** (all configs) |
| Storm analysis documented | **PASS** |
| April with chosen config | **N/A** — no chosen config |
| Regression / CI | **PASS / GREEN** |

**T5-CORRECTIVE: FAIL. T6: NO-GO. Next: T5-CORRECTIVE-2.**

## 6. Final configuration

**None.** Do not promote a storm-safe Δt/Ah; the search failed.

## 7. Pipeline hygiene

Full `fpm test` **60/60**, strict build 0; H-2 PASS; T-23 FIXED; ERA5
120/120; snowfall CONFIRMED_1H; `git diff --check` clean. No ocean
physics/EOS/scheduler change; T6 not started; no `data/runs/` data deleted.
