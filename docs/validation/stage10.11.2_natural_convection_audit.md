# Stage 10.11.2 — Scientific Audit and Fortran Verification of Natural-Convection Basal Melt

**Classification: B — PASS WITH LIMITATIONS.** The Stage 10.11 natural-convection
closure is scientifically sound, dimensionally correct, and now verified by a real
Fortran unit test (delivered in this stage). The audit found **no production-physics
bugs**, but it did find and correct three documentation/verification problems that
the Stage 10.11 delivery left behind:

1. The claimed Fortran test `iceberg_test_10p11_natural_convection` was **never
   delivered** in commit `6a0014e` (`docs/wiki/Stage10.11...`; the stage report
   §5.1/§8/§9 claimed "15 checks" that did not exist). This stage delivers the
   actual test: **23 checks, 0 errors** (embedded-literal independent replicas).
2. The original report's effect table claimed "at `U_rel = 0.1 m/s`, natural
   convection adds ~0.1% to forced convection". This is **wrong by ~5 orders of
   magnitude**: the float64 replica gives `gamma_T_eff/gamma_T_forced - 1 =
   2.177e-8` (≈ 2.2e-6 %), and the float32 production shows the two melt rates
   agree to within 2.2e-7 relative — natural convection at `U_rel = 0.1 m/s` is
   numerically indistinguishable from forced-only convection.
3. The Gayen et al. (2016) citation is **mis-cited** in the sources, comments and
   reference docs as "Melt-driven convection under a horizontal ice face"
   (JFM 798, 617-641). The actual paper is "Simulation of convection at a
   **vertical** ice face dissolving into saline water", J. Fluid Mech. **798,
   284-298**, DOI 10.1017/jfm.2016.315 (verified via Crossref). It studies a
   VERTICAL ice face and therefore does **not** support the "L_char = draft D"
   claim attributed to it. The characteristic length in production is the
   iceberg length `L` (the code passes `state%L`); comments claiming
   `L_char = D` per Gayen were a mis-attribution and are corrected (comment-only).

**Production physics changed:** NO (comment-only corrections in
`src/iceberg_types.f90`, `src/iceberg_thermodynamics.f90`; no numerical change).

**Commit:** `stage10.11.2: audit and verify natural-convection basal melt`

---

## A. Scope

Per the Stage 10.11.2 task specification (no Stage 10.12; no lateral melt /
atmospheric stability / EOS / geometry changes; no calibration; no artificial
`U_min` / `gamma_floor`; no "floor" framing; single logical commit):

1. Audit the scientific correctness of the Stage 10.11 natural-convection closure
   as implemented in production.
2. Deliver the missing Fortran unit test and verify real numbers.
3. Correct code comments and reference docs to match reality (characteristic
   length `L`, real Gayen 2016 paper, real 0.1 % → 2.2e-6 % effect magnitude).
4. Add missing bibliography entries.
5. Report honestly, including the anisotropy of supported claims.

## B. Physics Audit (production closure)

The production closure (Stage 10.11, selectable via
`BASAL_MELT_SCHEME_THREE_EQUATION_NATURAL`) consists of:

1. **Double-diffusive Rayleigh number** (`natural_convection_transfer_coeff`,
   `src/iceberg_types.f90:615-697`):

   ```
   Ra_eff = g * L^3 / (nu * alpha) * [beta_T * (T_w - T_B) + beta_S * (S_w - S_B) * Le]
   ```

   with `g = 9.80665`, `nu = 1.82e-6 m²/s`,
   `alpha = k/(rho_w*c_w) = 0.56/(1028*3974) = 1.3708e-7 m²/s`
   (→ `g/(nu*alpha) = 3.9307e13`), `beta_T = 3.0e-5 1/K`,
   `beta_S = 7.8e-4 1/PSU`, `Le = 100`, S in PSU = 1000·S_kg.

   - **Dimensionally correct**; combined buoyancy term is a linear (additive)
     double-diffusive stabilisation measure, not a finger-regime theory. This
     simplification is documented and retained (removing the haline term would
     zero `Ra` at `U_rel = 0` for `T_w - T_B ≈ 0`, an unphysical startup
     artifact; the `+` sign is retained as documented).
   - **Characteristic length:** production passes `state%L` (berg length) via
     `compute_basal_melt(prof, draft, state%L, ...)` — i.e. `L = L_berg`, NOT
     the draft. This matches the Fujii (1973) horizontal-plate correlation where
     the plate dimension is the horizontal scale. The variable is named
     `l_char` / `l_char_nat` in the code. **Comment-only bug:** several doc
     blocks claimed "D = draft (Gayen et al. 2016: cell scale ~ D, not L)".
     Fixed in this stage (see §E).

2. **Nusselt number** (Fujii et al. 1973, downward-facing horizontal plate):

   ```
   Laminar   (Ra < 1e7):   Nu = 0.27 * Ra^0.25
   Turbulent (Ra >= 1e7):  Nu = 0.15 * Ra^(1/3)
   Ra capped at RAYLEIGH_MAX = 1e10 before the regime switch.
   ```

   - Regime transition at `Ra = 1e7`, cap at `1e10` — consistent with the
     standard Fujii correlation range. Verified Crossref reference:
     Fujii, Honda & Morioka, *Int. J. Heat Mass Transf.* **16** (1973) 611-627,
     DOI 10.1016/0017-9310(73)90227-5.
   - **NUMERICALLY IMPORTANT FINDING (limitation):** for ANY realistic iceberg
     the cap is always active:
     - thermal-only term: `Ra = L³·3.93e13·(3e-5·ΔT) ≥ 1e10` at
       `L ≥ (1e10/(3.93e13·3e-5·2.9))^(1/3) ≈ 1.3 m`;
     - with the haline term (`β_S·ΔS·Le ≈ 7.8e-4·18.5·100 = 1.44` at the
       zero-flow anchor) the cap activates at `L ≈ 0.06 m`;
     - production `L = 40-100 m` ⇒ `Ra_eff ≈ 1e19-1e20 ≫ 1e10` ⇒ `Nu` is
       ALWAYS pinned at `0.15·(1e10)^(1/3) = 323.165` in production.
     So the laminar branch and the `1e7` transition are numerically latent in
     production; the correlation is used only in its capped-turbulent form. This
     is a documented limitation (the closure is a quiescent-flow floor proxy,
     not a regime-resolving theory), consistent with "not a floor" framing: the
     closure is a physical (buoyancy) mechanism, but its regime spectrum is
     collapsed by the cap at realistic berg sizes.

3. **Transfer coefficients:**

   ```
   gamma_T_nat = Nu * k / (L * rho_w * c_w)   [m/s]
   gamma_S_nat = gamma_T_nat * (K_S / K_T)     [m/s]  (J2010 Table 2 ratio)
   ```

   - Dimensionally correct (`m/s` velocity scale). With the cap pinned:
     `gamma_T_nat = 323.165·0.56/(L·1028·3974) = 4.43e-5/L` → `4.4e-7 m/s` at
     `L = 100 m`, `8.9e-7 m/s` at `L = 50 m` (exact L⁻¹ scaling, verified).

4. **Mixed convection** (Churchill 1977, exponent n=3):

   ```
   gamma_T_eff = (gamma_T_forced^3 + gamma_T_nat^3)^(1/3)
   ```

   - Churchill (1977), AIChE J. **23**(1) 10-16, DOI 10.1002/aic.690230103:
     the abstract explicitly recommends "the third root of the sum of the third
     powers" — n=3 is the correct, standard choice. Verified via Crossref.
   - **Effect magnitude at U_rel = 0.1 m/s:** the original Stage 10.11 report
     claimed ~0.1%. Correct value: `gamma_nat/gamma_forced = 4.43e-7/1.1e-4 =
     4.03e-3`, so `gamma_eff/gamma_forced = (1 + (4.03e-3)³)^(1/3) = 1 +
     2.177e-8`. Natural convection adds **2.2e-6 %** (relative) — NOT 0.1 %. At
     `U_rel = 1 m/s` the ratio is `(1 + 4e-10)^(1/3) − 1 ≈ 1.3e-10`. The
     contribution exceeds 1 % only below `U_rel ≈ 1e-3 m/s` (float64 replica).

5. **Three-equation interface** (`solve_three_equation_interface_natural`):
   bisection on the same Eq. I–III system as the forced solver, with per-iteration
   re-evaluation of the effective coefficients; the Stage 10.10.1 density-weighted
   salt balance `rho_w·gamma_S·(S_w - S_B) = rho_i·m·S_B` is retained (hard rule).
   Verified end-to-end (see §D, §F).

## C. Implementation Audit

- `natural_convection_transfer_coeff` — `pure` function, local variables only,
  no stale state. Units checked line-by-line (all SI inside the iceberg thermodyn
  module). `RAYLEIGH_MAX` is module-private; `RAYLEIGH_TRANSITION` and the
  Nusselt/Churchill constants are public (used by the new test). No `as any`-style
  Fortran shortcuts, no implicit floors, no `U_min`.
- `solve_three_equation_interface_natural` — the caller passes
  `l_char = state%L` (berg length). Solver mirrors the forced bisection exactly
  (same doubling upper bound 60+60, float32). No NaN/Inf paths found in the
  evaluated regimes.
- **Historical Stage 10.10 shadowing bug** (`latent_heat` local vs module
  `LATENT_HEAT`) is not present in the natural solver (checked; the natural
  solver uses distinctive local names).
- No production-physics change was required by the audit. **The formulation's
  physics is sound as implemented.**

## D. Verification (NEW — the missing Fortran test)

`test/iceberg_test_10p11_natural_convection.f90` is delivered in this stage.
It recomputes every anchor from **embedded literals** (Pr, ν, k, ρ_w, ρ_i, c_w,
c_i, L_f, EOS-80 coefficients, K_T/K_S, beta_T/beta_S, Le, Fujii coefficients,
Churchill n), calls the production functions only for the compared output, and
prints per-check OK/FAIL.

**Result (production Fortran build, float32):**

```
TOTAL CHECKS: 23  ERRORS: 0
```

Covers:

| Block | Checks | What is verified (all vs independent replica / embedded literals) |
|-------|--------|------------------------------------------------------------------|
| A | 2 | Cold ocean (`T_w < Tf`): `m = 0`, `S_B = S_w`, `T_B = Tf` |
| B | 4 | Zero-flow anchor `U_rel=0, T_w=2, S_w=34.5, L=100, D=50`:`m = 1.63801133e-8 m/s`(exact, ind 1.638e-8), `0.001415 m/day`, `S_B = 0.015961`, `T_B = −0.9016 °C` |
| C | 2 | Laminar branch (isolated, uncapped): L⁻⁰·²⁵ scaling `γ(0.05)/γ(0.1) = 1.189207 = 2^0.25`; `γ_T_nat(L=0.1) = 1.7174e-5` |
| D | 2 | Turbulent branch (isolated, uncapped): L-independent `γ(0.05)/γ(0.1) = 1.0`; `γ_T_nat(L=0.1) = 2.9886e-4` |
| E | 2 | Capped branch (Ra > 1e10): `γ(50)/γ(100) = 2.0` (Nu pinned, γ ∝ 1/L); `γ_T_nat(L=100) = 4.4299e-7` |
| F | 1 | Churchill mixing at U=0.1: `gamma_eff/gamma_forced − 1 < 0.1%` (float32-resolved; float64 true value 2.2e-6 %) |
| G | 2 | Monotonicity: `m(0) < m(1e-3) < m(0.1) < m(1)` |
| H | 1 | Linear U-scaling in the forced regime: `m(0.2)/m(0.1) = 2.000000` |
| I | 4 | Production end-to-end: zero-flow contract, interface freshening (`T_B > Tf`, `S_B < S_w`), scheme switch effective (`NATURAL` vs `THREE_EQUATION` at U=0), U=0.1 contract `m = 4.06740673e-6` |
| J | 3 | Scheme control regression: bulk forced U=0 `m = 0` (unchanged), THREE_EQUATION `m(U=0.1) = 4.06740764e-6` (regression), NATURAL finite |

**Cross-language contract** (production Fortran float32 vs Python float64 replica
from `three_equation_natural.py`):
- `m(U=0) = 1.63801133e-8 m/s` — Fortran/Python identical to 7 significant digits;
- `m(U=0.1) = 4.06740673e-6 m/s` — identical to 7 significant digits;
- Python suite `test_three_equation_natural.py`: **70 checks, 0 errors**.

## E. Documentation Audit (corrections in this stage)

| Location | Before | After |
|----------|--------|-------|
| `src/iceberg_types.f90` (constants doc block + function docstring + in-body) | "L_char = draft D (Gayen et al. 2016: cell scale ~ D, not L)"; `Ra_eff = g·D³...`; `γ_T_nat = Nu·k/D`; Gayen "horizontal ice face" JFM 798, 617-641 | `L` = berg length (Fujii plate scale); production passes `state%L`; `Ra_eff = g·L³...`; `γ_T_nat = Nu·k/L`; Gayen corrected to vertical-face paper JFM 798, 284-298, context only |
| `src/iceberg_thermodynamics.f90` (solver header) | "Характерная длина ... = осадка D (Gayen et al. 2016)" | "= длина айсберга L ... вызывающий код передаёт state%L" |
| `python/validation/three_equation_natural.py` (docstring) | "Characteristic length = draft D (Gayen 2016)" | L, with audit note |
| `docs/references/literature_matrix.md` | Gayen row: "Melt-driven convection under a horizontal ice face ... supports L_char = D" | Corrected title (vertical face), CONTEXT only, no L_char=D |
| `docs/references/citation_map.md` | Same mis-citation | Corrected |
| `docs/references/references.bib` | **missing** `fujiiHondaMoriokaNaturalConvection1973`, `gayenGriffithsKerrMeltDrivenConvection2016`, `churchillComprehensiveCorrelatingEquation1977` | Added (3 verified DOIs; 148 total entries) |
| `docs/model/model_equation_ledger.md` §10.3 | Gayen "convection cells; Gayen 2016 LES"; "(15 checks)" | L per Fujii plate; audit note; "(23 checks, delivered in Stage 10.11.2)" |
| `docs/validation/stage10.11_natural_convection.md` | §5.1 "15 checks", §6 "~0.1%"; Gayen line | Superseded claims annotated (see §G); exact values inserted |

## F. Parameters and Provenance

| Parameter | Value | Source | Audit |
|-----------|-------|--------|-------|
| `THERMAL_EXPANSION_COEFF` β_T | 3.0e-5 1/K | Fofonoff & Millard 1983 | plausible at freezing; no change |
| `HALINE_CONTRACTION_COEFF` β_S | 7.8e-4 1/PSU | Fofonoff & Millard 1983 | standard; no change |
| `LEWIS_NUMBER` | 100 | α/D_S for seawater | standard magnitude; no change |
| `NU_LAMINAR_COEFF` / `NU_LAMINAR_EXP` | 0.27 / 0.25 | Fujii et al. 1973 | Crossref-verified source; numerically latent in production (cap) |
| `NU_TURBULENT_COEFF` / `NU_TURBULENT_EXP` | 0.15 / 1/3 | Fujii et al. 1973 | Crossref-verified source; the only branch active in production |
| `RAYLEIGH_TRANSITION` | 1e7 | Fujii et al. 1973 | latent in production |
| `RAYLEIGH_MAX` | 1e10 | correlation validity cap | always active for production L; see §B.2 finding |
| `MIXED_CONVECTION_EXP` | 3 | Churchill 1977 | Crossref-verified (abstract explicitly recommends n=3) |
| `THREE_EQ_KT` / `THREE_EQ_KS` | 1.1e-3 / 3.1e-5 | Jenkins et al. 2010 Table 2 | U-based convention; documented limitation |

## G. Known Limitations (unchanged or new)

1. **Ra-cap collapses the regime spectrum** (NEW, quantified): for production
   berg lengths the cap pins `Nu = 323.165`; laminar and transition branches are
   latent. The closure is a buoyancy-driven low-flow proxy, not a
   regime-resolving theory — remains a documented approximation.
2. **Zero-flow melt is below the quiescent-observation band** (unchanged):
   `m(U=0) = 1.4e-3 m/day` vs the observed quiescent 0.01-1 m/day band — the
   natural-convection closure does NOT close the Stage 10.8.2 quiescent gap by
   itself (known limitation; documented, not hidden).
3. **Characteristic length:** production uses berg length `L`; the draft-based
   cell-scale justification attributed to Gayen et al. (2016) is withdrawn
   (that paper studies a vertical face). `L` remains the model-documented choice
   (matches what the code does) but is not directly validated for the horizontal
   base by the cited LES.
4. **Double-diffusive simplification:** the additive `β_T ΔT + β_S ΔS·Le`
   buoyancy measure is not full double-diffusive theory (finger/diffusive
   regimes not represented). Retained as documented; removing the `+` haline
   term reintroduces the zero-flow startup artifact.
5. **At `U_rel = 0.1 m/s` natural convection is negligible** (2.2e-6 %), NOT
   0.1 % as the original report stated. Forced convection dominates for any
   `U_rel ≳ 1e-3 m/s`. The closure's practical effect is confined to
   `U_rel ≲ 1e-3 m/s`.
6. **Fortran verification gap closed:** the Stage 10.11 report previously
   claimed a 15-check Fortran test that did not exist; the delivered test has
   23 checks and passes. All Fortran suites green; Python suites green
   (70 natural, 65 three-equation, 229 observational, 212 calibration,
   44 basal-melt).

## H. Regression

- Fortran: `fpm test --flag "-I/usr/include"` — **53 test targets, EXIT 0**
  (52 pre-existing + the newly delivered `iceberg_test_10p11_natural_convection`).
- Strict build: `-Wall -Wextra -fcheck=all` — clean.
- Python: 70/65/229/212/44 checks, all 0 errors.
- `git diff --check` — clean.
- `.gitignore` carries one local uncommitted line (`.omo/`) unrelated to this
  stage; left unstaged.

## I. Classification

**B — PASS WITH LIMITATIONS.**

The Stage 10.11 natural-convection closure is scientifically sound and
dimensionally correct as implemented; real Fortran verification now exists
(23/23 checks, cross-language contracts exact); all references are verified
(Fujii, Churchill via Crossref; Gayen corrected to the real paper); code
comments and reference docs were aligned with the actual production behavior
(length `L`, capped-Nu regime, 2.2e-6 % effect at U=0.1). No production-physics
change, no calibration, no artificial floors.

Limitations that prevent an "A": the Ra cap collapses the regime spectrum at
realistic berg sizes (laminar/transition latent — the closure behaves as a
single regime in production); the zero-flow melt (1.4e-3 m/day) remains below
the observed quiescent band; the characteristic-length choice `L` is
documented and consistent with the code but its horizontal-base justification
can no longer cite Gayen et al. (2016) (vertical-face paper); the
double-diffusive additive measure is a simplification.

**Not done (per Stage 10.11.2 rules):** no Stage 10.12, no internal thermal
evolution, no 10.8.2 re-scoring, no lateral melt / atmospheric stability / EOS /
geometry changes, no calibration, no `U_min`/`gamma_floor`, no
"natural-convection floor" framing.

---

*Report generated: 2026-09-11*
*Commit: `stage10.11.2: audit and verify natural-convection basal melt`*