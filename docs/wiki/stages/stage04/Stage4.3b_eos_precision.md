# Stage 4.3b — IEEE-754 / Float-Precision Verification of the EOS Root Cause

## Summary

Stage 4.3b **independently verifies at the bit level** the float32
quantization mechanism proposed in
`docs/wiki/stages/stage04/Stage4.3_convective_root_cause.md`. It adds a **diagnostic-only**
Fortran test (`test/eos_precision_test.f90`), a standalone Python companion
(`python/analysis/eos_precision_analysis.py`), and a compiler-flag experiment.
**No production physics is changed** — EOS, threshold `0.9e-7`, mixer, guard,
blocks 200/210/280 are byte-for-byte untouched.

**Classification: A. CONFIRMED.** The production float32 EOS
`RO = 1.0/(0.698 + aa/bb) − 1.02` has an **attainable-value grid of exactly
`2^-23 = 1.1920929e-7`**, so the historical threshold `0.9e-7` is
**mathematically unreachable**: no nonzero residual difference can be
`≤ 0.9e-7`, only exact `0` can. The 1000-iteration guard is therefore the
correct, physical exit. One **precision nuance** refines Stage 4.3 wording
(see §5): `spacing(RO)` at the RO magnitude is `2^-31/2^-32`, NOT `2^-23` —
but the _attainable set_ (image of the EOS) and every residual difference are
exact multiples of `2^-23`, which is the quantity that matters.

## 1. What Was Added (Diagnostics / Tests Only)

| File                                        | Content                                                                                                                                                                                                                                                     |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test/eos_precision_test.f90`               | 8-check standalone Fortran test: REAL kind/storage, EOS reproduction (float32, exact production operation order), `spacing`/`nearest`, TRANSFER bit-level `next representable`, dense-grid enumeration, REAL64 reachability. Auto-discovered by `fpm test`. |
| `python/analysis/eos_precision_analysis.py` | numpy float32/float64 EOS reproduction, random-pair reachability, guard-event reconstruction from CSV + daily NetCDF → `data/output/eos_precision_summary.csv` + `eos_precision_report.txt`.                                                                |
| `/tmp/opencode/eos_compiler_test.f90`       | standalone (NOT committed): identical EOS output across `-O0/-O2/-O3/-fno-fast-math/-ffast-math`.                                                                                                                                                           |

## 2. Verified Fact: Production REAL Is float32

From `test/eos_precision_test.f90` check 1 (matches `param.f90` declarations,
no `kind` anywhere):

```
default REAL: kind=4, storage=32 bits, precision=6, range=37  -> IEEE-754 binary32
```

So `T, S, aa, bb, X, RO` and the threshold `eps_density = 0.9e-7_sp` are all
float32 (`0.9e-7` prints as `9.0000E-08`).

## 3. EOS Reproduction (Bit-Exact)

The production formula (`src/equation_of_state.f90`):

```fortran
aa = 1779.5 + (11.25 - 0.0745*t)*t - (3800.0 + 10.0*t)*s
bb = 5891.0 + 3000.0*s + (38.0 - 0.375*t)*t
ro = 1.0/(0.698 + aa/bb) - 1.02
```

Reproduced in `eos32()` / `eos64()` with **identical operation order**, and
cross-validated **bit-exact** against Fortran stored density in the daily
NetCDF (e.g. `results_day_XX.nc` density `0x3b7b2800` reproduced exactly by
Python float32 EOS). Representative values:

| T, S      | X32 (bits)   | RO32 (bits)  | RO64         | RO64 − RO32 |
| --------- | ------------ | ------------ | ------------ | ----------- |
| 15, 0.033 | `0x3f8320eb` | `0x3b918f00` | 0.0025335799 | +6.3e-10    |
| 10, 0.034 | `0x3f835871` | `0x3bc91500` | 0.0027479343 | +5.7e-10    |
| 0, 0.033  | `0x3f8365c0` | `0x3bd66400` | 0.0027728952 | +5.8e-10    |
| 25, 0.035 | `0x3f8303f2` | `0x3b692c00` | 0.0021222957 | +6.7e-10    |

## 4. Spacing Facts

- `spacing(X)` for `X ∈ [1, 2)` is **exactly `2^-23 = 1.1920929e-7`** (all
  float32 in `[1, 2)` are exact multiples of `2^-23`).
- `spacing(RO)` at `RO ≈ 0.004` (binade `2^-8..2^-9`) is **`2^-31/2^-32`
  = 4.6566e-10 / 2.3283e-10** — i.e. NOT `2^-23`. This is the representable
  grid of an individual float32 at that magnitude.
- However, the **attainable RO set** (the image of the EOS) is quantized at
  `2^-23`:

```
X  = 1/(0.698 + aa/bb)                 float32 in [1,2) -> exact multiple of 2^-23
1.02                                      float32 in [1,2) -> exact multiple of 2^-23
RO = X - 1.02: exact difference is a multiple of 2^-23, and since
   2^-23 = 256 * 2^-31 (= 512 * 2^-32), the difference is EXACTLY
   representable on the RO binade -> NO rounding occurs.
```

So **every attainable RO value is an exact integer multiple of `2^-23`**, and
any residual `RO(k) − RO(k+1)` is a multiple of `2^-23`. Verified on
**7,792,470 stored density values** from the daily NetCDF: **all** are exact
multiples of `2^-23` (0 exceptions).

## 5. Dense-Grid and Random-Pair Reachability

| Scan                                                                               | min nonzero \|ROa−ROb\|               | pairs ≤ 0.9e-7 | result                                                                |
| ---------------------------------------------------------------------------------- | ------------------------------------- | -------------- | --------------------------------------------------------------------- |
| Dense grid (T −2..26 step 0.01 × S 0.033..0.035 step 0.0001), 33,931 distinct RO32 | `1.1920929e-7` = exactly 1 ulp(2^-23) | **0**          | threshold unreachable                                                 |
| 2e6 random float32 T/S pairs (2×0−25 °C × 0.033−0.035)                             | `1.1920929e-7` = exactly 1 ulp(2^-23) | **0**          | threshold unreachable; 100.000% of diffs are exact multiples of 2^-23 |
| Same dense grid in **REAL64**                                                      | `1.258e-12`                           | **> 0**        | `0.9e-7` IS reachable in float64                                      |

**Conclusion:** `0 < diff ≤ 0.9e-7` has **zero** attainable solutions in
float32 and nonzero solutions in float64. The float32 quantization is the
sole cause; the threshold is mathematically unreachable by construction.

## 6. Production Guard Events (Reconstruction)

From `data/output/convective_guard_events.csv` (1,660 capped events) +
`results_day_XX.nc`:

- All **1,660** reconstructed columns have RO values that are exact multiples
  of `2^-23`; all nonzero residuals are exact multiples of `2^-23`.
- Logged `resid_inv`: min = `1.1921e-07` (= `2^-23`), max = `2.3842e-07`
  (= `2·2^-23`) — matching Stage 4.3's `1,658/1,660 = 1 ulp` split.
- First event (day 2, step 3, i=51, j=53, ki=18): `iter_count=1001`,
  `nmix=2009`, `k_problem=1`, `resid_inv = 1.1921E-07`. The end-of-day NetCDF
  snapshot for that column is **fully converged** (resid at `k_problem` = 0),
  confirming the guard fires on a transient 1-ulp residual that mixing cannot
  remove, not on a persistent profile defect.
- CSV `resid_inv` is formatted ES12.4 (4 sig figs), so the string is not
  bit-exact; the raw `1.1921E-07` parses to float32 bits `0x34000032`
  (≈ `2^-23 · 1.000006`) — consistent with an exact-`2^-23` residual rounded
  by the format.

## 7. Compiler Effect: NONE

`eos_compiler_test.f90` compiled the identical EOS under:

| flags                | md5 of RO output |
| -------------------- | ---------------- |
| `-O0`                | identical        |
| `-O2`                | identical        |
| `-O3`                | identical        |
| `-O2 -fno-fast-math` | identical        |
| `-O2 -ffast-math`    | identical        |

The quantization is a property of IEEE-754 float32 arithmetic, independent of
optimization.

## 8. Classification (Reassessed, Stage 4.3b)

**A. CONFIRMED — root cause = float32 EOS quantization (`2^-23` attainable
grid) vs. threshold `0.9e-7` below the grid.**

- The Stage 4.3 conclusion is **correct** in substance.
- **Precision nuance (refinement, not correction of substance):** Stage 4.3
  stated "every density value sits on a grid of spacing `2^-23`". Strictly,
  `spacing(RO) = 2^-31/2^-32` for RO near 0.004. The correct statement is:
  _the attainable RO values and all residual differences lie on the `2^-23`
  grid_ (because `RO = X − 1.02` is an exact difference of two `[1,2)`
  float32 multiples of `2^-23`). `spacing()` reports the representable grid,
  not the attainable set. All observable quantities that drive the guard —
  residuals `RO(k) − RO(k+1)` — are multiples of `2^-23`, so the mechanism
  and conclusion stand unchanged.

### Why NOT B / C / D

- **Not B (code regression):** no `kind`/precision change anywhere in the
  modernization; `-Wall -Wextra` and the compiler-flag experiment show
  identical IEEE-754 float32 results.
- **Not C (missing physics):** residual is provably the float32 quantization
  floor (min nonzero diff ≡ `2^-23`), and float64 on the same grid reaches
  `0.9e-7`.
- **Not D (data problem):** the bit-level reconstruction is cross-validated
  bit-exact against the daily NetCDF and reproduces the CSV `resid_inv`
  distribution.

## 9. Physics Impact

**None.** No production file changed. The convective adjustment is physically
converged when the guard fires (all real inversions removed; only the float32
1-ulp numerical residual remains), exactly as Stage 4.3 stated. Conservation
remains at machine precision.

## 10. Validation

| Check                                                              | Result                          |
| ------------------------------------------------------------------ | ------------------------------- |
| `gfortran test/eos_precision_test.f90 -Wall -Wextra`               | ✅ no warnings                  |
| `eos_precision_test` standalone run                                | ✅ 8/8 checks, `STOP 0`         |
| `fpm build -I/usr/include -Wall -Wextra`                           | ✅                              |
| `fpm test -I/usr/include` (conv 15/15, EOS 7/7, precision, NetCDF) | ✅                              |
| `fpm run -I/usr/include -fcheck=all -ffpe-trap` 30-day ERA5        | ✅ unchanged, EXIT=0            |
| Python `eos_precision_analysis.py`                                 | ✅ summary CSV + report written |
| Compiler-flag experiment                                           | ✅ bit-identical md5            |

## 11. Files

- `test/eos_precision_test.f90` — new 8-check diagnostic test (committed)
- `python/analysis/eos_precision_analysis.py` — new Python companion (committed)
- `data/output/eos_precision_summary.csv` / `eos_precision_report.txt` — generated
- `/tmp/opencode/eos_compiler_test.f90` — compiler experiment (NOT committed)
- `docs/wiki/stages/stage04/Stage4.3b_eos_precision.md` — this report

## 12. Next Steps

- Stage 3.5 real grid — DEFERRED (unchanged).
- Any fix (raise threshold above `2^-23`, or double-precision EOS) requires
  promt.md procedure + approval — NOT part of this stage.
- Stage 4.4 (whatever it is) — NOT started automatically.
