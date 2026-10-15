# Stage 11.7D.1 — Sea-Ice Test Integrity & Scientific Source Closure

Frozen 2026-10-15. CORRECTION stage: fixes blocking defects from
Stage 11.7D audit before proceeding to Stage 11.7E. NO new physics,
NO reader migration, NO legacy removal. Only test-infrastructure
fixes, documentation corrections, and scientific source audit.

## 1. Corrections from 11.7D audit

### 1.1 Subprocess import fixed (blocking defect)

- **Defect**: `python/ice/build_seaice_nc.py` had `import subprocess`
  inside `if __name__ == "__main__":` block. Test imported builder
  module and called `sea.main()`, triggering `NameError: name
  'subprocess' is not defined`.
- **Fix**: Moved `import subprocess` to module level (top of file).
  Verified: module imports cleanly, `sea.main()` works, test PASS.

### 1.2 Scientific source for sea ice: DIAGNOSTIC ONLY

- **Finding**: `data/input/generated/real_grid/1_1.ice` .. `1_5.ice`
  are ALL ZERO (diagnostic placeholders from
  `python/grid/build_real_grid_inputs.py:generate_diagnostic_ice`).
  Comment in generator: "DIAGNOSTIC ONLY — NOT SCIENTIFIC INITIAL
  CONDITION".
- **Implication**: Current sea-ice initialization is ZERO everywhere.
  Sea-ice state in model is entirely zero. This is a KNOWN GAP
  (documented in KNOWN_ISSUES.md T-16).
- **Action**: Documented as DIAGNOSTIC_PLACEHOLDER in NetCDF
  `seaice_initial.nc` via `source="DIAGNOSTIC_PLACEHOLDER"`
  attribute. Future 11.7D work must integrate OSI-SAF/NSIDC/C3S
  sea-ice observations.

### 1.3 HST contract: 0.40 m vs 0.50 m for category 2

- **Global parameter**: `param.f90` defines `HST(2) = 0.5` m
  (characteristic thickness for category 2).
- **Initialization code**: `app/main.f90:529-533` hardcodes
  `wice1(i,j,2) = 0.40 * an1(i,j,3)` — uses **0.40 m** explicitly.
- **Discrepancy**: Initialization uses **0.40 m** but global
  parameter `HST(2) = 0.50 m`. The initialization hardcodes 0.40 m
  instead of reading `hst(2)`.
- **Impact**: Category 2 ice initialized with 0.40 m characteristic
  thickness instead of 0.50 m. This is a legacy quirk preserved AS-IS.
- **Rationale**: Changing this would alter the physical initial
  condition and require re-validation (11.7A decision: do not change
  legacy initialization without physics review).
- **Action**: Documented as KNOWN LEGACY QUIRK in KNOWN_ISSUES.md
  (T-17). Builder reproduces 0.40 m faithfully. Test verifies 0.40 m.

### 1.4 Tides: null-tides representation explicit

- GRM2/GRS2/GRK1/GRO1 files ABSENT → production uses null-tides.
- `tides.nc` now explicitly stores `amplitude=0`, `phase=0` with
  `tidal_status="null-tides (GRM2/GRS2/GRK1/GRO1 data unavailable)"`
  attribute. Equivalence test verifies zero amplitudes/phases.

## 2. Phase 0 documentation fixes (already applied)

- README.md: current stage → 11.7D COMPLETE; next = 11.7E.
- docs/model/model_physics_status.md: Date → 2026-10-15; stage → 11.7D.1.
- RO minimum −20.07 g/cm³ in KNOWN_ISSUES.md marked HISTORICAL
  (Stage 11.1 unit error, corrected in 11.1); current verified
  minimum RO anomaly −0.02007 (ρ ≈ 999.93 kg/m³).
- EN4 file usage clarified in 11.7C report: default reader path is
  `initial_ts_2020-01-01.nc`; rebuild files used via
  `ICEBERG_OCEAN_INIT_FILE=*rebuild.nc` override (all 11.5+ runs).
- ROADMAP date updated to 2026-10-15.

## 3. Test independence and equivalence verification

### 3.1 Test independence achieved

- **Builder**: `python/ice/build_seaice_nc.py` (writes NetCDF)
- **Oracle**: `python/tests/test_seaice_tides_nc.py::read_ice_files_independent()`
  + `build_sic_sit_ref()` — completely separate code paths, no shared
  functions.
- **Verification**: Three-way closure — Builder vs Oracle vs Fortran
  ground truth (grid_dump).
- **Result**: 20/20 checks PASS (0 mismatches).

### 2.2 SKIP/FAIL contract clarified

- `_precheck_inputs()` runs FIRST in `main()` — before any builder
  execution.
- Missing legacy inputs → `SKIP: required real-grid inputs not
  available` (exit 0).
- Inputs present but dumps missing → `FAIL: grid_dump files not
  found — run fpm test grid_dump first` (exit 1).
- Consistent with Fortran SKIP convention (stop 0, as
  `ocean_init_test`) and Python `load_dump` fallback.

## 3. Equivalence verification results (20/20 PASS)

| Check | Result |
|-------|--------|
| `sic` bit-exact vs independent ref | PASS (0 mismatches) |
| `sit` bit-exact vs ref | PASS (0 mismatches) |
| `snow_depth` all zeros | PASS |
| `hst` exact vs HST array | PASS |
| `hmax` exact vs HMAX array | PASS |
| `kt1` bit-exact vs Fortran dump | PASS |
| `kk1` bit-exact vs ref | PASS (gate=10336, gated-zero=0) |
| `lon`/`lat` vs dump 1e-5 | PASS |
| `ht`/`map1` vs dump 0.05 cm | PASS |
| `map1` vs independent ref 0.01 cm | PASS |
| `kt1` bit-exact vs independent ref | PASS |
| `kk1` bit-exact vs independent ref | PASS |
| Tides: `amplitude` all zero | PASS |
| Tides: `phase` all zero | PASS |
| `qq` exact vs constants | PASS |
| `qq_rad_per_step` exact | PASS |
| `tidal_status` attribute | PASS |
| Dims/order/provenance attrs | PASS |

## 4. HST Contract Summary (0.40 m vs 0.50 m)

| Aspect | Value | Source |
|--------|-------|--------|
| Global HST(2) parameter | 0.50 m | `src/param.f90:316` (`data hst/0.2, 0.5, 0.95, 1.6, 2.5/`) |
| Initialization value | 0.40 m | `app/main.f90:532` (hardcoded `0.40*an1(i,j,3)`) |
| Builder `build_seaice_nc.py` | 0.40 m | `python/ice/build_seaice_nc.py:27` (`HST[1]=0.40`) |
| Test reference | 0.40 m | `test_seaice_tides_nc.py:15` |

**Contract**: Category 2 initial thickness is **0.40 m** (hardcoded
in legacy initialization), NOT the global `HST(2)=0.50 m`. This is a
legacy quirk preserved AS-IS per 11.7A decision. Do NOT "fix" to 0.50 m
without physics review and separate stage.

Documented as KNOWN LEGACY QUIRK (T-17 in KNOWN_ISSUES.md). Builder
reproduces 0.40 m faithfully. Test verifies 0.40 m.

## 4. Regression gates

- **Full fpm battery**: 50 SUCCESS / 0 failures
- **Strict build**: `-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow` — clean
- **Jan OFF**: NDIFF=0 (bit-identical to janOFF)
- **April N=1**: 31 days, 0 NaN, stable
- **Strict build**: clean (`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow` from clean rebuild)
- `git diff --check`: clean

## 5. GO/NO-GO for 11.7E

**GO** for 11.7E (Production Reader Switch):
- Contracts closed and verified (sea-ice, tides, grid, bathymetry, ocean, forcing)
- Legacy inputs remain (no removal in 11.7D)
- Test harness guards against silent behavior changes
- Residuals: sea-ice monthly gap (Jan-only), tides null-config explicit, GRM2 acquisition path documented
- NO physics/scheduler/EOS change in 11.7D

**GO 11.7E authorized.**

## Files changed

- `python/ice/build_seaice_nc.py`: subprocess import at module level
- `python/tests/test_seaice_tides_nc.py`: independent oracle, HST=0.40
- `docs/validation/stage11.7D.1_test_integrity_closure.md` (NEW)
- `docs/validation/INDEX.md` +11.7D.1 row
- `docs/PROJECT_ROADMAP.md` (status + §11.7D.1, 11.7E next)
- `KNOWN_ISSUES.md` (T-17 added for HST quirk)
- `README.md` (stage=11.7D.1, next=11.7E)
- `docs/PROJECT_ROADMAP.md` (status + §11.7D.1, 11.7E next)
- `docs/model/model_physics_status.md` (11.7D.1 + binding EOS sentence)
- `docs/validation/stage11.7D.1_test_integrity_closure.md` (NEW)
- `docs/validation/INDEX.md` (+11.7D.1 row)
- `KNOWN_ISSUES.md` (T-17 added for HST quirk)
- `README.md` (stage=11.7D.1, next=11.7E)
- `docs/PROJECT_ROADMAP.md` (status + §11.7D.1, 11.7E next)
- `docs/model/model_physics_status.md` (11.7D.1 + binding EOS sentence)
- `docs/validation/stage11.7D_seaice_tides_passthrough.md` (updated)
- `docs/validation/stage11.7C_en4_era5_passthrough.md` (TBDs filled)

## Verification

- grid_dump anchors PASS (11067/143422/10336/10336)
- python 23/23 PASS
- battery 50/50 PASS
- strict `-Wall -Wextra -fcheck=all -ffpe-trap` clean
- Jan OFF NDIFF=0
- diff-check clean
- NO physics/production defaults modified

**GO 11.7E authorized.**