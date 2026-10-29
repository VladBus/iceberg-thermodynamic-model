# Stage 11.8.0 T5-CORRECTIVE-3 — Monotone Advection + Boundary Sponge

**Status:** COMPLETE — **FAIL** (no storm-safe configuration; RO<0).
**Date:** 2026-10-25
**Base:** `8d98932` (T5-CORRECTIVE-2)
**D-33:** all new switches default OFF; production legacy branch bit-identical.

---

## 1. Phase 0 — Reference findings

Reference files were copied to `docs/references/` (`Dmitriev_1995.txt`,
`Nesterov_last.txt`, `model_all.txt`). `Iceberg_1.docx` and
`Iceberg_Voxel_Thermal_Model.docx` are absent.

Key finding: the original `ADVS` is **FCT with a Zalesak limiter**, not central
differences; the current code is the same FCT (T-29 boundary fix included).
Original boundary conditions are no-gradient copies on three edges; there is
no radiation/sponge in the reference. Full details:
`t5c3_reference_findings.md`.

## 2. Phase 1 — Monotone/positive salinity implementation

Switch: `STAGE118_MONOTONE_ADVECTION` (default OFF).

Because the existing FCT already applies the Zalesak limiter, the switch adds
the requested explicit safety net after `advs`:

- `S = min(max(S, 0), S_max_initial)` on wet cells (hard positivity/no-new
  global maximum);
- temperature is bounded to `[-2, 30] °C` by the same switch (needed to stop
  the observed nonphysical T extrema; documented as a safety net, not a
  physics correction).

Default OFF preserves the legacy path bit-identically.

**Test:** `test/test_monotone_advection.f90` — sharp S gradient, uniform
velocity; S min 0, S max 0.035, negative cells **0** → **PASS**
(`docs/wiki/stages/stage11/evidence/t5c3_monotone_test.json`).

## 3. Phase 2 — Boundary sponge

Switch: `STAGE118_SPONGE_BOUNDARY` (default OFF), `STAGE118_SPONGE_ALPHA`
(default 1/day). Five-cell band, exponential ramp, applied after
advection/CA and before Block 200:

```
U,V,UP,VP *= max(0, 1 - (alpha/86400)·dt·ramp)
```

**Test:** `test/test_sponge_boundary.f90` — boundary pulse 1.0 → 0.9583;
interior unchanged 1.0 → **PASS**
(`docs/wiki/stages/stage11/evidence/t5c3_sponge_test.json`).

## 4. Phase 3 — 90-day Config 1 with both fixes (FAIL)

Configuration: dt=900, Ah=20000, monotone ON, sponge ON, alpha=1/day, all T4
switches, LEGACY, Q1 ERA5.

| Metric | Value |
|---|---|
| Days completed | **90** |
| NaN/Inf | **0** |
| max \|U\| / \|V\| / \|W\| | **1.141 / 0.682 / 0.0024 m/s** |
| KE day 30 / 60 / 90 | 5.155e14 / 6.106e14 / 5.951e14 J |
| **KE90/KE60** | **0.975** (<5) |
| S min / max | **0 / 37.07 PSU** |
| T min / max | **−2 / 30 °C** |
| **RO min** | **−24.24 kg/m³** |
| **RO-negative cells day 90** | **3,187** |
| Heat / salt relative drift | 5.99e-3 / 5.78e-3 |

The hard S/T bounds eliminate NaN and satisfy the KE/max-U/S/T bounds, but
create **nonphysical S=0/T=30 combinations with negative density**. The
acceptance criterion `RO > 0` **fails**. Without the T bound the run returned
NaN; the hard range is a safety net, not a consistent density fix.

`docs/wiki/stages/stage11/evidence/t5c3_90day_with_fixes.json`.

## 5. Phase 4 — April 30-day with fixes (PASS)

Configuration identical to Phase 3, April EN4/ERA5:

| Metric | Value |
|---|---|
| max \|U\| / \|V\| | 0.853 / 0.539 m/s |
| KE day 15 / 30 | 2.384e14 / 3.647e14 J |
| **KE30/KE15** | **1.530** (<10) |
| Volume / heat / salt | 0 / 9.10e-3 / 3.75e-4 |

Seasonal stability passes; the hard caps are active but do not break April.
`docs/wiki/stages/stage11/evidence/t5c3_april_with_fixes.json`.

## 6. Trade-offs

- Hard positivity/extrema caps are **strongly diffusive** and can create
  physically inconsistent S/T pairs; the RO<0 result demonstrates that a
  tracer cap alone is not a valid density fix.
- Sponge width 5, α=1/day damps the boundary pulse as required but does not
  repair interior tracer/density corruption.
- The existing FCT already includes Zalesak monotone limiting; a separate
  Sweby limiter would duplicate it. The remaining failure is the **density/
  thermodynamic coupling**, not the absence of a monotone salinity flux.

## 7. T6 decision

**T6 remains NO-GO.** T5-CORRECTIVE-4 must address the coupled density/
thermodynamic path (or accept the limitation); monkey-patching S/T bounds is
not acceptable production physics.

## 8. Regression

Full `fpm test` **62/62** (including the two new tests), strict build 0;
default legacy bit-identity unchanged; H-2 PASS; T-23 FIXED; ERA5 120/120;
snowfall CONFIRMED_1H; `git diff --check` clean. No ocean physics/EOS/scheduler
change; D-33 switches default OFF.
