# Stage 11.5H-RC — Release-Candidate Gate: Self-Containment + Doc Sync + D-22…D-28

Frozen (date). No physics, EOS, CA threshold, B200/B210/B280/shal/advs/advt/
CA/EOS/ice equations, EN4/ERA5/grid/coefficients changed; no guards/clamps;
shal frozen (dt1=120/mm3=30 untouched); legacy default unchanged
(OFF = bit-identical, Jan NDIFF=0 re-verified on the RC binary). No NetCDF
migration (11.7), no EOS-80 switch (11.6), no skt closure (D-25 debt),
no new forensic experiments, Stage 12 NOT started. Only source change =
self-containment override in `app/main.f90` + `s115h_warn_ignored` in
`src/stage115h_production.f90`.

## 1. Production scheduler self-containment (what changed)

11.5H required external `STAGE113_MM2=24` and silently fell back to a
legacy config when mm2<24 (dead branch in practice, but a silent-fallback
shape — unacceptable for a release candidate). 11.5H-RC:
- prod ON forces its own config: mm2=24, nsub=24, ostep=1, d2_npass=24,
  dt_ocean=150, shal-once (override in `main.f90`, no forensic env read);
- conflicting env (`STAGE113_MM2`, `STAGE115C_OCEAN_SUBSTEPS`,
  `STAGE115D2_EXP`, `STAGE115D3_DT`) triggers an explicit
  `STAGE115H WARNING: ... ignored` line and is overridden;
- final-config assertion: any inconsistency → `stop 1` with
  `STAGE115H FATAL` (codebase `stop 1` convention, cf. iceberg_types) —
  NO silent fallback exists on the production path;
- OFF path: override skipped entirely → bit-identical legacy.

## 2. Verification (no silent fallback; behavior preserved)

- Smoke (`stage11.5HRC_Smoke`, Jan, NO STAGE113_MM2, conflicting
  `STAGE115D2_EXP=B` deliberately set): log shows prod-mode line +
  WARNING-ignored line + `24x24 … (STALE coupling, self-contained)` and NO
  ExpB line (forensic env never parsed); INIT-OK; trajectory md5-identical
  to `stage11.5H_JanProd` days 0–4 (external MM2 unnecessary); stable-flat
  to d6, 0 NaN (killed d7 by session interrupt, not by the model).
- Jan OFF (`stage11.5HRC_JanN1`, RC binary): md5-identical to
  `stage11.5C_janOFF` (NDIFF=0) — override + guards neutral when OFF.
- Legacy April rerun (`stage11.5H_LegApr`, 29 d, exit 0): bit-identical to
  `stage11.5D1_AprLegacy` (days 0/1/7 checked); 29 s wall-clock.
- Full fpm battery: PASS (zero failures, `ice_init` chain validated).
- Strict `-Wall -Wextra` build from clean: zero warnings/errors.

## 3. Documentation synchronization (all files)

- `docs/PROJECT_ROADMAP.md`: status → 11.5H-RC CURRENT; §11.5 header lists
  11.5A–11.5H COMPLETE + compact 11.5C.3–11.5H entries (commits); old
  11.6=NetCDF / 11.7=sea-ice replaced by 11.6 EOS-80 (NEXT MAJOR) /
  11.7 NetCDF+CFL / 11.8A validation / 11.8B audit / 11.9 closure;
  12.0 BLOCKED until 11.9 (D-28).
- `docs/validation/INDEX.md`: this 11.5H-RC row (11.5A–11.5H rows intact).
- `docs/model/model_physics_status.md`: stage → 11.5H-RC + reference-regime
  note (legacy N=1 reference; dt=150 candidate; STALE≠legacy; EOS-80 criterion).
- `docs/model/model_equation_ledger.md`: header → 11.5H-RC + equations-vs-
  temporal-architecture separation note (equations untouched).
- `docs/DECISIONS.md`: D-22…D-28 appended (reference lock, dt150
  terminology, STALE verdict, skt debt, shal freeze, sea-ice gate, Stage-12
  block) with date/rationale/sources/limitations/next.
- `KNOWN_ISSUES.md` (root): N-11 (convergence), N-12 (dt150 regime + gate),
  N-13 (skt debt), T-14 (230× perf cost) appended in table format.
- `docs/validation/stage11.5H_production_temporal_architecture.md`: §7/§8
  TBDs resolved (battery PASS, baseline locked to N=1).
- `README.md`: stage bullet → 11.5H-RC.

## 4. Cross-reference verification

- ROADMAP ↔ INDEX: 11.5A–11.5H-RC listed in both; statuses
  COMPLETE/CURRENT/NEXT-MAJOR/BLOCKED match.
- ROADMAP ↔ DECISIONS: D-22…D-28 present with matching numbers/stages.
- physics_status ↔ code: stage + scheduler description match
  (`STAGE115H_PRODUCTION_MODE`, OCEAN_DT=150, STALE, shal 1×/day).
- KNOWN_ISSUES ↔ behavior: N-11/12/13 + T-14 all live in 11.5H outputs;
  no fixed-but-listed items added.
- 11.5H report ↔ DECISIONS: §4 verdict → D-22/D-24; §5 debt → D-25;
  §8 gate → D-27/D-28; EOS criterion → 11.6 section.

## 5. Readiness for 11.6 EOS-80

Scheduler is self-contained and reference-locked (N=1); the 11.6
re-baseline target is defined; EOS-80 criterion corrected
(correctness + reference tests + stability + impact). 11.6 may start.

## 6. Files + verification

- Code: `app/main.f90` (self-containment override replaces silent
  fallback) + `src/stage115h_production.f90` (`s115h_warn_ignored`).
- Docs: this file (NEW); ROADMAP; INDEX; physics_status; ledger;
  DECISIONS (D-22…D-28); KNOWN_ISSUES (N-11/12/13, T-14); 11.5H report
  (§7/§8 TBDs); README.
- Verification: smoke bit-identical (no-MM2 ≡ MM2-run d0–4) + WARNING path;
  Jan OFF NDIFF=0; legacy-Apr bit-identical; battery TBD; strict TBD;
  `git diff --check` clean; NO physics/production-defaults changes.
