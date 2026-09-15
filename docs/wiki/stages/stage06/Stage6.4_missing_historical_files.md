# Stage 6.4 — Missing Historical Input Files Documentation

**Generated:** 2026-08-19  
**Status:** Documented from actual source code inspection

---

## Summary

The model currently operates in `grid_mode=TEST` (synthetic grid) because the historical input files required for `grid_mode=REAL` are not available. The model gracefully falls back to synthetic fields when these files are absent.

---

## Missing Files by Module

### 1. KOORD.DAT — Geographic Coordinates (FI/DL)
**Required by:** `src/grid_coupling.f90:389` (when `grid_mode=grid_mode_real`)
**Purpose:** Full 2D fields of latitude (FI) and longitude (DL) for the real model grid
**Format:** Two arrays of size `(is1, js1)` = `(133, 105)` — read sequentially
**Current behavior (TEST mode):**
- Generates synthetic coordinates:
  - `fi(i,j) = 66.0 + 16.0*real(j-1)/real(js1-1)` → 66–82°N
  - `dl(i,j) = 30.0 + 33.0*real(i-1)/real(is1-1)` → 30–63°E
- **Explicit warning printed:** "WARNING: TEST ONLY synthetic grid... FI/DL are synthetic and NOT a real basin"

### 2. hhh.bar — Bathymetry / Ocean Mask
**Required by:** `src/grid_coupling.f90:31` (always attempted)
**Purpose:** Bathymetry data (depth) and land/ocean mask
**Current behavior:**
- If not found: "NOTICE: hhh.bar not found. Generating synthetic ocean basin for test run."
- Generates synthetic bathymetry via `map1` and `ht` arrays
- Used to set `kt1` (number of wet levels per column)

### 3. FI1DL1.DAT — Legacy Meteorological Grid Coordinates
**Required by:** `src/wind_forcing.f90:49` (legacy wind1 path)
**Purpose:** Latitude/longitude grid for legacy meteorological forcing interpolation
**Format:** Two arrays of size `(135, 107)` — `fi1`, `dl1`
**Current behavior:** "WARNING: FI1DL1.DAT not found, using default zeros for grid." — only affects legacy forcing path

### 4. GRM2 — Grid/Mask Parameters
**Required by:** `app/main.f90:142`
**Purpose:** Historical grid/mask configuration parameters
**Current behavior:** "WARNING: GRM2 missing, using defaults"

### 5. DAV4_5.98 — Legacy Atmospheric Forcing
**Required by:** `app/main.f90:174` (when `forcing_mode=forcing_mode_legacy`)
**Purpose:** Monthly mean atmospheric pressure fields for geostrophic wind calculation
**Format:** Pressure data on meteorological grid
**Current behavior:** "WARNING: DAV4_5.98 missing, using defaults" — only affects legacy forcing path

---

## Current Configuration

```fortran
! param.f90:165-167
integer, parameter :: grid_mode_real = 0
integer, parameter :: grid_mode_test = 1
integer :: grid_mode = grid_mode_test  ! DEFAULT

! param.f90:158-160
integer, parameter :: forcing_mode_legacy = 0
integer, parameter :: forcing_mode_era5 = 1
integer :: forcing_mode = forcing_mode_legacy  ! DEFAULT in param, but overridden in main.f90:77
```

**In main.f90:77:**
```fortran
forcing_mode = forcing_mode_era5  ! ERA5 forcing is ACTIVE by default
```

---

## Real Grid Activation Requirements

To enable `grid_mode=REAL`, the following files must be provided in the working directory:

| File | Dimensions | Content | Source |
|------|------------|---------|--------|
| `KOORD.DAT` | 133 × 105 × 2 | FI (lat), DL (lon) in degrees | AARI historical archive |
| `hhh.bar` | TBD | Bathymetry + mask | AARI historical archive |

**Note:** The model will **STOP with fatal error** if `grid_mode=REAL` is set but `KOORD.DAT` is missing (grid_coupling.f90:396-398).

---

## Scientific Context

From the Dmitriev/Nesterov model documentation (Stage 3.3_mapping.md):
- The original model was developed for the **Barents Sea region**
- Historical coordinates cover the Arctic basin including Barents Sea, Svalbard, Franz Josef Land
- The synthetic TEST grid (66–82°N, 30–63°E) approximately matches this region but is **not geographically accurate**

---

## Recommendation

**Do NOT fabricate these files.** The synthetic TEST grid is validated and numerically stable. Real grid activation should only proceed when:
1. Authentic `KOORD.DAT` and `hhh.bar` are recovered from AARI archives
2. A scientific validation plan exists comparing TEST vs REAL grid results
3. The Stage 6.1/3.5 real grid transition procedure is followed (promt.md items 5-6)

---

## Related Documentation

- `docs/wiki/stages/stage03/Stage3.5_real_grid.md` — Real grid deferral status
- `docs/wiki/stages/stage06/Stage6.1_real_grid_recovery.md` — Real grid recovery attempts
- `docs/wiki/stages/stage06/Stage6.2_barents_domain.md` — Barents ERA5 domain configuration
- `docs/wiki/stages/stage06/Stage6.4_unit_audit.md` — Unit audit (this stage)

---

*No physics modified — documentation only*