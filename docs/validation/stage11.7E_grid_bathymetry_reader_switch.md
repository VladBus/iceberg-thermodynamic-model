# Stage 11.7E — Production Reader Switch: Grid/Bathymetry

Frozen 2026-10-17. FIRST reader switch (lowest risk): grid/bathymetry
production input switchable between legacy KOORD.DAT/hhh.bar (default
OFF, bit-identical) and NetCDF grid.nc (ON) via `STAGE117E_NETCDF_GRID`.
Ocean/forcing/seaice/tides readers NOT switched (11.7E.2–11.7E.5);
NO legacy removal; NO physics/scheduler/EOS change (LEGACY default,
N=1 reference, EOS-agnostic); NO CFL thresholds; NO 11.8A/B/11.9/12.

## 0. Phase-0 preflight fixes (in this commit)

- Sea-ice source manifest (`python/ice/seaice_source_manifest.json`):
  builder transfers manifest fields verbatim; NEVER infers source from
  data values (fixes value-heuristic defect). Missing/inconsistent
  manifest → `source=UNKNOWN`.
- Sea-ice test `_precheck_inputs()`: requires 1_*.ice FIRST (its actual
  dependency); grid_dump files NOT required (they belong to the grid
  test). Also fixed latent `import sys` scoping fragility.
- "Three-way" wording: sea-ice/tides equivalence is two-way
  (builder vs independent oracle); Fortran ground truth applies to the
  grid path (grid_dump anchors in battery).
- INDEX duplicate 11.7D rows removed (exactly one each); "ice levels"
  grid/ocean anchor removed from sea-ice rows; ROADMAP §11.6/§11.6.1
  structure + dates + EOS-status sentence verified current.
- CI note: Python equivalence tests run locally, not in CI
  (no data/* in CI by construction).

## 1. Switch architecture (file-read layer only)

- Env `STAGE117E_NETCDF_GRID` (default OFF), read once in `s117e_init()`
  before `coup1()`. OFF: legacy KOORD.DAT/hhh.bar path byte-unchanged
  (incl. synthetic fallback + KOORD FATAL + TEST synthetics).
- ON: `s117e_read_codes()` (kt1_raw int16 → int) + `s117e_read_coords()`
  (lon/lat f64 → FI/DL f32) from `data/input/processed/grid/grid.nc`
  (CWD-relative, like legacy). The ENTIRE derivation chain below
  (ht/mod/smooth/map1/kt1-counts/kk1/hu/hv/dz/IDX/Coriolis) runs
  UNCHANGED in both paths — divergence by construction impossible;
  the equivalence gate measures only the IO layer (f64→f32 rounding).
- Deviation from the 11.7A sketch (documented, deliberate): finals
  (ht/map1) are NOT read; codes+coords are read and the validated
  derivation reused. Rationale: smallest new-code surface, zero
  derivation-divergence risk; bathymetry.nc stays a validated artifact.
- Rollback: unset the env var (legacy files untouched in place).
  Missing grid.nc with ON → FATAL STOP with rollback hint (no silent
  fallback; KOORD-missing convention).
- Rationale record: `src/netcdf_grid_reader.f90` header.

## 2. System-library quirk (found, worked around, proven harmless)

- System libnetcdff (4.6.2) reads 2D vars of python-written NETCDF4
  files TRANSPOSED through whole-var/hyperslab calls (small slabs and
  C-library ncdump read fine; affects EN4 files identically — their
  reader is axis-order-independent by design, which is why production
  never noticed). Root cause in the library/HDF5 layer is out of scope.
- Workaround IN the reader (not the files — files stay canonical):
  read into (js1,is1) buffers + transpose back with explicit loops.
- Proof (not assertion): 0/13965 mismatches vs independent Python read
  of kt1_raw; final OFF-vs-ON model runs bit-identical (§3).

## 3. Equivalence (same build; only the switch differs)

- Jan N=1 legacy: ON ≡ OFF ≡ janOFF — bit-identical ALL outputs
  (32 files, day_00…day_30).
- Apr N=1 legacy: ON ≡ OFF ≡ AprLegacy — bit-identical ALL outputs
  (31 files, 0 NaN total across all fields).
- f64→f32 coordinate rounding: zero observable effect (bit-identity).
- Wall-clock: ON ≈ OFF (reader runs once at init).

## 4. Regression gates

- Full fpm battery: 50 SUCCESS / 0 failures (incl. grid_dump anchors
  11067/143422/10336 + ocean/ice/ERA5 reader tests; all OFF-path).
- Strict (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`,
  clean rebuild): compiled clean, 0 warnings/errors.
- Jan OFF: triple-identity NDIFF=0 vs janOFF and vs JANON (new binary).
  Apr OFF: triple-identity NDIFF=0 vs AprLegacy and vs APRON. Both
  double as OFF-path gates for the switch.
- Jan/Apr ON: identical vs OFF (see §3).
- `git diff --check`: clean.

## 5. Files + verification + go/no-go 11.7E.2

- Code: NEW `src/netcdf_grid_reader.f90` (init/flag/codes/coords/FATAL);
  `app/main.f90` (+use/init-call); `src/grid_coupling.f90` (+use,
  two if/else wraps around FILE-READ blocks only); Phase-0 python/doc
  fixes (manifest, precheck, INDEX dupes, metric wording, CI note).
- Docs: this file (NEW); INDEX +11.7E row; ROADMAP (11.7E COMPLETE,
  next 11.7E.2); physics_status (11.7E).
- Verification: §3 bit-identity (Jan+Apr triple, 32+31 files); battery
  50/0; strict clean (0 warnings/errors); diff-check clean; NO
  physics/defaults changes (only additive switch code + Phase-0 fixes).
- GO 11.7E.2 (ocean_initial reader): switch pattern proven (env-gated
  IO-layer swap + bit-identical equivalence); residual = the §2 library
  quirk (contained by transpose-back + gate; revisit if a future reader
  needs Hyperslabs beyond whole-var reads).

## 6. Rollback procedure

1. `unset STAGE117E_NETCDF_GRID` (or any value other than true/TRUE/1).
2. Rerun — legacy KOORD.DAT/hhh.bar path engages (verified identical
   this stage: JANOFF/APROFF runs).
3. No file moves, no rebuild needed (switch is runtime).
