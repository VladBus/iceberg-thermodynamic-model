# Stage 12.16 — Drift verification, Enderlin diagnostics, ensemble, layer drag, energy ledger

**Date:** 2026-11-12  
**Status:** ACTIVE (12.16 work completed; no commit except the Stage 12.15 hygiene commits).  
**Scope:** drift-force audit and analytical test; Enderlin diagnostic baselines;
12-start 2024 ensemble at 50^3 with two 70^3 repeats; per-layer voxel drag
areas; boundary-energy ledger. No calibration and no physics change beyond the
explicit layer-resolved drag/energy instrumentation.
## 1. Executive summary

| Item | Result |
| --- | --- |
| Drift bug? | **No** missing wind, sea-ice suppression, or unit defect. Wind force is present; Coriolis balances it. |
| Analytical 100 m cube | 7 m/s: model **0.003927** vs discrete 0.003929; 15 m/s: **0.018013** vs 0.018042 |
| Current-only 0.1 m/s | Coriolis ON **0.000624 m/s** (0.62%); no Coriolis 0.0837 m/s after 60 d |
| Ensemble 2024 50^3 | 9 starts reach 365–366 d; P08/P11 ground early, P10 leaves ocean data at day 41 |
| Annual mass loss | **26.8–97.0%** for the nine long runs; P08 80.7%/275 d, P11 72.5%/189 d, P10 1.3%/41 d |
| t90 (10% remaining) | only P04 reaches it, at **311 d** |
| Enderlin baselines | constant **MAE 0.0241**; bulk 0.0302; voxel 0.0287 (RMSE 0.0318/0.0378/0.0399) |
| Skill vs constant | bulk **−0.416**, voxel **−0.574** |
| Layer drag | cube matches prism Method A within **0.59%**; eroded 30 d prism side area 15.2%/18.3% high (50^3/100^3) |
| Energy ledger | 30 d residual **0.067%** (50^3) and **0.664%** (100^3) of latent after adding melt sensible enthalpy |
## 2. Drift verification (priority 1)
### 2.1 Analytical force balance
`test/iceberg_test_drift_force_balance.f90` (100 m cube, prism drag, no melt).
Continuous equilibrium `u_eq=F_wind/(M f)`; the semi-implicit scheme adds
`sqrt(1+(f dt)^2)`.

| Forcing | Model | Discrete | Continuous | u/wind |
| --- | ---: | ---: | ---: | ---: |
| Wind 7 m/s | 0.003927 | 0.003929 | 0.004412 | 0.056% |
| Wind 15 m/s | 0.018013 | 0.018042 | 0.020257 | 0.120% |
| Current 0.1 m/s, Coriolis ON | 0.000624 | 0.000628 | — | 0.62% of current |
| Current 0.1 m/s, no Coriolis, 60 d | 0.0837 | — | drag-limited | 83.7% of current |

At equilibrium wind ≈ Coriolis ≫ water drag; the model matches the discrete
analytic value within 0.1–0.5%.
### 2.2 Annual-run force budget
`run.nc_forces.csv` stores ice/ocean/wind velocities, relative speeds, mass,
grounded flag, and wind/water/Coriolis/pressure/FK forces.

| Point | Speed [m/s] | Wind [N] | Water [N] | Coriolis [N] | Relative water [m/s] |
| --- | ---: | ---: | ---: | ---: | ---: |
| P01 | 0.00643 | 627.8 | 4.09 | 593.5 | 0.0214 |
| P04 | 0.02582 | 677.7 | 14.02 | 635.3 | 0.0598 |
| P06 | 0.00733 | 762.9 | 2.79 | 709.6 | 0.0171 |

Wind is present in every run and balances Coriolis; water drag is 1–2 orders
smaller. The 0.006 m/s scale is the Coriolis-limited equilibrium of a 100 m,
9.1e8 kg body, not a missing forcing.
### 2.3 Sea ice

`siconc` is read from GLORYS and written to output; it is used only by the
optional wave-erosion closure. `iceberg_dynamics` has no sea-ice drag or
concentration gate. P01 has mean `siconc` **0.370**, max **0.995**, and still
drifts. There is no concentration threshold that suppresses drift. The force
CSV now also carries `siconc` and zero `f_ice_x/y` columns because no sea-ice
force exists in the dynamics.
Conclusion: no wind/sea-ice/unit bug was found; no drift fix or re-run was
required before the ensemble.
## 3. Enderlin diagnostics without calibration

Baselines use the same 190 observations and the 12.15 current voxel run; the
bulk row is the archived 12.7a bulk output (the current run was voxel-only).

| Predictor | n | MAE | RMSE | Bias | Skill vs constant |
| --- | ---: | ---: | ---: | ---: | ---: |
| Constant (median observed) | 190 | 0.02411 | 0.03179 | −0.00574 | 0.000 |
| Bulk thermodynamic (12.7a) | 190 | 0.03019 | 0.03783 | +0.00505 | −0.416 |
| Voxel current (12.15) | 190 | 0.02869 | 0.03988 | −0.02193 | −0.574 |

The voxel model does not beat the constant median in MAE/RMSE; its lower bias
is bought with a larger error spread. Ratio correlations (n=190):

| Variable | Pearson r | p | Spearman rho | p |
| --- | ---: | ---: | ---: | ---: |
| ΔT (water − freezing) | −0.059 | 0.417 | +0.104 | 0.153 |
| Draft | −0.285 | 6.7e-5 | **−0.498** | 2.7e-13 |
| Size (sqrt surface area) | −0.285 | 6.9e-5 | **−0.506** | 9.6e-14 |
| Relative water speed | +0.001 | 0.988 | +0.198 | 0.006 |
| Interval duration | −0.028 | 0.702 | +0.020 | 0.785 |
| Mean wetted area | −0.237 | 0.001 | **−0.531** | 3.3e-15 |

Site medians: BG 2.48 (n=4), HG 1.10 (21), LG 1.11 (9), WG 1.02 (14), CG 0.47
(42), SG 0.39 (35), TG 0.45 (65). Size strata: ≤100 m 1.248 (20), 100–300 m
0.832 (60), >300 m 0.407 (110). Precipitation is not diagnosed because the
prescribed Enderlin runs used a constant atmosphere and the output has no
snowfall field.
**Conclusion (≤10 lines).** The under-melt of large icebergs is a size/draft-
dependent structural deficit: the ratio falls monotonically with draft and
wetted area (Spearman ≈ −0.50), while ΔT and duration show no relation. The
over-melt of small icebergs is the other side of the same size trend, amplified
by the lateral-dominated partition (median lateral 0.617 of submarine loss).
Relative speed has only a weak positive rank correlation (0.20). The pattern is
not explained by a missing temperature contrast or a short interval; Enderlin
uses prescribed trajectories, so it is not a drift effect. Parameters were not changed.
## 4. 2024 ensemble

Twelve 100 m cube starts, 50^3 / 2 m, 2024 daily GLORYS+ERA5, `--strict-ocean
--stop-on-grounding`. Wall 493–743 s per point (mean ≈ 660 s); total 119 min.
Table: `docs/wiki/stages/stage12/evidence/stage12.16/ensemble_2024_50cube.csv`
(full run outputs remain local in `data/validation/stage12.16/`).

| Point | Start | Days | Mass loss [%] | t90 [d] | Path [km] | Note |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| P01 | 78.0N 30E | 366 | 52.3 | — | 176 | complete |
| P02 | 78.0N 40E | 366 | 51.8 | — | 195 | complete |
| P03 | 78.0N 50E | 366 | 81.7 | — | 304 | complete |
| P04 | 78.0N 55E | 366 | 97.0 | 311 | 715 | complete |
| P05 | 79.0N 35E | 366 | 62.2 | — | 192 | complete |
| P06 | 79.0N 45E | 366 | 49.7 | — | 205 | complete |
| P07 | 79.0N 55E | 366 | 60.8 | — | 209 | complete |
| P08 | 80.0N 30E | 275 | 80.7 | — | 183 | grounded |
| P09 | 80.0N 40E | 366 | 87.2 | — | 464 | complete |
| P10 | 80.0N 50E | 41 | 1.3 | — | 20 | strict-ocean stop |
| P11 | 81.0N 20E | 189 | 72.5 | — | 80 | grounded |
| P12 | 81.0N 55E | 366 | 26.8 | — | 94 | complete |

Nine runs reached 365–366 d. P08 and P11 grounded at 80.01N 28.22E and
80.99N 18.88E; P10 left the valid ocean data at 80.08N 49.77E after 41 d.
Partial runs are not annual results and are marked in the maps. Only P04
reached 10% remaining mass (t90 = 311 d). Maps:
`figures/stage12.16/ensemble_2024_50cube_summary.png` and
`ensemble_2024_50cube_tracks.png`.
### 4.1 70^3 repeats

| Point | Grid | Mass loss [%] | t10 [d] | t90 [d] | Path [km] |
| --- | --- | ---: | ---: | ---: | ---: |
| P04 | 50^3 | 96.99 | 50.5 | 311.4 | 715.4 |
| P04 | 70^3 | 95.92 | 50.7 | 317.3 | 642.5 |
| P06 | 50^3 | 49.67 | 199.1 | — | 205.1 |
| P06 | 70^3 | 48.55 | 198.7 | — | 208.0 |

The 50-to-70 difference is ~1.1 percentage points in annual mass loss; t10
changes by <0.4 d, and P04 t90 changes by 5.9 d (1.9%). These are resolution
checks, not converged references.
## 5. Layer-resolved voxel drag

`voxel_iceberg_get_layer_areas` returns, per submerged layer, the projected
+x/−x/+y/−y face areas from `phi`. `compute_water_force` integrates drag over
those layers using ocean velocity interpolated to each layer centre; the prism
Method A branch remains only for the non-voxel regression path. The cube test
matches `W*draft`/`L*draft` within **0.59%** at 50^3 / 2 m; the eroded test
(half-width removal plus `phi=0.5` in one layer) follows `phi` and the
remaining silhouette (1.85% vs the prism reference).
Footprint (50^3 / 2 m, 2020, 30 d): prism side area 8782.2 m^2, voxel layer
integral 7447.6 m^2 (**15.2%**); prism waterline 9788.9 vs voxel 10000 m^2
(**2.16%**). At 100^3 / 1 m: prism side 8727.5, voxel layer 7128.4
(**18.3%**); waterline 9889.6 vs 10000 (**1.12%**). The cube meets the <1%
target; the eroded body does not, because the prism assumes vertical sides.
The layer integral is the actual submerged silhouette; the 15.2%/18.3% is the
prism approximation error that Method A previously hid.
## 6. Energy ledger

The ledger separates the submerged conductive flux (`Q_sub`), air Robin flux
(`Q_air`), test-only Dirichlet flux, flushed-ice energy, and the sensible
enthalpy of melted mass. With `Q_sub` the conductive flux into the ice, the
total ocean heat supply is `Q_sub + L*m_melt`; after cancelling `L*m_melt`:
`(E_sens-E_sens0) + (E_flush-E_flush0) + (E_melt_sens-E_melt_sens0)
 - (Q_sub+Q_air+Q_test) = residual`.

| Case | Days | L*Δm [J] | Q_sub [J] | Q_air [J] | E_melt_sens [J] | Final residual [J] | Final % | Max abs % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50^3 | 30 | 6.395e12 | 1.178e12 | −2.091e11 | −2.323e11 | 4.31e9 | 0.067% | 1.14% |
| 100^3 | 30 | 6.309e12 | 1.280e12 | −1.936e11 | −1.456e11 | 4.19e10 | 0.664% | 1.69% |

Both closures meet the 1–2% target after the melted-mass sensible term is
included. Without that term the 50^3 residual is 3.70% of latent
(2.365e11 J), equivalent to an unaccounted sensible heat at about 5.9 C; this
localizes the missing term. The model removes melt mass at the local cell
temperature without subtracting its sensible enthalpy. The diagnostic makes
the budget auditable but does not change the state evolution.
## 7. Verification and limitations

- `test/iceberg_test_drift_force_balance.f90`: 6 checks, 0 errors.
- Enderlin diagnostics: 190 rows, no calibration, 8^3 test grid.
- Ensemble: 12/12 completed or stopped with an explicit reason; 70^3 repeated
  on two points.
- Layer drag: cube 0.59%, eroded test 1.85%; 30-day footprint reported above.
- Energy: 50^3 final 0.067% (max 1.14%); 100^3 final 0.664% (max 1.69%).
- Strict build RC 0; `fpm test` 82 STOP 0, 0 failures; docs links 0 broken;
  `git diff --check` RC 0.
**Limitations for the thesis.** Capsize/roll is not modelled; there is no
buoyant rise; waves are off; drift is not validated against observed tracks;
the 100^3 convergence error is 3.75% at p=0.71; Enderlin has Spearman 0.16 and
a strong size-dependent ratio; strict-ocean/grounding stops prevent a full-year
trajectory at several northern starts; the 70^3 repeats are resolution checks,
not new references. The energy ledger closes diagnostically, not at the state
level.
## 8. Files

- Drift: `test/iceberg_test_drift_force_balance.f90`; log in
  `evidence/stage12.16/drift_force_balance.txt`.
- Enderlin: `evidence/stage12.16/enderlin_{baselines,correlations,site_table,diagnostics}.csv`;
  figure `figures/stage12.16/enderlin_ratio_drivers.png`.
- Ensemble: `evidence/stage12.16/ensemble_2024_{50,70}cube.csv`; maps in
  `figures/stage12.16/`; full outputs local under `data/validation/stage12.16/`.
- Energy/footprint: `evidence/stage12.16/energy_{50,100}_30d_closure.json` and
  `footprint_{50,100}_30d.json`; code in `src/voxel_iceberg.f90`,
  `src/iceberg_dynamics.f90`, `src/voxel_thermal_solver.f90`.
