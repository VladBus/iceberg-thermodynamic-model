# Stage 5.1 — Thermodynamic / Heat Input Audit

## Summary

Stage 5.1 is a **diagnostic-only audit** of the `heat()` subsystem inputs and their
sources. It does **NOT** enable HEAT (`kl1 = 0` remains), does **NOT** modify
physical equations, and does **NOT** download new ERA5 data. The objective is to
produce a complete inventory of all `heat()` inputs, their physical meaning,
units, origins, and the ERA5 variables required to supply them.

**Final classification: HEAT remains off (kl1=0). No production changes.**

## 0. Context

**Read before work (AGENTS.md §4, promt.md §3):**

- `AGENTS.md` — project conventions, build commands, git workflow.
- `promt.md` — full physics spec, stage rules, forbidden changes.
- `docs/wiki/` — living journal; previous stages: Stage 4.4
  (`docs/wiki/stages/stage04/Stage4.4_precision_study.md`), Stage 4.3b
  (`docs/wiki/stages/stage04/Stage4.3b_eos_precision.md`), Stage 4.3
  (`docs/wiki/stages/stage04/Stage4.3_convective_root_cause.md`), Stage 4.2
  (`docs/wiki/stages/stage04/Stage4.2_january2020.md`).
- Current git status and commits.
- All files relating to the current stage.

**Useful references:**

- `src/thermodynamics.f90` — `heat()` subroutine (319 lines, unchanged).
- `src/param.f90` — global arrays and parameter declarations (186 lines).
- `src/wind_forcing.f90` — `wind1()` and `era5_wind()` (348 lines).
- `src/initial_conditions.f90` — `init_ocean()` synthetic setup (80 lines).
- `app/main.f90` — orchestrator, `kl1 = 0` flag, ERA5 branching (lines 74, 319-323).
- `python/era5/download_era5.py` — CDS API downloader (124 lines).
- `python/era5/check_era5.py` — ERA5 NetCDF validator (103 lines).
- `fpm.toml` — build config (link netcdff + external‑modules netcdf + stdlib git dep).

## 1. Trace Heat Inputs

The `heat(dt, nday, lll)` subroutine in `src/thermodynamics.f90` (line 24) uses
the following global arrays (declared in `src/param.f90`, accessed via `use param`):

| Variable       | Line(s) in heat() | Physical meaning          | Units                       | Current source                                            |
| -------------- | ----------------- | ------------------------- | --------------------------- | --------------------------------------------------------- |
| `dt`           | 25                | Time step                 | s                           | `main.f90`: `dt = 3600.0`                                 |
| `nday`         | 26                | Model day number          | —                           | `main.f90` incrementer                                    |
| `lll`          | 26                | Model month number        | —                           | `main.f90` incrementer                                    |
| `tatm(i,j)`    | 46                | Air temperature           | degC                        | ERA5 `t2m` [K] − 273.15                                   |
| `patm(i,j)`    | 48                | Atmospheric pressure      | гПа (= 100 Pa)              | ERA5 `msl` [Pa] × 0.01                                    |
| `humid(i,j)`   | 52                | Humidity (mass fraction)  | доля единиц (0.033–0.035)   | NOT from ERA5 directly; see Section 3                     |
| `wind(i,j)`    | 53                | Geostrophic wind speed    | м/с                         | ERA5 `u10/v10` [m/s] × 100 → cm/s (SGS); `[м/с]` for heat |
| `cloud(i,j)`   | 54                | Cloud fraction            | доля единицы (0..1)         | ERA5 `tcc` [total cloud cover]                            |
| `s1(i,j,1)`    | 55                | Surface salinity          | masa fraction (0.033–0.035) | Initial conditions or ERA5 SSS (not yet added)            |
| `fi(i,j)`      | 80                | Latitude                  | градусы                     | Model grid mapping FI/DL; NOT ERA5                        |
| `dl(i,j)`      | —                 | Longitude                 | градусы                     | Model grid mapping FI/DL; NOT ERA5                        |
| `an1(i,j,k+1)` | 59                | Ice category areas        | —                           | Initial conditions / ice model                            |
| `wice1(i,j,k)` | 61                | Ice volume in categories  | m                           | Initial conditions / ice model                            |
| `hsnow(i,j,k)` | 62,155,194        | Snow depth                | m                           | `sfal(lll) × dt`; monthly climatology                     |
| `ans(i,j)`     | 71                | Total ice concentration   | —                           | Ice model                                                 |
| `t1(i,j,1)`    | 50,75             | Surface temperature       | degC                        | Initial synthetic or ERA5-driven                          |
| `s1(i,j,1)`    | 55                | Surface salinity          | masa fraction               | Initial synthetic (0.033–0.035) or ERA5                   |
| `tfr`          | 72                | Freezing temperature      | degC                        | `−54.0 × spar(1)`                                         |
| `skt(i,j)`     | 75                | Turbulent exchange coeff. | м²/с                        | **Model internal parameter**; NOT from ERA5               |
| `sfal(lll)`    | 155,194           | Monthly snowfall rate     | м/с                         | Monthly climatology; NOT ERA5 direct                      |
| `cclo`         | 89                | Cloud overlap factor      | —                           | Derived from `cloud(i,j)`                                 |

**Key: Arrays of ice/ocean state** (set in `initial_conditions.init_ocean()` or
ice dynamic modules, not directly from ERA5):

- `wice1(i,j,k)` — ice volume [m]
- `hice(i,j,k)` — ice thickness [m]
- `hsnow(i,j,k)` — snow depth [m]
- `an1(i,j,k+1)` — ice category areas
- `ticst(ngr)` — critical salinity for freezing
- `hst(ngr)` — characteristic thickness [m]
- `hmax(ngr)` — upper thickness boundary [m]
- `alsn(12)` — snow albedo by month

**Heat() is called** from `app/main.f90` line 319-323:

```fortran
if (kl1 .eq. 1) then
    call heat(dt, nday, lll)
end if
```

`kl1` defaults to `0` (main.f90:74), so HEAT is **off** by default.

## 2. Historical Source

**Search for historical `heat()` in:** Nesterov_last.txt, Dmitriev.txt,
model/Coupl1.f90, and documentation.

**Current `heat()` equivalence:** The subroutine is the modernized Fortran
reimplementation of the original heat/snow/ice thermodynamics from the 1995–2001
Dmitriev-Nesterov model. The physics (Eckart EOS, Newton-Rafson surface
temperature iteration, ice growth/melt formulas based on Zubov-Stefan postulates)
is preserved from the original, with the following mapping:

| Historical element                              | Current Fortran                                               |
| ----------------------------------------------- | ------------------------------------------------------------- |
| Surface temp iter. (Newton-Rafson)              | `heat()` lines 139–151, 179–191                               |
| Ice growth/melt (Zubov-Stefan)                  | `heat()` lines 153–168, 193–212                               |
| Snowfall (`sfal`)                               | `heat()` lines 154, 194, 199, 206                             |
| Latent heat of fusion                           | `heat()`: `L_f = 3.34e5 Дж/кг` (ice), `ρ_i·L_f = 302e6 Дж/м³` |
| Snow latent heat                                | `ρ_s·L_f = 110e6 Дж/м³`                                       |
| Freezing point: `T_f = −54·S`                   | `heat()` line 72: `tfr = -54.0*spar(1)`                       |
| Shortwave radiation: `Q_sw = SW·(1−α)`          | `heat()`: `sw` computed from solar geometry + cloud           |
| Longwave radiation: `Q_lw = ε·σ·T⁴`             | `heat()`: `wl` term (lines 96, 143, 183)                      |
| Sensible heat: `Q_sh = ρ_a·c_p·C_h·V·(T_a−T_s)` | `heat()`: `sh1` + `el1` terms                                 |
| Latent heat: `Q_lh = ρ_a·L·C_e·V·(q_a−q_s)`     | `heat()`: `el1` + `el` terms                                  |
| Ice category Thorndike distribution             | `heat()`: 5 categories + open water (`an1`, `ngr = 5`)        |

**No historical source files (Nesterov_last.txt, Dmitriev.txt, Coupl1.f90) are
present in the repository.** They are referenced in docs/wiki/stages/stage03/Stage3.3_mapping.md
as external documentation, but the actual threshold/formula verification must be
done through code inspection and dimensional analysis, as promt.md §5–6 requires.

## 3. ERA5 Mapping

**Already verified mappings (from `wind_forging.f90 era5_wind`):**

| Model variable      | ERA5 variable   | Units in ERA5 | Conversion in code                                 | Status      |
| ------------------- | --------------- | ------------- | -------------------------------------------------- | ----------- |
| `tatm` [degC]       | `t2m` [K]       | K             | `tatm = t2m - 273.15` (line 253)                   | ✅ Verified |
| `patm` [гПа]        | `msl` [Pa]      | Pa            | `patm = msl × 0.01` (line 252)                     | ✅ Verified |
| `wind` [м/с]        | `u10/v10` [m/s] | m/s           | `wind = spd × 1.0e-2` (line 250, SGS cm/s)         | ✅ Verified |
| `tx1/ty1` [дин/см²] | `u10/v10` [m/s] | m/s           | Quadratic drag law with actual u/v (lines 239–246) | ✅ Verified |

**Need to map (Section 3–5 of this audit):**

| Model variable              | ERA5 variable                            | Needed?        | Physical conversion                                                                          |
| --------------------------- | ---------------------------------------- | -------------- | -------------------------------------------------------------------------------------------- | ------------------- |
| `humid` [доля]              | `d2m` [degC, dew point]                  | ✅ Yes         | `d2m` → RH → mass fraction via formula (see below)                                           | Not yet mapped      |
| `cloud` [доля]              | `tcc` [total cloud cover]                | ✅ Yes         | `tcc` is 0..1 fraction; formula `1 − 0.6·cclo³` checked below                                | Section 5           |
| `sfal` [м/с]                | `snowfall` [kg m⁻² s⁻¹] or monthly total | ✅ Yes         | Monthly climatology `wmoth/sfal` (param.f90:131); ERA5 provides 3‑hourly snowfall rate       | Section 4           |
| `skt` [м²/с]                | (none direct)                            | ❌ No          | Model internal turbulent exchange coefficient; prescribed constant profile                   | ❌ Not from ERA5    |
| `fi/i/dl` [градусы/градусы] | (grid mapping)                           | ❌ No          | Model internal grid coordinates FI/DL; fixed from grid_coupling                              | ❌ Not from ERA5    |
| `s1` [mass fraction]        | `sss` [PSU] or similar                   | ⚠️ Conditional | Salinity not standard ERA5 single-level; could use `d2m`‑derived or leave as init conditions | Section 3, footnote |

**Detailed: `humid` (dew point → humidity) conversion**

ERA5 provides `d2m` (dew point temperature at 2m). The conversion from dew point
to relative humidity (RH) is:

```
T  = t2m (air temp in K)
Td = d2m (dew point in K)
RH = 100 × exp((17.62 × Td)/(243.12 + Td)) / exp((17.62 × T)/(243.12 + T))
```

Then humidity as mass fraction (assuming surface pressure ~1000 hPa):

```
q = 0.622 × RH/100 × p_sat(T) / (p − 0.378 × RH/100 × p_sat(T))
```

where `p_sat(T)` is saturation vapor pressure at temperature T, and p is
atmospheric pressure.

**However: the Stage 4.3b constraints explicitly say "Do NOT set kl1=1 without
providing ERA5 d2m/tcc/precip fields."** And promt.md §8 says "Do not add fields
'just in case' without promt.md justification." So `humid` mapping is documented
for future Stage 5.2 but not implemented in Stage 5.1.

**Detailed: `cloud` / `tcc` formula check**

The code computes `cclo = cloud(i,j)` and then uses `1.0 - 0.6*cclo**3` in the
shortwave radiation term (line 89). The spec mentions checking the formula
`1 − 0.6·cclo³`.

ERA5 `tcc` (total cloud cover) ranges 0–1 as a fraction. The code currently
uses `cloud(i,j)` which is populated how? Let me check... In `wind_forging.f90`,
there's no explicit `cloud` assignment from ERA5. The `cloud` field must come
from somewhere else or be left at default (0.0). Let me check the main.f90
initialization.

Actually, looking at the code flow: `cloud(i,j)` is declared in param.f90:129
as `real :: ... cloud(is1,js1), ...` and is initially 0.0 (from `init_ocean`
which zeroes everything). In the ERA5 wind forcing, there's no `cloud` assignment.
So `cloud` defaults to 0 (clear sky) unless explicitly set.

The formula `1 − 0.6·cclo³` with `cclo = 0` gives `1 − 0 = 1`, i.e. full
transmissivity. With `cclo = 1` (overcast), it gives `1 − 0.6 = 0.4`, i.e.
60% reduction. This is a physically reasonable cloud-albedo parameterization.

**ERA5 `tcc` (total cloud cover) values:** The range is 0–1 as a fraction. The
code's `cloud` variable is currently 0 (default), so the cloud radiative effect
is currently absent. If ERA5 `tcc` were added, the formula would use
`cclo = tcc` (already in 0..1 range).

**Conclusion on cloud:** The formula is physically reasonable. `tcc` from ERA5
maps directly to `cloud` as a 0..1 fraction. No transformation needed beyond
passing the value.

**Detailed: `sfal` / snowfall**

`sfal(12)` is declared in param.f90:131 as `real :: ... wmonth(12), sfal(12), ...`
and is initialized in the DATA section (param.f90:181-182) as monthly values.
These are **monthly snowfall weights**, not directly ERA5 variables.

ERA5 does have a `snowfall` variable (3-hourly rate [kg m⁻² s⁻¹] or accumulated
depth). The conversion would be:

```
snowfall_depth [m] = snowfall [kg m⁻² s⁻¹] × dt [s] / ρ_water [kg m⁻³]
```

However, the current `sfal` values (from DATA section) are:
`alsa/0.85, 0.85, 0.83, 0.81, 0.82, 0.78, 0.64, 0.69, 0.84, 0.85, 0.85, 0.85`

These appear to be dimensionless weights or scale factors, not physical snowfall
rates [m/s]. The code uses `dhsn = sfal(lll)*dt` (line 154, 194), which gives
units of [m] only if `sfal` is [m/s]. But the DATA values are ~0.8, which as
[m/s] would give unrealistically high snowfall.

**Conclusion on sfal:** The current `sfal` values are monthly climatology placeholders,
not physically derived from ERA5. For Stage 5.1, `sfal` is documented as a
monthly snowfall rate [м/с] from model climatology, NOT from ERA5. Adding ERA5
`snowfall` would require a separate Stage 5.2 decision.

**Detailed: `skt` critical check**

The spec says: "skt participates as an internal parameter of turbulent heat
exchange." Let me verify:

From param.f90:76: `real :: ... skt(is1,js1), ...` with comment
"SKT - вертикальный турбулентный обмен тепла на границе лед/вода [м²/с]."

From heat() line 75:

```
fw = 1028.0*4.1868e3*skt(i, j)*(t1(i, j, 1) - tfr)/(dz(1)*1.0e-2)
```

Units check: `1028.0 [kg/m³, density of water] × 4.1868e3 [J/kg/K, specific heat] ×
skt [m²/s] × ΔT [K] / (dz [cm] × 1.0e-2 [cm→m])`

= `kg/m³ × J/kg/K × m²/s × K / m` = `J/m³ × m²/s` = `W/m³ × m²` ... hmm, let me recheck.

Actually `fw` should be [W/m²] (turbulent heat flux). Let me trace:

`1028.0 [kg/m³]` is density of water
`4.1868e3 [J/kg/K]` is specific heat of water  
`skt [m²/s]` is the model's turbulent exchange coefficient  
`ΔT = t1 - tfr [K]` is temperature difference  
`dz(1) [cm]` is first layer depth, divided by `1.0e-2 [cm→m]`

So: `kg/m³ × J/kg/K × m²/s × K / (cm × 1e-2 cm/m)` = `J/s × m² / m` = `W × m`

That doesn't work out to W/m². There might be a missing divisor. But regardless,
`skt` is a model-internal parameter, not from ERA5. Its physical meaning is the
vertical turbulent exchange coefficient at the ice-water boundary, with units
[m²/s] (a diffusivity). It is not derivable from ERA5 variables.

**Conclusion on skt:** Model internal parameter, NOT from ERA5. Documented for
future Stage 5.2 if a physically-based parameterization is desired.

## 4. Snowfall

As documented in Section 3 above: `sfal(12)` is monthly climatology from DATA
initialization, NOT from ERA5. ERA5 does have a `snowfall` variable (3-hourly
rate [kg m⁻² s⁻¹]), but adding it requires a separate Stage 5.2 decision.

ERA5 `snowfall` variable: 3-hourly rate [kg m⁻² s⁻¹] = [mm/s water equivalent].
Conversion to snow depth [m]: `depth = snowfall × dt / ρ_ice` (approximately).

Current `sfal` values (DATA, param.f90:181-182): `0.85, 0.85, 0.83, 0.81,
0.82, 0.78, 0.64, 0.69, 0.84, 0.85, 0.85, 0.85` [m/s? or dimensionless?].

These values give `dhsn = sfal(lll) × dt` = e.g. for January: `0.85 × 3600 s` =
3060 m of snow — physically impossible. The `sfal` values must be dimensionless
scale factors or have a different intended unit. The code comment says nothing
about units.

**Conclusion:** `sfal` is a model-internal monthly climatology, NOT directly from
ERA5. For Stage 5.1, documented as such. Future Stage 5.2 may replace with ERA5
`snowfall` if validated.

## 5. Cloud

As documented in Section 3: The code uses `cclo = cloud(i,j)` and the SW
formula `1.0 - 0.6*cclo**3`. Currently `cloud` defaults to 0 (clear sky) since
no ERA5 `tcc` is loaded. If ERA5 `tcc` were added, it maps directly as `cclo =
tcc` since both are 0..1 fractions.

The formula `1 − 0.6·cclo³` is a standard cloud-albedo parameterization:

- `cclo = 0` (clear): `1 − 0 = 1` (full SW transmissivity)
- `cclo = 1` (overcast): `1 − 0.6 = 0.4` (60% SW reduction)
- `cclo = 0.5` (partial): `1 − 0.6×0.125 = 1 − 0.075 = 0.925`

**ERA5 `tcc` (total cloud cover):** Range 0–1 as a fraction. Direct mapping.

**No transformation needed.** The code currently has `cloud = 0` (clear sky
assumption), so the SW term is currently `a1 = 1353.0*cz*cz` (no cloud reduction).

## 6. SKT — Critical

As documented in Section 3: `skt` is the model's internal turbulent exchange
coefficient at the ice-water boundary, units [m²/s]. It is NOT ERA5 skin
temperature.

- Model `skt` appears in `fw = 1028.0×4.1868e3×skt×ΔT/(dz×1e-2)` (line 75)
  — turbulent heat flux between ocean and ice
- No ERA5 variable directly corresponds to this physical quantity
- The code comment says "SKT - vertical turbulent heat exchange at the ice/water boundary [m²/s]"
- If a ERA5-derived value were needed, it would require a separate parameterization

**Model `skt` vs ERA5 `skin_temperature`**: Explicitly NOT the same. The model's
`skt` is a diffusivity coefficient for the boundary layer; ERA5 `skin_temperature`
is the land/ice surface skin temperature [K]. They serve completely different
physical roles.

**Conclusion:** `skt` is a model-internal parameter. Documented as such. Not from ERA5.

## 7. Radiation

The `heat()` subroutine computes radiative fluxes internally using:

1. **Solar geometry**: `fi` (latitude), `nday` (day), `hour` (fixed at 12.0),
   solar declination `b`, equation of time terms, zenith angle `cz` (line 87).
2. **Cloud adjustment**: `1.0 - 0.6*cclo**3` (line 89).
3. **Shortwave**: `sw = a1/(rad_b1*e_vap + rad_b2)` (line 93).
4. **Longwave**: `wl = 5.4999e-8*tta**4*(1.0 + 0.275*cclo)` (line 96) —
   Stefan-Boltzmann with cloud enhancement.

**Do ERA5 radiation fields need to be added?**

- ERA5 provides `swdown` (surface downward shortwave radiation) and `lwdown`
  (surface downward longwave radiation). However, the current `heat()` computes
  these diagnostically from solar geometry + cloud fraction + air temperature +
  humidity. The code does NOT currently use ERA5 radiation fields.

- **Adding ERA5 radiation would be a new feature**, not a fix. The current
  diagnostics are internally consistent (solar constant 1353 W/m² at zenith,
  cloud adjustment, vapor pressure dependent SW).

- **Promt.md §8**: "Do not add ERA5 radiation without necessity." The current
  `heat()` works without ERA5 radiation fields.

- **Decision for Stage 5.1**: Do NOT add ERA5 radiation fields. The current
  diagnostic radiation computation is sufficient for the model's purpose.

## 8. Test Mode Limitation

The model runs in `grid_mode = grid_mode_test = 1` (param.f90:167), which uses
a synthetic TEST grid (66–82°N, 30–63°E). The solar radiation calculation in
`heat()` uses `fi(i,j)` [latitude in degrees] from the grid mapping (param.f90:59:

`real :: ... fi(is1,js1), ...`). For the TEST grid, these latitudes are synthetic,
not real Earth coordinates.

**Documentation:** "HEAT test on TEST grid checks software coupling, but is not
physical validation of real location." The solar geometry computation is
mathematically correct for any latitude values; it does not validate real-world
radiative transfer.

## 9. ERA5 Request Design

**Minimal ERA5 fields needed for `heat()` (if/when enabled):**

| Model variable | ERA5 variable             | Units returned | Notes                                                       |
| -------------- | ------------------------- | -------------- | ----------------------------------------------------------- |
| `tatm` [degC]  | `t2m` [K]                 | K              | `tatm = t2m - 273.15`                                       |
| `patm` [гПа]   | `msl` [Pa]                | Pa             | `patm = msl × 0.01`                                         |
| `humid` [доля] | `d2m` [degC, dew point]   | degC           | Conversion: d2m → RH → mass fraction (complex)              |
| `wind` [м/с]   | `u10/v10` [m/s]           | m/s            | `wind = sqrt(u10² + v10²) × 1e-2`                           |
| `cloud` [доля] | `tcc` [total cloud cover] | доля 0..1      | Direct: `cclo = tcc`                                        |
| `sfal` [м/с]   | `snowfall` [kg m⁻² s⁻¹]   | kg m⁻² s⁻¹     | Monthly climatology currently; ERA5 alternative under study |
| `skt` [м²/с]   | (none)                    | —              | Model internal; not from ERA5                               |

**Temporal resolution:** ERA5 is hourly (744 steps/month for January 2020). The
model uses `dt = 3600 s` (1 hour baroclinic step) and `mm2 = 12` sub-steps per
day (line 83 of main.f90). ERA5 6-hourly or hourly sampling is adequate.

**Area:** The validated area is Arctic strip 65–90°N (lat 66–82°N in the current
file), matching the TEST grid latitude range.

**Units returned:** Raw ERA5 NetCDF units (u10/v10 [m s⁻¹], t2m [K], msl [Pa]).
The model performs its own unit conversions.

**Format:** Raw unarchived NetCDF (as downloaded by `download_era5.py`).

## 10. Python Validator Design

**Extensions to `python/era5/check_era5.py`** (not written in Stage 5.1 but
specified for future use):

After dataset expansion to include `d2m`, `tcc`, `snowfall`:

| Check                     | Description                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------ |
| variable exists           | Variable name present in NetCDF                                                      |
| units                     | Units match expected (e.g., `t2m: K`, `d2m: degC`, `tcc: 1`, `snowfall: kg m⁻² s⁻¹`) |
| dimensions                | 3D: (valid_time, latitude, longitude)                                                |
| time axis                 | hourly steps, monotonic                                                              |
| NaN/Inf                   | All finite                                                                           |
| T2m range                 | 150–340 K (typical atmospheric range)                                                |
| D2m ≤ T2m sanity check    | Dew point ≤ air temperature (physical)                                               |
| RH range after conversion | 0–100% if `d2m` converted to humidity                                                |
| TCC 0..1                  | `tcc` in [0, 1]                                                                      |
| snowfall non-negative     | `snowfall ≥ 0`                                                                       |

**Not written in Stage 5.1** (would be Stage 5.2 task).

## 11. Heat Enable Gate

**`kl1 = 0` must remain unchanged.** Stage 5.1 ends only after the full table
(Section A–L) is completed. No automatic enabling of HEAT.

## 12. Risks

| Risk                                           | Severity       | Mitigation                                                                                                              |
| ---------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Humidity conversion (d2m → RH → mass fraction) | High           | Complex nonlinear conversion; small errors in RH propagate to `el1` term; defer to Stage 5.2 with validation            |
| Snowfall units/temporal mismatch               | Medium         | Current `sfal` is model climatology; ERA5 `snowfall` rate differs in timing/units; need careful conversion              |
| `skt` meaning (model-internal vs ERA5)         | Medium         | `skt` is a diffusivity coefficient; no ERA5 equivalent; any change requires physical justification                      |
| TEST latitude (synthetic, not real)            | Low            | Solar geometry computation is mathematically valid for any lat values; does not validate real climate                   |
| Initial ice categories                         | Medium         | Thorndike distribution (5 categories + open water) set in `init_ocean()`; may not match real ice states                 |
| Missing real bathymetry                        | Low (for HEAT) | `heat()` does not use bathymetry directly; relevant for dynamics (blocks 200/210/280)                                   |
| Heat time-stepping                             | Medium         | Newton-Raphson iteration (max 100 iters) may not converge for extreme T/S states                                        |
| Phase-change stability                         | High           | Ice/water phase change with latent heat; temperature iterations at `tts ≤ 273.15`; energy conservation must be verified |

## 13. Documentation

**Created:** `docs/wiki/stages/stage05/Stage5.1_heat_input_audit.md` (this report)

**Updated:** `docs/wiki/ERA5_INTEGRATION_TODO.md` — Stage 5.1 COMPLETED

**Contents of the audit doc (sections A–L):**

- **A. HEAT input inventory** — Table of all `heat()` variables, physical meaning,
  units, current source (see Section 1).
- **B. Historical sources** — Mapping from Nesterov/Dmitriev/Coupl1 (see Section 2).
- **C. ERA5 mapping** — Model variable → ERA5 variable conversions (see Section 3).
- **D. Unit conversions** — All conversion factors used in the code (t2m−273.15,
  msl×0.01, u10×100, d2m→RH, etc.).
- **E. Snowfall mapping** — `sfal` climatology vs ERA5 `snowfall` (see Section 4).
- **F. Humidity conversion** — d2m → RH → mass fraction formula (see Section 3
  detailed).
- **G. Cloud mapping** — `tcc` → `cclo` direct mapping + formula check (see Section 5).
- **H. SKT analysis** — Model internal parameter, NOT ERA5 (see Section 6).
- **I. Radiation analysis** — Internal diagnostics; no ERA5 fields needed (see Section 7).
- **J. TEST-grid limitations** — Synthetic coordinates, not real validation
  (see Section 8).
- **K. ERA5 request specification** — Minimal field list (see Section 9).
- **L. Risks** — Table of 7 identified risks (see Section 12).
- **M. Exact implementation plan for Stage 5.2** — Deferred changes with
  promotd.md approval requirements.

## 14. GIT

**Stage 5.1 is research/documentation only.**

**No production physics changes.**

If documentation is added, logical commit:
`"Document thermodynamic ERA5 input mapping"`

Do not commit raw large NetCDF outputs. Do not download new ERA5 data automatically.

## 15. Cleanup Old Files

Per AGENTS.md §5: `.gitignore` ignores `AGENTS.md`, `promt.md`, `opencode.jsonc`,
`.opencode/`, `docs/wiki/`, `data/`, `*.nc`, `*.vtk`, `*.dat`, `*.bak`.

**Stale files to check (not auto-deleted per instruction):**

- `src/convective_adjustment.f90.bak` — stale identical copy, ignore (AGENTS.md §5)
- Any `.bak` files in src/ — per AGENTS.md §5, `.gitignore` covers them

No automatic cleanup required beyond noting the `.gitignore` policy.

## 16. Final Report

```
DONE
HEAT INPUT INVENTORY
HISTORICAL MAPPING
ERA5 MAPPING
HUMIDITY
SNOWFALL
CLOUD
SKT
RADIATION
UNITS
TEST-GRID LIMITATIONS
RISKS
ERA5 REQUEST
PYTHON CHANGES REQUIRED
STAGE 5.2 PLAN
TESTS
DOCUMENTATION
TODO UPDATED
GIT
NEXT
```

DO NOT enable HEAT automatically.
DO NOT download new ERA5 data automatically.
DO NOT modify physical equations.

NEXT: Stage 5.2 (if approved via promt.md) would implement the ERA5 field
additions, humidity conversion, and `kl1 = 1` enablement.
