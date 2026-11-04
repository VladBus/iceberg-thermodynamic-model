# Stage 11.8.0 T6-SEASONAL — Seasonal Validation + Production Scheduler

**Status:** COMPLETE — **11.8A GO** (matrix specified, not executed).
**Date:** 2026-10-25
**Base:** `e06a583`

---

## 1. T5 long-run limitation — ACCEPTED (T-38)

The T5 chain is formally closed with an accepted limitation:

| Attempt | Config | Failure |
|---|---|---|
| T5-C1 | dt900/Ah20000 | FPE after day63; Umax 1361 |
| T5-C2 | diagnostics | advection primary; boundary amplifier |
| T5-C3 | monotone+sponge | no NaN, but RO min −24.24 / 3,187 cells |
| T5-C4 | density repair | CA/B200 recreate RO<0; NaN day69 |

**Root cause:** systemic explicit-scheme/resolution limitation — 13.89 km grid
vs 2.36 km first baroclinic Rossby radius; advection→CA→B200 recreates
negative density faster than repair. **30-day forced runs are validated**
(Jan T4, Apr T5, Jul/Oct T6); **90-day runs are not validated**. T-38 records
future work (implicit fast-wave coupling, full FCT with positivity, adaptive
Δt/local CFL, wind-stress capping, finer/telescoping grid). This is **not a
blocker for 11.8A** or iceberg-drift applications.

## 2. July 30-day (standard config, LEGACY, N=1)

| Metric | Value |
|---|---|
| max \|U\| / \|V\| | **0.542 / 0.549 m/s** |
| KE15 / KE30 | 2.325e14 / 1.923e14 J |
| **KE30/KE15** | **0.827** (<5) |
| T min / max | −1.86 / 11.82 °C |
| S min / max | 21.91 / 35.23 PSU |
| **RO min** | **0** (0 negative cells) |
| NaN/Inf | **0** |
| Volume / heat / salt | 0 / 4.86e-3 / 4.82e-4 |

**PASS.** (11 day-0 T=0 cells carry S=0.0339, i.e. physical freezing, not
unfilled T=0/S=0 pairs.) `t6s_july_results.json`.

## 3. October 30-day (standard config, LEGACY, N=1)

| Metric | Value |
|---|---|
| max \|U\| / \|V\| | **0.690 / 0.451 m/s** |
| KE15 / KE30 | 2.189e14 / 4.711e14 J |
| **KE30/KE15** | **2.152** (<5) |
| T min / max | −2.06 / 9.30 °C |
| S min / max | 25.01 / 35.26 PSU |
| **RO min** | **0** (0 negative cells) |
| NaN/Inf | **0** |
| Volume / heat / salt | 0 / 2.62e-3 / 6.18e-4 |

**PASS.** `t6s_october_results.json`.

## 4. Production scheduler retest (55/360 blocker)

Configuration: January, standard protective set, **`STAGE115H_PRODUCTION_MODE=true`**,
LEGACY. The production scheduler forces OCEAN_DT=150 s, 24 fires/day ×24
passes, shal 1×/day (self-contained, no silent fallback).

| Metric | Value |
|---|---|
| Days completed | **30/30** |
| Production fire-steps | **720/720** (360/360 canonical 12-step days) |
| Historical blocker | **RESOLVED for the 30-day standard configuration** |
| max \|U\| / \|V\| | 0.494 / 0.487 m/s |
| KE15 / KE30 | 5.155e14 / 7.628e14 J |
| KE30/KE15 | **1.480** |
| T / S bounds | −1.95…7.08 °C / 31.52…37.07 PSU |
| RO min | **0** (0 negative cells) |
| NaN/Inf | **0** |
| Volume / heat / salt | 0 / 0.2028 / 6.79e-4 |

**Verdict:** the historical 55/360 NaN blocker does **not** reproduce with the
Stage 11.8 fixes. Production scheduler is viable for the 30-day matrix.
`t6s_production_results.json`.

**EOS80 + production 10-day smoke:** PASS (10/10 days, max |U| 0.405,
RO min 0, NaN 0). Early signal only; 30-day EOS80 production cells remain to
be run in 11.8A. `t6s_eos80_smoke.json`.

## 5. 11.8A matrix

Specification: `docs/validation/stage11.8A_matrix_plan.md`.
Dimensions **EOS {LEGACY,EOS80} × scheduler {N1, PRODUCTION} × season
{Jan,Apr,Jul,Oct} = 16 cells**, 30 days each, standard protective config.
Gates: no NaN; KE30/KE15<5; max |U|<2 (seasonal) / documented; S≥0; RO≥0;
volume 0; salt<1e-3; heat via T-34; production 720/720.

**D-29 rule:** EOS80 promoted only if all EOS80 cells pass, it is equivalent or
better on a documented metric, and no scheduler interaction pathology;
otherwise EOS80 remains optional and “EOS-80 in production” is recorded NOT
MET. D-28 is unchanged.

**Storage:** ~299 MB per 30-day run → ~4.8 GB for 16 cells (EOS80 production
~0.34 GB/cell); disk free 857 GB; existing runs 44.08 GB with an archive
recommendation pending user approval; no deletion performed.

**Ice caveat:** January uses real OSI-SAF/C3S ice; Apr/Jul/Oct still use
January-derived/diagnostic `1_*.ice` initialization and are **not
OSI-SAF-validated**. Matrix ice diagnostics will be labeled accordingly.

## 6. GO/NO-GO

**11.8A execution: GO.** All four seasons pass the 30-day N=1 LEGACY gate;
the production scheduler passes 30/30 days; EOS80 production smoke is stable.
Matrix execution is **not** started in this stage.

## 7. Regression

Full `fpm test` 63/63, strict build 0; default 1-day legacy md5 identical;
H-2 PASS; T-23 FIXED; ERA5 120/120; snowfall CONFIRMED_1H; `git diff --check`
clean. No physics/EOS/scheduler code change; switches default OFF;
`EOS_MODE=LEGACY` default; no `data/runs/` deletion.
