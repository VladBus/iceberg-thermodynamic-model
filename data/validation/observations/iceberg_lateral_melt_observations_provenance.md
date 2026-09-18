# Iceberg lateral/side-melt observations — dataset provenance (Stage 10.18B)

Data files (curated, versioned):
- `iceberg_lateral_melt_observations.csv` (17 case rows)
- `iceberg_lateral_melt_observational_sources.csv` (9 sources)

Purpose: independent, verified observational anchors to discriminate the
Stage 10.18A lateral-melt parameterizations (legacy constant, bulk forced
convection, Bigg1997, Bigg+buoyant, FitzMaurice plume) and to test whether
observational evidence can narrow the 30-day mass-loss range (1.3–26.1 %)
established in Stage 10.18A. This is **discrimination, not calibration**: no
coefficient is fit to the data.

## Rule for numbers

Every value in the CSV is either (a) taken verbatim from the cited published
source (fetched full text during the Stage 10.18B audit), or (b) a documented
derived quantity (unit conversion, or the published relationship evaluated at
the reported temperature). No observational number is invented. Missing
quantities are `NA`. Values that could NOT be verified from a primary source
are excluded from the dataset (documented below under "Excluded / unverified").

## Verified primary sources (fetched full text)

| source_id | Citation | DOI | Verified content -> CSV |
|---|---|---|---|
| RH80 | Russell-Head 1980, Annals of Glaciology 1:119-122 | 10.3189/S0260305500017092 | Lab block side/basal melt, S~35; published fit `R = 1.8e-2*(T+1.8)^1.5` m/day; evaluated at T=0/2/5/10/18 degC -> 0.0434/0.1333/0.3192/0.7296/1.5859 m/day (fit-derived rows; individual figure points not digitized) |
| ENDERLIN14 | Enderlin & Hamilton 2014, J. Glaciol. 60(224) | 10.3189/2014JoG14J085 | Sermilik summer area-averaged submarine melt ~0.39 m/day (0.38±0.17 cylinder, 0.41±0.18 cone); ~144 m/a; 10 icebergs; DEM differencing; upper-bound (idealized shapes) |
| SCHILD21 | Schild et al. 2021, GRL 48(3) | 10.1029/2020GL089765 | Sermilik July 2017: iceberg A L=733 m keel=386 m height~35 m; B L=518 m keel=255 m height~22.5 m; overall melt (volume loss / reconstructed area): GPS 9d 0.16/0.10, GPS 6d 0.18/0.09, drone 6d 0.27/0.15 m/day; calving <4 % |
| ENDERLIN23 | Enderlin et al. 2023, J. Glaciol. 69(278) | 10.1017/jog.2023.54 | 15 Antarctic sites 2011-2022: max melt ~50 m/a (WAP), ~40 (WAIS), ~5 (EAIS), ~5 (EAP) m/a -> 0.137/0.110/0.014/0.014 m/day; Thwaites melt-vs-thermal-forcing sensitivity 24 m/a per degC (R2=0.80), range ~0-100 m/a/degC; "temperature-only parameterizations unlikely to be accurate"; open-ocean large icebergs up to ~1.5 m/day (~500 m/a) cited |
| MOYER19 | Moyer et al. 2019, GRL 46 | 10.1029/2019GL082309 | Sermilik iceberg velocities: mean 0.018±0.002 (2017) / 0.023±0.003 (2018) m/s; max 0.14±0.02 m/s; GPS-tracker mean 0.017 m/s; used as U_rel magnitude reference only |

## Derived quantities and documented assumptions

- RH80 rows: `delta_T_K = T_water + 1.8` (the published fit uses `T+1.8`
  with -1.8 degC as the freezing/onset temperature); `L_m = 1.0`, `D_m = 0.5`
  (block ~1:2:4, lengths up to 1 m — geometry approximate, documented);
  melt values from the published relationship (fit-derived), matching the
  Stage 10.8.2 convention for the same source.
- ENDERLIN23 rows: `delta_T_K = 1.5` for WAP/WAIS (paper: T ~1 degC near
  surface, ~2 degC at depth, depth-averaged thermal forcing rarely >2 degC —
  midpoint documented), `0.5` for EAIS/EAP (cold shelf waters, thermal
  forcing ~0.3 K in the Weddell-like sites). These are **reported-range
  midpoints, not case-level measured driving**; flagged
  `COMPARABLE_AFTER_NORMALIZATION`.
- ENDERLIN23 melt values: maxima `m/a -> m/day` via /365 (0.137/0.110/0.014/0.014).
- `delta_T_K`/`u_rel_m_s` for Sermilik cases (ENDERLIN14, SCHILD21) left `NA`:
  concurrent CTD temperature and relative velocity are not reported in the
  extracted text (13 CTD profiles exist in SCHILD21 but values not extracted).

## Excluded / unverified (documented gaps — NOT entered as cases)

- FitzMaurice et al. 2017 Sermilik model side melt 0.06-0.10 m/day: MODEL_DERIVED
  (their parameterization applied to Sermilik), kept as a model reference only.
- Grand Banks: no independently measured thermal sidewall-melt dataset verified;
  Kubat et al. 2007 field comparison is calving intervals; wave erosion dominates
  in the operational model but is not separable from observations here.
- Wave erosion: Cenedese & Straneo 2023 parameterized maximum 0.5-1.0 m/day
  (MODEL_DERIVED summary, cites El-Tahan et al. 1987 — original not fetched);
  White et al. 1980 / Kubat et al. 2007 wave-erosion equations not verifiable
  from primary sources -> wave erosion remains **NOT CONSTRAINED**.
- Russell-Head individual experimental points (Figure-only) and salinity
  series (17.5-35 per-mille, Figure 5): not digitized -> not entered.
- Barents Sea "71 % wave erosion" claim (Shtokman studies): primary source not
  identified during the audit -> **UNVERIFIED**, excluded.
- Sulak et al. 2017, Mountain 1980, Sodhi & El-Tahan 1980, Diemand 1984:
  no case-level side-melt numbers verified from primary text -> excluded.

## Directness / comparability conventions

- DIRECT: quantity measured directly (lab dimensional melt).
- INDIRECT: melt recovered from volume loss / area (DEM/GPS/sonar) — the
  "melt rate" is an area-averaged normal retreat of the submerged surface
  (side+basal); for lateral-only comparison it is an upper bound.
- MODEL_DERIVED: parameterization summaries / model outputs (kept for context,
  excluded from prediction metrics).
- comparability:
  - DIRECTLY_COMPARABLE — lateral melt rate with known driving (RH80 lab);
  - COMPARABLE_AFTER_NORMALIZATION — submarine (side+basal) with reported
    thermal forcing range (ENDERLIN23);
  - QUALITATIVE_ONLY — missing driving/velocity or definition mismatch
    (Sermilik submarine cases, velocity constraint row);
  - NOT_COMPARABLE — model outputs / different quantity.

## Full-text access note

Wiley (GRL) publisher pages returned HTTP 403; SCHILD21 full text was fetched
from the author-hosted open copy (University of Maine repository); ENDERLIN14
and ENDERLIN23 full text from Cambridge Core / DOI redirect; RH80 from
Cambridge Core. Firecrawl was unavailable (IP-based block); webfetch used.