# Stage 12.7.audit — Voxel Melt Deficiency

**Status:** COMPLETE (bug fixed; residual structural deficit documented).
**Date:** 2026-11-01
**Decision:** D-60
**Base:** `65c97f9` (clean; docs-only note after `b2eb7d7`)
**Scope:** diagnose the ~17× voxel under-melt found in Stage 12.7a. No calibration.

## 1. Representative cases

Selected from `docs/wiki/stages/stage12/evidence/stage12.7a_trajectory_manifest.csv` and
`docs/wiki/stages/stage12/evidence/stage12.7a_results.csv`:

| Case | Regime | √A, m | mean ΔT, °C | observed melt, m/day | baseline voxel ratio |
| ---- | ------ | ----: | ----------: | -------------------: | -------------------: |
| `BG_20160825133704-..._003` | small, high ΔT | 60.9 | 2.62 | 0.02857 | 0.218 |
| `CG_20201013133346-..._000` | medium, moderate | 163.6 | 1.50 | 0.02733 | 0.093 |
| `TG_20191011185555-..._007` | large, low ΔT | 644.5 | 0.34 | 0.02335 | 0.113 |

Baseline = Stage 12.7a production voxel code before this audit.

## 2. Hypotheses

### H3 — submerged area / fixed voxel geometry — **ROOT CAUSE**

`voxel_model_configure()` always initialized the production voxel grid as
**10×10×10 cells at 10 m = a 100 m cube**, independent of the iceberg’s
`state%L/W/H`. The voxel area was therefore ~46,000 m² for every case, while
the actual analytical prism areas are:

| Case | Actual L×W×H, m | Actual area, m² | Baseline voxel area, m² | Ratio |
| ---- | --------------: | --------------: | ----------------------: | ----: |
| small | 61×61×49.7 | ~14,400 | 46,000 | 3.2× too large |
| medium | 164×164×78.6 | ~72,300 | 46,000 | 0.64× |
| large | 645×645×323.8 | ~1,154,000 | 46,000 | 0.04× (25× too small) |

This produces exactly the observed size trend: large icebergs under-melt,
small ones are less affected. The mismatch is a **configuration bug**, not a
K_T problem.

### H1 — K_T scale — not the root cause; not applied

`VOXEL_KT_SCALE` was added (audit hook only). Ratios at scale 1/5/10:

| Case | K_T=1 | K_T=5 | K_T=10 |
| ---- | ----: | ----: | -----: |
| small | 1.058 | 6.545 | 13.101 |
| medium | 0.258 | 0.890 | 1.852 |
| large | 0.089 | 0.439 | 0.868 |

No single scale is physically justified or uniform across regimes; scaling
K_T by 5–10 would be calibration to Enderlin. **Not permanently applied.**

### H2 — relative velocity — **not a bug**

Prescribed mode sets `state%u=v=0`, but the observed trajectory speeds are
tiny (mean ≈ 0–1.0×10⁻⁴ m/s), so `u_rel=|u_ocean|` is correct. The actual
GLORYS coastal currents at the nearest wet cells are only 0.001–0.02 m/s;
the voxel mean `u_rel` is 0.0012–0.0039 m/s for medium/large. No trajectory-
derivative correction is needed.

### H4 — wave erosion — **not testable with current data**

No WAM product is staged. A synthetic `Hs=2 m` run (`ICEBERG_WAVE_CONST_HS=2`,
`siconc=0` because sea ice was not extracted) gives wave mass loss
1.17×10⁸ kg versus submarine 2.05×10⁷ kg for the small case (final volume
3.37×10⁴ vs 1.62×10⁵ m³). This is **not representative**: with no `siconc`
the Bigg factor is maximal. Wave erosion remains OFF; H4 requires WAM and
sea-ice concentration.

## 3. Fixes applied

1. **Geometry initialization:** the voxel grid is now initialized from the
   iceberg state on the first thermodynamic step:
   `dx=L/nx`, `dy=W/ny`, `dz=H/nz`. Voxel mass/area/draft now match the prism
   (small 14.6k vs 14.4k m²; large 1.166M vs 1.154M m²).
2. **kg/s → geometry mapping:** `voxel_model_step` now converts basal/lateral
   mass loss using the same areas that `iceberg_update_geometry` multiplies:
   `m_basal=basal/(ρ L W)`, `m_lateral=lat/(ρ H(L+W))`. This preserves the
   voxel’s own kg/s in the coupled mass budget.
3. **Autonomous air balance:** exposed faces no longer use bulk
   `diag%q_net_surface` (D-61), so surface energy is independent.

## 4. Updated three-case results (K_T=1)

| Case | Bulk ratio | Voxel ratio (baseline) | Voxel ratio (fixed) |
| ---- | ---------: | ---------------------: | ------------------: |
| small | 2.843 | 0.218 | **1.057** |
| medium | 1.918 | 0.093 | **0.258** |
| large | 0.616 | 0.113 | **0.089** |

Three-case median voxel ratio = **0.258**, below the [0.5, 2.0] target.
Small/high-ΔT now agrees; medium/large remain low because GLORYS coastal
currents are weak (0.001–0.02 m/s) and the three-equation forced-convection
melt vanishes at low `u_rel`. This is a **structural limit** (no free-
convection/low-flow floor, no waves, no calving), not a remaining geometry bug.

The Stage 12.7a voxel column (median 0.059) was produced with the fixed-cube
bug and is **superseded**; the bulk column is unaffected.

## 5. Conclusion

- The ~17× deficit had two components: (i) the fixed 100 m voxel cube
  (dominant, size-dependent), and (ii) incorrect kg/s→bulk-area mapping.
  Both are fixed.
- The residual medium/large deficit is structural: three-equation forced
  convection at weak GLORYS currents + no waves/free convection/calving.
- H1 scaling is not a valid fix; no melt parameter was calibrated.
- **Stage 12.8 voxel-driven Barents experiments: NO-GO** until a physically
  justified low-flow/free-convection closure (or an approved calibration
  stage 12.7c) is added.

## 6. Artifacts

- Audit driver: `python/validation/audit_voxel_melt.py`
- Results: `docs/wiki/stages/stage12/evidence/stage12.7.audit_results.csv`
- Baseline/fixed JSON: local `data/validation/results/audit_voxel_*/audit.json`
- Air balance: `docs/wiki/stages/stage12/stage12.7b_autonomous_air.md`, D-61
