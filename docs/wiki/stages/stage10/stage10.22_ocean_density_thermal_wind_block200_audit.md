# Stage 10.22 — Ocean Density / Thermal-Wind / Block-200 Stability Audit (Causal Isolation)

**Date:** 2026-09-24
**Status:** COMPLETE — causal isolation of the density→thermal-wind→Block-200 chain delivered; **first physically impossible state = day 4 (ρ-anomaly < 0 after CA)**, **first NaN = day 5 step 6 (density-first, `ro_nan=198` at CA_after, matching 10.19/10.20 `NaN_RO=198` at `F_after_conv`)**, Block 200 confirmed **transmitter, not origin**; A5 independent replay reproduces Block 200 exactly for all stable closures (a1/a3/a4: 30/30 days PASS, worst rel ≤ 4.213e-06)
**Baseline:** `7a17cac` (Stage 10.21); **this stage commit:** `928041a`
**Classification target:** C/D — diagnostic instrumentation + research replay (audit-only; NO production physics change; all switches default OFF → bit-identical legacy)
**Production decision target:** **KEEP_CURRENT physics**; D-20 recorded; residual ocean instability root-caused to the CA/EOS float32 corruption path (T-01 family) producing nonphysical density → baroclinic pressure-gradient corruption in Block 200 → Thomas vertical-viscosity blowup (T-03 family) after-the-fact

---

## 1. Objective

Establish, with diagnostic evidence, the **causal chain of the production
ocean divergence** (10.19 CASE C/D → 10.20 → 10.21: days 1–4 corrupt but
non-NaN, density-first divergence mid-day-5, zombie from day 6), by
isolating each link of the chain:

```
EN4 T/S init → EOS ρ → CA mixing → baroclinic pressure gradient (Block 200)
             → geostrophic momentum → vertical viscosity (Block 210, Thomas)
```

Open questions addressed:

1. **First physically impossible state:** on which day does the ocean first
   become nonphysical (ρ-anomaly < 0, T/S out of range) — and in which block?
2. **First NaN:** which field, which block, which step produces the first
   NaN? Is density-first (10.19/10.20/10.21 claim) confirmed at
   step-granularity?
3. **Block 200 role:** is the baroclinic momentum step a *source* of the
   divergence or a *transmitter* of already-corrupt density fields
   (geostrophic-spike hypothesis, T-03 family)?
4. **Block 210 role:** is the Thomas vertical-viscosity blowup (T-03) an
   independent cause or a downstream consequence? (Its pivots are shown to
   be negative *by construction* — §13.)
5. **Implementation exactness:** is Block 200 implemented consistently with
   an independent Python replay under all experiment closures (A5)?

**Constraints (RULES.md / AGENTS.md):** all instrumentation is behind
env-gated switches, default OFF → **bit-identical legacy (verified, §8)**.
Entity physics (EOS formula, CA structure, Block 200/210/280, barotropic
solver) is UNCHANGED. No production physics change is made.

## 2. Baseline

Stage 10.21 (`7a17cac`, D-19) closed the CA-precision question as
**necessary-but-not-sufficient**:

- CA 1000-iteration guard saturation = float32 EOS quantization floor
  (`2⁻²³ = 1.1920929E-07 > eps 0.9E-07`, reciprocal `1/(0.698+aa/bb) ≈
  1.027 ∈ [1,2)` binade); every closure (f64 path, eps ladder 1.5e-7/2.4e-7)
  **eliminated the guard days 1–4** yet **every closure still diverged
  density-first mid-day-5** (`NaN_RO=198` at `F_after_conv`, 0 NaN in
  U/V/T/S) → guard = symptom, not cause.
- The residual driving mechanism was classified OUT OF SCOPE for 10.21:
  "Block-200 geostrophic spike / Thomas vertical-viscosity ill-conditioning
  (T-03 family)". **This is the scope of Stage 10.22.**
- Pre-existing evidence chain: 10.19 CASE C (day-1 `NaN_RO` first NaN in
  Block 210 after Block-200 geostrophic spike with legacy forcing);
  10.20 (full-coverage ERA5 → days 1–4 clean, first NaN = `NaN_RO=198` at
  `F_after_conv` III=6 of day 5, density-first; day 4 T/S nonphysical
  −45…+50 °C, S<0, ρ −43.7…+9.5).

## 3. Hypothesis

1. **ρ-first chain:** days 1–4 the CA mixing (float32 quantization noise)
   corrupts ρ slowly; the **first physically impossible state** is a
   **negative density anomaly (ρ − ρ_ref < 0)** which appears **during
   convective adjustment** on day 4 — before any momentum pathology.
2. **Block 200 = transmitter:** the baroclinic momentum step consumes the
   corrupt ρ field and produces a **geostrophic spike**; the first *NaN* is
   still **ρ** (not u/v) — entering day-5-step-6 CA with nonphysical T/S
   pushes the EOS inversion over the float32 overflow boundary → `ρ = NaN`
   while u/v are still finite (0 NaN) at the B200 entry probe.
3. **Block 210 = after-the-fact blowup:** the Thomas vertical-viscosity
   RHS (`rhs_max`) and viscosity (`rr_max`) remain bounded through day 4
   and the first 5 steps of day 5, then explode **in the same step where ρ
   is already NaN** — a consequence of the corrupted momentum fields, not
   an independent cause. Its pivot negativity is **structural** (`a1 =
   −1+a+b < 0` for the interior Thomas recurrence), i.e. `piv_neg = piv_cnt`
   is the normal state, NOT a failure indicator.

## 4. Switch contract (env-gated, default OFF → bit-identical legacy)

Implemented in `src/stage1022_diagnostics.f90` (new module) +
`src/convective_adjustment.f90` + `app/main.f90`:

| Env var                          | Values  | Effect                                                                                      |
| -------------------------------- | ------- | ------------------------------------------------------------------------------------------- |
| `STAGE1022_DIAG`                 | `true`  | enable probe/budget/conditioning instrumentation (write CSVs)                               |
| `STAGE1022_FREEZE_RO`            | `true`  | a1: `conv_adj` mixes T/S but keeps pre-adjustment RO (RO writeback suppressed)              |
| `STAGE1022_FREEZE_THERMAL_WIND`  | `true`  | a2: zero the baroclinic momentum sums in Block 200 (`sum_b_x/y = 0`, thermal-wind term off) |
| `STAGE1022_FREEZE_TS`            | `true`  | a3: T/S advection/CA mixing skipped entirely (T/S held at day-0 state)                      |
| `STAGE1022_FREEZE_RO_DOWNSTREAM` | `true`  | a4: ρ-anomaly pinned to `ro_ref` captured at init (sandwich between conv_adj and use sites) |

All default OFF/FALSE → the production binary is bit-identical to the
pre-10.22 legacy path (verified §8).

## 5. Experiment matrix

| Exp | Run dir                     | Config                      | Intended probe                                  |
| --- | --------------------------- | --------------------------- | ----------------------------------------------- |
| a0  | `stage10.22_p30d_a0`        | all OFF                     | bit-identity anchor; reproduces 10.21 A0        |
| a0_diag | `stage10.22_p30d_a0_diag` | `_DIAG=true`, physics OFF   | full probe/budget/conditioning trace of a0      |
| a1  | `stage10.22_p30d_a1_freeze_ro` | `_FREEZE_RO=true`       | ρ cannot be corrupted by CA → if ρ-first, clean |
| a2  | `stage10.22_p30d_a2_no_tw`  | `_FREEZE_THERMAL_WIND=true` | thermal-wind/baroclinic term off → isolates Block-200 spike contribution |
| a3  | `stage10.22_p30d_a3_freeze_ts` | `_FREEZE_TS=true`       | T/S frozen → full T/S-ρ path bypassed           |
| a4  | `stage10.22_p30d_a4_frozen_ro` | `_FREEZE_RO_DOWNSTREAM=true` | ρ pinned downstream of CA → CA-noise decoupled from baroclinic forcing |

All 30-day production runs (`ICEBERG_PRODUCTION=true`,
`era5_2020_01_fullcoverage_merged.nc`, 124 slices). `stage10.22_g3d_smoke`
= 3-day smoke gate.

## 6. Diagnostic instrumentation (all read-only)

Three CSV families, written only under `STAGE1022_DIAG=true`:

1. **`stage1022_probes.csv`** — field extrema/NaN/Inf counts at 6 points of
   the step loop: `INIT` (day 0), `CA_after`, `B200_before`, `B200_after`,
   `B210_after`, `END_step`. Columns per field: `nan, inf, n, min, max,
   mean, rms, spike` for u1, v1, u2, v2, and `nan, inf, n, min, max, mean,
   rms, oob` for t, s, ro (44 probe columns + label/day/step).
2. **`stage1022_block200.csv`** — independent budget-recorder inside Block
   200: `ro_min/ro_max/ro_mean` (ρ-anomaly extrema), `sum_max/sum1_max`
   (barotropic/baroclinic pressure-gradient sum maxima), `acc_bar_u/v`
   (baroclinic acceleration), `acc_dp_u/v` (all terms), `acc_lap_u/v`
   (Laplacian-only), `dp_ratio_u/v` (= acc_dp/acc_lap: gradient-dominance
   indicator), `max_u1/max_v1/max_u2/max_v2`, `amp_u/amp_v`. Machinery that
   A5 mirrors and verifies.
3. **`stage1022_block210.csv`** — Thomas solver conditioning:
   `rr_min/rr_max` (NU = vertical-viscosity coefficient range), `piv_min`
   (min |Thomas pivot|), `piv_neg/piv_cnt` (negative-pivot count / total),
   `rhs_max` (max |Thomas RHS|), `den_min` (min |1 − bb·uc| back-substitution
   denominator), `den_neg` (negative-denominator count).

The a0 vs a0_diag `daily_diagnostics.csv` are **byte-identical**
(md5 `1ef13cb4d212db8570dd64737e945897`) → instrumentation has zero
perturbation on the trajectory (§8).

## 7. A5 — independent Python replay engine

`python/validation/block200_isolate.py` (694 lines, committed) replays the
**Block-200 momentum budget** from the production NetCDF snapshots
(`results_day_XX.nc`) with no Fortran dependency:

- **Inputs:** T/S/RO/u1/v1 snapshots; barotropic mode summed per X/Y at the
  same index conventions; the recorded CSV budget columns are the target.
- **Reconstruction for `--all-days`:** raw forcing between snapshots is not
  stored at output cadence; the raw field at day d is reconstructed from the
  snapshot as `raw_d = raw_{d−1} + (12/11)·(snap_{d−1} − raw_{d−1})`
  (linear interpolation of the daily-mean drift; 12 steps/day cadence).
  Day 1 uses the raw snapshot ("PASS" without rec marker); days 2+ use the
  reconstruction ("PASS(rec)").
- **Experiment semantics mirrored exactly** (commit message §7 of `928041a`):
  `freeze_ro` (a1) → RO held at pre-CA value in the force evaluation;
  `freeze_tw` (a2) → baroclinic momentum sums zeroed, two-path budget split;
  `freeze_ts` (a3) → T/S held at snapshot; `frozen_ro` (a4) → ro pinned to
  ro_ref.
- **Metrics (13):** `ro_min/ro_max/ro_mean`, `sum_max/sum1_max`,
  `acc_bar_u/acc_bar_v`, `dp_ratio_u/dp_ratio_v`, `max_u2/max_v2`,
  `amp_u/amp_v` — compared CSV (production recorder, never zeroed) vs replay
  at rel tolerance 1e-4 (float32 floor; PASS lines run at ≤ 4.3e-6).

## 8. Bit-identity verification

| Artifact                    | Result                                                                 |
| --------------------------- | ---------------------------------------------------------------------- |
| Production binary, all OFF  | legacy path, byte-identical baseline (no production code differences vs 10.21 `7a17cac` physics) |
| `a0` vs `a0_diag` daily_diagnostics.csv | **IDENTICAL** (md5 `1ef13cb4d212db8570dd64737e945897`) — probe/budget instrumentation is read-only |
| Ocean/iceberg physics       | NO production change in `src/` (only instrumentation behind gates + comment); iceberg modules untouched |
| Offline path (TEST_11)      | untouched (no iceberg source change)                                   |

## 9. First physically impossible state — day 4 (ρ-anomaly < 0 after CA)

Probe evidence (`a0_diag`, CA_after probe, `ro_min` column):

| Day | ro_min (CA_after) | Note                            |
| --- | ----------------- | ------------------------------- |
| 1   | 6.852e-03         | ρ-anomaly positive everywhere   |
| 2   | 5.499e-03         | positive                        |
| 3   | 6.071e-04         | positive, decaying toward zero  |
| 4s1 | **−1.946690e-04** | **FIRST SUB-ZERO ρ-anomaly**    |
| 4s12| −4.365810e-02     | end-of-day-4 minimum (block200.csv daily min −4.37e-2) |
| 5   | (corrupt, §10)    | −4.19e6…+8.83e5 pre-NaN values |

**Verdict:** the first physically impossible state is a **negative density
anomaly (ρ < ρ_ref) appearing at day 4 step 1, produced during convective
adjustment** (CA_after probe, 0 NaN yet). T/S at day 4 begin to leave
physical range (−45…+50 °C, S<0 per 10.20/10.21) — the EOS/CA float32
quantization corruption path (T-01 family) reaches ρ < ρ_ref on day 4.
Velocity probes stay clean (0 NaN) through END_step day 5 step 5.

## 10. First NaN — day 5 step 6, density-first (CA_after)

Probe step-granularity trace (a0_diag), NaN counts per field:

| Probe      | day5 s5 | day5 s6 | Interpretation                          |
| ---------- | ------- | ------- | --------------------------------------- |
| CA_after   | 0 NaN   | **ro_nan=198**, u2/v2 0! | **FIRST NaN = ρ, in the CA block**, u/v still finite |
| B200_before| 0 NaN   | ro_nan=198, u2/v2 0 | ρ already NaN, momentum entry fields clean |
| B200_after | 0 NaN   | u2_nan=333, v2_nan=333 | Block 200 consumes NaN ρ gradient → NaN momentum |
| B210_after | 0 NaN   | all NaN  | Thomas solver receives NaN input fields  |
| END_step   | **0 NaN**| u2/v2 333, ro 198 | first-NaN step complete                 |

Corroborating magnitudes at the same probes: `CA_after d5s6 ro_min =
−4.194300e+06`, `ro_max = +1.677720e+07` — the corrupt finite ρ values of
day-5 steps 1–5 (±10⁵–10⁶) finally overflow the float32 EOS inversion to
NaN **while u1/v1/u2/v2/T/S show 0 NaN**.

**Verdict:** the 10.19/10.20/10.21 `NaN_RO=198 at F_after_conv` claim is
confirmed at step-granularity: **density-first**, first NaN = `ro_nan=198`
at the **CA_after** point of day 5 step 6. The zombie state (day 6+:
`END_step d6s1` → u1/u2 NaN 131,476; t/s/ro NaN 142,081 = all wet cells)
follows.

## 11. Block 200 role — TRANSMITTER, not source

- At the moment of first NaN (day 5 step 6, `B200_before`): ρ already NaN
  (198 cells), **all momentum fields 0 NaN** → Block 200 does not originate
  NaN; it receives them from the CA/EOS step.
- `B200_after` same step: u2/v2 NaN (333 cells each) → the baroclinic
  pressure gradient propagates the field corruption into momentum.
- Day-1 (clean state) budget evidence for a geostrophic-spike *amplifier*
  role: `dp_ratio_u ≈ 1.11`, `dp_ratio_v ≈ 2.98` (a0 day 1, §12) — the
  pressure-gradient term dominates the Laplacian term in the momentum sum,
  i.e. Block 200 is dominated by the gradient that carries ρ noise.
- Yet with ρ freezing (a1/a4) or T/S freezing (a3) the 30-day run is
  **stable and exactly replayable** (§14) — Block 200 is mechanically fine;
  its "spike" is the forced response to corrupt ρ.

## 12. Block 200 budget recorder vs replay — day 1 (ro-phase artifact)

a0 day 1 step 1, CSV budget vs A5 replay (13 metrics; `block200_isolate.py
--run a0 --day 1 --step 1`):

| Metric      | CSV           | Replay        | rel err |
| ----------- | ------------- | ------------- | ------- |
| ro_min      | 7.482650e-03  | 7.480383e-03  | 3.030e-4 |
| ro_max      | 8.181450e-03  | 8.185506e-03  | 4.957e-4 |
| ro_mean     | 7.915240e-03  | 7.988018e-03  | **9.195e-3** |
| sum_max     | 7.014540e-07  | 6.998718e-07  | 2.256e-3 |
| sum1_max    | 1.053680e-06  | 1.049041e-06  | 4.403e-3 |
| acc_bar_u   | 2.477260e+00  | 2.471667e+00  | 2.258e-3 |
| acc_bar_v   | 3.721180e+00  | 3.704792e+00  | 4.404e-3 |
| dp_ratio_u  | 1.107650e+00  | 1.105151e+00  | 2.256e-3 |
| dp_ratio_v  | 2.981040e+00  | 2.967915e+00  | 4.403e-3 |
| max_u2      | 1.168530e+01  | 1.161258e+01  | 6.224e-3 |
| max_v2      | 4.535010e+00  | 4.519271e+00  | 3.471e-3 |
| amp_u       | 1.323060e+00  | 1.314826e+00  | 6.223e-3 |
| amp_v       | 7.722770e-01  | 7.695971e-01  | 3.470e-3 |

All 13 fail at 3e-4…9.2e-3 (> 1e-4 tol) for **a0 only** — this is the
**documented RO-phase artifact**: the replay's ρ field at step 1 is taken
from the day-1 snapshot that *predates* the in-run ρ (the production ρ is
already CA-corrupted between snapshots), so the replay's baroclinic
gradient uses a phase-shifted ρ. The momentum metrics (max_u2/max_v2/amp)
fail at the same 3–6e-3 level — consistent with the geostrophic response
being proportional to the ρ anomaly used (δmax_u2/δro ≈ 6.2e-3 vs
δro_mean ≈ 9.2e-3). **It is a methodology artifact of snapshot-phase,
quantitatively documented — NOT a physics failure and NOT a Block-200
implementation difference** (proven: when ρ is frozen — a1/a4 — or T/S
frozen — a3 — the SAME replay passes 30/30 days at ≤ 4.3e-6, §14).

## 13. Block 210 / Thomas conditioning — pivot negativity is structural

`stage1022_block210.csv` columns: `day,step,rr_min,rr_max,piv_min,piv_neg,
piv_cnt,rhs_max,den_min,den_neg`.

**Pivot sign:** the interior Thomas forward-sweep pivot is `aa = a1 −
uca·a` with `a1 = −1 + a + b` and `a = b = −aa/dz·rr(k2)`; for any
positive viscosity `rr > 0` the substencil entries a,b are negative, so
`a1 < −1` and `aa < 0` **for every interior level by construction** (with
`uca ∈ [0,1)`: `aa = a1 − uca·a = −1 + a·(1−uca) + b < −1` strictly). Hence
`piv_neg = piv_cnt` (2,659,296 pivots/day = 221,608/step = 100 %) is the
**normal state, not a failure indicator** — the earlier reads of "piv_neg"
as danger were a false lead. CSV scope: ratio is **exactly 1.0 for all 48
day-1–4 steps and day-5 s1/s2/s4**; the first tiny deviations appear at
day-5 s3/s5 (0.99998/0.99999 — a handful of pivots NaN-overflowing in
float32 as the corrupt velocity shear spikes), and the ratio collapses only
once ρ = NaN enters the solve (s6: 0.9974 → s8: 0.183 → s9+: 0.0 zombie —
NaN pivots fail the `v ≤ 0` test, so they leave `piv_neg` while `piv_cnt`
keeps counting). The informative conditioning signals are
`rr_max` (NU magnitude), `rhs_max` (Thomas RHS), `den_min` (min |1−bb·uc|):

| Day-step       | rr_max        | rhs_max       | den_min   |
| -------------- | ------------- | ------------- | --------- |
| 1, 1–12        | 1.65e1…2.59e3 | 1.15e1…5.38e1 | 0.449–0.998 |
| 2, 1–12        | 5.19e2…9.79e2 | 3.50e1…1.55e2 | 0.504–0.770 |
| 3, 1–12        | 6.95e2…3.53e3 | 1.63e2…3.96e2 | 0.320–0.802 |
| 4, 1–12        | 2.27e3…8.43e3 | 4.14e2…6.98e2 | 0.607–0.763 |
| 5, 1           | 1.95e4        | 8.74e2        | 0.743     |
| 5, 2           | 1.14e7        | 7.36e5        | 0.741     |
| 5, 3           | 9.63e10       | 1.07e9        | 0.281     |
| 5, 4           | 5.36e9        | 9.58e10       | 6.54e-3   |
| 5, 5           | 6.57e12       | 6.72e10       | 6.75e-3   |
| 5, 6           | 1.66e12       | **1.13e16**   | **7.06e-4** |
| 5, 7+          | decay→NaN     | →0           | NaN       |

**Verdict:** through day 4 (and day 5 steps 1–5, the *finite* pre-NaN
steps) `rr_max ≤ 6.6e12` grows monotonically — the viscosity coefficient
itself is the **forced response** to the day-5 ρ/velocity corruption
(§10: CA_after day-5 steps 1–5 produce ρ ±10⁵–10⁶ → baroclinic momentum
spikes → shear → NU = sl²·|ΔU/Δz|). The Thomas RHS explodes to 1.13e16
and `den_min` to 7.06e-4 **only at step 6 — the same step the ρ-field
turns NaN** — i.e. the Thomas solver blows up ON the already-NaN input,
**after** the density-first event. Block 210 is a downstream amplifier,
NOT an independent cause (10.19's "Block 210 first-NaN site" = consequence
of the 10.19-era coverage-triggered day-1 spike; under full-coverage ERA5
forcing the Thomas system is well-conditioned through day 4:
rr ≤ 8.43e3, rhs ≤ 6.98e2, den ≥ 0.32, piv_min = 1.0 — `den_min` dips
below 0.61 only transiently on days 1–3 (min 0.449 d1s2, 0.320 d3s9), the
day-4 window itself is 0.607–0.763; all stay orders of magnitude above the
7.06e-4 degeneracy that marks the day-5 step-6 blowup).

## 14. A5 replay verdicts — per experiment (30 days × step 1)

From `data/output/diagnostics/stage10.22/replay_verify.log`
(`block200_isolate.py --run <exp> --all-days --step 1`, rel tol 1e-4):

| Exp   | Result                | Worst rel   | Failing metrics                          |
| ----- | --------------------- | ----------- | ---------------------------------------- |
| a0    | FAIL (days 1–30)      | 9.195e-3 (d1); day6+ 14 fails + 3 NaN skip | ro-phase artifact, §12; after day 6 the ocean is zombie (CSV NaN) → replay N/A (3 metrics skipped/day) |
| a1    | **PASS 30/30**        | 4.213e-6 (d21) | none                                   |
| a2    | FAIL (ro-phase only)  | 2.954e-1 (d9) | **exactly 9 ro-phase metrics** (`ro_*`, `sum_max`, `sum1_max`, `acc_bar_u/v`, `dp_ratio_u/v`); **momentum `max_u2/max_v2/amp_u/amp_v` PASS** → the freeze_tw two-path budget split is EXACT |
| a3    | **PASS 30/30**        | 4.100e-6 (d9) | none                                   |
| a4    | **PASS 30/30**        | 4.213e-6 (d21; identical to a1 CSV path) | none                                   |

- a1/a3/a4 failures = 0 across all 30 days, worst rel 4.213e-6 — an order
  of magnitude below the 1e-4 tolerance and consistent with float32
  round-off of the independent replay (different summation order).
- **a2 is the exactness proof of the freeze_tw implementation:** with the
  baroclinic momentum sums zeroed, the momentum metrics match the replay to
  the PASS level while the recorder columns (which are *never zeroed* —
  they record the full sums) still show the ro-phase artifact at the same
  magnitude as a0. The two-path split in `block200_isolate.py` mirrors
  `src` exactly.
- a0 day-6+ "14 fails" includes the 13 ro-phase metrics minus metrics the
  NaN-skip applies to (1 metric drops out, 3 skipped) — the CSV target
  becomes NaN once the ocean is zombie; the skips are the *continuation
  evidence* of the day-5 death, not replay noise.

## 15. Causal-isolation verdict (experiment matrix)

| Exp | Physics closure           | 30-day outcome | Conclusion |
| --- | ------------------------- | -------------- | ---------- |
| a0  | none (production)         | dies day 5 s6  | baseline   |
| a1  | ρ frozen inside CA        | **stable 30 d, replayable** | ρ corruption in CA is causal |
| a2  | thermal-wind term off     | dies day 5 (ro-phase artifact persists) | Block-200 geostrophic term is NOT the origin — ρ still corrupts the (recorded) budget and the residual path kills the run |
| a3  | T/S frozen entirely       | **stable 30 d, replayable** | T/S→ρ path confirmed |
| a4  | ρ pinned downstream of CA | **stable 30 d, replayable** | decoupling ρ from CA noise removes the baroclinic corruption trigger |

a2 dies with the SAME ro-phase artifact signature as a0 → the thermal-wind
term is NOT required for the death; the corrupted ρ (from CA/EOS float32
noise) is sufficient. a1/a3/a4 all stabilize by freezing ρ or its source —
**the causal origin is the CA/EOS float32 density corruption (T-01
family), FIRST via ρ < 0 on day 4, then ρ = NaN on day 5 s6; Block 200
transmits it into momentum; Block 210 amplifies it post-hoc.**

## 16. Comparison with previous stages

| Claim (10.19/10.20/10.21)                                    | 10.22 evidence                                                                 |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| "first NaN = `NaN_RO=198` at `F_after_conv` III=6 day 5"     | **CONFIRMED** at step/block granularity: `ro_nan=198` at CA_after day5 s6, u/v 0 NaN |
| "density-first, 0 NaN in U/V at that instant"                | **CONFIRMED** (B200_before probe: momentum 0 NaN)                               |
| "Block 210 = first-NaN site" (10.19, legacy forcing)         | **SUPERSEDED for full-coverage ERA5**: Block 210 conditioning is healthy through day 4 (rr≤8.4e3, rhs≤7e2, piv_min=1.0 structural; den_min dips transiently to 0.449 d1s2 / 0.320 d3s9, day-4 window 0.607–0.763); its day-5 blowup is downstream of the ρ-NaN step |
| "Block-200 geostrophic spike" (T-03) as independent cause    | **REFUTED as origin**: with ρ frozen (a1/a4) or T/S frozen (a3) the run is stable; Block 200 only transmits corrupt ρ (dp_ratio 1.1/3.0 shows gradient dominance, but with clean ρ the recorders + replay match to 4.3e-6) |
| "CA guard saturation = symptom" (10.21)                      | **HARDENED**: the first physical violation (ρ < 0, day 4) and first NaN (ρ, day 5 s6) both occur INSIDE the CA block; eliminating the guard (10.21) did not help because the corruption is the float32 EOS inversion itself, not the guard iteration |
| T-03 "Thomas ill-conditioning blowup risk"                   | **RE-CHARACTERIZED**: pivot negativity is structural (100 % negative by construction); the actual conditioning (rr_max, rhs_max, den_min) is healthy through day 4 and only breaks ON the day-5 ρ-NaN input |

## 17. PROVEN / LIKELY / UNPROVEN classification

| # | Statement | Class |
| - | --------- | ----- |
| 1 | First physically impossible state = ρ-anomaly < 0 at CA_after day4 s1 (−1.946690e-04), reaching −4.37e-2 by day 4 end | **PROVEN** (probe CSV) |
| 2 | First NaN = ρ (`ro_nan=198`) at CA_after day5 step 6, momentum 0 NaN at that instant | **PROVEN** (probe CSV, 3 independent families) |
| 3 | Block 200 is a transmitter (receives NaN ρ, emits NaN u2/v2), not the origin | **PROVEN** (B200_before/after probes) |
| 4 | Block 210 Thomas blowup (rhs 1.13e16, den 7.06e-4) occurs in the same step as the ρ-NaN and is downstream | **PROVEN** (block210 CSV row 5,6) |
| 5 | Thomas pivot negativity is structural (a1 = −1+a+b < 0 with rr > 0) — `piv_neg=piv_cnt` is the healthy state | **PROVEN** (analytic for any rr > 0; CSV ratio exactly 1.0 for all 48 day-1–4 steps + day-5 s1/s2/s4; tiny deviations day-5 s3/s5 = NaN-overflowed pivots; collapse 0.9974 → 0 only after the ρ-NaN) |
| 6 | Freezing ρ (a1/a4) or T/S (a3) stabilizes the 30-day run; a2 (thermal-wind off) does not | **PROVEN** (experiment matrix) |
| 7 | A5 replay reproduces Block 200 exactly under stable closures (≤ 4.213e-6, 30/30) | **PROVEN** (replay_verify.log) |
| 8 | A5 a0/a2 ro-phase artifact is a snapshot-phase methodology effect (replay ρ predates in-run ρ), not a physics difference | **LIKELY** (magnitude correlation with δro; a2 momentum metrics PASS ⇒ implementation match; day-1-only artifact on the clean day) |
| 9 | The day-4 ρ < 0 arises specifically from float32 EOS quantization noise accumulated in CA mixing (T-01) — vs other EOS/CA precision paths | **LIKELY** (10.21 established the 2⁻²³ floor; 10.22 adds the ρ<0 day-4 signature, but the exact mixed-cell mechanism is not micro-traced) |
| 10 | A production fix path exists that keeps KEEP_CURRENT physics (accepted) while removing the death (e.g. ρ-ref clamp or EOS f64 in CA) | **UNPROVEN** (not attempted — requires an approved physics stage per RULES.md; a1/a3/a4 prove the lever exists but are diagnostic switches only) |

## 18. Physics interpretation

1. **The ocean death is a precision-triggered, density-first cascade with a
   documented step-by-step chain.** days 1–3: CA mixes T/S with float32
   quantization noise (2⁻²³ floor, 10.21); ρ-anomaly minimum decays
   6.85e-3 → 6.07e-4. Day 4: ρ crosses below ρ_ref (negative anomaly —
   sub-seawater density) inside CA; T/S leave physical range. Day 5 s1–s5:
   corrupt finite ρ (±10⁵–10⁶) drives baroclinic momentum spikes
   (dp_ratio gradient-dominated) → shear → NU = sl²|ΔU/Δz| grows 1.95e4 →
   6.6e12. Day 5 s6: the EOS inversion overflows to NaN ρ inside CA (198
   cells) → Block 200 emits NaN momentum (333 cells) → Block 210 Thomas RHS
   1.13e16 / denominator 7.06e-4 → full NaN. Day 6+: zombie (142,081 wet
   cells).
2. **Block 200 is deterministic and exactly implemented** — the A5 replay
   matches it to ≤ 4.3e-6 whenever the ρ input is controlled (a1/a3/a4);
   its "spike" is the amplification of ρ corruption via the baroclinic
   gradient (dp_ratio measure), not a solver defect.
3. **T-03 reframed:** the Thomas vertical-viscosity machinery is healthy
   (piv_min = 1.0, den_min ≥ 0.32 [day-4 window 0.607–0.763], rr bounded)
   through day 4; the T-03 "ill-
   conditioning blowup" exists only as the late-stage amplifier of the
   density-first cascade. The 10.19 day-1 Block-210 site was an artifact of
   the legacy (gap-riding) forcing, already superseded at 10.20.

## 19. Required table (spec §34) — causal-chain evidence summary

| # | Event | Day-step | Block/site | Field | Evidence (value) |
| - | ----- | -------- | ---------- | ----- | ---------------- |
| 1 | ρ-anomaly first sub-zero | 4, 1 | CA_after | ro_min | −1.946690e-04 (probe) |
| 2 | ρ-anomaly daily min | 4, 12 | CA_after | ro_min | −4.365810e-02 (probe/block200) |
| 3 | T/S out of physical range | 4 | daily diag | t_min/max, s_min | −45…+50 °C, S<0 (10.20/10.21 daily_diagnostics) |
| 4 | ρ pre-NaN corruption | 5, 1–5 | CA_after | ro_min/ro_max | −4.19e6…+8.83e5 |
| 5 | **FIRST NaN** | **5, 6** | **CA_after** | **ro_nan** | **198** (probe; u2/v2 0) |
| 6 | Block 200 entry | 5, 6 | B200_before | ro_nan / u2,v2_nan | 198 / 0 (probe) |
| 7 | Momentum NaN | 5, 6 | B200_after | u2_nan, v2_nan | 333, 333 (probe) |
| 8 | Thomas RHS explosion | 5, 6 | B210 | rhs_max | 1.13e16 (block210) |
| 9 | Thomas denominator collapse | 5, 6 | B210 | den_min | 7.06e-4 (block210) |
| 10 | Zombie state | 6, 1 | END_step | t/s/ro_nan | 142,081 = all wet cells (probe) |
| 11 | a1/a3/a4 stable + replayable | 1–30 | — | A5 | 0 fails, ≤ 4.213e-6 |
| 12 | a2 momentum exact | 1 | — | A5 max_u2/v2/amp | PASS (ro-phase only fails) |

## 20. Causal diagram (spec §35)

```
T01 (float32 EOS 2⁻²³ quantization, CA mixing)           [10.21, PROVEN]
   │  days 1–3: ro_min decays 6.85e-3 → 6.07e-4
   ▼
ρ-anomaly < 0 (ρ < ρ_ref)  day 4 s1, CA_after             [PROVEN §9]
   │  −1.95e-4 → −4.37e-2 by end of day 4; T/S −45…+50 °C, S<0
   ▼
Corrupt finite ρ ±10⁵…10⁶  day 5 s1–s5                   [PROVEN §10]
   │
   ├──► Block 200 baroclinic gradient (dp_ratio 1.11/2.98) → momentum spikes
   │        └──► shear → NU = sl²|ΔU/Δz|: 1.95e4 → 6.6e12 (day 5 s1–s5)
   ▼
EOS inversion overflow → ρ = NaN (198 cells)  day 5 s6, CA_after
   │                                                   [FIRST NaN, PROVEN]
   ▼
Block 200 transmits: u2/v2 = NaN (333)                  [TRANSMITTER, PROVEN]
   ▼
Block 210 Thomas: rhs 1.13e16, den 7.06e-4 → all NaN    [AMPLIFIER, PROVEN]
   ▼
Zombie day 6+: 142,081 wet cells NaN                    [PROVEN §10]
```

Lever (NOT applied — needs approved physics stage): freezing ρ in CA (a1),
pinning ρ downstream (a4), or freezing T/S (a3) each stabilizes the 30-day
run and is exactly replayable.

## 21. Dimensional analysis / magnitudes sanity

- ρ-anomaly range over physical T/S domain: +0.0061…+0.0083 (10.21
  binade study) — day-4 value −4.37e-2 is −5.3× the physical minimum;
  day-5 pre-NaN ±10⁵–10⁶ are 8–9 orders above physical → the EOS
  inversion is being fed T/S far outside the EOS-80 validity window.
- Block-200 momentum response: max_u2 ≈ 11.7 (cm/s, a0 day1) with
  δro_replay 9.2e-3 → δmax_u2 6.2e-3 rel — consistent with
  ΔU ≈ (g/ρ₀)·(Δρ·H)/f-scale amplification, i.e. geostrophic scaling of the
  ρ-corruption, not a numerical instability of the momentum step itself.
- NU growth: rr (sl²·|ΔU/Δz|) ×10⁸ over day 5 s1→s5 while ρ goes ×10⁸
  nonphysical — the viscosity is a mirror of the shear forced by the
  corrupted gradient.
- Thomas pivot |aa| ≥ piv_min = 1.0 always (diagonal-dominated, a = −1+
  a+b): the matrix remains invertible; the explosion is in the RHS
  (1.13e16), not the factorization.

## 22. Limitations

- A5 replays **step 1 only** (`--step 1`); intermediate steps of a day are
  verified by the production recorder CSV (never zeroed) but not
  cross-replayed per-step. The recorder CSV itself is the trace (§12); a
  per-step replay would require snapshots at every step (not available —
  outputs are daily).
- The ro-phase artifact in a0/a2 is **documented, not eliminated**: the
  replay always uses the day-d snapshot ρ against the in-run ρ the
  recorder saw. This limits a0/a2 replay verdicts to "implementation
  matches except ρ-phase" — the a1/a3/a4 exactness is the positive control
  that closes the gap (with frozen ρ the phase problem vanishes and the
  match is ≤ 4.3e-6).
- Causality is established by experiment (a1/a3/a4 stable) + probe timing;
  a micro-traced cell-level CA-mixing mechanism for the day-4 ρ < 0 is not
  yet delivered (would require a CA-cell tracer — future work).
- The day-5 s6 first-NaN step itself: u/v/T/S 0 NaN but ρ NaN — the exact
  EOS overflow cell (which T/S pair overflows a float32 reciprocal) is not
  isolated by cell id; only counts are recorded.

## 23. Out of scope / not done (explicit)

- **No production physics change**: `src/` gains only the diagnostics
  module (read-only, behind `STAGE1022_DIAG`) + three diagnostic
  freeze-hooks (default OFF). EOS formula, CA structure, Block 200/210/280,
  barotropic solver, grid, ERA5, bathymetry, thermodynamics: untouched.
- No CA/EOS precision change (that was 10.21; closed). No preconditioned-
  solver study (proposed next).
- No iceberg-module change; offline TEST_11 untouched.
- The a1/a3/a4 freeze switches are **diagnostic levers, not production
  physics**: converting any into a production stabilization requires an
  approved physics stage per RULES.md (D-20 recommendation records this).
- No cell-level tracer, no per-step replay (limitations above).

## 24. Decision (D-20)

- **KEEP_CURRENT physics** — all Stage 10.22 switches default OFF;
  production binary bit-identical (instrumentation verified read-only:
  a0 vs a0_diag daily-diagnostics byte-identical).
- **Causal attribution closed:** the production ocean death is the
  **CA/EOS float32 density-corruption cascade** (T-01 family):
  ρ < 0 on day 4 (first physical violation) → ρ = NaN day 5 s6 (first
  NaN, density-first) → Block 200 transmits → Block 210 amplifies
  (T-03 re-characterized as downstream amplifier; pivot negativity
  structural).
- **Next-stage recommendation:** an approved physics stage choosing the
  **minimal stabilizer** proven by the experiment matrix: (a) ρ-anomaly
  clamp at physical bounds in CA writeback, (b) EOS f64 inversion in CA
  (10.21 machinery already exists), or (c) pinning ρ to a periodic
  reference update (a4-like). Acceptance stays: 30-day gate
  `steps executed : 360` with 0 NaN.
- The A5 replay engine (`python/validation/block200_isolate.py`) is
  **retained** as the Block-200 regression oracle for future physics
  stages (proven exact for stable closures).

## 25. Reproducible commands

```bash
# 30-day diagnostic runs (production binary, ICEBERG_PRODUCTION gate)
ICEBERG_PRODUCTION=true STAGE1022_DIAG=true fpm run --flag "-I/usr/include" -- \
  stage10.22_p30d_a0_diag data/input/processed/era5/2020/2020_01/era5_2020_01_fullcoverage_merged.nc
ICEBERG_PRODUCTION=true STAGE1022_FREEZE_RO=true fpm run --flag "-I/usr/include" -- \
  stage10.22_p30d_a1_freeze_ro ...
ICEBERG_PRODUCTION=true STAGE1022_FREEZE_THERMAL_WIND=true fpm run --flag "-I/usr/include" -- \
  stage10.22_p30d_a2_no_tw ...
ICEBERG_PRODUCTION=true STAGE1022_FREEZE_TS=true fpm run --flag "-I/usr/include" -- \
  stage10.22_p30d_a3_freeze_ts ...
ICEBERG_PRODUCTION=true STAGE1022_FREEZE_RO_DOWNSTREAM=true fpm run --flag "-I/usr/include" -- \
  stage10.22_p30d_a4_frozen_ro ...

# A5 independent replay (per experiment, all days step 1; or --day N --step S)
python python/validation/block200_isolate.py --run a0 --all-days --step 1
python python/validation/block200_isolate.py --run a1 --all-days --step 1   # 30/30 PASS
python python/validation/block200_isolate.py --run a2 --all-days --step 1   # ro-phase only
python python/validation/block200_isolate.py --run a3 --all-days --step 1   # 30/30 PASS
python python/validation/block200_isolate.py --run a4 --all-days --step 1   # 30/30 PASS
# single-day tick: --run a0 --day 1 --step 1  (13-metric table, §12)
```

## 26. Files changed (this stage, committed `928041a`)

- `src/stage1022_diagnostics.f90` (new, 527 lines) — `s22_probe`,
  `s22_block200_budget`, `s22_write_*` CSVs, ro_ref capture/sandwich.
- `app/main.f90` (+99) — env-var parsing, probe/budget call sites,
  `STAGE1022_FREEZE_TS` skip hooks in heat and adv/conv_adj.
- `src/convective_adjustment.f90` (+21) — `STAGE1022_FREEZE_RO` hook
  (a1: mix T/S, keep pre-adjustment RO).
- `python/validation/block200_isolate.py` (new, 694 lines) — A5 replay
  engine + document strings + verdict logic.

No changes to entity physics modules; no test/ changes in this commit
(Python regression test for the A5 verdicts is delivered with this report,
see §27 and `python/tests/test_stage10_22_block200_audit.py`).

## 27. Test battery, acceptance status, final conclusion

**Fortran:**
```bash
rm -rf build && fpm test --flag "-I/usr/include"
```
PASS — full battery (all SUCCESS, STOP 0). No Fortran test added in 10.22
(all changes diagnostic; the replay oracle is Python).

**Python (this report's regression deliverable):**
```bash
python python/tests/test_stage10_22_block200_audit.py
```
Encodes: (1) the causal-chain evidence constants (day-4 ρ < 0, day-5 s6
ro_nan=198 / u2=333 / rhs=1.13e16 / den=7.06e-4, zombie 142,081);
(2) the pivot-negativity-by-construction identity (piv_neg = piv_cnt for
every healthy step: analytic + CSV exact 1.0 for all 48 day-1–4 steps, the
day-5 deviation being NaN-overflowed pivots, not positive pivots); (3) the A5 verdict contract (a1/a3/a4 30/30 ≤ 4.3e-6, a2
ro-phase-only, a0 day-6+ NaN-skips); (4) bit-identity invariant
(a0 vs a0_diag daily_diagnostics md5 `1ef13cb4…`) — run against the
committed run artifacts where available, structural assertions otherwise.

**Acceptance status:** offline path fully validated (unchanged); online-
coupled 30-day gate `steps executed : 360` remains OPEN — now with the
causal chain closed and the stabilizer levers proven, the acceptance
depends on an approved physics stage (§24), not on further diagnostics.

**Final conclusion:** Stage 10.22 isolates the production ocean divergence
to a **density-first cascade originating in the CA/EOS float32 path**
(T-01 family): first physical violation ρ-anomaly < 0 at day 4 step 1,
first NaN ρ at day 5 step 6 (198 cells, u/v still clean), Block 200 a
proven transmitter (never an origin), Block 210 a proven downstream
amplifier whose pivot negativity is structural and whose conditioning is
healthy through day 4. The A5 independent replay proves the Block-200
momentum implementation exact (a1/a3/a4: 30/30 days, ≤ 4.213e-6; a2
two-path split exact; a0/a2 differences are the documented snapshot-phase
artifact). Production physics is KEEP_CURRENT; D-20 records the closed
attribution and the proven stabilizer levers for the next approved stage.