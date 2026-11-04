# Stage 11.5C.8.1 — Full-Field B200 Term Attribution (top-1000 cells)

Frozen (date). PURELY DIAGNOSTIC + TERM ATTRIBUTION. No physics, EOS,
CA, advection, ice-dynamics, or numerical-scheme change; no guards;
B200/B210/B280/advs/advt/CA/EOS/txic/shal untouched; production defaults
unchanged. Implementation: NEW module `src/stage115c81_attr.f90` (env
`STAGE115C81_ATTR`, OFF → early return) + 8 call sites in `app/main.f90`
(use/init/6×op-snap-accumulate; additive calls only).

## 1. Method (aggregates only; 4 CSV rows total)

Per B200/B210/B280 boundary, full-field: C6-identical term mirrors
(B200: TW/DPX/Cor/Lap/solve, ice≡0; B280: btp/bcl; B210: exact total),
first-order dE_term = 2U·dU_term + 2V·dV_term accumulated per-cell over
day-1 (9 arrays ≈ 9 MB) + quadratic remainder aQ per op (exact =
first-order + quadratic). At day-2 entry: rank by cell first-order
total → top-1000/100/20 + all-positive sets → per-term sums →
`term_attribution_aggregates.csv` (subset,ncells,8 sums,total_firstorder,
total_exact). NaN-safe (skipped+counted; ninv=0 day-1).
KEY SEMANTIC (documented): first-order = LATE-weighted (early U≈0
contributes ~0 regardless of dU); exact = spin-up-fill-inclusive.
Selection is by FIRST-order total ≠ C8's exact ranking (different
question: sustained injection vs one-time fill).

## 2. Execution (N24 April, realistic EN4 INIT-OK, killed day 2+)

Run `stage11.5C81_AprN24` (TRACE + ATTR). Dump at day-2 entry:
top-cells=1000, ninv=0. Subsets: top-1000 (1000), top-100 (100),
top-20 (20), all-positive (1532 cells).

## 3. Attribution table (day-1; first-order | exact)

| subset | B200_TW | B200_Cor | B200_DPX | B200_Lap | B200_solve | B280_btp | B280_bcl | B210 | 1st-tot | exact |
|---|---|---|---|---|---|---|---|---|---|---|
| top-1000 | +1.96e5 | −6.86e4 | +1.82e4 | −5.85e4 | −2.30e5 | +3.56e5 | +0.86e5 | −4.9e4 | +2.49e5 | +1.42e6 |
| top-100 | +1.11e5 | −2.85e4 | +0.13e4 | −4.20e4 | −1.79e5 | +0.91e5 | +2.83e5 | −4.2e4 | +1.94e5 | +1.08e6 |
| top-20 | +0.97e5 | −1.08e4 | −0.02e4 | −2.14e4 | −0.94e5 | +0.17e5 | +1.48e5 | −1.6e4 | +1.20e5 | +0.60e6 |
| all-pos | +2.09e5 | −0.74e5 | +0.23e5 | −0.60e5 | −2.38e5 | +4.12e5 | +0.27e5 | −4.9e4 | +2.51e5 | +1.45e6 |

- B200 first-order NET is NEGATIVE in all sets (−1.4e5 top-1000);
  its only big positive term is TW (+1.96e5); Cor/solve/Lap damp.
- B280: btp DOMINATES at top-1000 (+3.56e5, 81% of B280) and all-pos
  (+4.12e5, 94%); bcl leads ONLY at top-20 (+1.48e5 vs +0.17e5) —
  attribution FLIPS with subset: extreme injectors = bcl-driven (seed
  story), broad base = btp-driven.
- B210 negative everywhere (−4..−5e4 first-order).
- Closure: first-order (+2.5e5) vs exact (+1.4e6) = 5.7× gap = quadratic
  spin-up fill (one-time transient). C8 exact global (+3.21e7) is
  dominated by this fill; first-order isolates SUSTAINED injection.

## 4. Central refinement (new vs 11.5C.8)

Exact day-1 +3.21e7 is DOMINATED by quadratic spin-up fill (large dU
from rest, B210 +2.8e6/pass early transient) — a ONE-TIME transient,
not the runaway. The DANGEROUS component is first-order sustained
injection (TW +2.1e5, btp +4.1e5 day-1, both H2-growing 60×/450×) that
CONTINUES past day 1 (day-2 E 3e7→3e16 is first-order-dominated).
Phase-1 = spin-up fill (harmless alone; N1 absorbs its single fill) +
growing first-order feedback (TW/btp H2) that 24×/day compounding
keeps feeding. This splits 11.5C.5's E+F into transient + sustained
parts — the sustained part is the 11.5D target.

## 5. Hypothesis verdicts

- A (TW >70% of B200 +2.007e7): REJECTED as stated (B200 first-order
  net negative; exact dominated by quadratic fill). REFINED: TW is
  B200's sole significant SUSTAINED-positive term (+1.96e5 top-1000;
  79% of first-order total) — A holds for the sustained component.
- B (TW 30–70% multi-term): closest for first-order total if counting
  btp alongside (btp 143%, TW 79%, negatives offset).
- C (TW <30%): REJECTED (TW 79% of sustained total).
- D (bcl >70% of B280): REJECTED except top-20 (bcl leads only the
  extreme 20; btp 81–94% elsewhere).
- E (btp >70% of B280): CONFIRMED for top-1000/all-positive (81/94%).
- OVERALL: E + refined-A (TW = B200's sustained-positive; btp =
  B280's broad injector; bcl = extreme-cell injector) + spin-up/fill
  vs sustained split.

## 6. Implications for 11.5D (promotion still BLOCKED)

1. Do NOT promote N=24 (unchanged).
2. Target the SUSTAINED first-order feedback (TW + btp H2 growth), not
   the spin-up fill (transient, N1-safe) and not magnitude-dominant
   Coriolis (damping). E-weighted + spin-up-discounted metrics required.
3. Next (diagnostic-only, proposed): late-day (passes 20–24) term
   attribution (first-order-dominated regime, no fill contamination);
   maxU-cell list already available (11.5C.7).
4. Artifacts: run `stage11.5C81_AprN24` (killed d2+, INIT-OK);
   `term_attribution_aggregates.csv` (4 rows); `stage11.5C81_janOFF`.
5. Files: NEW `src/stage115c81_attr.f90`; `app/main.f90` hooks; this doc;
   INDEX 11.5C.8.1 row; ROADMAP status.
   Verification: Jan OFF (`stage11.5C81_janOFF`, final binary, no env;
   EXIT 0, INIT-OK, 30 d / 32 files) md5-identical to `stage11.5C_janOFF`
   across ALL 32 outputs; full fpm battery PASS (no failures/errors);
   `git diff --check` clean.
