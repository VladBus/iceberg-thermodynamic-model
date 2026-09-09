# Model Equation Ledger — Математическая спецификация текущей модели

**Дата:** 2026-09-10  
**Current repository stage:** Stage 10.6.1  
**Production baseline:** Stage 10.6 + documentation correction `40d4a3b`  
**Units:** SI in the iceberg module unless explicitly noted.

---

## 1. Geometry

The iceberg is a rectangular prism with prognostic dimensions `L`, `W`, `H`.

`V = L W H`  
`M = rho_ice V`  
`D = H rho_ice / rho_water`  
`A_base = L W`  
`A_lat = 2 H (L + W)`

Constants: `rho_ice = 910 kg m^-3`, `rho_water = 1028 kg m^-3`.

Geometry is updated after thermodynamic melt. The model does not currently prognose orientation, tilt, fracturing or internal temperature structure.

## 2. Position and coordinates

`dx/dt = u`  
`dy/dt = v`

With the current explicit time step:

`x(n+1) = x(n) + u(n) dt`  
`y(n+1) = y(n) + v(n) dt`

`DX = DY = 13890 m`. Model x/y is authoritative for moving forcing. Geographic latitude/longitude are diagnostic and are obtained from the model grid coordinate fields. The stored lat/lon state is not currently updated during every motion step.

## 3. Dynamics

The horizontal momentum equations are

`M du/dt = F_wind + F_water + F_coriolis + F_pressure`

`M dv/dt = F_wind + F_water + F_coriolis + F_pressure`.

Wind and water drag act on relative velocities. Coriolis is treated semi-implicitly. The pressure-gradient forcing is retained from the existing model formulation.

## 4. Atmospheric forcing

ERA5 supplies surface pressure, 10-m wind, 2-m air temperature/dew point, total cloud cover and snowfall. Surface fields are interpolated horizontally to the current iceberg position.

Conversions include K→°C for temperatures and m/s→cm/s where required by legacy interfaces. The iceberg thermodynamic flux equations use SI units.

## 5. Solar radiation

The shortwave input is based on

`SW_down = S0 cos(Z) T_clear T_cloud`,

with `S0 = 1353 W m^-2` and solar zenith angle `Z` from astronomical solar geometry. Spencer (1971) is the source for the declination/equation-of-time approximation.

The current attenuation parameterization contains Rayleigh, water-vapour, aerosol and cloud terms. The exact empirical constants are documented in source code; their provenance and sensitivity remain an open documentation/validation item.

## 6. Surface longwave and turbulent fluxes

The surface energy budget is assembled as

`Q_nonlatent = SW_absorbed + LW_down + LW_up + Q_SH`

`Q_LH = m_vapor L_s`

`Q_surface = Q_nonlatent + Q_LH`.

Sensible heat uses the neutral bulk form

`Q_SH = rho_air c_p C_H U (T_air - T_surface)`.

Latent mass exchange is

`m_vapor = rho_air C_E U (q_air - q_sat,ice)`

and

`Q_LH = m_vapor L_s`.

Negative `m_vapor` denotes sublimation; positive values denote deposition. Ice saturation vapour pressure follows Murphy & Koop (2005). The present atmospheric closure is neutral and uses fixed transfer coefficients.

## 7. Prognostic surface temperature and phase change

The surface temperature has an effective heat capacity `C_eff`. Below the melting point, net surface energy changes `T_surface`. When the discrete step crosses the melting point, energy is partitioned at the crossing. At the melting point,

`Q_melt = max(Q_surface, 0)`

and

`m_melt = Q_melt / (rho_ice L_f)`.

Geometry responds to both melt and atmospheric ice-mass exchange:

`dH/dt = -(m_melt + m_vapor/rho_ice)`

for the implemented surface contribution, with corresponding geometry updates in the production module.

The crossing treatment has passed independent implementation checks, but complete external validation of the high-flux surface-energy response remains pending.

## 8. Ocean forcing

EN4 temperature and salinity profiles are interpolated horizontally and vertically. At iceberg draft `D`, ocean temperature is interpolated within the available profile and extrapolated using the nearest available level when the draft exceeds the deepest available model level in a shallow column.

## 9. EOS-80 freezing point

The freezing temperature is

`Tf = (A0 + A1 sqrt(S) - A2 S) S + BP P`

with

`A0 = -0.0575`  
`A1 = 1.710523e-3`  
`A2 = 2.154996e-4`  
`BP = -7.53e-4`.

`S` is practical salinity in PSU and `P = rho_w g z / 1e4` is pressure in dbar. The implementation follows the Fofonoff & Millard (1983)/UNESCO freezing-point formulation, with Gill (1982) as supporting reference.

The implementation computes freezing point only. It is **not** a complete EOS-80 or TEOS-10 density equation of state.

A literature check reproduces `Tf(S=40 PSU, P=500 dbar) = -2.588567 °C`.

## 10. Ocean-side relative flow and heat transfer

For each ocean profile level,

`U_rel(z) = sqrt((u_water(z)-u_ice)^2 + (v_water(z)-v_ice)^2)`.

The characteristic length is currently

`L_char = L`.

This is an approximation because iceberg orientation is not prognosed.

The Reynolds number is

`Re = U_rel L_char / nu`.

For `Re < 5e5`:

`Nu = 0.664 Re^0.5 Pr^(1/3)`.

For `Re >= 5e5`:

`Nu = 0.037 Re^0.8 Pr^(1/3)`.

The transfer coefficient is always calculated from the canonical relation

`gamma_T = Nu k / L_char`.

Therefore the expanded forms are:

**Laminar**

`gamma_T = 0.664 k Pr^(1/3) U_rel^0.5 nu^(-0.5) L_char^(-0.5)`.

**Turbulent**

`gamma_T = 0.037 k Pr^(1/3) U_rel^0.8 nu^(-0.8) L_char^(-0.2)`.

The Stage 10.6.1 correction `40d4a3b` synchronized these negative length exponents across documentation and source comments.

Basal melt is then

`DeltaT_b = max(0, T(D) - Tf(D))`

`m_basal = gamma_T DeltaT_b / (rho_ice L_f)`.

The implemented correlation is canonical flat-plate forced-convection theory applied as an iceberg approximation. It is not a geometry-specific derivation for an iceberg. At `U_rel = 0`, the current forced-convection closure gives zero transfer; natural convection is not included.

## 11. Lateral melt

The submerged thermal excess is depth-averaged:

`<DeltaT>_D = (1/D) integral_0^D max(0, T(z)-Tf(z)) dz`.

The current lateral melt closure remains legacy/approximate. Published laboratory work shows sensitivity to flow speed and vertical shear, so this block should not be treated as fully validated.

## 12. Real-grid and initialization definitions

The real grid contains 133×105 nodes and 132×104 active cells, with DX=DY=13.89 km. KOORD.DAT supplies grid coordinates and hhh.bar supplies bathymetry/land classification.

Real sea-ice initialization for 2020-01-01 uses OSI-SAF SIC CDR v3.1 and C3S CS2SMOS SIT L4 combined v1.1. The reconstruction produces the legacy category files `1_1.ice`–`1_5.ice`.

## 13. Numerical conventions

The standard thermodynamic/dynamic production time step is one hour unless an experiment explicitly changes it. The iceberg module uses SI units; legacy ocean-model interfaces may use CGS. Moving forcing is evaluated from the current x/y position rather than the initial position.

## 14. Verification versus validation

The FPM suite currently contains 50 test targets. Tests establish implementation identities, numerical regressions and selected analytical properties. They do not constitute independent observational validation.

The scientific validation requirement for future stages is: equation/source provenance + independent analytical check + regression coverage + external observation/benchmark where available.

## 15. Primary references

- Spencer (1971) — solar geometry.
- Murphy & Koop (2005) — ice saturation vapour pressure.
- Fofonoff & Millard (1983); Gill (1982) — seawater freezing point.
- Eckert & Drake (1959) — canonical heat/mass transfer correlations.
- Weeks & Campbell (1973) — empirical iceberg melt context.
- Holland & Jenkins (1999); Jenkins et al. (2010) — three-equation ice-ocean thermodynamics.
- FitzMaurice & Stern (2018) — tabular iceberg basal melt comparison.
- Bigg et al. (1997); Martin & Adcroft (2010); NEMO-ICB literature — iceberg dynamics/thermodynamics and coupled modelling context.

Full records are maintained in `docs/references/references.bib`; source-to-component roles are maintained in `docs/references/literature_matrix.md`.