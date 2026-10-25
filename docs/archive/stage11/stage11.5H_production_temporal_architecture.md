# Stage 11.5H — Production Temporal Architecture + Reference Regime Validation

Frozen (date). Production scheduler implementation + reference-regime
validation + forensic cleanup. No physics, EOS, CA threshold,
B200/B210/B280/shal/advs/advt/CA/EOS/ice equations, EN4/ERA5/grid/
coefficients changed; no guards/clamps; shal frozen (dt1=120/mm3=30
untouched); legacy default unchanged (OFF = bit-identical, Jan NDIFF=0).
No NetCDF migration (11.7), no EOS-80 switch (11.6), no skt closure
(scientific debt, §5). Stage 12 NOT started.

## 1. Production temporal architecture (as built)

- OCEAN_DT = 150 s (conservative reference; 225 s is the largest proven
  29-day stable dt per 11.5D.3 — NOT the reference; 150 s stays until a
  validation gate justifies otherwise).
- BAROTROPIC_DT = 120 s (shal internal microsteps, 30×120 = 3600 s, 1×/day).
- ICE_DT = 3600 s (ice/thermo/stress/redis cadence, per iii).
- OCEAN_ICE_COUPLING = STALE: ocean substeps see ice state (txic/tyic/ans)
  frozen at day-start values (all 24 fires); ice sees ocean at end of
  previous hour (never intermediate substep states — structural, both modes).
- One hour: ice update → thermodynamics → ice stress → redistribution →
  ocean 24×150 s (advs/advt → CA → B200 → B210 → B280 → W each pass),
  shal 1×/day.
- Switch: STAGE115H_PRODUCTION_MODE (default OFF). ON forces production
  config WITHOUT consulting STAGE115C/D/F/G env (parse block skipped,
  override sets nsub=24/ostep/dt_ocean=150/d2_npass=24/shal-once; requires
  mm2≥24 else legacy-config fallback with inert freeze).
- STALE freeze semantics = 11.5F F3, production-owned (`s115h_gate_entry`:
  snapshot substep-1 pre-tail, restore on later entries; T/S/CA/u2/v2 fresh).

## 2. Reference regime validation (April kill-d8; Jan in §7)

Method: d7 absolutes (comparable to 11.5E/11.5F tables) + d1→d7 drift
(d1 baseline excludes the d0→d1 init transient: −1.1% salt inventory
adjustment on first-day ice-ocean contact, identical all regimes).
CFL: no new run (s112 diag OFF in all runs) — analytic bounds from 11.2
(Cx=0.023/Cy=0.015/Cz=0.10/Cwave=0.66/f·DT=0.52 at dt=3600; dt=150 scales
advective numbers 24× DOWN) → all ≪1 in every regime here.

| Metric (April d7) | N=1 legacy (`AprLegacy`) | dt150 fresh (`dt150full`) | F3 115C1-freeze (`11.5F_F3`) | PROD-STALE 115H (`11.5H_ProdApr`) |
|---|---|---|---|---|
| Heat d7 | 4.3715e28 (−1.0%) | 3.4450e28 (−22%) | 3.4503e28 (−22%) | 3.4503e28, **md5-identical to F3 days 0–7** |
| Icevol d7 | 215.02 | 779.31 | 776.80 | 776.80 (bit-identical) |
| maxU / maxV | 0.532 / 0.578 | 0.283 / 0.330 | 0.283 / 0.330 | identical |
| EUU d7 | 7.5930e14 | 7.7105e14 | 7.7253e14 | 7.7253e14 (exact, incl. cols=6297135) |
| CA maxiter / nmix | 1001 / 4842287 | 1001 / overflow | 1001 / overflow | 1001 / overflow |
| Salt d1→d7 | −1.99e-04 | −1.27e-04 | −1.29e-04 | −1.29e-04 |
| NaN | 0 | 0 | 0 | 0 |

Notes: (i) kinetic energy does NOT diverge (all EUU within 2%) — the
regime change is thermodynamic (heat/ice), not momentum. (ii) CA guard
saturates (maxiter=1001) in ALL regimes incl. legacy — pre-existing
float32 quantization floor (10.21), not a regime signal. (iii) Salt
conservation O(1e-4) all regimes — no regime-dependent mass error.

## 3. Forensic machinery removal (from production path)

- All 71 `call s115c*`/`s115g_*` sites in `app/main.f90` guarded by
  `if (.not. s115h_prod_active())` (mechanical single-line-IF prefix,
  zero nesting risk, zero collisions — verified by grep).
- Forensic env parse block (11.5C/D) skipped on production path
  (wrapped); production config forced by override (only
  STAGE115H_PRODUCTION_MODE consulted).
- `s115h_gate_entry` (STALE freeze) is production-owned and unguarded.
- Modules stay in `src/` as forensic archive (reproducibility of
  11.5C–11.5G); unreachable from production graph when ON; fully
  executed when OFF (legacy bit-identical, Jan NDIFF=0).
- Full physical deletion deferred to 11.8 modular-ocean-core work.

## 4. Verdict: is dt=150 STALE closer to legacy or to fresh?

Decisively to FRESH: PROD-STALE is bit-identical to F3 and ≈ fresh
(heat −22% vs legacy −1%; ice 777 vs 215). STALE ice→ocean coupling —
the only freezable direction without freezing the ocean (11.5F §1
theorem) — does NOT recover legacy climate. The regime change lives in
ocean→ice freshness + ocean-internal cadence (11.5F closure, narrowed by
11.5G to {T/S-freshness?, CA-cadence?}). Consequence for the production
baseline: **legacy N=1 stays the reference regime**; dt=150 (+STALE or
fresh) is an experimental climate pending the mandatory sea-ice
validation gate (OSI-SAF/NSIDC, 11.5E). The 11.8 matrix therefore
baselines against N=1 legacy.

## 5. skt scientific debt (NOT solved here)

- Production legacy semantics: `skt` (`param.f90:139`) is not prognostic
  in production; `heat()` reads it (`thermodynamics.f90:117`) for fw;
  production never writes it (sole write = synthetic
  `test/cold_ice_snow_test.f90:123`) → skt ≡ 0 → **fw ≡ 0 in all
  production runs** (11.5G §1). Basal freeze/melt runs on conduction.
- Debt: a proper ice-ocean turbulent thermodynamic flux closure needs a
  prognostic skt equation + exchange formulation + validation — OUT OF
  SCOPE for Stage 11 (would re-open Stage-10 physics); deferred to a
  future stage (possibly Stage 12+). Documented, not implemented.

## 6. Performance benchmark

Method: script-epoch wall-clock (includes fpm startup; same for both).

- Legacy N=1 April (`stage11.5H_LegApr`, 29 d, exit 0): 29 s → **~1 s/sim-day**.
- PROD-STALE April (`stage11.5H_ProdApr`, kill d9): 2073 s / 9 d → **~230 s/sim-day** (≈230× legacy; 576 ocean passes/day vs 1).
- dt150-fresh cost ≡ prod (same pass count; freeze/restore overhead is
  3×is1×js1 copies/fire — negligible; /usr/bin/time peak-RSS unavailable —
  run was killed before `time -v` printed).
- Memory: identical footprint by construction (same grid/state; prod adds
  three is1×js1 snapshot arrays ≈ 170 KB) — not separately measured.
- I/O: same daily NetCDF outputs (identical file sets); per-day volume
  unchanged vs legacy.
- CPU fraction by operator: unavailable (no profiling hooks; honest
  boundary — candidate for 11.8 if needed).

## 7. Regression + battery

- Jan OFF (`stage11.5H_JanN1`, new guarded binary): md5-identical to
  `stage11.5C_janOFF` (NDIFF=0) — guards neutral when OFF.
- Jan prod-mode (`stage11.5H_JanProd`, STALE): stable-flat 8 outputs
  (maxU/V 0.24–0.48), 0 NaN, killed d8.
- Full fpm battery: PASS (zero failures). `git diff --check`: clean.

## 8. Implications for next stages

- 11.6 (EOS-80): correct criterion = physical correctness + reference
  tests + numerical stability + impact on model (NOT "improvement vs
  observations" — EOS-80 is a fundamental EOS, not a calibration closure).
  Re-baseline procedure per 11.5G §5.2 on the production scheduler.
- 11.7 (NetCDF + legacy removal + CFL): production scheduler is the
  migration target; CFL monitoring becomes permanent (11.2 analytic
  bounds + 11.5H empirical table as baseline).
- 11.8 (closure): validation matrix (30-day Jan/Apr/Jul/Oct) runs the
  production executable; reference regime LOCKED to legacy N=1 (§4 verdict:
  STALE does not rejoin legacy — the gate adjudicates between two climates).
- Sea-ice validation (OSI-SAF/NSIDC) is a MANDATORY production gate:
  legacy d7 ice 215 vs Family-B 779–2736 is a regime change (11.5E);
  §4 decides whether STALE rejoins legacy or the gate must adjudicate
  between two climates.

## 9. Files + verification

- Code: NEW `src/stage115h_production.f90` + `app/main.f90` (use/init/
  parse-wrap/override/entry/71 guards).
- Docs: this file (NEW); INDEX 11.5H row; ROADMAP (11.5G COMPLETE).
- Verification: Jan OFF NDIFF=0; prod-Apr md5-identical to F3 days 0–7;
  Jan prod stable-flat 8 outputs, 0 NaN; legacy-Apr rerun bit-identical to
  AprLegacy; full fpm battery PASS; `git diff --check` clean; NO physics/
  production-defaults changes.
