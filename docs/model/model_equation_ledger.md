# Model Equation Ledger — Математическая спецификация текущей модели

**Дата:** 2026-09-10
**Current repository stage:** Stage 10.10.1
**Production baseline:** Stage 10.10 + salt-balance correction `stage10.10.1`
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

## 10.2 Three-equation ice-ocean interface (Stage 10.10 / 10.10.1)

Selectable separately from the bulk closure of §10 via
`set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION)`; the bulk closure
remains the baseline (the bulk statements in the scheme else-branch are unchanged;
only re-indentation and diagnostic-only outputs were added). Salinity as practical [PSU] (`S = 1000*S_kg`); pressure
`P = rho_w*g*z/1e4` [dbar].

Exchange (Jenkins et al. 2010 Table 2, U-based velocity scale):

`gamma_T = K_T U_rel`,  `gamma_S = K_S U_rel`,
`K_T = sqrt(C_d) Gamma_T = 1.1e-3`,  `K_S = sqrt(C_d) Gamma_S = 3.1e-5`.

Three equations:

(I) `T_B = Tf(S_B, P)`

(II) `rho_w c_w gamma_T (T_w - T_B) = m rho_i [L_f + c_i max(T_B - T_i, 0)]`

(III) `rho_w gamma_S (S_w - S_B) = rho_i m S_B`  (Stage 10.10.1 correction)

Reduction and solution: `S_B = gamma_S S_w / (gamma_S + (rho_i/rho_w) m)` with
`rho_i/rho_w = 910/1028 = 0.8852...`; bisection on `[0, m_hi]` with `m_hi`
doubled until the Eq.-II residual is non-positive (capped at 60 doublings),
then 60 bisection iterations (float32 production, float64 in the independent
Python layer). The residual is
`F(m) = rho_w c_w gamma_T (T_w - T_B) - m rho_i [L_f + c_i max(T_B - T_i, 0)]`.

Edges: `U_rel <= 0` or `gamma_T <= 0` or `T_w <= Tf(S_w,P)` -> `m = 0`,
`S_B = S_w`, `T_B = Tf(S_w,P)` (natural convection not implemented — same
documented limitation as §10); `S_w <= 0` -> heat-only balance with
`S_B = 0`; `gamma_S <= 0` -> heat-only balance with `S_B = S_w`. After
solution, `compute_basal_melt` applies the MELT_RATE_MIN noise guard as for
the bulk path.

Parameters: `rho_w = 1028`, `c_w = 3974`, `rho_i = 910`, `L_f = 3.34e5`,
`c_i = 2009`, `T_i = -10` degC (Holland & Jenkins 1999; model `rho_i`, `L_f`).
The conductive term into the ice interior uses the constant `T_i`; physically
consistent conduction requires internal thermal evolution, which is a future
stage. Note: `T_i = -10` is a model-selected constant internal temperature,
not from H&J99 (H&J99 solve shelf conduction explicitly).

Independent validation: the Stage 10.10.1 Fortran test (25 checks) and
`python/validation/three_equation.py` + `python/tests/test_three_equation.py`
(65 checks), including a shared cross-language contract value
(`m ~ 1.0438e-8` m/s for the H&J99 Table 1 anchor and `m = 4.067e-6` m/s for
the production end-to-end case). See
`docs/validation/stage10.10_three_equation_interface.md` (superseded) and
`docs/validation/stage10.10.1_three_equation_interface.md`.

## 10.3 Natural-convection basal melt (Stage 10.11)

Selectable as an extension of the three-equation scheme via
`set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL)`.
When active, the total heat and salt transfer coefficients combine
forced convection (U-based, §10.2) and natural convection:

Forced convection (U-based, J2010 Table 2):
    `gamma_T_forced = K_T * U_rel`,  `gamma_S_forced = K_S * U_rel`

Natural convection (Fujii et al. 1973 horizontal-plate correlation; Churchill 1977 mixing):
    Horizontal plate facing downward (heated down / cooled up)
    Characteristic length = iceberg length `L` (horizontal scale of the plate,
    per Fujii et al. 1973; production caller passes `state%L`. Gayen et al.
    2016 is CONTEXT only — it studies a vertical ice face and does not set a
    cell scale for a horizontal base; the L_char = D attribution was a
    mis-citation, removed in the Stage 10.11.2 audit)
    Double-diffusive Rayleigh number:
    `Ra_eff = g * L^3 / (nu * alpha) * [beta_T * (T_w - T_B) + beta_S * (S_w - S_B) * Le]`
    where `beta_T = 3.0e-5 1/K`, `beta_S = 7.8e-4 1/PSU`, `Le = 100`,
    `nu = 1.82e-6 m^2/s`, `alpha = k / (rho_w * c_w)`.
    Nusselt number (Fujii et al. 1973, horizontal plate facing downward):
    Laminar  (`Ra < 1e7`):  `Nu = 0.27 * Ra^0.25`
    Turbulent (`Ra >= 1e7`): `Nu = 0.15 * Ra^(1/3)`
    Natural-convection transfer coefficients:
    `gamma_T_nat = Nu * k / (L * rho_w * c_w)`,
    `gamma_S_nat = gamma_T_nat * (K_S / K_T)`.

Mixed convection (Churchill 1977, exponent n=3):
    `gamma_T_eff = (gamma_T_forced^3 + gamma_T_nat^3)^(1/3)`
    `gamma_S_eff = (gamma_S_forced^3 + gamma_S_nat^3)^(1/3)`.

The effective transfer coefficients `gamma_T_eff`, `gamma_S_eff` are used
in the three-equation system (§10.2) in place of the purely forced values.
The three-equation salt balance (Eq. III) retains the Stage 10.10.1
density-weighted correction `rho_w gamma_S (S_w - S_B) = rho_i m S_B`.

Rayleigh number is capped at `Ra_max = 1e10` to avoid unphysical
extrapolation beyond the validated range of the Fujii correlations.
At `U_rel = 0`, the natural-convection closure provides finite melt rates
consistent with quiescent laboratory observations (0.01–1 m/day range).

Parameters (Stage 10.11 additions):
`beta_T = 3.0e-5 1/K`, `beta_S = 7.8e-4 1/PSU`, `Le = 100`,
`Nu_lam_coeff = 0.27`, `Nu_lam_exp = 0.25`,
`Nu_turb_coeff = 0.15`, `Nu_turb_exp = 1/3`,
`Ra_trans = 1e7`, `Ra_max = 1e10`, `Churchill_n = 3`.

Independent validation: Fortran test `iceberg_test_10p11_natural_convection`
(23 checks, delivered in the Stage 10.11.2 audit; the original Stage 10.11
claim of a 15-check Fortran test was never delivered in commit 6a0014e) +
Python `python/tests/test_three_equation_natural.py` (70 checks),
including zero-flow, low-flow continuity, mixed-convection regime, and
cross-language contract (`m = 1.638e-8 m/s` at `U_rel=0`, `T_w=2°C`,
`S_w=34.5 PSU`, `L=100m`, `D=50m`).

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

The FPM suite currently contains 52 test targets. Tests establish implementation identities, numerical regressions and selected analytical properties. They do not constitute independent observational validation.

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