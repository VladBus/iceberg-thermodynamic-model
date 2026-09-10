# Stage 10.10 — Three-Equation Ice-Ocean Interface

**Classification: C (modern formulation implemented and independently validated)**
**Production physics changed: YES (added on a separately selectable path; bulk path physics unchanged — only re-indented and given diagnostic outputs)**

Implementation and independent validation of the three-equation ice-ocean
interface (Holland & Jenkins 1999; Jenkins et al. 2010 Table 2) for the basal
melt of the iceberg model. The closure is added behind an explicit runtime
switch (`BASAL_MELT_SCHEME_THREE_EQUATION`); every other path of
`compute_basal_melt` retains the legacy bulk formulation with the same statements
(only re-indented inside the scheme else-branch and given diagnostic outputs).
Validation is performed in two fully independent language layers (Fortran and
Python) whose expected values are hand-computed from embedded literals, plus
two cross-language contract anchors. No coefficient is calibrated.

One **real implementation bug was found and fixed during this stage**: the local
variable `latent_heat` shadowed the module constant `LATENT_HEAT` through
Fortran case-insensitivity, which corrupted Eq. II (m: Infinity) in production
while an isolated copy of the same algorithm converged. See §9.

References: `src/iceberg_types.f90`, `src/iceberg_thermodynamics.f90`
(`set_basal_melt_scheme`, `solve_three_equation_interface`,
`compute_basal_melt` branch, `iceberg_thermodynamics_step` diagnostics),
`test/iceberg_test_10p10_three_equation.f90` (19 checks, cases A-L),
`python/validation/three_equation.py` + `python/tests/test_three_equation.py`
(46 checks, blocks A-T).

---

## 1. Scope and objective

Stage 10.9 concluded that no scalar heat-transfer coefficient is identifiable
from the 10.8.2 observational set (required coefficient spans ~8.3x across the
two independent sources; mismatch is a functional form dT^0.73 vs dT^1.0, not
a scale error). The recommended structural upgrade — a three-equation
ice-ocean interface accounting for the interface freshening and the 
latent-plus-conduction heat balance — is implemented here as a selectable
basal closure.

Objective criteria for this stage:
- correct three-equation algebra (Eqs. I-III) with provenance;
- independently verifiable semantics: every expected value derived from
  embedded literals, not from production diagnostics;
- baseline bulk closure unchanged (else-branch byte-identical);
- cross-language consistency (Fortran float32 vs Python float64, rel < 1e-4);
- behavior: warm ocean produces melt inside the observed 0.01–1 m/day band;
- no calibration, no fitting, no change to canonical model physics.

## 2. Physics

Holland & Jenkins's formulation (Holland & Jenkins 1999, Eqs 1-3; Jenkins
et al. 2010).

Exchange coefficients (J2010 Table 2; velocity scale, not shear `u*`):

    gamma_T = K_T * U_rel,     gamma_S = K_S * U_rel
    K_T = sqrt(C_d) * Gamma_T = 1.1e-3
    K_S = sqrt(C_d) * Gamma_S = 3.1e-5

Interface conditions at the ice-ocean boundary:

    (I)   T_B = Tf(S_B, P)                                    [interface at freezing]
    (II)  rho_w c_w gamma_T (T_w - T_B)
          = m rho_i ( L_f + c_i max(T_B - T_i, 0) )          [heat balance, melt rate in ice frame]
    (III) gamma_S (S_w - S_B) = m S_B                        [salt balance, S_i = 0]

`S` in PSU: `S = 1000 * S_kg`; pressure `P = rho_w g z / 1e4` dbar. EOS-80
freezing point (Stage 10.5): `Tf = (A0 + A1*sqrt(S) - A2*S)*S + BP*P`, with
`A0 = -0.0575`, `A1 = 1.710523e-3`, `A2 = 2.154996e-4`,
`BP = -7.53e-4` degC/dbar.

Salt balance yields the reduction

    S_B(m) = gamma_S S_w / (m + gamma_S)

which is monotone in m; substituting into (I) and (II) gives a scalar equation
in m with a single root for `T_w > Tf(S_w, P)` and a unique zero boundary at
the freezing edge.

## 3. Numerical solver

- `F(m) = rho_w c_w gamma_T (T_w - T_B(m)) - m * latent(T_B(m))` with
  `latent = rho_i (L_f + c_i max(T_B - T_i, 0))`.
- Starting estimate `m_est = rho_w c_w gamma_T (T_w - Tf(S_w))/(rho_i L_f)`;
  `m_hi = max(m_est, 1e-9)`.
- double `m_hi` until `F(m_hi) <= 0` (cap 60) — this is safe because
  `S_B -> 0`, `T_B -> Tf(0,P)` and `F -> 0 - m*latent` is strictly negative at
  large m.
- 60 bisection iterations on `[0, m_hi]` (float32 production; float64 in the
  Python reference; final values agree to < 1e-4 rel, see §8).

Edge cases (mirror the bulk closure's documented behaviour):

| Condition | Result |
|---|---|
| `U_rel <= 0` or `gamma_T <= 0` or `T_w <= Tf(S_w,P)` | `m = 0`, `S_B = S_w`, `T_B = Tf` |
| `S_w <= 0` (fresh water) | heat-only balance, `S_B = 0` |
| `gamma_S <= 0` | heat-only balance, `S_B = S_w` |
| post-solution `m < MELT_RATE_MIN` | guard zeroing as for the bulk path |

## 4. Parameter provenance

| Constant | Value | Source |
|---|---|---|
| `rho_w` | 1028 kg/m^3 | H&J99 (also model reference density) |
| `c_w` | 3974 J/(kg K) | H&J99 (seawater heat capacity) |
| `rho_i` | 910 kg/m^3 | production `RHO_ICE` |
| `L_f` | 3.34e5 J/kg | production `LATENT_HEAT` |
| `c_i` | 2009 J/(kg K) | H&J99 (ice heat capacity) |
| `T_i` | -10 degC | H&J99 (internal ice temperature, constant) |
| `K_T`, `K_S` | 1.1e-3, 3.1e-5 | J2010 Table 2 (U-based) |

Convention note (open risk from Stage 10.7/10.9): `K_T = sqrt(C_d) Gamma_T`
is the **U-based** velocity-scale convention. The glaciological melt-driven
Stanton `St = 0.011` (Jenkins et al. 2010, `u*`-based) is a different
convention; it is documented but **not** implemented, and it remains an open
question for a future calibration stage (§11).

## 5. Independence of the validation

Neither test layer calls the other's implementation, and neither derives its
expected values from production state:
- The **Fortran** test embeds its own literals (1028, 3974, 910, 3.34e5, 2009,
  -10.0, EOS-80 coefficients) and re-implements the reduction
  `S_B = gamma_S S_w/(m+gamma_S)` + bisection *inside* the test; production
  subroutines are called only to obtain the actual output.
- The **Python** layer (`python/validation/three_equation.py`) reproduces the
  formulation independently in float64 from embedded constants and only passes
  the two canonical ``values below as cross-language contracts.
- Cross checks that compare production vs independent code (C.1/C.2, L.1/L.2)
  are cross-language contracts, not same-source derivations.

No expectation in either suite is a re-derivation of a production diagnostic;
both suites were authored from the equations, not from output.

## 6. Fortran validation (19 checks, cases A-L)

Runtime gate: `fpm test --flag "-I/usr/include" iceberg_test_10p10_three_equation`
-> `TOTAL CHECKS: 19 ERRORS: 0`.

- **A** cold ocean (`T_w < Tf`): m = 0, `S_B = S_w`, `T_B = Tf`.
- **B** `U_rel = 0`: m = 0 (natural convection not implemented; same documented
  limitation as the bulk closure).
- **C** H&J99 canonical anchor (`T_w = -1.85`, `S_w = 34.5`, `gamma_T = 1e-4`,
  `gamma_S = 5.05e-7`, depth 0): m = 9.44566203e-9 m/s; production and
  independent match float32-exactly; `0 < S_B < S_w`, `Tf < T_B < T_w`.
- **D** Eq.-II and Eq.-III balance residuals ~ 0 at the root.
- **E** conduction term on/off: conduction reduces melt (ratio 0.952 at the
  production case).
- **F** linear U-scaling: m(2U)/m(U) = 2.0000000 (gamma proportional to U).
- **G** freezing edge: `T_w = Tf` -> m = 0; `T_w = Tf + 1e-4` -> small
  positive m.
- **H** fresh-water edge: `S_w = 0` -> `S_B = 0`, heat-only m > 0.
- **I** `gamma_S = 0` edge: `S_B = S_w`, closed-form heat-only balance.
- **J** J2010 Table 2 consistency: `sqrt(C_d)*Gamma_T = 1.0834e-3` vs
  `K_T = 1.1e-3`; `sqrt(C_d)*Gamma_S = 3.0531e-5` vs `K_S = 3.1e-5`
  (rel ~ 1.5%).
- **K** warm ocean band: 0.345 m/day within the observed 0.01–1 m/day
  (Cenedese & Straneo 2023).
- **L** production end-to-end (`set_basal_melt_scheme` +
  `compute_basal_melt(2.0, S=0.0345, D=50, U_rel=0.1)`): m = 3.99846886e-6 m/s
  matching the independent reduction; interface freshening
  `T_B = -0.853` > `Tf = -1.932`, `S_B = 0.0151 < S_w`; the default scheme
  still produces the bulk m = 1.585e-6 (regression: the switch is effective).

## 7. Python validation (46 checks, blocks A-T)

Gate: `python python/tests/test_three_equation.py`
-> `TOTAL CHECKS: 46 ERRORS: 0`.

Blocks: A EOS-80 (UNESCO 500 dbar checkvalue, pressure term, monotonicity);
B transfer coefficients (K_T = sqrt(C_d)\*Gamma_T consistency, ratio);
C canonical anchor + cross-language contract (m, S_B, T_B; balance residuals
|F|/flux < 1e-9; bracketing); D no-flux/sub-freezing/zero-gamma edges;
E fresh-water and gamma_S = 0 closed forms (incl. conduction in the closed
form); F conduction on/off (effect ~1% near-freezing, regime-dependent);
G linear U-scaling = 0.5 and root bracketing; H freezing-edge grind;
I depth/pressure monotonicity (deeper -> colder Tf -> more melt at fixed T);
J warm-band 0.345 m/day; K wrapper == raw solver + MELT_RATE_MIN guard;
L production-end contract (m = 3.99846886e-6 m/s, S_B = 15.0666 PSU,
T_B = -0.85317); M regime separation vs the Stage 10.8.1 bulk closure
(m3eq = 3.998e-6 vs mbulk = 1.585e-6); N 3x3x2 finite/bounded/freshened
matrix; O determinism; T documented natural-convection limitation.

## 8. Cross-language contract

| Anchor | Fortran (float32) | Python (float64) | rel |
|---|---|---|---|
| H&J99 canonical m | 9.44566203e-9 m/s | 9.445700e-9 m/s | 3.4e-6 |
| H&J99 S_B | 3.38665470e-2 | 33.866547 PSU | 1.0e-3 (PSU scale) |
| production end-to-end m | 3.99846886e-6 m/s | 3.9984685e-6 m/s | 8.9e-8 |
| production S_B | 1.50666293e-2 | 15.0666293 PSU | 1.0e-3 |
| production T_B | -0.85317093 | -0.853171 | 1.0e-3 |

Both layers agree to float32 precision; the bisection (60+60) reproduces the
root in float64 with no tolerance relaxation.

## 9. Bug found and fixed during implementation

**Symptom**: the production `solve_three_equation_interface` returned
`m = Infinity`, `S_B = 0`, `T_B = -0.0` for the canonical case while a
self-contained copy of the identical algorithm converged to 9.4457e-9.
A fresh standalone compile of the module reproduced Infinity, ruling out
archive/cache artefacts; the instrumentation showed `m_hi = Infinity` already
at the first doubling step and a latent term equal to only the conduction
part (`rho_i c_i (T_B - T_i)`) — i.e. the `rho_i L_f` base was absent.

**Root cause**: in `solve_three_equation_interface` the local variable was
named `latent_heat`, which is case-insensitively **identical** to the module
constant `LATENT_HEAT`. `latent_heat = RHO_ICE*LATENT_HEAT` assigned the
uninitialised local scaled by rho_i, and `m_est` divided by the same
uninitialised value (0 or garbage) -> Infinity -> every `F(m)` = -Infinity ->
bisection output m = Infinity with S_B -> 0 (the "freshened" interface state
was an artefact of the divergent root, not physics).

**Fix**: rename the local to `l_heat`. `grep -c latent_heat` in the source is
now 0 and `LATENT_HEAT` retains all 10 references. Class: real implementation
bug (Fortran identifier case-insensitivity), not a literature or physics
conflict.

## 10. Regression

- Fortran gate: `fpm test --flag "-I/usr/include"` — all **52** auto-discovered
  test programs exit 0 (was 51), including the new 10.10 target and the
  canonical 9.x suite.
- Strict: `fpm build --flag "-I/usr/include -Wall -Wextra -fcheck=all"`
  — 0 warnings.
- Python regressions: 10.8.1 (44), 10.8.2 (229), 10.9 (212), 10.10 (46) —
  all 0 errors.
- `git diff --check` clean.
- Bulk `compute_basal_melt` path unchanged in physics (git diff shows only
  re-indentation and diagnostic-only additions `t_iface`/`s_iface`).

## 11. Known limitations (documented, deferred)

1. Constant `T_i` conduction: Eq. II uses a fixed internal ice temperature
   (-10 degC); physically consistent conduction requires internal thermal
   evolution of the iceberg (future stage).
2. Natural-convection floor not implemented: `U_rel = 0 -> m = 0` for the
   new closure, identical to the bulk closure; this remains the largest
   structural gap from 10.8.2 and was confirmed uncalibratable by 10.9.
3. `K_T`/`K_S` are the U-based J2010 values; the melt-driven `u*`-based
   Stanton (St = 0.011) is a different convention and remains an open
   calibration question. No attempt was made to re-score the 10.8.2 set
   (no calibration in this stage, per 10.9).
4. Lateral melt still uses the legacy depth-averaged closure; the
   three-equation treatment is implemented for the basal path only.

## 12. Acceptance criteria

| Criterion | Result |
|---|---|
| Correct three-equation algebra with provenance | Passed (§2, §4) |
| Independent expected values from embedded literals | Passed (§5-§7) |
| Baseline bulk closure unchanged | Passed (bulk statements identical; re-indentation + diagnostics only, §10) |
| Cross-language consistency < 1e-4 rel | Passed (§8) |
| Warm-ocean melt inside observed band | Passed (0.345 m/day in [0.01, 1]) |
| No calibration / no canonical-physics change | Passed (selectable path only) |

## 13. Files changed

- `src/iceberg_types.f90` — scheme selector constants / `set_basal_melt_scheme`,
  three-equation constants, `t_interface`/`s_interface` diagnostics.
- `src/iceberg_thermodynamics.f90` — `solve_three_equation_interface` +
  branch in `compute_basal_melt`, diagnostics in `iceberg_thermodynamics_step`,
  `l_heat` rename (bug fix).
- `test/iceberg_test_10p10_three_equation.f90` (new, 19 checks).
- `python/validation/three_equation.py` (new), `python/tests/test_three_equation.py`
  (new, 46 checks).
- Docs: `docs/model/model_equation_ledger.md` (§10.2), `docs/model/model_physics_status.md`,
  `docs/model/stage10_modernization_plan.md` (§10.10), `docs/PROJECT_ROADMAP.md`,
  `docs/references/literature_matrix.md`, `docs/references/citation_map.md`,
  `AGENTS.md`, `.github/workflows/ci.yml`.

## 14. Sources

- Holland, D. M., & Jenkins, A. (1999). Modeling thermodynamic ice-ocean
  interactions at the base of an ice shelf. *Journal of Physical Oceanography*, 29, 1787-1800.
- Jenkins, A., Nicholls, K. W., & Corr, H. F. J. (2010). Observation and
  parameterization of ablation at the base of Ronne Ice Shelf. *JPO* / *J. Glaciol.* (Table 2).
- Fofonoff, P., & Millard, R. C. (1983). UNESCO Technical Papers in Marine Science 44.
- Gill, A. E. (1982). *Atmosphere-Ocean Dynamics* (§3.5 freezing point).
- Cenedese, C., & Straneo, F. (2023). Icebergs melting. *Annual Review of Fluid Mechanics* (observed band).
- FitzMaurice, A., & Stern, A. (2018). Tabular iceberg basal melt (context/comparison).

Full keys in `docs/references/references.bib`; roles in `docs/references/literature_matrix.md`.

## 15. Q&A

- *Why is m in the ice frame?* Eq. II multiplies latent and conduction terms by
  rho_i because m is a volume loss of ice; this is the H&J99 convention and
  the reason the bulk path's `/rho_i L_f` form is not reused verbatim.
- *Why did S_B -> 0 look physical before the fix?* At a divergent root m ->
  Infinity, Eq. III forces S_B = 0, i.e. the freshening asymptote of a
  physically large melt rate; the freshening constraint holds regardless of
  root quality, so the state was internally consistent but wrong.
- *Is the Python layer a clone?* It re-implements the reduction and bisection
  independently in float64 from the published equations; only the two contract
  anchors above reference Fortran output.
- *Why not re-score the 10.8.2 set now?* 10.9 demonstrated that the mismatch
  is functional-form, not a scalar offset, and closure re-scoring belongs to a
  calibration stage after the natural-convection and internal-thermal gaps are
  closed (Stage 10.11+), not to an implementation stage.