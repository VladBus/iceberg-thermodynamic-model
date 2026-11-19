# Stage 12.22 — Enderlin23 Taylor diagrams and bias diagnostics

**Date:** 2026-11-18  
**Status:** COMPLETE (validation only; no calibration, no model runs)  
**Scope:** Existing Stage 12.15 Enderlin23 hindcast, re-analysed at the
independent-case level. The model, its constants, and its numerical schemes
were not changed.

## Stage 0 — reconnaissance (answers first)

### 1. Where are the Enderlin23 model results?

The analysed results are:

- `data/validation/stage12.15/enderlin_current2/enderlin23_hindcast_results.csv`
  (190 rows) — per-case observed and modeled submarine melt rates.
- Individual time-series inputs:
  `data/validation/stage12.15/enderlin_current2/<case_id>_voxel.nc` (190
  files; `mass`, `draft`, `ocean_T_draft`, `ocean_S_draft`, etc.).
- Trajectory/initial-state manifest:
  `data/validation/stage12.15/enderlin_trajectory_manifest.csv` (190 rows).

Coverage is 190 cases: 125 WAP and 65 WAIS. The grid is the **8³ test grid
(12.5 m voxels)**, not 100³/1 m. The model is the current Stage 12.15
voxel/CN configuration (`VOXEL_ENABLED=true`, prescribed trajectory); wave
erosion is OFF. The result CSV was written on 2026-11-11 on the current-code
Stage 12.15 branch. The committed analysis is `92bcf8c` (2026-11-12); the
exact executable/build hash is not embedded in the CSV, so this is documented
provenance rather than a bit-reproducible binary record.

The ocean forcing is the locally staged **GLORYS12 0.083° daily** product
`GLOBAL_MULTIYEAR_PHY_001_030` (202311 native-S3 acquisition), seven site
files, 32.2 MB total. There is **no Antarctic ERA5 atmosphere** in this run;
the atmosphere is the documented constant/cold boundary condition. Surface and
vapour losses are reported separately and are excluded from the validation
quantity.

The per-case CSV does contain a model melt-rate column:
`modeled_melt_rate_voxel` [m/day], plus the component mass losses and mean
wetted area.

### 2. How was each case initialized?

- Rectangular-prism initial shape.
- `L = W = √surface_area`; `H = volume_i / surface_area` for 141 cases.
- For 49 CG cases where raw `volume_i` is inconsistent with
  `surface_area`/`draft`, `H = draft·ρ_w/ρ_i` (documented Stage 12.7a
  `H0_rule`; not a new choice).
- Initial ice temperature `T_ice = −10 °C` (documented assumption, not
  observed).
- The observed start/end positions are linearly interpolated daily; dynamics
  are disabled in prescribed-trajectory mode. GLORYS12 T/S/u/v are interpolated
  to the iceberg draft, time, and prescribed position; the nearest wet cell
  within 0.5° is used at land/NaN ice-front cells.
- No calving, wave erosion, sea-ice drag, or tides.

### 3. Are the observed and modeled quantities the same?

Yes, after applying the metric definitions below.

- All 743 observation rows have `melt_definition = SUBMARINE_TOTAL`.
- Observed rate is exactly
  `melt_rate = volume_change_rate / submerged_area` [m/day]. This was checked
  row-by-row (maximum relative discrepancy `7.1e-14`).
- Observed 1σ uncertainty is
  `σ_obs = |volume_change_uncert| / submerged_area` [m/day]. The file has no
  negative uncertainties in the 190-case set. Median `σ_obs` is
  `0.00714 m/day` (25.9% of the median observed rate).
- Model rate is
  `(basal + lateral + wave) / ρ_ice / (mean_wet_area × duration) × 86400`
  [m/day]. `ρ_ice = 916.7 kg m⁻³`; `wave = 0` in these runs. Surface and
  vapour mass losses are excluded, matching `SUBMARINE_TOTAL`. The stored
  column reproduces from the component masses to machine precision.
- This is a **mass- loss / mean-wetted-area** rate, not a point melt rate and
  not a side-only rate. No definition correction was needed; only the metric
  analysis was added.

### 4. Which cases ended early?

None. All 190 rows have `status=OK`; no grounding or out-of-domain stop is
recorded in this prescribed run. Final model mass is 53.3–99.7% of initial
mass; no case reaches the 1% mass threshold. The metric therefore uses the
full observed interval for every case. This is a property of the prescribed
hindcast, not evidence that grounding is absent in free-drift runs.

### 5. Is temperature forcing available per case?

Yes. `mean_delta_t_voxel = T_w − T_f` at the draft is stored for every case
(mean 2.03 °C; range 0.243–3.525 °C). The per-step `ocean_T_draft`,
`ocean_S_draft`, and `T_ice` are also in the 190 NetCDF files, so the forcing
can be reconstructed without new GLORYS extraction. The analysis uses the
stored mean; no new forcing was generated.

### Missing / caveats in the input

- The observation table has **743** rows with `independent_case=True`; the
  **190** cases are the Stage 12.15 duration-filtered hindcast subset
  (`time_separation_days ≤ 120`). There are no model runs for the other 553
  observations, so this report does not claim them as matched cases.
- The exact model binary commit is not encoded in the result file.
- Only seven `independence_group` values exist after the 190-case filter.
  WAIS is one group; all WAP sites are separate groups. Cluster CIs for
  single-group strata cannot be estimated.
- There is no per-case observed `T_w`, velocity, or ice temperature; the
  forcing is model/reanalysis, not in-situ.

## 1. Matched table

`docs/wiki/stages/stage12/evidence/stage12.22/matched_cases.csv` contains one
row per case with:

`case_id`, `site`, `region`, `independence_group`, observed rate and
uncertainty [m/day], model rate [m/day], duration [d], `surface_area` [m²],
`draft` [m], `delta_t` [°C], `final_mass_pct`, and `early_stop`.

All rates are m/day. The 190-case table has no missing model or observation
rates. No calibration or model rerun was performed. The previous full 190-case
hindcast wall time was 992 s (≈5.2 s/case); no new run was justified.

## 2. Metrics

For rates `o_i` and `m_i`, with `s_o` and `s_m` the sample standard
deviations (`ddof=1`):

- `bias = mean(m_i − o_i)`
- `median ratio = median(m_i/o_i)`
- `mean log10 ratio = mean(log10(m_i/o_i))`
- `sd log10 ratio = sd(log10(m_i/o_i))`
- `MAE = mean|m_i − o_i|`; `RMSE = sqrt(mean((m_i − o_i)²))`
- `MAE_log10`, `RMSE_log10` use `log10` rates.
- Pearson, Spearman, and Kendall are computed on raw rates; `Pearson_log10`
  uses `log10` rates.
- `σ_model/σ_obs = s_m/s_o`
- `CRMSE/σ_obs = sqrt(mean[((m_i − mean m) − (o_i − mean o))²])/s_o`
- The log-space analogs use `log10` rates.

The **95% confidence intervals** are percentile intervals from a **cluster
bootstrap over `independence_group`** (5,000 draws, replacement, fixed seed
`122022`). This preserves within-group dependence but gives only seven
clusters overall and six for WAP; WAIS and every individual site have a single
cluster, so their interval is reported as unavailable rather than fabricated.

The **observation-noise ceiling** is a Monte Carlo expectation: independently
perturb each observation by `N(0, σ_obs_i)`, recompute the correlation with the
unperturbed observations, and average 5,000 draws. It assumes independent
Gaussian 1σ errors, no correlated systematic error, and no error in the model
forcing. It is an optimistic ceiling for any model, not a model score.

### Overall metrics

| Metric | Linear | log10 |
| --- | ---: | ---: |
| N / independence groups | 190 / 7 | 190 / 7 |
| Median observed / model [m/day] | 0.0383 / 0.0210 | — |
| Bias (mean model − obs) [m/day] | −0.0219 [−0.0297, −0.0078] | — |
| Median model/obs ratio | 0.540 [0.452, 1.013] | 0.540 [0.452, 1.013] |
| Mean log10(model/obs) | — | −0.218 [−0.321, 0.003] |
| SD log10(model/obs) | — | 0.451 [0.384, 0.477] |
| MAE [m/day] | 0.0287 [0.0184, 0.0348] | — |
| RMSE [m/day] | 0.0399 [0.0287, 0.0460] | — |
| MAE log10 | — | 0.400 [0.309, 0.440] |
| RMSE log10 | — | 0.500 [0.386, 0.546] |
| Pearson | 0.042 [−0.301, 0.394] | 0.154 [−0.271, 0.628] |
| Spearman | 0.156 [−0.274, 0.627] | 0.156 [−0.274, 0.627] |
| Kendall | 0.117 [−0.186, 0.433] | 0.117 [−0.186, 0.433] |
| σ_model/σ_obs | 0.412 [0.202, 0.695] | 0.585 [0.386, 0.837] |
| CRMSE/σ_obs | 1.062 [0.933, 1.237] | 1.075 [0.792, 1.392] |
| Observation-noise ceiling (r) | 0.941 | 0.558 |

### Regions

| Stratum | N | groups | median ratio | mean log10 ratio | Pearson log10 | σ ratio log10 | noise ceiling log10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| WAP | 125 | 6 | 0.650 [0.464, 1.258] | −0.136 [−0.263, 0.145] | 0.336 [−0.320, 0.708] | 0.513 [0.353, 0.713] | 0.561 |
| WAIS | 65 | 1 | 0.446 (no cluster CI) | −0.375 (no cluster CI) | −0.199 (no cluster CI) | 0.703 (no cluster CI) | 0.791 |

Site table (n ≥ 8) is in
`docs/wiki/stages/stage12/evidence/stage12.22/metrics_by_region.csv`.
The sites are BG n=4, CG n=42, HG n=21, LG n=9, SG n=35, TG n=65, WG n=14;
BG is reported but excluded from the site Taylor points because n<8.

## 3. Figures

All figures are PNG in
`docs/wiki/stages/stage12/figures/stage12.22/`; the six matching vector PDFs
are in `data/validation/stage12.22/journal_pdf_vectors.zip` (outside git).
The manifest is `figures_manifest.csv`.

- **T1** Taylor diagram, log10 rates: observed on the axis; All, WAP, WAIS,
  CG, HG, SG, TG and WG (8 points, cap respected); normalized σ radius, r arcs,
  normalized CRMSE contours, observation-noise arc, and bootstrap crosses.
  WAIS and single-site points have no cluster CI.
- **T2** the same Taylor construction on linear rates. The noise ceiling is
  0.941 in linear space, versus 0.558 for log10.
- **B1** log-log scatter with 1:1, factor-2/factor-10 guides, region colour,
  uncertainty-scaled markers, N, median ratio, Pearson(log10), and Spearman
  with cluster CIs.
- **B2** histogram and ECDF of log10(model/obs), zero and median lines, median
  ratio with CI, and WAP/WAIS boxplots.
- **B3** median log10 ratio versus thermal forcing, size (`√surface_area`),
  duration, and region; binned medians have 95% bootstrap bars.
- **B4** independence-group mean observed and model rates, with 95% CI of the
  mean. This reduces individual-iceberg noise but does not create new
  independent groups.
- **L1 is intentionally omitted.** The Stage 10.8.2 basal/lateral literature
  tables contain lab, Sermilik, regional-maximum and synthesis-derived values;
  there are no matched model runs at their forcing/geometry, and no new runs
  were allowed. A like-for-like L1 comparison would conflate model and
  observation conditions, so it is not drawn.

## 4. Results and interpretation

**Good.** The model median is a factor 1.85 below the observed median, but it
is not a gross order-of-magnitude failure: the median ratio is 0.540 and the
bias is only −0.0219 m/day. The median-ratio confidence interval is wide
(0.452–1.013) because group-level resampling sees only seven clusters.

**Bad.** The model is too smooth: `σ_model/σ_obs = 0.412` in linear space
(0.585 in log10), while `CRMSE/σ_obs ≈ 1.06–1.07`. Pearson(log10) is 0.154
(CI includes zero); Spearman is 0.156 (CI −0.274 to 0.627). The model does not
reproduce the observed rank ordering at a useful confidence level.

**Where it is systematically biased.** The median log10 ratio is +0.118 for
the smallest size quartile (`√A ≤ 170 m`) and −0.290, −0.385, and −0.399 for
the next three quartiles. This is a clear size-dependent under-melt, not a
uniform multiplicative offset. By region, WAP has median ratio 0.650 and log
mean −0.136; WAIS has median 0.446 and log mean −0.375. The WAIS result is one
cluster, so its CI cannot be separated from site-level dependence. Thermal
forcing does not produce a monotonic binned bias (−0.421, −0.186, −0.206,
−0.279 across quartiles), so a simple “more ΔT → more melt” correction would
not explain the residual.

**Against the noise ceiling.** The observed-noise ceiling is 0.558 in log10:
if the quoted 1σ errors were the only error source, a perfect model could
still correlate at most about 0.56 with this observed vector. The model's
0.154 is below that ceiling, so observation noise alone does not explain the
low rank correlation; however, the ceiling calculation assumes independent
Gaussian errors and does not include correlated representation error.

**What not to do.** Do not tune `K_T`, `K_S`, `γ_free`, or `melt_cap` to these
plots. The size-dependent residual, the 8³/12.5 m grid, the prescribed
trajectory, and the constant atmosphere are structural limitations. A future
physics study should test a mechanism (for example low-flow/forced-convection
partition, size-resolved lateral area, or subgrid melt distribution) against
these diagnostics; this stage is a validation baseline only.

## 5. Limitations

1. Antarctic (WAP/WAIS), not the Barents Sea; no Barents inference.
2. 8³/12.5 m test grid; not resolution-converged.
3. Rectangular prism voxel body versus a real irregular iceberg.
4. Prescribed observed trajectory, so drift and grounding feedback are not
   tested.
5. Only 190 of 743 Enderlin observations have a model counterpart; the 190
   are the ≤120-day hindcast subset, not a new independence flag.
6. Seven independence groups; WAIS and all site-level subsets contain one
   cluster, so their cluster CIs are not estimable.
7. Observation uncertainty is treated as independent 1σ Gaussian; correlated
   systematic error would reduce the noise ceiling.
8. No wave erosion, no Antarctic ERA5 atmosphere, no calving, no tides; surface
   and vapour losses are excluded by the `SUBMARINE_TOTAL` definition.
9. The exact model binary commit is not embedded in the result CSV.
10. No matched literature analog exists, so L1 is skipped rather than forced.

## 6. Files

- `docs/wiki/stages/stage12/evidence/stage12.22/matched_cases.csv`
- `docs/wiki/stages/stage12/evidence/stage12.22/metrics.csv`
- `docs/wiki/stages/stage12/evidence/stage12.22/metrics_by_region.csv`
- `docs/wiki/stages/stage12/evidence/stage12.22/stage0_recon.json`
- `docs/wiki/stages/stage12/figures/stage12.22/T1_taylor_log10.png`
- `docs/wiki/stages/stage12/figures/stage12.22/T2_taylor_linear.png`
- `docs/wiki/stages/stage12/figures/stage12.22/B1_scatter_loglog.png`
- `docs/wiki/stages/stage12/figures/stage12.22/B2_ratio_distribution.png`
- `docs/wiki/stages/stage12/figures/stage12.22/B3_bias_diagnostics.png`
- `docs/wiki/stages/stage12/figures/stage12.22/B4_group_means.png`
- `docs/wiki/stages/stage12/figures/stage12.22/figures_manifest.csv`
- `python/analysis/stage12.22_enderlin_validation.py`
- `python/tests/test_stage12_22_enderlin.py`
- `data/validation/stage12.22/journal_pdf_vectors.zip` (outside git)
