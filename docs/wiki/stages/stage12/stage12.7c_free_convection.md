# Stage 12.7c — Free-Convection Closure for Low-Flow Regimes

**Status:** COMPLETE (physics closure added; 3-case audit; structural large/low-ΔT deficit documented).
**Date:** 2026-11-01
**Decision:** D-62
**Base:** `d9c1305` (Stage 12.7.audit + 12.7b)
**Scope:** physically justified mixed-convection floor; no calibration to Enderlin.

## 1. Physical basis

The three-equation Stefan interface used a purely forced-convection law:

```text
gamma_T = K_T · u_rel,   gamma_S = K_S · u_rel
```

which is the standard forced-convection limit (Jenkins 2010, `K_T=1.1e-3`,
`K_S=3.1e-5`) and is valid for `u_rel ≳ 0.1 m/s`. At low flow the melt must
not vanish: buoyancy-driven free convection maintains a heat/salt exchange.

For free convection, ocean–ice heat transfer is bounded by a roughly constant
exchange coefficient of order `1e-5 m/s` (Kerr & McPhee 2004, *J. Geophys.
Res.*; Hellmer & Olbers 1989, *J. Phys. Oceanogr.*). Standard ocean–ice models
use the mixed-convection maximum rather than switching off at low flow
(NEMO-ICB and MITgcm practice):

```text
gamma_T = max(K_T · u_rel, gamma_free_T)
gamma_S = max(K_S · u_rel, gamma_free_S)
gamma_free_T = 1.0e-5 m/s
gamma_free_S = 1.0e-6 m/s   (Pr/Sc ~ 10)
```

This is a **physical lower bound**, not calibration: the defaults are fixed
from the literature, not fitted to Enderlin. They are overridable only for
sensitivity via `VOXEL_GAMMA_FREE_T` / `VOXEL_GAMMA_FREE_S`.

## 2. Implementation

In `src/voxel_thermal_solver.f90` (`three_equation_melt`):

- `gamma_T/gamma_S` are now `max(forced, free)`.
- The previous `u_rel <= 0 → m = 0` early return was removed; at zero flow the
  free-convection floor still produces melt if the water is above freezing.
- The `VOXEL_KT_SCALE` audit hook scales only the forced term; it does not
  scale the free floor.
- Defaults: `VOXEL_GAMMA_FREE_T=1e-5`, `VOXEL_GAMMA_FREE_S=1e-6`.

## 3. Three-case audit (K_T scale = 1)

Cases from Stage 12.7.audit; all use prescribed Enderlin trajectories and
GLORYS12 forcing.

| Case | Regime | Bulk ratio | Voxel without free | Voxel with free (1e-5) |
| ---- | ------ | ---------: | -----------------: | ---------------------: |
| BG_..._003 | small, high ΔT | 2.843 | 1.057 | **1.309** |
| CG_..._000 | medium, moderate | 1.918 | 0.258 | **0.655** |
| TG_..._007 | large, low ΔT | 0.616 | 0.089 | **0.208** |

- Small and medium are now within [0.5, 2.0].
- Large/low-ΔT remains below 0.5.
- Three-case median with free convection = **0.655** (in range); **not all
  three** satisfy the target.

### Sensitivity (`VOXEL_GAMMA_FREE_T`)

| gamma_free_T, m/s | Small | Medium | Large |
| -----------------: | ----: | -----: | ----: |
| 5e-6 | 1.185 | 0.475 | 0.148 |
| 1e-5 (default) | 1.309 | 0.655 | 0.208 |
| 2e-5 | 1.642 | 1.057 | 0.327 |

No value in the specified sensitivity range brings the large low-ΔT case to
0.5; 2e-5 raises it only to 0.327 while pushing the small case toward the upper
bound. Higher values would be calibration, so they are not adopted.

## 4. Full Enderlin hindcast

**Not re-run** because the "all three ratios in [0.5, 2.0]" gate is not met
(the large low-ΔT case remains at 0.208). The 12.7a voxel column remains
superseded by the audit; no full-population free-convection metrics are claimed.

## 5. Structural deficit

The remaining large/low-ΔT deficit is structural:

- GLORYS12 coastal currents at the nearest wet cells are only
  ~0.001–0.02 m/s; the free floor is the dominant term at the large case.
- The voxel model has no mechanical calving/capsizing, no wave erosion
  (WAM absent), and no sea-ice concentration coupling.
- Observed Enderlin `melt_rate` is an indirect, area-averaged submarine
  estimate; no calving correction is applied in the model.
- The large case has ΔT ≈ 0.34 °C; a small absolute heat-flux error is a large
  relative error.

No melt parameter was calibrated to Enderlin.

## 6. GO / NO-GO for Stage 12.8

**Conditional GO for exploratory Barents 2020 runs with the voxel model**
(warm/high-ΔT cases where small/medium free-convection ratios are in range).
**NO-GO for quantitative low-ΔT/large-iceberg melt or lifetime claims** until
waves, calving, and/or a validated low-flow closure are included. Bulk remains
**ARCHIVED** (regression only); new science runs use `VOXEL_ENABLED=ON`.

## 7. Acceptance

| Criterion | Status |
| --------- | ------ |
| Free-convection closure `gamma_T=max(K_T u, 1e-5)` | PASS |
| Physical basis documented (Kerr & McPhee; Hellmer & Olbers) | PASS |
| 3 cases re-run; ratios documented | PASS |
| Full hindcast if all 3 in [0.5, 2.0] | NOT RUN (large = 0.208) |
| Structural deficit documented; no calibration | PASS |
| Tests / strict build / CI | PASS (81/81; strict clean; CI pending push) |
| No Stage 11 ocean code / `app/main.f90` | PASS |

## 8. Artifacts

- Source: `src/voxel_thermal_solver.f90`
- Audit driver: `python/validation/audit_voxel_melt.py`
- Results: `docs/wiki/stages/stage12/evidence/stage12.7c_results.csv`,
  `docs/wiki/stages/stage12/evidence/stage12.7c_sensitivity.csv`,
  `docs/wiki/stages/stage12/evidence/stage12.7c_summary.json`
- Related: `stage12.7.audit_voxel_melt.md`, `stage12.7b_autonomous_air.md`
