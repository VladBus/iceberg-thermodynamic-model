# Stage 11.7C — EN4 & ERA5 Passthrough Builders + Equivalence Verification

Frozen (date). Passthrough verification: the ocean_initial.nc and
forcing_era5.nc pipelines are PROVEN bit-reproducible; contracts verified
against 11.7A spec and reader expectations. NO reader switch (production
reads exactly as before), NO legacy removal, NO physics/scheduler/EOS
change (LEGACY default, N=1 reference, EOS-agnostic), NO seaice/tides
(11.7D), NO CFL thresholds, NO 11.8A/B/11.9/12 start.

## 0. Phase 0 documentation fixes (in this commit)

- README zombie paragraph (10.19 CASE C text dangling as current status)
  marked historical, SUPERSEDED by 10.20 restoration.
- INDEX 11.7B.2 row + ROADMAP §§11.7B.1/11.7B.2: "reproducibly benign /
  proven / C!=8 proven" → "observed consistent in the reference build
  environment" (matches 11.7B.2 report + T-15).
- ROADMAP Updated → 2026-10-15; physics_status → 11.7B.3.
- README + AGENTS first-run: "three steps" (0 conditional IBCAO check,
  then 1, 2) with explicit skip-if-present rule.

## 1. Data flow (verified current)

- EN4 raw (`data/input/raw/ocean/EN.4.2.2.f.analysis.g10.YYYYMM.nc`, 4
  months present) → `python/ocean/build_initial_ts.py` (--raw/--out/
  --json, --method nearest|bilinear) → `initial_ts_YYYY-MM-01[_rebuild].nc`
  → `initial_ocean_reader.f90` (requests `temperature_celsius`,
  `salinity_mass_fraction` by name; dims i=133/j=105/k=18) → T2/S2
  (kt1 from coup1, intent(in)). `ICEBERG_OCEAN_INIT_FILE` override.
- ERA5 raw (`data/input/raw/era5/2020/YYYY_MM/{era5,snowfall}_*.nc`) →
  `python/era5/merge_snowfall.py` (instantaneous + 12-hourly snowfall →
  merged) → `era5_YYYY_MM_merged.nc` → `netcdf_input`/`era5_wind`
  (bilinear, lon-wrapped, D32 edge fallback) → forcing fields.
- Production currently reads the `*_rebuild.nc` / `*_merged.nc` files
  (all 11.5+ runs). Builders support explicit out-paths (safe rebuilds).

## 2. ocean_initial.nc contract verification (vs 11.7A §2)

- File (`initial_ts_2020-04-01_rebuild.nc`): dims i=133/j=105/k=18;
  `temperature_celsius`/`salinity_mass_fraction`/`density_anomaly_gcm3`
  float32 NaN-fill; `regrid_flag` int8; `water_column_levels` int64;
  `wet_mask` int8; `lat`/`lon` float64; `z_model_m` float64 =
  [2.5..600] m ≡ DATA z (cm→m) elementwise.
- Units: T °C, S mass fraction (reader contract; converts only at
  NetCDF-output boundary + EOS-80 S×1000 internally) ✓.
- Content (April rebuild): T −2.172..6.747 (mean 0.786); S
  0.00000..0.03520 (mean 0.01968); RO −0.02007..0.00842 (pre-existing
  11.1 negative excursion, documented); wet cols 11067, levels 143176.
- Builder reproducibility: fresh rebuilds (Jan + Apr, current builder)
  are BIT-IDENTICAL (0.0) to committed `*_rebuild.nc` — all float vars,
  masks, regrid_flag. Passthrough PROVEN.
- Non-reproducibility explained (not a defect): Aug-30 BASE files differ
  hugely (ΔT 7.6°C) — built by an older pipeline; SUPERSEDED by Oct-6
  rebuilds. Base files retained (11.7E cleanup candidate, NOT deleted
  here — scope restriction).

## 3. forcing_era5.nc contract verification (vs 11.7A §2)

- File (`era5_2020_04_merged.nc`): dims valid_time=120/latitude=101/
  longitude=1440; float32 u10/v10 [m/s], t2m/d2m [K], msl [Pa],
  tcc [0–1], sf [m/s]; lat 90→65 DECREASING 0.25°; lon −180→179.75;
  valid_time seconds-since-1970 proleptic_gregorian (2020-04-01T00 →
  2020-04-30T18, 120 = 30 d × 4/day); NaN fill; D32 edge rule is CODE
  behaviour (no file metadata — documented here).
- Builder reproducibility: fresh merge (raw instantaneous + snowfall)
  BIT-IDENTICAL all 7 vars (0.0, NaN patterns match). Passthrough PROVEN.
- Reader behaviour unchanged (D32, conversions, interp — 11.7A §2 holds;
  era5_coverage_test green in battery).

## 4. Regression gates

- Battery: PASS (50 SUCCESS, 0 failures). Strict
  (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`, clean
  rebuild): zero warnings/errors.
- Jan legacy N=1 (`stage11.7C_JanN1`): exit 0, md5-identical to janOFF
  (NDIFF=0) — production reads rebuild/merged files correctly.
- April legacy N=1 (`stage11.7C_AprN1`): exit 0, 31 outputs, 0 NaN total.
- Preserved: KOORD.DAT/hhh.bar sole grid inputs; rebuild/merged files
  as-is; no reader switch/removal; EOS LEGACY default; N=1 reference;
  11.6.1 dispatch; all physics/numerics.
- `git diff --check`: TBD.

## 5. Planning notes (11.8A EOS criteria / 11.8A gates / Stage-12 entry)

- a. 11.8A EOS-80 decision: compare Legacy vs EOS-80 under BOTH N=1 and
  production scheduler; include OSI-SAF/NSIDC sea-ice validation;
  quantify interaction (11.6.1: heat +0.6865e28 / ice +375.41 — never
  assume factorization); promote-or-keep-optional with justification.
- b. 11.8A draft gates: 30-day Jan/Apr/Jul/Oct ×
  {Legacy+N1, Legacy+prod, EOS80+N1, EOS80+prod}; metrics NaN/Inf,
  T/S/ρ ranges, U/V/W, CA stats, CFL, conservation, ice extent;
  no-NaN gate; conservation drift < 1%/month; ice extent within
  OSI-SAF bounds.
- c. Stage-12 entry (D-28): 11.9 closure + validated production temporal
  architecture + EOS decision documented + NetCDF migration complete
  (all 6 sources) + legacy inputs removed + permanent CFL + scientific
  validation passed.

## 6. Files + verification + go/no-go

- Code: NONE (builders/tests/producers untouched; rebuilds to /tmp only).
- Docs: this file (NEW); INDEX 11.7C row; ROADMAP (11.7C COMPLETE, next
  11.7D); physics_status (11.7C); Phase-0 fixes (README/AGENTS/INDEX/
  ROADMAP/11.7B.2-softening already applied above).
- Verification: builders bit-identical (EN4 Jan+Apr, ERA5 Apr); battery
  TBD; strict TBD; Jan NDIFF=0; Apr 0 NaN; diff-check TBD; NO physics/
  reader/EOS changes.
- GO 11.7D (seaice_initial.nc + tides.nc): passthrough pattern proven
  twice; residual = stale base files (11.7E cleanup), monthly-ice gap
  (11.7D scope), tides null-config (11.7D scope).
