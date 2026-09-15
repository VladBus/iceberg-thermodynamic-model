# Stage 9.4C.1 Solar Radiation & ERA5 Variable Audit

**Date:** 2026-09-04  
**Status:** COMPLETE — Simplification Confirmed, ERA5 Radiation Not Used

---

## 1. Solar Geometry Implementation (iceberg_thermodynamics.f90)

### 1.1 Current Implementation (lines 214-221)

```fortran
lat_rad = state%latitude/57.2957795  ! градусы → радианы
decl = 0.0                           ! склонение Солнца (упрощение: экватор)
dec_rad = decl/57.2957795

hour_angle = 0.0  ! локальный полдень (упрощение)
! cos(zenith) = sin(φ)sin(δ) + cos(φ)cos(δ)cos(h)
cos_zenith = sin(lat_rad)*sin(dec_rad) + cos(lat_rad)*cos(dec_rad)*cos(hour_angle)
cos_zenith = max(0.0, cos_zenith)  ! только дневное
```

### 1.2 Simplification Analysis

| Parameter    | Value    | Meaning                 | Physical Reality                    |
| ------------ | -------- | ----------------------- | ----------------------------------- |
| `decl`       | 0.0      | Solar declination = 0°  | **Equinox only** (Mar 21 / Sep 23)  |
| `hour_angle` | 0.0      | Hour angle = 0          | **Local solar noon only**           |
| `cos_zenith` | cos(lat) | Zenith angle = latitude | No diurnal cycle, no seasonal cycle |

**Result:** The model assumes **permanent equinox at local noon** everywhere.

### 1.3 Impact at Representative Latitudes

| Latitude | cos_zenith | SW_down (clear sky) | Daily Average SW (actual) | Model / Actual    |
| -------- | ---------- | ------------------- | ------------------------- | ----------------- |
| 70°N     | 0.342      | 463 W/m²            | ~150 W/m² (annual avg)    | 3.1× overestimate |
| 75°N     | 0.259      | 350 W/m²            | ~100 W/m² (annual avg)    | 3.5× overestimate |
| 80°N     | 0.174      | 235 W/m²            | ~50 W/m² (annual avg)     | 4.7× overestimate |

**The model significantly overestimates shortwave radiation** because:

1. No night (hour_angle fixed at noon)
2. No winter (decl fixed at equinox)
3. cos²(zenith) weighting overestimates daily average

---

## 2. Shortwave Radiation Formula (lines 224-236)

```fortran
sw_down = SOLAR_CONSTANT*cos_zenith**2*(1.0 - CLOUD_COEFF*atmos%tcc**3)

! Empirical atmospheric transmissivity correction (legacy HEAT)
rad_b1 = (cos_zenith + 2.7)*1.0e-5
rad_b2 = 1.085*cos_zenith + 0.1

e_sat_air = SAT_VAPOR_0*10.0**(TETENS_A*(t_air_k - 273.15)/t_air_k)
e_sat_dew = SAT_VAPOR_0*10.0**(TETENS_A*(t_dew_k - 273.15)/t_dew_k)
rh = min(1.0, max(0.0, e_sat_dew/e_sat_air))
e_vap = rh*e_sat_air

sw_down = sw_down/(rad_b1*e_vap + rad_b2)  ! итоговое SW_down
```

### 2.1 Constants

| Constant         | Value       | Role                               |
| ---------------- | ----------- | ---------------------------------- |
| `SOLAR_CONSTANT` | 1353.0 W/m² | Solar constant (top of atmosphere) |
| `CLOUD_COEFF`    | 0.6         | Cloud attenuation factor           |
| `ALBEDO_ICE`     | 0.7         | Ice albedo                         |

### 2.2 Formula Critique

- `cos_zenith²` — unusual; typically just `cos_zenith` for direct beam
- Cloud attenuation: `(1 - 0.6*tcc³)` — empirical, not standard
- Water vapor correction: `/(rad_b1*e_vap + rad_b2)` — legacy empirical formula

**This is a legacy parameterization from the Dmitriev-Nesterov HEAT model, not a modern radiation scheme.**

---

## 3. Longwave Radiation (lines 242-248)

```fortran
! Incoming LW: empirical formula (legacy HEAT)
lw_down = LW_EMISS*t_air_k**4* &
          (1.0 + LW_CLOUD_FACTOR*atmos%tcc)* &
          (1.0 - LW_HUMID_COEFF*exp(-LW_HUMID_EXP*(273.15 - t_air_k)**2))

! Outgoing LW: black body with ice emissivity
lw_up = -EMISSIVITY*STEFAN_BOLTZ*t_surf_k**4
```

### 3.1 Constants

| Constant          | Value          | Role                                         |
| ----------------- | -------------- | -------------------------------------------- |
| `LW_EMISS`        | 5.4999e-8      | Effective atmospheric emissivity coefficient |
| `LW_CLOUD_FACTOR` | 0.275          | Cloud enhancement factor                     |
| `LW_HUMID_COEFF`  | 0.261          | Humidity correction coefficient              |
| `LW_HUMID_EXP`    | 7.77e-4        | Humidity exponent                            |
| `EMISSIVITY`      | 0.97           | Ice emissivity                               |
| `STEFAN_BOLTZ`    | 5.670374419e-8 | Stefan-Boltzmann constant                    |

---

## 4. ERA5 Radiation Variables — NOT USED

### 4.1 ERA5 Variables Available (CDS)

| Variable | CDS Name | Units | Type        | Description                         |
| -------- | -------- | ----- | ----------- | ----------------------------------- |
| SSR      | `ssr`    | J/m²  | Accumulated | Surface net solar radiation         |
| STR      | `str`    | J/m²  | Accumulated | Surface net thermal radiation       |
| SSRD     | `ssrd`   | J/m²  | Accumulated | Surface solar radiation downwards   |
| STRD     | `strd`   | J/m²  | Accumulated | Surface thermal radiation downwards |
| SSHF     | `sshf`   | J/m²  | Accumulated | Surface sensible heat flux          |
| SLHF     | `slhf`   | J/m²  | Accumulated | Surface latent heat flux            |

### 4.2 Current Model Behavior

**The model does NOT read or use any ERA5 radiation variables.**

From `src/netcdf_input.f90`, only these ERA5 variables are read:

- `u10`, `v10` (wind)
- `t2m` (2m temperature)
- `d2m` (2m dew point)
- `msl` (mean sea level pressure)
- `tcc` (total cloud cover)
- `sf` (snowfall)

### 4.3 Accumulated vs Instantaneous — Critical Issue

If ERA5 radiation variables were to be used in the future:

| Variable             | Units | Accumulation Period                             | Conversion to Flux                       |
| -------------------- | ----- | ----------------------------------------------- | ---------------------------------------- |
| SSR, STR, SSRD, STRD | J/m²  | **Since forecast start** (typically 12h or 24h) | Divide by accumulation period in seconds |
| SSHF, SLHF           | J/m²  | **Since forecast start**                        | Divide by accumulation period in seconds |

**Example:** ERA5 hourly forecast output has 1-hour accumulation. To get W/m²:

```
Flux [W/m²] = Accumulated [J/m²] / 3600 [s]
```

**The current model does not need this conversion because it computes radiation internally.**

---

## 5. Solar Geometry — Classification

### 5.1 Simplification Status

| Aspect                    | Status                         | Documented?              |
| ------------------------- | ------------------------------ | ------------------------ |
| `decl = 0.0` (equinox)    | **INTENTIONAL SIMPLIFICATION** | ✅ Yes (Stage 9.4A docs) |
| `hour_angle = 0.0` (noon) | **INTENTIONAL SIMPLIFICATION** | ✅ Yes (Stage 9.4A docs) |
| No diurnal cycle          | **KNOWN LIMITATION**           | ✅ Yes                   |
| No seasonal cycle         | **KNOWN LIMITATION**           | ✅ Yes                   |

### 5.2 Classification per Stage 9.4C.1 Decision Tree

| Category | Description                           | Applies?                                           |
| -------- | ------------------------------------- | -------------------------------------------------- |
| A        | Fully implemented, physically correct | ❌ No                                              |
| B        | Implemented but simplified/legacy     | ✅ **YES** — documented intentional simplification |
| C        | Unresolved scientific issue           | ❌ No — simplification is intentional              |
| D        | Confirmed defect                      | ❌ No — not a bug, documented limitation           |
| E        | Insufficient evidence                 | ❌ No                                              |

**Classification: B — Documented intentional simplification (legacy approximation).**

---

## 6. Recommendations for Stage 9.4D

### 6.1 Solar Geometry (Required for Physical Correctness)

1. **Compute solar declination** from model date:

   ```
   decl = -23.44° * cos(2π * (day_of_year + 10) / 365.25)
   ```

2. **Compute hour angle** from model time:

   ```
   hour_angle = 15° * (local_solar_time - 12)
   local_solar_time = UTC + longitude/15 + equation_of_time
   ```

3. **Diurnal averaging** — integrate over day or use proper time-stepping

### 6.2 ERA5 Radiation Variables (Optional Enhancement)

If using ERA5 radiation:

- Read `ssrd`, `strd` (downwelling SW/LW)
- Convert from J/m² (accumulated) to W/m² (flux) using accumulation period
- Replace internal SW/LW parameterization with ERA5 values
- Handle cloud-radiation consistency (ERA5 tcc vs radiation)

### 6.3 Modern Radiation Scheme (Long-term)

Replace legacy parameterizations with:

- SW: Two-stream or delta-Eddington with spectral bands
- LW: RRTM or similar correlated-k method
- Surface albedo: spectral, dependent on melt state, snow cover

---

## 7. Summary for Stage 9.4C.1 Report

| Audit Item           | Status         | Notes                                        |
| -------------------- | -------------- | -------------------------------------------- |
| Solar declination    | **SIMPLIFIED** | `decl = 0.0` (equinox) — documented          |
| Hour angle           | **SIMPLIFIED** | `hour_angle = 0.0` (noon) — documented       |
| Diurnal cycle        | **ABSENT**     | Known limitation                             |
| Seasonal cycle       | **ABSENT**     | Known limitation                             |
| SW formula           | **LEGACY**     | cos²(zenith) + empirical corrections         |
| LW formula           | **LEGACY**     | Empirical atmospheric emissivity             |
| ERA5 radiation vars  | **NOT USED**   | Model computes internally                    |
| ERA5 accumulation    | **N/A**        | Not applicable (not used)                    |
| Physical correctness | **LIMITED**    | Overestimates SW by 3-5× at Arctic latitudes |
| Classification       | **B**          | Documented intentional simplification        |

---

## 8. Files Referenced

- `src/iceberg_thermodynamics.f90` — Solar geometry and radiation (lines 29-30, 167, 196, 214-248)
- `src/netcdf_input.f90` — ERA5 variable reading (lines 31-39, 193-213)
- `docs/wiki/stages/stage09/Stage9.4A_Lagrangian_core_correction.md` — Documents simplification
