# Stage 10.18C observational dataset — provenance

Directory: `data/validation/observations/stage10.18c/` (version-controlled).

Files:
- `observations.csv` (18 rows) — reanalyzed dataset with explicit independence,
  melt-definition and velocity classification (Stage 10.18B corrections applied);
- `sources.csv` — source metadata (see below);
- `provenance.md` — this file.

## Rule for numbers

Every numerical value is either (a) verbatim from the cited published source
(fetched full text during Stage 10.18B/C), or (b) a documented derived
quantity. No value is fabricated. Missing values are `NA`. `data_quality` in
PRIMARY_SOURCE / AUTHOR_DATA / SUPPLEMENTARY_DATA / FIGURE_DIGITIZED /
MODEL_DERIVED / UNVERIFIED — only the first three may enter quantitative
validation.

## Row-by-row provenance

| case group | Source (DOI) | Value -> CSV | Assumptions / transformations |
|---|---|---|---|
| RH80_*C (5 rows) | Russell-Head 1980, Ann. Glaciol. 1:119-122, 10.3189/S0260305500017092 | Fit `R = 1.8e-2*(T+1.8)^1.5` m/day at T = 0/2/5/10/18 °C, S=35 -> 0.0434/0.1333/0.3192/0.7296/1.5859 m/day | `independent_case=FALSE` (ONE published fit); `observation_type=PUBLISHED_FIT_EVALUATION`; `delta_T=T+1.8`; `u_rel_speed=0.0` (quiescent by experiment); L=1.0 m, D=0.5 m approximate block geometry; side = mean recession of submerged walls; basal and mean-side similar |
| ENDERLIN14_SERMILIK_CYL/CONE | Enderlin & Hamilton 2014, J. Glaciol. 60(224), 10.3189/2014JoG14J085 | 0.39 ± 0.17 (cylinder) / 0.41 ± 0.18 (cone) m/day | `observation_type=INDIRECT_SUBMARINE`; `melt_definition=SUBMARINE_TOTAL` (side+basal, area-averaged, upper bound); aggregate over 10 icebergs (`independent_case=FALSE`); `delta_T=NA`, `u_rel=NA` (not reported with the values); dates 2011-2013 summers |
| SCHILD21_A_* / B_* (6 rows) | Schild et al. 2021, GRL 48(3), 10.1029/2020GL089765 (open copy: climatechange.umaine.edu grl61898.pdf) | A: L=733 m, keel=386 m, h~35 m; B: L=518, keel=255, h~22.5 m; melt (GPS-9d) 0.16/0.10, (GPS-6d) 0.18/0.09, (drone-6d) 0.27/0.15 m/day; vol loss A 1.99e5, B 8.59e4 m3/d | `INDIRECT_SUBMARINE`, `SUBMARINE_TOTAL` (volume loss / reconstructed area; calving <4%); 2 independent icebergs (groups A/B); repeated estimates within group (`independent_case=FALSE`); `ice_speed` A=0.045, B=0.072 m/s **derived** from reported track lengths (35/56 km over 9 days) — documented derivation, NOT from a reported speed table; `u_rel_speed=NA` (no ocean velocity; no ADCP dataset found); `delta_T=NA` (13 CTD casts exist 16-21 Jul 2017 but no numeric T/S table extracted; qualitative hydrography: Polar Water 10-150 m, Atlantic Water below ~150 m, warming below ~250 m) |
| ENDERLIN23_* (4 rows) | Enderlin et al. 2023, J. Glaciol. 69(278), 10.1017/jog.2023.54 | max ~50/40/5/5 m/a -> 0.137/0.110/0.014/0.014 m/day (WAP/WAIS/EAIS/EAP) | `INDIRECT_SUBMARINE`, `SUBMARINE_TOTAL`; regional maxima (aggregates, `independent_case=FALSE`); `delta_T` = reported thermal-forcing range midpoint (WAP/WAIS 1.5 K, range 1-2 K; EAIS/EAP 0.5 K, range 0.3-0.7 K); Thwaites slope 24 m/a per degC (R2=0.80) kept as `SUBMARINE_TOTAL` thermal sensitivity (NOT lateral); **individual-iceberg dataset EXISTS at USAP-DC 10.15784/601679 (Antarctic-iceberg-csvs.zip) but requires a USAP-DC account — not anonymously retrievable in this session; regional-maximum treatment retained (documented gap for future work)**; `u_rel_speed=NA` |
| MOYER19_FJORD_VELOCITY | Moyer et al. 2019, GRL 46, 10.1029/2019GL082309 | mean iceberg speed 0.018 ± 0.002 (2017) / 0.023 ± 0.003 (2018) m/s; max 0.14 ± 0.02; GPS-tracker mean 0.017 m/s | `observation_type=VELOCITY_REFERENCE` (NOT a melt observation); `ice_speed` only — **u_ice ≠ u_rel** (no paired ocean velocity); no machine-readable dataset found |

## Data-recovery audit (access date 2026-09-18)

- Schild21 supplementary data: Arctic Data Center records 10.18739/A22V2CB5M
  (GPS/SfM), 10.18739/A2QF8JK6B (multibeam), 10.18739/A2NG4GS8C (CTD),
  10.18739/A2KP7TS5N (2017-2019 combined) — raw point clouds/casts; **no tidy
  derived geometry/melt table; no ADCP/current-meter data**.
- Enderlin23 data product: USAP-DC dataset 601679, DOI 10.15784/601679,
  `Antarctic-iceberg-csvs.zip` (per-iceberg CSV: coordinates, dates, median
  surface elevation, density, volume, surface area, draft, submerged area,
  volume change, submarine meltwater flux) — **identified, not downloaded**
  (account-gated; README retrieved).
- Enderlin14 / Moyer19: no public machine-readable associated datasets found.
- Wiley (GRL) publisher pages return HTTP 403; author/open copies used
  (documented). Firecrawl unavailable (IP-based block); webfetch/curl used.

## Independence classification (see observations.csv)

| independence_group | source | independent units | note |
|---|---|---|---|
| RH80_SINGLE_FIT | RH80 | 1 (one published fit) | 5 temperature evaluation points, NOT independent |
| ENDERLIN14_REGION | ENDERLIN14 | 1 (aggregate) | 10 icebergs per paper; paper-level value |
| SCHILD21_ICEBERG_A | SCHILD21 | 1 | one independent iceberg |
| SCHILD21_ICEBERG_B | SCHILD21 | 1 | one independent iceberg |
| ENDERLIN23_REGION_* (4) | ENDERLIN23 | 4 (regional aggregates) | individual-iceberg data at USAP-DC (not retrieved) |
| MOYER19_FJORD | MOYER19 | 0 (velocity reference) | not a melt observation |

Independent observational units for melt: **8** (1 RH80 fit + 1 Enderlin14
aggregate + 2 Schild21 icebergs + 4 Enderlin23 region aggregates). No row is
falsely marked independent.