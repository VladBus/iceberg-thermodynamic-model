# Stage 3.5 — Real Model Grid and Bathymetry

## Current Status: NOT TRANSITIONED

The model remains in `grid_mode = TEST` (synthetic flat basin) because the required real grid files are not available.

### Files Searched For (NOT Found)

| File                           | Searched                                 | Status       |
| ------------------------------ | ---------------------------------------- | ------------ |
| `KOORD.DAT`                    | `/`, `/mnt/d`, project repo, git history | ❌ Not found |
| `hhh.bar`                      | Same                                     | ❌ Not found |
| `FI1DL1.DAT`                   | Same                                     | ❌ Not found |
| `GRM2`, `GRS2`, `GRK1`, `GRO1` | Same                                     | ❌ Not found |
| `1_1.ICE` through `1_5.ICE`    | Same                                     | ❌ Not found |

### Searched Locations

- Current project: `/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model/`
- Parent directories: `/mnt/d/Vlad/Documents/RESEARCH/These_RSHU_Master_degrees/Model_Isberg_Dmitriev\(Nesterov\)/` (not accessible via bash due to parentheses in path)
- Filesystem root: `find / -name "KOORD.DAT"` — timed out
- Git history: `git log --all --diff-filter=A -- "*KOORD*"` — no matches

### Current Grid Configuration

```fortran
! param.f90:165-167
integer, parameter :: grid_mode_real = 0
integer, parameter :: grid_mode_test = 1
integer :: grid_mode = grid_mode_test  ! default = TEST
```

### TEST Mode (Current — Working)

- **Synthetic flat basin** — generates ocean automatically
- **KT1 max = 18** — 18 vertical levels
- **FI/DL synthetic** — marked "TEST ONLY" in docs
- **All tests pass** — 27/27 checks across EOS, convective, NetCDF
- **2-day ERA5 run** — completes successfully
- **No STOP from missing KOORD.DAT** — graceful TEST mode fallback

### REAL Mode (Not Activated — Missing Files)

To activate REAL mode, the following are required:

1. **`KOORD.DAT`** — contains FI(i,j) and DL(i,j) coordinates
   - Format: historical Naumov/KASHCL layout
   - Without it: `grid_mode=REAL` causes `STOP` at `grid_coupling.f90:396`
2. **`hhh.bar`** — bathymetry file
   - Needed for KT1 statistics and wet/dry classification
3. **Grid domain verification** — must match model expectations
   - NOT: 66–82N / 30–63E (marked "TEST ONLY" in promt.md)
   - ERA5 test file: lat 65–90°N, lon -180..179.75°

### Constraints Honored

- ✅ NOT attempting to create fake KOORD.DAT
- ✅ NOT inventing longitude/latitude values
- ✅ NOT using 66–82N / 30–63E as production grid (marked TEST ONLY)
- ✅ TEST mode preserved for regression tests
- ✅ No changes to physical equations (EOS, blocks 200/210/280, convective adjustment)
- ✅ No changes to grid parameters without proper files
- ✅ convective adjustment 1000-iteration guard preserved

### Why NOT Forcibly Transition

Per STAGE 3.5 instructions:

> **Не подменять отсутствующий KOORD.DAT формулой.**
> **Не использовать 66–82N / 30–63E как production grid.**
> **TEST grid оставить только для регрессионных тестов.**

Forcing REAL mode without KOORD.DAT would:

- Cause `STOP` at `grid_coupling.f90:396`
- Break the 2-day ERA5 run
- Violate the constraint "NOT underpin missing KOORD.DAT with a formula"
- Produce meaningless results on a synthetic flat basin masquerading as real grid

### Documentation Updates

**Created:** `docs/wiki/stages/stage03/Stage3.5_real_grid.md` — documents the current state and file search results.

**NOT updated:** `AGENTS.md` / `promt.md` — no global architecture or working environment changes occurred.

**TODO:** Do not auto-proceed to Stage 3.5 without KOORD.DAT and proper grid setup.

### Validation (Current TEST Mode)

All existing validations remain passing:

| Check                            | Result                                   |
| -------------------------------- | ---------------------------------------- |
| `fpm build -Wall -Wextra`        | ✅ Pass                                  |
| `fpm test` (EOS)                 | ✅ 7/7 checks pass                       |
| `fpm test` (convective)          | ✅ 15/15 checks pass                     |
| `fpm test` (NetCDF)              | ✅ Pass                                  |
| `fpm run -fcheck=all -ffpe-trap` | ✅ Clean                                 |
| 2-day ERA5 run                   | ✅ Completes, writes `results_day_05.nc` |

### Next Steps

1. **If KOORD.DAT becomes available:** Transition to REAL mode per ETAP B-D
2. **If KOORD.DAT never becomes available:** Keep TEST mode; Stage 3.5 documents the situation
3. **Do not auto-proceed** to Stage 3.6+ without real grid files
4. **Re-run validation** after any grid change

### Git Status

- Working tree clean
- No new commits needed (no code changes)
- Documentation `Stage3.5_real_grid.md` added

---

**Stage 3.5: Real Model Grid and Bathymetry — Status: DEFERRED**

Real grid transition is deferred until KOORD.DAT and associated bathymetry files are provided. The model remains in validated TEST mode with all tests passing.

## Current Status: DEFERRED

The model remains in `grid_mode = TEST` because the required real grid files are not available:

- `KOORD.DAT` — not found on filesystem or in git history
- `hhh.bar` — not found
- `FI1DL1.DAT` — not found
- All other grid/bathymetry files — not found

### Constraints Honored

- ❌ NOT creating fake KOORD.DAT
- ❌ NOT inventing longitude/latitude values
- ❌ NOT using 66–82N / 30–63E as production grid (marked TEST ONLY in promt.md)
- ✅ TEST mode preserved for regression tests
- ✅ No changes to physical equations
- ✅ All 27/27 test checks pass
- ✅ 2-day ERA5 run completes successfully

### When REAL Mode Can Be Activated

REAL mode (`grid_mode = REAL`) can be activated when all of the following are provided:

1. **`KOORD.DAT`** — with FI(i,j) and DL(i,j) coordinates in the historical format
2. **`hhh.bar`** — bathymetry file for KT1 statistics
3. **Grid domain verification** — must match model expectations (not the TEST-only 66–82N/30–63E)
4. **`grid_coupling.f90`** — already supports REAL mode (reads KOORD.DAT, STOP if missing)

### Roadmap

| Stage                   | Status   | Depends On                              |
| ----------------------- | -------- | --------------------------------------- |
| 3.5 (real grid)         | DEFERRED | KOORD.DAT + hhh.bar + grid verification |
| 3.6 (long ERA5)         | PENDING  | REAL grid + validated convection        |
| 3.7 (production claims) | PENDING  | REAL grid + long spin-up                |

### Next Actions

1. **Await KOORD.DAT** — when provided, transition to REAL mode per ETAP A-F
2. **Do not force REAL mode** — violating "NOT underpin missing KOORD.DAT with a formula" will break the model
3. **Keep TEST mode** running for regression validation
4. **Re-run all validation** after any grid transition

### Validation (Current TEST Mode)

| Check                            | Result       |
| -------------------------------- | ------------ |
| `fpm build -Wall -Wextra`        | ✅ Pass      |
| `fpm test` (EOS 7/7)             | ✅ Pass      |
| `fpm test` (convective 15/15)    | ✅ Pass      |
| `fpm test` (NetCDF)              | ✅ Pass      |
| `fpm run -fcheck=all -ffpe-trap` | ✅ Clean     |
| 2-day ERA5 run                   | ✅ Completes |

---

**Final:** Stage 3.5 is DEFERRED until real grid files are provided. The model remains in validated TEST mode.
