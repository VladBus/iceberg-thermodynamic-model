# Stage 7.7 — Phase 1: Initial Ocean T/S Forensic Audit

**Classification: A (audit)** — the complete current ocean-T/S initialization
chain is documented below, end to end. No external ocean T/S file exists in the
repository; the initial state is entirely synthetic and generated in Fortran.

**Date:** 2026-08-27

---

## 1. Executive summary of the audit

- The **only** source of initial ocean temperature/salinity is the subroutine
  `init_ocean()` in `src/initial_conditions.f90`. It is deterministic and fully
  synthetic — it does **not** read any file.
- A repository-wide search (`data/input/*`, `src/`, `app/`) found **no** existing
  file with initial ocean T/S (`*ocean*`, `initial*t*`, `*.t`, `T/S`), no legacy
  temperature/salinity input file, and no NetCDF reader for ocean state. The only
  NetCDF input is ERA5 atmospheric forcing (`netcdf_input.f90`).
- The model state variables are **`t2`/`s2`** (3-D, `is1×js1×ks = 133×105×18`),
  at **T-points** of the Arakawa-B grid. `t1`/`s1` are previous-time-step buffers.
- The **only intended scientific change** for Stage 7.7 is therefore the body of
  `init_ocean()` (or a new file-based reader used in its place) — no physics,
  EOS, grid, or ice code needs to change.

## 2. Current input source

```fortran
! src/initial_conditions.f90 (lines 20–86)
subroutine init_ocean()
    t1 = 0.0; t2 = 0.0     ! [°C]
    s1 = 0.0; s2 = 0.0     ! [массовая доля]
    u1 = 0.0; u2 = 0.0     ! [см/с]
    v1 = 0.0; v2 = 0.0
    w = 0.0; ro = 0.0; up1=0.0 ... ym2 = 0.0
    do k = 1, ks
      depth_ratio = (k-1)/(ks-1)               ! 0 (surface) .. 1 (bottom)
        do j = 1, js; do i = 1, is
          if (kt1(i,j) > 0 .and. k <= kt1(i,j)) then
            t2(i,j,k) = 15.0 - 13.0*depth_ratio          ! 15 °C → 2 °C
            s2(i,j,k) = 0.033 + 0.002*depth_ratio        ! 0.033 → 0.035
            if (50<i<80 .and. 40<j<60 .and. k<=5) t2 += 8.0   ! synthetic heat-spot
            u2 = 0.20  [см/с]; v2 = 0.10 [см/с]          ! weak drift
          else
            t2 = 0.0; s2 = 0.0; u2 = 0.0; v2 = 0.0        ! land / below sea floor
          endif
        end do; end do
    end do
```

Called from `app/main.f90:307`, **after** `coup1()` (line 238) and `ikuv()`
(line 241) and after the ice initialization (`1_k.ice → redis()`, lines 272–304),
**before** `eos_diag()` (line 311) and `write_nc(results_day_00.nc)` (line 314).

## 3. Current file format

None. Purely code-generated analytic fields.

## 4. Current variables

| Symbol         | Shape            | Meaning / units                                   |
| -------------- | ---------------- | ------------------------------------------------- |
| `t1`, `t2`     | `(is1, js1, ks)` | ocean temperature [°C] (previous / current step)  |
| `s1`, `s2`     | `(is1, js1, ks)` | salinity [mass fraction, 0.033–0.035] (not PSU)   |
| `ro`           | `(is1, js1, ks)` | density anomaly = ρ − 1.02 [g/cm³]                |
| `u1/u2, v1/v2` | `(is1, js1, ks)` | velocity [cm/s] (not initialised from ocean data) |

## 5. Dimensions

- `is1 = 133`, `js1 = 105`, `ks = 18` (`src/param.f90:33–38`).
- Active inner domain: `i = 1…is (132)`, `j = 1…js (104)`; ghost row/col
  `i=is1`, `j=js1` populated by the whole-array zeroing, i.e. land.
- The wet/ocean mask is `kt1(i,j)` (from `coup1()`): **`kt1 = 0` ⇔ land**;
  `kt1 = k` ⇔ column has wet Z-levels `1…k`. `kt1` is the _second-pass_ value
  computed at `grid_coupling.f90:302–313` (the first-pass value in the
  depth-modification block is stale and overwritten — do not rely on it).

## 6. Vertical convention (Z-levels)

`src/param.f90:310–312` (`data z/...`, **cm**, centre depths of 18 levels):

| k      | 1    | 2     | 3     | 4     | 5     | 6     | 7     | 8     | 9     |
| ------ | ---- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| z [cm] | 250  | 500   | 1000  | 1500  | 2000  | 2500  | 3000  | 4000  | 5000  |
| z [m]  | 2.5  | 5     | 10    | 15    | 20    | 25    | 30    | 40    | 50    |
| k      | 10   | 11    | 12    | 13    | 14    | 15    | 16    | 17    | 18    |
| z [cm] | 7500 | 10000 | 15000 | 20000 | 25000 | 30000 | 40000 | 50000 | 60000 |
| z [m]  | 75   | 100   | 150   | 200   | 250   | 300   | 400   | 500   | 600   |

- **Positive downward**, centre-of-layer values, top-of-water at z=0.
- `dz(1) = z(1)`; `dz(k) = z(k) − z(k−1)` (layer thickness, cm).
- `dz1(1) = 0.5·(z(2)+z(1))`; `dz1(k) = 0.5·(z(k+1)−z(k−1))`;
  `dz1(ks) = 0.5·(z(ks)−z(ks2))` (half-layer thicknesses, cm).
  Both computed in `coup1()` (`grid_coupling.f90:273–296`).
- The layer centres are **2.5…600 m**: the model's vertical extent is capped at
  **600 m** (z(18)=60000 cm). The stale comment “250 m…6000 m” in `param.f90:31`
  is wrong; the `data z/` statement is authoritative. 1,255 cells on the real
  grid are deeper than 600 m (known, preserved; see Stage 7.6A).
- `kt1(i,j) = max{ k : z(k) ≤ HT(i,j) }` where `HT(i,j)` is the model depth in
  **cm** (`= 100 × hhh.bar index`, floored to 3 m minimum; cells with
  5 < index ≤ 10 are clamped to 10; see `grid_coupling.f90:96–114`).

## 7. Units

| Quantity        | Model internal          | NetCDF output (`netcdf_output.f90`)            |
| --------------- | ----------------------- | ---------------------------------------------- |
| Temperature     | `t2/t1` [°C]            | `temperature [K]` = t2 + 273.15 (`:409`)       |
| Salinity        | `s2/s1` [mass fraction] | `salinity_mass_fraction [kg/kg]` = s2 (`:427`) |
| Density anomaly | `ro` [g/cm³] = ρ−1.02   | `density_anomaly [kg m-3]` = ro×1000 (`:432`)  |
| Depth           | `z/dz/dz1/ht` [cm]      | `levels [m]`, `water_column_levels`            |

- Salinity is **mass fraction (kg/kg)**, NOT practical salinity units;
  `0.033 ≈ 33 g/kg ≈ 33 PSU`. The Eckart EOS internally scales S by 10⁻²
  coefficients, so converting external PSU → fraction is `S_frac = S_PSU / 1000`.
- Depths are CGS (cm) internally; conversion to SI only at output boundary.

## 8. Indexing / grid-point location

- T/S/ρ live **at T-points** of the Arakawa-B grid (`fi/dl` at T-points,
  `KOORD.DAT`). All distance computations for advection (advt/advs) read
  `i±1`/`j±1` ghosts, but the boundary rows/columns are land, so sea-only
  initialization needs no special ghost treatment.
- `u1/u2/v1/v2` are at U/V points and are currently set to a constant drift
  (0.20/0.10 cm/s); Stage 7.7 does **not** touch velocities (objective is T/S only).
- Indexing: `(i, j, k)` = (x, y, z); axes X ↔ j, Y ↔ i; Y inverted (j=1 = north).

## 9. Land / missing-value handling (current)

- Land: `ht = 8888.0` ⇔ `kt1 = 0`. `init_ocean()` sets **0.0** (never NaN) on
  land and below-sea-floor cells. `==` on reals is forbidden; epsilon
  `abs(x−8888.0) < 1e-8` is the canonical test.
- No missing-value machinery exists (nothing to do: the field is generated).

## 10. Interpolation

None at present. The synthetic T/S is written directly at T-points.

## 11. EOS call chain & density calculation

- `density_anomaly(t, s)` — Eckart, single precision
  (`src/equation_of_state.f90:55–68`):

```
aa = 1779.5 + (11.25 − 0.0745·t)·t − (3800.0 + 10.0·t)·s
bb = 5891.0 + 3000.0·s + (38.0 − 0.375·t)·t
ro = 1/(0.698 + aa/bb) − 1.02   [g/cm³]
```

- Called in:
  1. `eos_diag()` (`equation_of_state.f90:80–116`) — fills `ro(i,j,k)` on wet
     cells (`kt1>0, k≤kt1`) and prints min/max/mean; invoked at `main.f90:311`
     (day 0) and `:1047` (end).
  2. `convective_adjustment.f90` — `conv_adj()` reads `t2/s2`, mixes statically
     unstable interfaces with threshold `eps_density = 0.9e-7 g/cm³`, writes
     `t2/s2/ro` back. Guard: >1000 iterations ⇒ halt (float32 2⁻²³ residual).
- `ro` is **diagnostic only**: the baroclinic pressure gradient (`drx/dry`,
  `param.f90:81–82`) is disabled, so the initial T/S field does NOT feed the
  momentum equations in the current run configuration.

## 12. Hydrostatic initialisation

- There is **no explicit hydrostatic adjustment**. Initial "hydrostatic
  consistency" means: `ro` finite and physically plausible everywhere in wet
  cells; no reliance on baroclinic balance at t=0.
- The barotropic mode uses `ht`/`map1`/`y1,y2` and does not involve T/S.

## 13. Exact Fortran routines involved (init chain)

| Order | Call (main.f90:line)                 | Module / file               | Role                                                                      |
| ----- | ------------------------------------ | --------------------------- | ------------------------------------------------------------------------- |
| 1     | `setup_run_dirs` (112)               | `run_config.f90`            | run_id, output dirs, era5 path                                            |
| 2     | `datte()` (230)                      | `main.f90` (internal)       | nominal date 1998-04-16 (legacy, superseded by ERA5 clock)                |
| 3     | `coup1()` (238)                      | `grid_coupling.f90`         | `ht/hu/hv/map1/kt1/kk1/dz/dz1/fi/dl/fu/fv/idx/idy`                        |
| 4     | `ikuv()` (241)                       | `grid_masks.f90`            | `kush/kvsh/iku/ikv` masks                                                 |
| 5     | read `1_k.ice` (272–304) + `redis()` | `main.f90`, `ice_redis.f90` | initial ice categories                                                    |
| 6     | `init_ocean()` (307)                 | `initial_conditions.f90`    | **synthetic T/S + drift (this stage)**                                    |
| 7     | `eos_diag()` (311)                   | `equation_of_state.f90`     | `ro` from `t2/s2`                                                         |
| 8     | `write_nc(day_00)` (314)             | `netcdf_output.f90`         | day-0 snapshot                                                            |
| —     | per thermo step (425–699)            | `main.f90`                  | `t1=t2`→`heat()`→`redis()`→dynamics→`advs/advt`→`conv_adj()`→`eos_diag()` |

## 14. What Stage 7.7 must therefore deliver

1. A file-based realistic T/S initial state that fills `t1=t2`, `s1=s2` on the
   **same T-point wet cells** (`kt1>0, k≤kt1`) with identical **units**:
   T [°C], S [mass fraction = PSU/1000].
2. Land and below-sea-floor cells kept at **0.0** (never NaN); boundary ghost
   rows are land — no open-sea ghost special case exists.
3. Vertically on the 18 model levels (2.5…600 m centres), using local water
   depth per column; no interpolation across land; no silent extrapolation.
4. Zero NaN/Inf; finite `ro` via the _existing_ Eckart float32 EOS (unchanged).
5. Temperature representation: the EOS takes an in-situ-like temperature
   (T·S scale); external products carry potential temperature `thetao` — the
   equivalence error at ≤600 m is ≪ other errors and will be documented.

## 15. Files inspected

- `src/param.f90` (arrays, Z-level data, units)
- `src/grid_coupling.f90` (`coup1`, dz/dz1, ht/kt1/map1, depth modification)
- `src/grid_masks.f90` (`ikuv`)
- `src/initial_conditions.f90` (`init_ocean` — THE file to replace)
- `src/equation_of_state.f90` (Eckart `density_anomaly`, `eos_diag`)
- `src/convective_adjustment.f90` (`conv_adj`, `convect_column`, guard, residuals)
- `src/advection_3d_t.f90` / `advection_3d_s.f90` (advt/advs: read t2/s2)
- `src/thermodynamics.f90` (`heat`: top-layer t1/s1, Zubov freezing point)
- `app/main.f90` (init + main time-loop order)
- `src/netcdf_output.f90` (output units/conventions)
- `data/input/processed/grid/ibcao_model_grid.nc` (grid coords, depth, mask;
  EPSG:3996 polar stereographic, `lat`/`lon` coords at (i,j))
- Repository search for any existing ocean T/S file → **none found**.

## 16. Conclusion / next step

The audit conclusively scopes Stage 7.7: acquire a realistic January-2020 Arctic
T/S analysis, regrid it onto the T-point wet mask and the 18 Z-levels with the
units/conventions above, and load it through a new (or modified) initialization
path **without touching the physics**. Proceeding to Phase 2 (dataset selection).
