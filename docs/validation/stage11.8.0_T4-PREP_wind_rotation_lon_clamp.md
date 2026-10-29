# Stage 11.8.0 T4-PREP — Wind Rotation (H-2) + Longitude Clamp (T-23)

**Status:** COMPLETE — both T4 prerequisites fixed behind OFF-by-default
switches; **T4 is GO** for implementation after this stage.
**Date:** 2026-10-25
**Base:** `cde710e` (T3-CORRECTIVE-4)
**Scope:** forcing interpolation only. No ocean physics, EOS, scheduler or
numerical-operator change; switches default OFF for backward compatibility.

---

## 1. H-2 — ERA5 wind rotation (geographic → rotated grid)

### Method

The real grid orientation is read from `KOORD.DAT` (`FI` = latitude, `DL` =
longitude on the 133×105 grid). The model grid-X direction is the `i` axis.
For each cell, using central differences along `i`:

```
east  = (lon(i+1,j) - lon(i-1,j)) · cos(lat(i,j))
north =  lat(i+1,j) - lat(i-1,j)
alpha = atan2(north, east)
```

then ERA5 geographic wind is rotated:

```
u_grid = u_geo·cos(alpha) + v_geo·sin(alpha)
v_grid = -u_geo·sin(alpha) + v_geo·cos(alpha)
```

The switch is **`STAGE118_WIND_ROTATION` (default OFF)**; ON applies the
rotation in `era5_wind()` before wind stress/`windx1`/`windy1` are formed.
OFF is the legacy unrotated path and is bit-identical.

### Verification

`python/tests/ocean/test_wind_rotation.py` (KOORD + real ERA5 u10/v10):
- mean alpha (wet cells): **50.06°**; median **50.18°**; range **14.02–81.28°**
  (matches the documented H-2 values ~50.2° median / ~81° maximum);
- 20 sample cells: `dir_grid == dir_geo − alpha`, max angular error
  **2.8e-14°** → **PASS**;
- Fortran implementation: 1-day `STAGE118_WIND_ROTATION=OFF/ON` runs show a
  maximum wind-vector change of **13.46 m/s** and interior rotation error
  **3.45e-4 m/s** (boundary `i=is1` copies the interior rotated value);
  `wind_rotation_fortran.json` → **PASS**.

Outputs: `docs/wiki/stages/stage11/evidence/wind_rotation_verification.json`,
`wind_rotation_fortran.json`.

## 2. T-23 — ERA5 longitude edge clamp

### Method

`era5_bilinear2d` retains the legacy cyclic ±360° wrap when
**`STAGE118_LON_CLAMP` is OFF** (default, bit-identical). When ON, an
out-of-range longitude is clamped to the file edges:

```
lon = min(max(lon, lon_file_min), lon_file_max)
```

and the right longitude neighbour no longer wraps to column 1; the last column
is used at the east edge.

### Verification

`python/tests/ocean/test_era5_longitude_wrap.py` runs the production harness in
both modes on a narrow 10–70°E file:

| query | OFF (legacy wrap) | ON (clamp) |
|---|---|---|
| 75°E | **10°E** (wrong side) | **70°E** (east edge) |
| 5°E control | 10°E | 10°E |

Status **FIXED**; `docs/wiki/stages/stage11/evidence/lon_clamp_verification.json`,
`era5_longitude_wrap_result.json`.

T1 spatial/temporal suites with `STAGE118_LON_CLAMP=true`:
- spatial: **PASS** (interior PASS, edges PASS, out-of-range query returns the
  edge 135°E); temporal: **PASS**.

## 3. Integration

T3 rest run with **both** switches ON and the T3-CORRECTIVE-4 chosen
configuration (dt=1800, Ah=10000, E1+E2+E3, zero forcing):

| metric | value |
|---|---|
| max \|U\| / \|V\| | 0.147 / 0.103 m/s |
| KE day 15 / 30 | 3.899e13 / 2.216e13 J |
| KE30/KE15 | **0.568** |
| classification | bounded (DRIFTING) |

The result is exactly the same as the chosen T4-PREP baseline
(`t3c4_dt1800_ah10000`), confirming that wind rotation and longitude clamping
do not affect the zero-forcing rest test. `docs/wiki/stages/stage11/evidence/t3_with_fixes.json`.

## 4. Regression and safety

| Check | Result |
|---|---|
| Full `fpm test` | **60/60**, exit 0 |
| Strict build | exit 0 |
| T1 spatial (clamp ON) / temporal | PASS / PASS |
| T-23 wrap test | **FIXED** (OFF 10°E, ON 70°E) |
| H-2 rotation test | **PASS** (max angular error 2.8e-14°) |
| ERA5 contract / snowfall | 120/120 / CONFIRMED_1H |
| EN4 T0 / T3-PREP / mask | CLEAN / CLEAN / CLEAN |
| Default legacy bit-identity | 1-day rest md5 identical to baseline |
| `git diff --check` | clean |

No ocean physics changed; both switches default OFF; `EOS_MODE=LEGACY`
default. T4–T6 not started; no `data/runs/` data deleted.

## 5. T4 decision

**GO for T4 (wind forcing) implementation.** The numerical T3b gate passed in
T3-CORRECTIVE-4, and the two T4 prerequisites (H-2 and T-23) are now fixed and
verified behind switches. Production defaults remain OFF until T4 validation
and the D-37 decision to promote them.
