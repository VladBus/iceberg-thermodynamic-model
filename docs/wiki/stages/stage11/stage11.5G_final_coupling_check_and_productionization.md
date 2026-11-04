# Stage 11.5G — Final Coupling Mechanism Check (skz-freeze) + Productionization Specification

Frozen (date). FINAL freeze experiment + productionization specification.
No physics, EOS, CA threshold, B200/B210/B280/shal/advs/advt/CA/EOS/ice
equations, EN4/ERA5/grid/coefficients changed; no guards/clamps; shal
frozen (dt1=120/mm3=30 untouched); production defaults unchanged. Only
source change = NEW diagnostic module `src/stage115g_skzfreeze.f90` +
4 hook lines in `app/main.f90` (OFF = instant return, Jan bit-identical).
Stage 12 NOT started. After this stage: NO MORE freeze experiments.

## 1. skz/skt static audit (CORRECTS 11.5F §1/§5 one-letter misread)

Repo-wide word-boundary audit (excl. build/):
- `skz` (`param.f90:83`): written ONLY `main:1425` (B210 `rr(1)`); read by
  NO physics — only `stage115c1_trace.f90:211,263` diagnostics.
  → skz is WRITE-ONLY for physics. (The stale comment at `param.f90:83-84`
  "используется в heat() для fw" documents intent, not fact; left untouched.)
- `skt` (`param.f90:139`): read ONLY `thermodynamics.f90:117`
  (`fw = 1028·4186.8·skt·(T1−Tfr)/dz`); written NOWHERE in production
  (sole write = `test/cold_ice_snow_test.f90:123` synthetic TEST).
  → in production skt ≡ 0 → **fw ≡ 0 in ALL configs** (all stages, legacy
  and Family B). The turbulent ocean→ice flux channel is dead code-path
  in production; basal freeze/melt runs on the conduction term
  (`dhic = −dt/302e6·(fw − b·(tfr−tts))`, thermo:299-302) driven by FRESH T1.
- 11.5F §1/§5 "skz → heat fw" conflated skz with skt. Corrected here.
- Consequence: freezing skz is provably a physics no-op (restores values
  nothing reads). B150-SKZ doubles as empirical proof: expect bit-identity
  with dt150-fresh.

## 2. B150-SKZ experiment (STAGE115G_FREEZE_SKZ=true, dt=150, T/S/CA/txic fresh)

Run `stage11.5G_B150SKZ` (April MM2=24, INIT-OK, killed d8):

| Run | Heat d7 | Icevol d7 | Reading |
|---|---|---|---|
| N=1 legacy | −1.0% (4.3715e28) | 215 | baseline |
| dt150 fresh (`stage11.5D3_dt150full` d7, re-verified) | −22% (3.4450e28) | 779 | Family-B climate |
| dt150 + frozen txic/tyic/ans (11.5F F3) | −22% | 777 | ≡ fresh (ice→ocean ruled out) |
| B150-SKZ (dt150 + frozen skz) | −22% (3.4450e28) | 779.31 | BIT-IDENTICAL to fresh (md5 days 0–7) → skz carries NOTHING |

Run `stage11.5G_B150SKZ` (April MM2=24, `STAGE115G_FREEZE_SKZ=true`,
INIT-OK, killed d8, 0 NaN, maxU 0.283/maxV 0.330): day-7 outputs
md5-identical to `stage11.5D3_dt150full` days 0–7 (all 8 files);
icevol 779.31 vs 779.31, heat 3.4450e28 vs 3.4450e28 — exact match.

## 3. Interpretation: is skz the primary cause?

NO — proven twice, statically (§1: skz unread by physics) and empirically
(§2: B150-SKZ bit-identical to fresh). skz-entrainment drops out of the
11.5F residual set {skz-entrainment?, T/S-freshness?, CA-cadence?} →
residual = {T/S-freshness (u2/v2/T1/S1 24×/day into heat/ice-drag),
CA-cadence (24× redistribution before fluxes act)}. Note the dead-channel
corollary (§1): the turbulent ocean→ice flux fw ≡ 0 in production, so the
Family-B basal-freezing divergence runs on the conduction term with FRESH
T1 — consistent with T-freshness as the leading residual candidate, but
formally unisolated (separation requires freezing the ocean itself —
11.5F §1 theorem).

## 4. DECISION: stop freeze experiments, proceed to productionization

Regardless of §3 outcome: NO MORE freeze experiments after 11.5G
(mandate). Residual unisolated set {T/S-freshness?, CA-cadence?} CANNOT
be separated without freezing the ocean itself (11.5F §1 u1-rollover
theorem: any u2/v2/t2/s2 freeze propagates into the ocean in one pass) —
accepted as boundary. Resolution path = production architecture (11.5H
defines coupling cadence explicitly) + sea-ice validation gate (11.5E),
not more freezes.

## 5. Productionization specification

### 5.1 Stage 11.5H — Production temporal architecture

- Reference production ocean timestep: **dt=150 s** (largest fully
  validated stable dt is 225 s per 11.5D.3, but 225/150 unconverged
  climates (11.5E) → 150 s is the conservative reference; 225 s stays
  a candidate ONLY with validation-gate justification).
- Barotropic timestep: BAROTROPIC_DT = 120 s (legacy shal cadence
  preserved; shal() hardcoded dt1=120/mm3=30 untouched).
- Ice timestep: ICE_DT = 3600 s (legacy iii cadence preserved).
- Coupling timestep: OCEAN_ICE_COUPLING_DT = 3600 s option STALE
  (legacy N=1 semantics: ocean reads end-of-day ice, ice reads day-stale
  ocean) vs 150 s option RESPONSIVE (Family-B semantics) — 11.5H MUST
  implement the choice as an explicit named switch with documented
  semantics; default = STALE (legacy climate) until the sea-ice
  validation gate (11.5E) justifies RESPONSIVE.
- State vs diagnostic/flux split: prognostic = {u1/v1/u2/v2/t1/t2/s1/s2,
  ro, w, ym2, ice state, iceberg [x,y,u,v,L,W,H]}; diagnostic =
  {skz, rr, txic/tyic (recomputed per ice step), ans-derived a1};
  flux = {fw (≡0 pending skt decision), conduction, atmos fluxes}.
  skt disposition (write-only-test vs production-zero) MUST be decided
  in 11.5H: either wire B210→skt (physics change, needs stage + validation)
  or document fw≡0 as legacy semantics (keep, document).
- Temporal splitting diagram (per day): [iii=1..24: ice update (ICE_DT) →
  heat → redis → ice stress → adv2d → redis → W → GATE FIRE (ocean tail
  at dt=150: advs/advt → CA → B200 → B210 → B280, shal 1×/day) ] ×24.
- Remove ALL STAGE115* switches from the production path (115C/D/F/G
  modules stay in tree as forensic archive, unreachable by default);
  keep only production switches (EOS_MODE, ICEBERG_PRODUCTION, tides, etc.).

### 5.2 Stage 11.6 — EOS-80 productionization

- Criterion: if 11.4.1 validation shows EOS-80 improves physical realism
  vs observations → EOS_MODE=EOS80 becomes production default;
  if significant deviations → stays optional.
- Fallback: EOS_MODE=LEGACY_REFERENCE always available.
- Re-baseline procedure on switch: EN4 → EOS80 → density → thermal wind
  → B200 → B210 → B280 → ocean → ice coupling (full Stage 11 validation
  matrix re-run, 11.8).

### 5.3 Stage 11.7 — NetCDF migration + legacy removal + CFL monitoring

- NetCDF input architecture: grid.nc (replaces KOORD.DAT, hhh.bar),
  bathymetry.nc, ocean_initial.nc (replaces EN4 intermediate),
  forcing_era5.nc, seaice_initial.nc (replaces 1_1.ice…1_5.ice),
  tides.nc (replaces GRM2 or null tides).
- Legacy removal order (each AFTER its .nc validated bit-identical):
  KOORD.DAT → hhh.bar → 1_1.ice…1_5.ice → DAV4_5.98/FI1DL1.DAT (dead)
  → GRM2 (tides.nc or null).
- CFL monitoring becomes permanent production feature: record
  cfl_x/cfl_y/cfl_z/cfl_wave/cfl_coriolis/cfl_diffusion in NetCDF
  diagnostics; thresholds PASS/WARNING/FAIL; WARNING logs only (no stop).

### 5.4 Stage 11.8 — Stage 11 closure / release candidate

- Production validation matrix: 30-day Jan/Apr/Jul/Oct with the production
  executable; compare vs N=1 legacy baseline; conservation (salt/heat/
  volume); CFL monitoring active; no NaN/Inf.
- Stage 11 COMPLETE criteria:
  - Numerical: stable production dt, CFL monitoring, no NaN/Inf,
    reproducible, documented temporal splitting + operator cadence.
  - Physical: EOS-80 pathway decided (or justified legacy), documented
    density/thermal-wind, ocean heat/salt budgets, ice-ocean coupling
    semantics (STALE vs RESPONSIVE decided + validated).
  - Software: NetCDF I/O, legacy inputs removed, no STAGE115* in
    production path, forensic diagnostics out of production, modular
    ocean core.
  - Reproducibility: 30-day Jan/Apr/Jul/Oct, same executable + input contract.

### 5.5 Stage 12 prerequisites (entry gate, NOT started)

Stage 12 (voxel thermodynamics) may start ONLY after: Stage 11 COMPLETE
(all §5.4 criteria) + validated production ocean core + defined
ice-ocean interface semantics + active CFL monitoring + validated NetCDF
I/O + removed legacy inputs.

## 6. Files + verification

- Code: NEW `src/stage115g_skzfreeze.f90` + 4 hook lines in `app/main.f90`
  (use/init/entry/exit; OFF = instant return).
- Docs: this file (NEW); INDEX 11.5G row; ROADMAP (11.5F COMPLETE, 11.5G
  status, 11.5H→11.6→11.7→11.8→12 plan).
- Verification: Jan OFF (`stage11.5G_JanN1`) md5-identical to
  `stage11.5C_janOFF` across ALL outputs (new binary, NDIFF=0); JanDT150
  stable-flat, 0 NaN; B150-SKZ md5-identical to dt150-fresh days 0–7;
  full fpm battery PASS; `git diff --check` clean;
  NO physics/production-defaults changes.
