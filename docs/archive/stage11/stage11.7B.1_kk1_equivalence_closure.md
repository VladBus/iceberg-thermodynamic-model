# Stage 11.7B.1 — kk1 Equivalence Closure & Grid Contract Audit

Frozen (date). Closes the 11.7B kk1 gap + dimension semantics + anchor
accounting. NO reader migration, NO legacy removal, NO EOS/scheduler/
physics change (LEGACY default, N=1 reference preserved), NO Fortran
algorithm change (observed quirks replicated, not fixed), NO CFL
thresholds, NO 11.7C/11.8A/B/11.9/12 start.

## 1. Defect (11.7B kk1 + shared-logic test)

11.7B `build_kk1` applied min-of-four to ALL interior cells, dropping the
:238 activation gate; the equivalence test shared the same logic, so 34/34
passed spuriously. Root cause of the miss: transcription-vs-transcription
testing without Fortran ground truth.

## 2. Exact Fortran sequence (re-traced; corrects 11.7B's "count-8" reading)

coup1() order: hhh read (raw codes) → ht ladder → mod loop → stale-hht
block (:180-196: land kt1=8 explicitly, wet = uniform garbage count C) →
hu/hv faces (from raw-mod ht) → SMOOTHING (:200-236: ht=mean of valid
faces, i=0..131/j=0..103, skips kt1==8) → :238 kk1 gate (all four
first-pass != 8) → map1 (smoothed ht) → dz/dz1 → :317 kt1-final
(0/land/max-k) → :410 kk1=min where gated, borders zeroed.
Key corrections vs 11.7B: (a) the :238 gate tests first-pass counts where
land IS 8 (stale-block else) — a proper land gate, not a count-8 skip
(the "40–49 m skip" reading is WITHDRAWN); C!=8 proven by map1 wet
~10336 (C==8 would zero kk1/map1 almost everywhere). (b) ht SMOOTHING
(:200-236) sits between raw ht and kt1-final — runtime kt1 sum is 143422,
not the unsmoothed 143176. (c) map1 members are BACKWARD neighbours
(i,j-1),(i-1,j) — 11.7B used forward rolls (caught by dump, 9392 cells).
(d) i=is1 column NOT forced land (101 wet cells).

## 3. Correction + independent verification (three-way, zero mismatches)

- Builders implement the full pipeline (raw→faces→smooth→kt1→kk1-gate→
  map1); bathymetry.nc gains ht_raw (future readers must derive hu/hv
  from pre-smoothing ht); grid.nc dims renamed x,y,z → i,j,k (Option A).
- NEW `python/grid/kk1_reference.py`: plain-loop oracle from scratch
  (no shared code with builders).
- NEW `test/grid_dump.f90`: runs production coup1(), dumps
  kt1/ht/map1/kk1/FI/DL to gitignored *.dat + asserts anchors
  (wet cols 11067, sum 143422).
- Python test rewritten around the dump: builder-vs-dump (kt1/kk1
  bit-exact 0 mismatches; FI/DL 1e-5 f32-rounding tol; ht/map1 0.05 cm),
  oracle-vs-dump bit-exact 0 mismatches, builder-vs-oracle bit-exact,
  gate cells 10336, gated-zero-wet 0.
  **TOTAL CHECKS: 23 ERRORS: 0.**
- Ordering: `fpm test grid_dump && python test_grid_bathymetry_nc.py`.

## 4. Anchors + water_column_levels explanation

- Static anchors (SOURCE files, runtime smoothed grid): wet cols 11067,
  sum(kt1) 143422 — match ocean_init_test AND the dump (no EN4 needed).
- Discrepancy resolved: Jan AND April products are IDENTICAL
  (wet 11067, sum 143176, masks/lat/lon/z bit-equal) — NO month geometry
  drift. 143422 (model, smoothed) vs 143176 (product, pre-smoothing
  levels): the EN4 builder used unsmoothed depths (+246 levels). Products
  agree column-wise (11067/11067); the 246-level delta is the smoothing
  effect. EN4 comparison is additional-only (recorded, never gated).
- IBCAO quantization evidence: grid.nc vs canonical < 1e-4 deg.

## 5. Dimensions + CF-1.10

- Option A applied: dims i(133)/j(105)/k(18) = model indices (CF cell
  indices, not physical axes); physical axes documented in attrs
  (X along j/east, Y along i/north); builders/tests/reruns consistent.
- CF-1.10: structural compliance present (Conventions, units,
  _FillValue, coords, provenance); projected-CRS grid_mapping with full
  CF mapping parameters ABSENT (also absent upstream in IBCAO source) —
  documented gap, full CF compliance deferred (no value/physics change).

## 6. Verification + go/no-go

- grid_dump anchors PASS; python 23/23; battery PASS (50 SUCCESS,
  0 failures, dump in-battery); strict `-Wall -Wextra` clean from rebuild;
  Jan OFF NDIFF=0; diff-check clean.
- New files: builders edited (pipeline), oracle, dump harness, rewritten
  test; docs: this file, INDEX row, ROADMAP §11.7B.1, KNOWN_ISSUES only
  if new (none — quirks documented, not defects).
- GO for 11.7C: grid/bathymetry contracts closed with Fortran ground
  truth; residual = documented quirks + CF-mapping gap (both deferred
  explicitly, neither blocks passthrough builders).

## 7. Files + confirmation

- Code: `python/grid/build_grid_nc.py` (smoothing+kk1+dims),
  `python/grid/build_bathymetry_nc.py` (smoothing+ht_raw+map1-gate+dims),
  NEW `python/grid/kk1_reference.py`, NEW `test/grid_dump.f90`,
  `python/tests/test_grid_bathymetry_nc.py` (rewritten, 23/23).
- Docs: this file; INDEX; ROADMAP.
- NO physics/production-defaults changes (Fortran untouched except NEW
  dump harness; KOORD.DAT/hhh.bar stay sole production inputs).
