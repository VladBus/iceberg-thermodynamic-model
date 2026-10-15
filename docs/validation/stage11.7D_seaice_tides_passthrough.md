# Stage 11.7D — Sea-Ice & Tides Passthrough Builders + Equivalence Verification

Frozen 2026-10-15. Passthrough verification: the seaice_initial.nc and
tides.nc pipelines are PROVEN bit-reproducible; contracts verified
against 11.7A spec and reader expectations. NO reader switch (production
reads exactly as before), NO legacy removal, NO physics/scheduler/EOS
change (LEGACY default, N=1 reference, EOS-agnostic), NO ocean/forcing
migration (11.7C done), NO 11.7E/11.7F/11.8A/B/11.9/12 start.

## 0. Phase 0 documentation fixes (in this commit)

- 11.7C report TBDs filled: Frozen 2026-10-15; battery 50 SUCCESS/0
  failures; strict clean (-Wall -Wextra -fcheck=all -ffpe-trap);
  diff-check clean; git diff --check clean.
- README.md: current stage → 11.7C COMPLETE; next = 11.7D.
- docs/model/model_physics_status.md: Date → 2026-10-15; stage → 11.7C.
- RO minimum −20.07 g/cm³ in KNOWN_ISSUES.md marked HISTORICAL
  (Stage 11.1 unit error, corrected in 11.1); current verified
  minimum RO anomaly −0.02007 (ρ ≈ 999.93 kg/m³).
- EN4 file usage clarified in 11.7C report: default reader path is
  `initial_ts_2020-01-01.nc`; rebuild files used via
  `ICEBERG_OCEAN_INIT_FILE=*rebuild.nc` override (all 11.5+ runs).
- ROADMAP date updated to 2026-10-15.

## 1. Roadmap supplement: 11.7D–F + 11.8A matrix

Added to PROJECT_ROADMAP.md:

- **11.7D — Sea-Ice & Tides Passthrough (THIS STAGE)**: builders +
  equivalence tests; legacy 1_*.ice / null-tides stay production inputs.
- **11.7E — Production Reader Switch**: switch Fortran readers to
  NetCDF; A/B comparison; rollback via env var.
- **11.7F — Legacy Removal + Permanent CFL**: remove legacy inputs;
  add CFL monitoring; only after 11.7E validation.
- **11.8A Configuration Matrix** (for EOS-80 decision D-29):
  - Configurations: Legacy×N1, Legacy×Prod, EOS80×N1, EOS80×Prod
  - Seasons: Jan, Apr, Jul, Oct (30 d each)
  - Metrics: NaN/Inf, T/S/ρ, U/V/W, CA, CFL, conservation, ice extent
  - Gates: no NaN/Inf; drift < 1%/mo; OSI-SAF/NSIDC ice bounds
  - Decision D-29: promote EOS-80 to default OR keep optional

## 2. seaice_initial.nc contract verification

- **Source**: 1_1.ice … 1_5.ice (legacy text, 133×105, categories 1..5)
  - Format: list-directed, 9.99→0, ≥1→1 clamp, Σ≤1 normalization
  - HST (category thicknesses): [0.20, 0.40, 0.95, 1.60, 2.50] m
  - HMAX boundaries: [0.3, 0.7, 1.2, 2.0, 50.0] m
  - Read by app/main.f90:506–541 (an1 → wice1 = HST×an1 → redis)
- **NetCDF contract (seaice_initial.nc)**:
  - dims: cat(5) × j(105) × i(133) ≡ cat×y×x (model indices)
  - vars: sic (cat,j,i) f4; sit (cat,j,i) f4; snow_depth (cat,j,i) f4
  - attrs: hst f8 (5), hmax f8 (5); CF-1.10; provenance attrs
  - dims renamed x,y,z → cat,j,i (Option A, model indices)
- **Builder**: python/ice/build_seaice_nc.py
  - Reads 1_1..1_5.ice from data/input/generated/real_grid/
  - Transposes to (cat,j,i) for NetCDF (cat,j,i order)
  - Replicates legacy processing: 9.99→0, ≥1→1 clamp, Σ≤1
  - wice1 = HST × an1; redis() conservative redistribution
- **Equivalence test** (python/tests/test_seaice_tides_nc.py):
  - Independent reference (separate Python loops, no shared code)
  - sic/sit bit-exact (0 mismatches); HST/HMAX exact
  - snow_depth all zeros (no snow data yet)
  - Wet columns: 11067 (matches legacy product); ice levels: 143176 (April)
  - NOTE: Only January data exists; other months reuse Jan init (known gap)
- **Known limitation**: January data reused for all months (gap
  documented in 11.7A; future work = seasonal sea-ice obs)

## 3. tides.nc contract verification

- **Source**: GRM2/GRS2/GRK1/GRO1 files ABSENT → production uses
  null-tides (amp=0, faz=0). qq constants: M2=28.9841042, S2=30.0,
  K1=15.041069, O1=13.943036 °/h (src/tide_forcing.f90:30-33).
- **NetCDF contract (tides.nc)**:
  - dims: const(4) × j(105) × i(133)
  - vars: constituent_name S1(4); qq f8(4) [°/h]; amplitude f4(j,i)
    [m]; phase f4(j,i) [rad]; qq_rad_per_step f8(4) [rad/step]
  - attrs: tidal_status="null-tides (GRM2/GRS2/GRK1/GRO1 data unavailable)";
    tidal_constituents="M2, S2, K1, O1"; source_grm2="missing"
- **Builder**: python/tides/build_tides_nc.py
  - Creates tides.nc with zero amplitudes/phases, correct qq
  - qq_rad_per_step = qq × dt1/3600/57.2958 (dt1=120s)
- **Equivalence test** (python/tests/test_seaice_tides_nc.py):
  - amplitude/phase all zeros (bit-exact)
  - qq exact match to 4 constants; qq_rad_per_step exact (1e-12 tol)
  - tidal_status attribute verified
  - qq_rad_per_step = qq × dt1/3600/57.2958 (dt1=120s)
- **Null-tides contract**: explicitly represents current production state
  (GRM2 data missing). Future: replace with TPXO/FES data when available.

## 4. Regression gates

- **Full fpm battery**: PASS (50 SUCCESS, 0 failures).
- **Strict build**: `fpm build --flag "-I/usr/include -Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow"` → clean (0 warnings).
- **January NDIFF=0** (stage11.7D_JanN1): md5-identical to janOFF (32/32 files).
- **April N=1** (stage11.7D_AprN1): 31 days, 0 NaN across all fields.
- **Equivalence tests**: 20/20 PASS (seaice 17 + tides 3).
- **Strict build**: clean (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow` from clean rebuild).
- **January NDIFF=0**: md5-identical to janOFF (legacy-preservation only, NOT reader-equivalence).
- `git diff --check`: clean.

## 5. Planning notes (11.7E/11.7F/11.8A/Stage-12)

- **11.7E — Production Reader Switch**: switch Fortran readers to
  NetCDF; A/B comparison via env var; rollback via legacy path.
- **11.7F — Legacy Removal + CFL**: remove legacy inputs; add CFL
  monitoring; after 11.7E validation.
- **11.8A EOS-80 decision matrix** (D-29):
  - Configs: Legacy×N1, Legacy×Prod, EOS80×N1, EOS80×Prod
  - Seasons: Jan, Apr, Jul, Oct (30 d each)
  - Metrics: NaN/Inf, T/S/ρ, U/V/W, CA, CFL, conservation, ice extent
  - Gates: no NaN/Inf; drift <1%/mo; OSI-SAF/NSIDC ice bounds
  - Decision D-29: promote EOS-80 to default OR keep optional
- **Stage 12 entry (D-28)**: 11.9 closure + validated prod scheduler +
  EOS decision + NetCDF complete + legacy removed + CFL monitoring +
  scientific validation passed.

## 6. Files + Verification + GO/NO-GO

- **New code** (4 files): python/ice/build_seaice_nc.py,
  python/tides/build_tides_nc.py, python/ice/build_seaice_nc.py
  (already existed, updated), python/tides/build_tides_nc.py,
  python/tests/test_seaice_tides_nc.py
- **Docs**: NEW stage11.7D_seaice_tides_passthrough.md; INDEX +11.7D;
  ROADMAP (§11.7D/11.7E/11.7F/11.8A matrix); physics_status (11.7D);
  KNOWN_ISSUES (RO −20.07 historical note added).
- **Verification**: equivalence 20/20 PASS; battery 50/0; strict clean;
  Jan NDIFF=0; Apr 31d/0 NaN; diff-check clean; NO physics changes.
- **GO 11.7E**: contracts closed; residual = 1_*.ice monthly gap
  (January-only), future seasonal sea-ice obs needed; tides null-config
  explicit; GRM2 acquisition path documented.

**GO 11.7E (Production Reader Switch)**.

**NO physics, NO reader switch, NO legacy removal, NO EOS change, NO Stage 12.**