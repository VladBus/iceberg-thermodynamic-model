# Stage 11.5C.8 — Full-Field Energy Injection Map

Frozen (date). PURELY DIAGNOSTIC + FULL-FIELD MAPPING. No physics,
EOS, CA, advection, ice-dynamics, or numerical-scheme change; no
guards/clamps; B200/B210/B280/advs/advt/CA/EOS/txic/shal untouched;
production defaults unchanged. Implementation: NEW module
`src/stage115c8_full.f90` (env `STAGE115C8_FULLFIELD`, OFF → early
return) + 8 call sites in `app/main.f90` (use/init/6×op-snap-compute;
additive calls only). One correctness fix during stage: exact dE =
Δ(U²+V²) instead of first-order 2U·dU (the latter misses the +dU²
spin-up fill and biases nets negative; found via C5 cross-check).

## 1. Method (aggregates only, no huge CSV)

Per operator boundary (B200/B210/B280 before→after): snapshot U2/V2,
then per wet cell exact dE; accumulate sum_pos/sum_neg/net, counts,
max±with location, per-level Ek[18] (ks=18, not 17 — documented),
ninv; one row per op (34 cols) + flush. Day-1 spatial map: D_E(i,j,k)
accumulated, top-1000 positive dump at day-2 entry (min-heap;
`spatial_top1000_d1.csv`) — INSTEAD of NetCDF (documented deviation:
diagnostic module takes no NetCDF dependency). NaN-safe (skipped+counted).

## 2. Execution (N24 April, realistic EN4 INIT-OK, killed ~d11; days 1–10 usable)

Run `stage11.5C8_AprN24` (TRACE + FULLFIELD). Full 29-day April
completed by surviving orphan (open FDs) — full exact-dE dataset.
Event d3s1 (112,17,9) — 11th deterministic reproduction.

## 3. Operator balance day-1 (24 passes; BUDGET CLOSED)

B200: pos +3.04e7 / neg −1.04e7 / net +2.007e7.
B210: pos +1.45e7 / neg −1.55e7 / net −1.03e6 (near-balanced, slight damping).
B280: pos +4.48e7 / neg −3.18e7 / net +1.306e7.
Total +3.21e7 = C5 Δ (pass-1 +2.78e6 + passes 2–24 +2.93e7) EXACTLY
(pass-1 accounted — earlier 9% "gap" closed). advs/advt/CA/shal touch
no U2/V2 (structural zero, re-confirmed). Pass trajectory: p1 +2.78e6 →
p12 −3.2e4 (quasi-steady) → p23 +5.4e6 → p24 +7.2e7?? no — +7.18e6
(feedback; 250× midday).

## 4. Depth decomposition (day-1 net per level, all ops)

k=1 +3.82e6, k=2 +3.53e6 … monotonic decrease … k=9 +2.16e6,
k=10 +1.57e6 … k=12 +0.48e6, k=13 +0.28e6, k=14 +0.37e6, k=15 +0.46e6,
k=16 +0.54e6, k=17 +0.48e6, k=18 +0.02e6. Surface-weighted total
(k1–9 ≈ 75%), slight deep bump k13–17.
PER OPERATOR (the separation): B200 peaks DEEP (k15/k14/k16/k13:
4.9/4.8/4.0/3.5e6); B280 peaks SHALLOW (k1–k4: 4.0/3.7/3.6/3.5e6);
B210 ≈ 0 at every level (top-k ~2e4 = noise). → B200 = deep injector
(thermal-wind integral grows with depth), B280 = surface injector
(barotropic imprint strongest at surface), B210 = neutral damper.

## 5. Spatial map (top-1000 day-1 D_E)

1000 cells (0.7% of wet) hold +2.055e7 = 64% of day-1 net —
heavy-tailed, NOT uniform. Depth histogram: k1–9 ~830, k10–17 ~170
(surface-weighted count, deep tail present). Top sites scattered:
(108,14,3), (3,18,7), (129,22,5), (9,24,2), (54,5,9), (9,23,4) — many
regions, no single spot.

## 6. Classification

- A (deep B200/TW dominant): CONFIRMED for B200's own injection
  (peaks k13–16; C7 deep-TW cells consistent); REJECTED for the total
  (surface-weighted via B280).
- B (distributed small-positive): PARTIAL — heavy-tailed (64% in top
  1000) across many sites; remainder distributed.
- C (operator balance): CONFIRMED as budget structure — three distinct
  roles (deep injector / neutral damper / surface injector).
- D (surface dominant): PARTIAL for total (k1–5 53%), contradicted for
  B200 (deep-peaked).
- OVERALL: C + A(B200) + B/D-background. The "where" is CLOSED:
  B200-deep-TW + B280-surface-imprint, heavy-tailed over sites,
  B210 neutral.

## 7. Implications for 11.5D (promotion still BLOCKED)

1. Do NOT promote N=24 (unchanged).
2. Depth-separated operator roles give the first ACTIONABLE map:
   B200-deep-TW vs B280-surface-imprint vs B210-neutral. Any future
   cadence/co-stepping design must treat deep and surface differently
   (surface responds to barotropic cadence, deep to thermal-wind
   accumulation rate).
3. Next (diagnostic-only, proposed): maxU-cell targeting already done
   (11.5C.7); remaining open: B200-global +2e7 term attribution at the
   top-1000 sites (C6 module + cell list from §5).
4. Artifacts: run `stage11.5C8_AprN24` (full April, INIT-OK);
   `fullfield_energy_aggregates.csv` (2088 rows), `spatial_top1000_d1.csv`;
   `stage11.5C8_janOFF` (Jan OFF, EXIT 0, INIT-OK, 32 files, md5-identical).
5. Files: NEW `src/stage115c8_full.f90`; `app/main.f90` hooks; this doc;
   INDEX 11.5C.8 row; ROADMAP status.
   Verification: Jan OFF (final binary, no env) md5-identical to
   `stage11.5C_janOFF` across ALL 32 outputs; full fpm battery PASS
   (no failures/errors); `git diff --check` clean.
