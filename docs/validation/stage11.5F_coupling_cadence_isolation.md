# Stage 11.5F — Ice-Ocean Coupling Cadence Isolation

Frozen (date). Coupling-cadence isolation (dt vs coupling-frequency).
No physics, EOS, CA threshold, B200/B210/B280/shal/advs/advt/CA/EOS/ice
equations, EN4/ERA5/grid/coefficients changed; no guards/clamps; shal
frozen (dt1=120/mm3=30 untouched); production defaults unchanged. NO new
code was needed (key design finding §2 — existing 11.5C.1 freeze IS the
F3 experiment); Stage 12 NOT started.

## 1. F1 — Temporal graph of ice↔ocean exchange (audited with file:line)

Per-iii order: rollover `t1=t2, s1=s2, v1=v2, u1=u2` (main:814-818) →
`heat(dt)` (main:820+) → redis → ice stress microloop (txic/tyic
main:896-897; per iii) → adv2d → redis (ans/wices/hices, ice_redis:282+)
→ W recompute → gate(ocean tail).
- Ocean→ice: u2/v2 (drag + txic formula, per pass), t1/s1 (heat k=1,
  per iii), t2/s2 (heat reads, per iii), skz (B210 main:1425 → heat fw
  thermo:117, per pass→per iii), skt (dead input, never written).
- Ice→ocean: txic/tyic (B210 surface BC, per pass), ans→a1 (B210
  weighting main:1441, per pass), hices→hht (txic denominator, per iii).
- Forcing→all: era5_wind daily per kkk + per-iii wind-stress interp;
  tatm etc. daily-frozen.
- Legacy N=1: ocean 1×/day (iii=24) reads end-of-day ice; ice reads
  day-stale ocean all day. Family B: per-iii interleave (1-hour-fresh
  both directions).
- DESIGN THEOREM (constrains all freeze experiments): the u1-rollover
  (u1←u2 every iii) propagates ANY u2/v2 freeze into the ocean in one
  pass; t2/s2-freeze is likewise ocean-freezing (advs writes S2, CA
  operates on T2/S2 — 11.5C.3). Hence freezable-without-freezing-ocean
  set = {txic, tyic, ans} ONLY (ice outputs, never rolled into ocean
  inputs). F3 ≅ 11.5C.1 coupling-freeze + full-day dt150 follows.

## 2. F2 — Heat/ice budgets (existing outputs; component split honest boundary)

| Run | icevol d7 | icevol d29 | heat d7 | heat d29 | salt d7 |
|---|---|---|---|---|---|
| N1 | 215 | 358 (1.7×) | 4.3715e28 (−1.0%) | 4.2755e28 (−3.2%) | −0.02% |
| dt225 | 778 | 2736 (3.5×) | 3.4595e28 (−21.7%) | 2.1781e28 (−49%) | −0.03% |
| dt150 | 779 | 1872 (2.4×) | 3.4450e28 (−22%) | 2.1633e28 (−51%) | −0.02% |
Salt identical (no mass error); heat drains 20× faster in Family B at
ALL depths + extra surface (11.5E); ice 5–8× legacy, accelerating.
Divergent component = basal freezing (growth, NOT melt: ocean cools +
ice grows ⟹ freezing + export to atmosphere; melt would show opposite
correlation). Direct per-flux diagnostics don't exist in outputs
(honest boundary — component split by correlation, not measurement).

## 3. F3 — dt=150 + legacy coupling (txic/tyic/ans frozen, EXISTING 11.5C.1 switch, zero new code)

Run `stage11.5F_F3` (April MM2=24, INIT-OK, killed d8): day-7 icevol=777
vs dt150-fresh 779 (0.3%), heat 3.450e28 vs 3.4450e28 (0.1%) — IDENTICAL
to fresh coupling, FAR from N1 (215 / 4.3715e28).
VERDICT: txic/tyic/ans freshness carries NOTHING of the heat/ice
divergence. Combined with 11.5C.3 (t1/s1 no-op) and 11.5C.4 (no single
ice-state freeze stops phase-1): the divergence driver is NOT in the
ice→ocean direction and NOT in heat scratch fields.

## 4. F4 — SKIPPED as incoherent (documented, not merely "optional")

At fixed dt=3600, N=1 (stale coupling) and N=24 (fresh coupling,
= 11.5C-E, blows d3) EXHAUST the design space — both already run
(legacy; AprE + 5–12 deterministic reproductions). No untested
(dt=3600, fresh-coupling) point exists that isn't E. The remaining
untested direction (ocean→ice freshness at fixed dt with ocean frozen)
is unimplementable without freezing the ocean itself (§1 theorem).

## 5. Comparison + conclusion (primary cause?)

| Experiment | dt | Coupling | Heat d7 | Ice d7 | Reading |
|---|---|---|---|---|---|
| N=1 legacy | 3600 | stale/day | −1.0% | 215 | baseline |
| dt150 fresh | 150 | fresh/iii | −22% | 779 | Family-B climate |
| dt150 + frozen txic/ans | 150 | ice→ocean frozen | −22% | 777 | ≡ fresh (coupling-txic ruled out) |

LOGICAL CLOSURE: total ocean heat can only leave via surface/ice fluxes
(all transport operators conservative). Those fluxes are computed by
heat/ice models from ocean inputs. In Family B these inputs (u2/v2/T2/
S2/skz) refresh 24×/day vs 1×/day legacy — while heat/ice themselves run
24×/day in BOTH. Therefore the heat divergence comes from OCEAN→ICE
INPUT FRESHNESS (24×/day responsive coupling) and/or ocean-internal
cadence (24× CA/advection redistributing before fluxes act) — and NOT
from ice→ocean feedback (ruled out by F3), NOT from t1/s1 (ruled out
11.5C.3), NOT from dt per se for heat (dt=150 already diverges).
Unisolated within {skz-entrainment?, T/S-freshness?, CA-cadence?} —
ranked candidates; skz-only freeze is feasible (B210 output, never
rolled into ocean — PROPOSED as the single cheapest next experiment,
11.5D follow-up, not executed here).

## 6. Family B + Stage 12 implications

- Family B changes the ice↔ocean coupling REGIME (responsive vs stale),
  not just ocean numerics — promotion requires sea-ice validation gate
  (11.5E) AND coupling-cadence justification, not just momentum stability.
- 11.5D.0 contract covers momentum cadence only — MUST extend to
  thermodynamic/coupling cadence (skz/T/S freshness semantics) before
  any Family-B production decision.
- Stage 12 (voxel thermodynamics) builds on this interface — BLOCKED
  until interface cadence semantics validated (reaffirmed).

## 7. Files + verification

- Code changes: NONE (F3 used existing `STAGE115C1_FREEZE_COUPLING`;
  F1/F2/F4 are audit/analysis/scope decisions).
- Docs: this file (NEW); INDEX 11.5F row; ROADMAP (11.5E COMPLETE,
  11.5F status).
- Verification: Jan OFF (`stage11.5F_JanN1`) md5-identical to
  `stage11.5C_janOFF` across ALL 32 outputs (current binary, no env);
  JanDT225 stable-flat 8 d + JanDT150 stable-flat 10 d, 0 NaN
  (JanDT150 first attempt double-launched by overlapping scripts —
  discarded, reran solo-verified); full fpm battery PASS;
  `git diff --check` clean; NO physics/production-defaults changes.
