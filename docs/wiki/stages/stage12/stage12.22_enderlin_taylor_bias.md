# Stage 12.22 — Enderlin23 Taylor diagrams and bias diagnostics

**Date:** 2026-11-19 (corrective audit; original report 2026-11-18)

**Status:** COMPLETE after corrective audit (validation only; no calibration, no model runs, no Fortran changes)
**Scope:** existing Stage 12.15 Enderlin23 prescribed-trajectory hindcast.

This revision fixes the density conversion, the observation-reliability
definition, the Taylor axes and negative-correlation display, B3's bootstrap
unit, B4's unsupported intervals, and titles/annotations. It also records the
model-document audit. The original Stage 12.15 result files were not overwritten.

## Stage 0 — reconnaissance (answers first)

### 1. Where are the Enderlin23 model results?

- `data/validation/stage12.15/enderlin_current2/enderlin23_hindcast_results.csv`
  — 190 per-case rows, including component mass losses, mean wetted area,
  duration, and the legacy `modeled_melt_rate_voxel`.
- `data/validation/stage12.15/enderlin_current2/<case_id>_voxel.nc` — 190
  per-case time series (`mass`, `draft`, `ocean_T_draft`, etc.).
- `data/validation/stage12.15/enderlin_trajectory_manifest.csv` — 190
  initial states/trajectories.

The grid is the **8³ / 12.5 m test grid**, not 100³/1 m. The run uses the
voxel/CN core (`VOXEL_ENABLED=true`) with prescribed trajectory; wave erosion is
OFF. The result CSV was written on 2026-11-11 on the current-code Stage 12.15
branch. The committed analysis is `92bcf8c`; the exact executable/build hash
is not embedded in the CSV, so this is documented provenance, not a
bit-reproducible binary record. Ocean forcing is the locally staged GLORYS12
0.083° daily product `GLOBAL_MULTIYEAR_PHY_001_030` (202311 native-S3
acquisition), seven site files, 32.2 MB total.

The per-case CSV contains the model melt-rate column, but the validation rate
is **not** copied from it: see §1 of the corrective changes.

### 2. How was each case initialized?

- Rectangular-prism initial shape.
- `L = W = √surface_area`; `H = volume_i/surface_area` for 141 cases.
- For 49 CG cases with inconsistent `volume_i`/`surface_area`/`draft`,
  `H = draft·ρw/ρi` (documented Stage 12.7a `H0_rule`).
- Initial ice temperature `T_ice = −10 °C`.
- Observed start/end positions are linearly interpolated daily; dynamics are
  disabled in prescribed-trajectory mode.
- GLORYS12 T/S/u/v are interpolated to the observed position, draft, and time;
  the nearest wet cell within 0.5° is used at land/NaN ice-front cells.
- No ERA5 Antarctic atmosphere is staged; a constant atmospheric boundary is
  used. Surface and vapour losses are excluded from the validation quantity.
- No calving, waves, sea-ice drag, or tides.

### 3. Are observed and modeled quantities the same?

All 743 observation rows have `melt_definition = SUBMARINE_TOTAL`. The observed
rate is exactly

`melt_rate = volume_change_rate / submerged_area` [m/day].

This was checked row-by-row (maximum relative discrepancy `7.1e-14`). The 1σ
uncertainty is

`σ_obs = |volume_change_uncert| / submerged_area` [m/day].

`volume_change_rate` and `volume_change_uncert` are already daily rates, so no
additional interval division is applied. Median `σ_obs` is `0.00714 m/day`
(25.9% of the median observed rate).

The model rate is

`(basal + lateral + wave) / ρ_ice / (mean_wet_area × duration) × 86400`
[m/day],

with `ρ_ice = 910.0 kg m⁻³` (matching `src/iceberg_types.f90`), `wave = 0`, and
surface/vapour losses excluded. It is a mass-loss / mean-wetted-area rate, not a
point melt rate and not side-only. The component masses are total kg over the
case; the duration is seconds.

### 4. Which cases ended early?

None. All 190 rows have `status=OK`; no grounding or out-of-domain stop is
recorded in this prescribed hindcast. Final model mass is **53.3–99.7%** of
initial mass; no case reaches the 1% threshold. The metric uses the full
observed interval for every case.

### 5. Is temperature forcing available per case?

Yes. `mean_delta_t_voxel = T_w − T_f` at the draft is stored for every case:
mean **2.03 °C**, range **0.243–3.525 °C**. Per-step `ocean_T_draft`,
`ocean_S_draft`, and `T_ice` are also in the 190 NetCDF files. The analysis uses
the stored mean; no new GLORYS extraction was needed.

### Missing / caveats in the input

- The observation table has **743** rows with `independent_case=True`; the
  **190** cases are the Stage 12.15 duration-filtered hindcast subset
  (`time_separation_days ≤ 120`). There are no model runs for the other 553
  observations, so they are not matched cases.
- The exact model binary commit is not encoded in the result file.
- Only seven `independence_group` values remain after the 190-case filter.
  WAIS has one group; every individual site is one group.
- No per-case observed `T_w`, velocity, or ice temperature exists; forcing is
  model/reanalysis, not in-situ.

## 1. Corrective changes

### 1.1 Density

The existing Stage 12.15 `modeled_melt_rate_voxel` used `ρ_ice = 916.7`.
Fortran uses **910.0**. The validation rate is now recomputed from the component
mass losses with 910.0:

`model_rate = (basal + lateral + wave) / (910.0 × mean_a_wet × seconds) × 86400`.

`modeled_melt_rate_voxel` is retained only as provenance
(`model_rate_legacy_9167` in `matched_cases.csv`). `python/validation/enderlin23_hindcast.py`
now also uses 910.0 for future Enderlin runs.

Checks against the expected conversion:

| Quantity | Old 916.7 | Corrected 910.0 |
| --- | ---: | ---: |
| Median model/obs | 0.5397 | **0.5437** |
| Bias [m/day] | −0.02193 | **−0.02177** |

### 1.2 Observation reliability / noise ceiling

The former Monte Carlo function added noise to the already noisy observations
and reported their correlation with the original. That is a stability check, not
a classical reliability ceiling, and it was mislabeled. It is replaced by the
analytic reliability estimate

- linear: `r_rel = sqrt(max(0, 1 − mean(σ_obs²)/var(obs)))`;
- log10: `σ_log = σ_obs/(obs·ln 10)`, then the same expression on `log10(obs)`.

The sample variance uses `ddof=1`. The estimate assumes independent additive
Gaussian errors with the supplied 1σ values and **no correlated or
representative error**. It is a reliability ceiling under those assumptions,
not a strict upper bound for a real model. It is drawn on Taylor diagrams as a
constant-angle line `θ = arccos(r_rel)`, not as a constant-radius arc.

### 1.3 Figures

All six figures have no overall or panel titles; the names belong in the text
captions. The corrected Taylor diagrams show negative correlations, use one
radial σ label instead of duplicated X/Y labels, show marginal 95% cluster
bootstrap intervals, and label the reliability line correctly. B3 uses a
cluster bootstrap over whole `independence_group`s; a bin with fewer than two
groups gets no CI. B4 shows descriptive group means only, without fabricated
confidence intervals. B1/B2 retain axes, units, statistics, ratio lines/ECDF,
and panel letters only.

## 2. Matched table

`docs/wiki/stages/stage12/evidence/stage12.22/matched_cases.csv` contains one
row per case:

`case_id`, `site`, `region`, `independence_group`, `obs_rate`,
`obs_unc`, `model_rate`, `model_rate_legacy_9167`, `duration_days`,
`surface_area`, `draft`, `delta_t`, `final_mass_pct`, `early_stop`.

All rates are m/day. There are 190 rows and no missing model/observation rates.
No calibration or model rerun was performed. The previous full 190-case run
took 992 s (≈5.2 s/case); no new run was justified.

## 3. Metrics

For rates `o_i`, `m_i`, sample standard deviations `s_o`, `s_m` (`ddof=1`):

- `bias = mean(m_i − o_i)`;
- `median ratio = median(m_i/o_i)`;
- `mean log10 ratio = mean(log10(m_i/o_i))`;
- `sd log10 ratio = sd(log10(m_i/o_i))`;
- `MAE`, `RMSE` in linear and log10 space;
- Pearson linear/log10, Spearman, Kendall;
- `σ_model/σ_obs = s_m/s_o`;
- `CRMSE/σ_obs = sqrt(mean[((m_i − mean m) − (o_i − mean o))²])/s_o`,
  with the log10 analogue.

95% CIs are percentile intervals from **5,000 cluster-bootstrap resamples of
whole `independence_group`s**, fixed seed `122022`. The CSV files in
`evidence/stage12.22/` are the machine source of truth for the numbers below. WAIS and individual sites
contain one cluster, so their intervals are marked unavailable rather than
invented. The Taylor X/Y bars are **marginal** intervals, not a joint 95%
region.

### Overall

| Metric | Linear | log10 |
| --- | ---: | ---: |
| N / groups | 190 / 7 | 190 / 7 |
| Median observed / model [m/day] | 0.0383 / 0.0211 | — |
| Bias [m/day] | −0.02177 [−0.02950, −0.00756] | — |
| Median model/obs ratio | 0.5437 [0.4551, 1.0209] | 0.5437 [0.4551, 1.0209] |
| Mean log10(model/obs) | — | −0.2148 [−0.3181, 0.0065] |
| SD log10(model/obs) | — | 0.4509 [0.3836, 0.4766] |
| MAE [m/day] | 0.02864 [0.01844, 0.03468] | — |
| RMSE [m/day] | 0.03982 [0.02866, 0.04592] | — |
| MAE log10 | — | 0.3987 [0.3085, 0.4385] |
| RMSE log10 | — | 0.4984 [0.3855, 0.5442] |
| Pearson | 0.0422 [−0.3007, 0.3944] | 0.1543 [−0.2713, 0.6282] |
| Spearman | 0.1565 [−0.2740, 0.6268] | 0.1565 [−0.2740, 0.6268] |
| Kendall | 0.1171 [−0.1859, 0.4330] | 0.1171 [−0.1859, 0.4330] |
| σ_model/σ_obs | 0.4146 [0.2030, 0.6999] | 0.5849 [0.3865, 0.8367] |
| CRMSE/σ_obs | 1.0634 [0.9329, 1.2393] | 1.0750 [0.7916, 1.3920] |
| Reliability ceiling r | 0.9328 | 0.8843 |

### Regions

| Stratum | N | groups | median ratio | mean log10 ratio | Pearson log10 | σ ratio log10 | reliability log10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| WAP | 125 | 6 | 0.6543 [0.4671, 1.2671] | −0.1331 [−0.2593, 0.1486] | 0.3357 [−0.3204, 0.7079] | 0.5130 [0.3533, 0.7128] | 0.8889 |
| WAIS | 65 | 1 | 0.4497 (no cluster CI) | −0.3718 (no cluster CI) | −0.1988 (no cluster CI) | 0.7026 (no cluster CI) | 0.8645 |

The site table (n ≥ 8) is in
`docs/wiki/stages/stage12/evidence/stage12.22/metrics_by_region.csv`.
BG (n=4) is reported but excluded from Taylor points due to the eight-point cap.

## 4. Figures

PNGs: `docs/wiki/stages/stage12/figures/stage12.22/`. PDF vectors:
`data/validation/stage12.22/journal_pdf_vectors.zip` (outside git). Manifest:
`figures_manifest.csv`.

- **T1** Taylor, log10: 8 points (All, WAP, WAIS, CG, HG, SG, TG, WG); negative
  correlations displayed; normalized σ radial scale; r labels include negative
  values; CRMSE contours; constant-angle reliability line; marginal cluster CIs.
- **T2** same in linear space; reliability ceiling 0.9328.
- **B1** log-log scatter; 1:1, ×2, ×10; region colour; uncertainty-scaled
  markers; N/median/r/Spearman with cluster CIs.
- **B2** log10 ratio histogram, ECDF, median and CI, WAP/WAIS boxplots; no
  panel titles, panel letters only.
- **B3** global binned median log10 ratio versus ΔT, size, duration and region.
  Bin edges are fixed once on the original sample; each bootstrap replicate
  resamples whole `independence_group`s from the full group set, includes all
  their rows, and only then selects rows in the bin. No CI is drawn when a bin
  has fewer than two source groups. Individual icebergs and binned medians are
  distinguished. The Y label is individual `log10(model/observed)`.
- **B4** descriptive observed and modeled mean submarine melt for seven
  independence groups; **no confidence intervals** and no title.
- **L1 skipped**: the basal/lateral literature tables contain lab, Sermilik,
  regional-maximum and synthesis values with no matched model forcing/geometry.
  A like-for-like comparison would be artificial; no new runs were made.

## 5. Results

**Good.** The model median is factor 1.84 below the observed median, but not an
order-of-magnitude failure: median ratio **0.5437**, bias **−0.02177 m/day**.
The observed and modeled distributions overlap substantially.

**Bad.** The model is too smooth: `σ_model/σ_obs = 0.4146` linear and
**0.5849** log10, while normalized CRMSE is **1.063–1.075**. Pearson log10 is
**0.154** (CI includes zero) and Spearman is **0.156** (CI −0.274 to 0.627).
The model does not reproduce observed rank ordering at useful confidence.

**Size dependence.** Median log10 ratio is **+0.121** for the smallest size
quartile (`√A ≤ 170 m`) and **−0.287, −0.382, −0.396** for the next three
quartiles. This is a clear size-dependent under-melt, not a uniform offset.
WAP median ratio is **0.654**; WAIS **0.450**, but WAIS is one cluster.

**Thermal forcing.** Binned median log10 ratio is **−0.418, −0.183, −0.203,
−0.276** across ΔT quartiles; it is not monotonic. A simple “more ΔT → more
melt” correction would not explain the residual.

**Reliability.** The independence-error reliability ceiling is **0.884** in
log10; its assumptions are stated above. The model's 0.154 is below it, so
independent observation noise alone does not explain the weak rank correlation,
but correlated/representative error remains unquantified.

**What to investigate.** Structural limitations and mechanisms: 8³/12.5 m grid,
prescribed trajectory, prism initialization, large-iceberg geometry, forcing
representation, and regional/heat-transfer differences. Do **not** calibrate
`K_T`, `K_S`, `γ_free`, or `melt_cap` to these plots.

## 6. Model-document audit

The requested `Моделирование_термодинамики_айсбергов.docx` was **not present**
in the repository or under `/home/vlad`. The supplied current-state PDF and its
TeX source (`docs/references/Iceberg/Iceberg_Model_Current_State.{pdf,tex}`)
were audited instead; the detailed table is
`docs/references/Iceberg/Iceberg_Model_Current_State_12.22_AUDIT.md`. No
LaTeX/docx toolchain is installed, so the `.tex` source was corrected but the
supplied PDF was not rebuilt.

Corrections made to the `.tex` source:

- ice density is stated as **910 kg/m³** (already correct);
- connectivity period is now default **1 h**, configurable with
  `VOXEL_CONNECTIVITY_HOURS`, maximum 6 h; Stage 12.20 used 6 h;
- software grid default is distinguished from the scientific **100³/1 m**
  configuration and the Enderlin **8³/12.5 m** test grid;
- PCG maximum is corrected from a fixed 1000 to the actual default
  `10·Nx·Ny·Nz` (`ICEBERG_CG_MAXIT` override);
- the autonomous-air path (`autonomous_air=.true.` in the voxel step) is
  explicit;
- Stage 12.22 is explicitly stated to have made **no Fortran changes**.

The audited parameters are: `VOXEL_PHI_CONN=0.3`, `VOXEL_MELT_CAP=0.20`,
`ICEBERG_THETA=0.5`, `ICEBERG_CG_TOL=1e-10`.
The step order in the document matches the code: interface, CN, clamp,
boundary melt/cap, flush/connectivity, compaction, dynamics, ledger.
Implemented, disabled and future processes remain separated in the source.

## 7. Limitations

1. Antarctic WAP/WAIS, not the Barents Sea.
2. 8³/12.5 m test grid; not resolution-converged.
3. Prismatic/voxel initialization versus real irregular geometry.
4. Prescribed observed trajectory; drift/grounding feedback not tested.
5. Only 190 of 743 observations have model counterparts; the 190 are the
   ≤120-day subset.
6. Seven independence groups; WAIS and all sites have one cluster, so no
   cluster CI for them.
7. Observation uncertainty is treated as independent 1σ Gaussian; correlated
   systematic error is unquantified.
8. No waves, Antarctic ERA5, calving, or tides; surface/vapour excluded.
9. Exact model binary commit not embedded in the result CSV.
10. No matched literature analog; L1 omitted.

## 8. Files

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
- `docs/references/Iceberg/Iceberg_Model_Current_State.tex`
- `docs/references/Iceberg/Iceberg_Model_Current_State_12.22_AUDIT.md`
- `data/validation/stage12.22/journal_pdf_vectors.zip` (outside git)

## 9. Verification

- `python -m unittest discover -s python/tests -v`: **30 tests passed**.
- `python scripts/check_docs_links.py`: 67 files, 290 links, 0 broken.
- `git diff --check`: clean after the final formatting pass.
- `figures_manifest.csv`: six PNG files, six PDF entries.
- `data/validation/stage12.22/journal_pdf_vectors.zip`: six PDF vectors.
- Visual inspection: six PNG files; no figure titles; Taylor negatives and
  reliability lines visible; B3 whole-group CIs and B4 descriptive means only.
- No `fpm` run, no `iceberg_run`, no Fortran/model/constant change.
