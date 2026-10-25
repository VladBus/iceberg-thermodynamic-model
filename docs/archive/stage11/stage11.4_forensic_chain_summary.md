# Stage 11.4 Forensic Chain Summary (D24–D32) — archive condensation

Frozen 2026-09-29. This document condenses §§17–25 of
`stage11.4_en4_stabilization.md` (which remain the frozen primary record).
Question: why did Apr/Jul/Oct crash on Day 1 while Jan survived?

## Established causal chain (each link printed/traced, then fixed)

1. **Coverage gap (D31):** April/July/October ERA5 monthly files start at
   65.0°N; model cell (2,96) sits at 64.9578°N → `era5_bilinear2d` ok=false →
   `cycle` (`wind_forcing.f90:266-270`) → meteo arrays stay at init 0.0
   (55/13965 cells; log warning + p1-min-0.0 corroborate). January file starts
   at 63.0°N → covered.
2. **a3 = 0/0 (D31):** `ppatm`=0 → `ratm`=0 → `a3`=NaN in `heat()`; `el`/`a1`
   NaN; Newton exits via IEEE-false while-check; fallback/branch checks false
   → melt branch → `dhic1`=NaN → `hicp`=NaN (heat Day-1 iii=2, k=1, (2,96)).
   First NaN is created HERE (bracketed: pre-heat finite → intra-heat NaN).
3. **Aggregate + guard failure (D30/D29):** redis632 → `hices`=NaN →
   dynamics `hht`=NaN → guard `(hht<0.01)` FALSE per IEEE → `a`→`txic`→`b3`→
   `a2/b2`→`u/v` all NaN (printed full chain; `a3`-path clean).
4. **Transport + manufacture (D28):** `adv2d` imports NaN (POST_ADV iii=2);
   REDIS stage-5 fallback (`ice_redis.f90:234-236`) manufactures
   (`an1`=1.0, `wice1`=NaN)@(2,95). `adv2d`/boundary/ocean-u2v2 exonerated
   as creators (importers/carriers only).
5. **Scratch + ocean (D27/D26/D25/D24):** shared `tpar/spar(6)` carry NaN
   (staleness=carrier, proven by INIT experiment); heat else-branch
   `0×NaN` → `s1/t1` NaN; `advs` propagates (FIRST INVALID Day-1 iii=13
   at (2,2,1)); ocean zombie. Blind MAX-guards REJECTED and reverted (D27).
6. **Fix (D32):** nearest-edge latitude fallback in `era5_wind()` (loader-only,
   no physics/clamps). Apr 29 d + Jul/Oct 30 d clean (day-01 0 NaN); Jan
   32/32 md5-MATCH. **Accident CLOSED.**
7. **Cleanup + baselines (D33):** 6 forensic modules + hooks removed (zero
   physics `-` lines); runs 11 GB→2.8 GB; full battery + strict build clean;
   Ocean Baseline 11.x fixed (Jan30/Apr29/Jul30/Oct30, 0 NaN).

## What this chain did NOT establish (explicit non-claims)

- CA float32 quantization (T-01) and legacy Eckart EOS remain separate,
  real, non-fatal issues (see 11.3C inventory + EOS-80 plan).
- Small finite negative-ro excursions persist (monitored, non-NaN).
- `mm2=12` covers 12 h/day (legacy cadence, documented in 11.3C).
