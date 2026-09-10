# Stage 10.8.2 — Observational Validation of the Basal-Melt Closure

**Classification: C (pass with documented systematic limitations)**
**Production physics changed: NO**

Independent validation of the production basal-melt closure against a curated
set of published, verified observational melt rates for the submerged surface
of icebergs. The production coefficients (0.037 / 0.664 flat-plate Nusselt,
Pr = 13.8, nu = 1.82e-6 m^2 s^-1, k = 0.56 W m^-1 K^-1, Re_crit = 5e5,
rho_ice = 910 kg m^-3, L_f = 3.34e5 J kg^-1, EOS-80 freezing point,
MELT_RATE_MIN = 1e-12 m s^-1) are **inputs**, never fitted here.

References: verifiable record — `data/validation/observations/
iceberg_basal_melt_observations.csv` (19 records) + provenance note in the
same directory; `python/validation/observational_validation.py` (loader,
metrics, inverse-U, regimes, sensitivity, plots); `python/tests/
test_observational_validation.py` (229 checks, 15 function blocks A-O).

---

## 1. Scope and dataset

The observable that must be tested is the melt rate of the submerged surface of
icebergs (the basal plane where the draft/length aspect makes it dominant; the
side area contributes comparably for small bergs and in the tank experiments —
see the aspect-ratio analysis in Stage 10.9, which corrects the earlier
"basal plane dominating; side melt second" generalization), driven by the
ocean-side thermal forcing. Studies were selected only when they reported a
repeatable melt rate of an iceberg's submerged surface (laboratory, in-situ
field, synthesis, or remote-sensing position chains). Exclusions, applied
before any analysis:

- Rignot et al. 2010 calving-face rates (0.7-3.9 m/day): glacier terminus,
  plume-driven, not iceberg submarine melt — context only.
- Budd, Jacka & Morgan 1980 and Orheim 1980: breakage / size-distribution
  decay statistics and life-expectancy, not clean basal melt; the figure-only
  numeric melt bounds of the former are not OCR-recoverable, so no numeric row
  is taken from it (text anchors to Morgan & Budd 1978 are used in prose only).
- Tournadre/Bouhier-style remote-sensing *iceberg areal* estimates via physical
  resemblance: folded into the Enderlin et al. 2023 review upper bound, one
  context-only row.

Dataset composition (19 records):

| tier | count | rows | obs range (m/day) |
|---|---|---|---|
| lab-primary | 5 | Russell & Head 1980 (quiescent tank, S=35) | 0.0435 - 1.586 |
| synthesis-derived | 3 | Neshyba & Josberger 1980 (Antarctic best estimates) | 0.0137 - 0.1507 |
| field-primary | 1 | Keys & Williams 1984 (D'Urville Sea) | 0.06 +/- 0.01 |
| rs-derived | 10 | Enderlin & Hamilton 2014; Enderlin et al. 2016; Enderlin et al. 2023 (+ 1 context row) | 0.0137 - 0.50 |

All DOIs verified via the Crossref REST API; the 1980 Cambridge texts were
extracted from open-access PDFs. Uncertainties are transcribed only where the
source reports them; missing values are `NaN` (never invented).

## 2. Methods: model inputs per row

For the rows where the model closure is applicable (forcing fully specified
AND `u_rel > 0`), the production chain is evaluated exactly with
`depth_m = L_char_m` (draft). Four rows qualify: KW84 + NJ80(3). The five
quiescent-laboratory rows are evaluated separately as the natural-convection
gap test (`u_rel = 0` => closure value 0). The remote-sensing rows carry no
ocean forcing, so an **inverse-U** analysis reports which `U_rel` would be
required at `dT = 1/2/4 °C`, `L=50 m`, `S=35` (reference choices, stated).

Reference assumptions for the synthesis/field rows are documented per row in
the provenance file (`U_ref = 0.1 m/s`, `L_char = 50 m` NJ80; `L_char = 20 m`
KW84 from the 40-100 m berg length).

## 3. Result: point metrics on the four comparable rows

| metric | value |
|---|---|
| n | 4 |
| RMSE | 0.108 m/day |
| MAE | 0.092 m/day |
| bias (model - obs) | +0.083 m/day (model high) |
| mean obs / mean model | 0.0677 / 0.1506 m/day |
| mean abs rel err | 2.17 (217 %) |
| mean log10(model/obs) | +0.370 (= factor 2.3 high) |

Per row:

| row | obs (m/day) | model (m/day) | ratio | dT (°C) | Re | regime |
|---|---|---|---|---|---|---|
| KW84_DUrville | 0.060 +/- 0.01 | 0.0423 | 0.70 | 0.88 | 1.10e6 | turbulent |
| NJ80_dT2 | 0.0137 | 0.0800 | 5.84 | 2.0 | 2.75e6 | turbulent |
| NJ80_dT4 | 0.0466 | 0.1601 | 3.44 | 4.0 | 2.75e6 | turbulent |
| NJ80_dT8 | 0.1507 | 0.3201 | 2.12 | 8.0 | 2.75e6 | turbulent |

The single field observation (KW84) is reproduced at the lower edge of the
reported range (model 0.705x at L_char = draft = 20 m). With the production
characteristic length L_char = berg length (40-100 m) the ratio falls to
0.55-0.62x — below the reported 0.05-0.07 band; the comparison length
assumption is relaxed in Stage 10.9 Section 7. The synthesis curve is
overestimated by a factor that declines with thermal driving (5.8 -> 2.1 from
dT 2 to 8 °C). This positive bias toward high dT at the reference U/L is the
headline numerical finding; Stage 10.9 shows it is a functional-form
(dT-power-law) mismatch rather than a scale offset.

## 4. Natural-convection gap (quiescent laboratory rows)

Russell & Head 1980 report `R = 1.8e-2 (T+1.8)^1.5` m/day in a **quiescent**
tank (S=35), basal~(side). The forced-convection closure returns 0 (below the
1e-12 m/s noise guard):

| row | obs m/day | model m/day | orders above model floor |
|---|---|---|---|
| RH_0C | 0.0435 | 0 | 5.7 |
| RH_2C | 0.1333 | 0 | 6.2 |
| RH_5C | 0.3192 | 0 | 6.6 |
| RH_10C | 0.7296 | 0 | 6.9 |
| RH_18C | 1.5859 | 0 | 7.3 |

This quantifies a known production limitation: no natural-convection branch.
At `u_rel -> 0` the real melt is dominated by free convection driven by the
melt water itself; the flat-plate closure cannot represent it. **Documented as
evidence, not fixed** (adding a natural-convection branch is out of scope and
would require a new production parameter).

## 5. Inverse-U analysis (remote-sensing rows, no ocean forcing)

Required `U_rel` (m/s) to reproduce each observed melt with `L=50 m, S=35`:

| row | obs m/day | U(dT=1) | U(dT=2) | U(dT=4) |
|---|---|---|---|---|
| END14_Sermilik | 0.39 | 1.72 | 0.72 | 0.30 |
| END16_Ilulissat_shallow | 0.16 | 0.57 | 0.24 | 0.10 |
| END16_Ilulissat_deep | 0.50 | 2.35 | 0.99 | 0.42 |
| END16_Sermilik_shallow | 0.17 | 0.61 | 0.26 | 0.11 |
| END16_Sermilik_deep | 0.49 | 2.29 | 0.96 | 0.41 |
| END23_WAP | 0.137 | 0.47 | 0.20 | 0.082 |
| END23_WAIS | 0.110 | 0.35 | 0.15 | 0.062 |
| END23_EAIS | 0.0137 | 0.026 | 0.018 | 0.017 |
| END23_EAP | 0.0137 | 0.026 | 0.018 | 0.017 |

The Greenland fjord rates (0.16-0.5 m/day) require plausible fjord currents of
~0.1-1.0 m/s at dT=2-4 °C — consistent with observed Sermilik/Disko conditions,
so the closure is not obviously wrong in the turbulent regime. Caveat (resolved
in Stage 10.9): the rs rows measure **submarine** melt while the closure
predicts a **basal** melt rate; the two are equal only where the basal plane
dominates, which is an aspect-ratio-dependent condition, not a universal one.
The East Antarctic maximum (0.0137) requires only ~0.02 m/s, i.e. the model
easily produces small rates at low dT — physically reasonable. The context row
(open Southern Ocean, up to 1.5 m/day) is not a central estimate and is
excluded from metrics everywhere.

## 6. Regime analysis

All four comparable observations lie in the **turbulent** regime
(Re >= 1.1e6 > 5e5). The laminar branch (Re < 5e5, melt ~ U^0.5 L^-0.5) is
therefore not exercised by any model-comparable observation: any conclusion
about the production closure's field performance rests on the turbulent branch.
The laminar exponent checks (M.1-M.4) are verified analytically against the
code, but there is no field anchor to pin the laminar form.

## 7. Sensitivity to the reference U/L assumptions

Turbulent scaling (m ~ U^0.8 L^-0.2) at the reference S=35, dT=4:

| | L=20 m | L=50 m | L=100 m |
|---|---|---|---|
| U=0.05 m/s | 0.102 | 0.088 | 0.077 m/day |
| U=0.10 m/s | 0.184 | 0.160 | 0.139 m/day |
| U=0.20 m/s | 0.331 | 0.288 | 0.251 m/day |

Doubling U raises m by 1.74x (U^0.8); doubling L lowers m by 0.87x (L^-0.2).
Qualitative conclusions (order-of-magnitude agreement with the field row;
factor 2-6 overestimate of the synthesis row; 5.7-7.3 order gap at rest) are
robust to the stated U_ref/L ranges.

## 8. Model-vs-model benchmark (consistency with Stage 10.8.1)

The observational layer evaluates the **same** closure as
`python/validation/basal_melt.py` at bit level (float64): check J.1-J.3 assert
`via_ov == direct` (exact) for the KW84 row, and the G.2 independent literal
(re-implementation from EOS-80 and flat-plate constants) reproduces the
production chain to < 1e-12 relative. There is no numerical drift between the
10.8.1 reference layer and the 10.8.2 application.

## 9. Interpretation, systematic bias and limitations (Q9)

- Where a forcing-anchored observation exists (KW84), the closure agrees at
  the lower edge of the reported range at L_char = draft (0.705x), dropping to
  0.55-0.62x under the production berg-length length scale (Stage 10.9 §7).
- Against the NJ80 synthesis the closure reads **high**, by 2.1-5.8x at the
  reference parameters, with a clear dT-trend (ratio -> 2 as dT -> 8 °C). Stage
  10.9 demonstrates this is a dT-power-law mismatch (obs ~ dT^1.73, closure
  dT^1.0), i.e. a shape error, not a stable scale offset; it is NOT corrected
  in production.
- The closure cannot represent quiescent (lab) melt: 5.7-7.3 orders of
  magnitude gap. This is the strongest structural limitation; it is also
  structurally uncalibratable (a scalar multiplier times zero is zero), which
  is the main reason Stage 10.9 does not recommend a coefficient fit.
- fjord remote-sensing rates are reproducible with plausible U_rel; that is a
  necessary but weak consistency, not a verification, and it applies to
  submarine (not basal) melt.
- Side-area melt dominates or matches the basal plane for bergs with
  D/L < ~0.25; the "basal plane dominating" generalization in an earlier draft
  of this report is corrected in Stage 10.9 §3 (claims #7, #8).
- All F90 production physics is untouched; this is a diagnostics/validation
  stage only. The follow-up assessment (Stage 10.9) concludes that no scalar
  calibration of the heat-transfer coefficient is supported by these data.

## 10. Reproduction

```bash
python python/tests/test_observational_validation.py        # 229 checks, A-O
python python/tests/test_basal_melt_validation.py           # 10.8.1 unmodified
python python/validation/observational_validation.py        # prints metrics, writes figures
fpm test --flag "-I/usr/include"                            # canonical suite (unchanged)
```

Figures (data/output/diagnostics/stage10.8.2/):
`fig1_model_obs_loglog.png`, `fig2_dT_sweep.png`,
`fig3_required_Urel.png`, `fig4_regime_map.png`,
`fig5_observed_uncertainties.png`, `fig6_log_ratio_bias.png`.

Artifacts: `data/validation/observations/iceberg_basal_melt_observations.csv`
(+ provenance md), `python/validation/observational_validation.py`,
`python/tests/test_observational_validation.py`.

## 11. Files changed

- `data/validation/observations/iceberg_basal_melt_observations.csv` (new)
- `data/validation/observations/iceberg_basal_melt_observations_provenance.md` (new)
- `python/validation/observational_validation.py` (new)
- `python/tests/test_observational_validation.py` (new)
- `docs/validation/stage10.8.2_observational_validation.md` (this report)
- `docs/references/references.bib`, `docs/references/literature_matrix.md`,
  `docs/references/citation_map.md`, `docs/model/*`, `docs/PROJECT_ROADMAP.md`,
  `AGENTS.md`, `.github/workflows/ci.yml` (see diff)
- `src/*`, `test/*`, `python/validation/basal_melt.py`,
  `python/tests/test_basal_melt_validation.py`: **unchanged**

## 12. Classification rationale

**C** — the validation is complete and the checks all pass, but the 
production closure shows (i) a 5.7-7.3 order-of-magnitude inability to
represent quiescent melt (structural limitation), and (ii) a systematic
positive bias factor 2.1-5.8 against the NJ80 synthesis at reference
parameters (later shown in Stage 10.9 to be a dT-power-law shape mismatch),
with no observational anchor for the laminar branch. These are
documented findings; no production coefficient was changed and calibration is a
separate stage. AS IS, validation passed, with documented systematic
limitations.

---

## ASSUMPTIONS

- `depth_m = L_char_m` (draft) for the freezing-point pressure.
- NJ80 `S=35`, `U_ref=0.1 m/s`, `L=50 m`; KW84 `L=20 m` (from the reported
  40-100 m berg length) — reference, not measured, values. Stage 10.9 shows
  the KW84 ratio falls to 0.55-0.62x when the production berg-length L is used.
- `melt_component = submarine` for the remote-sensing rows is a basal proxy
  whose validity is aspect-ratio-dependent (Stage 10.9 claims #7/#8 correct the
  stronger "basal dominates" generalization); documented, no tuning.

## RISKS

- Only 4 model-comparable observational rows from **2** independent sources;
  the turbulent branch is the only branch with field anchors. Laminar
  coefficients remain unverified against field data.
- The positive synthesis bias is a dT-shape mismatch (obs ~ dT^1.73 vs closure
  dT^1.0), not a scale offset; the required individual-row coefficient spans
  ~8x across the two source families, which Stage 10.9 quantifies and uses to
  rule out any scalar calibration. This is documented, not silently changed.

## 15. Follow-up assessment (Stage 10.9)

The claims in this report marked with caveats, plus the identifiability of the
heat-transfer coefficient itself, are assessed in
[`stage10.9_calibration_assessment.md`](stage10.9_calibration_assessment.md).
Conclusion: **no scalar calibration of the production coefficient is
supported**; the recommended next step is a three-equation ice-ocean interface
(Holland & Jenkins 1999) with a natural-convection floor.

## Verified sources (all DOI-checked via Crossref)

Russell & Head 1980 (10.3189/S0260305500017092); Neshyba & Josberger 1980
(10.1175/1520-0485(1980)010<1681:OTEIAI>2.0.CO;2); Josberger & Neshyba 1980
(10.3189/S0260305500017080); Keys & Williams 1984
(10.3189/S0022143000005955); Enderlin & Hamilton 2014
(10.3189/2014JOG14J085); Enderlin, Hamilton, Straneo & Sutherland 2016
(10.1002/2016GL070718); Enderlin et al. 2023 (10.1017/jog.2023.54);
Schild et al. 2021 (10.1029/2020GL089765); Budd, Jacka & Morgan 1980
(10.3189/S0260305500017079); Orheim 1980 (10.3189/S0260305500016888).