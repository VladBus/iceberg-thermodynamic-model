# Scientific Model Description

## 1. Scope and current composition

The repository contains a Lagrangian iceberg model coupled to an Eulerian
ocean/sea-ice framework. The iceberg is represented either as a rectangular
prism (legacy) or as a thermally resolved voxel body (Stage 12). The current
scientific model is the Stage 12 voxel iceberg driven by offline/prescribed
reanalysis; the Stage 11 prognostic ocean is frozen and is not a
production-validated ocean.

| Layer | Status | Role |
| --- | --- | --- |
| Legacy rectangular-prism iceberg thermodynamics | Historical, retained for regression and comparison | Original compact model; `VOXEL_ENABLED=false` |
| Stage 11 prognostic ocean/sea-ice | **FROZEN** research artifact (D-51) | Numerical cross-check only; not production-validated |
| Stage 12 voxel iceberg | **Active science path** | Per-voxel temperature/ice fraction, CN conduction, three-equation interface, geometry-driven drift |
| Stage 12 reanalysis forcing | **Active, offline/prescribed** | GLORYS12 ocean and ERA5 atmosphere; one-way coupling |
| Stage 11 + Stage 12 validation | Completed through Stage 12.8 | Exploratory/fallback results only where stated |

This document is the narrative model description. The authoritative
mathematical specification is [`model_equation_ledger.md`](model_equation_ledger.md);
block maturity and switches are in [`model_physics_status.md`](model_physics_status.md);
decisions are in [`../DECISIONS.md`](../DECISIONS.md). Stage 12 reports are in
[`../wiki/stages/stage12/`](../wiki/stages/stage12/).

**Current status.** Stage 12.8 is the latest completed published validation.
Its Barents matrix used monthly-mean GLORYS and a constant atmosphere; drift and
lifetime are lower bounds, not daily-forcing validation. Stage 12.9a
daily-forcing acquisition is complete; **12.9b thesis writing** is GO with
explicit fallback labeling. Stage 12 is not an operationally validated forecast
system.

## 2. Grid and coordinates

The reconstructed real grid has 133 × 105 nodes and 132 × 104 active cells on a
B-grid with DX = DY = 13.89 km. Production reads coordinates, bathymetry, and
land mask from the NetCDF file `data/input/processed/grid/grid.nc`; legacy
`KOORD.DAT`/`hhh.bar` files are offline regression fixtures only
(see [`../LEGACY_IO_POLICY.md`](../LEGACY_IO_POLICY.md)). The grid is derived
from IBCAO V5.2 (400 m, EPSG:3996).

Model axes are X ↔ `j` ↔ `u` and Y ↔ `i` ↔ `v`; the Y axis is inverted.
Hydrodynamics use CGS internally and thermodynamics use SI, with conversion
only at the NetCDF output boundary. Geographic latitude/longitude are
diagnostic in legacy model mode and authoritative when
`OCEAN_SOURCE=reanalysis` (Stage 12.6a).

## 3. Iceberg representation and geometry

### 3.1 Legacy prism

The legacy prognostic mechanical state is `[x, y, u, v, L, W, H]`; the surface
and interior extensions add `T_surface` and `T_ice`. For a rectangular prism:

- `V = L W H`;
- `M = rho_ice V`;
- `D = H rho_ice / rho_water`;
- `A_base = L W`;
- `A_lat = 2 H (L + W)`.

The prism has no orientation, tilt, calving, or fracture. Its thermodynamics is
the historical compact closure and is retained for regression; it is **not**
used for new science runs (D-61).

### 3.2 Stage 12 voxel body

The voxel model stores temperature `T` and ice fraction `φ` per cell on a
state-scaled grid. Finite-volume conduction, phase change, submerged-face melt,
exposed-face air exchange, geometric erosion, and removal at `φ < φ_min`
determine the body. Voxel mass, Archimedes draft, projected submerged area
`A_sub_proj`, and exposed sail area `A_sail` drive drift when
`VOXEL_ENABLED=ON` (Stage 12.5). The default is OFF for bit-identical legacy
regression; science runs enable the voxel path explicitly. The CN boundary
assembly uses one local interface temperature per exposed face; it does not
average different face temperatures. A six-neighbour flood fill distinguishes
exterior-connected empty cells from isolated cavities, so closed voids do not
receive ocean or atmosphere fluxes. These changes are documented and tested in
Stage 12.10; residual medium/large under-melt remains structural
(Stage 12.7.audit, 12.7c).

## 4. Dynamics

The momentum balance includes wind drag, water drag, Coriolis acceleration, and
optional pressure-gradient forcing. Water drag uses the relative velocity
between the iceberg and the depth-dependent ocean current; wind drag uses the
exposed sail area. The Coriolis term is treated semi-implicitly. `iceberg_state`
is real(8) from Stage 12.6a; generic interfaces keep the legacy tests and
`app/main.f90` compiling.

In prescribed/reanalysis mode the observed latitude/longitude trajectory is
authoritative and the position update is first-order:
`dlat = v·dt/R`, `dlon = u·dt/(R cosφ)`. The legacy `model_coords_to_latlon`
mapping is blocked in that mode. The ~50° model-grid rotation is neglected in
the relative-flow calculation (documented limitation). Iceberg drift is
one-way: the ocean does not feel the iceberg.

## 5. Atmosphere, surface temperature, and phase change

The atmosphere provides wind, air temperature, dew point, pressure, cloud, and
snowfall. Surface fluxes include absorbed shortwave, longwave, sensible heat,
and latent heat. Solar geometry follows Spencer (1971); ice saturation vapour
pressure follows Murphy & Koop (2005). Sensible and latent transfer use a
neutral bulk formulation with fixed coefficients and no Monin–Obukhov stability
correction.

`T_surface` is prognostic with a finite effective surface heat capacity.
Positive surface energy at the melting point is partitioned into melt;
sublimation/deposition is represented through a vapour mass flux and latent-heat
sink/source. In the Stage 12 voxel path, exposed faces use autonomous
SW/LW/SH/LH Robin fluxes (Stage 12.7b); the bulk `diag%q_net_surface` is
retained only for regression. The discrete high-flux melting transition remains
a validation target.

## 6. Ocean thermodynamics and the ice–ocean interface

### 6.1 Freezing point and ocean EOS

The freezing temperature uses the EOS-80/UNESCO pressure-dependent polynomial
`Tf = (A0 + A1 sqrt(S) − A2 S) S + BP P`, with salinity as mass fraction at the
model boundary and pressure approximated hydrostatically. UNESCO EOS-80 is the
runtime default since Stage 11.8B (`EOS_MODE` unset); `EOS_MODE=LEGACY` selects
the historical Eckart path. TEOS-10 and a full iceberg seawater EOS are not
implemented. The Stage 11 ocean default is validated only for the N=1 30-day
matrix; the production scheduler remains blocked (T-39).

### 6.2 Bulk forced convection

The legacy basal path uses a flat-plate Reynolds/Nusselt correlation with a
laminar/turbulent transition at `Re = 5e5`, `L_char = L`. This is a
boundary-layer approximation for an iceberg, not a geometry-specific
derivation. At zero relative flow the bulk forced path gives zero transfer.

### 6.3 Three-equation interface and free convection

The selectable three-equation closure uses `gamma_T = K_T u_rel`,
`gamma_S = K_S u_rel` (`K_T=1.1e-3`, `K_S=3.1e-5`), an EOS-80 interface
temperature, and a mass-conserving salt balance. Stage 12.7c replaces the
zero-flow cutoff with a mixed-convection floor:
`gamma_T = max(K_T u_rel, 1e-5)` and `gamma_S = max(K_S u_rel, 1e-6)`. The floor
improves small/medium voxel ratios but leaves a large/low-ΔT under-melt; it is
a physical lower bound, not a calibration.

Natural convection is also available on the selectable
`THREE_EQUATION_NATURAL` path (Stage 10.11). Its Rayleigh cap is always active
at iceberg scale, the haline term is numerically inert, and the zero-flow floor
does not reach the observed quiescent band. The low-flow closure (Stage 10.13)
is a research parameterization behind `low_flow_closure_enabled` (OFF by
default); `t_scale` and `f_dc` are not calibrated.

### 6.4 Voxel interface and thermal solver

For each submerged voxel face, Stage 12.4 solves the three-equation interface
by bisection for `m ≥ 0` (no accretion), with per-depth `T/S/u/v` forcing,
`Tf(S_B,P_f)`, and melt capped at `VOXEL_MELT_CAP=0.20`. The interface
temperature is fed back as a Dirichlet condition in the thermal matrix.
Voxel conduction uses a Crank–Nicolson θ-scheme (`θ=0.5`) with PCG+Jacobi and
two Rannacher backward-Euler steps after geometry changes; the explicit scheme
is retained via `VOXEL_THERMAL_SCHEME=explicit`. The 3D `h_norm` per face and
the energy-consistent `φ` clamp are documented in Stage 12.4.

## 7. Lateral melt and wave erosion

The legacy lateral closure is depth-averaged and velocity-independent
(`C_LATERAL = 1e-6 m/(s·K)`); its dominance is formulation-dependent, and
observational constraints do not identify a unique field formulation
(N-07). The Stage 12 voxel path applies the three-equation interface to
submerged lateral faces and derives lateral mass loss from the voxel geometry.

Wave erosion follows the Bigg/NEMO form
`m_wave = max((1/12)(T_w+2) S_s [1+cos(pi c^3)], 0)/day`, with Douglas sea state
from significant wave height and optional Stokes drift. Both gates
(`ICEBERG_WAVE_EROSION`, `ICEBERG_STOKES_DRIFT`) default OFF. No real WAM
forcing has been validated; sea-ice drag and tides are not implemented.

## 8. External forcing and initialization

Stage 12 uses **GLORYS12** for ocean temperature, salinity, currents, SSH, and
sea ice, and **ERA5** for the atmosphere. The coupling is offline/prescribed
and one-way; the Stage 11 prognostic ocean is not the Stage 12 forcing. The
data contract is [`../references/reanalysis_data_plan.md`](../references/reanalysis_data_plan.md).

Legacy initialization uses EN4 T/S, IBCAO bathymetry, OSI-SAF SIC CDR v3.1,
and C3S CS2SMOS SIT. January 2020 uses real sea-ice initialization; April/July/
October seasonal sea-ice data remain missing (T-16). Daily-forcing acquisition
for Stage 12.9 is in progress; active manifests and status are in
[`../validation/INDEX.md`](../validation/INDEX.md).

## 9. Numerical implementation and verification

The Fortran model is built with fpm and linked to netcdf-fortran; builds always
require `-I/usr/include`. The full test battery is the implementation gate;
observational agreement is a separate validation question.

Stage 12 numerical schemes include voxel finite-volume conduction, CN/PCG/
Jacobi with Rannacher smoothing, explicit thermal fallback, three-equation
Stefan boundary treatment, free-convection floors, voxel geometry projection,
wave erosion, and reanalysis interpolation. Defaults, switches, and limitations
are inventoried in [`numerical_scheme_inventory.md`](numerical_scheme_inventory.md).
Test counts and current battery status are maintained in
[`model_physics_status.md`](model_physics_status.md), not duplicated here.

The CN matrix receives one local `T_B` per exposed submerged face and uses an
`open_face` mask from a six-neighbour exterior flood fill. Isolated cavities do
not exchange with the ocean or atmosphere. When `VOXEL_ENABLED=ON`,
`iceberg_run` can write three compact snapshots (`T`, `phi`, `open_mask`,
`tb_face`, mass, draft, energy) to `<run>_voxel.nc`; the time-series file also
records `sensible_energy` and `flushed_energy`. Plotting from saved NetCDF is
handled by `python/analysis/plot_voxel_results.py`.

## 10. Verification versus validation

Internal tests establish implementation consistency, conservation identities,
and regression behaviour. They do not establish observational validity. The
Stage 12.7a Enderlin23 hindcast is a controlled comparison, not a calibration;
Stage 12.8 is an exploratory fallback-forcing matrix; Stage 12.9 thesis writing
may use those results only with explicit fallback labeling.

## 11. Current limitations

- The Stage 11 prognostic ocean is frozen, not production-validated: N², real
  tides, 90-day runs, and the production scheduler remain open (N-15, T-38,
  T-39, T-43).
- Rectangular-prism legacy geometry lacks orientation, tilt, calving, and
  fracture; voxel geometry adds shape but not capsize or calving.
- Three-equation transfer coefficients are uncalibrated; the free-convection
  floor leaves large/low-ΔT under-melt; per-iceberg velocity dependence is not
  observable with current data.
- The bulk atmospheric transfer coefficients are neutral and fixed; no
  stability correction.
- Wave erosion is gated and has no real-wave validation; sea-ice drag and tides
  are absent.
- The Stage 12.8 matrix uses monthly-mean GLORYS and constant atmosphere; its
  drift and lifetime are lower bounds.
- Internal temperature is a lumped two-node model; internal melt and removed-ice
  enthalpy are incomplete.
- No full observational validation of the coupled thermodynamic trajectory.

These limitations are part of the model definition; regression-test success
must not be presented as physical validation.

## 12. Literature strategy

The repository bibliography contains 156 entries
(`grep -c '^@' docs/references/references.bib`). Direct equation sources,
comparison studies, background references, data products, and future-work items
are distinguished in [`../references/literature_matrix.md`](../references/literature_matrix.md).
New physics requires a literature basis, explicit equations, parameter
provenance, independent tests, and an external validation target where
applicable.
