# Stage 11.3C.2 — Ocean Time-Integration Architecture Audit

Frozen 2026-09-30. PURE AUDIT — no code, physics, or cadence changes. Line
numbers: `app/main.f90` at 11.3C.1 (`4e01eff`).

## 1. Temporal architecture (verified by code reading)

`do iii = 1, mm2` opens at line 624 and closes at line 909 (sole 16-space
`end do` in range). Contents split:

**INSIDE iii (mm2×/day):** state snapshot `t1=t2/s1=s2/u1=u2/v1=v2` (~613) →
`heat(dt)` (628) → `redis()` (632) → ice dynamics `jjj`-loop (656–749) →
`adv2d()` AN1/WICE1 per category (758/764) → `redis()` (769) → W continuity
(790–908). Related D24–D31 `iii` references to heat/dynamics events are
genuine substep labels.

**ONCE PER DAY, stale `iii = mm2+1`:** `s112` vertical-CFL + `s112_cfl_dist`
(912–917) → `advs/adct(dt,c2)` (940/943) → `conv_adj(kkk,iii)` (961) →
Block 200 (986–1072, `dt`) → Block 210 (~1105–1242, `dt`) → `shal()` (1294,
`dt1` inside) → Block 280 (~1316) → END scans/timeseries (1354–1362) →
B3.3 min/max print (1383) → `iceberg_step` (1397, despite "каждый часовой шаг"
comment) → daily `write_nc` (1418).

Timeline per model day: `mm2` × [heat→redis→ice-dyn→adv2d→redis→W] then 1×
[scans→advs/advt→CA→B200→B210→shal→B280→scans→iceberg→output]. W is
recomputed identically each substep (wasteful, harmless — ocean state frozen
across `iii`). `iceberg_step` runs once/day (comment claims hourly — stale).
`ib_model_time_sec` uses stale `iii` (off-by-one-hour when enabled — latent,
noted, untouched).

## 2. Operator frequency table (per model day)

| Operator | Line | In iii? | Calls/day | dt used | State/forcing |
|---|---|---|---|---|---|
| wind interp `era5_wind` | 576 | NO | 1 | daily slice | tx1/ty1… |
| `heat` | 628 | YES (mm2×) | mm2 | DT | t1/s1, ERA5 |
| `redis` | 632/769 | YES (2×mm2) | 2·mm2 | — | an1/wice1 |
| ice dynamics | 656–749 | YES (mm2×mm3 micro) | mm2·mm3 | DT1 | u/v, u2/v2 |
| `adv2d` | 758/764 | YES (mm2×) | mm2 | DT | an1/wice1 |
| W continuity | 790–908 | YES (mm2×, recomputed) | mm2 | — (diagnostic) | u1/v1 |
| `advs`/`advt` | 940/943 | NO | 1 | DT | t2/s2 → t1/s1 |
| `conv_adj` | 961 | NO | 1 | — | t2/s2/ro |
| Block 200 | 986–1072 | NO | 1 | DT | u1→u2 |
| Block 210 | 1105–1242 | NO | 1 | DT (+DT1 via txic) | u2 (+Thomas) |
| `shal` | 1294 | NO | 1 | DT1 (internal) | eta, up2/vp2 |
| Block 280 | ~1316 | NO | 1 | — | u2/v2 |
| `iceberg_step` | 1397 | NO | 1 | DT | ib_state |

Legacy cadence: ice integrates mm2·DT = 12 h/day; ocean integrates 1×DT
(1 h/day at DT=3600). 11.3C.1 scaling: ice 24 h/day; ocean still 1×DT/day.

## 3. Historical provenance

Primary sources (`Nesterov_last.txt`, `Coupl1.f90`, `Dmitriev.txt`) are NOT in
the repo — only citations in `docs/wiki/stages/stage03/Stage3.3_mapping.md`.
Recovered facts: Coupl1 daily order ≡ current order (W → [GO TO 888 skips
dead adv/diff] → B200 → B210 → `shal()` → B280; advS/advT/conv_adj at 779–846
before 888); "U1=U2 at each baroclinic step" (Coupl1:365-366); dt=3600 named
baroclinic STEP; `heat` must run "with the same step as the ocean" (current
comment ~625). Git archaeology: `do iii` predates staged history (initial
squashed import) — the split cannot be dated. Coupl1 loop bounds (the
decisive evidence: did B200 run inside an hourly loop?) are unrecoverable
from available materials.

## 4. Classification verdict: Option C (HYBRID/UNCLEAR), B-leaning

- FOR A (intentional): Coupl1 daily-cycle order matches current code exactly;
  Stage 3.3 deliberately placed blocks there; no mapping note mentions ocean
  subcycling; original authors tolerated reduced cadence (GO-TO-888 skips,
  "12 hours" header admission).
- FOR B (error): dt-as-STEP semantics; same-step heat/ocean comment;
  u1-snapshot currently refreshes per-iii (12–96×/day), implying the team
  model treats `iii` as "the step"; team-wide per-iii mental model (incl.
  D24–D32) contradicts the code — nobody designed ocean-outside deliberately
  on record; daily budgets incoherent (12 h ice + 1 h ocean legacy).
- Decisive test unavailable: needs Coupl1 loop bounds or author consultation.
  Minimal B-fix (if ever approved): move the ocean pass inside `iii`
  (24×3600 s = coherent day) — NOT now (scheme-adjacent, RULES procedure).

## 5. Matrix reinterpretation (11.3C/11.3C.1 A/B/C)

A/B/C did NOT test ocean temporal convergence (ocean = 1×DT/day in all).
Measured EUU drift (+3.8/+2.6% as DT falls) = combined response of (a) finer
ocean dt once daily and (b) 2–4× more ice/thermo substeps (48/96 vs 24).
D/E ≡ A confirms barotropic/microstep convergence; the drift source (ocean
dt vs ice cadence) is UNSEPARATED — separation requires an `mm2`-at-fixed-DT
experiment (proposed `STAGE113_MM2` override, not implemented). A correct
ocean-convergence test needs an ocean substep loop (future stage).

## 6. Recommendations

- Keep 11.3C.1 envelope (DT∈[900,3600] stable) as CADENCE-sensitivity, not
  convergence, evidence.
- 11.4 (EOS-80) unaffected: run at reference cadence A.
- Future: (i) recover Coupl1 loop bounds or consult authors for A/B closure;
  (ii) `STAGE113_MM2` override to separate ice-vs-ocean DT response;
  (iii) fix stale-`iii` labels in scans/iceberg-time if the ocean pass ever
  moves (not now).
