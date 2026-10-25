# Stage 11.5D.1 — Family A Controlled Temporal Integration Prototype

Frozen (date). Implementation + measurement per 11.5D.0 §4 Family A.
No physics change (EOS, CA threshold, B200/B210/B280 equations, shal
internals, advection, ice, thermo, EN4/ERA5/grid/coefficients all
untouched); no clamps/damping; Family B NOT implemented.

## 1. Implementation (`app/main.f90` ONLY, +44/−1)

Env `STAGE115D1_FAMILY_A_N` (default unset → legacy untouched):
validated 1≤N≤mm2 else legacy-with-warning; takes precedence over
`STAGE115C_OCEAN_SUBSTEPS` (documented). When set: reuses the 11.5C
gate machinery (`nsub_115c`/`ostep_115c`/`dt_ocean`) with
dt_sub = 3600/N (NOT 86400/N) — ocean integrates 3600 s/day TOTAL for
every N; `ostep = mm2/N` (N=1/2/4/6/12/24 → ostep 24/12/6/4/2/1 at
MM2=24; B3.3 firing prints confirm). Three behavioral deltas vs 11.5C:
(a) shal fires ONLY at iii==mm2 (last fire) — its fixed 3600 s then
equals the daily ocean total for every N (N=1/legacy: the single fire
is at iii==mm2 — unchanged); (b) W recompute uses dt_sub on firing
iiis (early dt-swap before the W block, N>1 only; single swap/restore
pairing preserved via `famA_preswapped` flag); (c) ice/thermo/forcing/
output/iceberg_step byte-untouched.
N=1 analysis: ostep=mm2, dt_sub=3600=dt (swap numerically no-op, as
11.5C-A proved), single fire at iii==mm2, shal fires — structurally
identical to legacy → EXPECTED bit-identical (proven §2).

## 2. N=1 equivalence gate — PASS (triple)

- April mm2=12: pure-legacy (no env) vs FamilyA-N=1 → 31/31 NetCDF
  md5-identical (`stage11.5D1_AprLegacy` vs `stage11.5D1_AprN1`).
- April MM2=24: FamilyA-N1 vs 11.5C-AprA → 31/31 identical.
- January mm2=12: FamilyA-N1 vs `stage11.5C_janOFF` → 32/32 identical.
Gate HELD: no N>1 run launched before proof (matrix launched after).

## 3. Matrix results (April MM2=24, DIAG+FIRST_INVALID+TRACE+GAIN; all INIT-OK)

| N | dt_sub | EXIT | Events | maxU d1/d2/d29 | EUU d1/d7/d29 | CA maxiter |
|---|---|---|---|---|---|---|
| 1 | 3600 | 0 | 0 | 26.8/~/404.7 | 6.585e14/7.786e14/2.248e15 | 1001 (=baseline) |
| 2 | 1800 | 0 | 0 | ~24.6/~25/— | …/…/2.183e15 | 1001 |
| 4 | 900 | 0 | 0 | ~23.5/—/— | …/…/2.141e15 | 1001 |
| 6 | 600 | 0 | 0 | ~23/—/— | …/…/2.117e15 | 1001 |
| 12 | 300 | 0 | 0 | ~—/27–28/— | …/…/2.104e15 | 1001 |
| 24 | 150 | 0 | 0 | 21.7/~/399.7 | 6.589e14/7.711e14/2.047e15 | 1001 (nmix print OVERFLOWS: 24× CA calls/day — accounting, not pathology) |

3-day gate: PASS all N (no NaN/Inf; maxU ~20–30 ≪ 1000 cm/s; RO sane;
CFL P95<1 per 11.5B DT-only finding at dt≤3600 — dt_sub only smaller).
7-day gate: PASS all N (bounded EUU trajectories; CA unchanged from
baseline incl. pre-existing 1001-guard saturation (T-01 family);
conservation closure audit does not exist — prerequisite noted in D0,
conditionally skipped per spec).
29-day gate: PASS all N (EXIT 0; EUU d29 N1→N24 −9% monotonic
2.248e15→2.047e15; slow drift to ~400 maxU by day 29 present in N=1
too — pre-existing prognostic drift family (cf. 11.1/10.20), NOT a
Family-A regression; N24 within 1% of N1 at day 29).

## 4. Term comparison across N (day-1 per-op dE, GAIN module)

| N | B200 | B210 | B280 | shal | net |
|---|---|---|---|---|---|
| 1 | +1.68e5 | +1.03e6 | −1.88e5 | 0 | +1.01e6 |
| 2 | +6.8e4 | +5.8e5 | −1.27e5 | 0 | +0.52e6 |
| 4 | +1.7e4 | +4.7e5 | −8.9e4 | 0 | +0.40e6 |
| 6 | −768 | +4.8e5 | −7.4e4 | 0 | +0.41e6 |
| 12 | −1.9e4 | +5.0e5 | −5.9e4 | 0 | +0.42e6 |
| 24 | −2.7e4 | +5.1e5 | −5.1e4 | 0 | +0.43e6 |

(B280 N24 = −5.05e4 — table value kept exact; net recomputed
accordingly ≈ +4.3e5.) B200 DECREASES with N and flips sign at N≥6
(finer dt_sub → super-linearly smaller increments: implicit solve
damps more at small dt); B210 halves once then flat (spin-up fill
conserved-ish across passes); B280 magnitude shrinks with N. Net day-1
halves+ from N1 (+1.0e6) to N≥4 (+0.4e6). TW-vs-N term split NOT
measured (REG not enabled; B200-total-vs-N suffices for the gate
question; TW-specific-vs-N proposed for 11.5D.2).

## 5. Interpretation (per spec §6: timestep/cadence/coupling/splitting)

Total integrated ocean time is FIXED (3600 s/day) for all N — therefore
the −9% EUU drift and the B200 sign flip CANNOT come from total time.
Remaining confounded triple: (a) timestep refinement (dt_sub 3600→150 s;
B200 increments shrink super-linearly — consistent with dt-scaling +
stronger implicit damping); (b) operator cadence (N× calls/day);
(c) coupling freshness (ice reads u2 updated N×/day vs 1×) + smaller
splitting error. The experiment ISOLATES total-time (ruled out) but
does NOT separate a/b/c — stated honestly; separating them needs
single-factor follow-ups (11.5D.2 proposal: same-N different-cadence
vs same-cadence different-dt — expensive, deferred).
vs 11.5C-E (N24 full-day, dt=3600, 86400 s/day → blowup day 3):
FamilyA-N24 (3600 s/day, dt=150) is clean 29 d. Difference = total
ocean time (24×) + dt (24×) + shal cadence (1×3600 vs 24×3600).
Total-time is the leading suspect (it is the only 24× factor; dt goes
the stabilizing direction per §4), but NOT isolated — no root-cause
claim beyond: substepping per se (at fixed totals) is BENIGN.

## 6. Family B implications

Promotion rule (§6.4 D0) SATISFIED: Family-A N=24 passed all applicable
gates → Family-B experiments MAY be proposed (11.5D.2+; NOT this stage,
NOT started). Note for proposers: Family B needs shal-dt-awareness +
W + re-baseline (D0 §4 flagged RULES-procedure changes) and must
reproduce-then-tame the E-blowup; Family A result predicts the blowup
returns with full-day totals (testable prediction).

## 7. January regression (TASK 8)

JanN1 (mm2=12) ≡ janOFF bit-wise (32/32 — §2). JanN24 (MM2=24):
EXIT 0, zero events, maxU d1/d5/d29 = 19.7/19.0/418.8 vs JanN1
42.6/55.4/403.8 (same slow-January class; pre-existing seasonal drift
family per 11.1, NOT a Family-A effect). STABLE, physically reasonable.

## 8. Files + verification

- `app/main.f90` (+44/−1: decls/env/preswap/skip-reswap/shal-gate).
- Docs: this file (NEW); INDEX 11.5D.1 row; ROADMAP (11.5D.1 status).
- Verification: triple N=1 equivalence (Apr-mm12, Apr-MM24-vs-AprA,
  Jan-vs-janOFF); full fpm battery (see commit); `git diff --check`
  clean; shal/physics/EN4/ERA5/grid/coefficients untouched; Family B
  NOT implemented; no damping/clamps.
