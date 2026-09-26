# Stage 10.20 — Ocean Initialization & Numerical Stabilization

**Date:** 2026-09-22
**Status:** COMPLETE — closed as **necessary-but-not-sufficient** (negative result)
**Baseline:** `03bb42c` (Stage 10.19); **this stage commit:** pending
**Classification target:** D — ocean-init / numerical stabilization attempt (data-level coverage fix adopted; physics stabilization NOT performed)
**Production decision target:** **KEEP_CURRENT physics**; ERA5 full-coverage data fix adopted as the *necessary* forcing precondition (data-level, not physics); residual CASE-D/T-03 float32-EOS instability fully characterized — requires an approved physics stage to resolve

---

## 1. Objective

Stabilize the ocean state so that the online-coupled production iceberg run
(Stage 10.19) can pass its acceptance gate: a 30-day `ICEBERG_PRODUCTION=true`
run where the iceberg executes real steps instead of reporting
`steps executed : 0` on the NaN zombie ocean.

Stage 10.19 classified the blocker:

- **CASE C** (force-coupling blocker): the ocean forcing delivered to the
  iceberg is invalid (NaN) from day 1 of the production run — 56.5 % of
  cells, start cell 15/18 levels NaN.
- **CASE D root cause** (T-03 family): the physical/numerical instability
  that produces the zombie state — Block 210 Thomas vertical-viscosity
  blowup after a Block 200 geostrophic spike from the EN4 thermal-wind init.

Stage 10.20 tested the first-stage hypothesis (insufficient ERA5 forcing
coverage = the day-1 trigger) and then characterized the *residual*
instability that survives the fix.

**Constraints (per stage plan):** no physics change in 10.20. Data-file
fixes are NOT physics (no approval needed). Changing the convective
threshold / EOS precision / Thomas solver / EN4 init / ocean physics is
FORBIDDEN without a RULES.md procedure and approval.

## 2. Baseline

Stage 10.19 (committed `03bb42c`) left the production executable running the
iceberg module behind the `ICEBERG_PRODUCTION=true` env gate (default OFF →
legacy bit-identical) with an explicit NaN validity guard in
`get_ocean_profile`. The ocean zombie state (CASE C/D) blocked all
online-coupled runs: day_01 56.5 % NaN, iceberg `steps executed : 0` on the
1-day/7-day/30-day gates.

The 10.19 run used the legacy default ERA5 file
`data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc`.

## 3. Method

### 3.1 Data fix: full-coverage ERA5 file (data-level, not physics)

The 3-day default file was superseded by a **full-coverage merged ERA5
January 2020 file**:

- `data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_merged.nc`
- 124 slices (4/day × 31 days), snowfall (`sf`) merged, ~39.6 MB,
  downloaded via the standard ERA5 pipeline (`python/era5/download_era5.py`
  `--include-snowfall` + merge).
- Purpose: eliminate any forcing-coverage/insufficiency contribution to the
  day-1 blowup (CASE C at the data level).

The file is passed via the CLI (`fpm run -- <run_id> <era5_file>`); the
default path in `src/param.f90:301` is **NOT changed in this stage** (see
§8, default-path recommendation).

### 3.2 Step cadence resolution (10.19 "720" vs actual 360)

10.19's limitation text says the acceptance gate is "30-day run with
`steps executed = 720`". The production loop runs the iceberg once per
barotropic step `III` with `mm2 = 12` steps per day (dt = 3600 s):

- 12 steps/day × 30 days = **360 steps** is the correct 30-day acceptance
  criterion (not 720).
- Verified empirically: the 3-day gate runs `36` steps = 12/day.

The "720" figure in the 10.19 report (D-17 limitation line) is a
documentation error — it is **not corrected in the 10.19 report** (reports
are not rewritten); this stage records the correction here (§8).

### 3.3 Gates run (all with `ICEBERG_PRODUCTION=true`)

| Run                       | ERA5 file                | Result                                                                  |
| ------------------------- | ------------------------ | ----------------------------------------------------------------------- |
| `stage10.20_gate3d_fullcov`  | full coverage (124 sl.) | **EXIT 0, 36 steps, 0 NaN days 1–3** (CASE C resolved at data level)    |
| `stage10.20_gate30d_fullcov` | full coverage (124 sl.) | **EXIT 0, 55 steps, NaN from mid-day-5 → acceptance NOT met (360)**     |
| `stage10.20_micro_d2`        | legacy default (0103)    | day-2 control – legacy-file behavior (prior NaN context)                |
| `stage10.20_micro_d2_fullcov`| full coverage            | day-2 control – clean                                                    |

### 3.4 Verbose stage-86 diagnostics

`ICEBERG_STAGE86_DIAG=verbose` captures the full field state per stage tag
(B_wind, C_after_heat, D_after_redis, E_after_adv, F_after_conv,
G_before_B200 [velocity], H_after_B200, I_after_B210, J_after_B280) at every
`III` of every day, with NaN counters per variable. This located the exact
first-NaN event of the residual instability.

## 4. Results

### 4.1 3-day gate PASS — the day-1 zombie is gone

`stage10.20_gate3d_fullcov` (full coverage): EXIT 0, iceberg
`steps executed : 36` (12/day × 3 days), NaNflag = 0 on all three days. This
is the first time a production `ICEBERG_PRODUCTION=true` run has executed
iceberg steps on a clean ocean. The data-level coverage fix **eliminates the
day-1 CASE-C zombie**.

### 4.2 30-day gate FAIL — acceptance not met

`stage10.20_gate30d_fullcov`: the ocean is clean on days 1–4, then dies
**mid-day 5**; from day 6 onward the zombie state is structurally identical
to 10.19 (T frozen, 142,081/251,370 = 56.5 % NaN cells). The iceberg
executed **55 steps** (≈ 4.6 days) then froze:

```
   steps executed      :           55
   final lat/lon       :    75.0005341      /    30.0800781
   final L/W/H         :    99.2816315      /    99.2816315      /    99.9405289
   final mass [kg]     :    896439168.
EOS [g/cm3] min=           NaN max=           NaN mean=           NaN n=  142081
   >>> Successfully wrote NetCDF file: .../results_day_final.nc
```

**Acceptance criterion 360 steps NOT met (55/360).** The online-coupled
production path remains blocked.

## 5. Residual instability forensic (CASE D characterization)

### 5.1 First-NaN chain (verbose diag log)

The first NaN of the full run appears on **day 5, III=6** — NOT in Block
200/210 (the 10.19 CASE-D site), but at the **convective adjustment output
`F_after_conv`** and only in **density (RO)**, 198 cells, while U/V/T/S still
show 0 NaN at that moment:

```
1013: STAGE86 [F_after_conv] d= 5 III= 6  NaN_U=0 NaN_V=0 NaN_W=0 NaN_T=0 NaN_S=0 NaN_RO=198
      T=[-7.90E+22, +2.80E+23] C  S=[-5.00E+20, +1.83E+21]  RO=[-4194305., +16777215.] g/cm3
      U=[-5.24E+08, +4.39E+08] m/s  (velocities already divergent, but not yet NaN)
1019: STAGE86_VEL [H_after_B200] d= 5 III= 6  NaN_U=332  NaN_V=332
```

and the cascade over the next IIIs:

```
d5 III=7: NaN_U=333  NaN_T=934  NaN_RO=969
d5 III=8: NaN_T=115505  (46 %)  → H_after_B200 NaN_U=107987
d5 III=9: NaN_T/S/RO=142081  (100 % of wet cells)
```

So: density NaN is the **first** NaN; velocities and T/S follow within 1–2
substeps. This differs from the 10.19 day-1 sequence (Block 200 → Block 210
velocity blowup) — the residual day-5 death is **density-driven**, not
directly a Thomas-solver velocity blowup.

### 5.2 T/S corruption precedes the blowup (day 4 already nonphysical)

Day 4 (`results_day_04.nc`, clean day in the *NaN* sense — 0 NaN cells) is
already basin-wide nonphysical:

| variable                   | min        | max        | NaN |
| -------------------------- | ---------- | ---------- | --- |
| T (converted °C)           | −45.43     | +49.54     | 0   |
| S (mass fraction)          | −0.0099    | +0.040     | 0   |
| ρ anomaly (kg m⁻³)         | −43.66     | +9.54      | 0   |

Negative salinity and ±50 °C temperature on a January Arctic run are
physically impossible. The corruption accumulates gradually over days 1–4
(no discontinuity), consistent with a **slow instability seeded from day 1**,
becoming nonphysical by day 4 and divergent mid-day-5.

### 5.3 Convective-adjustment guard saturation — root mechanism

The CA 1000-iteration guard saturates **from day 1** of the full-coverage
run (daily diagnostics CSV):

| day | ca_nmix      | ca_max_iter | ca_guard_hits | ca_affected_cols | euu (KE)      |
| --- | ------------ | ----------- | ------------- | ---------------- | ------------- |
| 1   | 2.224e+08    | 1001        | 67,919        | 128,503          | 8.653e+15     |
| 2   | 1.969e+08    | 1001        | 58,413        | 129,376          | 1.806e+16     |
| 3   | 1.884e+08    | 1001        | 53,961        | 127,296          | 2.607e+16     |
| 4   | 1.794e+08    | 1001        | 49,291        | 127,447          | 4.457e+16     |
| 5   | 7.360e+08    | 1001        | 81,440        | 128,608          | 5.816e+16     |
| 6+  | 1.575e+09    | 1001        | 131,592       | 131,592          | ~2–5e+16 (zombie) |

- `ca_max_iter = 1001` (= 1000 + 1) on **every day**: the guard's iteration
  cap is hit every daily diagnostic from day 1 — the adjustment never
  converges.
- Guard events CSV shows the residual inversion **pinned at
  `resid_inv = 1.1921E-07`** for essentially all events — i.e.
  **2⁻²³ ≈ 1.19e-7**, the float32 quantization step of the EOS (the exact
  documented root cause of Stage 4.3/4.4 and KNOWN_ISSUES T-01).
- The daily max inversion magnitude grows monotonically with the state
  degeneration: 3.2E-4 (day 1) → 1.25E-2 (day 4) → 0.36 (day 5, III=1) →
  79.3 (day 5, III=6) → 0 columns remain inverted at day 5 III=12 (fully
  NaN).
- Kinetic energy grows monotonically days 1→5 (euu 8.65e15 → 5.82e16),
  then drops/recomputes as NaNs take over.

### 5.4 Mechanism synthesis

1. **Necessary step (this stage, adopted):** the ERA5 forcing coverage was
   at least partly responsible for the day-1 death — with the full-coverage
   file, days 1–4 are clean and the iceberg runs 55 real steps (vs 0 at
   10.19). **CASE C is resolved at the data level.**
2. **Not sufficient:** the float32-EOS / convective-adjustment instability
   (T-01/T-03 family) survives. From day 1 the EOS density quantization
   `2⁻²³ ≈ 1.19e-7` sits *above* the 0.9e-7 convective threshold, so the CA
   cycle cannot converge within the 1000-iteration guard; residual
   inversions are parked at 1.19e-7 and the guard saturates every day. The
   residual drives slow T/S/ρ corruption (nonphysical by day 4), which
   becomes a density-driven divergence on day 5 (first NaN = `NaN_RO` at
   `F_after_conv`, III=6) and the familiar zombie state from day 6.
3. The 10.19 CASE-D site (Block 200/210 velocity blowup on day 1) is **not
   reproduced** with full coverage; the residual death is **density-first at
   `F_after_conv`** — a different manifestation of the same T-03 float32-EOS
   family.

This is exactly the instability the RULES.md constraint flags: *"Do not
raise the 0.9e-7 convective threshold or switch EOS to double — root cause
is float32 2⁻²³ quantization; needs RULES.md procedure + approval."* The
fix is a **physics decision** (EOS precision / threshold / guard policy) and
is therefore outside a no-physics stage.

## 6. Findings

- **F-1 (resolved):** ERA5 forcing insufficiency contributed to the day-1
  zombie. Full-coverage January file (124 slices) → days 1–4 clean, 55 real
  iceberg steps. CASE C force-coupling blocker removed at the data level.
- **F-2 (residual, OPEN):** float32 EOS quantization 2⁻²³ vs CA threshold
  0.9e-7 → CA guard saturates from day 1 (maxiter=1001 every day), residual
  inversions pinned at 1.1921E-07; slow T/S/ρ corruption → day-4
  nonphysical fields (−45…+50 °C, S<0) → day-5 mean-day density-first
  divergence (first NaN = NaN_RO at F_after_conv, III=6) → zombie from day
  6. 30-day acceptance (360 steps) NOT met (55/360).
- **F-3 (corrected):** the 10.19 "720-step" acceptance figure is a doc
  error; actual cadence is 12 steps/day → **360 steps** for 30 days
  (verified: 3-day gate = 36 steps). Recorded here; 10.19 report not
  rewritten.
- **F-4:** with full coverage the iceberg drifts ~0.0005° lat / 0.08° lon
  and loses ~0.4 % mass over 55 steps before the ocean dies — the
  online-coupled path is *started correctly*, then blocked by F-2.

## 7. Conclusion (necessary-but-not-sufficient)

The Stage 10.20 hypothesis — that ERA5 forcing coverage was a sufficient
cause of the ocean zombie state — is **refuted**. The coverage fix is
**necessary** (CASE C removed; first clean gate runs; 0 → 55 steps) but
**NOT sufficient**: the residual float32-EOS / CA-guard instability
(T-03 family) kills the ocean on day 5 through a density-first divergence,
and the 30-day acceptance is not met.

Closing this stage as **necessary-but-not-sufficient** with a fully
characterized residual:

- **Adopted:** full-coverage ERA5 file as the production forcing input
  (data-level fix, recommendation to update the default path — §8).
- **Residual:** CASE-D/T-03 float32-EOS instability, mechanism now closed
  (CA guard saturation from day 1 → pinned 2⁻²³ residual → slow T/S/ρ
  corruption → day-5 density-first NaN). Resolution requires a dedicated
  **physics** stage per RULES.md (EOS precision/CA threshold/guard policy
  change with approval), or a numerical preconditioner study (Thomas /
  pressure solvers) under the same procedure.
- **Outcome for the online-coupled path:** still blocked (55/360 steps);
  the offline real-forcing path (TEST_11 family) remains the sanctioned
  production iceberg mode.

## 8. Decisions & corrections

- **D-18 (added, ACTIVE):** Stage 10.20 closed as necessary-but-not-
  sufficient — ERA5 full-coverage data fix adopted (CASE C resolved at data
  level), residual CASE-D/T-03 float32-EOS instability characterized, 30-day
  acceptance NOT met; resolution deferred to an approved physics stage.
  See `docs/DECISIONS.md`.
- **Default-path recommendation (NOT applied):** point
  `src/param.f90:301` `era5_input_file` to
  `data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_merged.nc`.
  Not changed in this stage because the residual instability makes the
  default-file change cosmetic until the physics stage lands; the legacy
  default also keeps all pre-10.20 runs reproducible. Apply together with
  the physics fix.
- **Cadence correction:** 30-day acceptance = 360 steps (12/day), not 720
  (10.19 doc error). Note recorded here; 10.19/reports not rewritten.

## 9. Files, artifacts, commands

Run outputs:

- `data/runs/stage10.20_gate3d_fullcov/` — EXIT 0, 36 steps, 0 NaN
- `data/runs/stage10.20_gate30d_fullcov/output/nc/results_day_00..30(+final).nc`
- `data/runs/stage10.20_gate30d_fullcov/output/csv/daily_diagnostics.csv`
  (ca_* and euu columns, §5.3)
- `data/runs/stage10.20_gate30d_fullcov/output/csv/convective_guard_events.csv`
  (3001 events; `resid_inv` pinned at 1.1921E-07)
- `data/runs/stage10.20_gate30d_fullcov/output/iceberg_production.csv`
- Diag log: `/tmp/opencode/stage1020/gate30d_diag.log` (verbatim first-NaN
  chain, §5.1); gate log `/tmp/opencode/stage1020/gate30d.log`

Forcing:

- `data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_merged.nc`
  (124 slices, snowfall-merged)

Commands:

```bash
ICEBERG_PRODUCTION=true fpm run --flag "-I/usr/include" -- stage10.20_gate3d_fullcov \
    data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_merged.nc
ICEBERG_PRODUCTION=true fpm run --flag "-I/usr/include" -- stage10.20_gate30d_fullcov \
    data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_merged.nc
# verbose diagnostics:
ICEBERG_PRODUCTION=true ICEBERG_STAGE86_DIAG=verbose fpm run --flag "-I/usr/include" -- ... 
```

## 10. Verification

- Full fpm test battery: PASS — `fpm build` + `fpm test --flag "-I/usr/include"`
  (54 targets) after `rm -rf build`, `TEST_EXIT=0`, 0 failed checks.
  Log: `/tmp/opencode/stage1020/battery_fpm.log` (run 2026-09-22T20:11:13+03:00).
- Full Python battery: PASS — all `python/tests/test_*.py` (17 files) +
  `python/validation/low_flow_fortran_comparison.py`, `FAILED_COUNT=0`.
  Log: `/tmp/opencode/stage1020/battery_py.log`.
- `git diff --check`: clean.
- Source changes this stage: only the Stage-10.19-pending iceberg print
  format fix in `app/main.f90` (17-token format; diagnostics only, no
  physics — no further `src/` change).
- Data file is gitignored (under `data/`), not committed.

---

**Next stage (candidate):** approved physics stabilization per RULES.md —
float32-EOS precision (double) or CA threshold/guard policy change, or
preconditioned-solver study — acceptance: 30-day `ICEBERG_PRODUCTION=true`
gate with `steps executed = 360` on a clean ocean (day-3 gate already
demonstrates the required cleanliness for days 1–3).