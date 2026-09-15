# Stage 6.1 — Real Grid File Recovery and Provenance

## Summary

Exhaustive search for real grid and bathymetry files required for Stage 3.5
(real grid transition) across the repository, git history, and available
filesystem locations. **No required files found.**

**Stage 3.5 remains DEFERRED.** The model continues in validated `grid_mode=TEST`.

## 1. Files Searched

| File                    | Purpose                                              | Historical Source               | Status       |
| ----------------------- | ---------------------------------------------------- | ------------------------------- | ------------ |
| `KOORD.DAT`             | FI(i,j), DL(i,j) coordinates [deg]                   | Coupl1.f90, Dmitriev.txt        | ❌ Not found |
| `hhh.bar`               | KT1 mask (15I5 format), bathymetry source            | grid_coupling.f90, Dmitriev.txt | ❌ Not found |
| `FI1DL1.DAT`            | Alternative coordinate file                          | Stage 3.5 docs                  | ❌ Not found |
| `intdav`                | NP1 interpolation indices + X01/Y01                  | Coupl1.f90                      | ❌ Not found |
| `NP1`                   | Single integer NP                                    | Coupl1.f90                      | ❌ Not found |
| `GRM2`                  | Tidal amplitudes/phases M2,S2,K1,O1 (4 constituents) | Coupl1.f90                      | ❌ Not found |
| `GRS2`                  | Same as GRM2 for 2nd constituent set                 | Coupl1.f90                      | ❌ Not found |
| `GRK1`                  | Same for 3rd constituent set                         | Coupl1.f90                      | ❌ Not found |
| `GRO1`                  | Same for 4th constituent set                         | Coupl1.f90                      | ❌ Not found |
| `1_1.ICE` ... `1_5.ICE` | Initial ice area an1(i,j,2..6) [IS1 x JS1]           | Coupl1.f90                      | ❌ Not found |
| `DAV4_5.98`             | Atmospheric pressure P(i,j) [1420 x MM1+1]           | Coupl1.f90                      | ❌ Not found |

## 2. Search Coverage

### 2.1 Current Repository (`/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model/`)

- `find . -type f` — no matches for any target filenames
- `git log --all --full-history -- "**/KOORD*"` — no history of these files

### 2.2 Git History

- No commits adding/removing these files
- Repository was initialized with modernized Fortran sources only
- Historical model sources are in separate directory (not tracked in this repo)

### 2.3 Historical Model Directory

**Location:** `/mnt/d/Vlad/Documents/RESEARCH/These_RSHU_Master_degrees/Model_Isberg_Dmitriev(Nesterov)/`

**Contents:**

- Source directories: `mod_all/` (original F77), `model/` (F90 modernization), `model/copy1/`, `model/old_NDP/`
- Documentation: `Dmitriev.txt`, `Naumov.txt`, `Nesterov_last.txt`, `Polykov.txt`, `model_all.txt`
- **No data files** (KOORD.DAT, hhh.bar, etc.) present in any subdirectory

**Subdirectories checked:**

- `mod_all/` — source only
- `mod_all/дмитриев/` — source only
- `mod_all/наумов/` — source only (contains KASHCL.f for Kashin's scheme)
- `mod_all/поляков/` — source only
- `model/` — F90 sources + Debug/ build artifacts
- `model/copy1/` — duplicate sources
- `model/old_NDP/` — original F77 sources

### 2.4 Other RSHU Directories

- `/mnt/d/Vlad/Documents/RESEARCH/These_RSHU_Bachelors_degrees/` — no data files
- `/mnt/d/Vlad/Documents/RESEARCH/Langmuir_Waves/` — unrelated

### 2.5 Filesystem-Wide Search

```bash
find /home/vlad -iname "koord*" -o -iname "hhh*" -o ...
find /mnt/d -iname "koord*" -o -iname "hhh*" -o ...
```

**Results:** No matches for any target filename pattern.

## 3. File Format Specifications (from Historical Sources)

### 3.1 KOORD.DAT

**Read in:** `Coupl1.f90:118` and `grid_coupling.f90:391`

```fortran
READ(1) FI, DL      ! Unformatted (binary) read
```

- **Format:** Unformatted binary (Fortran direct access)
- **Arrays:** `FI(IS1,JS1)`, `DL(IS1,JS1)` — latitude/longitude [degrees]
- **Dimensions:** `IS1=133`, `JS1=105` (from param.f90)
- **Total elements:** 133 × 105 = 13,965 per array
- **Expected size:** ~112 KB per array (real*4) or ~224 KB (real*8)

### 3.2 hhh.bar

**Read in:** `grid_coupling.f90:31-41`, `Dmitriev.txt:767`

```fortran
READ(1,1011)
READ(1,1010) ((KT1(I,J),J=J1,J2),I=1,IS1)
```

- **Format:** Formatted text, 15I5
- **Structure:** 7 blocks of 15 columns each (J1=1→J2=15, step 15)
- **Array:** `KT1(IS1,JS1)` = `KT1(133,105)`
- **Values:** Integer mask (8=land, 0..KS=water depth index)
- **Records:** 7 × 133 = 931 lines of 15 integers each
- **Expected size:** ~70 KB

### 3.3 Tidal Files (GRM2, GRS2, GRK1, GRO1)

**Read in:** `Coupl1.f90:65-100`

```fortran
READ(3,*) (AMP1(I,1),I=1,133)
READ(3,*) (FAZ1(I,1),I=1,133)
...
```

- **Format:** Formatted text (list-directed)
- **Per file:** 4 constituents × (AMP + FAZ for IS1 + AMP + FAZ for JS1)
- **Arrays:** `AMP1..3(133,4)`, `FAZ1..3(133,4)`, `AMP2..3(105,4)`, `FAZ2..3(105,4)`

### 3.4 Ice Files (1_1.ICE .. 1_5.ICE)

**Read in:** `Coupl1.f90:175-200`

```fortran
READ(1,*) (AN1(I,J,2..6),J=1,JS1)  ! per file, per I
```

- **Format:** Formatted text
- **Per file:** `IS1` lines × `JS1` values = 133 × 105 = 13,965 reals
- **5 files** for categories 2..6 (category 1 = open water)

### 3.5 Initial Conditions Files

- `intdav`: `NP1(1330,4)`, `X01(1330)`, `Y01(1330)` — interpolation indices + coords
- `NP1`: Single integer `NP`
- `DAV4_5.98`: `MM1` then `P(1420, MM1+1)` atmospheric pressure

## 4. Version Compatibility Assessment

### Source Model Versions Found

| Directory        | Era       | Language | Notes                            |
| ---------------- | --------- | -------- | -------------------------------- |
| `mod_all/`       | 1995-2001 | F77      | Original Dmitriev/Naumov/Polykov |
| `model/`         | 2001-2002 | F90      | Modernized by Nesterov           |
| `model/copy1/`   | 2001-2002 | F90      | Duplicate of `model/`            |
| `model/old_NDP/` | 1995-1997 | F77      | Pre-Nesterov                     |

### Grid Dimensions Consistency

All versions use: `IS=132`, `JS=104`, `KS=18` → `IS1=133`, `JS1=105`, `KS1=19`

- Confirmed in `param.f90` (modernized) and `Coupl1.f90` (historical)
- `hhh.bar` read loops: `DO I=1,IS1` (133), `J=1,JS1` (105)

### Compatibility Risk: HIGH

- No data files exist to validate against
- Format assumptions based on READ statements only
- Unformatted `KOORD.DAT` binary format endianness unknown (likely little-endian x86)
- No checksums or metadata to verify integrity

## 5. Constraints Honored

| Constraint                               | Status                 |
| ---------------------------------------- | ---------------------- |
| ❌ NOT creating fake KOORD.DAT           | ✅ Honored             |
| ❌ NOT inventing coordinates             | ✅ Honored             |
| ❌ NOT using 66–82N/30–63E as production | ✅ Honored (TEST ONLY) |
| ✅ TEST mode preserved                   | ✅ Honored             |
| ✅ No physics changes                    | ✅ Honored             |
| ✅ All 27/27 tests pass                  | ✅ Honored             |

## 6. Recommendations

### If Files Become Available

1. **Verify format** against READ statements above
2. **Check dimensions** match `IS1=133`, `JS1=105`
3. **Validate coordinates** — ensure FI/DL cover intended domain
4. **Run compatibility test** in `grid_mode=REAL` with `-fcheck=all`

### If Files Remain Unavailable

- Keep `grid_mode=TEST` (current working state)
- Stage 3.5 documented as DEFERRED
- All regression tests pass in TEST mode
- 30-day ERA5 integration validated in TEST mode

## 7. Search Coverage Conclusion

| Location             | Searched | Result                |
| -------------------- | -------- | --------------------- |
| Current repo         | ✅       | No files              |
| Git history          | ✅       | No history            |
| Historical model dir | ✅       | Sources only, no data |
| Parent RSHU dirs     | ✅       | No data files         |
| Filesystem-wide      | ✅       | No matches            |

**Verdict:** Files are genuinely absent, not merely misplaced. Stage 3.5 cannot proceed without external provision of these files.

## 8. Documentation Updates

**Created/Updated:**

- `docs/wiki/stages/stage03/Stage3.5_real_grid.md` — already documents this search
- `docs/wiki/ERA5_INTEGRATION_TODO.md` — Stage 3.5 = DEFERRED
- `docs/wiki/stages/stage06/Stage6.1_real_grid_recovery.md` — this report

**No code changes.** No commits to repository (working tree clean).

## 9. Next Actions

1. **Await external provision** of KOORD.DAT + hhh.bar minimum
2. **Do not force REAL mode** — will STOP at `grid_coupling.f90:396`
3. **Continue TEST mode validation** — all tests pass
4. **Re-evaluate** if files are provided

---

**Stage 6.1 Complete: Search exhausted, files not found. Stage 3.5 remains DEFERRED.**
