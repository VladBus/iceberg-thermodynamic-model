# Stage 11.7B.3 — hht Determinism Guard & Test Contract Fix

Frozen (date). NARROW test-infrastructure + documentation fix. NO
production Fortran modified (`src/grid_coupling.f90` untouched — hht
NOT initialized, kk1/map1 logic untouched); NO EOS/scheduler change
(LEGACY default, N=1 reference); NO reader migration; NO legacy
removal; NO CFL thresholds; NO 11.7C/11.8A/B/11.9/12 start.

## 1. Three aggregate control counters in grid_dump.f90 (FAIL-capable portability guard)

- Added gate-cell counter: ngate recomputed from ht (land-ness preserved
  through smoothing ⟹ equals the :238 gate set) — expected 10336.
  Harness now asserts THREE aggregate control counters with
  actual-vs-expected ERROR lines and non-zero exit on ANY mismatch.
  Explicitly VERIFIED against expected values:
  nwet (wet column count) == 11067, sumkt (sum of kt1) == 143422,
  ngate (gate cell count) == 10336.
  Computed and REPORTED but NOT verified against expected values:
  map1wet, kk1pos (printed for inspection only).
  Note: ngate is computed from neighbouring ht values, not directly from
  the temporary kt1 set used in the :238 gate condition. The equivalence
  holds under the observed land-classification assumption but is not
  independently verified within this test.
  Verified run: `grid_dump: ... gate= 10336 / GRID DUMP OK`.
- Added the mandated hht comment (uninitialized → anchors encode
  reference-environment behaviour → compiler change needs manual review
  → do NOT 'fix' Fortran to satisfy the test).
- If hht behaviour changes under another compiler/flags, the test FAILS
  loudly instead of silently emitting a different grid.

## 2. Python SKIP pre-check moved to main() entry

- `_precheck_inputs()` runs BEFORE any builder: legacy inputs absent →
  `SKIP: required real-grid inputs not available`, exit 0; inputs present
  but dumps missing → `FAIL ... run fpm test grid_dump first`, exit 1.
- Consistent with the Fortran SKIP convention (stop 0, as
  ocean_init_test) and the in-load_dump fallback (defense in depth).
- Builders never crash-before-SKIP in clean environments now.

## 3. hht language corrections (11.7B.2 softened)

- "reproducibly benign" → "observed consistent in the project's
  reference build environment"; "proven/PROVES" → "observed/consistent
  with"; added explicit undefined-behavior + non-portability statement
  and the investigate-don't-modify rule (11.7B.2 §1).
- KNOWN_ISSUES T-15 ADDED (known legacy quirk, environment-dependent
  risk, anchor-verification mitigation, manual-review action).
- T-12 (11.7B.2) stands as corrected. Historical reports untouched.

## 4. CI limitation statement (verified accurate)

- fpm auto-discovers grid_dump (no explicit `[test.grid_dump]` section
  in fpm.toml for the harness; other tests have explicit `[test.*]`
  sections, grid_dump relies on fpm's automatic test discovery) →
  `fpm test` executes it wherever it runs.
- CI cannot run the grid gate: data/* gitignored + symlinks absent in
  fresh clones → grid_dump SKIP-stop-0 (no inputs), python test SKIP;
  python CI job does not run the equivalence test. KNOWN LIMITATION,
  not a bug: "CI does not currently execute the grid equivalence gate.
  This test requires real-grid inputs (KOORD.DAT, hhh.bar) which are
  gitignored. The gate is executed locally as part of the fpm test
  battery. A future CI enhancement could provision minimal test
  fixtures, but this is out of scope for Stage 11.7."

## 5. Verification (actual)

- grid_dump: anchors PASS (11067/143422/10336/10336), STOP 0; dumps in
  build/ (6 files), root ZERO grid_dump_*.dat; symlinks intact.
- Python: TOTAL CHECKS: 23 ERRORS: 0 (three-way kk1 0 mismatches).
- Battery: PASS (50 SUCCESS, 0 failures; gate anchor in-battery).
  Strict (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`,
  clean rebuild): zero warnings/errors. Jan OFF NDIFF=0
  (legacy-preservation only, NOT reader-equivalence). Python 23/23.
  diff-check clean.
- Files: `test/grid_dump.f90` (gate anchor + comment + SKIP kept),
  `python/tests/test_grid_bathymetry_nc.py` (pre-check); docs (this
  file, INDEX, ROADMAP, 11.7B.2 softening, T-15). NO production
  Fortran modified.

## 6. Go/no-go 11.7C

GO: three aggregate control counters guard determinism (FAIL-capable), SKIP contracts
consistent both languages, CI limits honest, all gates green.
Residuals unchanged (hht quirk, CF gap) — explicitly deferred.
