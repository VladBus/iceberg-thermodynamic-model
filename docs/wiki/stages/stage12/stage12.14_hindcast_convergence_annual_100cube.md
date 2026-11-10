# Stage 12.14 — Enderlin regression, convergence, and 100^3 annual runs

**Date:** 2026-11-10  
**Status:** AUDIT COMPLETE; Enderlin rerun BLOCKED by missing site forcing; annual
100^3 runs completed to 365.0 d of requested 366 d by explicit strict-ocean stop.
**Scope:** Enderlin23 rerun attempt, mass-loss convergence/Richardson, 2020 tail
diagnosis, 100^3 2020/2024 runs, prism/voxel footprint audit, plot corrections,
energy diagnostics. No calibration, no downloads, no commit/push.

## 1. Executive summary

| Item | Result |
| --- | --- |
| Enderlin23 rerun on current code | **BLOCKED_INPUT**: 0/190 rows, Antarctic GLORYS site files and trajectories absent |
| 30-day convergence order, 50/70/100 | `p = 0.7108`; extrapolated mass loss `0.0373275`; 100^3 error `3.75%` |
| 2020 tail | Grounded on a 7 m bank; drift speed becomes 0; melt continues slowly, not a zero-melt solution |
| 100^3 annual 2020 | 365.0 d, mass loss `50.13%`, no fallback, strict stop at final point |
| 100^3 annual 2024 | 365.0 d, mass loss `50.23%`, no fallback, strict stop at final point |
| Prism minus voxel footprint | 100^3 30 d `2.91%`; annual 2020 `37.8%`; annual 2024 `6.74%` |
| Energy budget | **NOT CLOSED independently**: boundary heat flux is not accumulated |
| Plots | T 3D `shade=False`; S_B labels; face-profile check and legend fixed |

## 2. Constraints and inputs

- No new downloads. No commit or push.
- Runs were launched strictly one at a time on the 8 GB WSL2 host.
- Annual runs: 100 m cube, `100x100x100`, `dx=dy=dz=1 m`, `dt=3600 s`,
  start `78.0 N, 30.0 E`, `--strict-ocean`, requested 366 days.
- Inputs have 366 daily records for 2020 and 2024; no substitution was used.
- 100^3 annual output is generated data under `data/validation/stage12.14/` and
  was not added to Git.
## 3. Enderlin23 regression (12.7a)

The current harness is `python/validation/enderlin23_hindcast.py`. It requires:

```text
data/input/raw/reanalysis/glorys12/antarctic/glorys12_<site>_daily.nc
data/input/raw/reanalysis/glorys12/antarctic/glorys12_<site>_static.nc
data/validation/trajectories/enderlin23/<case>.csv
```

None of those files or the `antarctic` directory are present; only the unrelated
Barents static file exists under `data/input/raw/reanalysis/glorys12/static`. A full harness attempt returned
`0/190 OK, 190 SKIP_NO_DATA` and exit code 2. No current-code melt rate,
lifetime, or metric comparison can be made without reacquiring the 32 MB local
site forcing; that would violate the no-download rule.

The 12.7a baseline remains the authoritative comparison:

| Metric | Bulk | Voxel |
| --- | ---: | ---: |
| N | 190 | 190 |
| Median model/observed ratio | 1.394 | 0.0593 |
| Mean ratio | 2.417 | 0.132 |
| Spearman | 0.136 | 0.153 |
| MAE, m/day | 0.0302 | 0.0413 |
| RMSE, m/day | 0.0378 | 0.0517 |
| Median modeled, m/day | 0.0471 | 0.00227 |

No lifetime was computed by 12.7a; the observations are prescribed intervals,
not lifetime experiments. The Stage 12.7.audit/12.7c three-case ratios
(1.057/0.258/0.089 without the floor; 1.309/0.655/0.208 with it) remain the
only post-12.7 voxel sensitivity evidence, and were not rerun here.
## 4. 30-day mass-loss convergence

Using the last three grids (`N=50, 70, 100`) and the non-uniform generalized
Richardson equation:

| N | h [m] | 30-day mass loss | mean submarine melt rate [m/day] |
| ---: | ---: | ---: | ---: |
| 50 | 2.0 | 0.0396212 | 0.0293222 |
| 70 | 1.43 | 0.0391333 | 0.0289574 |
| 100 | 1.0 | 0.0387289 | 0.0286532 |

The difference ratio is `1.20652`; solving
`(1.4^p-1)/(1-1.42857^-p)=1.20652` gives **p = 0.71079**.
Richardson extrapolation gives `L_inf = 0.0373275`; the 100^3 mass loss is
`3.754%` above that limit. This is a slow, non-asymptotic convergence order; the
100^3 grid remains a reference, not a demonstrated converged solution.
`T_max` is not used: it is grid-dependent; mass loss and mean wetted-area melt
rate are the integral metrics. The mean melt-rate trend is 6.7% from 8^3 to
100^3 (0.030705 to 0.028653 m/day).
## 5. 2020 tail and grounding

The 8^3 diagnostic run at `76.5 N, 20 E` (`annual_2020_8cube`) was replayed and
compared with the independent static bathymetry. Daily diagnosis is in
`data/validation/stage12.14/tail_daily.csv`:

| Day | Latitude | Longitude | Speed [m/s] | Mass [kg] | Draft [m] | Bathy [m] | Grounded | Fallback/day |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 295 | 76.7789 | 17.3229 | 0.036 | 19,788,314 | 43.72 | 71.3 | no | 0 |
| 299 | 76.8282 | 17.1162 | 0.020 | 17,972,486 | 43.74 | 15.2 | yes | 16 |
| 300 | 76.8383 | 16.9213 | 0.059 | 17,074,752 | 43.63 | 7.0 | yes | 24 |
| 301 | 76.8369 | 16.8608 | 0.018 | 16,857,256 | 43.71 | 7.0 | yes | 24 |
| 365 | 76.8369 | 16.8608 | 0.000 | 12,649,387 | 43.75 | 7.0 | yes | 1 |

The body reaches a **7 m bank**; its 43.7 m draft is grounded, so drift stops.
Melt does not stop: mass falls from 17.08 Mt on day 300 to 12.65 Mt on day 365
(1.39% of initial mass), but the rate falls from about 0.54 Mt/day (295–300) to
0.043 Mt/day (320–365). The 1,577 fallback events begin at day 299.33; 24
events/day occur while the body remains on the bank.

The old run did not terminate at grounding. A new `--stop-on-grounding` option
was added and tested: it stops at day `300.25`, record 7,207, mass
`1.6928e7 kg`, with the explicit message
`STOP: iceberg grounded ... draft=43.68118 m`. The new option is opt-in; it does
not change the default physical evolution. The old 365-day tail is therefore a
**diagnostic continuation**, not a valid free-drifting annual trajectory.
Old 8^3 figures in Stage 12.11/12.13 carry the overlay `DIAGNOSTIC 8^3 — NOT A RESULT`.
## 6. 100^3 annual runs

Both runs used strict-ocean forcing: if the primary GLORYS/ERA5 point is land or
missing, the run stops; no nearest-cell substitution is made.

| Year | Records | Days | Mass loss | Final mass [kg] | Draft/freeboard [m] | Terminal point |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2020 | 8,761 | 365.0 | 50.13% | 453,795,168 | 80.30 / 6.70 | 78.1926 N, 28.6852 E |
| 2024 | 8,761 | 365.0 | 50.23% | 452,879,776 | 80.59 / 7.41 | 78.2262 N, 27.2213 E |

Both runs were requested for 366 days but produced 365.0 d: the final primary
ocean point is unavailable and strict mode stops with an explicit message.
`run.nc_fallback.csv` is absent for both; no substitution occurred. This is not
a complete 366-day calendar result; it is a strict-ocean 365.0-day result.
Wall times were about 1h38 (2020) and 1h36 (2024), RSS ~0.6 GB peak.
## 7. Prism/dynamics and footprint diagnostic

`voxel` remains authoritative for mass and draft/freeboard; prism `L/W` still
changes through lateral melt. Footprint is `prism_volume/(prism_draft +
prism_freeboard)` versus the voxel waterline area from `phi`.

| Case | Initial diff | Mid diff | Final diff |
| --- | ---: | ---: | ---: |
| 100^3, 30 d | 0.0074% | 1.26% | 2.91% |
| 2020, 100^3 | 0.0048% | 6.41% | 37.8% |
| 2024, 100^3 | 0.0006% | 3.13% | 6.74% |

Active `state%L/W` uses:

| Location | Use | Status |
| --- | --- | --- |
| `iceberg_dynamics:96,175` | prism mass/sail fallback | inactive when voxel is on |
| `iceberg_dynamics:263-264` | Method A layer side areas | **active prism approximation** |
| `iceberg_dynamics:327` | Method B wet area fallback | inactive when voxel is on |
| `iceberg.f90:145-150,172-173` | prism diagnostics/buoyancy | overwritten or diagnostic |
| `iceberg.f90:486-493` | lateral prism L/W update | active footprint bookkeeping |
| `iceberg_thermodynamics:271,1566-1567,365-369` | bulk l_char; voxel kg/s→prism rates; wave L/W | active prism footprint conversion; waves off |
| `iceberg_geometry.f90` | mass-budget diagnostics | diagnostics only |
| `app/iceberg_run:270` | prism volume record | diagnostic only |

The Method A side area cannot be replaced by the current scalar voxel
projected area without losing its layer-resolved force integral. The footprint
diagnostic quantifies the error; **Method A remains a documented WARNING**, not
an exact voxel representation.
## 8. Plots and face-profile check

- T 3D uses `shade=False`, so face colors match the `YlOrRd` colorbar and the
  horizontal/vertical sections.
- S 3D and S sections are labelled `interface salinity S_B (ice without salt)`.
- Face profiles use explicit labels with `(i,j)`: `x=0 face`,
  `x=max face`, and `interior x=center`; the shared legend is outside the axes.
- The `x=max` profile and the `j=50` slice are elementwise identical:
  `max|dphi| = 0.0`. The apparent `0.03` is the layer-24 cell at
  `z_center=23.5 m` (`phi=0.031554`); at `z_center=24.5 m`, `phi=0.095291`.
  The 0.03-vs-slice difference was an index/shading presentation issue, not a
  second field. See `face_profile_check.txt`.
## 9. Energy budget

Using `sensible_energy`, cumulative mass loss, flushed mass/energy, and
`L_f=3.34e5 J/kg`, the **implied** boundary heat is:

| Case | Δsensible [J] | latent melt [J] | flushed energy [J] | implied boundary [J] | % initial latent |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2020 annual | 1.1298e13 | 1.5102e14 | 1.3470e12 | 1.6367e14 | 53.85% |
| 2024 annual | 1.1048e13 | 1.5133e14 | 1.3528e12 | 1.6373e14 | 53.87% |

This is **not a closed independent budget**. The model does not accumulate an
auditable time series of boundary heat flux (submerged Dirichlet + autonomous
air) separately from the CN state; therefore `implied boundary` is a residual
definition, not a verification of it. The missing terms are the integrated
face-by-face boundary flux and a clean split of flushed latent/sensible heat.
No energy-closure claim is made.
## 10. Verification

- Enderlin harness: `0/190 OK, 190 SKIP_NO_DATA`, exit 2 (expected blocked).
- 30-day convergence: `p=0.71079`, `error_100=3.754%`.
- Annual 100^3: 8,761 records each; strict-ocean stop; no fallback CSV.
- `stage12.14_audit.py` writes footprint/energy JSON and CSV for each run.
- strict `fpm build` with `-Wall -Wextra -fcheck=all -ffpe-trap=...`: RC 0.
- `fpm test`: 81 programs STOP 0, 0 failures.
- `check_docs_links.py --all/--anchors`: 0 broken links, 0 anchor warnings.
- `git diff --check`: RC 0. No commit/push.

## 11. Open limitations

Enderlin remains unverified on current code because the site forcing is absent.
The 100^3 runs are 365.0 days, not 366, and stop where strict ocean data end.
The convergence order is only 0.71; 100^3 is still 3.75% from the Richardson
limit. Prism footprint remains 37.8% different from voxel waterline at the 2020
annual endpoint. Method A still uses prism side areas. Full energy closure is
not independent. No observational validation or calibration is implied.
