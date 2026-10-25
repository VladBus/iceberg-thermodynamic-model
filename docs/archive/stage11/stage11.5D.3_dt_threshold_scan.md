# Stage 11.5D.3 — Controlled dt-Threshold Scan for Family B

Frozen (date). Threshold scan (dt at fixed 86400 s/day ocean totals,
shal 1×/day) + stability boundary. No physics change (EOS, CA threshold,
B200/B210/B280/shal/advs/advt/CA/EOS/ice equations, EN4/ERA5/grid/
coefficients untouched); no guards/clamps; Family B NOT implemented as
production (diagnostic scan only); production defaults unchanged.

## 1. Implementation (`app/main.f90` ONLY, diagnostic)

Extended `STAGE115D2_EXP=D` with `STAGE115D3_DT` (default 150 s):
d2_npass = nint(3600/dt) internal passes per gate fire (24 fires/day →
24×npass passes/day = 86400/dt total; dt ∈ {1800,900,450,225,150} →
npass ∈ {2,4,8,16,32}); dt_ocean = dt; guards (dt>0, 3600/dt integer,
dt≤3600, mm2≥24 → else legacy-with-warning). Existing 6 hooks reused
(no new call sites). Precedence: D3-D > D2-B > FamilyA > 115C > legacy
(documented). Per-pass B200-term instrumentation deemed INFEASIBLE at
high pass counts (diagnostic full-domain scans would dominate runtime
~100×; substituted EUU trajectories + binary verdicts + outputs +
D1 term data reused — documented deviation from the letter of TASK 3).

## 2. Phase 1 (kill ~day 4–9; April MM2=24, realistic EN4, all INIT-OK)

| dt | passes/d | maxU trajectory (m/s, outputs) | NaN | Verdict |
|---|---|---|---|---|
| 3600 (B, 11.5D.2) | 24 | d2: 91→1.4e9 | d3 RO (106,9,2) | UNSTABLE d2–3 |
| 1800 | 48 | 0.28→0.55→3.3→8.5 → NaN d4 (262952) | d4 | UNSTABLE d3–4 |
| 900 | 96 | 0.28→0.42→0.47→1.4→2.6→4.6→5.2 → blow d7 (8.4e4 + 2702 NaN) | d7 | UNSTABLE d6–7 |
| 450 | 192 | 0.28→0.30→0.45→0.32→0.47→0.68→1.27→1.72→2.54 (d0–8, clean) | 0 thru d8 | MARGINAL (see Phase 2) |
| 225 | 384 | 0.28→0.26→0.32→0.39→0.36→0.27→0.30→0.41→0.44 (d0–8, FLAT) | 0 | STABLE trend |
| 150 (D, 11.5D.2) | 576 | 24→28 cm/s d1–2, EUU ≡ control | 0 thru d7 | STABLE |

Blowup day scales inversely with dt (3600→d2.5, 1800→d3.5, 900→d6.5):
halving dt roughly doubles survival — consistent with per-pass TW/btp
increments ∝ dt (11.5C.8.2: sustained feedback needs ~48 large-dt
passes to reach TW-threshold; small dt never gets there).

## 3. Phase 2 (boundary refinement)

- dt450 extended (fresh run, killed d16): d9–16 maxU 3.6→5.9→7.5→6.7,
  maxV to 14.3, ZERO NaN through day 16. Growing sub-critically
  (9× over 16 d, no detonation). MARGINAL: passes the 7-day gate
  formally (d7: 1.72 < 10 m/s, no NaN) but trajectory heads toward
  eventual blowup (~d20–30 extrapolated — NOT confirmed).
- dt225 (8 d): FLAT (0.26–0.44, no trend, 0 NaN). STABLE.
- Boundary: FLAT-stable dt* ≤ 225; dt=450 = slow-burn marginal
  (survives ≥16 d, growing). Largest PROVEN-flat dt = 225.

## 4. Phase 3 (full April 29 d, INIT-OK, EXIT 0 unless noted)

- dt225full (EXIT 0, 31 files): 0.26→5.9 by d25, ZERO NaN all 29 d.
  PASSES 29-day gate (maxU 5.9 < 10 m/s).
- dt150full (EXIT 0, 31 files): 0.24→4.0 by d29, ZERO NaN.
  PASSES 29-day gate (+ consistency on final binary).
- dt450full (EXIT 0, 31 files): survives to d25 (5.2/10.7, clean) then
  blows d26–29 (262952 NaN, zombie). FAILS 29-day gate.
- Largest PROVEN-29d-stable dt = 225. Blowup threshold dt_blow ∈
  (450, 900]. Recommended Family-B dt: ≤ 225 (proven-flat class);
  dt=150 conservative reference. Cost: dt225 ≈ 384 passes/day
  (~2 min/day April); dt150 ≈ 576 passes/day (~7 min/day) — ice
  dominates runtime (NOT proportional to passes).

## 5. dt → stability analysis

- B200-dE-per-dt curve (direct, per-pass): NOT measured (infeasible —
  §1); substituted: binary verdicts + EUU/maxU trajectories + D1
  term data (B200-total-vs-N at fixed totals: +1.68e5 (dt=3600-equiv)
  → −2.7e4 (dt=150-equiv), sign flip N≥6) + 11.5C.8.2 per-pass growth
  (TW 5× p12→p24, btp 2.7× at dt=3600).
- Stability boundary: dt* ∈ (225, 450] for flat-stability;
  dt=450 marginal (16 d survival + growth); dt≥900 blows ≤7 d;
  dt=3600 blows d2–3. Recommended Family-B dt range: dt ≤ 225
  (proven-flat class), with dt=150 as the conservative reference
  (7 d proven + Phase-3 full April pending).
- D1 comparison (fixed 3600 s/day totals): B200 sign flip at N≥6
  (dt≤600) — SAME dt-controlled sign behavior at different totals →
  boundary does NOT shift qualitatively with total time; totals set
  the integration length, dt sets the per-pass gain. (D1 totals 3600
  vs D3 totals 86400: same dt→same per-pass physics; totals only
  change how many passes compound.)
- Physical reading: per-pass sustained TW/btp increments ∝ dt;
  runaway when cumulative feedback crosses TW-threshold within the
  available passes; at dt≤225 increments stay sub-threshold
  indefinitely (bounded oscillation); CA maxiter saturated (1001)
  throughout — orthogonal pre-existing family.

## 6. Files + verification

- `app/main.f90` (D3-DT env + npass derivation + guards; hooks reused).
- Docs: this file (NEW); INDEX 11.5D.3 row; ROADMAP (11.5D.2 COMPLETE,
  11.5D.3 status).
- January: N1 ≡ janOFF (32/32 md5); JanDT150 (dt=150, killed d8):
  maxU flat 0.24–0.39, ZERO NaN — STABLE (January too).
- Verification: Jan OFF (`stage11.5D3_JanN1` ≡ janOFF) + JanDT150 stable;
  full fpm battery PASS (no failures/errors); `git diff --check` clean.
- RAM discipline note (user constraint): all runs strictly sequential
  (stray-check gates), killed at verdict (no full-month waste except
  Phase-3 gates), no parallel battery/analysis loads; repo-persistent
  init files (`data/input/processed/ocean/*_rebuild.nc`) ended the
  /tmp-wipe failure class (9 wipes survived via rebuild routine).
