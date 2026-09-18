# Stage 10.18B — Observational Constraint and Parameterization Discrimination

**Date:** 2026-09-18
**Status:** COMPLETE — observational research/validation stage; **no production physics change**
**Baseline commit:** `0504853` (Stage 10.18A); **this stage commit:** pending
**Scope:** build a verified observational dataset of iceberg lateral/side melt,
normalize it to the model's quantities, evaluate every Stage 10.18A lateral-melt
parameterization against it, and determine whether observations can discriminate
between the formulations and narrow the 30-day mass-loss range (1.3–26.1 %).

---

## 1. Objective

Determine, from **observations** (not model preference):

1. which observational data can actually discriminate between the
   velocity-independent legacy formulation, velocity-dependent forced-
   convection formulations, plume formulations, and the geometry conventions;
2. whether sufficient observational evidence exists to select one formulation
   for the production model.

Answer based on data. If the data do not discriminate, say so (OPTION E/F).

## 2. Stage 10.18A baseline (carried forward)

| Variant | m_lateral (30-day TEST_11 mean) | ΔM_30d |
| --- | --- | --- |
| LEGACY_FULL_HEIGHT | 0.2599 m/day | 15.43 % |
| LEGACY_SUBMERGED | 0.4599 m/day (effective shrink) | 26.08 % |
| BULK_FORCED | 0.0126 m/day | 1.28 % |
| BIGG1997 | 0.0169 m/day | 1.54 % |
| BIGG_PLUS_BUOY | 0.0515 m/day | 3.58 % |
| FITZMAURICE_PLUME | 0.0372 m/day | 2.74 % |

Stage 10.18A decision: **OPTION D** — multiple parameterizations remain
plausible; an observational constraint was required before any production
change. This stage delivers that constraint assessment.

## 3. Observational inventory

Curated dataset (versioned, with the Stage 10.8.2 convention):
`data/validation/observations/iceberg_lateral_melt_observations.csv`
(17 cases) + `..._observational_sources.csv` (9 sources) +
`..._observations_provenance.md`. Generated outputs (gitignored):
`data/output/stage10.18b/`.

| Case group | Source | Cases | Directness | Melt definition |
| --- | --- | --- | --- | --- |
| RH80 lab blocks | Russell-Head 1980 (Annals Glaciol. 1) | 5 (T = 0/2/5/10/18 °C, S = 35) | **DIRECT** | side (mean recession of submerged walls), quiescent |
| Sermilik submarine | Enderlin & Hamilton 2014 (J. Glaciol. 60) | 2 (cylinder/cone idealized geometry) | INDIRECT | submarine (side+basal), area-averaged |
| Sermilik GPS/sonar | Schild et al. 2021 (GRL 48) | 4 (A/B × GPS-9d/drone-6d) | INDIRECT | submarine (side+basal), area-averaged, individual geometry |
| Antarctic shelf | Enderlin et al. 2023 (J. Glaciol. 69) | 4 regional maxima + Thwaites sensitivity | INDIRECT | submarine (side+basal), area-averaged, satellite differencing |
| Sermilik velocity | Moyer et al. 2019 (GRL 46) | 1 (velocity constraint row) | INDIRECT | iceberg velocity (not a melt observation) |

Regions: laboratory, Sermilik Fjord (SE Greenland), Antarctic shelf (WAP/WAIS/
EAIS/EAP), open Southern Ocean (cited). Grand Banks: no independently measured
thermal sidewall-melt dataset verified (Kubat et al. 2007 validation is calving
intervals; documented). Barents Sea: no verified side-melt observations;
the "71 % wave erosion" claim was not traced to a primary dataset (UNVERIFIED,
excluded). **Direct lateral-melt field observations are scarce**: the only
prediction-usable cases are the Russell-Head laboratory blocks.

## 4. Data sources

| source_id | Citation | DOI | Content |
| --- | --- | --- | --- |
| RH80 | Russell-Head 1980, Ann. Glaciol. 1:119-122 | 10.3189/S0260305500017092 | Lab block side/basal melt, S~35, fit `R = 1.8e-2*(T+1.8)^1.5` m/day |
| ENDERLIN14 | Enderlin & Hamilton 2014, J. Glaciol. 60(224) | 10.3189/2014JoG14J085 | Sermilik submarine melt 0.39 ± 0.17 m/day (cylinder), 10 icebergs, DEM |
| SCHILD21 | Schild et al. 2021, GRL 48(3) | 10.1029/2020GL089765 | Sermilik GPS+sonar overall melt 0.10–0.27 m/day, 2 icebergs |
| ENDERLIN23 | Enderlin et al. 2023, J. Glaciol. 69(278) | 10.1017/jog.2023.54 | Antarctic 15 sites: max 5–50 m/a; Thwaites sensitivity 24 m/a/°C (R²=0.80) |
| MOYER19 | Moyer et al. 2019, GRL 46 | 10.1029/2019GL082309 | Sermilik iceberg velocities 0.018–0.023 m/s mean, 0.14 max |
| CS2023 | Cenedese & Straneo 2023, ARFM 55 | 10.1146/annurev-fluid-032522-100734 | Parameterization summary (MODEL_DERIVED) |
| FITZMAURICE17 | FitzMaurice et al. 2017, GRL 44 | 10.1002/2017GL073585 | Lab plume parameterization; Sermilik model 0.06–0.10 m/day (MODEL_DERIVED) |
| KUBAT07 | Kubat et al. 2007 | NA | Grand Banks model validation vs calving intervals (MODEL_DERIVED) |
| BROSTROM09 | Broström et al. 2009, met.no rep. 17 | NA | Model deterioration runs (MODEL_DERIVED) |

## 5. Data quality

| Quality class | Sources | Count |
| --- | --- | --- |
| PRIMARY_DIRECT | RH80 (lab) | 5 cases |
| PRIMARY_INDIRECT | ENDERLIN14, SCHILD21, ENDERLIN23, MOYER19 | 12 cases |
| MODEL_DERIVED | CS2023, FITZMAURICE17 (application), KUBAT07, BROSTROM09 | reference only (excluded from prediction metrics) |
| UNVERIFIED | "71 % Barents wave erosion"; White et al. 1980 / Kubat et al. 2007 wave equations; Grand Banks side-melt numbers | **excluded from the dataset** |

No `UNVERIFIED` value is used as a quantitative constraint.

## 6. Observational definitions

- **RH80**: side melt = mean recession rate of the submerged walls (direct
  dimensional measurement); basal and mean-side rates reported as similar.
- **ENDERLIN14 / SCHILD21 / ENDERLIN23**: submarine melt = volume loss divided
  by submerged surface area (area-averaged normal retreat); includes side AND
  basal faces — for a lateral-only comparison this is an **upper bound**.
  Enderlin14 idealized (cylinder/cone) shapes → stated upper-bound estimates;
  Schild21 individual full geometry (22–43 % area under-estimates in idealized
  shapes, per Schild21).
- No source reports lateral-only melt in the field: **direct lateral field
  observations are not available**; all field values are submarine
  (side+basal).

## 7. Normalization

`data/output/stage10.18b/observational_dataset_normalized.csv` (17 rows) +
`observational_provenance.csv` (traceability per case).

| Quantity | Convention | Status |
| --- | --- | --- |
| melt rate | m/day (Enderlin23 m/a → /365) | done |
| delta_T | RH80: `T+1.8` (published fit); Enderlin23: reported thermal-forcing midpoint (1.5 K WAP/WAIS, 0.5 K EAIS/EAP — documented range midpoints); Sermilik: **NA** (concurrent CTD values not extracted) | documented |
| u_rel | RH80: 0.0 (quiescent); all field cases: **NA** (relative velocity not reported with the melt); Moyer19 velocity used as magnitude reference only | U_missing = TRUE for field |
| geometry | L/D reported for Schild21; RH80 block ~1 m (approximate); Antarctic/sermilik-DEM: NA | partial |

Normalization confidence: HIGH (RH80), MEDIUM (Enderlin23 range midpoints),
QUALITATIVE (Sermilik).

## 8. Geometry conventions

- Full-height vs submerged distinction affects the **volume** loss for a given
  rate, not the rate itself. No observation reports the vertical distribution
  of melt (sail vs draft): **geometry = NOT CONSTRAINED BY AVAILABLE
  OBSERVATIONS**.
- Geometry-sensitive quantities that ARE observable: Schild21 area-averaged
  rates use true reconstructed surface area (not an idealized perimeter),
  i.e., they are convention-free at the rate level. Implied volume-loss per
  area convention is shown in Fig 6 for illustration only.
- `geometry_transform_required` = no mathematical geometry transform is
  applied (rate-level comparison only).

## 9. Velocity conventions

| Case group | U_rel | Status |
| --- | --- | --- |
| RH80 lab | 0.0 (quiescent tank) | used |
| Sermilik / Antarctic field | NA | **U_missing = TRUE** |
| Moyer19 (Sermilik) | mean 0.018–0.023 m/s, max 0.14 m/s | magnitude reference only (not a melt case) |

Consequence: velocity-dependent formulations (BULK, BIGG, PLUME detached) can
be evaluated **only** against the quiescent lab cases (where they give 0 or
the plume branch), not against the field. The legacy equivalent U ≈ 0.30 m/s
(Stage 10.18A) is **10–15× above the observed Sermilik mean iceberg velocity
(0.018–0.023 m/s) and above the observed max (0.14 m/s)** — the implicit
forcing of the legacy constant is high relative to measured fjord flow;
consistent with the interpretation that the legacy constant acts as an
effective *total* thermal coefficient (including buoyant/plume contributions),
not a forced-convection coefficient.

## 10. Temperature conventions

- RH80 uses bulk tank temperature with the freezing onset −1.8 °C (`ΔT = T+1.8`).
- Enderlin23 reports depth-averaged thermal forcing (WAP ~1–2 °C, rarely >2 °C;
  Weddell-like sites ≤0.3 °C); range midpoints documented.
- Sermilik cases: temperature NA (CTD data exist in Schild21 but values not
  extracted in this audit) → **no ΔT-based prediction for Sermilik**.
- No case conflates plume temperature with bulk temperature: the FitzMaurice
  plume prediction uses the ambient-ΔT proxy, explicitly flagged.

## 11. Model parameterizations

Formulas, coefficients and provenance: `data/output/stage10.18b/
literature_parameterizations.csv`; implementations in
`python/validation/lateral_melt.py`. All six Stage 10.18A variants are
evaluated; predictions are **NA when a required input is missing** (no
mean-substitution).

## 12. Model-vs-observation comparison

`data/output/stage10.18b/model_observation_comparison.csv` (102 rows = 17 cases
× 6 models). Directly comparable (rate + ΔT known): **RH80 lab, N = 5**.
Field cases with reported thermal forcing (Enderlin23, N = 4) are usable by the
legacy (ΔT-only) family and are treated as a **bounded comparison**
(lateral-only ≤ observed submarine total).

Statistics on the directly comparable set (RH80 lab, N = 5):

| Model | RMSE | MAE | bias |
| --- | --- | --- | --- |
| LEGACY_FULL_HEIGHT / LEGACY_SUBMERGED | 0.211 | 0.198 | **+0.198** (systematic over-prediction) |
| BULK_FORCED | 0.796 | 0.562 | **−0.562** (gives 0 at U=0) |
| BIGG1997 | 0.796 | 0.562 | −0.562 |
| BIGG_PLUS_BUOY | 0.475 | 0.342 | −0.342 |
| FITZMAURICE_PLUME | 0.427 | 0.263 | −0.256 |

[m/day units]. Interpretation: on the quiescent lab data, the legacy family has
the lowest RMSE but a systematic positive bias (linear-in-ΔT over-predicts the
nonlinear `ΔT^1.5` lab behaviour at low temperature: legacy/RH80 = 3.6 at
ΔT = 1.8 K → 1.1 at ΔT = 19.8 K); the forced-convection-only variants fail the
quiescent cases outright (0 vs 0.04–1.6 m/day); the buoyant/plume terms capture
the nonzero-at-rest behaviour but under-predict magnitude. **The direct
comparison does not select a winner; it shows that the lab observations
require a nonzero-at-U=0 (buoyant/plume) term and a nonlinear temperature
dependence.**

## 13. Statistical analysis

- Filtered datasets (per stage rule):
  - Dataset A (PRIMARY_DIRECT only): RH80, N = 5 → metrics above.
  - Dataset B (DIRECT + INDIRECT with ΔT): adds Enderlin23 (N = 4) but only for
    the legacy family (ΔT-only); the added cases are submarine (side+basal),
    so they enter the bounded comparison, not the point metrics.
  - Dataset C (all usable): identical to B (field cases without ΔT cannot be
    predicted).
- **Leave-one-source-out: NOT APPLICABLE** — all prediction-usable cases come
  from a single source (RH80); removing any other source does not change the
  set (verified: identical RMSE/MAE across non-RH80 drops), and removing RH80
  empties the set.
- Normalized residuals: no directly comparable case carries a reported
  uncertainty (only ENDERLIN14, which is not directly comparable) →
  `comparison_status = qualitative_only` for the sigma-normalized analysis
  (Fig 5 documents this).

## 14. Regime analysis

`parameterization_regime_matrix.csv` (exploratory thresholds: LOW_U < 0.03,
MOD 0.03–0.3, HIGH > 0.3 m/s; LOW_ΔT < 1 K, MOD 1–5 K, HIGH > 5 K):

- RH80 lab: U = 0 (LOW_U), ΔT 1.8–19.8 K (MOD→HIGH).
- Enderlin23: ΔT 0.5–1.5 K (LOW→MOD); U unknown.
- Sermilik: ΔT and U unknown (Moyer19 velocity: LOW_U mean).
- **The observational ΔT axis is covered** (0.5–19.8 K); **the U axis is
  effectively unconstrained at field scale** (only the quiescent point U = 0
  and one fjord velocity reference).

## 15. Geometry constraint

**NOT CONSTRAINED.** No observation separates sail vs draft melt or measures
the vertical distribution of lateral retreat. The full-height vs submerged
ambiguity (Stage 10.17 F2 / 10.18A factor 1.77) remains a modeling choice
undetermined by available data.

## 16. Wave erosion constraint

**NOT CONSTRAINED.** No dataset in this inventory separates wave erosion from
thermal melt. The C&S 2023 parameterized maximum (0.5–1.0 m/day) and the
White/Kubat wave equations could not be verified from primary sources; no wave
forcing exists in the model (Stage 10.18A). Wave erosion is excluded from the
thermal lateral-melt comparison.

## 17. Effective C_LATERAL

`data/output/stage10.18b/effective_c_lateral.csv` (N = 9: 5 RH80 + 4
Enderlin23). C_eff = m_obs/ΔT in m/(s·K):

| Statistic | Value | vs production 1e-6 |
| --- | --- | --- |
| p10 | 3.15e-7 | 0.32× |
| p25 | 3.24e-7 | 0.32× |
| **median** | **5.43e-7** | **0.54×** |
| p75 | 8.49e-7 | 0.85× |
| p90 | 9.53e-7 | 0.95× |
| range | 2.79e-7 … 1.06e-6 | 0.28× … 1.06× |
| Thwaites slope (Enderlin23) | 24 m/a/°C = 7.6e-7 | 0.76× (range 0–3.2e-6) |

**Production C_LATERAL = 1e-6 m/(s·K) falls near the top of the observational
C_eff distribution** (between p75 and p90), and within the Thwaites slope
range. The distribution is regime-dependent (lab quiescent buoyant convection
vs Antarctic shelf), and no single coefficient is recovered — the spread spans
~0.3× to ~1.1× production. The production constant is **observationally
plausible as an effective total thermal coefficient** but is not uniquely
determined by the data.

## 18. Uncertainty

- Only ENDERLIN14 reports symmetric uncertainties (0.38 ± 0.17 m/day).
- Schild21 reports rate spread (0.10–0.27) and geometry-induced uncertainty
  (22–43 % area), not a single σ.
- RH80 individual points are figure-only (not digitized); the entered values
  are evaluations of the published fit → fit uncertainty not reported.
- All other cases: uncertainty NA. **No σ is fabricated.**

## 19. Conflicting observations

- Sermilik: Enderlin14 (0.39 ± 0.17 m/day) vs Schild21 (0.10–0.27 m/day). Not
  an outlier case: Schild21 attribute the difference to individual-geometry
  area (22–43 % higher surface area → lower rate for the same volume loss) and
  note their rates are lower than prior studies. Both are retained; the spread
  is documented as geometry-method dependence.
- Legacy over-prediction at cold low-ΔT (RH80 low-T; Enderlin23 cold sites):
  consistent across two independent environments — treated as a real
  temperature-dependence signal, not an outlier.

## 20. Findings

| # | Finding | Classification | Evidence |
| --- | --- | --- | --- |
| O-01 | Direct lateral-melt field observations are **scarce**: only the RH80 lab blocks (N = 5) support point prediction; field values are submarine (side+basal) area-averaged | VERIFIED | dataset audit |
| O-02 | Quiescent lab melt is nonzero (0.04–1.6 m/day) and **requires a buoyant/plume (U=0-nonzero) term**; forced-convection-only variants (BULK, BIGG) predict 0 and fail these cases (bias −0.56 m/day) | VERIFIED | RH80 metrics |
| O-03 | Lab temperature dependence is **nonlinear** (RH80 `R = 1.8e-2·ΔT^1.5`); linear legacy over-predicts low-ΔT lab melt (3.6× at 1.8 K → 1.1× at 19.8 K) | VERIFIED | RH80 fit |
| O-04 | Legacy lateral-only exceeds the observed **total** submarine melt in 3/4 Antarctic shelf cases (cold EAIS/EAP, WAIS) — legacy over-predicts cold low-ΔT shelf conditions | VERIFIED (bounded) | Enderlin23 + bounded comparison |
| O-05 | Production C_LATERAL = 1e-6 is near the top of the observational C_eff distribution (median 0.54×; range 0.28–1.06×) and within the Thwaites slope range — **observationally plausible as an effective coefficient**, not uniquely determined | RESEARCH FINDING | C_eff N=9 |
| O-06 | Legacy equivalent U ≈ 0.30 m/s is 10–15× above observed Sermilik mean iceberg velocity (0.018–0.023 m/s) and above the observed max (0.14 m/s) — the legacy constant behaves as a total-thermal (buoyant+plume-inclusive) coefficient, not a forced-convection coefficient | RESEARCH FINDING | Moyer19 + 10.18A |
| O-07 | Velocity dependence qualitatively supported (Enderlin23: "temperature-only parameterizations unlikely to be accurate"; shear importance; lab U^0.8) but **not field-quantified** — no velocity-resolved melt observations | RESEARCH FINDING (qualitative) | Enderlin23 |
| O-08 | Geometry (full-height vs submerged): **NOT CONSTRAINED** by available observations | NOT CONSTRAINED | dataset audit |
| O-09 | Wave erosion: **NOT CONSTRAINED** (no separable observations; no verified primary equations) | NOT CONSTRAINED | §16 |
| O-10 | Leave-one-source-out: NOT APPLICABLE (single prediction source RH80) | VERIFIED | LOSO analysis |
| O-11 | The direct comparison does **not** select a unique formulation; the highest-RMSE failures are the forced-convection-only variants on quiescent data | VERIFIED | §12 |

## 21. Limitations

- Sample size: 5 directly comparable cases, all from one lab source and one
  environment; field cases lack concurrent ΔT/U.
- Mixed definitions: field "submarine" = side+basal; the lateral-only
  comparison is valid only as an upper-bound check.
- RH80 entered values are evaluations of the published fit (figure points not
  digitized); the fit is quiescent-lab, not ocean.
- Enderlin23 ΔT values are reported-range midpoints (documented), not
  case-level measured driving.
- Firecrawl/Wiley access blocked during the audit; some primary full texts
  (Schild21 via author repository, Enderlin via Cambridge/DOI) were fetched;
  Grand Banks and Barents Sea side-melt observations remain unverified.
- No seasonal/ocean-state normalization: Sermilik summer vs Antarctic
  multi-year means vs January TEST_11 are not temporally matched.

## 22. Scientific decision

**OPTION E — multiple formulations remain observationally plausible
(insufficient discrimination for a unique selection).** Concretely:

- the legacy constant is **observationally compatible** at the aggregate level
  (C_eff distribution brackets production; Sermilik absolute rates 0.10–0.27
  m/day bracket the legacy 0.26 m/day at its driving), but **not uniquely
  confirmed**;
- the lab observations **require** a nonzero-at-U=0 (buoyant/plume) term and a
  nonlinear temperature dependence, which the legacy linear form lacks at low
  ΔT (systematic over-prediction there);
- velocity dependence is **qualitatively supported** but **not
  field-quantified**;
- geometry and wave erosion are **not constrained**.

The 30-day mass-loss range (1.3–26.1 %, Stage 10.18A) is **not narrowed to a
single point** by the observations; it is narrowed only in the sense that the
forced-convection-only end of the range is inconsistent with the quiescent lab
evidence, and the legacy over-predicts cold low-ΔT conditions.

## 23. Production implications

**Production decision: KEEP_CURRENT.**

- No evidence justifies changing production lateral-melt physics in this
  stage (legacy observationally compatible; no unique alternative selected;
  geometry and wave erosion unconstrained).
- The findings are research inputs for a future, explicitly approved physics
  stage: (a) add a buoyant-convection term (Neshyba-Josberger/RH80-type) to
  represent U=0 melt; (b) reconsider the linear-ΔT legacy at low driving;
  (c) resolve the geometry convention with targeted observations; (d) add
  wave erosion only when wave forcing and verified parameterizations exist.

## 24. Reproducibility

```bash
# Independent tests (62 checks)
conda run -n iceberg-thermodynamic-model \
    python python/tests/test_observational_constraint.py

# Analysis + normalized dataset + comparison + statistics + figures
conda run -n iceberg-thermodynamic-model \
    python python/analysis/stage10_18b_observational_constraint.py
# writes data/output/stage10.18b/ (normalized dataset, provenance,
# literature parameterizations, regime matrix, model-observation comparison,
# statistics, leave-one-source-out, effective C_LATERAL, constraint matrix,
# summary.json, reproducibility.log, plots/fig01..fig10.png)

# Full Python suite (all stage tests, standalone scripts)
for t in python/tests/test_*.py; do conda run -n iceberg-thermodynamic-model python "$t"; done
```

Curated dataset (versioned): `data/validation/observations/
iceberg_lateral_melt_observations.csv` + sources + provenance. Environment:
conda `iceberg-thermodynamic-model` (Python 3.12, numpy, pandas, matplotlib).
Full-text access: Wiley 403 → author/Cambridge copies used (documented in the
provenance file).

## 25. Classification

| Item | Classification |
| --- | --- |
| Observational inventory (17 cases, 9 sources) | **VERIFIED** (fetched primary texts; exclusions documented) |
| Direct lateral-melt field observations availability | **VERIFIED: scarce** |
| Quiescent lab melt requires buoyant/plume term | **VERIFIED** |
| Lab temperature dependence nonlinear (ΔT^1.5) vs legacy linear | **VERIFIED** |
| Legacy over-predicts cold low-ΔT (lab + Antarctic shelf) | **VERIFIED (bounded)** |
| Production C_LATERAL observationally plausible (C_eff median 0.54×, range 0.28–1.06×) | **RESEARCH FINDING** |
| Legacy equivalent-U 0.30 m/s above observed fjord velocities | **RESEARCH FINDING** |
| Velocity dependence qualitative (not field-quantified) | **RESEARCH FINDING (qualitative)** |
| Geometry constraint | **NOT CONSTRAINED** |
| Wave erosion constraint | **NOT CONSTRAINED** |
| Discrimination to a unique formulation | **NOT DEMONSTRATED (OPTION E)** |
| Production physics | **UNCHANGED (KEEP_CURRENT)** |