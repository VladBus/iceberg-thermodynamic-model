# Stage 11.7B — Grid & Bathymetry NetCDF Builders + Equivalence

Frozen (date). First controlled migration: grid.nc + bathymetry.nc BUILT
and equivalence-tested. NO reader migration (KOORD.DAT/hhh.bar stay
production inputs), NO legacy removal/rename, NO physics/scheduler/EOS
change (LEGACY default untouched, migration EOS-agnostic per §8),
NO other sources (ocean/forcing/ice/tides stay — later substages),
NO CFL thresholds, NO 11.8A/B/11.9/12 start, NO H(2) physics fix.

## 0. Preflight + documentation corrections

- Base `5ac01ef`, clean tree, main, no strays. AGENTS/RULES/issues/
  roadmap/decisions/physics/11.3B/11.7A read.
- ROADMAP EOS-80-default contradiction FIXED: the §11.6 "On pass:
  EOS_MODE=EOS80 becomes production default" line is STRUCK and marked
  SUPERSEDED by binding D-29 (EOS-80 OPTIONAL, legacy DEFAULT +
  reference, decision deferred to 11.8A, legacy retained permanently).
- Test-count clarified: 11.7A §4 "4 existing" = 3 input-reader tests
  (era5_coverage, ocean_init, ice_init) + 1 interpolation unit test
  (iceberg_test_era5_interp). "5 missing" stands (4 reader-equivalence
  incl. this stage's grid/bathy — now DONE — + EOS-duplication rule).
- Q1 RESOLVED at source (`build_real_grid_inputs.py:119-120,144-145`
  + round-trip check :310-328): FI=latitude °N, DL=longitude °E,
  Fortran column-major flatten, float32, 4-decimal text. Confirmed by
  the equivalence test below (not by assertion). Q1 closed.

## 1. Contract resolution (code-traced, no reinterpretation)

- Conversion chain (producer → consumer): IBCAO depth float32 m
  (NaN=land) → round → clip[3,600] int metres (KT1 codes, 8=land;
  `build_real_grid_inputs.py:196-201`, LAND_CODE=8, MIN/MAX 3/600) →
  coup1: ht=real(kt1); forced-land borders (i=1..15@j=94 1-indexed,
  j=1/js1 rows, i=1 col — the i=is1 col is NOT forced, stays wet:
  verified, 101 cells); kt1==8→8888.0; land cycles mod loop; wet
  5<HT≤10→10 (+T/S L3 copy), HT≤3→3, ×100→cm → ht[cm].
- Q2 RESOLVED: authoritative kt1 = SECOND pass (:317-329): 0 default,
  land (8888.0, eps 1e-8) stays 0, wet max{k: z(k)≤HT}. The :117
  first-pass + :238 kk1-01 gate test first-pass COUNTS (land=10), so
  :238 skips map1 for neighbours of count-8 (40–49 m) cells — OBSERVED
  quirk, replicated verbatim, NOT fixed (out of scope; harmless: map1
  re-checks ht members, kk1 overwritten with min-counts at :410).
- Field ownership: grid.nc → lon/lat (FI/DL), kt1_raw codes, kt1_levels
  (final counts), kk1-min, wet/land masks, z_levels. bathymetry.nc →
  ht + map1 (+provenance). hu/hv stay runtime-derived (documented).
- Vertical: z DATA (param.f90:310-313) hardcoded in builders with source
  citation; k↑ = depth↑, centers, dz/dz1 DERIVED never stored.

## 2. Equivalence policy (as built)

- Canonical: IBCAO lat/lon float64 (full precision).
- Legacy decoded: KOORD float32-rounded 4-decimal text.
- grid.nc stores DECODED values as float64 (no false precision claim);
  canonical-vs-legacy delta REPORTED as quantization evidence.
- Tolerances: int masks/counts BIT-EXACT; lon/lat vs KOORD-decoded
  1e-6 deg; vs IBCAO canonical 1e-4 deg (4-decimal rounding bound);
  ht EXACT (small ints exact f32+f64); map1 0.01 cm (last-ulp f32/f64
  division); kt1 anchors vs EN4 product (wet cols + sum) EXACT.
- No rounding of canonical values to force bitwise tests (policy kept).

## 3. Builders + tests (this stage's code)

- NEW `python/grid/build_grid_nc.py` → `data/input/processed/grid/grid.nc`
  (dims x=133/y=105/z=18; lon/lat f64; kt1_raw i2; kt1_levels/kk1/
  wet/land_mask i1/i2; z_levels f64; CF-1.10 + CRS/provenance/MD5/git-sha
  attrs; x↔i, y↔j elementwise, NO transpose).
- NEW `python/grid/build_bathymetry_nc.py` → `.../grid/bathymetry.nc`
  (ht/map1 f4 cm, 8888 land, provenance attrs).
- NEW `python/tests/test_grid_bathymetry_nc.py`: self-contained
  (runs builders, independent minimal transcription + anchors).
  **TOTAL CHECKS: 34 ERRORS: 0.**
- Anchors hit exactly: wet cols 11067 == product wet_mask; sum(kt1)
  143176 == product water_column_levels (April; January 143422 differs
  legitimately by month). lon 8.3269–76.3245, lat 64.2057–85.0414.
- Q3 (H(2) 0.40 vs hst 0.5) and Q4 (CFL NaN rule) remain OPEN (out of
  scope: physics fix deferred; CFL rule due 11.7F).

## 4. Regression gates

- Full fpm battery: PASS (50 SUCCESS, 0 failures; incl. NetCDF
  reader tests era5_coverage/ocean_init/ice_init).
- Strict `-Wall -Wextra` clean from rebuild (Python builders unaffected;
  no Fortran changed).
- Equivalence: 34/34 (see §3).
- Model regression Jan OFF (`stage11.7B_JanN1`): exit 0, INIT-OK,
  md5-identical to janOFF (NDIFF=0) — tree intact (no Fortran changed).
- Preserved: EOS LEGACY default + optional EOS-80; legacy+N1 reference;
  11.5H-RC scheduler; 11.6.1 dispatch + tests; all physics/numerics.
- `git diff --check` clean.

## 5. Risks + rollback + next

- Risks closed this stage: i=is1 border asymmetry (caught by anchor,
  fixed pre-test); :238 quirk (replicated, documented); canonical-vs-
  legacy quantization (evidenced, not hidden).
- Rollback: builders/tests are ADDITIVE (new files only); outputs live
  under gitignored data/; legacy KOORD.DAT/hhh.bar untouched and still
  sole production inputs — nothing to roll back.
- NEXT: 11.7C (ocean_initial.nc + forcing_era5.nc passthrough builders +
  equivalence + coverage gates). No reader migration yet.

## 6. Files + verification

- Code: NEW `python/grid/build_grid_nc.py`, `python/grid/build_bathymetry_nc.py`,
  `python/tests/test_grid_bathymetry_nc.py` (34/34).
- Docs: this file (NEW); ROADMAP (11.7B COMPLETE→§11.7C next; EOS fix);
  INDEX 11.7B row; physics_status 11.7B line.
- Data (gitignored, not committed): `data/input/processed/grid/grid.nc`,
  `bathymetry.nc`.
- Verification: battery 50/50; strict clean; equivalence 34/34; Jan OFF
  NDIFF=0; diff-check clean; NO physics/defaults changes.
