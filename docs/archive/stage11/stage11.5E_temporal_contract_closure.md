# Stage 11.5E — Temporal Contract Closure + Constants Audit + Conservation + Convergence

Frozen (date). VALIDATION + AUDIT + DOCUMENTATION. No physics,
EOS, CA threshold, B200/B210/B280/shal/advs/advt/CA/EOS/ice equations,
EN4/ERA5/grid/coefficients changed; no guards/clamps; production
defaults unchanged. No new env switches were needed (E1–E5 use code
audit + existing runs + existing env paths — stated explicitly per
spec allowance; nothing new to gate). Stage 12 NOT started.

## 1. E1 — Temporal contract table (all operators; N=1 vs Family-B dt≤225)

| Operator | Calls/day (N=1) | Calls/day (FamB) | dt used | Increment/call | Hardcoded? |
|---|---|---|---|---|---|
| ERA5 forcing | 1 (kkk) | 1 (unchanged) | daily slice | 1 slice | no (file-driven) |
| heat (thermo) | 24 (iii) | 24 (unchanged) | dt=3600 (arg) | dt-scaled ✓ | no |
| ice dynamics | 24 (iii) | 24 (unchanged) | internal dt1_val=120 fixed | fixed microstep | YES (fixed, but ice cadence unchanged → no conflict) |
| adv2d/redis | 24 (iii) | 24 (unchanged) | 3600-class | unchanged | no |
| W recompute | 24 (iii) | 24 (unchanged) | dt variable | dt-aware ✓ | no |
| advs/advt | 1 | 384–576 | dt_sub (swapped) | dt-scaled ✓ | no |
| CA | 1 | 384–576 | n/a (state-iterative) | per-call | no (no dt arg) |
| B200 | 1 | 384–576 | dt_sub (swapped) | dt-scaled ✓ | no |
| B210 | 1 | 384–576 | dt_sub (swapped) | dt-scaled ✓ | no |
| shal | 1 (3600 s fixed) | 1 (3600 s fixed) | dt1=120/mm3=30 HARDCODED locals | FIXED 3600 s/call | YES — structural (see E3) |
| B280 | 1 | 384–576 | n/a (algebraic) | per-call | no |
| iceberg_step | 1 | 1 (unchanged) | 3600 | unchanged | no |
| write_nc | 1 | 1 (unchanged) | n/a | — | no |
| gladw (pressure smooth) | 1 (forcing) | 1 (unchanged) | dt=3600 hardcoded local | fixed coeff | no conflict (daily preprocessing, not integrated) |
| thermal_wind_init | 1 (startup) | 1 (startup) | dt_val=3600 local | init-only | no conflict (t=0 state) |

## 2. E2 — Hard-coded constants audit (repo-wide grep)

- `3600[.0]`: iceberg_thermodynamics (hour→sec CONVERSION, not step),
  netcdf_input (`days*86400+h*3600` time conversion), smooth_filter:36
  (`dt=3600` smoother coeff — daily preprocessing, §1), thermal_wind_init:330
  (init-only), main:179 (`dt=3600` master step — THE step, parameterized
  downstream via swaps), s112 diagnostics (labels/CFL reference values).
- `120[.0]`: main:185 (`dt1=120` master barotropic step), shal:97
  (LOCAL shadowing to 120 — the conflict), ice_stress:68 (`dt1_val=120`
  ice microstep — fixed by ice-cadence design, no conflict),
  s112_compute_barotropic_cfl(120.0) (diagnostic literal matching shal).
- `86400[.0]`: netcdf_input (day→sec conversion), iceberg_types
  (`LOW_FLOW_TIME_SCALE_S`, diagnostic), main comments/prints.
- `30[.0]`: shal:102 (`mm3=30` LOCAL — the conflict); main mm3
  (overridden by STAGE113 when active).
- `12/24`: mm2 legacy assignments (12) + STAGE113 override path (24);
  documented, env-driven.
- MM2/MM3/DT/DT1: main-owned globals, correctly threaded via swaps
  EXCEPT shal's shadowing locals (E3).
- python/: units.py conversions (presentation only, no model impact).

## 3. E3 — Dimensional consistency: ONE structural conflict + clean rest

- CONFLICT (known, binding): `shal()` re-declares `dt1=120.0`/`mm3=30`
  as LOCALS, shadowing main's globals — shal ALWAYS integrates 3600 s
  per call regardless of dt_sub. Consequence: shal can NEVER substep
  with the ocean (Family A/B both hold it at 1×/day by design). Making
  shal dt-aware = changing shal LOCALS → behavior change → RULES
  approval procedure required (NOT done here; flagged for 11.5D
  follow-up IF full-day barotropic evolution is ever required).
- CLEAN: heat(dt-arg), advs/advt(dt,c2 args), B200/B210(dt variable),
  W(dt variable), CA (stateless iterative), EOS (state function),
  ice (fixed internal microstep by cadence design), gladw/thermal-init
  (non-integrated), conversions (units, not steps).

## 4. E4 — Conservation N=1 vs dt=225 vs dt=150 (April days 0–7/29)

- Salt: all three −1.1% d0→1 (spinup transient) then −0.02∼0.03%/7d,
  identical to 4 digits — NO artificial salt drift from Family B.
- Heat: N1 −1.0% d7 / −3.2% d29 (surface cooling fluxes); dt225 −21.7%
  d7 / −49% d29; dt150 −22% / −51%. FAMILY-B DRAINS OCEAN HEAT ~20×
  FASTER (bulk cooling at ALL levels + extra surface; §5 mechanism).
- Ice (cause/correlate): N1 vol 215→358 (1.7×/month); dt225 778→2736
  (3.5×); dt150 779→1872 (2.4×). Family B grows 5–8× legacy ice by
  day 29 (accelerating). Mechanism: 24×-responsive ice↔ocean coupling
  (fresh skz/T/S each iii vs day-stale legacy) → stronger entrainment +
  freezing → ocean heat loss + ice growth (second-order feedback loop;
  exact partitioning unisolated — honest boundary).
- EUU: N1 7.79e14 vs dt225 7.71e14 vs dt150 ~same d7 (−1%: fine).
- VALIDATION GAP (blocking): which ice regime is correct is
  UNVALIDATED (no sea-ice extent obs in scope; April Barents observed
  extent is large — neither 1.6% nor 5% conc is validated). Family B
  changes climate 5–8× vs legacy → CANNOT promote without OSI-SAF/NSIDC
  sea-ice validation (proposed).

## 5. E5 — Temporal convergence 225 vs 150 (day-29 fields)

- Heat content: 2.178 vs 2.163e28 (0.7% — CONVERGED bulk).
- Fields: T RMS 0.27 K (max 4.0); S RMS 0.0031 (max 0.061, 3× mean
  locally); RO RMS 2.5 (max 49); U RMS 0.22 (280% of mean, max 6.2);
  V RMS 0.35 (max 10.4). Ice vol 2736 vs 1872 (46% apart).
- VERDICT: NOT converged in detail (eddy/phase-level O(1) differences;
  chaotic divergence at 29 d makes bit-convergence impossible in
  principle); bulk heat converges, ice diverges (threshold behavior).
  dt=225 ≠ dt=150 interchangeably. Family B needs smaller dt or
  ensemble/statistical validation — NOT production-ready on
  convergence grounds either.

## 6. Final assessment

- Family B (dt≤225) is STABLE (no NaN 29 d April + 8 d January) but
  produces a DIVERGENT CLIMATE (5–8× ice, −50% ocean heat/month) that
  is unvalidated and unconverged across dt. Stability ≠ correctness.
- Recommended dt: NONE for production. Reference dt=150 for further
  forensics (slowest drift). The dt-threshold (11.5D.3) bounds
  STABILITY; this stage bounds CORRECTNESS — and correctness fails.
- What 11.5D must address (proposal only): (a) sea-ice extent
  validation gate (OSI-SAF/NSIDC) before ANY Family-B promotion;
  (b) ice↔ocean coupling-cadence study (fresh-vs-stale skz/T/S
  experiment — the heat-drain mechanism); (c) co-stepping design
  must include the thermodynamic closure, not just momentum
  (11.5D.0 contract covers momentum cadence only — EXTEND it);
  (d) shal dt-awareness via RULES procedure IF full-day barotropic
  evolution is required (currently held 1×/day by design).
- Stage 12 (voxel thermodynamics) implications: built on the ocean/ice
  thermodynamic interface — MUST NOT start until the interface
  cadence semantics are validated (this stage shows they are not).

## 7. Files + verification

- Docs: this file (NEW); INDEX 11.5E row; ROADMAP (11.5D.3 COMPLETE,
  11.5E status).
- Code changes: NONE (audit + existing runs + Jan reruns only;
  no STAGE115E_* switches needed — nothing new to gate; stated per
  spec allowance).
- Verification: Jan OFF (`stage11.5E_JanN1`) md5-identical to
  `stage11.5C_janOFF` across ALL 32 outputs (current binary, no env);
  JanDT225/JanDT150 stable-flat 8 d, 0 NaN; full fpm battery PASS;
  `git diff --check` clean; NO physics/production-defaults changes.
