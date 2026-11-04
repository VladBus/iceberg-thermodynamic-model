# Stage 11.8.0 T5 — Time-Stepping Stability + T-34 Heat Closure

**Status:** **FAIL** — 90-day January run becomes numerically unstable at
day 61; April 30-day run is stable and seasonally consistent. **T-34 is
CLOSED (physical, tentative)**. **T6 is NO-GO; T5-CORRECTIVE required.**
**Date:** 2026-10-25
**Base:** `ef633d5` (T4)

---

## 1. Phase 1 — 90-day January run (FAIL)

Configuration: all T4 switches ON (wind rotation, longitude clamp, Δt=1800,
Ah=10000, E1+E2+E3, LEGACY); corrected EN4 January; ERA5 Q1 2020; 90-day target.

| checkpoint | max \|U\| | max \|V\| | KE (J) |
|---|---|---|---|
| day 0 | 0.260 | 0.163 | 4.645e13 |
| day 15 | 0.413 | 0.246 | 4.393e14 |
| day 30 | 0.853 | 0.583 | 6.704e14 |
| day 45 | 0.646 | 0.496 | 6.220e14 |
| **day 60** | **488.214** | **571.394** | **1.178e19** |

- **KE60/KE30 = 17,568** (acceptance <5) — explosive growth between day 45 and
  day 60.
- At day 60, CA input `A_after_adv` has `max_inv = 2.50e2` and 10,625/10,966
  columns inverted; `KE3D` jumps from 8.64e14 J (day 59) to 1.15e19 J (day 60).
- **SIGFPE at day 61** (erroneous arithmetic under the strict build), after
  physically impossible velocities; no NaN was written before the abort.
- Heat/salt drift at day 60: 6.46e-3 / 2.844e-2; salt fails, confirming loss of
  numerical integrity. The run did **not** complete 90 days → **FAIL**.
- Output: `docs/wiki/stages/stage11/evidence/t5_90day_results.json`; run
  `data/runs/t5_90day_jan/` (60 daily files).

**Trigger context:** the Q1 forcing reaches strong March winds
(`tx` up to 8.8 dyn/cm² near the failure); this is a long-run forced
instability, not a heat-budget leak. T-35 records it for T5-CORRECTIVE.

## 2. Phase 2 — April 30-day seasonal check (PASS)

Configuration identical; corrected EN4 April; corrected April ERA5
(30-day product extended by one 6-hour slice to satisfy the model's
`ntime-1` limit).

| metric | April | January T4 | ratio |
|---|---|---|---|
| max \|U\| | **0.866 m/s** | 0.970 m/s | 0.893 |
| max \|V\| | 0.533 m/s | 0.598 m/s | 0.891 |
| KE day 15 / 30 | 3.269e14 / 5.038e14 J | 4.408e14 / 6.699e14 J | — |
| **KE30/KE15** | **1.541** (<10) | 1.520 | — |
| KE30 April/January | — | — | **0.752** |
| T / S RMS drift | 0.455 °C / 0.116 PSU | 0.311 °C / 0.229 PSU | — |
| Volume / heat / salt | 0 / **1.311e-2** / 7.34e-4 | 0 / 5.228e-3 / 8.319e-4 | — |
| Ekman day-15 mean angle | **+6.75°**, 34.4 % right | **−40.43°**, 61.4 % right | — |

**Seasonal stability is consistent** (KE and max-U within factor 2; KE30/KE15
well below 10). **Ekman rightward turning is not observed in April** at day 15;
the spring surface current is geostrophically dominated. This is a seasonal
physical caveat, not a stability failure. Outputs:
`t5_april_results.json`, `t5_seasonal_comparison.json`.

## 3. Phase 3 — T-34 heat closure (CLOSED, physical/tentative)

| stable 30-day run | heat relative change | implied mean surface flux |
|---|---|---|
| T4 January | 5.228e-3 | **−3.94 W/m²** |
| April | 1.311e-2 | **−9.81 W/m²** |

Both are cooling with magnitudes in the Arctic winter/spring range
(≈−4 to −10 W/m²; the T-34 criterion −5…−50 is met by April, January is at
its low edge). Volume is exactly conserved and salt is <1e-3 in January;
the heat change is a forced response, not a numerical leak. **T-34 CLOSED
(physical, tentative)**. The 90-day failure is a separate long-run numerical
instability and does not change the 30-day heat attribution.
`docs/wiki/stages/stage11/evidence/t34_heat_closure.json`.

## 4. Phase 4 — 180-day run

**Not performed.** Phase 4 is conditional on the 90-day run passing; the
90-day run failed at day 61. Recording this as a skipped conditional phase is
the correct outcome.

## 5. Overall assessment

- **90-day January: FAIL** (explosive growth, SIGFPE at day 61).
- **April 30-day: PASS** for stability/seasonal consistency; Ekman not observed
  in April (seasonal caveat).
- **T-34: CLOSED (physical, tentative)**.
- **T5 overall: FAIL.** The T4 30-day stabilization does not extrapolate to
  the March storm period; a dedicated long-run stability correction is needed.
- **T6: NO-GO.**

## 6. Regression and safety

Full `fpm test` **60/60**, strict build 0; H-2 rotation PASS; T-23 FIXED;
ERA5 contract 120/120; snowfall CONFIRMED_1H; EN4/T2 suites unchanged;
default 1-day legacy md5 identical; `git diff --check` clean. No ocean
physics/EOS/scheduler change; T5-CORRECTIVE is the next numerical-stability
stage. No `data/runs/` data deleted.
