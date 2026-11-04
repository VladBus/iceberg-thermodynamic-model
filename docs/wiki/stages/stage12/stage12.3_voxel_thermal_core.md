# Stage 12.3 — Voxel Thermal Core

**Status:** COMPLETE (implementation + self-consistency/integration tests; default **OFF**).
**Date:** 2026-10-30
**Base:** `253ca59` (Stage 12.2). Authority: D-51 (reanalysis) + D-53 (this).
**Scope:** voxel data structure + thermal solver + `VOXEL_ENABLED` integration.
**No** Stage 11 ocean code, **no** reanalysis reader/ocean-provider (12.2) change,
**no** `fpm.toml`/CI change (tests auto-discovered).

## Objective

Replace the rectangular-prism bulk thermodynamics with a thermally resolved
**voxel** iceberg forced by the GLORYS12 reanalysis + ERA5 (one-way). This
stage is the model **implementation** from the voxel specification; it is **not**
an observational validation (that is Stage 12.7).

Reference: `docs/references/Iceberg/Iceberg_Voxel_Thermal_Model_8.pdf`
(**model specification**, not calibration). Its open items are carried into the
code as documented simplifications (see §6).

## Architecture

```
iceberg_thermodynamics_step
    ├─ (existing bulk path — UNCHANGED when VOXEL_ENABLED off)
    └─ voxel_model_step (new, gated)
          │  ocean T/S/u/v = interp_at_draft(ocean_prof, draft)
          │  atmos  T, Qnet, wind from atmos_forcing / diag%q_net_surface
          ▼
    voxel_iceberg (src/voxel_iceberg.f90)
          │  T(:,:,:)  φ(:,:,:)  + derived mass/draft/areas
          │  step = conduction → boundary fluxes → erosion → waterline
          ▼
    voxel_thermal_solver (src/voxel_thermal_solver.f90)
          │  solve_heat_conduction  (finite-volume explicit + enthalpy phase change)
          │  apply_boundary_fluxes  (Stefan ocean melt + air-surface balance)
          ▼
    ocean_provider (12.2) + ERA5  — offline/prescribed (one-way, D-51)
```

## Voxel data structure

- `voxel_iceberg_type`: `nx,ny,nz`, uniform `dx,dy,dz` (m), per-voxel `T` [°C]
  and `phi` [0..1] (ice fraction), logical `submerged_mask`/`exposed_mask`.
- Derived: `total_mass`, `draft`, `freeboard`, `waterline_area`,
  `submerged_area`, `exposed_area`, and `basal/lateral/surface_melt_rate` [kg/s].
- `voxel_iceberg_init` fills a uniform grid and calls `compute_state`.
- `compute_state`:
  - `mass = Σ φ·ρ_ice·dx·dy·dz`;
  - **waterline via Archimedes** — `ρ_w·V_sub = mass` → `V_sub`, then the
    horizontal plane `z_w` whose solid-ice volume below it equals `V_sub`
    (voxel straddling resolved by the partial level) → `draft = z_w`;
  - `submerged/exposed_mask` by voxel centre vs `z_w`;
  - areas by counting **external** faces (a face whose neighbour is empty /
    outside the domain), split by submerged/exposed.

## Thermal solver

- **Conduction** `solve_heat_conduction`: explicit finite-volume
  `T += dt·α·∇²T`, `α=k_ice/(ρ_ice·c_ice)≈1.15e-6 m²/s`; face conduction weighted
  by `min(φ_self, φ_neighbour)` (ice conducts only through ice); zero flux at
  empty cells and the domain border (adiabatic). Stability is **enforced** via
  substeps `nsub=⌈dt/dt_max⌉`, `dt_max=1/(2α·Σ1/dx²)`; for dx=10 m, dt=3600 s
  the explicit criterion is met (no substeps needed) but the guard generalises.
- **Enthalpy phase change** (in conduction): `T>0` melts `dφ=c_ice·T/L` and
  clamps `T→0`; `φ∈[0,1]`. (Freezing of ambient water is **not** modelled —
  open item.)
- **Boundary fluxes** `apply_boundary_fluxes` (deltas computed from the input
  state → order-independent, applied once):
  - submerged faces: `γ_T` from `ocean_heat_transfer_coeff(u_rel,l_char)`
    (forced convection, Eckert&Drake), `Tf=ocean_freezing_point(S,0)`;
    Stefan melt velocity `m=γ_T·(T_ocean−Tf)/(ρ_ice·L)` [m/s]; `m>0` melts,
    `m<0` freezes; face orientation → **basal** (z-normal) vs **lateral**
    (side); voxel `φ -= m·dt/dz`.
  - exposed faces: air balance `Q=Qnet + h_s·(T_air−T_surface)`,
    `h_s=C_D·ρ_air·c_p·wind`; sensible warms the voxel, `T>0` melts → **surface**.
  - returns `basal/lateral/surface_melt` [kg/s] (signed, +=melt).
- **Erosion / removal**: after fluxes, voxels with `φ<φ_min` (default 0.01) are
  removed (`φ=0`); `compute_state` recomputes mass/draft/areas (dynamic waterline).

## Integration (`iceberg_thermodynamics.f90`)

- Env `VOXEL_ENABLED` (**default off** → `voxel_model_step` returns immediately;
  the existing basal/lateral/surface + internal-temperature path is byte-for-byte
  untouched). `VOXEL_NX/NY/NZ`, `VOXEL_DX/DY/DZ`, `VOXEL_T_INIT`,
  `VOXEL_PHI_INIT`, `VOXEL_PHI_MIN` configurable.
- When on, a parallel voxel is advanced each step from the **same**
  `ocean_profile`/`atmos_forcing` the bulk path uses; its melt kg/s is written to
  `diag%m_basal/m_lateral/m_surface` (m/s). The prism `state` geometry is **not**
  overwritten by the voxel (kept separate) — full geometry feedback is a
  Stage 12.4 concern. **One-way**: no feedback to ocean/atmosphere (D-51).

## Unit + integration tests (CI-safe, synthetic forcing, no `.nc` I/O)

| Test | Checks | Key results |
|---|---|---|
| `test_voxel_thermal_solver` | 7 | adiabatic ΣT·φ conserved (rel 0); hotspot diffuses; phase clamp `T:+5→0, φ:1→0.9686`; isolated submerged voxel → basal & lateral melt >0 and `melt_v>0` reduces φ; sub-Tf ocean + current → freeze (basal<0, φ up); air flux → surface melt |
| `test_voxel_iceberg` | 8 | mass = analytic `ρ_ice·V` (9.10e8 kg, tol 1e-3); **draft = 88.521 m = Archimedes `ρ_i/ρ_w·H`** (exact); external-face area ≈ 60000 m², waterline cross-section ≈ 10000 m²; **mass conserved under zero forcing (drift 0.0e0 over 100 steps)**; warm melt → mass & draft down; `φ<φ_min` voxel removed; draft recomputed after mass change |
| `test_voxel_integration` | 6 | 24 daily steps of GLORYS-like forcing (T=2 °C, S=0.035, u=0.1): **no NaN**, φ∈[0,1], mass & draft decrease; bulk three-equation melt velocity ~1.4e-6 m/s cross-check (order-of-magnitude agreement); voxel-vs-bulk difference documented (per-voxel geometry) |

Full `fpm test` battery green; new tests **always run** (no data-file dependency,
no SKIP). Default `VOXEL_ENABLED=off` keeps the model-path bit-identical.

## Known limitations / open items (from the spec, visible in code)

1. **`γ_S`/salt boundary layer** not solved (thermal-only Stefan); a real
   three-equation (heat+salt) interface belongs to Stage 12.4.
2. **`Tf` uses surface value** (`ocean_freezing_point(S,0)`); pressure/depth
   correction at draft deferred to 12.4.
3. **`u_rel = |ocean current|`** (iceberg velocity not in the point API) —
   relative-flow refinement in 12.4+.
4. **Cavity / channel exchange, spray/waterline band, turbulent-coefficient
   calibration** — not modelled (spec open items).
5. **Freezing of ambient water** into voxels not modelled (melt-only phase change).
6. **Voxel↔prism geometry feedback** and **melt-water/ buoyancy feedback** to the
   ocean are out of scope (one-way, D-51); prism `state` still drives drift.
7. **dx used for both horizontal/vertical** faces assumed uniform; non-cubic
   voxels supported by `dx,dy,dz` but `dz` melt-depth conversion is 1-D.
8. No observational calibration/validation yet (Stage 12.7).

## GO / NO-GO for Stage 12.4 (ice–water / ice–air boundary coupling)

| Gate | Result |
|---|---|
| Voxel grid + per-voxel `T,φ` + derived mass/draft/areas | **YES** |
| Finite-volume conduction + enthalpy phase change (stable, energy-conserving) | **YES** |
| Stefan ocean melt (basal/lateral) + air-surface melt, budget kg/s | **YES** |
| Geometric erosion (`φ_min`) + dynamic Archimedes waterline | **YES** |
| `VOXEL_ENABLED` integration, default OFF, no Stage 11 ocean change | **YES** |
| Tests green (7+8+6); full battery green | **YES** |

**GO for Stage 12.4** (a proper three-equation ice–water interface at draft
depth with `γ_T`/`γ_S`, salt boundary layer, and `Tf(S,p)`; plus relative-flow
`u_rel`). **Stage 12.4 not started** in this stage.

## Files

- New: `src/voxel_thermal_solver.f90`, `src/voxel_iceberg.f90`,
  `test/test_voxel_thermal_solver.f90`, `test/test_voxel_iceberg.f90`,
  `test/test_voxel_integration.f90`.
- Modified: `src/iceberg_thermodynamics.f90` (gated `VOXEL_ENABLED` hook;
  default-off bulk path unchanged).
- Doc: this report, D-53, `STAGE12_PREPARATION.md`, `REANALYSIS_DATA_PLAN.md`,
  `model_physics_status.md`, `AGENTS.md`, `CHANGELOG.md`, `README.md`.
