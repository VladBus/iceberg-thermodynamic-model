# Stage 11.7B.2 — Grid Reproducibility & Test Artifact Hygiene

Frozen (date). NARROW audit + test-infrastructure task. NO physics/
numerics change (coup1/hht untouched), NO EOS/scheduler change (LEGACY
default, N=1 reference), NO reader migration, NO legacy removal,
NO CFL thresholds, NO 11.7C/11.8A/B/11.9/12 start.

## 1. hht audit (conclusion: UNINITIALIZED but reproducibly benign)

- Trace (`grid_coupling.f90:coup1`, execution order): `hht` declared :45
  (local, no init). FIRST use :191 (`if (hht .lt. z(k)) exit` in the
  stale-kt1 block) has NO assignment on ANY prior path → uninitialized
  on every execution. Later uses (:212 smoothing `hht=0.0` first,
  :259/:322 `hht=ht(i,j)`) are all properly assigned.
- Origin check: model_all.txt ABSENT from tree → original-code comparison
  impossible; the in-code comment (:181-183) already documents it as a
  source bug. No transcription error on our side (we replicate outcomes,
  not the defect).
- Why benign (proven, not asserted): the stale block writes a UNIFORM
  garbage count C to all wet cells (same hht) and 8 to land; downstream
  only tests `==8`. Model behaviour (map1 wet 10336, kk1 gating) PROVES
  C!=8 across all validated runs. Even a NaN hht degrades gracefully
  (all comparisons false → same gate outcome as C!=8).
- Reproducibility (controlled): `rm -rf build` + standard flags
  (`fpm build --flag "-I/usr/include"`) + `fpm test grid_dump` →
  all six dumps BIT-IDENTICAL md5 across rebuilds
  (e2321a90/5a364b59/a25f8b7f/b2bf6847/b83a7730/5b4f049e);
  anchors 11067/143422/10336/10336 stable.
- Verdict: legacy quirk with known behaviour, reproducible. Fortran
  UNTOUCHED per mandate (no init, no repair). GO (not BLOCKED).

## 2. Artifact relocation (root → build/)

- Problem: grid_dump wrote six *.dat to CWD (project root).
- Fix: `test/grid_dump.f90` writes `build/grid_dump_*.dat` (6 `open`
  paths + `mkdir -p build` fallback via execute_command_line; build/
  always exists under fpm, fallback is belt-and-braces).
  `.gitignore:43` covers `build/` → artifacts ignored ✓.
- `python/tests/test_grid_bathymetry_nc.py` reads from `build/`;
  works after `rm -rf build` + clean `fpm test` with NO manual moves
  (grid_dump recreates its own outputs; verified §5).
- Cleanup: removed EXACTLY the six known root files by explicit names
  (no wildcards): dl/fi/ht/kk1/kt1/map1. Symlinks (KOORD.DAT, hhh.bar,
  1_1..1_5.ice) untouched — verified present post-cleanup.
- After clean run: ZERO grid_dump_*.dat in root (verified §5).

## 3. CI coverage assessment (honest)

- fpm.toml: NO per-test entries — fpm AUTO-DISCOVERS test/*.f90, so
  `fpm test` executes grid_dump wherever it runs. ✓ (in-battery here)
- CI (`.github/workflows/ci.yml`): `fpm test` job exists (netcdf
  installed) BUT data/* is gitignored → fresh clone has NO KOORD.DAT/
  hhh.bar/EN4/ERA5. grid_mode defaults REAL → coup1 would STOP.
- Fix (repo SKIP convention, as ocean_init_test): grid_dump now
  SKIP-stop-0 when KOORD.DAT or hhh.bar absent; python test SKIPs
  (exit 0) when dumps absent AND legacy inputs absent, FAILS (exit 2)
  when legacy inputs present but dumps missing (forgotten grid_dump).
- Verdict: grid equivalence CANNOT run in CI (no real-grid inputs) —
  documented limitation, NOT claimed coverage. Proposal: CI gains a
  synthetic-grid gate later (explicitly NOT a substitute for the
  real-grid gate); python CI job does not run the equivalence test
  (unchanged).

## 4. Documentation consistency

- INDEX: this 11.7B.2 row.
- ROADMAP: §11.7B.2 + status → 11.7B.2 COMPLETE.
- T-12 corrected: symlinks PRESENT (were documented absent); MUST NOT be
  removed/moved; grid_dump added to passing-with-symlinks list.
- CF grid_mapping gap stays as documented (11.7B.1) — no expansion.
- NDIFF=0 statement: "NDIFF=0 validates legacy control preservation
  ONLY. It does NOT validate NetCDF-reader equivalence, as the reader
  is not yet connected to production."

## 5. Verification (actual commands/results)

- Repro: `rm -rf build && fpm build --flag "-I/usr/include"` (exit 0) +
  `fpm test --flag "-I/usr/include" grid_dump` (STOP 0, anchors
  11067/143422/10336/10336) → six dumps md5-identical across rebuilds.
- Equiv: `python test_grid_bathymetry_nc.py` → TOTAL CHECKS: 23 ERRORS: 0
  (kk1 three-way 0 mismatches; gate 10336; gated-zero-wet 0).
- Battery: PASS (50 SUCCESS, 0 failures; grid_dump anchors in-battery).
  Strict (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`,
  clean rebuild): zero warnings/errors (notably no uninit warning for
  hht — consistent with provable-benign verdict). Jan OFF NDIFF=0
  (legacy-preservation only, NOT reader-equivalence). Python 23/23.
  diff-check clean.
- Root after clean run: 0 grid_dump_*.dat (verified); symlinks present
  (KOORD.DAT, hhh.bar, 1_1..1_5.ice).
- Files: `test/grid_dump.f90` (paths+mkdir+SKIP), python test
  (build/ path + SKIP/FAIL rule); docs (this file, INDEX, ROADMAP,
  T-12). NO physics/defaults changes.

## 6. Go/no-go 11.7C

GO: reproducibility proven (bit-identical rebuilds), artifacts out of
root with self-recreating workflow, CI limits documented honestly,
all gates green. Residuals (hht quirk, CF gap) explicitly deferred.
