# Stage 10.18C — Existing Observations Reanalysis and Velocity-Resolved Melt Constraint

**Date:** 2026-09-18
**Status:** COMPLETE — scientific validation / observational research; **production physics UNCHANGED**
**Baseline:** `d99a4bf` (Stage 10.18B); **this stage commit:** pending
**Classification target:** A — scientific validation / observational research
**Production decision target:** **KEEP_CURRENT**

---

## 1. Objective

Determine what the **existing** public observations can actually constrain
about lateral/side melt, total submarine melt, temperature dependence,
velocity dependence, relative velocity, depth dependence, geometry
dependence, and the side-vs-basal distinction — before any new field
campaign and without changing the model. Extract the maximum scientifically
defensible information from the public datasets (Schild21, Enderlin23,
Enderlin14, Moyer19, RH80), including a search for machine-readable
associated datasets and an attempted reconstruction of actual relative
velocity.

## 2. Baseline

Stage 10.18B conclusion (**preserved**): **OPTION E** — insufficient
evidence for unique parameterization selection; production **KEEP_CURRENT**.
Stage 10.18C does not overturn this unless genuinely stronger evidence is
produced. The Stage 10.18A parameterization set (LEGACY_FULL_HEIGHT,
LEGACY_SUBMERGED, BULK_FORCED, BIGG1997, BIGG_PLUS_BUOY, FITZMAURICE_PLUME)
is re-compared against the **corrected** observational categories.

## 3. Methodological corrections to Stage 10.18B (mandatory)

| # | Correction | Consequence |
| --- | --- | --- |
| M-1 | **RH80 N=5 is NOT five independent observations** — they are five evaluation points of ONE published fit `R = 1.8e-2·(T+1.8)^1.5` (`independent_case=FALSE`, `observation_type=PUBLISHED_FIT_EVALUATION`). RH80-based RMSE/MAE/bias are re-labelled **curve-evaluation diagnostics**, not independent-sample statistics. | Stage 10.18B §12 metrics re-interpreted accordingly; no independent N=5 claim. |
| M-2 | **No mixed C_eff.** `C_eff_lab_lateral` (RH80) and `C_eff_submarine` (field, side+basal) are computed and reported **separately**. The field quantity is `SUBMARINE_TOTAL_EFFECTIVE_COEFFICIENT`, never a lateral coefficient. | Stage 10.18B §17 mixed N=9 percentile table is superseded. |
| M-3 | **Moyer19 is U_ice, not U_rel.** The legacy effective velocity scale U_eq ≈ 0.30 m/s is compared only against iceberg **translational** speeds (0.018–0.023 m/s mean; max 0.14 m/s), with the explicit statement that this is not a direct U_rel comparison. | No claim "model U_rel is 10–15× observed U_rel". |
| M-4 | **Nonzero melt at U=0 ⇒ `NONZERO_BUOYANCY_OR_FREE_CONVECTION_COMPONENT`**, not "plume". The exact FitzMaurice plume mechanism is not established by RH80. | Wording in §20/§30. |
| M-5 | **Enderlin23 slope (24 m/a/°C) is a submarine-melt thermal sensitivity**, not a lateral coefficient; no side/basal partition is observationally justified. | Kept as `SUBMARINE_TOTAL` slope. |

## 4. Observational sources

| source_id | Study | What it provides |
| --- | --- | --- |
| RH80 | Russell-Head 1980 (Ann. Glaciol. 1) | Laboratory side melt, S~35, fit `R = 1.8e-2·(T+1.8)^1.5` m/day; U=0 |
| SCHILD21 | Schild et al. 2021 (GRL 48) | 2 Sermilik icebergs, full 3D geometry, GPS/drone/sonar, overall submarine melt 0.10–0.27 m/day; 13 CTD casts (qualitative hydrography); **no ocean currents** |
| ENDERLIN23 | Enderlin et al. 2023 (J. Glaciol. 69) | 15 Antarctic sites 2011–2022; regional maxima 5–50 m/a; Thwaites submarine thermal sensitivity 24 m/a/°C; **individual-iceberg CSV collection at USAP-DC 601679 (identified, not retrieved — account-gated)** |
| ENDERLIN14 | Enderlin & Hamilton 2014 (J. Glaciol. 60) | Sermilik submarine melt 0.39 ± 0.17 m/day (aggregate, idealized geometry) |
| MOYER19 | Moyer et al. 2019 (GRL 46) | Sermilik iceberg translational speeds (0.018–0.023 m/s mean; 0.14 max) — velocity reference only |

## 5. Data acquisition

- **Schild21:** raw GPS/SfM/multibeam/CTD records identified at the Arctic Data
  Center (10.18739/A22V2CB5M, A2QF8JK6B, A2NG4GS8C, A2KP7TS5N) — point clouds
  and casts, **no tidy derived melt table, no ADCP/current-meter dataset**.
  Paper-level values (Table 1, text) used; mean along-track speeds (A 0.045,
  B 0.072 m/s) **derived** here from reported track lengths (35/56 km over
  9 days) — documented derivation.
- **Enderlin23:** USAP-DC dataset 601679 (10.15784/601679),
  `Antarctic-iceberg-csvs.zip` — per-iceberg CSV collection (coordinates,
  dates, elevation, density, volume, surface area, draft, submerged area,
  volume change, submarine meltwater flux). **Identified but not retrieved**:
  download requires a USAP-DC account; anonymous access returned the portal
  landing page. Regional-maximum treatment retained (documented gap).
- **Enderlin14 / Moyer19:** no public machine-readable associated datasets
  found.
- **RH80:** full text fetched (Cambridge Core); individual points are
  figure-only (not digitized).

Provenance for every value: `data/validation/observations/stage10.18c/
provenance.md` (row-by-row) and `sources.csv`.

## 6. Data provenance

See `data/validation/observations/stage10.18c/provenance.md`. Key rules:
values verbatim or documented-derived; NA for missing; no uncertainty
fabrication; no U_rel substitution; no regional-maximum inflation to
individual observations.

## 7. Data independence

`independence_groups.csv` (generated). Melt observational units:
**8 independent units** (1 RH80 single fit + 1 Enderlin14 aggregate (10
icebergs, paper-level) + 2 Schild21 icebergs + 4 Enderlin23 regional
aggregates). Repeated Schild21 estimates of one iceberg share a group
(`independent_case=FALSE`); RH80 points share `RH80_SINGLE_FIT`. No row is
falsely independent (test-enforced).

## 8. Melt definitions

| source | melt_definition | observation_type |
| --- | --- | --- |
| RH80 | LATERAL_ONLY | PUBLISHED_FIT_EVALUATION |
| ENDERLIN14, SCHILD21, ENDERLIN23 | SUBMARINE_TOTAL (side+basal) | INDIRECT_SUBMARINE |
| MOYER19 | — (velocity) | VELOCITY_REFERENCE |

Lateral model output is compared against submarine observations only as a
**bound** (lateral ≤ submarine total), explicitly marked `BOUNDED`.

## 9. Temperature normalization

| source | convention |
| --- | --- |
| RH80 | `ΔT = T + 1.8` (published fit onset; lab) |
| ENDERLIN23 | depth-averaged thermal forcing; range midpoints 1.5 K (WAP/WAIS), 0.5 K (EAIS/EAP) — `normalization_status = MEDIUM`, reported-range midpoints documented, **not** `T+1.8` |
| ENDERLIN14 / SCHILD21 / MOYER19 | NA (no numeric T/S table recovered; Schild21 hydrography qualitative: Polar Water 10–150 m, Atlantic Water below ~150 m, warming below ~250 m) |

## 10. Velocity normalization

- RH80: `u_rel_speed = 0.0` (quiescent by experiment).
- All field cases: `u_rel_speed = NA`, `u_rel_status = NOT_RECONSTRUCTED` —
  no paired ocean velocity exists in any dataset.
- Schild21 ice speeds (A 0.045, B 0.072 m/s) are **derived iceberg
  translational speeds** (`u_ice`), never promoted to `u_rel`.
- Moyer19 speeds are `u_ice` reference values only.

## 11. U_rel reconstruction

**Attempted, not possible.** Reconstruction requires vector ocean velocity
+ vector iceberg velocity at the same time/depth. No dataset provides ocean
velocity (no ADCP/current-meter in Schild21 or associated records; Moyer19 is
iceberg tracking only; Enderlin23 has no velocity data; Enderlin14 no data
files). **Actual U_rel cannot be reconstructed from existing public data.**
Vector relative velocity is implemented and tested in the validation layer
for future use.

## 12. Schild21 analysis

- 2 independent icebergs (A: L 733 m, keel 386 m, h ~35 m; B: L 518, keel
  255, h ~22.5 m); overall submarine melt (GPS-9d) 0.16 / 0.10 m/day,
  (GPS-6d) 0.18 / 0.09, (drone-6d) 0.27 / 0.15; calving < 4 %; volume loss
  A 1.99e5, B 8.59e4 m³/day.
- Depth-dependent parameterization range quoted in the paper: 0.05–0.65
  m/day; model depth-average 0.30 / 0.21 m/day — **MODEL_DERIVED context
  only**.
- Hydrography qualitative (13 CTD casts, Polar/Atlantic Water structure);
  no numeric profiles recovered.
- **Side vs basal separation: not possible** — geometry reconstruction gives
  area-averaged submarine melt only → `SUBMARINE_TOTAL` preserved.
- **Velocity/depth dependence: `VELOCITY/DEPTH_DEPENDENCE_SUPPORTED_QUALITATIVELY`**
  (keel-depth-linked melt differences and hydrographic structure per the
  paper) — no paired U_rel(z) allows quantitative testing. This does **not**
  validate any specific parameterization.

## 13. Enderlin23 analysis

- 4 regional maxima retained (WAP 0.137, WAIS 0.110, EAIS 0.014, EAP 0.014
  m/day); Thwaites submarine thermal sensitivity 24 m/a/°C (R² = 0.80,
  RMSE 3.7 m/a/°C), range near-zero to ~100 m/a/°C.
- Variability at similar thermal forcing is reported by the authors (WAP
  shallow bergs show no thermal-forcing relationship; shear/plume peaks at
  Thwaites/Edgeworth) — **observed variability is documented; causal
  mechanism (shear/velocity) is a stated hypothesis of the authors, not a
  measured U_rel relation here**.
- Individual-iceberg CSV collection (USAP-DC 601679) identified but not
  retrievable anonymously; **documented gap** (future: download with account,
  extract per-iceberg melt+draft+thermal-forcing population, then the
  ΔT-dependence test can be replicated at iceberg level).

## 14. Enderlin14 analysis

- Retained at paper level (0.39 ± 0.17 m/day, cylinder; 0.41 ± 0.18, cone;
  10 icebergs; upper-bound idealized geometry). No individual iceberg values,
  temperature or current data accessible; uncertainty inseparable from the
  aggregate. No replacement of idealized geometry possible.

## 15. Moyer19 velocity constraint

- Mean iceberg translational speed 0.018 ± 0.002 (2017) / 0.023 ± 0.003
  (2018) m/s; max 0.14 ± 0.02 m/s; GPS-tracker mean 0.017 m/s.
- These are **u_ice**; the legacy effective velocity scale U_eq ≈ 0.30 m/s is
  larger than these translational speeds, but this is **not a direct U_rel
  comparison** (no ocean velocity). Statement corrected per M-3.

## 16. RH80 fit reference

- `R = 1.8e-2·(T+1.8)^1.5` m/day, S = 35, U = 0. Curve evaluation only
  (not 5 independent observations).
- Key information: (1) nonzero lateral melt at U = 0 →
  `NONZERO_BUOYANCY_OR_FREE_CONVECTION_COMPONENT`; (2) nonlinear temperature
  dependence `m ∝ ΔT^1.5`; (3) laboratory side melt. Not generalized to
  oceanic plume physics.

## 17. Velocity-resolved subset

`velocity_resolved_observations.csv`: cases with melt + ΔT + U_rel
simultaneously → **5 rows, ALL Russell-Head laboratory (U = 0 known)**.
**FIELD velocity-resolved cases: 0.**

> No velocity-resolved field observational cases with simultaneous melt,
> thermal forcing and relative velocity were recoverable from the existing
> public datasets.

This is the central negative result of the stage.

## 18. Temperature dependence

- RH80: exponent 1.5 (from the published relationship, **not fitted here**).
- Enderlin23: Thwaites submarine sensitivity 24 m/a/°C (= 0.0657 m/day/°C),
  i.e. a **submarine-total slope**; legacy lateral slope 0.0864 m/day/°C is
  1.3× the Thwaites slope and within the observed 0–100 m/a/°C range — a
  compatibility statement under the submarine definition, **not** validation.
- Independent-of-RH80 nonlinear temperature dependence: **not identifiable**
  (no other source with a ΔT series; Enderlin23 slope is a single linear
  regression).
- Field ΔT exponent: `TEMPERATURE_EXPONENT_NOT_IDENTIFIABLE` beyond RH80.

## 19. Velocity dependence

**NOT IDENTIFIABLE quantitatively.** No paired U_rel field cases. Qualitative
support exists (lab U^0.8 scaling; Antarctic shear hypothesis; Schild21
keel-linked melt) but no quantitative constraint. `VELOCITY_DEPENDENCE_NOT_IDENTIFIABLE`.

## 20. Depth dependence

- Schild21: hydrographic structure qualitative; keel-linked melt differences
  reported by the authors → `VELOCITY/DEPTH_DEPENDENCE_SUPPORTED_QUALITATIVELY`.
- Depth-resolved ΔT(z)/U(z) curves: **not recoverable** from public data
  (no numeric CTD table; no ADCP). `DEPTH_DEPENDENCE_NOT_IDENTIFIABLE`
  quantitatively.

## 21. Geometry constraint

`GEOMETRY_DISTRIBUTION_NOT_CONSTRAINED`: no observation measures the vertical
distribution of lateral retreat (sail vs draft). Schild21's reconstructed
geometry gives area-averaged rates (convention-free at rate level) but does
not separate the melt distribution. The full-height vs submerged convention
(factor 2·ρ_i/ρ_w = 1.77) remains unconstrained.

## 22. Side/basal separation

**NOT CONSTRAINED.** All field melt is `SUBMARINE_TOTAL` (side+basal). No
dataset separates sidewall recession from basal recession (Schild21 geometry
reconstruction gives volume loss / total submerged area). The model's lateral
vs basal distinction cannot be tested against any field observation.

## 23. Wave-erosion constraint

`WAVE_EROSION_NOT_CONSTRAINED`: no wave observations in any recovered
dataset; no verified primary wave-erosion equations (White 1980/Kubat 2007
unverified). The unverified "71 % wave erosion" Barents claim is excluded.

## 24. Parameterization comparison

Comparison matrix (`comparison_matrix.csv`) with explicit
`comparison_status`:

| status | cells | meaning |
| --- | --- | --- |
| DIRECT_COMPARABLE | 30 (5 RH80 rows × 6 models) | lateral lab melt with known ΔT and U=0; **curve evaluation** |
| BOUNDED | 8 (4 Enderlin23 × 2 legacy-family models) | legacy lateral vs submarine-total (lateral ≤ total test) |
| QUALITATIVE / INSUFFICIENT_INPUTS | rest | field cases lack ΔT or U_rel |

**Curve-evaluation diagnostics (RH80 lab, one fit):**

| model | bias [m/day] | note |
| --- | --- | --- |
| LEGACY_* | +0.198 | over-predicts low-ΔT (linear vs ΔT^1.5); matches at ~20 °C |
| BULK_FORCED / BIGG1997 | −0.56 | give 0 at U=0 — fail quiescent cases |
| BIGG_PLUS_BUOY | −0.34 | nonzero at U=0 via buoyant term; under-predicts |
| FITZMAURICE_PLUME | −0.26 | nonzero at U=0 via attached-plume branch |

These are diagnostics on a single published relationship, **not**
independent-sample validation, and do not select a formulation.

**Bounded comparison:** legacy lateral exceeds observed total submarine melt
in 3/4 Enderlin23 cold-shelf region cases — legacy over-predicts cold low-ΔT
conditions (consistent with the RH80 low-ΔT over-prediction).

## 25. Effective coefficients (corrected)

| quantity | definition | N | median [m/(s·K)] | vs production 1e-6 |
| --- | --- | --- | --- | --- |
| C_eff_lab_lateral | m_lateral/ΔT, RH80 fit evaluations | 5 points (1 fit) | 5.43e-7 | 0.54× |
| C_eff_submarine | m_submarine/ΔT, Enderlin23 region aggregates | 4 | 5.86e-7 | 0.59× |
| Thwaites slope (submarine) | 24 m/a/°C = 7.6e-7 | regression | 0.76× | range ~0–3.2e-6 |

**No mixed distribution.** The production coefficient is compatible with
these aggregate effective thermal sensitivities under the stated definitions;
this is **not** validation (field quantity is submarine, RH80 is a lab fit).

## 26. Uncertainty

- ENDERLIN14: symmetric ± (0.17/0.18 m/day).
- SCHILD21: rate spread (0.09–0.27) and geometry-induced area uncertainty
  (22–43 %, quoted) — no single σ.
- RH80: fit values without uncertainty (points figure-only).
- ENDERLIN23: regional maxima without uncertainty (individual dataset has
  per-iceberg uncertainties but was not retrieved).
- No σ fabricated; `melt_uncertainty = NA` where absent.

## 27. Statistical limitations

- No independent-sample statistics on mixed dependent observations
  (test-enforced).
- RH80 = curve evaluation; Schild21 = 2 independent icebergs with repeated
  estimates; Enderlin23 = 4 region aggregates (individual data pending);
  Enderlin14 = 1 aggregate; Moyer19 = velocity reference only.
- Leave-one-source-out was NOT APPLICABLE in 10.18B and remains so (single
  prediction-usable source: RH80).
- A fitted oceanic temperature exponent or velocity exponent is **not
  justified** by the data (`NOT_IDENTIFIABLE`).

## 28. Observational gap matrix

`observational_gap_matrix.csv` (variable × source, YES/PARTIAL/NO):

| variable | RH80 | Enderlin14 | Schild21 | Enderlin23 | Moyer19 |
| --- | --- | --- | --- | --- | --- |
| lateral melt | YES | NO | NO | NO | NO |
| submarine melt | NO | YES | YES | YES | NO |
| ΔT | YES | NO | NO | YES | NO |
| U_ice | YES(0) | NO | PARTIAL (derived) | NO | YES |
| U_ocean | NO | NO | NO | NO | NO |
| U_rel | YES(0) | NO | NO | NO | NO |
| depth-resolved T | NO | NO | PARTIAL (qualitative) | NO | NO |
| depth-resolved U | NO | NO | NO | NO | NO |
| draft | PARTIAL | NO | YES | PARTIAL | NO |
| full geometry | PARTIAL | NO | YES | NO | NO |
| side/basal separation | NO | NO | NO | NO | NO |
| wave data | NO | NO | NO | NO | NO |
| uncertainty | NO | YES | PARTIAL | NO | NO |

## 29. Future targeted observations

Design derived strictly from the gaps above. Target record (each quantity
needed because): `m_lateral or side recession` (direct lateral constraint),
`ΔT(z)` (temperature dependence, side-basal partition input), `U_ocean(z)`
+ `U_ice` (vector U_rel), `U_rel(z)` (velocity dependence), `draft`,
`submerged/side/basal area` (geometry convention + side-basal partition),
`time` (paired), `wave state` (wave erosion separation), `uncertainty`.
The minimal package: **GPS + drone SfM + multibeam sonar + repeat bathymetry
(iceberg) + CTD + ADCP/current meters (ocean) + wave buoy/altimeter**. A
Schild21-style campaign **plus ADCP and concurrent CTD profile tables** would
close the velocity and temperature gaps; a USAP-DC account download of
Enderlin23 601679 would upgrade the ΔT-dependence population from 4 region
aggregates to iceberg level.

## 30. Findings

| ID | Finding | Classification | Evidence | Confidence |
| --- | --- | --- | --- | --- |
| C-01 | RH80 provides ONE published lab fit; 5 temperature points are evaluations, not independent observations | VERIFIED | dataset design + tests | HIGH |
| C-02 | No field dataset provides simultaneous melt + ΔT + U_rel (FIELD velocity-resolved cases = 0) | VERIFIED | velocity-resolved subset | HIGH |
| C-03 | Actual U_rel cannot be reconstructed: no ocean-velocity (ADCP/current) data in any public dataset | VERIFIED | data-recovery audit | HIGH |
| C-04 | Nonzero lateral melt at U=0 (RH80) ⇒ `NONZERO_BUOYANCY_OR_FREE_CONVECTION_COMPONENT` required | VERIFIED (lab) | RH80 fit | HIGH |
| C-05 | Lab temperature dependence nonlinear (ΔT^1.5); linear legacy over-predicts low-ΔT (up to 3.6× at 1.8 K) | VERIFIED (lab) | RH80 fit | HIGH |
| C-06 | Legacy lateral exceeds observed total submarine melt in 3/4 Antarctic cold-shelf region cases | BOUNDED | Enderlin23 + bounded comparison | MEDIUM |
| C-07 | C_eff_lab_lateral (0.54× production) and C_eff_submarine (0.59×) separate; production compatible with both under stated definitions, not validated | RESEARCH_FINDING | corrected C_eff | MEDIUM |
| C-08 | Legacy effective scale U_eq ≈ 0.30 m/s > observed iceberg translational speeds (0.018–0.023 m/s); NOT a U_rel comparison | QUALITATIVE | Moyer19/Schild21 u_ice | MEDIUM |
| C-09 | Velocity dependence NOT IDENTIFIABLE quantitatively (no paired U_rel) | NOT_IDENTIFIABLE | §17/19 | HIGH |
| C-10 | Field temperature exponent beyond RH80: NOT_IDENTIFIABLE (Enderlin23 slope is submarine and linear) | NOT_IDENTIFIABLE | §18 | HIGH |
| C-11 | Depth dependence supported qualitatively (Schild21 keel-linked melt; hydrographic structure) but not quantitatively | QUALITATIVE | Schild21 | MEDIUM |
| C-12 | Geometry (full-height vs submerged) NOT CONSTRAINED | NOT_CONSTRAINED | §21 | HIGH |
| C-13 | Side/basal separation NOT CONSTRAINED (all field melt submarine total) | NOT_CONSTRAINED | §22 | HIGH |
| C-14 | Wave erosion NOT CONSTRAINED | NOT_CONSTRAINED | §23 | HIGH |
| C-15 | Enderlin23 individual-iceberg dataset exists (USAP-DC 601679) but not anonymously retrievable — ΔT-dependence population upgrade deferred | QUALITATIVE (gap) | §13/§5 | HIGH |
| C-16 | The 30-day mass-loss range (1.3–26.1 %, 10.18A) is NOT narrowed by observations; only the forced-convection-only end is inconsistent with quiescent lab evidence, and legacy over-predicts cold low-ΔT | BOUNDED | comparison matrix | MEDIUM |

## 31. Scientific decision

**OPTION D — multiple formulations remain plausible, but the existing
observations provide useful bounds** (with elements of OPTION E: several
quantities remain unconstrained). Specifically:

- bounds: legacy is compatible with aggregate effective thermal sensitivities
  but over-predicts cold low-ΔT (lab + Antarctic shelf); forced-convection-
  only formulations are inconsistent with nonzero quiescent melt;
- unresolved: velocity dependence (no paired U_rel), geometry distribution,
  side/basal partition, wave erosion, field ΔT exponent.

**OPTION A/B/C are not selected** — no formulation is observationally
strongly supported or rejected at field scale, and no regime-specific
formulation is quantitatively established.

## 32. Production implications

**Production physics: KEEP_CURRENT.** No production change is justified or
performed (git diff `src/`/`test/` empty). Any future change (e.g., adding a
buoyancy/free-convection term, nonlinear ΔT dependence, geometry-convention
resolution) is documented as a proposal for a separate, explicitly approved
physics stage, contingent on the velocity-resolved or ΔT-population upgrades
identified in §29.

## 33. Reproducibility

```bash
# Analysis + figures + outputs
conda run -n iceberg-thermodynamic-model \
    python python/analysis/stage10_18c_existing_observations.py
# writes data/output/stage10.18c/ (independence_groups.csv,
# comparison_matrix.csv, velocity_resolved_observations.csv,
# observational_gap_matrix.csv, summary.json, reproducibility.log,
# plots/fig01..fig10.png)

# Tests
conda run -n iceberg-thermodynamic-model \
    python python/tests/test_stage10_18c_observations.py

# Full Python suite
for t in python/tests/test_*.py; do conda run -n iceberg-thermodynamic-model python "$t"; done
```

Dataset (versioned): `data/validation/observations/stage10.18c/{observations,
sources,provenance}`. The script fails loudly if the dataset is missing
(no silent mean substitution).

## 34. Tests

`python/tests/test_stage10_18c_observations.py` — **61 checks PASS**: schema,
independence (RH80 not independent; Schild21 groups), melt definitions,
velocity (u_ice never promoted to u_rel; vector combination analytic),
temperature conventions (no silent T+1.8 for field), statistics rule
(dependent observations excluded from independent RMSE), C_eff separation,
provenance. All 15 prior Python suites re-run PASS; `py_compile` clean;
fpm battery unchanged (no Fortran change).

## 35. Classification

| Item | Classification |
| --- | --- |
| RH80 = one lab fit (not 5 independent obs) | VERIFIED |
| No field velocity-resolved cases (melt+ΔT+U_rel) | VERIFIED |
| U_rel reconstruction impossible from public data | VERIFIED |
| NONZERO_BUOYANCY_OR_FREE_CONVECTION_COMPONENT at U=0 | VERIFIED (lab) |
| Lab ΔT^1.5 nonlinearity; legacy over-predicts cold low-ΔT | VERIFIED (lab) / BOUNDED (field) |
| C_eff_lab vs C_eff_submarine separated; production compatible, not validated | RESEARCH_FINDING |
| Velocity dependence | NOT_IDENTIFIABLE (quantitatively) |
| Field temperature exponent beyond RH80 | NOT_IDENTIFIABLE |
| Depth dependence | QUALITATIVE |
| Geometry / side-basal / wave | NOT CONSTRAINED |
| Production physics | UNCHANGED (KEEP_CURRENT) |
| Stage decision | OPTION D (bounds) / elements of OPTION E |