# Stage 12 Preparation — Voxel Iceberg on Reanalysis Forcing

**Status:** **Stage 12.8 COMPLETE (24/24 exploratory runs)** with documented
monthly-GLORYS/constant-atmosphere fallbacks. Stage 12.9 thesis writing may
proceed with explicit fallback labeling; quantitative daily-forcing claims
remain NO-GO. Workstreams: **12.9a daily-forcing acquisition** is in progress
(resumed 2026-11-04; do not start additional downloads unless explicitly
requested); **12.9b thesis writing** is GO with fallback labeling.
**Updated:** 2026-11-04
**Base:** Stage 11 freeze tag `stage11-final-frozen`.
**Implementation:** Stage 12.2–12.8 are complete as listed in
`docs/validation/INDEX.md`. The voxel path remains offline/prescribed and gated;
see `docs/model/model_physics_status.md` and `docs/DECISIONS.md` for current
switches and formulation status.

## 1. Objective

Replace the rectangular-prism iceberg thermodynamics with a thermally
resolved voxel iceberg forced by an **offline/prescribed reanalysis ocean** and
ERA5 atmosphere. The first implementation is deliberately one-way: the ocean
does not feel the iceberg.

The target is not a calibrated operational model. It is a controlled
thermodynamic model with explicit conservation budgets, voxel-level
diagnostics, and a documented observational comparison.

## 2. Fixed data architecture (D-51)

| Component | Source | Status |
|---|---|---|
| Ocean T/S/currents | GLORYS12 `GLOBAL_MULTIYEAR_PHY_001_030`, daily 1/12° (`thetao`, `so`, `uo`, `vo`, `zos`) | selected; not downloaded |
| Sea ice / SSH | same product (`siconc`, `sithick`, `zos`) | selected |
| Bathymetry / mask | `cmems_mod_glo_phy_my_0.083deg_static` (`deptho`, `mask`) | selected |
| Atmosphere | ERA5 (existing validated path) | existing |
| Iceberg geometry/bathymetry | IBCAO model grid (existing) | existing |
| Coupling | offline/prescribed, one-way | fixed for Stage 12 |

The Stage 11 N=24 ocean is **not** the Stage 12 ocean of record. It remains a
frozen numerical cross-check (`docs/wiki/stages/stage11/STAGE11_FREEZE.md`).

Fallback/cross-check only: `ARCTIC_MULTIYEAR_PHY_002_003` (TOPAZ4, daily).
Do not mix products inside one run.

## 3. Voxel model contract

The reference specification is
`docs/references/Iceberg/Iceberg_Voxel_Thermal_Model_8.pdf` (32 pages).
Freeze the following before coding:

- regular cubic voxel grid with per-voxel temperature `T` and ice fraction `φ`;
- finite-volume conduction through shared ice faces;
- Stefan / three-equation ice-water boundary flux on submerged faces;
- air-surface heat balance on exposed faces;
- geometric erosion and removal at `φ < φ_min`;
- hydrostatic waterline and drift coupling through voxel-derived mass, draft,
  and areas;
- explicit energy and meltwater budgets.

The PDF is a **model specification**, not an observational calibration. Its
own open items (turbulent coefficients, cavity exchange, spray/waterline zone,
no coupled feedback) must remain visible in the implementation.

## 4. Staged work packages

| Stage | Deliverable | Gate |
|---|---|---|
| 12.1 | Reanalysis acquisition/validation (GLORYS12 + ERA5 subset) | **COMPLETE** (Jan-2020 recon; regular grid/units/mask verified; report) |
| 12.2 | Reanalysis reader and offline forcing contract | **COMPLETE** (`reanalysis_reader`+`ocean_provider`+`iceberg_forcing`; D-52; tests green; default OFF) |
| 12.3 | Voxel thermal core | **COMPLETE** (`voxel_iceberg`+`voxel_thermal_solver`, D-53; FV conduction+phase change, Stefan/air melt, erosion, waterline; tests green; default OFF) |
| 12.4 | Ice-water/ice-air boundary coupling | **COMPLETE**: Crank–Nicolson (θ-scheme, PCG, Rannacher), geometry fix, three-equation Stefan (γ_T/γ_S, Tf(S,P), profile, u_rel), melt cap/flush; D-54/D-55; tests green; default OFF |
| 12.5 | Geometry/erosion/hydrostatic coupling | **COMPLETE**: voxel mass/draft/frontal A_sub_proj/A_sail drive drift (gated), GM estimate; D-56; tests green; default OFF |
| 12.6a | Drift in lat/lon + `iceberg_run` + real(8) | **COMPLETE** (D-57; IBCAO grounding; NetCDF; tests green) |
| 12.6b | Wave erosion (Bigg 1997), sea-ice drag, tides, lat/lon forcing refinements | **PARTIAL: wave erosion + optional Stokes COMPLETE** (D-58; gates default OFF); sea-ice drag/tides remain |
| 12.6 | Drift coupling with voxel-derived geometry | existing drift tests remain green; no two-way feedback |
| 12.7 | Validation and diagnostics | **12.7a COMPLETE**; **12.7.audit**; **12.7b**; **12.7c** free convection |
| 12.8 | Barents 2020 matrix | **COMPLETE 24/24** with monthly-GLORYS/constant-atmosphere fallbacks (D-63); 12.9 thesis writing GO with caveats |

Stages may be reordered only with an explicit decision. Stage 12.1 must not
start before its data plan is reviewed.

## 5. Data gates for Stage 12.1

- Barents subset: approximately **63–86°N, 5–80°E** (model domain
  `64.21–85.04°N, 8.33–76.32°E` plus a guard margin).
- Time: **2020-01-01 through 2020-12-31**, daily means; verify the exact
  availability end before the first run.
- Depth: surface through at least **600 m**; preserve the native GLORYS
  levels rather than pre-interpolating to the Stage 11 grid.
- Units: `thetao` °C, `so` 1e−3 (verify against model salinity mass fraction),
  `uo/vo` m s⁻¹, `zos` m, `siconc` fraction, `sithick` m.
- Mask: use the product `mask`/`deptho`; never fill land with zeros.
- Storage: monthly float32 chunks with compression; the uncompressed
  4-field 3-D subset is tens of GB, so the exact size must be measured before
  a full-year download.

## 6. Guardrails

- No two-way ocean coupling in Stage 12; that requires a separate approved
  stage.
- No change to Stage 11 EOS, scheduler, or frozen evidence.
- No production default change; new physics stays behind a dedicated switch.
- No claim of calibration or operational skill from a specification-only
  model.
- No reanalysis download in Stage 12.0; this stage is documentation only.
- Stage 11 limitations (N², tides, 90-day, T-39) remain limitations; they are
  not waived by changing the forcing source.

## 7. Entry/exit criteria

**Stage 12.0 exit:** frozen Stage 11 tag; D-51 recorded; plan + reanalysis data
plan reviewed; catalogue probe reproducible; Enderlin23 dataset staged. **DONE.**

**Stage 12.1 exit:** Jan-2020 subset downloaded + inspected; grid/units/mask/
depth/time verified against Python. **DONE** (`stage12.1_glorys12_validation.md`).

**Stage 12.2 exit:** reader + provider + iceberg-forcing integration; unit +
integration tests green; default `OCEAN_SOURCE=model` → Stage 11 bit-identical;
no ocean-code change. **DONE** (`stage12.2_reanalysis_reader.md`, D-52).

**Stage 12.3 exit:** voxel core (`voxel_iceberg` + `voxel_thermal_solver`) +
gated `VOXEL_ENABLED` integration (default OFF → bulk bit-identical); conduction
energy-conserving, Archimedes draft exact, erosion + dynamic waterline, melt
budgets; unit + integration tests green; no Stage 11/12.2 code change. **DONE**
(`stage12.3_voxel_thermal_core.md`, D-53).

**Stage 12.4 exit:** Crank–Nicolson θ-scheme (PCG 1e−10, Rannacher) with
boundary conditions in the matrix, single enthalpy clamp, energy‑consistent
flush transfer, 3D `h_norm` fix, melt cap; three‑equation Stefan per submerged
face with per‑depth profile, `Tf(S,P)`, `u_rel` with iceberg velocity,
`m≥0` (no accretion); D‑54/D‑55; tests green; default OFF. **DONE**
(`stage12.4_crank_nicolson_stefan.md`).

**Stage 12.5 exit:** voxel frontal/wetted areas + mass/draft drive drift
(gated), metacentric estimate, tests; D‑56; default OFF. **DONE**
(`stage12.5_voxel_geometry_drift.md`).

**Stage 12.6a exit:** real(8) state; lat/lon drift on reanalysis; standalone
`iceberg_run` (IBCAO grounding, NetCDF); tests green. **DONE**
(`stage12.6a_drift_latlon_iceberg_run.md`).

**Stage 12.6b exit (wave part):** Bigg (1997) erosion + optional Stokes,
NEMO-verified formula, gates default OFF, diagnostics/NetCDF, tests green.
**DONE** (`stage12.6b_wave_erosion.md`). Sea-ice drag and tides remain.

**Stage 12.7a exit:** 190 Enderlin23 icebergs, prescribed trajectories,
GLORYS12; bulk/voxel compared; no calibration. Bulk median ratio 1.39,
voxel 0.059; D-59. **DONE** (`stage12.7a_enderlin23_hindcast.md`). Voxel
column superseded by the audit.

**Stage 12.7.audit / 12.7b exit:** fixed-cube voxel geometry and kg/s mapping
fixed; residual medium/large under-melt is structural (weak currents, no
low-flow floor/waves). Autonomous voxel air balance tested (<1% closure).
**DONE** (`stage12.7.audit_voxel_melt.md`, `stage12.7b_autonomous_air.md`).

**Stage 12.7c exit:** mixed-convection floor `max(K_T u, 1e-5)` and
`max(K_S u, 1e-6)`; 3-case ratios 1.309/0.655/0.208; large low-dT remains
structural; no calibration. **DONE** (`stage12.7c_free_convection.md`).

**Stage 12.8 exit:** 24/24 voxel matrix runs (4 sizes x 2 seasons x 3 points)
completed with monthly-mean GLORYS (18 months) and constant atmosphere;
start points shifted to satisfy IBCAO depth + GLORYS mask; 7 figures; drift
1.2-6.3 km/year (lower bound), lateral melt 55-83%. **DONE with fallback
caveat** (`stage12.8_barents2020_matrix.md`).

## 8. References

- `docs/wiki/stages/stage11/STAGE11_FREEZE.md`
- `docs/references/reanalysis_data_plan.md`
- `docs/DECISIONS.md` D-51
- `docs/references/Iceberg/Iceberg_Voxel_Thermal_Model_8.pdf`
- `docs/references/data_sources.md`
