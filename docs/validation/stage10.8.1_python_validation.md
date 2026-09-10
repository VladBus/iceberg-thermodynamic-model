# Stage 10.8.1 — Independent Python Validation Layer

**Дата:** 2026-09-10
**Состояние репозитория:** Stage 10.8.1 commit (complete)
**Статус:** PASS — независимый Python-слой воспроизводит производственную формулировку базального таяния; классификация **B — PASS WITH LIMITATIONS**
**Python suite:** `conda run -n iceberg-thermodynamic-model python python/tests/test_basal_melt_validation.py` — 44 проверки, 0 ошибок, exit 0
**Fortran suite:** all fpm tests PASS (exit 0); strict `-Wall -Wextra` build clean; `git diff --check` clean

---

## 1. Objective

Establish a minimal, transparent and independently executable **Python validation
layer** for the current iceberg basal-melt formulation. The Python code recomputes
the scientific result from the documented equations without calling, importing or
parsing the Fortran implementation. The Fortran reference remains the
production-implemented formulation (independently audited in Stage 10.7); the
Python layer is a second numerical implementation for future analytical
verification, sensitivity analysis, observational validation, plotting, parameter
sweeps and uncertainty analysis.

## 2. Scope

- In scope: EOS-80 freezing point; relative ocean velocity; Reynolds number;
  laminar/turbulent Nusselt selection; `gamma_T`; positive thermal driving
  `DeltaT = max(T(D)-Tf(D),0)`; basal melt rate `m = gamma_T*DeltaT/(rho_ice*L_f)`;
  optional NumPy vectorization and a documented tolerance policy.
- **Explicitly out of scope** (later stages): observational calibration; iceberg-track
  comparison; laboratory fitting; three-equation ice-ocean interface; TEOS-10;
  natural convection; plume parameterization; iceberg orientation; new empirical
  coefficients; drag recalibration; lateral/surface melt; atmospheric/ocean forcing
  changes.

## 3. Scientific equations

Reproduced exactly from the production formulation (no modification):

```
Tf       = (A0 + A1*sqrt(S) - A2*S)*S + BP*P          [degC]
S        = practical salinity [PSU]  (production stores mass fraction * 1000)
P        = rho_w * g * z / 1e4                        [dbar]
U_rel    = sqrt((u_water - u_ice)^2 + (v_water - v_ice)^2)
Re       = U_rel * L_char / nu
Nu       = 0.664 * Re^0.5 * Pr^(1/3)     Re <  Re_crit      (laminar)
Nu       = 0.037 * Re^0.8 * Pr^(1/3)     Re >= Re_crit      (turbulent)
gamma_T  = Nu * k / L_char                               [W/(m^2 K)]
DeltaT   = max(T(D) - Tf(D), 0)                          [degC]
m_basal  = gamma_T * DeltaT / (rho_ice * L_f)            [m/s]
```

Transition condition `Re >= Re_crit` matches the production `if (reynolds .ge.
REYNOLDS_CRITICAL)` — exactly `Re = 5e5` selects the turbulent branch. At
`U_rel = 0` or `L_char = 0` the forced-convection guard returns
`gamma_T = 0` (hence `m = 0`); the production numerical-noise guard
`m < MELT_RATE_MIN -> 0` (`MELT_RATE_MIN = 1.0e-12 m/s`) is reproduced.

Production `L_char = L` (iceberg length in the flow direction); the Python API
takes `length_m` explicitly. No orientation is introduced.

## 4. Constants and provenance

| Constant | Python value | Production source (`src/iceberg_types.f90`) |
|---|---|---|
| `RHO_ICE` | 910.0 kg/m³ | line 34 |
| `RHO_WATER` | 1028.0 kg/m³ | line 35 |
| `LATENT_HEAT` | 334000.0 J/kg | line 39 |
| `GRAVITY` | 9.80665 m/s² | line 48 |
| `EOS_FP_A0` | -0.0575 | line 55 |
| `EOS_FP_A1` | 1.710523e-3 | line 56 |
| `EOS_FP_A2` | 2.154996e-4 | line 57 |
| `EOS_FP_BP` | -7.53e-4 °C/dbar | line 58 |
| `PRANDTL_NUMBER` | 13.8 | line 102 |
| `KINEMATIC_VISCOSITY` | 1.82e-6 m²/s | line 106 |
| `THERMAL_CONDUCTIVITY` | 0.56 W/(m·K) | line 110 |
| `REYNOLDS_CRITICAL` | 5.0e5 | line 119 |
| `MELT_RATE_MIN` | 1.0e-12 m/s | line 135 |

`SCHMIDT_NUMBER` (2400) is documented in production but **not** part of the basal
melt calculation and is therefore **not** used in Python. Literature context:
EOS-80 (UNESCO 1983 / Fofonoff & Millard 1983; Gill 1982 Eq. 3.5.2), flat-plate
correlations (Eckert & Drake 1959), bulk closure (Weeks & Campbell 1973),
iceberg-model comparison (FitzMaurice & Stern 2018) and observed submarine melt
band (Cenedese & Straneo 2023).

## 5. Python implementation location

- `python/validation/__init__.py` — package exports.
- `python/validation/basal_melt.py` — pure functions + optional vectorization.
- `python/tests/test_basal_melt_validation.py` — analytical validation suite.

Core function signatures:

```python
ocean_freezing_point(salinity_psu, depth_m) -> float
relative_velocity(u_water, v_water, u_ice, v_ice) -> float
reynolds_number(u_rel, length_m, nu=1.82e-6) -> float
nusselt_number(reynolds, prandtl=13.8, re_crit=5e5) -> float
ocean_heat_transfer_coefficient(u_rel, length_m, prandtl, nu, k, re_crit) -> float
thermal_driving(ocean_temperature, salinity_psu, depth_m) -> float
basal_melt_rate(ocean_temperature, salinity_psu, depth_m,
                u_water, v_water, u_ice, v_ice, length_m) -> float
basal_melt_rate_vectorized(...)  # NumPy broadcasting, optional
```

No external dependencies for the core path (standard library only); NumPy is
used only by the optional vectorized helper (present in the project conda
environment `iceberg-thermodynamic-model`).

## 6. Independence methodology

The Python layer:
- does **not** invoke the Fortran executable;
- does **not** call Fortran functions through Python or import compiled modules;
- does **not** parse Fortran output;
- recomputes the expected scientific result from the documented equations.

Fortran is the reference implementation being independently checked. Since both
implement the same documented equations, numerical consistency is expected to
float32 precision (production storage class in Fortran is `real`/float32, Python
uses float64). The established test runner is plain Python
(`python python/tests/<file>.py`); test functions are additionally
pytest-collectable (pytest is not installed in the environment, matching the
existing `python/tests` convention).

## 7. Test matrix

44 checks in 15 test groups (A–O):

| Block | Checks | What is verified |
|---|---|---|
| A | 3 | EOS-80: `Tf(40 PSU, 500 dbar) = -2.588567 °C` checkvalue; depth-form pressure consistency; float32 storage-class agreement |
| B | 2 | `T < Tf` → `DeltaT = 0`, `m = 0` (cold ocean, cf. Stage 10.7 case A) |
| C | 2 | `T > Tf` → `DeltaT > 0`, `m > 0` |
| D | 4 | relative velocity: zero if water=ice; pure-x; 3-4-5 vector; subtract-ice vector |
| E | 2 | `Re = U*L/nu` hand value; `U=0` guard |
| F | 3 | laminar branch: Re < 5e5, `Nu = 0.664 Re^0.5 Pr^(1/3)`, `gamma_T = Nu k/L` |
| G | 3 | turbulent branch: Re >= 5e5, `Nu = 0.037 Re^0.8 Pr^(1/3)`, `gamma_T` |
| H | 6 | exact transition: Re<5e5 laminar; Re==5e5 turbulent (>=); Re>5e5 turbulent |
| I | 4 | velocity monotonicity within branch: `gamma ~ U^0.5`, `gamma ~ U^0.8` |
| J | 2 | thermal-driving monotonicity: higher ΔT → higher m; `m/ΔT` const (linearity) |
| K | 2 | length scaling with correct exponents: laminar `L^-0.5`, turbulent `L^-0.2` |
| L | 4 | end-to-end chain against independent literals and the Stage 10.7 float32 value `1.5852e-6 m/s` |
| M | 2 | zero-flow limitation: `U_rel = 0` → `gamma_T = 0`, `m = 0` (no natural convection) |
| N | 1 | numerical-noise guard `m < MELT_RATE_MIN → 0` |
| O | 4 | vectorized (NumPy) parity with the scalar path |

Tolerance policy (documented): branch identities and scaling exponents are
exact in float64 (`1e-12` relative); the end-to-end chain vs Stage 10.7 float32
reference printed to 4 significant figures uses `1e-4` relative (measured
float64-vs-float32 residual ≈ 1.3e-7; reference-digit rounding ≈ 2.8e-5).

## 8. Numerical results

Canonical end-to-end case `S=34.5 PSU, depth=50 m, T=2.0 °C, U_rel=0.1 m/s,
L=100 m`:

```
Tf     = -1.9316 °C
DeltaT =  3.9316 °C
Re     =  5.4945e6  (turbulent)
gamma_T=  122.54 W/(m^2 K)
m      =  1.5852e-6 m/s   (= 0.137 m/day)
```

representative branch values: laminar `gamma(U=0.005,L=100) = 4.6748
W/(m^2 K)`; turbulent `gamma(U=0.5,L=100) = 444.09 W/(m^2 K)`;
transition-jump ratio ≈ 2.90 (inherent piecewise discontinuity, documented in
Stage 10.7). Magnitude case `U=0.5`: `m = 0.496 m/day`, inside the observed band
`0.01–1 m/day` (Cenedese & Straneo 2023; cf. Stage 10.7 case J).

## 9. Cross-validation results

Fortran ↔ Python cross-check uses the established analytical references (no
Fortran execution required, so no real-grid data dependency):

| Quantity | Stage 10.7 float32 reference | Python float64 | relative diff |
|---|---|---|---|
| `Tf(34.5 PSU, 50 m)` | — | -1.9315811 | — |
| `DeltaT` (T=2 °C) | 3.93158 | 3.9315811 | < 1e-6 |
| `m_basal` (U=0.1, L=100) | 1.5852e-6 m/s | 1.58515e-6 m/s | 2.8e-5 |
| `m` (U=0.5, L=100) | 0.4963 m/day | 0.49632 m/day | < 1e-4 |

The 4-significant-figure residual in `m` is the digit-rounding of the printed
Stage 10.7 reference; the raw float32 chain agrees with float64 to ≈ 1.3e-7
(one float32 ulp). No discrepancy was found between the documented equations,
the production Fortran and the Python implementation.

**Checkvalue convention note:** the Stage 10.5 reference `Tf = -2.588567 °C`
is defined at **pressure 500 dbar** (Fofonoff & Millard 1983). The production
depth→pressure conversion `P = rho*g*z/1e4` gives 504.06 dbar at exactly 500 m,
so `Tf(40 PSU, 500 m) = -2.59163 °C` by the depth-form; the checkvalue is
reproduced at the depth that yields exactly 500 dbar (≈ 495.97 m). Stage 10.8.1
A.1 reproduces the checkvalue and A.2 verifies the depth-form polynomial.

## 10. Limitations

- Python uses float64 while production uses float32 — last-ulp differences are
  expected and within the documented tolerance.
- The layer validates mathematical/numerical consistency; it is **not**
  observational validation of the basal-melt parameterization.
- `U_rel = 0` gives zero melt (forced-convection closure); natural convection is
  not represented.
- `L_char = L` is the orientation-averaged approximation; streamwise length is
  not prognosed.
- The flat-plate correlation is a canonical boundary-layer formulation, not a
  geometry-specific iceberg derivation; the three-equation interface is not
  implemented.
- No Fortran execution is attempted in the Python suite; cross-validation uses
  the published Stage 10.7 analytical reference values.

## 11. Production-physics statement

**Stage 10.8.1 does not modify production Fortran physics.** The protected
files `src/iceberg_types.f90`, `src/iceberg_forcing.f90` and
`src/iceberg_thermodynamics.f90` were not modified; no EOS, Re/Nu, heat-transfer,
melt, forcing, dynamics or timestep changes were made. If a discrepancy between
Python and Fortran had been found, it would have been STOPPED and reported
rather than silently changing either formulation.

## References

- Fofonoff, N. P. & Millard, R. C. (1983). UNESCO TPMS 44, §5 (EOS-80 freezing point).
- Gill, A. E. (1982). Atmosphere-Ocean Dynamics, Eq. 3.5.2.
- Eckert, E. R. G. & Drake, R. M. (1959). Analysis of Heat and Mass Transfer (flat-plate correlations).
- Weeks, W. F. & Campbell, W. J. (1973). J. Glaciol. 12, 207-233.
- FitzMaurice, A. & Stern, A. A. (2018). Ocean Modelling 131, 54-69.
- Cenedese, C. & Straneo, F. (2023). iceberg submarine-melt review (observed 0.01-1 m/day).
- Prior stage: `docs/validation/stage10.7_basal_melt_validation.md`.

**Test program:** `python/tests/test_basal_melt_validation.py` — 44 checks, 0 errors.