# Iceberg basal/submarine melt — observational dataset provenance (Stage 10.8.2)

Data file: `iceberg_basal_melt_observations.csv` (19 records).

Purpose: independent, verified observational anchors to test the production
basal-melt closure (EOS-80 freezing point + flat-plate Re/Nu forced-convection
heat transfer). This is **validation, not calibration**: no coefficient is fit
here.

## Rule for numbers

Every value in the CSV is either (a) taken verbatim from a published source or
(b) a *documented derived quantity* (unit conversion, `T` chosen so that
`T-Tf = dT`, or a stated reference assumption `U_ref`/`L`). No observational
number is invented. Missing quantities are `NaN`.

`tier` groups rows as `lab-primary`, `field-primary`, `synthesis-derived`,
`rs-derived`. `melt_component` is `basal` when the source reports bottom melt
and `submarine` when the source reports the melt of the submerged surface
(basal + side; the dominant term is basal).

## Row-by-row provenance

| record_id | Source | DOI (verified via Crossref) | Values -> CSV | Assumptions |
|---|---|---|---|---|
| RH_0C..RH_18C | Russell & Head 1980, *Annals of Glaciology* 1:119-122 | 10.3189/S0260305500017092 | Lab: `R = 1.8e-2*(T+1.8)^1.5` m/day (quiescent tank, S=35), T = 0/2/5/10/18 degC -> 0.0434/0.1333/0.3192/0.7296/1.5859 m/day | `u_rel=0`; `L_char=1 m` lab block; basal~(side). These rows exercise the **natural-convection gap** (production gives ~0). |
| NJ80_dT2/4/8 | Neshyba & Josberger 1980, *JPO* 10:1681-1685 | 10.1175/1520-0485(1980)010<1681:OTEIAI>2.0.CO;2 | Best-estimate synthesis: 5/17/55 m/yr at dT = 2/4/8 degC -> 0.013699/0.046575/0.150685 m/day | `T` s.t. `T-Tf(S=35,z=50m)=-1.96022`; `u_rel_ref=0.1 m/s`, `L_char=50 m` (reference choices, not source values) |
| KW84_DUrville | Keys & Williams 1984, *J. Glaciol.* 30:218-222 | 10.3189/S0022143000005955 | T=-1 degC, S=34, U~0.1 m/s; 0.06+/-0.01 m/day (range 0.04-0.08) | `u_rel=0.1` (reported); `L_char=20 m` draft estimate from 40-100 m length |
| END14_Sermilik | Enderlin & Hamilton 2014, *J. Glaciol.* 60(224):1084-1092 | 10.3189/2014JOG14J085 | Mean submarine melt 0.39 m/day (+/-0.18), Sermilik | No per-row ocean T/U -> `NaN` forcing; inverse-U only |
| END16_* | Enderlin, Hamilton, Straneo & Sutherland 2016, *GRL* 43(21) | 10.1002/2016GL070718 | Ilulissat shallow/deep 0.16 (0.11-0.21) / 0.50 (0.18-0.83); Sermilik 0.17 (0.05-0.29) / 0.49 (0.31-0.67) m/day | `NaN` forcing; inverse-U only |
| END23_* | Enderlin et al. 2023, *J. Glaciol.* 69(278):1718-1728 | 10.1017/jog.2023.54 | Regional maxima m/yr -> m/day: WAP 0.137, WAIS 0.1096, EAIS 0.0137, EAP 0.0137 | Regional maxima, not central estimates; `NaN` forcing; inverse-U only |
| OPEN_SO_context | open-Southern-Ocean large-iceberg upper bound (Enderlin et al. 2023 review) | -- | ~1.5 m/day (~500 m/yr) upper bound | **Context row**, `include_in_metrics=False` |

## Verification method

- 1980 Cambridge papers: full texts extracted from open-access PDFs (working
  copies in /tmp, not committed); quantitative anchors transcribed from text.
- Modern papers: DOIs resolved and bibliographic metadata confirmed through the
  Crossref REST API (`query.bibliographic`), including corrected DOIs for
  Josberger & Neshyba 1980 (`10.3189/s0260305500017080`) and Keys & Williams
  1984 (`10.3189/S0022143000005955`).
- Budd, Jacka & Morgan 1980 (10.3189/S0260305500017079): numeric melt bounds
  are figure-only and NOT OCR-recoverable -> excluded from CSV numerics; used
  in report context only.
- Uncertainty is transcribed where the source reports it; absent -> `NaN`.

## Selected vs. otherwise

See the 12-section report
`docs/validation/stage10.8.2_observational_validation.md` for selection rules
(study must report a repeatable melt rate of the submerged surface of icebergs;
Rignot et al. 2010 calving-face rates are excluded as glacier-terminus,
plume-driven values; Budd/Jacka/Morgan and Orheim 1980 are excluded as
decay/breakage statistics rather than clean basal-melt rates).