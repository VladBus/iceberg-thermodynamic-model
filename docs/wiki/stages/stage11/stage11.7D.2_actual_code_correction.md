# Stage 11.7D.2 — Actual Code Correction & Test Independence Enforcement

Frozen 2026-10-16. Corrective stage: every 11.7D.1 gap is closed IN CODE,
verifiable in the diff (not docs-only). NO production Fortran modified
(`src/` untouched — hht/kk1/map1/EOS/scheduler/physics all byte-identical);
NO reader switch; NO legacy removal; NO EOS change (LEGACY default);
NO 11.7E/11.8A/B/11.9/12 start.

## 1. Gap analysis (11.7D.1 claimed vs committed 0548734)

`git diff 93e890e..0548734 --stat` showed: the test file, KNOWN_ISSUES.md
and the `source` attribute were NOT in the commit — only the subprocess
import fix, docs, and report landed. This stage lands the rest.

## 2. Code changes (all verifiable via `git diff`)

- `python/tests/test_seaice_tides_nc.py`:
  `_precheck_inputs()` called FIRST in `main()` (SKIP exit 0 when legacy
  inputs absent; FAIL exit 1 when inputs present but dumps missing);
  oracle `read_ice_files_independent()` parses 1_*.ice from scratch;
  NO call to `sea.read_ice_files()` remains (verified by grep).
- `python/ice/build_seaice_nc.py`: `subprocess` at module level (11.7D.1,
  kept); NetCDF `source` + `sea_ice_status` attributes
  (`DIAGNOSTIC_PLACEHOLDER`/`DIAGNOSTIC` when inputs all-zero, else
  scientific source string) — read back and verified in the file.
- `python/tides/build_tides_nc.py`: `reference_dt1_seconds = 120.0`
  attribute + comment (qq_rad_per_step is bound to the legacy
  barotropic dt1; recompute if dt1 ever changes).
- `KNOWN_ISSUES.md`: T-16 (diagnostic sea-ice placeholders, KNOWN GAP
  blocking 11.8A science until real OSI-SAF/NSIDC/C3S data) + T-17
  (HST category-2 0.40 m hardcoded vs param 0.50 m, legacy quirk
  preserved AS-IS, test pins 0.40).

## 3. Test output (actual, this stage)

- `python test_seaice_tides_nc.py`: TOTAL CHECKS: 20 ERRORS: 0
  (sic/sit bit-exact vs independent oracle; HST/HMAX exact; tides
  null-tides zero + qq exact + status attr; dims/order/provenance).
- SKIP/FAIL contract: FULL path executed locally (inputs present);
  SKIP branches code-reviewed (CI has no data/* by construction).

- CI limitation: Python CI job does not run test_seaice_tides_nc.py.
  Python equivalence tests run locally, not in CI. CI integration is a
  future enhancement (no real-grid inputs in CI by construction).
- `fpm test grid_dump`: anchors 11067/143422/10336 (+gate 10336), STOP 0.

## 4. Regression (actual)

- Battery: PASS (50 SUCCESS, 0 failures; grid_dump anchors in-battery).
  Strict (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`,
  clean rebuild): zero warnings/errors. Jan OFF NDIFF=0
  (legacy-preservation only, NOT reader-equivalence). Python 20/20.
  diff-check clean.

## 5. Docs + go/no-go

- This file (NEW); INDEX +11.7D.2 row; ROADMAP (status + §11.7D.2);
  physics_status (11.7D.2); README already synced (11.7D.2).
- GO 11.7E: contracts closed in code as two-way builder-vs-independent-
  oracle comparisons (sea-ice/tides have no Fortran dump counterpart;
  Fortran comparison is done separately via grid_dump anchors in the
  fpm battery); residuals (monthly-ice gap, null tides, hht quirk,
  CF gap) explicitly deferred with owners. No blocker found.

## 6. Files + confirmation

- Code: test (SKIP-first + oracle), seaice builder (imports + source
  attr), tides builder (dt1 attr); docs (this file, INDEX, ROADMAP,
  physics_status, README, T-16/T-17).
- NO production Fortran source modified (verified: `git diff --stat`
  shows zero `src/` files); NO physics/defaults changes.
