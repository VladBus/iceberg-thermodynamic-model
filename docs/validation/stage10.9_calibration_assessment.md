# Stage 10.9 — Calibration Assessment of the Basal-Melt Coefficient

**Classification: C (validation insufficient for robust calibration)**
**Production physics changed: NO** (no parameter is calibrated here)

Scientific assessment of whether the ocean-side turbulent heat-transfer
coefficient of the production basal-melt closure can be calibrated against the
curated observational set of Stage 10.8.2. The answer, established by source-aware
identifiability analysis, is **no**: the problem is structurally non-identifiable
(multiple uni-parameter fits conflict by ~8x across sources and cannot be
reconciled by a single scalar), and the largest discrepancies are
functional-form differences, not scale errors. The recommended next step
(Stage 10.10) is a structural upgrade to a three-equation ice-ocean interface,
not a coefficient retune.

References: `python/validation/calibration_assessment.py` (module, 650 lines),
`python/tests/test_calibration_assessment.py` (212 checks, blocks A-T), the
Stage 10.8.2 dataset, and the six named literature sources (DOI-verified here).

---

## 1. Scope and objective

Stage 10.9 answers a single question: can the scalar production coefficient
`C_gamma` of the flat-plate closure be re-fit so that the model reproduces the
observational set of Stage 10.8.2, and is such a fit robust? Production
physics is frozen; `C_gamma` is the only hypothetical free parameter (we test
whether even one scalar could fit; we do not change it).

Production closure (written out, `python/validation/basal_melt.py`) with
`S` in PSU and `P = rho_w g z / 1e4` dbar:

```
Tf = (EOS_FP_A0 + EOS_FP_A1*sqrt(S) - EOS_FP_A2*S)*S + EOS_FP_BP*P
dT = max(T - Tf, 0)                       (clamped; never negative)
U  = relative_velocity(u_w,v_w,u_i,v_i)   (here ice at rest -> U = u_w)
Re = U * L_char / nu                      (nu = 1.82e-6, k = 0.56, Pr = 13.8)
Nu = 0.664*Re**0.5*Pr**(1/3)   (Re <  5e5, laminar)
Nu = 0.037*Re**0.8*Pr**(1/3)   (Re >= 5e5, turbulent)
m  = C_gamma * Nu * k / L_char * dT / (rho_ice * L_f)      [m/s]
```

with `rho_ice = 910`, `L_f = 3.34e5`, `MELT_RATE_MIN = 1e-12 m/s`. In the
production code `L_char = state%L` (berg length), passed unconditionally; the
Stage 10.8.2 comparison used `L_char = draft` (addressed in Section 7).

Linear-chain structure: `m = C_gamma * A(U,L,S) * dT` with `A` nondimensional,
so a single scalar `C_gamma` can only rescale, never reshape. All conclusions
here follow from that structural fact plus the heterogeneous dataset.

## 2. Data and applicable rows

Same curated set as Stage 10.8.2 (19 records, 4 tiers; all DOIs Crossref-verified).
Only rows with fully specified forcing AND `u_rel > 0` enter the calibration
basis (closure low-velocity branch requires flow to be formulated):

| row | source | obs m/day | model m/day | model/obs | dT °C | Re |
|---|---|---|---|---|---|---|
| KW84_DUrville | Keys & Williams 1984 | 0.060 ± 0.01 | 0.04230 | 0.705 | 0.880 | 1.10e6 |
| NJ80_dT2 | Neshyba & Josberger 1980 | 0.0137 | 0.08003 | 5.842 | 2.0 | 2.75e6 |
| NJ80_dT4 | Neshyba & Josberger 1980 | 0.0466 | 0.16006 | 3.437 | 4.0 | 2.75e6 |
| NJ80_dT8 | Neshyba & Josberger 1980 | 0.1507 | 0.32012 | 2.124 | 8.0 | 2.75e6 |

Model values are the production chain evaluated at the reference forcing. The
**effective number of independent observations is 2**, not 4: the three NJ80
rows are one source curve (`NJ80_as_one_source`, Grouping test M/N). All 4 rows
are turbulent (Re >= 1.1e6).

## 3. Independent audit of the Stage 10.8.2 claims (numeric re-computation)

Claim numbers follow the 10.8.2 report; 1-9 were each recomputed from the raw
data/equations in `calibration_assessment.py` (scripts independent of 10.8.2).

| # | Stage 10.8.2 claim | Audit result |
|---|---|---|
| 1 | KW84 reproduced "within reported range" (0.70x) | **PASS with caveat**: 0.705x at L_char=draft=20 m; in *production* L_char = berg length 40-100 m the ratio is 0.55-0.62, i.e. *below* the reported 0.05-0.07 band, so "better than the reported range" is overstated |
| 2 | NJ80 overestimated "2.1-5.8x at reference parameters" | **CONFIRMED numerically** (5.84, 3.44, 2.12), BUT the NJ80 observation scales ~ dT^1.73 while the closure is dT^1.0: a **functional-form mismatch**, not a scale error (Section 5) |
| 3 | natural-convection gap "5.7-7.3 orders" | **CONFIRMED** (5.70, 6.19, 6.57, 6.93, 7.26 orders above the closure's numerical floor 1e-12 m/s = 8.64e-8 m/day); closure returns exactly 0 at rest, so any scalar C_gamma leaves the gap infinite at u=0 |
| 4 | inverse-U: fjord rows reproducible at "plausible 0.1-1.0 m/s" | **PASS as consistency check** at dT=2-4 °C (U_req 0.10-0.99); at dT=1 °C two rows require 1.7-2.35 m/s. RS rows measure **submarine** melt, the closure predicts **basal** only -> basal-only proxy, weaker than stated |
| 5 | all comparable rows turbulent | **CONFIRMED** (Re >= 1.10e6 > 5e5) |
| 6 | laminar branch has no field anchor | **CONFIRMED** (0 comparable rows with Re < 5e5) |
| 7 | "basal plane dominating; side melt second" | **CORRECTED - not supported as stated**: A_side/A_basal = 2(L+W)D/(LW) is 0.8-1.33 for KW84-scale bergs (D/L ~ 0.2) and ~0.8 for L~1 km tabulars; the basal plane dominates only for D/L < 0.25. Russell & Head's own note states "basal~(side)" in the tank |
| 8 | "submarine approx. equal to basal" proportionality | **CORRECTED - not supported**: proportionality constant is not unity, varies with draft/length aspect and, for melting, with side (parabolic) vs basal (flat) flow geometry |
| 9 | comparison L_char = draft | **MISMATCH with production**: production passes `state%L` (berg length); comparison used draft (20/50 m). The L^-0.2 dependence keeps the effect modest (<= 25%), but the comparison L is not the production L (Section 7) |

Two claims are corrected in this stage (#7, #8). Claims #1, #2, #4 are
softened/qualified. Everything else is reconfirmed.

## 4. Identifiability: can one scalar reproduce the set?

For each applicable row the implied coefficient is `C_gamma = obs/model`
(a perfect model would need C_gamma = 1 on every row):

| row | inferred C_gamma |
|---|---|
| NJ80_dT2 | 0.1712 |
| NJ80_dT4 | 0.2910 |
| NJ80_dT8 | 0.4707 |
| KW84_DUrville | 1.4183 |

- Pooled spread: **max/min = 8.286** (0.918 decades); value not ~1 on the
  JW84 row and not ~1 on the NJ80 rows.
- Geometric mean (pooled, naive): 0.4270.
- Per-source geometric means: NJ80 **0.2862** (n=3 but 1 source), KW84 **1.4183** (n=1).

These are not within mutual uncertainty bands; the sources require 8x-different
coefficients. A single scalar cannot fit both. The identifiability summary is
deterministic (test T).

## 5. Functional-form mismatch (dT power-law)

Log-log slope of the observed melt curves:

| curve | observed exponent | closure |
|---|---|---|
| NJ80 synthesis | dT^1.7297 | dT^1.0 |
| RH80 tank law (R = 1.8e-2 (T+1.8)^1.5) | (T+1.8)^1.50 | dT^1.0 |

The closure is exactly linear in dT (tests I, J: model dT exponent = 1.0000).
The NJ80 curve rises ~73 % faster than linear as dT increases, so the required
C_gamma rises with dT (0.171 -> 0.471 across dT 2-8 °C). No scalar multiplier
can absorb a power-law difference in the driver; the factor "2.1-5.8x" of
Stage 10.8.2 is the projection of a shape mismatch onto one reference dT, not
a stable calibration target. Similarly the RH80 tank law carries a non-linear
temperature dependence that the forced-convection form cannot produce.

## 6. Sensitivity decomposition (exponent audit)

Measured finite-difference sensitivities (tests H, I, J):

| parameter | turbulent | laminar | analytic (flat-plate) |
|---|---|---|---|
| a_U (m ~ U^a_U) | +0.80000 | +0.50000 | 0.8 / 0.5 |
| a_L (m ~ L^a_L) | -0.20000 | -0.50000 | -0.2 / -0.5 |
| a_dT (m ~ dT^a_dT) | 1.00000 | 1.00000 | 1 |
| a_C (m ~ C^a_C) | 1.00000 | 1.00000 | 1 |

Dependence on C is exactly linear in both regimes (test K; c_gamma_grid =
`C * model`, C=0 -> 0). The only free knob affects the magnitude, not the form;
U and L enter only with their flat-plate exponents; dT enters linearly where
observations demand ^1.7-1.8. Doubling U raises melt 1.74x, doubling L lowers
it 0.87x (turbulent) - both small compared with the 8.3x spread between
sources.

## 7. Characteristic-length geometry sensitivity (berg length vs draft)

Production uses `L_char = state%L` (berg length); the 10.8.2 comparison used
`L_char = draft`.

KW84 (`L_char = 20..100 m`, observed D ~ 20 m):

| L_char m | model m/day | model/obs |
|---|---|---|
| 20 (draft, 10.8.2) | 0.0423 | 0.705 |
| 40 | 0.0375 | 0.624 |
| 60 | 0.0351 | 0.586 |
| 80 | 0.0337 | 0.562 |
| 100 | 0.0328 | 0.546 |

NJ80_dT4 (L_char 20..200 m):

| L_char m | model m/day | model/obs |
|---|---|---|
| 20 | 0.1912 | 4.104 |
| 50 (10.8.2 reference) | 0.1601 | 3.437 |
| 100 | 0.1407 | 3.020 |
| 200 | 0.1248 | 2.679 |

Using production L (berg length) instead of draft moves the KW84 row *further* from
the observation (0.55-0.62x vs 0.705x) and lowers the NJ80 ratio modestly; the L^-0.2
exponent bounds the effect at ~25 %. Replacing the comparison's draft choice with the
production length choice does not close the identifiability problem; it slightly
*degrades* the one field-anchored row. (Also: pressure enters only through Tf's small
BP*P term; with rho_w=1028 vs P~z dbar the difference is ~0.8 % at z=500 m - negligible.)

## 8. Stanton number reconciliation

The production coefficient `C_gamma` translates to a shear Stanton number
`St_shear = C_gamma * 0.037 * Re^-0.2 * Pr^(1/3)` (turbulent):

| row | St (flat-plate model) | St implied by observation |
|---|---|---|
| NJ80_dT2 | 3.436e-4 | 5.882e-5 |
| NJ80_dT4 | 3.436e-4 | 9.999e-5 |
| NJ80_dT8 | 3.436e-4 | 1.617e-4 |
| KW84_DUrville | 4.127e-4 | 5.854e-4 |

The observed band spans ~10x (5.9e-5 to 5.9e-4) and is dT-dependent in the NJ80
synthesis - the signature of a non-Stanton-scaled heat exchange (buoyancy,
three-equation coupling), not a constant-`C_gamma` offset. The melt-driven
glaciological anchor `St = 0.011` (Jenkins et al. 2010, see Section 9) is more
than an order of magnitude above both; a shear-only flat plate under-predicts
the melt-water-driven transfer that is the primary basal mechanism in fjord and
Antarctic settings, while the RS-submarine observations bound the bulk average
one to two orders below it. There is no single Stanton value consistent with
the two source families.

## 9. Literature base and conventions

The six named sources plus one supporting closure are now verified against
Crossref (title/author/year/journal match; previously only the corpus-internal
bibliography was consulted):

| source | DOI | status |
|---|---|---|
| Weeks & Campbell 1973 | 10.3189/S0022143000032044 | verified |
| Bigg 1997 | 10.1016/S0165-232X(97)00012-8 | verified |
| Holland & Jenkins 1999 | 10.1175/1520-0485(1999)029<1787:MTIOIA>2.0.CO;2 | verified |
| Jenkins & Nicholls 2010 | 10.1175/2010JPO4317.1 | verified |
| FitzMaurice & Stern 2018 | 10.1016/j.ocemod.2018.08.005 | verified |
| Cenedese & Straneo 2023 | 10.1146/annurev-fluid-032522-100734 | verified |

Key conventions (as cited in Stage 10.7/10.8.1 but not yet pinned to their
sources): Holland-Jenkins type three-equation interface (`St`-based melt-driven
transfer; the Jenkins 2010 St=0.011 anchor); buoyancy-driven boundary-layer
scaling (FitzMaurice & Stern 2018); and the laminar/turbulent flat-plate
correlation used in production is a **single-phase heat-transfer** law - it was
never derived for the melt-driven two-phase interface, which is the reason its
St and the observed/Jenkins St disagree rather than the model being off by a
coefficient.

## 10. Natural convection structure (uncalibratable by design)

The five quiescent lab rows (RH80) sit 5.70-7.26 orders of magnitude above the
closure's numerical floor (1e-12 m/s -> 8.64e-8 m/day). The closure returns
exactly 0 at rest (test L, and MELT_RATE_MIN is a guard, not melt). Because a
scalar C_gamma multiplies A = 0 identically, **no finite coefficient can raise
the quiescent branch from 0**; the gap is structural, not parametric. Any
realistic calibration target must therefore include a natural-convection branch
(or a free-convection floor) as new physics. This is the strongest single
argument that Stage 10.9 concludes "no scalar calibration" and points Stage 10.10
at an interface model.

## 11. Leave-one-source-out cross-check

Fitting on one source and scoring the other (source-wise groups):

| training source C_gamma | held-out source | model/obs on held-out |
|---|---|---|
| KW84-only, C = 1.418 | NJ80 (dT2/4/8) | 8.29 / 4.87 / 3.01 |
| NJ80-only, C = 0.286 | KW84 | 0.202 |

Every held-out source shows a residual beyond a factor ~2.4 in log space
(residual_log10 > 0.4), i.e. no refit reproduces the other source near 1. This is
the standard signature of non-identifiability of a single parameter across
heterogeneous sources, and is deterministic (test O).

## 12. Decisions (Q1-Q10)

- **Q1. Is there evidence in the curated set to change production
  C_gamma?** NO. Inferred required values straddle ~8x across sources and
  dT; no scalar is defensible.
- **Q2. Is the NJ80 factor 2.1-5.8 a calibration offset?** NO - it is the
  projection of a dT^1.73-observed vs dT^1.0-model shape mismatch; flipping the
  L/U reference moves the number to ~0.6-0.7 instead (KW84 side).
- **Q3. Is the KW84 "within range" result a stable anchor?** WEAK. It is one
  source at L=draft; with production L (berg length) it moves below the
  reported band (0.55-0.62x).
- **Q4. Would dropping the NJ80 rows (leaving KW84 only) enable a fit?**
  NO - one source cannot constrain a two-parameter form, and the dT shape
  mismatch that drives the spread remains unpinned.
- **Q5. Can U/L uncertainty reconcile the spread?** PARTIALLY - exponents
  U^0.8 L^-0.2 bound the effect to x1.84 and x0.87 per doubling; the 8.3x
  spread plus the dT exponent gap far exceeds it.
- **Q6. Can the natural-convection gap be removed by C_gamma?** NO -
  structurally impossible (Section 10); a free-convection branch is new physics.
- **Q7. Is the flat-plate drag/heat analogy appropriate physically?**
  APPROXIMATE at best - single-phase correlation mapped onto a two-phase
  melt-driven interface; literature (three-equation, St=0.011) disagrees at the
  convention level, not coefficient level.
- **Q8. Is a three-equation ice-ocean interface the right next step?**
  YES - Holland & Jenkins 1999, St-based melt-driven transfer (Jenkins 2010),
  buoyancy-informed (FitzMaurice & Stern 2018) would remove the shape and
  convention problems in one structural step.
- **Q9. What should Stage 10.10 contain?** Implementation of a
  three-equation interface (Tm = a S m^1/3, Tb = Tf(Sb, P), freezing-point
  coupling; heat/salt Stanton with melt-water correction), plus a
  natural-convection floor, with the 10.8.2 set re-scored as the acceptance
  criterion; continued no-change to the ocean model. Alternative (calibration
  of the current coefficient) explicitly NOT recommended.
- **Q10. Classification** - **C**: validation insufficient for a robust
  calibration; the assessment is complete and reproducible, the coefficient is
  NOT identifiable, and no production parameter was changed.

## 13. Production change statement

No production Fortran was changed; no parameter was calibrated. `git diff -- src/`
is empty. The only new code is diagnostics/validation Python
(`python/validation/calibration_assessment.py`) and its test suite. The
conclusion "do not change C_gamma" is itself the deliverable.

## 14. Files changed / reproduction

- `python/validation/calibration_assessment.py` (new; module)
- `python/tests/test_calibration_assessment.py` (new; 212 checks A-T)
- `docs/validation/stage10.9_calibration_assessment.md` (this report)
- `docs/validation/stage10.8.2_observational_validation.md` (claims
  #7, #8 corrected; #1, #2, #4 qualified; Section 15 of that report links here)
- `docs/model/*`, `docs/references/*`, `docs/PROJECT_ROADMAP.md`,
  `.github/workflows/ci.yml`, `AGENTS.md` (see diff)

Reproduction:

```bash
python python/tests/test_calibration_assessment.py        # 212 checks A-T
python python/tests/test_observational_validation.py      # 229 checks (unchanged)
python python/tests/test_basal_melt_validation.py         # 44 checks (unchanged)
python python/validation/calibration_assessment.py        # prints the assessment table
fpm test --flag "-I/usr/include"                          # canonical F90 suite (unchanged)
```

The Python layer is pure (no Fortran) so the suite runs without gfortran.

## 15. Classification rationale

**C** - a calibration of the current scalar heat-transfer coefficient is not
supported by the evidence (non-identifiable across sources, dT-shape
mismatch, and a structurally uncalibratable quiescent branch). The stage's
value is the negative result plus the corrected claims and the literature
pinning, which set up Stage 10.10 as a three-equation interface upgrade.
There is no scalar coefficient whose production change is justified today.

---

## ASSUMPTIONS

- `C_gamma` is the only tunable parameter; exponents, Re_crit, Pr, nu, k,
  rho_ice, L_f, and the EOS-80 freezing point are fixed physics (as in
  production).
- `L_char` in production is `state%L`; the 10.8.2 comparison's `L_char = draft`
  is treated as a choice to correct, not a production value.
- rs-derived rows measure submarine melt; they are a **proxy** for basal melt
  wherever the basal term dominates, which 10.8.2 assumed and 10.9 now shows is
  geometry-dependent (claims #7/#8).
- The NJ80 curve is treated as ONE source with three thermal-driving points
  (not three independent observations).

## RISKS

- The functional-form (dT^1.73) evidence rests on one synthesis curve;
  confirming it needs a second dT-resolved melt series.
- The natural-convection floor is unmeasured in the field for iceberg (vs tank)
  scales; research-scale data (Cenedese & Straneo 2023) should anchor it.
- Moving to a three-equation interface introduces new parameters (two Stanton
  numbers, melt-water slope a) that must be pinned before Stage 10.10 is
  re-scored against the same set.

## Verified sources by role

- **Weeks & Campbell 1973** - melt-rate parameterization context.
- **Bigg 1997** - closed-form melt closure context.
- **Holland & Jenkins 1999** - three-equation interface (basis for 10.10).
- **Jenkins & Nicholls 2010** - melt-driven Stanton anchor (St = 0.011).
- **FitzMaurice & Stern 2018** - buoyancy-driven tabular-berg basal melt.
- **Cenedese & Straneo 2023** - iceberg-melt review and research-scale anchors.
- **Martin & Adcroft 2010** - iceberg representation for ocean models.