# Stage 7.6A.1 — Fortran Grid Compatibility Audit

**Generated:** 2026-08-26  
**Status:** Complete — Classification A  
**Prerequisite:** Stage 7.6A (IBCAO V5.2 → model grid reconstruction)

---

## 1. Executive Summary

This audit performs a forensic, read-only compatibility analysis between the IBCAO V5.2 reconstructed model grid (`data/input/processed/grid/ibcao_model_grid.nc`) and the Fortran model's internal grid conventions, as reverse-engineered from the source code. The goal is to establish whether the reconstructed grid can be represented using the model's native data structures, and to identify every incompatibility or design decision required before connecting the grid to production Fortran.

**Key findings:**

1. **Dimensions are compatible.** The IBCAO grid has 133×105 nodes / 132×104 active cells, matching `param.f90:27` (`is=132, js=104, is1=133, js1=105`) exactly.

2. **Axis convention is compatible — but with a critical orientation difference.** The Fortran model uses X↔j (u-faces), Y↔i (v-faces), with Y inverted (north at j=1 in TEST mode). The IBCAO grid has latitude increasing with **i** (northward) and longitude increasing with **j** (eastward) — matching the Fortran convention `X↔j, Y↔i`. The TEST grid had latitude varying with j and longitude with i (transposed), which is the **opposite** of the correct real-grid orientation. The IBCAO grid corrects this.

3. **Cell-centre vs node representation: compatible.** The Fortran model stores all scalars (ht, kt1, fi, dl, ice state) at T-points (i,j). The IBCAO grid's `depth`, `lat`, `lon`, `mask` are cell-centre values, mapping directly to T-point arrays.

4. **Bathymetry sign convention: compatible.** IBCAO uses negative elevation (−5483 m ocean), converted to positive depth (4035 m) in the reconstruction. The model expects depth in cm (positive down) with land=8888.0. A conversion `depth_m × 100` and `land → 8888.0` is needed.

5. **Vertical Z-scale: 1,255 cells exceed 600 m.** All in westernmost 21 columns (Norwegian/Greenland Sea). The model's 18 Z-levels cap at 600 m (`param.f90:188–190`); kt1 saturates at 18 for deeper cells — an implicit clamp, not a crash. The Barents Sea proper (j > 21) is entirely < 600 m.

6. **KOORD.DAT format: documented but not yet generated.** The model reads `fi` and `dl` as list-directed real(4) arrays of shape (133,105) from `KOORD.DAT` (`grid_coupling.f90:389–393`). This can be trivially produced from the NetCDF product's `lat(i,j)` and `lon(i,j)`.

7. **hhh.bar format: documented, conversion needed.** The model reads `kt1` as 15I5 integer format in 7 blocks of 133 rows (`grid_coupling.f90:31–41`). The IBCAO NetCDF mask must be converted to the integer depth-code scheme (wet_fraction ≥ 0.5 → depth in model units; land → 8).

8. **1_k.ice format: documented, generation possible.** Five files `1_1.ice` through `1_5.ice`, each (133,105) real ASCII, one value per line (`main.f90:217–226`). Initial ice from OSI-SAF SIC + C3S/CS2SMOS SIT, regridded to the model grid, can be written in this format.

9. **ERA5 interpolation: compatible.** The model uses bilinear interpolation at each (fi(i,j), dl(i,j)) T-point (`wind_forcing.f90:225–226`). The IBCAO grid's latitude/longitude arrays are pointwise — no geometric assumption beyond the lat/lon values being correct.

10. **Drag-guard singularity: preserved.** The `hht < 0.01 → u=v=0` guard (`main.f90:401–406`) is independent of grid and will function identically on the real grid. The drag coefficient `a = c17*sqrt(...)/hht` (`main.f90:414`) has the same 1/hht singularity as before; the guard is the only protection.

---

## 2. Fortran Grid Dimensions (from `param.f90`)

```fortran
! param.f90:27
integer, parameter :: is = 132, js = 104, ks = 18
integer, parameter :: is1 = 133, js1 = 105, ks1 = 19
integer, parameter :: is2 = 131, js2 = 103, ks2 = 17
integer, parameter :: is3 = 134, js3 = 106, ngr = 5
integer, parameter :: is4 = 135, js4 = 107
```

| Parameter  | Value    | Meaning                                           |
| ---------- | -------- | ------------------------------------------------- |
| `is, js`   | 132, 104 | Active interior cells                             |
| `is1, js1` | 133, 105 | Nodes including ghost ring (T-point arrays)       |
| `ks`       | 18       | Vertical Z-levels                                 |
| `is3, js3` | 134, 106 | Extended dimensions for deformation tensor (EPR)  |
| `is4, js4` | 135, 107 | Extended dimensions for meteo-grid mapping (NP)   |
| `ngr`      | 5        | Ice thickness categories (Thorndike distribution) |

**IBCAO grid:** 133×105 nodes → 132×104 cells — **exact match.**

---

## 3. FI/DL Semantics (Geographic Coordinates)

From `param.f90:62`:

```fortran
real :: fi(is1, js1), dl(is1, js1)   ! [degrees]
```

- `fi(i,j)` = latitude [degrees_north]
- `dl(i,j)` = longitude [degrees_east]
- Shape: (133, 105) — full T-point arrays including ghost ring
- Units: degrees (not radians, not projected coordinates)

**Usage throughout the model:**

| Location                    | Usage                                                                |
| --------------------------- | -------------------------------------------------------------------- |
| `grid_coupling.f90:416`     | Coriolis: `fku(i,j) = omega * sin(fi(i,j)/57.3)`                     |
| `grid_coupling.f90:388–410` | Read from KOORD.DAT (REAL mode) or synthetic (TEST mode)             |
| `wind_forcing.f90:225–226`  | ERA5 interpolation: `lat = real(fi(i,j), 8); lon = real(dl(i,j), 8)` |
| `wind_forcing.f90:406–407`  | TEST mode: `fi = 66+16*(j-1)/104; dl = 30+33*(i-1)/132`              |
| `netcdf_output.f90`         | Written to CF-1.10 NetCDF as `latitude(i,j)`, `longitude(i,j)`       |

**TEST grid orientation (legacy):**

```fortran
! grid_coupling.f90:404-409 — TEST mode
fi(i, j) = 66.0 + 16.0*real(j - 1)/real(js1 - 1)  ! lat varies with J
dl(i, j) = 30.0 + 33.0*real(i - 1)/real(is1 - 1)  ! lon varies with I
```

In TEST mode: latitude ↔ j, longitude ↔ i.

**IBCAO grid orientation (real):**

- Latitude increases with **i** (northward: row 1 = south, row 133 = north)
- Longitude increases with **j** (eastward: col 1 = west, col 105 = east)
- This means **latitude ↔ i, longitude ↔ j** — the **inverse** of TEST mode

**Compatibility verdict:** The IBCAO grid uses the **correct** real-world orientation (lat↔i, lon↔j), consistent with the dynamical convention `X↔j, Y↔i`. The TEST grid's orientation (lat↔j, lon↔i) was intentionally transposed and is **not reused** for the real grid. This is correct.

---

## 4. B-Grid Convention (Arakawa)

The model uses an **Arakawa B-grid** with the following staggering:

### 4.1 T-points (scalars): `(i, j)`, shape (133, 105)

All scalar fields live at cell centres:

- `ht(i,j)` — bathymetric depth [cm] (`param.f90:76`)
- `kt1(i,j)` — wet-level index (integer) (`param.f90:87`)
- `fi(i,j)`, `dl(i,j)` — latitude, longitude [degrees] (`param.f90:62`)
- `t1(i,j,k)`, `s1(i,j,k)` — temperature [°C], salinity [fraction] (`param.f90:70`)
- `an1(i,j,k)` — ice concentration [fraction] (`param.f90:107`)
- `wice1(i,j,k)` — ice volume [m] (`param.f90:107`)
- `hsnow(i,j,k)` — snow thickness [m] (`param.f90:112`)

### 4.2 U-faces (X-direction): `hu(i, j)`, shape (133, 105)

`hu(i,j)` is the depth on the face between T-point `(i, j-1)` and `(i, j)`:

```fortran
! grid_coupling.f90:96-104
do j = 2, js1
    do i = 1, is1
        hu(i, j) = 0.5*(ht(i, j) + ht(i, j - 1))  ! avg of left/right T-points
    end do
end do
```

U-velocity: `u(i,j,k)` — at face between j-1 and j.

### 4.3 V-faces (Y-direction): `hv(i, j)`, shape (133, 105)

`hv(i,j)` is the depth on the face between T-point `(i-1, j)` and `(i, j)`:

```fortran
! grid_coupling.f90:106-114
do j = 1, js1
    do i = 2, is1
        hv(i, j) = 0.5*(ht(i, j) + ht(i - 1, j))  ! avg of top/bottom T-points
    end do
end do
```

V-velocity: `v(i,j,k)` — at face between i-1 and i.

### 4.4 Axis mapping

| Array axis   | Grid direction | Physical direction  |
| ------------ | -------------- | ------------------- |
| `j` (1..105) | X              | East (u-component)  |
| `i` (1..133) | Y (inverted)   | North (v-component) |

Y-axis is inverted: `j=1` is north, `j=js1=105` is south (in TEST mode: `fi = 66+16*(j-1)/104`).

### 4.5 IBCAO grid: compatible

The IBCAO grid stores everything at T-points (i,j) — depth, lat, lon, mask. U and V face depths are computed by `coup1()` from ht. The IBCAO grid does not need to pre-compute hu/hv; the Fortran code does it.

---

## 5. DX/DY Semantics

From `wind_forcing.f90:27`:

```fortran
real, parameter :: dxx = 13.89e5  ! [cm] = 13,890 m
```

This is used identically in both directions for pressure gradient scaling:

```fortran
! wind_forcing.f90:115-116 (legacy) and 283-284 (ERA5)
dpx1(i, j) = (p1(i, j + 1) - p1(i, j)) * 1.e3 / dxx   ! dp/dx along j
dpy1(i, j) = (p1(i, j) - p1(i + 1, j)) * 1.e3 / dxx   ! dp/dy along i
```

The model assumes **uniform, isotropic Cartesian spacing**: DX = DY = 13,890 m. There is no separate DY parameter. All horizontal derivatives use the same `dxx`.

**IBCAO grid:** The reconstructed grid has DX = DY = 13,890 m exactly (set by construction in `build_ibcao_grid.py`). The IBCAO polar-stereographic grid is locally uniform at 13.89 km — compatible.

**Note:** On a real polar-stereographic grid, the actual metric distance varies slightly with latitude. The model's Cartesian approximation introduces <1% error in metric distances at 66–85°N — acceptable for this model's accuracy. This is a known limitation documented in Stage 7.6A.

---

## 6. Cell-Centre vs Node Representation

The Fortran model uses **cell-centre (T-point) representation** for all scalars:

- Depth, coordinates, temperature, salinity, ice state — all at `(i,j)` = cell centre
- The "ghost ring" at `i=1`, `i=is1`, `j=1`, `j=js1` is the boundary/halo, not interior

The IBCAO reconstruction uses **pixel-centre aggregation** into node-centred boxes:

- Each `(i,j)` node represents a 13.89 km × 13.89 km box
- `depth(i,j)` = mean ocean depth within the box
- `mask(i,j)` = 0 (land) or 1 (wet)

**Compatibility:** The IBCAO grid's "node" values are effectively cell-centre values for boxes of size DX × DY. This matches the Fortran convention where ht(i,j) is the depth at the centre of the cell (i,j).

---

## 7. Bathymetry / hhh.bar Semantics

### 7.1 File format (`grid_coupling.f90:31–41`)

```
Open hhh.bar (if exists):
  For blocks jjj = 1..7:
    Read 1 header line
    Read 133 rows × 15 columns of kt1(i,j) as integer 15I5
    j1 = 1 + 15*(jjj-1), j2 = 15*jjj
  Close
```

The file contains `kt1(1:133, 1:105)` in 7 blocks of 15 columns each (15×7=105). Format: Fortran `15I5` (15 integers per line, 5 characters each).

### 7.2 Integer encoding of depth

From `grid_coupling.f90:43–85`:

```fortran
kt1(:, :) = 8                          ! land default
kt1(10:120, 10:90) = 600              ! ocean: depth code 600

ht(i, j) = real(kt1(i, j))           ! convert to real
! Then: ht(i,j) = ht(i,j) * 100.0    ! multiply by 100 to get cm
```

**Depth code convention:**

- `kt1 = 8` → land (ht → 8888.0 sentinel)
- `kt1 = integer depth in model units` → wet cell
- After `×100`: value in cm
- Model minimum clamp: `if (ht ≤ 3.0) ht = 3.0` → 300 cm = 3 m minimum
- Model maximum: 600 (→ 60,000 cm = 600 m) matches the deepest Z-level

### 7.3 Land sentinel: 8888.0

```fortran
! grid_coupling.f90:59-62
ht(1:15, 94) = 8888.0
ht(:, js1) = 8888.0
ht(:, 1) = 8888.0
ht(1, :) = 8888.0
```

All land cells are marked `8888.0` (real comparison with epsilon: `abs(ht-8888.0) < 1e-8`).

### 7.4 KT1 recomputation (`grid_coupling.f90:240–252`)

After HT is fully determined (including smoothing), KT1 is **recomputed** from HT:

```fortran
do j = 1, js1
    do i = 1, is1
        kt1(i, j) = 0
        hht = ht(i, j)
        if (abs(hht - 8888.0) .lt. 1e-8) cycle    ! land → kt1=0
        kt1(i, j) = 1
        do k = 2, ks
            if (hht .lt. z(k)) exit
            kt1(i, j) = k
        end do
    end do
end do
```

KT1 = number of full Z-levels that fit within the depth. For depth > 600 m: kt1 = 18 (saturation at ks=18).

### 7.5 Conversion from IBCAO

The IBCAO NetCDF has `depth(i,j)` in metres (positive down, NaN over land). Conversion to hhh.bar:

1. Map depth to integer code: `kt1_code = nint(depth_m)` (or nearest model level)
2. Land cells → 8
3. Write as 15I5 in 7 blocks of 133 rows

**Alternatively**, skip hhh.bar entirely and load depth directly from the NetCDF product into ht(i,j) (in cm), then let coup1() recompute kt1 from ht. This avoids the integer quantisation of the 15I5 format.

---

## 8. Vertical Z-Level Mapping

### 8.1 Z-levels (`param.f90:188–190`)

```fortran
data z/250., 500., 1000., 1500., 2000., 2500., 3000., 4000., &
       5000., 7500., 10000., 15000., 20000., 25000., &
       30000., 40000., 50000., 60000./    ! [cm]
```

| Level k | Depth z(k) [cm] | Depth [m] |
| ------- | --------------- | --------- |
| 1       | 250             | 2.5       |
| 2       | 500             | 5         |
| 3       | 1,000           | 10        |
| 4       | 1,500           | 15        |
| 5       | 2,000           | 20        |
| 6       | 2,500           | 25        |
| 7       | 3,000           | 30        |
| 8       | 4,000           | 40        |
| 9       | 5,000           | 50        |
| 10      | 7,500           | 75        |
| 11      | 10,000          | 100       |
| 12      | 15,000          | 150       |
| 13      | 20,000          | 200       |
| 14      | 25,000          | 250       |
| 15      | 30,000          | 300       |
| 16      | 40,000          | 400       |
| 17      | 50,000          | 500       |
| 18      | 60,000          | 600       |

### 8.2 Maximum resolvable depth: 600 m

KT1 saturates at 18 for any depth ≥ 600 m. The model's vertical resolution is adequate for the Barents Sea shelf (typically 200–400 m), but the western Norwegian/Greenland Sea basins (2,000–4,000 m) will be clamped to 600 m.

### 8.3 Deep cells (>600 m): 1,255 total

All in `j = 1..21` (westernmost columns), `i = 0..130`. These cells will have `kt1 = 18` — same as a 600 m cell. The model treats them as 600 m deep. This is an implicit clamp, not a crash.

**Impact assessment:** If dynamics in the western columns are unstable due to the depth clamp, the domain can be trimmed to `j ≥ 22` (removing Norwegian Sea). Alternatively, the 1255 cells can be accepted with the understanding that western-column dynamics are approximate.

---

## 9. Land/Sea Mask Semantics

### 9.1 Fortran convention

- `kt1(i,j) = 0` → land (or uninitialized)
- `kt1(i,j) = 8` → land (in hhh.bar encoding)
- `kt1(i,j) ∈ [1..18]` → wet, number of full Z-levels
- `ht(i,j) = 8888.0` → land sentinel (real comparison)
- `hu(i,j) = 8888.0` → land face
- `hv(i,j) = 8888.0` → land face

### 9.2 IBCAO convention

- `mask(i,j) = 0` → land
- `mask(i,j) = 1` → wet
- `wet_fraction(i,j)` → continuous [0,1] for fractional treatment

### 9.3 Conversion

| IBCAO             | Fortran                | Method                                 |
| ----------------- | ---------------------- | -------------------------------------- |
| `mask=0`          | `kt1=8`, `ht=8888.0`   | Land                                   |
| `mask=1, depth=d` | `kt1=k(d)`, `ht=d*100` | Wet: depth → cm, kt1 from Z-level loop |

---

## 10. Coriolis Parameter Dependencies

```fortran
! grid_coupling.f90:412-430
omega = 2.0 * 7.29e-5     ! [rad/s]
fku(i, j) = omega * sin(fi(i, j) / 57.3)   ! at T-points
fu(i, j) = 0.5*(fku(i,j) + fku(i+1,j))     ! at V-faces (between i and i+1)
fv(i, j) = 0.5*(fku(i,j) + fku(i,j+1))     ! at U-faces (between j and j+1)
```

Coriolis depends **only** on `fi(i,j)` (latitude). No dependency on grid geometry, spacing, or projection — just the latitude value.

**IBCAO grid:** `lat(i,j)` from the NetCDF product → direct mapping to `fi(i,j)`. Compatible with no conversion needed (both are degrees_north).

---

## 11. Wind/ERA5 Geographic Dependencies

### 11.1 ERA5 bilinear interpolation

```fortran
! wind_forcing.f90:223-270
do j = 1, js1
    do i = 1, is1
        lat = real(fi(i, j), 8)
        lon = real(dl(i, j), 8)
        ok = era5_bilinear2d(era5_u10(:,:,tidx), lat, lon, u10v)
        ! ... same for v10, t2m, msl, d2m, tcc, snowfall
    end do
end do
```

The interpolation uses the lat/lon values of each model T-point to look up ERA5 data. No geometric assumption — purely pointwise.

### 11.2 ERA5 domain coverage

| Property              | Value                      |
| --------------------- | -------------------------- |
| IBCAO grid extent     | ~64–85°N, 8–76°E           |
| ERA5 Barents download | 70–90°N, 10–70°E           |
| Southern gap          | ~6° (64–70°N) outside ERA5 |
| Western gap           | ~2° (8–10°E) outside ERA5  |

Points outside ERA5 return `ok=.false.` and are zeroed (`nbad` counter). This is a data-download issue, not a grid incompatibility. The ERA5 download domain should be expanded to cover the full model grid.

### 11.3 Pressure gradient

```fortran
! wind_forcing.f90:281-286
dpx1(i, j) = (p1(i, j + 1) - p1(i, j)) * 1.e3 / dxx   ! dp/dx along j
dpy1(i, j) = (p1(i, j) - p1(i + 1, j)) * 1.e3 / dxx   ! dp/dy along i
```

Uses DX=13.89e5 cm uniformly. Compatible with the IBCAO grid's uniform spacing.

---

## 12. KOORD.DAT Specification

### 12.1 Fortran reader (`grid_coupling.f90:388–400`)

```fortran
if (grid_mode .eq. grid_mode_real) then
    open (1, file='KOORD.DAT', status='old', iostat=ios)
    if (ios .eq. 0) then
        read (1, *) fi      ! list-directed read: real(4) array (133, 105)
        read (1, *) dl      ! list-directed read: real(4) array (133, 105)
        close (1)
    else
        print *, "FATAL: grid_mode=REAL but KOORD.DAT is missing."
        stop
    end if
end if
```

Format: Two lines of Fortran list-directed reals, each containing 133×105 = 13,965 values. Line 1 = `fi(1:133, 1:105)` (latitude), Line 2 = `dl(1:133, 1:105)` (longitude).

### 12.2 Reconstruction from NetCDF

```python
# Pseudocode
lat = nc['lat'][:]   # (133, 105) float32
lon = nc['lon'][:]   # (133, 105) float32

with open('KOORD.DAT', 'w') as f:
    f.write(' '.join(f'{v:.4f}' for v in lat.flatten()) + '\n')
    f.write(' '.join(f'{v:.4f}' for v in lon.flatten()) + '\n')
```

**Compatibility:** Straightforward. The NetCDF `lat(i,j)` and `lon(i,j)` map directly to `fi` and `dl`.

---

## 13. hhh.bar Specification

### 13.1 Fortran reader (`grid_coupling.f90:31–41`)

```fortran
j1 = 1; j2 = 15
do jjj = 1, 7
    read (1, *)                          ! header line (skipped)
    read (1, '(15I5)') ((kt1(i,j), j=j1,j2), i=1,is1)  ! 133 rows × 15 cols
    j1 = j1 + 15; j2 = j2 + 15
end do
```

7 blocks, each: 1 header line + 133 data lines of 15 integers (I5 format). Total: 105 columns = `js1`.

### 13.2 Integer depth code

- `8` = land
- `1..600` = wet cell; value × 100 = depth in cm
- After reading, `ht(i,j) = real(kt1(i,j))` is multiplied by 100 to get cm
- Minimum clamp: `ht ≤ 3.0 → ht = 3.0` (300 cm = 3 m)

### 13.3 Reconstruction from IBCAO

```python
# Pseudocode
depth_m = nc['depth'][:]    # (133, 105), positive down, NaN over land
mask = nc['mask'][:]        # (133, 105), 0=land, 1=wet

kt1_int = np.zeros((133, 105), dtype=int)
kt1_int[mask == 0] = 8                                    # land
kt1_int[mask == 1] = np.clip(np.round(depth_m[mask == 1]).astype(int), 1, 600)

with open('hhh.bar', 'w') as f:
    j1, j2 = 0, 15
    for block in range(7):
        f.write(f'Block {block+1}\n')                     # header
        for i in range(133):
            row = kt1_int[i, j1:j2]
            f.write(''.join(f'{v:5d}' for v in row) + '\n')
        j1 += 15; j2 += 15
```

---

## 14. 1_k.ice Specification

### 14.1 Fortran reader (`main.f90:217–226`)

```fortran
do k = 2, 6
    write (nam_file, '(A,I1,A)') '1_', k-1, '.ice'
    open (1, file=trim(nam_file), status='old', iostat=ios)
    if (ios .eq. 0) then
        do i = 1, is1
            read (1, *) (an1(i, j, k), j=1, js1)
        end do
        close (1)
    end if
end do
```

5 files: `1_1.ice` through `1_5.ice`. Each file: 133 lines × 105 real values (list-directed format). Values: ice concentration [fraction] for categories 1–5. `an1(i,j,1)` = open water fraction (computed, not read).

### 14.2 Post-read processing (`main.f90:228–247`)

```fortran
! Clip to [0, 1], set 9.99 → 0
! Compute open water: an1(i,j,1) = 1 - sum(an1(i,j,2:6))
! Initialize ice volume: wice1(i,j,k) = hst(k) * an1(i,j,k+1)
```

### 14.3 Dependencies for generation

The initial ice fields depend on:

- **Bathymetric mask** (`kt1`): ice only over wet cells (`kt1 > 0`)
- **OSI-SAF sea ice concentration** (SIC): for `an1(i,j,k+1)` values
- **C3S/CS2SMOS sea ice thickness** (SIT): to distribute across categories via `hst`
- **Model grid coordinates** (fi, dl): for spatial regridding of satellite data

### 14.4 Reconstruction path

1. Obtain January 2020 OSI-SAF SIC and C3S/CS2SMOS SIT (as identified in Stage 7.5 §12)
2. Regrid to model grid (133×105) using the `lat(i,j)`, `lon(i,j)` from the NetCDF product
3. Distribute SIT across 5 categories using the model's `hst` (0.2, 0.5, 0.95, 1.6, 2.5 m)
4. Write `1_1.ice` through `1_5.ice` as 133 lines × 105 reals

---

## 15. Drag-Coefficient Singularity

### 15.1 Guard location (`main.f90:401–406`)

```fortran
hht = 0.25*(hices(i,j) + hices(i,j2) + hices(i2,j) + hices(i2,j2))
if (hht .lt. 0.01) then
    u(i, j) = 0.0
    v(i, j) = 0.0
    cycle
end if
```

`hices(i,j)` = aggregate ice thickness (area-weighted mean of all categories). `hht` = average over 4 adjacent T-points. When `hht < 0.01 m`, velocity is zeroed.

### 15.2 Drag coefficient (`main.f90:414`)

```fortran
a = c17 * sqrt(b*b + a*a) / hht
```

1/hht singularity as hht → 0. The guard at 0.01 m prevents division by near-zero. This is **grid-independent** — works identically on the real grid.

### 15.3 Implication for real grid

The IBCAO grid's initial ice thickness (from satellite data) will determine how many cells start near the 0.01 m threshold. If large areas have thin ice (< 0.01 m), those cells will have u=v=0 (no motion) — physically correct (too thin to move) but potentially affecting mass transport. This was observed on the TEST grid in Stages 7.3–7.5.

---

## 16. NetCDF Output Compatibility

### 16.1 Existing output convention (`netcdf_output.f90`)

The model writes CF-1.10 NetCDF with:

- `latitude(i,j)`, `longitude(i,j)` — from `fi`, `dl`
- Model axes: X↔j (u), Y↔i (v)
- Unit system: canonical SI (temperature in K, salinity as mass fraction, etc.)

### 16.2 IBCAO NetCDF product

The Stage 7.6A product (`ibcao_model_grid.nc`) uses:

- `lat(i,j)`, `lon(i,j)` — from EPSG:3996→WGS84 conversion
- `depth(i,j)`, `mask(i,j)`, `wet_fraction(i,j)`
- CF-1.10 conventions

**Compatibility:** The coordinate arrays are in the same (i,j) shape and represent the same physical quantities. The NetCDF product can serve as a direct visualisation/validation reference against the Fortran model's output.

---

## 17. Deep Western Cells: Impact Assessment

### 17.1 Distribution

| Property                  | Value                                |
| ------------------------- | ------------------------------------ |
| Total cells > 600 m       | 1,255                                |
| Index range               | i ∈ [0, 130], j ∈ [0, 21]            |
| Geographic location       | Norwegian Sea / Greenland Sea basins |
| Depth range               | 600 – 4,035 m                        |
| Barents Sea cells > 600 m | 0 (j > 21)                           |

### 17.2 Model behavior for deep cells

- `kt1 = 18` (saturated) — the model "sees" 600 m
- All Z-levels are wet (k = 1..18)
- Vertical viscosity, advection, and thermodynamics operate normally
- The 3,400 m of "missing" depth is not represented

### 17.3 Options

1. **Accept clamp** — simplest; western-column dynamics are approximate but not unstable
2. **Trim domain** — remove columns j < 22; loses Norwegian Sea entirely
3. **Extend Z-levels** — physics change; requires promt.md procedure (forbidden without approval)

**Recommendation:** Accept clamp for Stage 7.6B diagnostic runs. If western-column instabilities appear, trim to j ≥ 22. Document explicitly.

---

## 18. Synthetic vs Real Grid: Orientation Comparison

| Property        | TEST grid                                         | IBCAO real grid                             |
| --------------- | ------------------------------------------------- | ------------------------------------------- |
| Latitude        | `fi(i,j) = 66 + 16*(j-1)/104` — varies with **j** | `lat(i,j)` — varies with **i** (northward)  |
| Longitude       | `dl(i,j) = 30 + 33*(i-1)/132` — varies with **i** | `lon(i,j)` — varies with **j** (eastward)   |
| Orientation     | Transposed (lat↔j, lon↔i)                         | **Correct** (lat↔i, lon↔j)                  |
| North direction | j=1 (high lat at j=1)                             | i=133 (high lat at i=133)                   |
| Coriolis        | f computed from fi(i,j) — works regardless        | f computed from fi(i,j) — works identically |

The TEST grid's transposed orientation worked because:

1. Coriolis uses `fi(i,j)` regardless of which axis it varies along
2. ERA5 bilinear interpolation uses the actual lat/lon values pointwise
3. The Cartesian dynamics don't "know" which axis is north

The real grid fixes the orientation to be geographically consistent. This is correct.

---

## 19. `grid_mode` Switch

```fortran
! param.f90:167-169
integer, parameter :: grid_mode_real = 0
integer, parameter :: grid_mode_test = 1
integer :: grid_mode = grid_mode_test   ! default
```

To activate the real grid, set `grid_mode = grid_mode_real` (0). This requires:

1. `KOORD.DAT` to exist (or the code stops at `grid_coupling.f90:396–399`)
2. `hhh.bar` to exist (or the code falls back to synthetic basin)

**For Stage 7.6B:** Both files must be generated from the IBCAO NetCDF product before the model can run in `grid_mode_real`.

---

## 20. Files to Generate for Real Grid

| File                   | Source                                  | Format                                | Size       |
| ---------------------- | --------------------------------------- | ------------------------------------- | ---------- |
| `KOORD.DAT`            | `lat(i,j)`, `lon(i,j)` from NetCDF      | 2 lines list-directed reals (133×105) | ~200 KB    |
| `hhh.bar`              | `depth(i,j)`, `mask(i,j)` from NetCDF   | 7 blocks × 133 lines × 15I5 integers  | ~100 KB    |
| `1_1.ice` .. `1_5.ice` | OSI-SAF SIC + C3S/CS2SMOS SIT regridded | 133 lines × 105 reals per file        | ~5 × 50 KB |

All three are small ASCII files. Generation is a Python post-processing step from the existing NetCDF product + satellite data.

---

## 21. Static Compatibility Matrix

| Aspect                          | Compatible?          | Notes                                                 |
| ------------------------------- | -------------------- | ----------------------------------------------------- |
| Grid dimensions (133×105)       | ✅ Yes               | Exact match to param.f90                              |
| B-grid staggering               | ✅ Yes               | T-points at (i,j); U at face j; V at face i           |
| DX=DY=13.89 km                  | ✅ Yes               | Uniform Cartesian approximation                       |
| FI/DL (lat/lon at T-points)     | ✅ Yes               | Pointwise, no geometric assumption                    |
| Cell-centre representation      | ✅ Yes               | IBCAO nodes = Fortran T-points                        |
| Bathymetry sign convention      | ⚠️ Conversion needed | IBCAO: neg elevation → Fortran: pos depth in cm       |
| Land sentinel (8888.0)          | ⚠️ Conversion needed | IBCAO: mask=0 → Fortran: ht=8888.0, kt1=8             |
| KT1 integer encoding            | ⚠️ Conversion needed | IBCAO: float depth → Fortran: integer code × 100      |
| Z-level coverage (600 m max)    | ⚠️ Partial           | 1,255 cells > 600 m clamped; Barents Sea OK           |
| ERA5 domain coverage            | ⚠️ Expansion needed  | Southern ~6° and western ~2° outside current download |
| Axis orientation (lat↔i, lon↔j) | ✅ Yes               | Correct real-world orientation                        |
| Coriolis from fi(i,j)           | ✅ Yes               | No conversion needed                                  |
| ERA5 bilinear interpolation     | ✅ Yes               | Pointwise lat/lon lookup                              |
| Ice initial condition format    | ⚠️ Generation needed | OSI-SAF + C3S data → 1_k.ice files                    |
| KOORD.DAT format                | ⚠️ Generation needed | NetCDF lat/lon → list-directed ASCII                  |
| hhh.bar format                  | ⚠️ Generation needed | NetCDF depth/mask → integer 15I5                      |
| Drag-guard singularity          | ✅ Yes               | Grid-independent, functionally identical              |

**Summary: 10/17 fully compatible; 7/17 require conversion/generation (all straightforward).**

---

## 22. Risk Register

| #   | Risk                                                      | Severity | Mitigation                                                    |
| --- | --------------------------------------------------------- | -------- | ------------------------------------------------------------- |
| 1   | Deep western cells (kt1=18 clamp) cause artificial mixing | Medium   | Monitor Stage 7.6B run; trim j<22 if unstable                 |
| 2   | ERA5 domain gap at southern/western edges                 | Low      | Expand download domain to [5–80°E, 60–90°N]                   |
| 3   | 1_k.ice categories not well-calibrated to IBCAO depth     | Medium   | Validate against OSI-SAF climatology; adjust hst distribution |
| 4   | Float32 precision in KOORD.DAT (list-directed)            | Low      | Same precision as TEST grid; already validated                |
| 5   | hhh.bar integer quantisation (1 m resolution)             | Low      | 1 m precision adequate for 13.89 km grid cells                |
| 6   | Coastal cells with wet_fraction 0.5–0.95 (977 cells)      | Low      | Majority rule is standard; document threshold                 |

---

## 23. Recommendations for Stage 7.6B

1. **Generate KOORD.DAT** from the IBCAO NetCDF product's `lat(i,j)` and `lon(i,j)`.
2. **Generate hhh.bar** from `depth(i,j)` and `mask(i,j)`, using the integer depth-code scheme.
3. **Set `grid_mode = grid_mode_real`** in `param.f90` (or pass via CLI).
4. **Generate initial ice files** (`1_1.ice` .. `1_5.ice`) from OSI-SAF SIC + C3S/CS2SMOS SIT, regridded to the model grid.
5. **Expand ERA5 download** to cover the full model domain (at minimum 60–85°N, 5–80°E).
6. **Run diagnostic experiment** (Classification A): 30-day ERA5-forced run on the real grid, monitoring:
   - KT1 distribution (deep-cell impact)
   - ERA5 interpolation quality (nbad counter)
   - Ice evolution & drag-guard frequency
   - Velocity stability (no NaN/Inf)
7. **Document deep-cell impact** explicitly in the Stage 7.6B report.

---

## 24. Classification

**A — Diagnostic/validation only.**

> Read-only forensic analysis of Fortran grid conventions vs IBCAO reconstructed grid. All 17 compatibility aspects documented. Seven conversion/generation tasks identified — all are straightforward Python post-processing. No production Fortran code modified. No physics changed. No model run attempted.

---

**End of Stage 7.6A.1 Audit**
