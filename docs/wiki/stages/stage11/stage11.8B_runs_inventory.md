# Stage 11.8B — data/runs Inventory & Cleanup Recommendations

**Status:** COMPLETE — inventory and recommendations only; **NO data deleted**.
**Date:** 2026-10-26
**Base:** `3a249cb` (Stage 11.8A Phase 2-ANALYSIS)
**Inventory JSON:** `docs/wiki/stages/stage11/evidence/runs_inventory_final.json`

---

## 1. Totals

| Metric | Value |
|---|---|
| Total size | **82.583 GB** (≈76.9 GiB on disk) |
| Top-level run directories | **289** |
| Root-level loose files | 0.711 MB |
| Previous 11.8A-era inventory | 44.08 GB (pre-matrix baseline) |
| Growth | ~38.5 GB from 11.8A matrix/production and verification runs |

The difference from the older 44.08 GB figure is expected: the 11.8A N=1
matrix, production diagnostics, OSM checks, and 11.8B default/reproducibility
verification runs were added after that inventory.

## 2. Classification

| Class | Count | Size | Policy / recommendation |
|---|---:|---:|---|
| **CRITICAL** | 83 | **31.734 GB** | Keep active; do not delete/archive |
| **ARCHIVE** | 153 | **40.563 GB** | tar + gzip (~3×); est. compressed **13.521 GB** |
| **TEMPORARY** | 47 | **8.629 GB** | Review then delete |
| **DUPLICATES** | 6 | **1.656 GB** | Keep newest; delete older after approval |
| **Estimated savings** | | **37.327 GB** | archive 2/3 + temporary + duplicates |

**Classification policy**

- **CRITICAL:** current 11.8A matrix cells, T3/T4/T5/T6 validation evidence,
  11.7E4 sea-ice provenance baselines, current canonical runs.
- **ARCHIVE:** historical stage 11.0–11.7 experiments and old baselines.
- **TEMPORARY:** `test_*`, probes, smokes, `*_default_check`, preliminary
  matrix/extrapolation runs, scripts.
- **DUPLICATES:** curated same-experiment reruns; keep the newest, remove the
  older copy only after approval.

## 3. Largest retained groups

**CRITICAL (top):** T5/T3 storm/freeze experiments (~0.9 GB each), current
11.8A matrix cells, T4/T6 seasonal baselines.

**ARCHIVE (top):** `stage11.5C1_janOFF2` (0.902 GB), `stage11.2_cfl_test`
(0.717 GB), `e2_synth_test` (0.509 GB), `e2_synthpresent_test` (0.402 GB).
These are historical experiments; no active analysis reads them.

**TEMPORARY (top):** `test_prov_allowed3` (0.549 GB), `test_prov_final`
(0.510 GB), `test_prov_allowed2`/`test_prov_force` (0.460 GB each), plus
repeated `*_default_check` runs (0.314 GB each).

**DUPLICATES:** six reruns of `stage11.5C1/11.5C2/11.5C6R` families
(0.109–0.314 GB each; 1.656 GB total). Keep the newest copy if the family is
still needed.

## 4. Recommendations (NOT executed)

1. **ARCHIVE:** `tar -czf` the 153 historical runs; expected ~13.5 GB after
   ~3× compression. This saves ~27.0 GB.
2. **TEMPORARY:** delete after review. This saves ~7.7 GB.
3. **DUPLICATES:** keep newest, remove the older six copies after approval.
   This saves ~1.7 GB.
4. **CRITICAL:** retain all 77 runs; the 11.8A matrix and T3–T6 evidence are
   release-critical.
5. Total estimated savings: **≈36.4 GB** (subject to actual gzip ratio and
   duplicate review).

**No files were deleted, moved, compressed, or archived in Stage 11.8B.**

## 5. Approval

Cleanup requires explicit user approval. Recommended execution order:
archive historical runs first, verify archive integrity, then delete
temporary/duplicate candidates. Critical runs must never be included.
