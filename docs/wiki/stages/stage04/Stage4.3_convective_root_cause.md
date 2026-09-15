# Stage 4.3 — Root-Cause Analysis: Convective-Adjustment Guard Cycling

## Summary

Stage 4.3 adds **monitoring-only** diagnostics (no physics changes) to the
convective adjustment and, for the first time, identifies the **precise
numerical mechanism** behind the 1000-iteration guard firing. The historical
cycling is caused by a **float32 quantization mismatch**: the EOS output
`RO = 1.0/(0.698 + aa/bb) − 1.02` is computed from an intermediate `X`
in `[1, 2)`, so every density value sits on a grid of spacing
`2^-23 ≈ 1.19e-7 g/cm3`. The historical convergence threshold `0.9e-7`
is **below** that grid spacing, so the algorithm can only ever declare an
interface converged when `RO(k) == RO(k+1)` **exactly**. Any 1-ulp residual
difference is always "inverted" and re-mixed, producing a perpetual cycle
that only the 1000-iteration guard can exit.

**Result: A. PHYSICALLY CONVERGED / ALGORITHMICALLY CYCLIC — root cause
identified as a float32 quantization / threshold mismatch** (see
§10 Classification).

## 1. What Was Added (Diagnostics Only)

All changes are **monitoring only** — the mixing algorithm, EOS, threshold,
guard limit and blocks 200/210/280 are UNTOUCHED.

### 1.1 `src/convective_adjustment.f90`

- `convect_column`: new optional outputs `o_k_problem` (interface with max
  residual inversion on exit) and `o_resid_inv` (its magnitude). Does not
  change the algorithm.
- `conv_adj(day, step)`: optional day/step arguments; on a guard hit logs a
  one-line event to `data/output/convective_guard_events.csv` via
  `ca_log_guard_event` (capped at `ca_guard_evt_cap = 100` events/day to
  bound output; full profiles are recovered from the daily NetCDF in Python).
- Event columns: `day, step, i, j, ki, iter_count, nmix, k_problem,
resid_inv, tdz_before, tdz_after, dtdz, rel_t, sdz_before, sdz_after,
dsdz, rel_s` — includes T·DZ1 / S·DZ1 conservation across the guard.
- `ca_probe_inversions(tag, day, step)`: read-only scan of `T2/S2` counting
  columns with density inversions > eps and printing a per-level histogram.
  Used to compare the inversion field **after advection** (point A) with the
  field **after convective adjustment** (point D).

### 1.2 `app/main.f90`

- `call conv_adj(kkk, iii)` now passes day/step for event logging.
- Probes installed at point A (`A_after_adv`, after `advs`/`advt`) and
  point D (`D_after_conv`, after `conv_adj`), sampled at `iii = 1, 6, mm2`.

### 1.3 Python (new)

- `python/analysis/convective_analysis.py` — aggregates the event CSV + daily
  diagnostics → `data/output/convective_analysis.csv` + `.txt` report.
- `python/plotting/convective_plots.py` — 5 figures in
  `python/plotting/figures/convective/`.

## 2. Data Verified (Matches Stage 4.2 Spec)

| Quantity      | Value                     |
| ------------- | ------------------------- |
| EUU day 1     | 9.618e15 cm²/s²           |
| EUU day 30    | 2.696e17 cm²/s²           |
| EUU max       | 3.043e17 (day 28)         |
| U range       | −40.75 … +36.10 cm/s      |
| V range       | −38.43 … +34.08 cm/s      |
| W range       | −0.081 … +0.110 cm/s      |
| T range       | −0.126 … +25.82 °C        |
| S range       | 0.032374 … 0.035020       |
| RO range      | 0.001848 … 0.008161 g/cm³ |
| wind max      | 19.07 m/s                 |
| Σ nmix        | 42,513,769                |
| guard hits    | 5,467 / month             |
| max_iter      | 1001                      |
| affected cols | 1,187,663 / month         |

## 3. Temporal Evolution of Guard Hits

Guard hits grow **super-linearly**:

```
day   2    5   10   15   20   25   30
hits  1    2   11   37  170  367  881
```

Correlations with `guard_hits` (Pearson, 30 points):

| variable         | r      |
| ---------------- | ------ |
| ca_nmix          | +0.978 |
| ro_max           | +0.898 |
| ro_mean          | +0.909 |
| t_min            | −0.879 |
| euu              | +0.802 |
| ca_affected_cols | +0.781 |
| w_max            | +0.495 |
| v_max            | +0.478 |
| u_max            | +0.439 |
| t_max            | +0.323 |
| wind_max         | −0.096 |

Correlation ≠ causation. The strong link to `ro_max`/`ro_mean` (max
density-anomaly and its mean grow through the run) combined with the weak
wind link points to an **ocean-state** driver, not a wind driver: as the
basin warms/salts up (T_max up, T_min down, RO_max up), more columns reach
near-neutral density where the 1-ulp quantization trap lives.

## 4. Problem Locations

- **All** 5,467 guard events are on columns with `ki = 18`. On the TEST grid
  **100% of wet columns have ki = 18** (uniform 600 m synthetic basin), so
  this is NOT a physical depth preference — it is an artifact of the uniform
  TEST bathymetry.
- Guard columns: 1,171 unique (i, j) of 8,991 wet columns (13%).
- Spatial clustering: i bin 98–120 (720 events) and j bins 10–26 (717),
  74–90 (364) — the edges of the basin.

## 5. Day-Internal Timing

Guard events concentrate in early baroclinic steps (III):

```
step   1    2    3    4    5    6    7    8    9   10   11   12
evts  420  384  201  144  124   91   82   63   44   32   39   36
```

Only 36 of the 1,660 logged events are at the last step (III = 12). Guard
hits are mostly **transient** (during the day) rather than persistent
end-of-day residuals.

## 6. T/S/RO Analysis

- Horizontal-mean vertical profiles remain **stably stratified** at all days
  0–30 (RO increases monotonically with depth), so the guard cycling is a
  **column-local** effect that horizontal averaging hides.
- Representative guard columns (from the daily NetCDF) show RO differences
  that are **exactly** `2^-23` (1 ulp) or `2·2^-23` at the residual
  interface — i.e. the profile is "as mixed as float32 allows".
- `resid_inv` distribution over 1,660 logged events:
  - `1.1921e-07` (= 2^-23, 1 ulp): **1,658 / 1,660 (99.9%)**
  - `2.3842e-07` (= 2·2^-23, 2 ulp): 2 / 1,660

## 7. U/V/W Analysis

`ca_probe_inversions` shows the driver of the growth:

| day | columns inverted after ADV (A) | residual after CONV (D) |
| --- | ------------------------------ | ----------------------- |
| 1   | ~58–88                         | 0                       |
| 5   | ~282                           | 0                       |
| 10  | ~1774                          | ~0.7                    |
| 15  | ~3629                          | ~2.7                    |
| 20  | ~4572                          | ~14                     |
| 25  | ~5775                          | ~30                     |
| 30  | ~6334                          | ~71                     |

The number of columns carrying density inversions **after advection** grows
from ~86 (day 1) to ~6,400 (day 30) — a 70× increase — while the residual
inversions left after `conv_adj` grow from 0 to only ~70. So convective
adjustment **removes the vast majority** of inversions every step; the guard
fires only on the last ~1% of columns, whose residual is stuck at the
float32 1-ulp level. The growth in guard hits is therefore driven by the
**advection creating more near-neutral columns** as the circulation spins up,
not by the mixer degrading.

## 8. Conservation

Across all 1,660 logged guard events (T·DZ1 / S·DZ1 before vs after guard):

| quantity  | max     | mean    |
| --------- | ------- | ------- |
| \|rel_t\| | 2.07e-7 | 1.20e-8 |
| \|rel_s\| | 2.36e-7 | 6.39e-9 |

Conservation is at machine precision — the guard exits do not corrupt T or S.

## 9. ROOT CAUSE (new, definitive)

The Stage 3.3a report described the _symptom_ (mixing at interface k →
outer-loop restart → re-processing) but not the _cause_. The mechanism is:

**1. EOS output is quantized on a `2^-23` grid.**

```
RO = 1.0/(0.698 + aa/bb) − 1.02      (equation_of_state.f90:31)
```

The intermediate `X = 1.0/(0.698 + aa/bb)` lies in `[1, 2)` for all
physical T/S. In float32 the spacing of `[1, 2)` is exactly
`2^-23 = 1.1920929e-7 g/cm3`. Subtracting the constant `1.02` preserves the
grid, so **any nonzero difference of two RO values is a multiple of 2^-23**.

**2. The threshold lies below the grid.**

The historical criterion `a = RO(k) − RO(k+1) ≤ 0.9e-7` can be satisfied
**only** by `a = 0` (exact equality), because the next nonzero value,
`1 ulp = 1.192e-7`, is already **larger** than `0.9e-7`.

**3. Exact equality everywhere is unreachable for a multi-interface column.**

Mixing interface `k` sets `RO(k) = RO(k+1)` exactly, but the new T/S at
level `k` makes interface `k−1` differ from `k` by 1 ulp → it is "inverted"
again → mixed → which re-inverts `k` or `k+1` … The sequential top-down
mixer cannot reach a state where _all_ interfaces differ by exactly 0,
because any intermediate mixing result lands back on the `2^-23` grid.

**4. The guard is therefore the _correct_ exit.**

After ~2,000 mixings the column is physically converged (all real density
differences removed); only the float32-representable 1-ulp residual remains,
which is _numerically_ unfixable. This is confirmed by:

- `resid_inv = 2^-23` in 99.9% of events;
- `nmix / iter_count ≈ 2.03` (a1 ≈ 2 mixings per outer loop, stable cycle);
- near-perfect T/S conservation;
- the probe data showing residual inversions stay at ~0–70 columns/day while
  post-advection inversions reach ~6,400.

**Historical note:** the original model (Nesterov et al., 1995–2001) used the
same EOS form and threshold; whether it cycled in the same way is unknown
(the modern 3D dynamics generate the near-neutral columns that trigger it).
The Stage 3.2 guard (1000 iterations) remains the correct, physical
workaround and is preserved unmodified.

## 10. Classification

**A. PHYSICALLY CONVERGED / ALGORITHMICALLY CYCLIC — root cause = float32
quantization (2^-23 grid of the EOS) vs. threshold 0.9e-7 below the grid.**

The convective adjustment is physically converged when the guard fires: all
real density inversions are removed, and only a single float32 ulp of
numerical residual remains at one interface. The algorithm cannot terminate
naturally because the historical threshold is unreachable in float32.

### Why NOT B (code regression) / C (missing physics) / D (data problem)

- **Not B:** the mixer, EOS, threshold and blocks 200/210/280 are byte-for-byte
  historical; nothing in the modernization changed this behavior (it is a
  property of `0.9e-7 < 2^-23`).
- **Not C:** the residual is provably a pure float32 quantization artifact
  (resid_inv ≡ 2^-23), not an unresolved physical instability; horizontal
  mean profiles are stable, and the mixer removes 99%+ of inversions.
- **Not D:** the event log, conservation columns and probes are internally
  consistent and cross-validated against the daily NetCDF.

## 11. No Code Changes to Physics

- EOS, threshold `0.9e-7`, mixing algorithm, `iter_count > 1000` guard —
  UNCHANGED.
- `kl1 = 0`, no d2m/tcc/precip, TEST grid — UNCHANGED.
- Only diagnostics added (event CSV, probes, optional outputs, day/step
  plumbing, Python analysis/plots).

## 12. TEST-Grid Limitations

- Uniform 600 m basin → `ki = 18` for 100% of wet columns; "ki=18 bias" in
  the events is an artifact, not a physical signature.
- Real-grid (Stage 3.5) will likely change the guard-hit distribution, but
  NOT the root cause (it is a numerical property of the EOS/threshold pair).
- A real fix (e.g., threshold raised above 2^-23, or double-precision EOS)
  is out of scope for Stage 4.3 (diagnostics only) and would require
  promt.md approval before touching equations.

## 13. Validation

| Check                                          | Result                          |
| ---------------------------------------------- | ------------------------------- |
| `fpm build -Wall -Wextra`                      | ✅                              |
| `fpm test` (conv 15/15, EOS 7/7, NetCDF)       | ✅                              |
| `fpm run -fcheck=all -ffpe-trap` 30-day ERA5   | ✅ clean, EXIT=0                |
| Event CSV sampling vs guard_hits               | ✅ (capped 100/day, sums match) |
| daily_diagnostics.csv dedup (3 runs → 30 rows) | ✅                              |
| Python analysis + plots                        | ✅                              |

## 14. Files

- `src/convective_adjustment.f90` — diagnostics (event log, probes, outputs)
- `app/main.f90` — day/step plumbing + A/D probes
- `data/output/convective_guard_events.csv` — 1,660 events (capped sample)
- `data/output/convective_analysis.csv` / `.txt` — aggregated analysis
- `python/analysis/convective_analysis.py`
- `python/plotting/convective_plots.py` + `figures/convective/*.png`
- `docs/wiki/stages/stage04/Stage4.3_convective_root_cause.md` — this report

## 15. Next Steps

- Stage 3.5 real grid (unchanged, DEFERRED).
- Any threshold/precision change requires promt.md item 5–6 procedure and
  explicit approval (NOT part of this stage).
