# Stage 11.5C.7 — Global Energy Injection / max-|U| Term Localization

Frozen (date). PURELY DIAGNOSTIC + SPATIAL LOCALIZATION. No physics,
EOS, CA, advection, ice-dynamics, or numerical-scheme change; no
guards/clamps; B200/B210/B280/advs/advt/CA/EOS/txic/shal untouched;
production defaults unchanged. Implementation: NEW module
`src/stage115c7_maxu.f90` (top-10 + 2-seed scan at B200/B210/B280
boundaries, env `STAGE115C7_MAXU_TRACK`, OFF → early return) + C6
3-slot cell override (`STAGE115C6_CELLS="i,j,k;i,j,k;i,j,k"`, filenames
unchanged, slots documented in run); 5 track + use/init hooks in
`app/main.f90` (additive calls only).

## 1. Max-|U| migration (tracker run `stage11.5C7_track`, N24, INIT-OK, killed d9)

Top cell per pass: d1s1 surface scattered ((22,16,1),(97,15,1) ~27–44)
→ d1s12 (6,21,1)/(24,18,16) ~53 → d1s23–24 hotspot (5,19,*) 266–471
(surface AND k=17 deep) → d2s1 (5,19,*) persists → d2s24 seed
neighborhood (111,17,*) 7.3e3→1.15e8 (B200 detonation there) → d3s1
(111,16,*) 5–10e7. i=5 is near-boundary; seed neighborhood is interior.
Event d3s1 (112,17,9) — 10th deterministic reproduction.

## 2. Per-operator dE at hotspot (5,19,1) d1s23–24 (offline join)

B200 −2..−3e4 (DAMPING), B210 −4..−6e3 (damping), B280 +1.3..+1.7e4
(ONLY injector) — same pattern as seed. Distribution over 207 recorded
day-1 (cell,pass) samples: B200 dE negative in 199 (sum −9.3e5),
positive in 8 (sum +28). B200 removes energy at essentially ALL
high-|U| cells; global +2.0e7 must come from the unsampled low/mid-|U|
bulk (avg +150/cell over ~140K — quasi-steady forcing wins where U
(and thus Coriolis/implicit damping ∝ U) is small).

## 3. Term decomposition at top cells (override run `stage11.5C7_terms`,
slots: file1=(5,19,1), file2=(5,19,17), file3=(111,17,15); residuals
worst 1e-6 — mirrors exact)

E-weighted day-1 B200: (5,19,1): Cor −9.3e4, Lap −2.7e4, TW −1.9e3,
DPX −397, solve +1.6e4 (net sink); (5,19,17) DEEP: TW +3.5e5 (!!),
Cor −8.25e4, Lap −2.46e4, solve +2.3e4, DPX +55 (NET +2.66e5 INJECTS);
(111,17,15): TW +1.3e5, Cor −2.1e4 (net +1e5 INJECTS).
B280 E-weighted: (5,19,1): bcl +7.3e4 (injects), btp −800;
(5,19,17): bcl −4.04e5 (removes), btp +1.5e3; (111,17,15): bcl −1.83e5.
(B280 pulls all levels toward the growing barotropic mean: surface
below mean +, deep above mean −; net global +.)
TW growth at (5,19,17): +4.6→+9.3→+33→+108→+247→+283 (60×/day, H2);
Cor −0.9→−81 (V-follower damping).

## 4. Localization verdict + classification

- Global +2e7 injection: deep-TW injectors ((5,19,17) +3.5e5,
  (111,17,15) +1.3e5 day-1 E) + distributed small-positive bulk
  (inferred arithmetically: +2.1e7 unattributed). Detonation site IS a
  TW injector from day 1.
- Variant A (localized TW source): CONFIRMED (primary) — deep TW
  injection with 60×/day H2 growth at/near the eventual detonation site.
- Variant B (distributed): PRESENT (bulk remainder) — A+B mix.
- Variant C (migrating): PRESENT (surface→(5,19)→seed-neighborhood).
- Variant D (not found): REJECTED.
- Overall: A-primary + B-background + C-migration. Surface cells are
  Coriolis-damped sinks; deep high-gradient cells are TW sources.

## 5. Implications for 11.5D (promotion still BLOCKED)

1. Do NOT promote N=24 (unchanged).
2. Depth structure matters: TW integral accumulates with depth → deep
   cells inject first; surface-focused diagnostics miss the source.
3. Next (diagnostic-only, proposed): full-field per-cell B200-dE map
   (requires in-loop accumulation instrumentation — 11.5D decision, as
   it touches the B200 loop region); maxU-cell list targeting worked
   and should be repeated if the grid/init changes.
4. Artifacts: runs `stage11.5C7_track` (killed d9), `stage11.5C7_terms`
   (override cells; killed d13) — both INIT-OK; `stage11.5C7_janOFF`.
   Process note: rm-vs-build race killed one battery + one Jan attempt
   (reran sequentially — never concurrent rm/build/run).
5. Files: NEW `src/stage115c7_maxu.f90`; C6 override (+~40 lines, env
   parse + slot dispatch; no physics lines); `app/main.f90` use/init/
   5×track (additive); this doc (NEW); INDEX 11.5C.7 row; ROADMAP status.
   Verification: Jan OFF (`stage11.5C7_janOFF`, final binary, no env)
   md5-identical to `stage11.5C_janOFF` across ALL 32 outputs; full fpm
   battery PASS; `git diff --check` clean.
