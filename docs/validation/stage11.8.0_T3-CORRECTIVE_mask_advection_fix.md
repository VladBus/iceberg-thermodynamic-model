# Stage 11.8.0 T3-CORRECTIVE — Mask Gap + Advection Boundary Fixes

**Status:** COMPLETE — **T-28 and T-29 FIXED; rest state still UNSTABLE (core T-03)**
**Date:** 2026-10-24
**Base commit:** `955abf4` (T3)
**Scope:** bug fixes in the EN4 builder/reader and the FCT advection writeback,
plus re-verification. No physics formula, EOS, scheduler or numerical scheme
change; `EOS_MODE=LEGACY` remains default.

---

## 1. T-28 — product/runtime wet-mask gap: **FIXED (Option C)**

**Mechanism:** the EN4 product was built on the pre-smoothing mask (11,067
columns / 143,176 level cells); the runtime mask after `coup1` smoothing is
143,422. For 796 columns / 934 levels the product stored T=S=0; the reader
loaded T=0 °C at those wet levels (S was repaired from above, T was not).

**Fix (belt and braces):**
1. **Builder** (`python/ocean/build_initial_ts.py`): new `--mask-dump`
   (default `build/grid_dump_kt1.dat`, the authoritative runtime `kt1`
   written by `test/grid_dump`). When present, the builder regrids and writes
   `water_column_levels` on that exact mask, filling levels below the EN4
   data with the deepest/finite value (no zeros). Provenance attr
   `mask_source` records the dump.
2. **Reader** (`src/initial_ocean_reader.f90`): reads the product
   `water_column_levels` and **FATALs** if it differs from the runtime `kt`
   (clear rebuild instruction); after loading/repair it **FATALs** if any wet
   cell still holds the unfilled `T=0,S=0` pair.

**Verification:** all **8 products** (4 seasons × canonical/rebuild) now have
**143,422 level cells**, **0 unfilled pairs**, **0 S≤0** wet cells, correct
600 m z-grid and 0 cells below Tf. New
`python/tests/ocean/test_mask_consistency.py` → **CLEAN (8/8)**;
`data/validation/mask_consistency_result.json`.

## 2. T-29 — advection boundary zeroing: **FIXED (Option A)**

**Mechanism:** `advection_3d_t/s` computed `cd` only on `1..is, 1..js` but
wrote `t2/s2 = cd` over the **full** array; the `i=is1`/`j=js1` boundary was
never written and became 0 at the first call (1,341 T=S=0 cells by day 1).

**Fix:** write back only the interior:
```
t2(1:is, 1:js, :) = cd(1:is, 1:js, :)
s2(1:is, 1:js, :) = cd(1:is, 1:js, :)
```
Boundary values are preserved from the previous state; interior numerics
unchanged.

**Verification:** new `test/test_advection_boundary.f90` (uniform S=0.035,
T=5 °C, zero velocity, all wet) → **PASS** (0 interior and 0 boundary
violations). Proven red: reverting the writeback makes the test exit 1;
restoring it exits 0. `data/validation/advection_boundary_result.json`.
In the rest run, day-1 S=0 cells fell from **1,341 to 0** and the boundary S
mean is preserved (0.034704).

## 3. T3 re-run after the fixes (30 days, zero forcing)

| Metric | LEGACY pre → post | EOS80 pre → post |
|---|---|---|
| Days / NaN | 30 / none → 30 / none | 30 / none → 30 / none |
| Max \|U\| (m/s) | 3.859 → **3.924** | 4.481 → **4.713** |
| Max \|V\| (m/s) | 5.912 → **5.498** | 4.706 → **6.021** |
| Max \|W\| (m/s) | 0.041 → 0.043 | 0.049 → 0.052 |
| KE day 0/15/30 (×10¹⁵ J) | 0 / 0.218 / 13.2 → 0 / 0.169 / **8.09** | 0 / 0.107 / 9.74 → 0 / 0.079 / **6.84** |
| KE growth (from day 1) | ×1128 → **×737** | ×911 → **×674** |
| T RMS drift (°C) | 0.405 → **0.337** | 0.254 → **0.147** |
| S RMS drift (PSU) | 3.40 → **0.432** | 3.38 → **0.311** |
| Heat conservation rel | 8.17e-3 → **3.18e-4** | 5.91e-3 → **2.04e-3** |
| Salt conservation rel | 1.46e-2 → **2.45e-3** | 1.33e-2 → **1.51e-3** |
| CA | 5.40e6/day, guard `***` | 2.48e4/day, guard 0 |
| T-28/T-29 markers | 934/1341 → **0/0** | 934/1341 → **0/0** |
| Classification | UNSTABLE → **UNSTABLE** | UNSTABLE → **UNSTABLE** |

**Interpretation:** the two interface defects are eliminated and
conservation/drift improve substantially (heat ×26, salt ×6, S-drift ×8), but
the current still grows to ~4–6 m/s. Since EOS-80 (CA converges, guard 0)
behaves almost identically to LEGACY, **the remaining driver is the core
pressure-gradient/velocity instability (T-03 family), not CA (T-25) and not
the fixed interface defects.** The day-1 0.068 m/s current also contains the
physical geostrophic adjustment of a zero-velocity state over a 3-D density
field; the exponential 30-day growth is the defect.

New baseline: `data/runs/t3c_legacy_canonical/`,
`data/runs/t3c_eos80_canonical/` + `data/validation/t3_rest_fix_result.json`;
the pre-fix `t3_*` runs remain as the defect baseline.

## 4. `data/runs/` inventory (recommendations only — NOTHING DELETED)

| Class | Runs | Size |
|---|---|---|
| CRITICAL (T3/T3c + current 11.7E4/11.8 diagnostics) | 13 | **1.9 GB** |
| ARCHIVE (older stages 10.x/11.1–11.7) | 161 | **40.5 GB** |
| TEMPORARY (test/probe/smoke runs) | 25 | **2.7 GB** |
| **Total** | 199 | **44.08 GB** |

Recommended (not executed, requires user approval): compress ARCHIVE
(~3× gzip, ≈27 GB saved) and delete TEMPORARY (2.7 GB) → **≈29.7 GB
potential savings**. Report: `data/validation/runs_inventory_result.json`
(also written to `data/runs_inventory.json`, gitignored).

## 5. Regression and CI

| Check | Result |
|---|---|
| Full `fpm test` | exit 0 — **60/60** (59 + advection-boundary test), 0 failures |
| Strict build | exit 0 |
| ERA5 / sea-ice / provenance | 120 / 33 / 28 |
| Ice coverage / sea-ice provenance | 16 / 8 |
| Snowfall / EN4 T0 / T3-PREP / mask consistency | CONFIRMED_12H / CLEAN / CLEAN / CLEAN |
| ERA5 coverage | unchanged (T-21 accepted, H-2 for T4) |
| T1 spatial/temporal/wrap | WARNING / PASS / RED_CONFIRMED |
| T2 homogeneous/weak/conservation/compressibility | PASS / PASS / PASS / CRITICAL_CONFIRMED |
| Advection boundary | PASS |
| `git diff --check` | clean |
| GitHub Actions | green on the pushed commit |

## 6. GO/NO-GO for T4

**NO-GO for T4** — the rest test still fails (|U|,|V| ≈ 4–6 m/s, KE grows
×674–×737). T-28/T-29 are closed; the next step is **T3-CORRECTIVE-2: core
T-03 investigation** (pressure-gradient/geostrophic adjustment; options:
balanced initialization for the rest test, potential-density CA per T-25,
and the numerical pressure-gradient discretization). Acceptance remains:
|U|,|V| < 0.01 m/s, no KE growth, conservation < 1e-4. T4 also still needs
T-23 (T1-CORRECTIVE wrap) and H-2 (rotation).

## 7. Confirmations

- No physics formula, EOS, scheduler or numerical scheme change; the only
  code changes are the T-28 reader checks, the T-29 advection **writeback
  restriction** (bug fix), and the builder mask option. `EOS_MODE=LEGACY`
  remains the default.
- T-25, T-23 and H-2 were NOT fixed (scheduled as before).
- No `data/runs/` directory was deleted or archived; recommendations only.
- T4–T6 not started.
