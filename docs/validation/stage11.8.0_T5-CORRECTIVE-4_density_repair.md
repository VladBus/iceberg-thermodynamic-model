# Stage 11.8.0 T5-CORRECTIVE-4 — Density Repair

**Status:** COMPLETE — **FAIL** (90-day still NaN; no storm-safe configuration).
**Date:** 2026-10-25
**Base:** `fefdaeb` (T5-CORRECTIVE-3)
**D-33:** all new switches default OFF; production legacy branch unchanged.

---

## 1. Phase 0 — .docx files / reference findings

`Iceberg_1.docx` and `Iceberg_Voxel_Thermal_Model.docx` are **absent** from the
workspace and from `/home/vlad`; they could not be copied. The added
`docs/references/Iceberg/Iceberg_Voxel_Thermal_Model_8.pdf` was read: it covers
the voxel iceberg heat-conduction/Stefan model and its **ice** stability
condition; it contains no ocean EOS, density, CA, salinity-advection, or storm
guidance. Details: `t5c4_reference_findings.md`.

## 2. Phase 1 — hard T caps removed

`STAGE118_MONOTONE_ADVECTION` no longer applies `T∈[−2,30]`. It now keeps:

- **S positivity** `S = max(S,0)` and no-new-S-maximum;
- **T no-new-maximum** (`T ≤ max(T_old)`) but **no hard T bounds**.

The previous hard caps were the cause of nonphysical S=0/T=30 states and
RO<0. `test_monotone_advection` still passes (S≥0, no new extrema).

## 3. Phase 2 — density repair

`STAGE118_DENSITY_REPAIR` (default OFF) runs after advection and before CA.
For each wet cell with `RO<0`, it computes dRO/dT and dRO/dS numerically from
the active EOS and applies the smaller-magnitude tracer correction to reach
`RO≥0` (target margin 1e-6 g/cm³). It adjusts only cells that are negative.

**Test:** `test/test_density_repair.f90` starts at T=30 °C, S=0:
RO **−0.0242 → +2.39e-4 g/cm³**, S **0 → 0.0326**, T unchanged → **PASS**
(`data/validation/t5c4_density_repair_test.json`).

## 4. Phase 3 — 90-day Config 1 with density repair (FAIL)

Configuration: dt=900, Ah=20000, monotone ON, density repair ON, sponge ON
(α=1/day), all T4 switches, LEGACY, Q1 ERA5.

| Metric | Value |
|---|---|
| Days completed | 90 (NaN from **day 69**) |
| max \|U\| | **34,027 m/s** |
| NaN cells day 90 | **261,804** |
| KE30 / 60 / 90 | 5.155e14 / 6.106e14 / 4.231e11 J (invalid after NaN) |
| KE90/KE60 | 6.93e-4 (invalid) |
| Day 65 T / S / RO | T max 168.7 °C; S max 57.1 PSU; **RO min −416.1**, 25 RO<0 cells |
| Heat / salt drift | 0.417 / 0.270 |

Density repair adjusted **139,620 cells/day**, but CA and the subsequent
momentum step recreate negative density; the run becomes NaN at day 69.
**FAIL** on no-NaN, max-U, RO>0.

`data/validation/t5c4_90day_density_repair.json`.

## 5. Phase 4 — April 30-day with density repair (PASS)

Same configuration, April EN4/ERA5:

| Metric | Value |
|---|---|
| max \|U\| / \|V\| | 0.853 / 0.539 m/s |
| KE30/KE15 | **1.530** (<10) |
| RO min day 30 | **0.0** (0 negative cells) |
| Volume / heat / salt | 0 / 9.10e-3 / 3.75e-4 |

April remains stable with repair; it does not exercise the March collapse.
`data/validation/t5c4_april_density_repair.json`.

## 6. Trade-offs and limitation

- The repair is sparse in principle but in the storm run it touches ~140k
  cells/day and changes salinity by O(0.03), i.e. it is not "minimal" in
  practice; CA immediately recreates negative density.
- Removing hard T caps restores physical T freedom but does not prevent the
  advective temperature runaway; the 90-day storm remains numerically
  unstable.
- April 30-day forced runs are stable; long-run forced operation is **not**
  validated.

## 7. Decision

**T6 remains NO-GO.** Accept the limitation: production/forced runs are
limited to the validated 30-day window unless a future dedicated
density/thermodynamic coupling stage is approved. Do not promote density
repair or monotone caps as a fix.

## 8. Regression

Full `fpm test` **63/63**, strict build 0; new density-repair, monotone, and
sponge tests pass; default 1-day legacy md5 identical; H-2 PASS; T-23 FIXED;
ERA5 120/120; snowfall CONFIRMED_1H; `git diff --check` clean. No EOS formula
change; D-33 switches default OFF.
