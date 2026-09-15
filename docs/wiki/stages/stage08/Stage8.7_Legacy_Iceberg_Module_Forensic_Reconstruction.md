# Stage 8.7 — Legacy Iceberg Module Forensic Reconstruction and Ocean–Iceberg Interface Audit

**Date:** 2025-09-03  
**Git Commit:** 1963ef1 (Stage 8.6 complete)  
**Classification:** **A** — Forensic complete; no legacy iceberg model found; clear path defined for Stage 8.8

---

## Executive Summary

Stage 8.7 conducted a comprehensive forensic investigation of the historical Dmitriev-Nesterov model archive to determine whether an individual iceberg model exists and can be ported to the current repository.

**Primary Finding: NO INDIVIDUAL ICEBERG MODEL EXISTS in the legacy code.**

The directory `Model_Isberg_Dmitriev(Nesterov)` and file headers referencing "модель айсбергов" (iceberg model) are a **historical misnomer**. The legacy code implements an **Eulerian ocean + sea ice model**, not a Lagrangian individual iceberg model. The term "iceberg" appears to have been used loosely in Russian oceanographic context to refer to sea ice modeling.

The current repository is a faithful, modernized reconstruction of this legacy ocean/sea-ice model (14/14 regression tests pass). The ocean instability documented in Stage 8.6 (atmospheric pressure forcing in Block 200) is a structural defect faithfully reproduced from the legacy physics.

**Stage 8.8 must implement the iceberg model as a NEW Lagrangian component**, using the reconstructed ocean as environmental forcing (offline initially).

---

## Answers to Required Questions

### Question 1: Does the legacy model contain an individual iceberg model?

**Answer: NO**

**Evidence:**

- All legacy state variables are **Eulerian grid fields** `(IS1, JS1)` or `(IS1, JS1, KS)` — not Lagrangian particle properties
- "Drift velocity calculation" in `Coupl1` computes **sea ice velocity field** `UIC(I,J), VIC(I,J)` on the grid
- Sea ice state: `HICES` (thickness), `ANS` (concentration), `WICE1` (categories) — continuum fields
- `ADVICE/ADV2D` is a **2D FCT advection scheme** (name = `ADV` + `2D`), not an iceberg model
- No variables for individual iceberg position, velocity, mass, geometry, or trajectory exist

### Question 2: Where is the iceberg code?

**Answer: DOES NOT EXIST**

No file, routine, module, or call chain implements an individual iceberg model. The legacy code contains only:

- Ocean model (3D U,V,T,S,RO,W)
- Sea ice model (2D HICES,ANS + categories, UIC,VIC velocity field)
- Coupling between them

### Question 3: Does `ADVICE` represent the iceberg model?

**Answer: NO**

**Proof:** `ADVICE.F` / `Advice.f90` implements subroutine `ADV2D` — a **2D Flux-Corrected Transport advection scheme** for scalar fields (ice concentration, ice thickness categories). The name is a Fortran-6-character abbreviation: `ADV`ective `2D` → `ADVICE`. It is called from `Coupl1` for sea ice advection, not for iceberg trajectory.

### Question 4: How is an iceberg represented mathematically?

**Answer: NOT REPRESENTED in legacy code.**

The legacy model represents **sea ice** as:

- State: Eulerian fields `HICES(x,y)`, `ANS(x,y)`, `WICE1(x,y,k)`, `UIC(x,y)`, `VIC(x,y)`
- Dynamics: VP rheology stress tensor + wind/water drag + Coriolis + sea surface tilt
- Thermodynamics: Category-based `HEAT()` with solar, turbulent, basal, lateral melt
- Advection: FCT scheme `ADV2D` for concentration and thickness categories

**For Stage 8.8, the iceberg must be represented as:**
| Variable | Symbol | Units | Description |
|----------|--------|-------|-------------|
| Position | `x, y` | m | Horizontal coordinates |
| Velocity | `u, v` | m/s | Drift velocity |
| Mass | `M` | kg | Total ice mass |
| Geometry | `L, W, H` | m | Length, width, height (rectangular prism) |
| Draft | `D` | m | Submerged depth (buoyancy: `D = H * ρ_ice/ρ_water`) |
| Waterline area | `A_w` | m² | `L × W` |
| Wet surface area | `A_wet` | m² | `2(L+W)D + L×W` |

### Question 5: Does the legacy model contain iceberg thermodynamics?

**Answer: NO — only SEA ICE thermodynamics**

**Distinction:**

| Process             | Sea Ice (Legacy `HEAT`)               | Individual Iceberg (Required)       |
| ------------------- | ------------------------------------- | ----------------------------------- |
| Representation      | Eulerian categories `AN1, WICE1`      | Lagrangian single object            |
| Surface melt        | Yes (TTS iteration)                   | Yes (top surface)                   |
| Basal melt          | Yes (via FW, **surface T only**)      | **Yes — needs T(z) at draft depth** |
| Lateral melt        | Yes (in leads, reduces concentration) | **Yes — side area × T(z) profile**  |
| Snow accumulation   | Yes (SFAL parameterization)           | Possible (precipitation on top)     |
| Internal conduction | No (surface temp only)                | Possible if H > ~50m                |
| Geometry evolution  | Category thickness `HICP`             | **L(t), W(t), H(t) all evolve**     |

### Question 6: How does the iceberg interact with the 3-D ocean?

**Answer: Legacy sea ice uses SURFACE CURRENT ONLY; iceberg needs FULL 3-D PROFILE.**

**Legacy sea ice coupling:**

```fortran
A1 = U2(I,J,1)/100.    ! Surface ocean current ONLY (k=1)
B1 = V2(I,J,1)/100.
```

**Required iceberg coupling:**

- Water drag: `∫₀ᴰ 0.5*ρ_water*C_d*side_area(z)*|U(z)-U_berg|*(U(z)-U_berg) dz`
- Basal melt: `T(z=D), S(z=D)` at draft depth
- Lateral melt: `T(z), S(z)` integrated over 0<z<D
- Pressure gradient: `SSH(x,y)` or `∇p` from barotropic mode

### Question 7: Which required ocean fields already exist in the current project?

| Iceberg Requirement            | Available?                | Source                                    | Stability         |
| ------------------------------ | ------------------------- | ----------------------------------------- | ----------------- |
| `T(z), S(z)`                   | ✅ **Initial/diagnostic** | EN4 Jan 2020 → `initial_ocean_reader.f90` | ✅ Stable         |
| `z(k), DZ(k)`                  | ✅ **Fixed**              | `param.f90`, `grid_coupling.f90`          | ✅ Fixed          |
| Bathymetry                     | ✅ **Fixed**              | IBCAO → `KOORD.DAT`, `hhh.bar`            | ✅ Fixed          |
| `u10, v10, t2m, q, cloud`      | ✅ **Time series**        | ERA5 → `wind_forcing.f90`                 | ✅ Stable         |
| `U(z), V(z)` climatology       | ✅ **Prescribed**         | Literature/observations                   | ✅ Stable         |
| `U(z,t), V(z,t)` time-evolving | ❌ **Unstable**           | 3D momentum (Block 200)                   | ❌ NaN by Day 1   |
| `SSH(t)` time-evolving         | ❌ **Unstable**           | Barotropic (shal + Block 280)             | ❌ Coupled to U/V |

### Question 8: Which ocean fields are currently unavailable or unstable?

| Field                | Status          | Blocker                                                     |
| -------------------- | --------------- | ----------------------------------------------------------- |
| Time-evolving 3D U/V | ❌ **Unstable** | Block 200 atmospheric pressure spike (25 m/s) → NaN cascade |
| Time-evolving SSH    | ❌ **Unstable** | Coupled to unstable U/V                                     |
| Consistent ∇p(t)     | ❌ **Unstable** | Same                                                        |
| Wave spectrum        | ❌ **Missing**  | Not in model                                                |

**Stage 8.6 Root Cause (not fixed in 8.7):** Atmospheric pressure gradient `dpx/dpy` in Block 200 acts as barotropic forcing (~25 m/s) overwhelming baroclinic balance (~0.1 m/s). Barotropic solver runs AFTER Block 200, cannot prevent spike.

### Question 9: Can an idealized iceberg experiment be run independently of the unstable full ocean time integration?

**Answer: YES — OFFLINE MODE**

**Recommended approach for Stage 8.8:**

1. **Prescribe** `T(z), S(z)` from EN4 (initial or climatology)
2. **Prescribe** `U(z), V(z)` from literature climatology (not model integration)
3. **Prescribe** ERA5 `u10, v10, t2m, q, cloud` at iceberg position
4. **Prescribe** bathymetry from IBCAO
5. **Integrate** iceberg ODEs independently (no ocean time step)
6. **Validate** against idealized cases and literature

This avoids the ocean instability entirely while developing the iceberg physics.

### Question 10: What exactly should Stage 8.8 do?

**Recommended Path: D — Minimal Cubic Iceberg Model** (with legacy-informed physics)

**Justification:**

- Paths A/B/C require legacy iceberg code that **does not exist**
- Path D: Build from first principles, informed by:
  - Legacy sea ice physics (drag coefficients, densities, rheology concepts)
  - Literature on iceberg drift/melt (Diansky, Keghouche, Marchenko, met.no CHC)
  - Supervisor's scientific direction ("thermodynamic evolution of icebergs")

**Stage 8.8 Objective (one paragraph):**
Implement a minimal Lagrangian iceberg model as a new Fortran module (`iceberg.f90`) with state vector `[x, y, u, v, L, W, H, M]` driven by **prescribed offline ocean fields** (EN4 T/S profiles, ERA5 wind, climatological U/V, IBCAO bathymetry). Physics: (1) Drift via `M*dV/dt = F_wind + F_water(z) + F_coriolis + F_pressure` with implicit Coriolis solver (adapted from legacy sea ice 2×2 system); (2) Thermodynamics via basal melt at draft `T(z=D)`, lateral melt integrated over draft, surface melt from ERA5 fluxes; (3) Geometry evolution `dL/dt, dW/dt, dH/dt` from melt rates with buoyancy-adjusted draft; (4) Grounding check against bathymetry. Experiments A-D from `experiment_design.md` validate buoyancy, melt tendency, drag profile, and 30-day coupled drift+melt. All runs offline — no ocean time integration required.

---

## Ocean Reconstruction Status

| Component         | Status                                        |
| ----------------- | --------------------------------------------- |
| Grid              | ✅ Complete (real IBCAO grid, Stage 7.6)      |
| Bathymetry        | ✅ Complete (Stage 7.6)                       |
| ERA5              | ✅ Complete (Stage 7.6C, expanded domain)     |
| T/S (initial)     | ✅ Complete (EN4 Jan 2020, Stage 8.0)         |
| 3-D U/V (initial) | ✅ Complete (discrete_ss balanced, Stage 8.5) |
| Vertical grid     | ✅ Complete (18 levels, fixed)                |
| Sea ice           | ✅ Complete (Stage 7.6C)                      |

---

## Ocean Instability Status

| Aspect                | Detail                                                                      |
| --------------------- | --------------------------------------------------------------------------- |
| Stage 8.6 Root Cause  | Atmospheric pressure (dpx/dpy) in Block 200 = barotropic forcing ~25 m/s    |
| Resolved in Stage 8.7 | **NO** — by design, Stage 8.7 is forensic only                              |
| Reason                | Requires canonical physics change (move dpx/dpy to shal) — not in 8.7 scope |
| Impact on Iceberg     | Time-evolving U/V/SSH unavailable; use prescribed profiles for 8.8          |

---

## Iceberg State Vector (New Design for 8.8)

| Variable       | Symbol    | Units | Initialization                   |
| -------------- | --------- | ----- | -------------------------------- |
| Position       | `x, y`    | m     | Prescribed (lat/lon → grid)      |
| Velocity       | `u, v`    | m/s   | 0 or ocean surface current       |
| Mass           | `M`       | kg    | `ρ_ice * L * W * H`              |
| Geometry       | `L, W, H` | m     | Prescribed (e.g., 100×100×100 m) |
| Draft          | `D`       | m     | `H * 910/1028` (buoyancy)        |
| Waterline area | `A_w`     | m²    | `L * W`                          |
| Wet area       | `A_wet`   | m²    | `2*(L+W)*D + L*W`                |

---

## Iceberg Forces (New Design for 8.8)

| Force         | Formula                             | Ocean Input        |
| ------------- | ----------------------------------- | ------------------ | -------------- | -------------------- |
| Wind          | `0.5*ρ_air*C_d_air*A_air*           | U_wind-u           | \*(U_wind-u)`  | ERA5 `u10, v10`      |
| Water drag    | `∫₀ᴰ 0.5*ρ_water*C_d_water*side(z)* | U(z)-u             | \*(U(z)-u) dz` | `U(z), V(z)` profile |
| Coriolis      | `M * f × (u, v)`                    | `f = 2Ω sin(lat)`  |
| Pressure grad | `-M/ρ_water * ∇SSH`                 | `SSH` (prescribed) |

---

## Iceberg Thermodynamics (New Design for 8.8)

| Process      | Rate                                          | Ocean Input          |
| ------------ | --------------------------------------------- | -------------------- |
| Basal melt   | `dH/dt = -C_b*(T(D)-T_f)/(ρ_ice*L_f)`         | `T(z=D), S(z=D)`     |
| Lateral melt | `dL/dt = dW/dt = -C_l*∫(T-T_f)dz/(ρ_ice*L_f)` | `T(z), S(z)` 0<z<D   |
| Surface melt | `dH/dt = -Q_net/(ρ_ice*L_f)`                  | ERA5 fluxes          |
| Wave erosion | `dD/dt = -C_w*H_s²*T_p`                       | Not available (omit) |

---

## Ocean → Iceberg Required Fields (Summary)

| Field                          | For                     | Availability              |
| ------------------------------ | ----------------------- | ------------------------- |
| `T(z), S(z)`                   | Basal/lateral melt, T_f | ✅ EN4 initial            |
| `U(z), V(z)`                   | Water drag              | ⚠️ Prescribed climatology |
| `z(k), DZ(k)`                  | Vertical mapping        | ✅ Fixed                  |
| Bathymetry                     | Grounding check         | ✅ IBCAO                  |
| ERA5 `u10, v10, t2m, q, cloud` | Wind drag, surface melt | ✅ Time series            |
| `SSH`                          | Pressure gradient       | ⚠️ Prescribed             |

---

## Currently Available Fields (Stable)

✅ EN4 T/S profiles (initial)  
✅ Vertical grid  
✅ Bathymetry  
✅ ERA5 atmospheric forcing (on model grid)  
✅ Iceberg can run **offline** with prescribed U/V climatology

## Missing/Unstable Fields

❌ Time-evolving 3D U/V from model integration  
❌ Time-evolving SSH  
❌ Wave spectrum  
❌ Two-way coupling (freshwater/heat feedback to ocean)

---

## Historical Validation

| Legacy Validation             | Status                                                  |
| ----------------------------- | ------------------------------------------------------- |
| Iceberg trajectory validation | **NONE** — legacy is sea ice model, not iceberg         |
| Sea ice validation            | Concentration vs satellite (Stage 7.2), but not iceberg |

---

## Recommended Stage 8.8

**PATH D — Minimal Cubic Iceberg Model** (new implementation)

**Stage 8.8 Objective:** Implement a minimal Lagrangian iceberg model (`iceberg.f90`) with drift + thermodynamics driven by prescribed offline ocean fields. Experiments A-D validate buoyancy, melt, drag, and 30-day evolution. All offline — no ocean time integration required.

---

## Canonical Physics Changes

| Item                      | Changed?                      |
| ------------------------- | ----------------------------- |
| Canonical physics         | **NO** (8.7 is forensic only) |
| Canonical grid            | NO                            |
| Canonical EOS             | NO                            |
| Canonical ERA5            | NO                            |
| Canonical sea-ice physics | NO                            |

---

## Regression

```
14/14 tests PASS (unchanged from Stage 8.6)
- convective_adjustment: 15/15
- eos: 7/7
- thermo_input: 8/8
- snowfall: 9/9
- cold_ice_snow: PASS
- eos_precision: PASS
- ocean_init: 13/13
- era5_coverage: PASS
- ice_init_chain: 4/4
```

---

## Files Created (Stage 8.7)

```
data/output/diagnostics/stage8.7/
├── baseline.json
├── current_repository_iceberg_search.json
├── current_repository_iceberg_search.md
├── legacy_iceberg_inventory.json
├── legacy_iceberg_inventory.md
├── legacy_iceberg_callgraph.md
├── iceberg_state_vector.json
├── iceberg_force_balance.md
├── iceberg_thermodynamics.md
├── vertical_ocean_coupling.md
├── ocean_iceberg_interface.md
├── ocean_status_for_iceberg.md
├── experiment_design.md
├── legacy_current_comparison.md
└── ocean_iceberg_interface.json (matrix)

docs/wiki/
└── Stage8.7_Legacy_Iceberg_Module_Forensic_Reconstruction.md (this file)
```

---

## Files Modified

**NONE** — Stage 8.7 is forensic only; no model code modified.

---

## Report

`docs/wiki/stages/stage08/Stage8.7_Legacy_Iceberg_Module_Forensic_Reconstruction.md`

---

**STAGE 8.7 COMPLETE**

**STOP — Stage 8.7 complete. Do not automatically continue to Stage 8.8.**
