# Stage 10.11.3 — Deep Scientific Audit and Sensitivity Analysis of Natural-Convection Basal Melt

**Status:** COMPLETE — Classification B (PASS WITH LIMITATIONS)
**Production physics:** UNCHANGED (`git diff -- src/` is empty)
**Date:** 2026-09-13
**Scope owner:** Stage 10.11.3 (audit only; no new physics)
**Parent stage:** Stage 10.11 (natural-convection closure) + Stage 10.11.2 (audit + Fortran test delivery)

---

## 1. Executive Summary

This audit examined the natural-convection basal-melt closure added in Stage 10.11
(`natural_convection_transfer_coeff` in `src/iceberg_types.f90`;
`solve_three_equation_interface_natural` in `src/iceberg_thermodynamics.f90`),
reconstructed it independently in Python, ran a controlled sensitivity study, and
verified every numeric and citation claim against primary literature.

**Headline result — the zero-flow melt rate is an artifact of the Rayleigh cap.**
For the production anchor (`T_w=2 °C`, `S_w=34.5 PSU`, `L=100 m`, `D=50 m`,
`U_rel=0`), the uncapped double-diffusive Rayleigh number is
`Ra = 5.68 × 10¹⁹`, **nine orders of magnitude above** the hard `Ra_max = 1e10`
cap. Consequently `Nu` is pinned at `0.15·(1e10)^(1/3) = 323.17` and the closure
returns `m = 1.638 × 10⁻⁸ m/s = 1.42 × 10⁻³ m/day`.

The sensitivity study shows that in this capped regime:

- the haline term `β_S·(S_w − S_B)·Le` is **numerically inert** — removing it
  entirely (or setting `Le = 0`) reproduces `m = 1.638 × 10⁻⁸ m/s` *exactly*
  (Table G);
- `β_T` and `β_S` can each be varied by ±1 order of magnitude with **zero change**
  to `m` (Table H);
- `γ_T_nat ∝ 1/L` because the cap fixes `Nu` (Table C), whereas the *uncapped*
  turbulent `Ra^(1/3)` law is `L`-independent;
- the laminar branch and the `Ra = 1e7` transition are **numerically latent** for
  any realistic iceberg (cap always active; `L` for cap = 0.056 m haline-only /
  1.43 m thermal-only) — confirming and quantifying the 10.11.2 finding.

**Physical finding — the haline sign does not describe the real mechanism.**
At a melting ice base the meltwater is cold *and* fresh. The salinity
stratification is **stabilizing** (light fresh water on top of dense saline water),
not destabilizing as the production's `+β_S·ΔS·Le` term implies. Giving the
haline term its physical sign drives `Ra < 0 → Nu = 0 → m = 0`, i.e. the closure
has **no physical branch** that produces finite quiescent melt. The real
quiescent melt is **double-diffusive convection** (destabilizing temperature +
stabilizing salinity), documented in situ/laboratory by Martin & Kauffman (1977),
Keitzl et al. (2016), and Middleton et al. (2021); the production closure does
not reproduce that mechanism.

**Citation finding.** The `0.15·Ra^(1/3)` turbulent coefficient is genuinely from
Lloyd & Moran (1974), **not** Fujii et al. (1973). The cited Fujii et al. (1973)
paper is a *theoretical, laminar, uniform-heat-flux* study whose reported
dependence is `Nu ∝ Ra^(1/5)` — it does not contain either `0.27·Ra^(1/4)` or
`0.15·Ra^(1/3)`. The `0.27·Ra^(1/4)` laminar coefficient is the standard
stable-orientation horizontal-plate value. Churchill's (1977) `n = 3` mixing rule
was derived for a **vertical, laminar, assisting** boundary layer, and its
application here to a horizontal double-diffusive base is an extrapolation.

**Practical finding.** Even taken at face value, `m(U=0) = 1.42 × 10⁻³ m/day`
is **7–700× below** the observed quiescent laboratory/field band of
`0.01–1 m/day` (Stage 10.8.2). It therefore does **not** close the zero-flow gap
that motivated Stage 10.11. The Stage 10.11/ledger claim that the closure is
"consistent with quiescent laboratory observations (0.01–1 m/day)" is
**factually wrong** and is corrected in the documentation updates accompanying
this audit.

**Classification: B (PASS WITH LIMITATIONS).** The implementation is
dimensionally consistent, numerically stable, deterministic, and honestly
documented as an empirical closure. It contains no coding bug. However, it
(a) reduces to an arbitrary cap-determined constant rather than a physical
prediction, (b) mis-attributes its coefficients, and (c) does not reach the
observed quiescent melt magnitude or reproduce the known double-diffusive
mechanism. Production physics is **not** changed; the recommended action is
documentation correction plus a future-physics note.

---

## 2. Scope

**In scope**

1. Full read and independent replication of the production natural-convection
   and three-equation interface code.
2. Dimensional and physical audit of `Ra_eff`, `Nu`, `γ_T_nat`, `γ_S_nat`, and
   the Churchill mixing.
3. Controlled sensitivity analysis over `Ra_max`, `L`, `U_rel`, `ΔT`, `S_w`,
   `β_T`, `β_S`, `Le`, and `n`.
4. Literature verification of every cited coefficient and the physical
   mechanism of quiescent basal melt.
5. Documentation-claim verification, including the Stage 10.11
   "0.01–1 m/day" claim.

**Out of scope**

- Any change to production equations or constants.
- Calibration to observations (prohibited by the stage rules; Stage 10.9 already
  showed no scalar coefficient is identifiable).
- New physics (double-diffusive flux laws, internal ice thermal evolution).
- Re-running the full ocean/iceberg model.

---

## 3. Repository State and Provenance

| Item | Value |
|---|---|
| Branch | `main` (`main...origin/main`, no divergence at audit start) |
| Audit-start HEAD | `a5fc4c5` (`chore: rename t_ice to t_ice_in, localize comments, verify citations, ignore .omo/`) |
| Preceding stages | `6a0014e` (10.11), `dda51b5` (10.11.1), `dcb9f3c` (10.11.2) |
| Working tree | clean except new `python/analysis/stage10_11_3_natural_convection_sensitivity.py` |
| Production source diff | **empty** (no `src/` edits in this stage) |
| Test baseline | all Fortran and Python suites pass (Section 26) |

The audit follows the repo workflow in `AGENTS.md`: read the sources, the wiki,
git status/log, and all related documents before acting; use the existing TODO
as the project plan; change no physics equations.

---

## 4. Production Code Under Audit

- `src/iceberg_types.f90`
  - constants: `RHO_WATER=1028`, `GRAVITY=9.80665`,
    `KINEMATIC_VISCOSITY=1.82e-6`, `THERMAL_CONDUCTIVITY=0.56`,
    `CP_SEAWATER=3974`, `THERMAL_EXPANSION_COEFF=3.0e-5`,
    `HALINE_CONTRACTION_COEFF=7.8e-4`, `LEWIS_NUMBER=100.0`,
    `RAYLEIGH_MAX=1.0e10`, `RAYLEIGH_TRANSITION=1.0e7`,
    `NU_LAMINAR_COEFF=0.27`, `NU_LAMINAR_EXP=0.25`,
    `NU_TURBULENT_COEFF=0.15`, `NU_TURBULENT_EXP=1/3`,
    `THREE_EQ_KT=1.1e-3`, `THREE_EQ_KS=3.1e-5`;
  - `natural_convection_transfer_coeff(...)` — builds `Ra_eff`, applies the cap,
    selects the laminar/turbulent branch, returns `γ_T_nat`, `γ_S_nat`.
- `src/iceberg_thermodynamics.f90`
  - `solve_three_equation_interface_natural(...)` — the natural-convection
    variant of the three-equation solver; bisection with a doubling upper-bound
    phase, the Stage 10.10.1 density-weighted salt balance, and the Churchill
    mixing;
  - `compute_basal_melt(...)` passes `state%L` as the characteristic length and
    dispatches on the scheme selector.
- Scheme selector `BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL`
  (`set_basal_melt_scheme`); the bulk baseline path is untouched.

The independent Python replica is
`python/validation/three_equation_natural.py`; the audit sensitivity driver is
`python/analysis/stage10_11_3_natural_convection_sensitivity.py`.

---

## 5. Governing Equations as Implemented

Forced (U-based, Jenkins et al. 2010 Table 2 convention):

```
γ_T_forced = K_T · U_rel            K_T = 1.1e-3
γ_S_forced = K_S · U_rel            K_S = 3.1e-5
```

Double-diffusive Rayleigh number:

```
Ra_eff = g · L³ / (ν · α) · [ β_T·(T_w − T_B) + β_S·(S_w − S_B)·Le ]
α = k / (ρ_w · c_w)
```

Nusselt number (branch on `Ra` after capping):

```
Ra <  Ra_trans :  Nu = 0.27 · Ra^0.25
Ra >= Ra_trans :  Nu = 0.15 · Ra^(1/3)
```

Natural transfer:

```
γ_T_nat = Nu · k / (L · ρ_w · c_w)
γ_S_nat = γ_T_nat · (K_S / K_T)
```

Churchill (1977) mixing, exponent `n = 3`:

```
γ_T_eff = (γ_T_forced³ + γ_T_nat³)^(1/3)
γ_S_eff = (γ_S_forced³ + γ_S_nat³)^(1/3)
```

The effective coefficients replace the forced ones in the three-equation system
(Eqs. I–III), whose salt balance retains the Stage 10.10.1 density weighting
`ρ_w γ_S (S_w − S_B) = ρ_i m S_B`.

---

## 6. Dimensional Analysis

| Quantity | Expression | Dimension | Verdict |
|---|---|---|---|
| `β_T·ΔT` | `1/K · K` | dimensionless | ✓ |
| `β_S·ΔS·Le` | `1/PSU · PSU` | dimensionless | ✓ |
| bracket | `[β_TΔT + β_SΔS·Le]` | dimensionless | ✓ |
| `Ra_eff` | `m/s² · m³ / (m²/s · m²/s)` | dimensionless | ✓ |
| `Nu` | `C·Ra^p` | dimensionless | ✓ |
| `γ_T_nat` | `W/(m·K) / (m · kg/m³ · J/(kg·K))` | m/s | ✓ |
| `γ_S_nat` | `γ_T_nat·(K_S/K_T)` | m/s | ✓ |
| Churchill root | sum of like dimensions | m/s | ✓ |

All algebraic combinations are dimensionally consistent. Note that combining a
`U`-based coefficient (`γ_forced`, no `L`) with an `L`-based coefficient
(`γ_nat ∝ 1/L`) via `n = 3` is dimensionally *homogeneous* (both are m/s) but
not a Churchill derivation for this geometry (Section 14).

---

## 7. Rayleigh-Number Construction

Measured components at the anchor (Python replica, float64):

| Component | Value |
|---|---|
| `α = k/(ρ_w c_w)` | `1.3708 × 10⁻⁷ m²/s` |
| `g/(ν·α)` | `3.9308 × 10¹³ 1/(m³·K)` |
| `ΔT = T_w − T_B` | `2.9016 K` |
| `ΔS = S_w − S_B` | `18.5386 PSU` |
| `β_T·ΔT` | `8.7047 × 10⁻⁵` |
| `β_S·ΔS·Le` | `1.4460` |
| haline / thermal | `1.66 × 10⁴` |
| `Ra` uncapped | `5.6843 × 10¹⁹` |
| `Ra` capped | `1.0 × 10¹⁰` |
| `Nu` | `323.1652` |

`Ra_eff` is a linear superposition of a thermal and a haline contribution
(verified by Python check B.9). Because the haline term carries `Le = 100` and
dominates by ~4 orders of magnitude, the uncapped `Ra` is essentially the haline
term alone. In production the value never matters, because the cap always binds.

---

## 8. Haline-Term Sign — Physical Audit

Meltwater at the interface is **cold and fresh**: `T_B = −0.90 °C`,
`S_B = 15.96 PSU`. Relative to the ambient (`2 °C`, `34.5 PSU`):

- thermal: cold water above warm water → gravitationally **destabilizing**
  (`β_T·ΔT > 0` contributes to unstable stratification);
- haline: fresh (light) water above saline (dense) water → gravitationally
  **stabilizing** (`β_S·ΔS > 0` should *oppose* convection).

The net density anomaly of the meltwater layer is dominated by salinity:
`β_S·ΔS = 1.446 × 10⁻²` vs `β_T·ΔT = 8.7 × 10⁻⁵`, i.e. the layer is ~1.4 %
**lighter** than the ambient. The overall column is therefore stably
stratified, and the convective motion that does occur is **double-diffusive**
(heat diffuses ~100× faster than salt; the unstable temperature field drives
flux through a stabilizing salinity field).

The production formulation adds the haline term with a **positive** sign and
multiplies it by `Le = 100`, so it treats the stabilizing salt field as the
dominant destabilizing driver. Stage 10.11.2 §B.1 acknowledged the positive sign
was retained to avoid a zero-`Ra` startup artifact rather than from physical
derivation; this audit quantifies the consequence:

- with `+β_S·ΔS·Le`, `Ra = 5.68 × 10¹⁹` (all from the haline term);
- with `Le = 0` (thermal only), `Ra = 3.42 × 10¹⁵` — **still above the cap**, so
  `m` is unchanged;
- with the physical minus sign, `Ra = −1.06 × 10²⁰ < 0`, the guard returns
  `Nu = 0`, and `m = 0`.

So the haline machinery changes nothing in production, and the physically
motivated sign removes the finite zero-flow melt entirely. Neither branch
represents the real double-diffusive mechanism.

---

## 9. Lewis Number

`Le = 100` is the ratio of thermal to haline molecular diffusivity. For seawater
`κ_T ≈ 1.4 × 10⁻⁷ m²/s` and `D_S ≈ 1.1 × 10⁻⁹ m²/s`, giving `Le ≈ 100–130`, so
the **value** is defensible. The defect is not the magnitude of `Le` but its
role: it is used to *amplify a stabilizing contribution as if destabilizing*.
In a double-diffusive parameterization, the diffusivity ratio enters through the
density ratio `R_ρ` and the flux laws, not as a multiplier on a summed `Ra`.

---

## 10. Characteristic Length

Production passes `state%L` (iceberg length) as the plate scale. The standard
horizontal-plate correlations (Lloyd & Moran 1974) use the Goldstein–Sparrow–Jones
length `L* = A/p` (area / perimeter). For an iceberg footprint `L × W`, this is
`L* = L·W/(2(L+W))`; e.g. `L=100 m, W=40 m → L* ≈ 14.3 m`, not 100 m. Using `L`
inflates `Ra` by `(L/L*)³ ≈ 340×` (pre-cap) — again irrelevant under the cap,
but it would matter if the cap were ever inactive. The `1/3`-power turbulent law
makes `γ` independent of the characteristic length (Section 17 and Kozanoglu &
Rubio 2014); the observed `γ ∝ 1/L` in production is a **cap artifact**, not a
property of the correlation.

The Gayen et al. (2016) "cell scale" attribution was removed in Stage 10.11.2
correctly; the `L = state%L` choice is internally consistent with the Fujii-plate
description but differs from the correlation's own scale definition.

---

## 11. Nusselt Correlation Provenance

| Coefficient | Attributed in code/docs to | Actual source (verified) | Notes |
|---|---|---|---|
| `0.15·Ra^(1/3)` (turbulent) | Fujii et al. 1973 | **Lloyd & Moran 1974**, JHT 96(4):443–447, DOI 10.1115/1.3450224 | Electrochemical, Sc≈2200, `RaL*` 8e6–1.6e9, transition ≈8e6 |
| `0.27·Ra^(1/4)` (laminar) | Fujii et al. 1973 | Standard stable-orientation horizontal-plate value (Incropera-style tables) | Applies to heated-plate-down / cooled-plate-up |
| `Nu ∝ Ra^(1/5)` | — | **Fujii, Honda & Morioka 1973**, IJHMT 16(3):611–627 | Theoretical, uniform **heat flux**, laminar, downward-facing |

Fujii et al. (1973) does **not** contain either constant used in production. The
citation is therefore a mis-attribution for the specific pair
`{0.27·Ra^(1/4), 0.15·Ra^(1/3)}`. Because the laminar branch is latent, the
operative coefficient is `0.15·Ra^(1/3)`, whose correct attribution is Lloyd &
Moran (1974).

---

## 12. Laminar Branch and Transition

For `Ra ∈ [1e5, 1e10]` the correlation is `Nu = 0.27·Ra^(1/4)`; for
`Ra ≥ 1e7` it switches to `Nu = 0.15·Ra^(1/3)`. The two forms are **not
continuous** at `Ra = 1e7`:

```
0.27·(1e7)^(1/4) = 15.183
0.15·(1e7)^(1/3) = 32.317      ratio = 2.128
```

a 113 % discontinuity. Production never sees it because `Ra` is capped at `1e10`
and the cap is always active (`L` for cap: 0.056 m haline-only, 1.43 m
thermal-only), so the laminar branch and the transition are **latent**. This
confirms and quantifies the Stage 10.11.2 finding that only the turbulent branch
fires in production.

Because the iceberg base is a cold surface facing warm fluid, the physically
expected unstable-orientation laminar coefficient would be `0.54` (not the
stable-orientation `0.27`); this is moot in production but should be noted if the
cap is ever removed or applied to small/weakly-stratified cases.

---

## 13. Rayleigh Cap

`Ra_max = 1e10` is the single most consequential constant. The uncapped anchor
`Ra = 5.68 × 10¹⁹` exceeds it by 9.8 decades. The cap therefore *defines* the
result: `Nu = 0.15·(1e10)^(1/3) = 323.165`, `γ_T_nat = 4.4299 × 10⁻⁷ m/s`,
`m = 1.638 × 10⁻⁸ m/s`. Varying the cap over `1e7…∞` moves `m` over
`1.4 × 10⁻⁴ … 2.53 m/day` (Section 16) — a range of four orders of magnitude,
with the observed quiescent band reached only for caps ≳ `1e13`.

The cap is also at/above the upper validity of the Lloyd & Moran turbulent
correlation (`1.6 × 10⁹`); `Nu = 323` is ~1.8× beyond the largest
correlation-validated value (`Nu ≈ 175` at `Ra = 1.6 × 10⁹`). So the closure
operates beyond the correlation's own range even after capping.

---

## 14. Churchill Mixing (`n = 3`)

Churchill (1977) derived `Y³ = Y₁³ + Y₂³` as the best combination for **laminar,
assisting** mixed convection on a **vertical** plate (a boundary-layer-theory
result). Production applies the same `n = 3` to a horizontal double-diffusive
base and uses it separately for heat and salt. Numerically, at `U_rel = 0.1` the
natural term contributes only `2.18 × 10⁻⁸` relative (`2.2 × 10⁻⁶ %`), so the
exponent choice is irrelevant there; the exponent matters only in the narrow
window near the crossover `U* ≈ 4.0 × 10⁻⁴ m/s` at `L = 100 m` (Section 23). The
`n = 3` choice is a defensible literature-based default, but it is an
extrapolation across geometry and flow regime.

---

## 15. Zero-Flow Limit

At `U_rel = 0`, `γ_forced = 0` and `γ_eff = γ_nat`. The closure returns:

- `γ_T_nat = 4.4299 × 10⁻⁷ m/s` (capped regime),
- interface `T_B = −0.9016 °C`, `S_B = 15.961 PSU`,
- `m = 1.638 × 10⁻⁸ m/s = 1.415 × 10⁻³ m/day`.

This is finite and stable (no NaN/zero), which was the stated goal of Stage
10.11. However, it is ~7–700× below the observed quiescent band
`0.01–1 m/day` (Stage 10.8.2), and it is the same value whether or not the
haline term is present (Table G). It is best described as a *cap-determined
floor*, not a physical prediction.

---

## 16. Sensitivity — Rayleigh Cap (`Ra_max` sweep)

Anchor `T_w=2 °C`, `S_w=34.5 PSU`, `L=100 m`, `D=50 m`, `U_rel=0`:

| `Ra_max` | capped | `Nu` | `γ_T_nat` [m/s] | `m` [m/s] | `m` [m/day] |
|---|---|---|---|---|---|
| 1e7 | Y | 32.32 | 4.430e-8 | 1.638e-9 | 0.000142 |
| 1e8 | Y | 69.62 | 9.544e-8 | 3.529e-9 | 0.000305 |
| 5e8 | Y | 119.06 | 1.632e-7 | 6.034e-9 | 0.000521 |
| 1e9 | Y | 150.00 | 2.056e-7 | 7.603e-9 | 0.000657 |
| **1e10 (prod)** | **Y** | **323.17** | **4.430e-7** | **1.638e-8** | **0.001415** |
| 1e11 | Y | 696.24 | 9.544e-7 | 3.529e-8 | 0.003049 |
| 1e12 | Y | 1500.00 | 2.056e-6 | 7.603e-8 | 0.006569 |
| 1e13 | Y | 3231.65 | 4.430e-6 | 1.638e-7 | 0.014151 |
| ∞ (no cap) | N | 576745.63 | 7.906e-4 | 2.923e-5 | 2.525749 |

The cap multiplier on `γ` is **1784.7×**. The observed quiescent band is only
reached at `Ra_max ≳ 1e13` or uncapped; the production cap sits far below it.

---

## 17. Sensitivity — Iceberg Length

Cap active throughout; `γ_T_nat·L = 4.430 × 10⁻⁵` is constant, i.e. `γ ∝ 1/L`:

| `L` [m] | `Ra` uncapped | `Nu` | `γ_T_nat` [m/s] | `m` [m/s] | `m` [m/day] |
|---|---|---|---|---|---|
| 10 | 5.684e16 | 323.17 | 4.430e-6 | 1.638e-7 | 0.014151 |
| 20 | 4.547e17 | 323.17 | 2.215e-6 | 8.190e-8 | 0.007077 |
| 40 | 3.638e18 | 323.17 | 1.107e-6 | 4.095e-8 | 0.003538 |
| 50 | 7.105e18 | 323.17 | 8.860e-7 | 3.276e-8 | 0.002830 |
| 100 | 5.684e19 | 323.17 | 4.430e-7 | 1.638e-8 | 0.001415 |
| 200 | 4.547e20 | 323.17 | 2.215e-7 | 8.190e-9 | 0.000708 |
| 400 | 3.638e21 | 323.17 | 1.107e-7 | 4.095e-9 | 0.000354 |

Under the *uncapped* turbulent law, `Nu ∝ L` and `γ ∝ 1/L` would cancel,
making `γ` length-independent; the explicit `1/L` scaling here is entirely a cap
artifact. This is a physically important caveat: production's "small bergs melt
faster at rest" behaviour is not a correlation property.

---

## 18. Sensitivity — Relative Velocity

Natural contributes a relative enhancement
`γ_eff/γ_forced − 1`:

| `U_rel` [m/s] | `γ_forced` | `γ_nat` | `γ_eff` | rel. excess | `m` [m/day] |
|---|---|---|---|---|---|
| 0 | 0 | 4.430e-7 | 4.430e-7 | — | 0.001415 |
| 1e-4 | 1.100e-7 | 4.430e-7 | 4.452e-7 | 3.05 | 0.001423 |
| 4e-4 | 4.400e-7 | 4.430e-7 | 5.563e-7 | 0.264 | 0.001778 |
| 1e-3 | 1.100e-6 | 4.430e-7 | 1.123e-6 | 0.0213 | 0.003591 |
| 1e-2 | 1.100e-5 | 4.430e-7 | 1.100e-5 | 2.18e-5 | 0.035143 |
| 1e-1 | 1.100e-4 | 4.430e-7 | 1.100e-4 | 2.18e-8 | 0.351420 |
| 1 | 1.100e-3 | 4.430e-7 | 1.100e-3 | 2.18e-11 | 3.51424 |

The natural branch matters only for `U_rel ≲ 1e-3 m/s`; above that, forced
convection dominates geometrically. This is consistent with Stage 10.11.2's
correction of the erroneous "~0.1 % at `U_rel = 0.1`" claim.

---

## 19. Sensitivity — Thermal Driving (`ΔT`)

Fixed `S_w=34.5 PSU`, `L=100 m`, `D=50 m`, `U_rel=0`:

| `T_w` [°C] | `ΔT` [K] | `γ_T_nat` [m/s] | `m` [m/s] | `m` [m/day] | `m/ΔT` [m/s/K] |
|---|---|---|---|---|---|
| −1.432 | 0.5 | 4.430e-7 | 1.662e-9 | 0.000144 | 3.324e-9 |
| −0.932 | 1.0 | 4.430e-7 | 3.478e-9 | 0.000300 | 3.478e-9 |
| 0.068 | 2.0 | 4.430e-7 | 7.509e-9 | 0.000649 | 3.754e-9 |
| 1.068 | 3.0 | 4.430e-7 | 1.196e-8 | 0.001033 | 3.987e-9 |
| 2.068 | 4.0 | 4.430e-7 | 1.671e-8 | 0.001444 | 4.178e-9 |

`γ_T_nat` is **constant** across `ΔT` (cap pins `Nu`); `m` responds through the
three-equation balance, nearly linearly in `ΔT` with a weak curvature from the
`Tf(S_B, P)` dependence of the interface state.

---

## 20. Sensitivity — Salinity

Fixed `T_w=2 °C`, `L=100 m`, `D=50 m`, `U_rel=0`:

| `S_w` [PSU] | `Tf` [°C] | `S_B` [PSU] | `γ_T_nat` [m/s] | `m` [m/s] | `m` [m/day] |
|---|---|---|---|---|---|
| 30.0 | −1.676 | 14.141 | 4.430e-7 | 1.582e-8 | 0.001367 |
| 32.0 | −1.789 | 14.958 | 4.430e-7 | 1.607e-8 | 0.001388 |
| 33.0 | −1.846 | 15.361 | 4.430e-7 | 1.619e-8 | 0.001399 |
| 34.0 | −1.903 | 15.762 | 4.430e-7 | 1.632e-8 | 0.001410 |
| 34.5 | −1.932 | 15.961 | 4.430e-7 | 1.638e-8 | 0.001415 |
| 35.0 | −1.960 | 16.160 | 4.430e-7 | 1.644e-8 | 0.001420 |

`m` varies by only ~4 % across `S_w = 30…35 PSU`, again because `γ` is pinned by
the cap and only the interface state shifts. This is strong evidence that the
closure does not encode a salinity-dependent convective response.

---

## 21. Sensitivity — Haline/Lewis Construction (decisive)

| Variant | `Ra` uncapped | `Nu` | `γ_T_nat` [m/s] | `m` [m/s] | `m` [m/day] |
|---|---|---|---|---|---|
| production `+β_SΔS·Le`, `Le=100` | 5.684e19 | 323.17 | 4.430e-7 | 1.638e-8 | 0.001415 |
| thermal only, `Le=0` | 3.422e15 | 323.17 | 4.430e-7 | 1.638e-8 | 0.001415 |
| haline no-`Le`, `Le=1` | 5.718e17 | 323.17 | 4.430e-7 | 1.638e-8 | 0.001415 |
| **physical (stabilizing)** `−β_SΔS·Le` | −1.058e20 | 0.0 | 0.0 | ≈0 (1.0e-26) | 0.0 |

The first three rows are **identical**: under the cap the haline term — including
its `Le` amplification — contributes nothing. The fourth row shows that the
physically motivated stabilizing sign **eliminates** the zero-flow melt. The
closure therefore has no configuration that both (a) has a defensible haline
sign and (b) yields the finite quiescent melt it was added to provide.

---

## 22. Sensitivity — Expansion Coefficients and Churchill Exponent

`β_T`, `β_S` varied ±1 order of magnitude (9 combinations): `Nu`, `γ_T_nat`, and
`m` are **bit-identical** in every case (`γ = 4.430e-7 m/s`, `m = 1.638e-8 m/s`).
The closure carries no information about the fluid's buoyancy coefficients in
the capped regime.

Churchill exponent at `U_rel = 0.1 m/s`:

| `n` | `γ_eff` [m/s] | rel. excess | `m` [m/day] |
|---|---|---|---|
| 1 | 1.104e-4 | 4.03e-3 | 0.35284 |
| 2 | 1.100e-4 | 8.11e-6 | 0.35143 |
| 3 (prod) | 1.100e-4 | 2.18e-8 | 0.35142 |
| 4 | 1.100e-4 | 6.58e-11 | 0.35142 |
| 5 | 1.100e-4 | 2.11e-13 | 0.35142 |

For `n ≥ 2` the natural contribution is negligible at this speed.

---

## 23. Crossover Velocity

`U* = γ_T_nat / K_T` — below `U*` the natural branch exceeds the forced branch:

| `L` [m] | `γ_T_nat` [m/s] | `U*` [m/s] |
|---|---|---|
| 10 | 4.430e-6 | 4.03e-3 |
| 20 | 2.215e-6 | 2.01e-3 |
| 40 | 1.107e-6 | 1.01e-3 |
| 100 | 4.430e-7 | 4.03e-4 |
| 200 | 2.215e-7 | 2.01e-4 |
| 400 | 1.107e-7 | 1.01e-4 |

`U* ∝ 1/L` (cap artifact). Natural convection is numerically relevant only in
the top decade of this range; typical ocean `U_rel ≳ 0.01 m/s` leaves the forced
branch dominant and the natural machinery invisible.

---

## 24. Comparison with Observations (Stage 10.8.2)

Stage 10.8.2 established a quiescent observational band of `0.01–1 m/day`
(quiescent lab/field anchors; natural-convection gap of 5.7–7.3 orders in the
then-current closure). Against that band:

- production `m(U=0) = 1.42 × 10⁻³ m/day` is **~7× below** the lower edge
  (`0.01`) and up to **~700× below** the upper edge (`1`);
- the value is reached only by the cap; and
- setting the haline term to its physical sign removes it entirely.

So Stage 10.11 did **not** close the zero-flow gap. The Stage 10.11 statement
that the closure "provides finite melt rates consistent with quiescent
laboratory observations (0.01–1 m/day range)" is **false** and must be corrected.
The correct statement is: it provides a *finite, cap-determined low-flow floor
that remains 7–700× below the observed quiescent band*.

---

## 25. Literature Evidence on the Real Mechanism

- **Martin & Kauffman (1977)** — *An Experimental and Theoretical Study of the
  Turbulent and Laminar Convection Generated under a Horizontal Ice Sheet
  Floating on Warm Salty Water*, J. Phys. Oceanogr. **7**(2), 272–283,
  DOI `10.1175/1520-0485(1977)007<0272:AEATSO>2.0.CO;2` (verified). This is the
  closest primary analogue to the iceberg-base geometry: a horizontal ice sheet
  melting into warm salty water develops a conductive sublayer, an unstable
  convective layer (part double-diffusive, part pure thermal), and a deep
  thermal-convection region; melt runs ~2× the purely diffusive prediction.
- **Keitzl, Mellado & Notz (2016)** — *Impact of Thermally Driven Turbulence on
  the Bottom Melting of Ice*, J. Phys. Oceanogr. **46**(4), 1171–1187,
  DOI `10.1175/JPO-D-15-0126.1` (verified). DNS/lab: for warm-water
  temperatures below ~4–8 °C the melt is **diffusion-limited**, with a stable
  meltwater layer shielding the interface; turbulent enhancement is only
  ~2.5–3.1× over conduction, and the melt law passes through regimes
  `m ∝ ΔT` (diffusive), `m ∝ ΔT^(4/3)`, then `m ∝ ΔT^(5/3)`.
- **Middleton, Vreugdenhil, Holland & Taylor (2021)** — *Numerical Simulations
  of Melt-Driven Double-Diffusive Fluxes in a Turbulent Boundary Layer beneath
  an Ice Shelf*, J. Phys. Oceanogr. **51**, 403–418,
  DOI `10.1175/JPO-D-20-0114.1` (verified). Confirms that melting supplies a
  **stabilizing salinity profile and a destabilizing temperature profile** —
  the diffusive-convection regime — so the salt field damps rather than drives
  the flux in a naive summed-`Ra` sense.
- **Lloyd & Moran (1974)** — *Natural Convection Adjacent to Horizontal Surface
  of Various Planforms*, J. Heat Transfer **96**(4), 443–447,
  DOI `10.1115/1.3450224` (verified). Origin of `Sh = 0.15·Ra^(1/3)`
  (`8e6–1.6e9`, `L* = A/p`); the source production's citation should point to.
- **Fujii, Honda & Morioka (1973)** — IJHMT **16**(3), 611–627,
  DOI `10.1016/0017-9310(73)90227-5` (verified). Theoretical, laminar,
  uniform-heat-flux downward-facing plate; `Nu ∝ Ra^(1/5)`. Not the source of the
  production constants.

The physical quiescent melt at Arctic `ΔT ≈ 2–4 °C` is therefore a
double-diffusive, diffusion-limited process of order `0.01–0.1 m/day` — not a
turbulent Rayleigh–Bénard state at `Ra = 10¹⁹` and not a summed-`Ra` law.

---

## 26. Component Confidence Table

| Component | Confidence | Basis |
|---|---|---|
| Dimensional consistency of `Ra_eff`, `Nu`, `γ` | **High** | algebraic audit, Python replication |
| Numerical stability / no NaN near `U=0` | **High** | Fortran + Python edge tests |
| Determinism | **High** | repeated-run checks |
| Three-equation coupling (Eqs. I–III, density-weighted salt) | **High** | Stage 10.10.1 independent validation |
| Forced-convection coefficients `K_T`, `K_S` | **Medium** | J2010 U-based convention; Stanton convention open (10.9) |
| `Ra` construction (linear superposition) | **Medium** | structurally correct but physically oversimplified for double diffusion |
| Haline sign in `Ra_eff` | **Low** | opposite to the physical stabilizing role; acknowledged as artifact-avoiding |
| `Le = 100` magnitude | **Medium** | correct order for seawater; wrong role in the formula |
| Characteristic length `L = state%L` | **Low** | differs from correlation scale `L* = A/p` |
| `0.15·Ra^(1/3)` turbulent coefficient | **Medium** | real (Lloyd & Moran 1974) but applied outside its range with wrong attribution |
| `0.27·Ra^(1/4)` laminar coefficient | **Low** | stable-orientation value; latent in production; wrong orientation if activated |
| Transition `Ra = 1e7` | **Low** | 113 % discontinuity; latent |
| Rayleigh cap `Ra_max = 1e10` | **Low (as physics)** | arbitrary; defines the production result |
| Churchill `n = 3` | **Low–Medium** | literature-based but for vertical laminar assisting flow |
| Zero-flow melt magnitude | **Low** | cap artifact; 7–700× below observed band |
| Physical mechanism (double-diffusive) | **Low (not implemented)** | production does not represent it |
| Documentation claims | **Low** | "0.01–1 m/day" claim false; attribution wrong |

---

## 27. Answers to the Audit Questions (Q1–Q10)

**Q1 — Are the equations dimensionally consistent?**
Yes. Every combination (`Ra_eff`, `Nu`, `γ_T_nat`, `γ_S_nat`, Churchill root)
is dimensionally homogeneous (Section 6).

**Q2 — Is the correlation geometry/orientation physically appropriate, and is
the citation correct?**
The correlation family is for horizontal plates, which matches the basal
geometry; the citation is **not** correct. Fujii et al. (1973) is a theoretical
laminar uniform-heat-flux study (`Nu ∝ Ra^(1/5)`) and does not provide either
production constant. The `0.15·Ra^(1/3)` form is Lloyd & Moran (1974); the
`0.27·Ra^(1/4)` laminar value is the stable-orientation coefficient, whereas the
ice base is an unstable-orientation (cold surface facing warm fluid) geometry.
Separately, the characteristic length (`L` vs `L* = A/p`) differs from the
source correlation.

**Q3 — Is the haline term sign physically justified?**
No. Meltwater is fresh and therefore gravitationally stabilizing; the production
`+β_S·ΔS·Le` treats it as the dominant destabilizing driver. The physically
motivated minus sign drives `Ra < 0 → Nu = 0 → m = 0`. Neither branch represents
double-diffusive convection.

**Q4 — Is `Le = 100` defensible?**
The value is (seawater `Le ≈ 100–130`), but its use — amplifying a stabilizing
term as if destabilizing — is not.

**Q5 — Is Churchill's `n = 3` applicable here?**
It is a literature-based default, not a derivation for this configuration; it was
derived for vertical, laminar, assisting flow. It is numerically irrelevant for
`U_rel ≳ 1e-3 m/s` and only matters in a narrow near-crossover window.

**Q6 — What does the Rayleigh cap actually do?**
It *defines* the result. Because `Ra_uncapped = 5.68 × 10¹⁹ ≫ 1e10`, `Nu` is
pinned at 323.17, the closure becomes insensitive to `β_T`, `β_S`, `ΔT`, `ΔS`,
and `Le`, and the laminar branch/transition are latent. The cap is an arbitrary
empirical value that sits above the correlation's own validity range.

**Q7 — Does the closure close the Stage 10.8.2 zero-flow gap?**
No. `m(U=0) = 1.42 × 10⁻³ m/day` is 7–700× below the observed `0.01–1 m/day`
band, and it vanishes under the physical haline sign. The motivating gap remains.

**Q8 — What is the sensitivity of `m(U=0)` to each input?**
Cap: `m ∝ Ra_max^(1/3)` (four decades across `1e7…∞`). `L`: `m ∝ 1/L` (cap
artifact). `ΔT`: near-linear. `S_w`: ~4 % over `30–35 PSU`. `β_T`, `β_S`, `Le`:
zero. `U_rel`: forced branch dominates above `~1e-3 m/s`.

**Q9 — Does the literature support the specific correlation/closure?**
Partially. The `0.15·Ra^(1/3)` turbulent correlation exists (Lloyd & Moran 1974),
but the environment at a melting ice base is not a turbulent Rayleigh–Bénard
state: Martin & Kauffman (1977), Keitzl et al. (2016), and Middleton et al.
(2021) show a double-diffusive, diffusion-limited regime with only ~2–3×
convective enhancement. The production closure does not represent that physics.

**Q10 — Should production physics be changed now?**
**No — formulation should remain unchanged pending future validation**, with
mandatory documentation corrections. The issues identified are documentable
limitations of an explicitly empirical closure, not a coding defect; the stage
rules forbid silent physics changes, and Stage 10.9 already showed no scalar
coefficient is identifiable. The required follow-up is a documentation
correction (false `0.01–1 m/day` claim, coefficient attribution, cap-dominance,
haline sign) and a future-physics proposal for a double-diffusive /
diffusion-limited low-flow parameterization.

---

## 28. Classification

**Classification: B — PASS WITH LIMITATIONS.**

Justification:

- The implementation is dimensionally consistent, numerically stable,
  deterministic, and regression-clean (all tests pass).
- No coding bug was found; production source is unchanged.
- The closure is an honest empirical device that provides a finite low-flow
  melt, which is the stated Stage 10.11 goal.
- However, it is (a) effectively a cap-set constant rather than a physical
  prediction, (b) built on a haline sign opposite to the physical role of
  salinity, (c) attributed to the wrong paper for its operative coefficient,
  (d) outside the source correlation's validity range, and (e) 7–700× below the
  observed quiescent band, so it does not close the gap it was meant to close.

This is *not* Classification A (the closure is not physically verified against
iceberg observations) and *not* C (there is no mechanism-level failure
requiring a production fix; the shortcomings are documented design limits).

---

## 29. Limitations of This Audit

1. The sensitivity study uses a float64 Python replica of the float32
   production; anchor agreement is to `~1e-7` relative, sufficient for the
   conclusions but not a bit-for-bit cross-language contract.
2. `β_T = 3.0e-5 1/K` and `β_S = 7.8e-4 1/PSU` are treated as given; their
   temperature dependence near the freezing point was not re-derived (the
   outcome is insensitive to them in the capped regime).
3. No full-model run was performed; the audit is at the closure level.
4. The double-diffusive flux laws are cited but not implemented; the audit
   identifies the gap, it does not fill it.

---

## 30. Recommendations and Documentation Corrections

**Required (documentation only; no production change):**

1. Correct `docs/model/model_equation_ledger.md` §10.3: delete/replace
   "consistent with quiescent laboratory observations (0.01–1 m/day range)"
   with the correct statement (`m(U=0) = 1.4 × 10⁻³ m/day`, 7–700× below the
   observed band).
2. Correct the coefficient attribution: `0.15·Ra^(1/3)` → Lloyd & Moran (1974);
   note that Fujii et al. (1973) gives `Nu ∝ Ra^(1/5)` and does not supply the
   production constants.
3. Record the orientation caveat (`0.27·Ra^(1/4)` is the stable-orientation
   coefficient; laminar branch latent).
4. Record the haline-sign caveat and the cap-dominance finding (with the Table G
   result that haline/`Le` is numerically inert).
5. Add verified references: Lloyd & Moran (1974), Martin & Kauffman (1977),
   Keitzl et al. (2016), Middleton et al. (2021).

**Future (new stage, not now):**

6. Propose a diffusion-limited / double-diffusive low-flow parameterization
   validated against Martin & Kauffman (1977) and Keitzl et al. (2016) as the
   Stage 10.12 candidate.

---

## 31. Verification Evidence

- Sensitivity driver: `python/analysis/stage10_11_3_natural_convection_sensitivity.py`
  (tables A–J; baseline asserts the production anchors
  `γ_T_nat = 4.429877e-7 m/s`, `m = 1.638e-8 m/s`).
- Fortran: `iceberg_test_10p11_natural_convection` → 23 checks, 0 errors;
  `iceberg_test_10p10_three_equation` → 25 checks, 0 errors.
- Python: `test_three_equation.py` 65; `test_three_equation_natural.py` 70;
  `test_basal_melt_validation.py` 44; `test_observational_validation.py` 229;
  `test_calibration_assessment.py` 212 — all 0 errors.
- Citation verification: Crossref API, DOIs listed in Section 25.
- `git diff -- src/` empty (production physics unchanged).

---

## 32. References (added/verified in this stage)

1. Lloyd, J. R., & Moran, W. R. (1974). Natural convection adjacent to
   horizontal surface of various planforms. *Journal of Heat Transfer*, 96(4),
   443–447. https://doi.org/10.1115/1.3450224
2. Martin, S., & Kauffman, P. (1977). An experimental and theoretical study of
   the turbulent and laminar convection generated under a horizontal ice sheet
   floating on warm salty water. *Journal of Physical Oceanography*, 7(2),
   272–283. https://doi.org/10.1175/1520-0485(1977)007<0272:AEATSO>2.0.CO;2
3. Keitzl, T., Mellado, J.-P., & Notz, D. (2016). Impact of thermally driven
   turbulence on the bottom melting of ice. *Journal of Physical Oceanography*,
   46(4), 1171–1187. https://doi.org/10.1175/JPO-D-15-0126.1
4. Middleton, L., Vreugdenhil, C. A., Holland, P. R., & Taylor, J. R. (2021).
   Numerical simulations of melt-driven double-diffusive fluxes in a turbulent
   boundary layer beneath an ice shelf. *Journal of Physical Oceanography*, 51,
   403–418. https://doi.org/10.1175/JPO-D-20-0114.1
5. Fujii, T., Honda, H., & Morioka, I. (1973). A theoretical study of natural
   convection heat transfer from downward-facing horizontal surfaces with
   uniform heat flux. *International Journal of Heat and Mass Transfer*, 16(3),
   611–627. https://doi.org/10.1016/0017-9310(73)90227-5
6. Churchill, S. W. (1977). A comprehensive correlating equation for forced,
   natural and mixed convection. *AIChE Journal*, 23(1), 10–16.
   https://doi.org/10.1002/aic.690230103
