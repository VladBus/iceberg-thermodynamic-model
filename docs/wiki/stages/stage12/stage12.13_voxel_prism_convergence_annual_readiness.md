# Stage 12.13 — Voxel/prism unification, convergence, and annual readiness

**Date:** 2026-11-09  
**Status:** COMPLETE WITH OPEN LIMITATIONS; no 100^3 annual reference (8^3 diagnostic reruns only).  
**Scope:** voxel/prism state consistency, vertical repositioning, 1 m resolution
convergence, T/phi asymmetry, 2020 fallback forcing, sensitivity, visualization,
and an honest annual-run readiness decision. No calibration, no new downloads,
no commit, and no annual production claim.

## 1. Executive summary

The voxel representation is authoritative for mass, draft/freeboard, grounding,
and dynamics diagnostics. Prism mass/volume and draft/freeboard are synchronized
from the voxel state; prism height is derived from voxel mass and the current
prism footprint. Annual post-processing is now mass-consistent. The 1 m
(`100x100x100`) grid is the reference grid, but lower resolutions do not meet
the <1% mass-loss criterion: 70^3 differs from 100^3 by about 1.04%.
Consequently no annual 1 m run was promoted as a reference in this stage.

| Task | Result |
| --- | --- |
| Palettes, 3D cut-away, salinity plots | **PASS**; T `YlOrRd`, phi `Blues`, S `Greens`, shared scales |
| T/phi horizontal asymmetry | **PASS (not reproduced)**; T residual `3.02e-14`, phi `0.0` |
| Voxel/prism mass and draft/freeboard | **PASS**; relative mass difference `~1e-16`; draft/freeboard equal at output; L/W remain prism footprint |
| Vertical repositioning | **PARTIAL**; empty bottom layers removed, but buoyant re-floating not solved |
| Resolution convergence | **WARNING**; 70^3 vs 100^3 30-day mass loss differs by `1.04%` |
| Physical sensitivity | **PASS for tested range**; cap, phi_min, c_ice effects are small |
| Energy budget | **WARNING**; mass closes, full energy budget does not |
| 2020 fallback/calendar | **WARNING**; old point has 1,577 events; 78N/30E is fallback-free in 30-day tests |
| Annual 2020/2024 | **NOT PROMOTED**; 8^3 diagnostic reruns only; 100^3 annual not run |
| Documentation | **PASS**; this report and indexes updated |

## 2. Voxel/prism unification

The voxel body is the source of truth for mass, volume, draft, and freeboard.
`sync_prism_from_voxel` in `src/iceberg.f90` copies these quantities after each
melt/erosion update and derives prism `H = V/(L*W)` from the current prism
footprint. `iceberg_check_grounding` uses the voxel draft; boundary-layer
forcing is sampled from the actual remaining solid surface. The prism remains a
derived diagnostic/state surrogate for legacy dynamics; it cannot retain mass
after voxel melt-out. A zero-voxel-mass guard sets prism mass, volume, L/W/H,
draft, and freeboard to zero before dynamics. L/W are not taken from a voxel
envelope; they remain the lateral-melt prism footprint.

| Case | Voxel mass (kg) | Prism mass (kg) | Relative difference | Draft/freeboard |
| --- | ---: | ---: | ---: | --- |
| 50^3, 30 d | 873,873,856 | 873,873,856 | 0 | equal |
| 100^3, 30 d | 874,692,160 | 874,692,160 | 0 | equal |
| 2020 annual (8^3 test) | 12,649,387 | 12,649,387 | 0 | equal |
| 2024 annual (8^3 test) | 0 | 0 | 0 | equal |

Both annual checks use the Stage 12.13 8^3 diagnostic reruns (2020 365.0 d;
2024 268.8 d melt-out); no 100^3 annual output exists. The comparison script reports max relative mass error `≤2.3e-16`,
median `0`, and draft/freeboard differences at floating-point level. This supersedes the
Stage 12.12 observation of 12–15% median and >80% maximum draft divergence;
that divergence predates synchronization and remains historical evidence.

**Limit:** equality is partly enforced by synchronization. It verifies
bookkeeping, not independent geometric prediction; the prism is not an
independent estimate of the eroded body. L/W are still updated by the prism
lateral-melt path, not by a voxel envelope.

## 3. Vertical repositioning

`voxel_iceberg_compact_vertical` removes empty layers adjacent to the bottom and
reindexes `T`, `phi`, and geometry arrays while preserving body-relative draft
and freeboard. The test covers bottom erosion and a partial top layer. Saved
2020 annual snapshots contain solid material in layers 0–3 after compaction; the
pre-compaction output had nonzero layers 4–7. The operation is conservative for
remaining solid mass and does not change the physical freeboard definition.

**Limit:** this is an array-index correction, not a buoyant rigid-body solve.
A strongly eroded body is still not re-floated to hydrostatic equilibrium. The
model reports remaining-body draft/freeboard, not a validated post-roll or
post-capsize position.

## 4. Resolution convergence

All tests used the 100 m cube and the same 2020 start point (`76.5N, 20E`).
The 100^3 grid is `1 m`; 8/20/50/70^3 are convergence tests.

| N | dx (m) | 5-day mass loss | 30-day mass loss | 30-day time (s) | 30-day RSS (MB) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 12.5 | 0.0094744 | 0.0414555 | 8.8 | 651 |
| 20 | 5.0 | 0.0093201 | 0.0407721 | 11.3 | 655 |
| 50 | 2.0 | 0.0088450 | 0.0396212 | 68.6 | 639 |
| 70 | 1.43 | 0.0086489 | 0.0391333 | 153.1 | 639 |
| 100 | 1.0 | 0.0084789 | 0.0387289 | 495.3 | 782 |

30-day mass-loss differences vs 100^3: 8^3 `6.6%`, 20^3 `5.3%`,
50^3 `2.3%`, 70^3 `1.04%`. No tested lower resolution satisfies <1%. The
100^3 run is the reference because it is the scientific target, not because
spatial convergence has been demonstrated. Final 100^3 diagnostics: draft
`87.97 m`, freeboard `11.03 m`, mean phi `0.9817`, max PCG iterations `4`,
maximum residual `1.0e-10`; all fields are finite. Extrapolated annual cost is
about 1.6 h and 0.8 GB RSS per run.

Figures: `figures/stage12.13/resolution/resolution_convergence.png`,
`resolution_summary.csv`, and `resolution_100_30d/`.

## 5. Temperature/phi asymmetry

The final 100^3 T and phi fields are mirror-symmetric to machine precision:
T x-symmetry residual `3.02e-14`, y-symmetry `3.55e-14`; phi x/y residuals
`0.0`; S_boundary x/y residuals `0.0`. The earlier impression of a warm left
side and cold right side is not present in the current full-resolution field.
It was consistent with a display/downsampling transpose artifact, not a
physical left-right asymmetry. Face profiles show symmetric edge-to-center
structure: solid T ranges from about `-9.63 C` at the cold outer faces to
`-3.12 C` at the warmest melted face.

Figures: `figures/stage12.13/face_profiles/face_profiles.png` and
`face_slice_T_phi.png`.

## 6. Sensitivity

50^3/30-day sensitivity, relative to baseline mass loss `0.0396212`:

| Variant | Mass loss | Change |
| --- | ---: | ---: |
| cap 0.10 | 0.0395262 | -0.24% |
| cap 0.40 | 0.0396405 | +0.05% |
| phi_min 0.001 | 0.0394275 | -0.49% |
| phi_min 0.05 | 0.0399762 | +0.90% |
| c_ice 2009 J/(kg K) | 0.0396709 | +0.13% |

The response is small over these ranges. `VOXEL_C_ICE` is now an environment
override; the default remains `2100 J/(kg K)`. This does not calibrate the
coefficients and does not resolve the known low-flow/large-iceberg deficit.

## 7. 2020 fallback forcing and calendar

The existing 2020 annual point (`76.5N, 20E`) has 1,577 fallback events in
3,203 warning lines. The first event is at day 299.33 and the last at day 365.0;
median displacement is `0.0833 deg`, near `76.83–76.84N, 16.86–17.08E`.
The run writes 8,761 records, i.e. 365.0 days of the requested 366-day
leap-year experiment, then stops because no valid ocean cell remains.
`iceberg_run` now writes `run.nc_fallback.csv` for every substituted cell and
supports `--strict-ocean`. A fallback-free candidate was tested at `78N, 30E`:

| Year | 30-day strict run | Fallback/STOP | Final mass |
| --- | --- | ---: | ---: |
| 2020 | exit 0 | 0 | 8.8945e8 kg |
| 2024 | exit 0 | 0 | 9.0200e8 kg |

The candidate removes the land-fallback problem for these short tests, but no
annual run was performed. The leap-year calendar question is documented, not
resolved.

## 8. Energy budget

Mass closure remains the strong result. The full energy budget is not closed:
the model does not accumulate a complete time-integrated boundary heat flux,
the latent heat of removed ice, and the flush/removed-voxel enthalpy in one
auditable ledger. Initial cold content is about `6.3%` of latent heat for the
100 m cube at `-10 C`; this is a diagnostic scale, not a closure. The report
therefore separates **mass PASS** from **energy WARNING**. No energy closure
claim is made.

## 9. Annual runs

No 100^3 annual reference was run. Diagnostic 8^3 bookkeeping reruns were made:
2020 reaches 365.0 days with fallback forcing near the end; 2024 melts out at
268.8 days. They are not promoted. A 100^3 annual run costs about 1.6 h
extrapolated and was not launched because spatial convergence is not <1% and
2020 fallback provenance is unresolved. The 100^3 reference remains
intentionally **NOT RUN**.

## 10. Verification and artifacts

- strict `fpm build` with `-Wall -Wextra -fcheck=all -ffpe-trap=...`: exit 0.
- full `fpm test`: 81 programs, STOP 0 after the final code changes.
- `test_voxel_iceberg`: geometry, partial-phi/freeboard, compaction, mass/energy
  checks pass.
- `python/tests/test_plot_voxel_results.py`: synthetic slice/transposition
  checks pass.
- `scripts/check_docs_links.py --all` and `--anchors`: pass.
- `git diff --check`: pass.
- No commit or push was made.

Figures and summaries are in `figures/stage12.13/`; working diagnostics are in
`data/validation/stage12.13/`.

## 11. Open limitations and decision

Open limitations: full energy closure is absent; no lower resolution meets
<1%; vertical repositioning is index compaction, not buoyant re-floating;
prism consistency is synchronized bookkeeping, not independent validation;
2020 366-day forcing/calendar remains unresolved at the original point; no
annual 1 m run and no observational validation; annual 100^3 cost is acceptable
only for a deliberate final run.

Promote the voxel state as the authoritative mass/geometry representation and
retain 100^3 as the reference grid. Do not publish annual 2020/2024 results from
this stage. The next annual attempt must use 100^3, a fallback-free start point
or an explicitly documented fallback ledger, and a complete energy-budget
diagnostic.
