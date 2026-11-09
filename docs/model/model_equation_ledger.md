# Model Equation Ledger — Mathematical Specification of the Current Model

> **Legacy prism / Stage 11 reference — Sections 1–16.**
> Sections 1–16 describe the rectangular-prism iceberg and Stage 11 ocean
> formulation. They are retained for historical and research traceability and
> must not automatically be interpreted as the current Stage 12 model.
> Section 17 is the current Stage 12 voxel/reanalysis specification.

**Date:** 2026-11-08
**Current repository stage:** **Stage 11 FROZEN** (D-51, tag `stage11-final-frozen`); **Stage 12 active** (GLORYS12 + ERA5 voxel iceberg). Sections 1–16 are the rectangular-prism and Stage 11 ocean specification and remain valid for the legacy/regression path. Section 17 specifies the implemented Stage 12 voxel, reanalysis, and wave formulations; it does not retroactively change the Stage 11 reference. Stage 12.9a acquisition is complete; see `docs/validation/INDEX.md`.
**Production baseline:** Stage 10.13 (low-flow closure behind `low_flow_closure_enabled`; OFF = Stage 10.12/10.10 behavior unchanged)
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

`gamma_T = K_T U_rel`, `gamma_S = K_S U_rel`,
`K_T = sqrt(C_d) Gamma_T = 1.1e-3`, `K_S = sqrt(C_d) Gamma_S = 3.1e-5`.

Three equations:

(I) `T_B = Tf(S_B, P)`

(II) `rho_w c_w gamma_T (T_w - T_B) = m rho_i [L_f + c_i max(T_B - T_i, 0)]`

(III) `rho_w gamma_S (S_w - S_B) = rho_i m S_B` (Stage 10.10.1 correction)

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
the production end-to-end case). See the consolidated
`docs/wiki/stages/stage10/stage10.10_three_equation_interface.md` report, which
includes the Stage 10.10.1 mass/salt correction.

## 10.3 Natural-convection basal melt (Stage 10.11)

Selectable as an extension of the three-equation scheme via
`set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL)`.
When active, the total heat and salt transfer coefficients combine
forced convection (U-based, §10.2) and natural convection:

Forced convection (U-based, J2010 Table 2):
`gamma_T_forced = K_T * U_rel`, `gamma_S_forced = K_S * U_rel`

Natural convection (horizontal-plate correlation, see attribution note below;
Churchill 1977 mixing):
Horizontal plate facing downward
Characteristic length = iceberg length `L` (horizontal scale of the plate;
production caller passes `state%L`. Note the source correlations use the
Goldstein-Sparrow-Jones scale `L* = A/p` (area/perimeter), not `L`; see
Stage 10.11.3 audit §10. Gayen et al. 2016 is CONTEXT only — it studies a
vertical ice face and does not set a cell scale for a horizontal base; the
L_char = D attribution was a mis-citation, removed in the Stage 10.11.2 audit)
Double-diffusive Rayleigh number:
`Ra_eff = g * L^3 / (nu * alpha) * [beta_T * (T_w - T_B) + beta_S * (S_w - S_B) * Le]`
where `beta_T = 3.0e-5 1/K`, `beta_S = 7.8e-4 1/PSU`, `Le = 100`,
`nu = 1.82e-6 m^2/s`, `alpha = k / (rho_w * c_w)`.
Nusselt number (horizontal plate):
Laminar (`Ra < 1e7`): `Nu = 0.27 * Ra^0.25`
Turbulent (`Ra >= 1e7`): `Nu = 0.15 * Ra^(1/3)`
Attribution (corrected in Stage 10.11.3): the operative turbulent
`0.15*Ra^(1/3)` coefficient is from Lloyd & Moran 1974 (JHT 96(4):443-447,
electrochemical, `L* = A/p`, turbulent range 8e6-1.6e9), NOT from Fujii
et al. 1973 — the latter is a theoretical, laminar, uniform-heat-flux study
whose reported dependence is `Nu ~ Ra^(1/5)`. The laminar `0.27*Ra^(1/4)`
coefficient is the standard stable-orientation horizontal-plate value.
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
extrapolation beyond the validated range of the horizontal-plate correlations.
Stage 10.11.3 audit finding: the cap is ALWAYS active for realistic icebergs
(uncapped anchor `Ra = 5.7e19` at `L=100 m`; `L` for cap = 0.056 m haline-only /
1.43 m thermal-only), so `Nu` is pinned at `0.15*(1e10)^(1/3) = 323.17` and the
zero-flow result is set by the cap rather than by the physics. In this regime the
haline term (including its `Le=100` factor) is numerically inert: dropping it
entirely reproduces the same `m`, and `beta_T`/`beta_S` variations of +-1 order
leave `m` unchanged.
At `U_rel = 0`, the closure provides a finite, cap-determined low-flow floor
`m = 1.638e-8 m/s = 1.4e-3 m/day` (anchor `T_w=2 C`, `S_w=34.5 PSU`,
`L=100 m`, `D=50 m`). This is **7-700x below** the observed quiescent
laboratory/field band of 0.01-1 m/day (Stage 10.8.2), i.e. it does NOT close the
zero-flow gap. The earlier Stage 10.11 claim of consistency with the 0.01-1 m/day
band was incorrect and is removed. The physically motivated (stabilizing) haline
sign would instead give `Ra<0 -> Nu=0 -> m=0`; the real quiescent mechanism is
double-diffusive / diffusion-limited convection (Martin & Kauffman 1977;
Keitzl et al. 2016; Middleton et al. 2021), which this closure does not
represent. See `docs/wiki/stages/stage10/stage10.11.3_natural_convection_physics_audit.md`.

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

## 10.4 Prognostic internal thermal evolution (Stage 10.12)

Two-node lumped interior model (design note Variant C; effective bulk
parametrization — Bi ≫ 1, diffusion time ≫ run length). The interior
temperature `T_ice` becomes a prognostic state variable replacing the
constant `T_i = -10` (now `T_ICE_INIT`, an initial condition) inside the
three-equation basal closure Eq. II.

Definitions:

    H_int  = max(H - H_EFF, H_MIN_INT)               [m]  (H_MIN_INT = 0.5)
    C_int  = rho_i * C_ICE * H_int                   [J/(m2 K)]
    q_cond = 2 * K_ICE * (T_surface - T_ice) / H     [W/m2]  (K_ICE = 2.2)
    q_bot  = m_basal * rho_i * CP_ICE_3EQ * max(T_B - T_ice, 0)  [W/m2]

Interior ODE (explicit Euler, clamped to [T_ICE_MIN, T_ICE_MAX] = [-100, 0] C):

    C_int dT_ice/dt = q_cond - q_bot

Energy-conserving lagged coupling: `q_cond` is subtracted from the surface
net flux inside `compute_surface_melt` (`q_internal_exchange`), so energy
leaving the skin enters the interior; `q_bot` exits to the base. The factor 2
in `q_cond` is the harmonic layer-centre separation `d = H/2`.

Switch: `thermal_evolution_enabled` (default `.true.`, setter
`set_thermal_evolution`). Fully gates Stage 10.12 in
`iceberg_thermodynamics_step`: ON computes `q_cond`, subtracts it from the
surface budget and updates the interior; OFF skips all of it
(`compute_surface_melt` called without the optional argument, interior
frozen, 10.12 diagnostics defined at legacy values) — bit-identical legacy
for both bulk and three-equation paths (3eq solver `T_ice` argument was
already gated). Verified by test block F.1-F.4 (OFF-switch legacy
invariance, surface budget bitwise-equal to a legacy call).

New diagnostics: `t_ice`, `dT_ice_dt`, `c_eff_int`, `t_ice_bound`.
Initial condition: `iceberg_init` sets `T_ice = T_ICE_INIT = -10 C`.

Independent validation: Fortran `iceberg_test_10p12_thermal_evolution`
(21 checks, 21/21 PASS, incl. OFF-switch legacy invariance F.1-F.4) +
Python float64 replica
`python/validation/internal_thermal.py` /
`python/tests/test_internal_thermal_evolution.py` (35 checks, 35/35 PASS);
cross-language contract `C_int(50 m) = 94594496 (float32) / 94594500 (float64)`.
Known limitations: lumped parametrization, no internal melt at `T_ice = 0`
(excess energy discarded at the clamp), removed-ice enthalpy not tracked
(intensive `T_ice` through geometry shrink), `K_ICE = 2.2 W/(m K)` is a model
parameter (literature range 2.0-2.3), not calibrated.
See `docs/wiki/stages/stage10/stage10.12_internal_thermal_evolution.md`.

## 10.5 Diffusion-limited / double-diffusive low-flow closure (Stage 10.13)

Research parameterization behind the switch `low_flow_closure_enabled`
(default `.false.`; setter `set_low_flow_closure`). Active only inside the
`BASAL_MELT_SCHEME_THREE_EQUATION` branch of `compute_basal_melt`; the bulk
and `THREE_EQUATION_NATURAL` paths are unchanged. Formulation (Phase A design
note; prototype `python/validation/low_flow.py`; Phase C production
`solve_three_equation_interface_low_flow` in `src/iceberg_thermodynamics.f90`):

Diffusion-limited sublayer thickness (regularized; MK77/Keitzl16 scale):

    delta_S = clip(sqrt(kappa_S * t_scale), delta_min, delta_max)      [m]
    kappa_T = THERMAL_CONDUCTIVITY / (rho_w * c_w)     (= 1.371e-7 m2/s)
    kappa_S = kappa_T / LEWIS_NUMBER                  (= 1.371e-9 m2/s)
    t_scale = LOW_FLOW_TIME_SCALE_S = 86400 s
    delta_min = 1e-4 m, delta_max = 5e-2 m

Double-diffusive enhancement factor (Middleton et al. 2021 criterion):

    R_rho  = alpha_T dT / (beta_S dS_psu)             (dS_psu regularized)
    Re_b   = eps / (nu * N^2),  eps = (sqrt(C_D_w) U)^3 / (k_vK delta_S)
    N^2    = g * beta_S * dS_psu / delta_S
    f      = LOW_FLOW_F_DC (=2.5)  if (R_rho > 1/Le AND Re_b < 1), else 1

Blend into the effective transfer coefficients (cosine smoothstep):

    w = 0.5 * (1 - cos(pi * clip((U - U_low)/(U_high - U_low), 0, 1)))
    U_low = 1e-3 m/s, U_high = 1e-2 m/s
    gamma_T_low = f * k_w * (L_f + c_i * max(T_B - T_i, 0)) / (delta_S * rho_w * c_w * L_f)
    gamma_S_low = gamma_T_low * (K_S / K_T)
    gamma_T_eff = (1 - w) * gamma_T_low + w * gamma_T_forced      (same for S)

The melt rate is then obtained from the **unchanged** three-equation solve
(`solve_three_equation_interface` with `allow_zero_flow = .true.` on this
path only; the legacy guard `U_rel <= 0 -> m = 0` remains the default of the
shared solver). A minimal Picard loop (<= `LOW_FLOW_MAX_ITER` = 4,
tolerance `LOW_FLOW_TOL` = 1e-6 relative on m) iterates the conduction term
in `gamma_T_low`; on NaN the forced branch is used as a deterministic
fallback.

Characteristic values (T=2 C, S=35 PSU, L=100 m, D=50 m): U=0 -> m = 0.107
m/day (regime 3, f=2.5); U=0.1 m/s -> ON == OFF bit-identical (forced).
Diagnostics: `low_flow_enabled/active/regime/u_rel/re_b/ri_star/r_rho/
delta_s/delta_t/f/gamma_t/gamma_s/iter/converged` (defined at legacy values
when OFF).

Validation: Fortran `iceberg_test_10p13_low_flow` (23 checks) +
Python/Fortran comparison `python/validation/low_flow_fortran_comparison.py`
(56 checks) + Python prototype `test_low_flow.py` (167 checks). Systematic
differences vs the Python reference (documented, within tolerance): kappa_S
convention (Le=100), interface freshening of the 3eq solve, gamma-blending
before the solve (vs m-blending in the Python hybrid). Known limitations:
t_scale dominant sensitivity, f_dc not calibrated, research parameterization
(not universal validation).
See `docs/wiki/stages/stage10/stage10.13_phase_c_results.md`,
`docs/wiki/stages/stage10/stage10.13_phase_b_results.md`,
`docs/wiki/stages/stage10/stage10.13_diffusion_limited_low_flow_design_note.md`.

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

The FPM suite currently contains 64 test targets (count as of 2026-10-18, verified by `ls test/*.f90 | wc -l`). Tests establish implementation identities, numerical regressions and selected analytical properties. They do not constitute independent observational validation.

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

## 16. Ocean advection schemes (11.3C authoritative note)

Forensic code audit (Stage 11.3C) established the ACTUAL schemes; this
ledger previously did not specify ocean advection — no contradiction is
corrected here, coverage is added. Full inventory:
`docs/model/numerical_scheme_inventory.md`.

- `advt`/`advs` (3D T/S): explicit 1st-order upwind predictor (X/Y/Z) +
  Zalesak FCT corrector in all three directions; final `t2/s2 = cd`.
- HISTORICAL NOTE: comments in `advection_3d_t.f90` (lines ~20/83/139-144)
  and `advection_3d_s.f90` (~13/121) claim an "implicit Thomas" vertical
  solve. The code performs a single explicit upwind sweep over old values;
  no tridiagonal system is assembled. Vertical advection is EXPLICIT and
  CFL-limited (measured Cz max 4.63 over 29 d without blowup — FCT-Z
  absorbs overshoot). Comments left untouched (audit-only stage).
- `advsh` (barotropic momentum): Lax–Richtmyer predictor with FCT
  anti-diffusion INTENTIONALLY disabled (`apx2/apy2 = 0`, `CDY*0` in
  X-block) — do not "fix" (stability constraint, AGENTS.md).
- Block 200: semi-implicit Coriolis via analytic 2×2 solve
  (`asa1 = f·dt/2`, `asa = 1+asa1²`) + explicit baroclinic/DPX/Laplacian.
- Block 210: genuine IMPLICIT Thomas solve for vertical viscosity
  (forward `uca/unu`, backward substitution; pivots negative by
  construction per Stage 10.22).

## 17. Stage 12 voxel, three-equation, wave, and reanalysis formulation

This section is the mathematical specification of the **implemented Stage 12
path**. It is supplementary to Sections 1–16 and does not alter the frozen
Stage 11 reference. Detailed derivations, tests, and limitations are in
[`../wiki/stages/stage12/`](../wiki/stages/stage12/).

### 17.1 Voxel energy balance (Crank–Nicolson)

For active voxels (`φ > 1e-12`) with heat capacity `C_i = φ_i ρ_ice c_ice V`:

```text
(C_i/Δt) (T_i^{n+1} − T_i^n) = θ F_i(T^{n+1}) + (1−θ) F_i(T^n)
```

- Meaning: implicit/explicit blend of conduction and boundary fluxes for each voxel.
- Units: `C_i` in J/K, `T` in °C, `F_i` in W, `Δt` in s.
- Parameters: `θ = ICEBERG_THETA = 0.5` (default); `θ=1` is backward Euler.
- Implementation: `src/voxel_thermal_solver.f90`; PCG+Jacobi with
  `ICEBERG_CG_TOL=1e-10`; two Rannacher backward-Euler steps after geometry
  changes.
- Limitations: boundary linearisation, melt cap, and grid-rotation neglect are
  model assumptions; see Stage 12.4.

### 17.1a Voxel draft and freeboard

For the remaining solid cells, with `h` the voxel edge and `phi` the ice
**volume fraction**:

```text
NX*h = L, NY*h = W, NZ*h = H
z_bot = (k_bot - 1)*h,  k_bot = min{k : V_k > 0}
z_top = k_top*h,        k_top = max{k : V_k > 0}
z_wl  = level where cumulative phi*V equals mass/rho_w
D     = z_wl - z_bot
F_b   = z_top - z_wl
```

- Meaning: `D` is the draft measured from the remaining lower surface;
  `F_b` is the actual geometric freeboard of the remaining body.
- Implementation: `voxel_iceberg_compute_state`; `phi` is not used as a
  vertical height. `waterline_height` is retained separately for face-depth
  calculations.
- Assumption: the specification assumes no vertical cavities in a column; a
  detected internal empty layer invalidates the cumulative waterline formula.
- Limitation: vertical coordinates are fixed; the voxel body is not
  repositioned upward as its bottom melts. A body can therefore appear
  over-submerged after strong bottom erosion.

### 17.2 Submerged-face conduction boundary

```text
G_b,f = 2 k_ice A_f / h_norm,f
T_b,f = Tf(S_f, P_f)
```

- Meaning: Dirichlet ice–water temperature and conductance on **each exposed
  face** `f`; `T_b,f` is never averaged across faces of one voxel.
- Units: `G_b,f` in W/K, `k_ice` in W/(m·K), `A_f` in m², `h_norm,f` in m,
  `T_b,f` in °C.
- Implementation: `src/voxel_thermal_solver.f90`; `Tf` from EOS-80; the
  `tb_face(i,j,k,f)` array supplies the CN matrix face by face.
- Openness: `open_face(i,j,k,f)` excludes faces adjacent to isolated internal
  cavities. Only empty cells connected to the exterior by a six-neighbour
  flood fill receive ocean/air exchange.
- Limitations: face-normal geometry is approximated; a cavity connected to the
  exterior is treated as an open water/air boundary, but no cavity-resolved
  spray or circulation model is included.

### 17.3 Three-equation Stefan interface

For each submerged face at depth `d_f`:

```text
S_B(m) = ρ_w γ_S S_w / (ρ_w γ_S + ρ_ice m)
T_B(m) = Tf(S_B, P_f),   P_f = ρ_w g d_f / 1e4
F(m) = ρ_w c_w γ_T (T_w − T_B) − ρ_ice L_f m
       − (2 k_ice/h_norm) (T_B − T_voxel)
```

- Meaning: salt balance, interface freezing temperature, and heat balance.
- Units: `m` m/s (ice-equivalent melt rate), `γ` m/s, `S` mass fraction at the
  boundary, `P_f` dbar, `F` W/m².
- Closure: `γ_T = K_T u_rel`, `γ_S = K_S u_rel`, `K_T=1.1e-3`,
  `K_S=3.1e-5`; `F(m)` is solved by bisection with `m ≥ 0` (no accretion).
- Implementation: `src/voxel_thermal_solver.f90`; per-face `F(m)`; converged
  `T_B` is fed back as the CN Dirichlet value.
- Limitations: coefficients uncalibrated; no accretion; cavity/spray exchange
  absent; large/low-ΔT under-melt remains.

### 17.4 Free-convection floor

```text
γ_T = max(K_T u_rel, 1e-5)
γ_S = max(K_S u_rel, 1e-6)
```

- Meaning: mixed forced/free convection at low relative flow.
- Units: `γ` m/s, `u_rel` m/s.
- Implementation: `src/voxel_thermal_solver.f90`; defaults
  `VOXEL_GAMMA_FREE_T=1e-5`, `VOXEL_GAMMA_FREE_S=1e-6`.
- Limitations: large/low-ΔT ratios remain below 0.5; the full 190-iceberg
  hindcast was not rerun (Stage 12.7c).

### 17.5 Voxel geometry and drag

```text
F_water = 0.5 ρ_w C_Dw A_sub_proj |u_rel| u_rel
F_wind  = 0.5 ρ_a C_Da A_sail     |v_rel| v_rel
```

- Meaning: water and wind drag using voxel-derived projected submerged area and
  exposed sail area.
- Units: forces N, areas m², velocities m/s.
- Implementation: `src/voxel_iceberg.f90` (`A_sub_proj`, `A_sail`, `GM`) and
  `src/iceberg_dynamics.f90` (gated use).
- Limitations: uniform flow direction; `A_sail` is total exposed surface, not a
  projected sail; no capsize/roll; concave silhouettes approximated.

### 17.6 Wave erosion (Bigg/NEMO)

```text
m_wave = max( (1/12)(T_w + 2) S_s [1 + cos(π c^3)], 0 ) / 86400
```

- Meaning: wave-driven lateral erosion rate.
- Units: `m_wave` m/s, `T_w` °C, `S_s` dimensionless Douglas sea state.
- Closure: `S_s` from significant wave height by Douglas/WMO bins; optional
  Stokes drift added to water drag.
- Implementation: `src/wave_forcing.f90`; gates `ICEBERG_WAVE_EROSION` and
  `ICEBERG_STOKES_DRIFT` default OFF.
- Limitations: no real WAM validation; `Tp`/direction unused; no sea-ice drag
  or tides; length/width recession only.

### 17.7 Reanalysis interpolation and position update

```text
T(x,y,z,t), S, u, v: bilinear in (lat,lon), linear in depth and time
dlat = v·dt/R
dlon = u·dt/(R cosφ)
```

- Meaning: offline/prescribed GLORYS12 ocean forcing and first-order geographic
  iceberg position in reanalysis mode.
- Units: positions rad, velocities m/s, depth m, time s.
- Implementation: `src/reanalysis_reader.f90`, `src/ocean_provider.f90`,
  `src/iceberg.f90`, `src/iceberg_run.f90`.
- Limitations: coarse coastal currents; no two-way coupling; first-order
  position update; grid rotation neglected in relative flow.
