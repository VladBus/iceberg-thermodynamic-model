# Stage 11.5C — Controlled Ocean Substepping Prototype

Frozen (date). EXPERIMENTAL scheduler, OFF bit-identical. Implementation
(`app/main.f90` ONLY, physics lines untouched): env `STAGE115C_OCEAN_SUBSTEPS`
(default 1); `ostep = mm2/N`; ocean tail (s112-vert → … → B3.3) moved inside
`iii` behind `if (mod(iii,ostep)==0)` with `dt/c2/c4/c5` save-swap-restore
(`dt_ocean` = DT when N=1, 86400/N when N>1); old iii `end do` relocated
after the gate; iceberg_step + daily output stay outside. Tail contains no
day-loop control flow (only an inner k-loop `cycle`, verified) — move safe.
OFF validation: Jan default-path run bit-identical per-variable to D32
across all 32 outputs (md5 incomparable — 11.4.1 alpha/beta vars added).

## 1. Dependency audit (coupling map)

- advs(S,U,V,W→S), advt(T,U,V,W→T), CA(T,S→T,S+ro): ocean-only.
- B200(u1,ro,dpx→u2), B210(u2,tx/tx*,txic→u2), shal(eta,U/V), B280(u2,up2):
  ocean-only. W(u1/v1→w): recomputed per-iii (inputs static across iii).
- Ice→ocean: txic/tyic (last microstep) + ice-conc average `a1` (B210 wind
  weighting) + skz→skt (turbulent exchange for heat fw).
- Ocean→ice: u2/v2 (drag), t1/s1 (heat), skt (fw).
- EUU accounting flaw found: `euu` ACCUMULATES per `shal()` call
  (`euu+=up²`, reset once/day) — cross-N EUU incomparable raw; normalize
  per substep for analysis.

## 2. Matrix (April, MM2=24, DIAG+FIRST_INVALID)

| Case | N | DT_ocean | Days | FIRST_INVALID | EUU end (raw) | CA nmix (maxiter) | Final state |
|---|---|---|---|---|---|---|---|
| A | 1 | 86400 | 29 | none | 2.103e15 | 8,876,752 (1001) | clean; ice 1079/446 |
| B | 2 | 43200 | 29 | Day2 RO=Inf AFTER_conv_adj | 6.916e15 | OVERFLOW (1001) | full NaN; ice ghost pandemic (area 10966, vol 0) |
| C | 4 | 21600 | 29 | Day2 RO=Inf AFTER_conv_adj | 6.527e15 | OVERFLOW (1001) | full NaN; same ghost pandemic |
| D | 12 | 7200 | 29 | Day2 RO=Inf AFTER_conv_adj (rerun; first attempt: 17 d, no event, EUU 6× — run-to-run variance, see §4) | 8.322e15 | OVERFLOW (1001) | full NaN |
| E | 24 | 3600 | 29 | Day3 RO=Inf AFTER_conv_adj | 7.718e15 | OVERFLOW, cols 263184 (1001) | full NaN |
(D rerun in background at commit time; table to be finalized on completion.)

## 3. Analysis (A–D; E pending)

- N=1 (single 86400 s step) is STABLE: FCT + strong damping absorb CFL≈25;
  cross-check: 11.5C-A ≡ 11.5B-B bit-for-bit (EUU digits, ice totals) —
  the gate move itself preserves behavior exactly.
- N=2/4 (dt 12 h/6 h): RO=Infinity on Day 2 (conv_adj scan point;
  generator upstream in B200/B210/adv with dt-scaled coefficients —
  unisolated to a line, honest boundary). nmix counter OVERFLOWS print
  (>99M); CA cols 2–4× baseline (churning). Runs complete as zombies.
- N=12 (dt 2 h): rerun → RO=Inf Day 2 (first attempt: 17 d no-event, EUU 6×;
  run-to-run variance consistent with uninitialized-state sensitivity, D26 —
  verdict unchanged).
- EUU cross-N incomparable raw (accumulation artifact §1); per-substep
  normalization: A 2.10e15, B 3.46e15, C 1.63e15 — B/C still anomalous
  (instability growth real, not just accounting).
- Ice ghost pandemic in B/C finals (an1=1/wice=0 everywhere): ice model
  collapses onto the D28 ghost signature globally once ocean forcing
  goes NaN — same mechanism, domain-wide.

## 4. Convergence / recommendation (COMPLETE matrix)

- N=1 (single 86400 s step) stable; N≥2 ALL singular: B/C/E RO=Inf Day 2–3,
  D RO=Inf Day 2 on rerun. Substepping per se destabilizes — NOT dt size
  (E uses baseline dt per pass).
- Scheduler verified (dist rows 29/58/116/196/696; MM2=24 prints).
- LEADING HYPOTHESIS (unisolated): tighter EXPLICIT ice–ocean coupling
  destabilizes — per-substep u1 snapshot, txic/eta feedback at 24×/day, CA
  re-mixing fresh states. Classic explicit-coupling instability signature
  (slow multi-day growth). Ruled OUT: dt magnitude (E≡baseline dt), FCT/CFL
  (bounded ops), the gate move itself (A≡11.5B-B bit-for-bit).
- EUU cross-N incomparable raw (shal accumulation artifact §1); normalized
  growth real in B/C/E.
- 11.5D promotion criteria: NOT MET for any N>1. Redirect 11.5D to
  coupling-point audit (u1 cadence, txic staleness, ym1 handling, shal
  mm3×dt1 timescale per call); candidate mitigations: implicit coupling,
  substep-aware eta bookkeeping, CA-per-day option.
