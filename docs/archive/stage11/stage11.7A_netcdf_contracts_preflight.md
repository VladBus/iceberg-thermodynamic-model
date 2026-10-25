# Stage 11.7A — NetCDF Input Contracts & Migration Preflight

Frozen (date). READ-ONLY audit + explicit testable migration contracts.
NO source migrated, NO legacy input removed/renamed, NO production-path
or default-EOS change, NO scheduler/physics change, NO 11.8A/11.8B/11.9/12
start, NO data/report deletion, legacy EOS retained. Only changes in this
stage: this doc + ROADMAP/INDEX/status wording (11.6/11.6.1 structure,
dates, EOS-status sentence). 11.3B (`stage11.3B_input_architecture_audit.md`)
is the design skeleton; below VERIFIES it against current source (post-11.6.1)
and adds field-level contracts + equivalence plan + CFL design.

## 0. EOS status (binding, EOS-agnostic migration)

"EOS-80 implemented and validated as OPTIONAL; legacy Eckart remains
DEFAULT and scientific reference; default decision deferred to Stage
11.8A observational validation; legacy EOS is retained permanently as
regression baseline and is NOT scheduled for removal."
Migration must work IDENTICALLY under EOS_MODE=LEGACY and EOS_MODE=EOS80
(all equivalence runs are duplicated per EOS; no EOS transition implied).

## 1. Input dependency graph (production, verified at source)

grid (KOORD.DAT/hhh.bar → coup1/ikuv) → masks (kt1/kt1-land, hu/hv, map1)
→ ice state (1_*.ice → an1 → wice1 → redis) + ocean state (EN4 .nc →
t1o/s1o → T/S, else synthetic init_ocean) → forcing (ERA5 .nc →
era5_wind per iii; GRM2→amp/faz else zeros + datte) → thermal wind
(init_thermal_wind on ro[]) → day-00 NetCDF → time loop.
Order spine (main.f90): CLI/dirs → calendar → c1–c17 → GRM2+datte
(432–460) → coup1/ikuv → DAV4 dead read → ice files+normalize+redis
(506–541) → init_ocean (synthetic, superseded) → CA/EOS/B200/CFL
switches incl. eos80_configure (577, before first eos_diag) → ERA5
open + era5_wind → init_thermal_wind (721, consumes ro[]) → day-00
output → loop. Init sequence matches 11.3B §2 (line numbers drifted).

## 2. Source inventory (grounded; Q = open question for 11.7B)

### grid.nc ← KOORD.DAT + hhh.bar (live; FATAL branches)
- Consumer: `grid_coupling.f90:coup1()` + `ikuv`; KOORD block :470–508.
- KOORD.DAT: list-directed, 2 records: full `fi` then `dl`, real(4),
  (is1,js1)=(133,105); missing + grid_mode_real → `stop` (FATAL);
  grid_mode_test → synthetic FI/DL (TEST ONLY, explicit WARNING).
  Q1: FI/DL semantic assignment (lat/lon?) + units (degrees?) — verify
  against `python/grid/build_real_grid_inputs.py` writer before contract.
- hhh.bar: 7 blocks × 15 cols, `(15I5)`, (133,105) ints = KT1 encoder
  (:29–30, :50–64): 8=land; 3..600 = depth index (×100 → cm; 600=600 m);
  missing → synthetic-basin fallback + NOTICE (test-only).
  ht/map1 ladder: kt1 → ht (:92–122; 8888.0 land, epsilon
  `abs(x-8888)<1e-8` at every comparison; note :122 `888800.0` = 8888×100
  scale in ht units) → map1 mean depth → HHT in B200/210/280.
  Q2: exact kt1→ht→map1 unit ladder per branch (11.7B must transcribe,
  not reinterpret).
- Orientation: X↔j↔u, Y↔i↔v, Y inverted (north j=1); DX=DY=1389000 cm
  (IBCAO Polar Stereographic; EPSG:3996 per AGENTS.md).
- Vertical (HIGHEST-RISK note): `param.f90:304–313` DATA z =
  250,500,1000,1500,2000,2500,3000,4000,5000,7500,10000,15000,20000,
  25000,30000,40000,50000,60000 [cm], 18 centers surface→bottom
  (k=1 top, k=18 bottom); dz(1)=z(1), dz(k)=z(k)−z(k−1); dz1 half-levels
  (:290–313); kt1(i,j) = wet level count (0=land); loops k=1..kt1.
  Contract MUST encode: k-index ↑ = depth ↑, centers (not edges),
  dz/dz1 DERIVED (never stored), kt1 authoritative wet count.

### bathymetry.nc ← hhh.bar depth content (same reader as grid)
- Same KT1 encoding; bathymetry.nc carries depth-mean field + provenance
  (IBCAO source); land = 8888.0 convention preserved in contract attrs.
- Split from grid.nc per 11.3B §3.1/contract (coords+masks vs depths).

### ocean_initial.nc ← EN4 pipeline (live; axis-order-independent reader)
- Producer: `python/ocean/build_initial_ts.py` (EN.4.2.2 analysis →
  `data/input/processed/ocean/initial_ts_YYYY-MM-01.nc`; Z_M canonical
  metre depths; model-z↔EN4-z regrid; residual: small finite negative-ro
  excursions, D23 cause-REJECTED).
- File (verified `initial_ts_2020-04-01.nc`): dims i=133/j=105/k=18;
  `temperature_celsius`, `salinity_mass_fraction`, `density_anomaly_gcm3`
  float32 _FillValue=NaN; `regrid_flag` int8; `water_column_levels` int64;
  `wet_mask` int8; `lat`/`lon` float64; `z_model_m` float64; k/i/j coord vars.
- Consumer: `initial_ocean_reader.f90:99–148` (`temperature_celsius`,
  `salinity_mass_fraction` by name via get_var; range-guard
  T∈[−10,40]/S∈[−0.002,0.1]; land/bottom = 0.0 NEVER NaN; `wet_mask`);
  `ICEBERG_OCEAN_INIT_FILE` override; synthetic fallback on failure.
- Units: T °C, S mass fraction 0.033–0.035 (NOT PSU — converts only at
  NetCDF-output boundary + EOS-80 S×1000 internally).
- Vertical: file k ↔ model k 1:1 (same 18, z_model_m documents depths);
  contract MUST assert z_model_m ≡ DATA z (cm→m) elementwise.
- **Amendment (Stage 11.7E.2):** the shipped products `initial_ts_2020-01-01.nc` (Aug 30) and `initial_ts_2020-04-01.nc` (Sep 25) carry a bilinear-producer signature: `z_model_m` = [2.5,5,7.5,12.5,17.5,25,40,50,62.5,75,100,125,175,225,275,350,450,550] (NOT `DATA z`/100). The Jan shipped file also has 52,164 nonzero dry cells. Per `docs/validation/stage11.4_en4_stabilization.md` §11: "shipped products stay untouched and valid"; the reader never reads `z_model_m`/`wet_mask` → runtime contract unaffected. The rebuild products (`*_rebuild.nc`, Oct 6) satisfy the STRICT contract (`z_model_m` = `DATA z`/100 = [2.5,5,10,15,20,25,30,40,50,75,100,150,200,250,300,400,500,600]; dry cells == 0). The default `realistic_ocean_file` points at the stale shipped Jan product — documented as valid, no production default change.

### forcing_era5.nc ← merged ERA5 (live; D32 fallback)
- Producer: `download_era5.py` + `merge_snowfall.py` (+ `check_era5.py`).
- File (verified `era5_2020_04_merged.nc`): dims valid_time=120 /
  latitude=101 / longitude=1440; float32 u10/v10 [m/s], t2m/d2m [K],
  msl [Pa], tcc [0–1], sf [m/s, merged snowfall]; lat 90→65 DECREASING
  0.25°, lon −180→179.75; valid_time seconds-since-1970
  proleptic_gregorian; _FillValue NaN (all vars).
- Consumer: `netcdf_input.f90` + `era5_wind` (`wind_forcing.f90`):
  bilinear (`era5_bilinear2d`), lon wrapped ±180°, lat NOT wrapped
  (out-of-range → ok=false); daily slice + per-iii linear wind interp;
  coverage: monthly from 65°N (Jan fullcov 63°N); 55 cells lat<65° →
  nearest-edge D32 (only u10 ok checked); conversions u/v×100→cm/s,
  msl×0.01→hPa, t2m−273.15→°C, Tetens humidity, sf/43200 accumulation,
  Cd0=1.1/Cd1=0.04 stress, spd>1e-6 guard; land post-mask 1.70141e38;
  no NaN fill in chain.
- Time: daily slices mapped to model days (calendar semantics:
  day_d = start+d days); forcing gaps → D32 edge rule (documented).
- Contract: (time,y,x) float32, CF units, lat-decreasing order PRESERVED
  (reader indexes it directly — do NOT silently re-sort).

### seaice_initial.nc ← 1_1..1_5.ice (live; January-only gap)
- Consumer: `main.f90:506–541`: `1_1..1_5.ice` CWD (symlink/copy of
  `data/input/generated/real_grid/ice_2020-01-01/`), text, per-i records
  of (an1(i,j,k), j=1..js1); 9.99→0, ≥1→1 clamp; sas-normalize
  (Σ≤1, empty→open-water); wice1 = H·an (H = 0.20/0.40/0.95/1.60/2.50 m
  hardcoded); snow init 0; `redis()` conservative redistribution.
  Q3: init H(2)=0.40 vs `param.f90` hst(2)=0.5 — transcribe AS-IS (0.40),
  flag discrepancy for a physics stage (NOT 11.7).
- Producer: `build_real_grid_inputs.py` (OSI-SAF CDR SIC + C3S CS2SMOS
  SIT 2020-01-01 → sic/sit/category files). Gap: January state reused
  ALL months (D30/D31 freezing-regime artifact) — contract is MONTHLY
  (category(5)/y/x + SIC/SIT + snow[5]), backfilled Jan initially.
- After migration legacy files remain EXPORTABLE (transition path).

### tides.nc ← GRM2 family (MISSING → null-tides production reality)
- Consumer: `main.f90:432–460`: GRM2 = 3 blocks (amp1/faz1[133],
  amp2/faz2[105], amp3/faz3[133]) list-directed; constituents
  M2/S2/K1/O1 qq = 28.9841042/30.0/15.041069/13.943036 °/h; `datte()`
  astronomical args; q scaled by dt1. Missing → zeros + WARNING
  (NOT fatal) → tides NULL in all production runs to date.
- Contract: tides.nc dims constituent(4)/y/x (amp+phase) AND an explicit
  null-tides representation (all-zero + `tides_provided=false` provenance
  flag) — the CURRENT production state must be encodable, not just the
  future acquired-DB state (11.3D decision still open).

## 3. Migration matrix (one row/source; acceptance per source)

| Source | Compares | Tolerance | Regression set | Still-legacy-after |
|---|---|---|---|---|
| grid.nc | FI/DL/lon/lat/masks/kt1 elementwise exact (int exact; float bit-identical f32) | 0 (same values, new container) | Jan OFF vs janOFF (NDIFF=0) + coup1 mask counts (143422 wet / 11067 cols anchors) | KOORD.DAT/hhh.bar export kept until 11.7-closeout |
| bathymetry.nc | depth-mean field exact vs map1 | 0 | same as grid.nc | hhh.bar (shared file — retires with grid.nc) |
| ocean_initial.nc | T/S arrays DECODED-VALUE equal (not MD5 — re-encoding allowed) | ≤1 f32-ulp per value vs current product (same float32 payload expected → 0) | ocean_init_test (dims/cell-count/finite/land-zero) + Jan OFF | EN4 raw + builder scripts retained (provenance) |
| forcing_era5.nc | decoded u10…sf equal per slice | 0 (same float32 payload) | era5_coverage_test (100% cells) + 1-day forced run diag-identical | merged-ERA5 pipeline retained |
| seaice_initial.nc | an1/wice1 post-normalize equal | 0 (fractions/thickness exact; H table AS-IS incl. 0.40) | ice_init_test (Σ≤1, redis invariants) + Jan OFF | 1_*.ice export path kept in transition |
| tides.nc | null-config: amp/faz zeros + flag; future DB: values exact | 0 | GRM2-missing WARNING path preserved + tidal-zeros run identical | GRM2-absent handling stays until DB acquired |

Checksum policy: MD5 ONLY for byte-identical files (legacy↔legacy,
regression outputs). Transformed/re-encoded data: compare DECODED VALUES
+ semantic metadata (dims, units, order, _FillValue, provenance); NetCDF
encoding differences NEVER fail a gate. Model-level controls after ALL
migrations: Jan OFF ≡ janOFF (NDIFF=0) BOTH EOS modes; April A-config ≡
AprLegacy; full battery; strict build; `git diff --check`.
Scientific constraints preserved: EOS_MODE default LEGACY; legacy+N1
reference; temporal defaults; 11.6.1 dispatch + tests intact; CA/B-blocks/
shal/skt/melt/thermo untouched.

## 4. Test coverage (existing → missing)

- EXISTS: `era5_coverage_test` (100% forcing cells, real reader channel);
  `ocean_init_test` (dims/cell-count/finite/land-zero); `ice_init_test`
  (fractions/redis invariants); `iceberg_test_era5_interp` (interp unit).
- MISSING (11.7B must add): per-source reader-equivalence tests
  (.nc-reader vs legacy-reader on same product, per §3 tolerances);
  grid.nc mask/count anchor test (143422/11067); monthly-ice test
  (backfill-Jan + one synthetic non-Jan month); tides null-config test
  (zeros + flag → identical run); EOS-duplicated equivalence (every
  reader test runs LEGACY and EOS80 — migration is EOS-agnostic).

## 5. Permanent CFL design (audit of `stage112_cfl_diagnostics.f90`)

Formulas (all CGS, dimensionless; env-gated `STAGE112_CFL_DIAG`, maxima +
`cfl_distribution.csv` percentiles; first-invalid event tracking separate):
- cfl_x = |u2|·dt/dx, cfl_y = |v2|·dt/dx (dx=1389000), ch = cx+cy
  (`s112_compute_advection_cfl`:137).
- cfl_z = |w|·dt/dz(k) (`s112_compute_vertical_cfl`:199).
- cfl_wave = √(g·H)·dt1/dx, g=981 (`s112_compute_barotropic_cfl`:241).
- cfl_coriolis = f·dt, stability requires < 2 for semi-implicit
  (`s112_compute_coriolis_cfl`:278, comment).
- cfl_diffusion: horizontal Kh·dt/dx², Kh=7.5e6 (explicit FCT part);
  vertical rr(k)·dt/dz² DIAGNOSTIC-ONLY (Thomas implicit — NOT a CFL)
  (`s112_compute_diffusion_stability`:313).
- Cadence: per-operator call sites (dt = operator dt actually used:
  dt_ocean on substepped path, dt1 for barotropic); NO single daily max —
  report per-site maxima + distribution percentiles.
- Thresholds: NO PASS/WARNING/FAIL exists in code. Event-only bounds
  under FIRST_INVALID tracking (cx/cy>10, ch>20, cz>1, cwave>1) are
  blowup detectors, NOT production gates. → ALL production thresholds
  TBD. Evidence required: 11.2 measured values (Cx=0.023/Cy=0.015/Cz=0.10/
  Cwave=0.66/f·DT=0.52 at dt=3600) + 11.8A matrix distributions per
  scheduler×EOS cell → thresholds set in 11.8B, NOT invented in 11.7A.
- Non-finite/unavailable: NO explicit guard found in s112 (relies on
  first-invalid tracking) — Q4: 11.7B must define NaN-propagation rule
  (skip+count vs abort) before making CFL permanent.
- NetCDF diagnostic contract (design, not yet built): per-run variables
  cfl_x/cfl_y/cfl_z/cfl_wave/cfl_coriolis/cfl_diffusion_h (+v diagnostic),
  attrs (formula, dt_used, aggregation=per-site-max + P50/P95/P99,
  threshold refs TBD) — WARNING logs only, never stops the model.

## 6. Staged sequence for 11.7B onward (proposal)

11.7B: builders grid.nc + bathymetry.nc (from builders' products) →
reader-equivalence tests → Jan OFF gate. 11.7C: ocean_initial.nc +
forcing_era5.nc passthrough builders → equivalence + coverage gates.
11.7D: seaice_initial.nc (monthly contract, Jan backfill) + tides.nc
null-config → equivalence gates. 11.7E: legacy-path detachment (dual-read
with .nc primary, legacy fallback) → full matrix → legacy removal
per 11.3B §5 priorities. 11.7F: permanent CFL (thresholds from 11.8A
evidence feed 11.8B). Each sub-stage: builders → tests → OFF gate →
commit. Rollback per source: keep legacy reader + export until that
source's closeout gate passes (criterion §3 + Jan OFF NDIFF=0 both EOS).

## 7. Risks + rollback criteria

- R1 vertical-convention mismatch (centers vs edges, k-direction, dz
  derived-vs-stored): contract §2-vertical is explicit; any deviation =
  STOP the sub-stage, do not "adjust" physics to fit.
- R2 silent re-sort/transpose (lat-decreasing ERA5, (i,j)↔(133,105)
  direct mapping, FI/DL order): equivalence tests compare INDEXED values,
  not statistics.
- R3 Q1–Q4 unresolved (FI/DL semantics, kt1→ht ladder, H(2) 0.40vs0.5,
  CFL NaN rule): 11.7B resolves BEFORE building; no contract ships with
  open Q in its own source row.
- R4 encoding drift mistaken for data change: checksum policy (§3) —
  MD5 only byte-identical; values+metadata otherwise.
- Rollback: any gate failure → legacy path remains primary for that
  source; .nc demoted to artifact; stage continues with other sources.

## 8. EOS statement (restated, binding)

Migration is EOS-agnostic; legacy Eckart remains DEFAULT and scientific
reference; no EOS transition is implied by any 11.7 work; every
equivalence gate runs under BOTH EOS_MODE values; legacy EOS retained
permanently as regression baseline, NOT scheduled for removal.
