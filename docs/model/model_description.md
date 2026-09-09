# Scientific Model Description

## 1. Scope

The repository contains a Lagrangian iceberg module coupled to a legacy Eulerian ocean/sea-ice modelling framework. An iceberg is represented as a rectangular prism whose position, velocity and dimensions evolve in time. Atmospheric, oceanic, bathymetric and sea-ice forcing can be supplied from external products.

This document is the narrative description of the current model. The equation ledger is the mathematical specification; the physics-status document records the maturity and limitations of individual blocks.

## 2. Grid and coordinates

The reconstructed real grid has 133 × 105 nodes, with 132 × 104 active cells. It is a B-grid with DX = DY = 13.89 km. Geographic coordinates are supplied by KOORD.DAT and bathymetry/land mask by hhh.bar. The real-grid reconstruction uses IBCAO V5.2 at 400 m resolution in EPSG:3996.

Iceberg motion is prognosed in model x/y coordinates. Atmospheric and oceanic forcing is interpolated at the current x/y position. Geographic latitude/longitude are diagnostic coordinates; the current implementation does not update the stored latitude/longitude state during each time step.

## 3. Iceberg state and geometry

The prognostic mechanical state is based on `[x, y, u, v, L, W, H]`. The surface-temperature extension adds prognostic `T_surface`; phase-change diagnostics include atmospheric vapour mass flux.

For a rectangular prism:

- `V = L W H`;
- `M = rho_ice V`;
- `D = H rho_ice / rho_water`;
- `A_base = L W`;
- `A_lat = 2 H (L + W)`.

The present geometry is intentionally simple. No orientation, tilt, calving, fracturing or internal thermal structure is prognosed.

## 4. Dynamics

The iceberg momentum balance includes wind drag, ocean drag, Coriolis acceleration and pressure-gradient forcing. The Coriolis term uses the repository's semi-implicit treatment. Ocean drag is based on the relative velocity between the iceberg and the depth-dependent ocean current.

The current ocean-side thermodynamic implementation uses the same relative-flow concept for heat transfer. This is important because a vertically sheared current can produce a different melt forcing from a single vertically averaged speed.

## 5. Atmospheric thermodynamics

The modernized surface flux block contains absorbed shortwave radiation, longwave radiation, sensible heat and latent heat. Solar geometry was modernized using an astronomical approximation following Spencer (1971). Shortwave attenuation includes clear-sky and cloud terms.

Sensible and latent turbulent fluxes use a neutral bulk-transfer formulation. Ice saturation vapour pressure follows Murphy & Koop (2005). The current coefficients are engineering closures rather than a site-specific stability-resolved atmospheric boundary-layer model.

## 6. Surface temperature and phase change

`T_surface` is prognostic. A finite effective surface heat capacity is used to partition atmospheric/ocean-free surface energy between temperature change and phase change. At the melting point, positive surface energy is converted into melt energy.

The latent heat term is retained explicitly in the surface energy balance. Sublimation is represented by a negative vapour mass flux and an associated latent-heat sink; deposition is positive. Melt thickness is derived from the positive melt-energy flux using ice density and latent heat of fusion.

The present crossing treatment is energy-accounting consistent for the implemented discrete formulation, but the high-flux melting transition remains a known area for further independent physical validation.

## 7. Ocean thermodynamics

### 7.1 Freezing point

The ocean freezing temperature uses the EOS-80/UNESCO pressure-dependent polynomial:

`Tf = (A0 + A1 sqrt(S) - A2 S) S + BP P`,

where practical salinity is represented in PSU and pressure is approximated hydrostatically from depth. The implementation is a freezing-point calculation, not a complete EOS-80 or TEOS-10 seawater density equation of state.

### 7.2 Relative-flow heat transfer

The basal melt calculation uses the temperature excess at iceberg draft relative to the local freezing point. The ocean-side transfer coefficient is calculated from a Reynolds/Nusselt correlation with a laminar/turbulent transition at `Re = 5 × 10^5`:

- laminar: `Nu = 0.664 Re^0.5 Pr^(1/3)`;
- turbulent: `Nu = 0.037 Re^0.8 Pr^(1/3)`;
- `gamma_T = Nu k / L_char`.

The production characteristic length is the iceberg `L`. This is an explicit approximation because iceberg orientation is not represented. The correlation originates from canonical flat-plate boundary-layer heat-transfer theory; its application to an iceberg is therefore a modelling approximation, not a direct geometry-specific derivation. At zero relative flow the current forced-convection formulation gives zero transfer; natural convection is not yet represented.

The empirical iceberg literature, including Weeks & Campbell (1973) and FitzMaurice & Stern (2018), is retained for comparison and future calibration/validation rather than being conflated with the flat-plate derivation.

## 8. Lateral melt

The lateral melt block currently uses a depth-averaged thermal forcing formulation over the submerged draft, with depth-dependent freezing temperature. The formulation remains a legacy/approximate closure. Laboratory results demonstrate that shear and nonlinear velocity dependence can matter for iceberg side melt, motivating future modernization.

## 9. External forcing and initialization

The real-grid experiment chain uses:

1. ERA5 atmospheric forcing, including wind, air temperature, dew point, pressure, cloud and snowfall fields;
2. EN4 ocean temperature and salinity profiles;
3. IBCAO V5.2 bathymetry;
4. OSI-SAF SIC CDR v3.1 for sea-ice concentration initialization;
5. C3S CS2SMOS sea-ice thickness L4 combined v1.1 for sea-ice thickness initialization.

For 2020-01-01, the current real sea-ice initialization reconstructs concentration and thickness on the model wet mask and produces the legacy category files `1_1.ice`–`1_5.ice`. The initialization uses an area/volume-preserving two-bin reconstruction within the prescribed thickness categories.

## 10. Numerical verification

The repository uses FPM/Fortran tests and targeted analytical audits. The current baseline has 50 FPM test targets passing locally, with strict Fortran compilation clean after the CI line-length corrections. Real-data tests are separated from synthetic tests where generated forcing/grid files are unavailable in a fresh CI checkout.

Verification is not treated as validation: passing algebraic and regression tests demonstrates implementation consistency, not agreement with independent observations.

## 11. Scientific limitations

The main limitations relevant to the next modernization steps are:

- rectangular geometry and absent orientation;
- approximate characteristic length for ocean-side transfer;
- flat-plate forced-convection correlation used as an iceberg approximation;
- no natural convection at zero relative flow;
- neutral, fixed atmospheric transfer coefficients;
- unresolved provenance/sensitivity questions for some shortwave attenuation constants;
- legacy lateral-melt closure;
- freezing-point calculation without a full seawater EOS;
- no TEOS-10 thermodynamic framework;
- no independent observational validation of the complete coupled thermodynamic trajectory yet;
- stored latitude/longitude are not currently prognostic during motion.

These limitations are part of the model definition and should not be hidden by regression-test success.

## 12. Literature strategy

The repository bibliography contains 137 unique records. Direct equation sources are distinguished from comparison, background, data and future-work sources in `docs/references/literature_matrix.md`. The private `work_references.bib` may retain local PDF paths, while `docs/references/references.bib` remains machine-independent.

The next physics stages should add or revise equations only after the relevant literature basis, assumptions, parameter values and independent validation target are documented.