# Stage 12.6a — Lat/Lon Drift + iceberg_run + Real(8) Migration

**Status:** COMPLETE. **Base:** `43756d0` (12.5). **Decision:** D‑57.
**Scope:** geographic drift, standalone `iceberg_run`, real(8) state. No Stage 11
ocean code / reanalysis reader / provider / `app/main.f90` modified.

## 1. Real(8) migration (Transition doc §6.3)

`iceberg_state` fields `x, y, u, v, L, W, H, latitude, longitude, T_surface,
T_ice, time` are now **real(8)**; `mass` and `volume` were added (real(8),
bookkeeping). Rationale: energy ~1e14 J, a 1e6 J step is 1e‑8 relative — at the
float32 boundary 2⁻²³ ≈ 1.2e‑7. Compiled with generic real4/real8 interfaces
for the three procedures `main.f90` calls with state fields
(`get_ocean_profile`, `get_atmos_forcing`, `model_coords_to_indices`) plus
`model_coords_to_latlon`; float32 ocean/atmosphere/thermo-correlation
boundaries are preserved (inputs are float32). **`app/main.f90` untouched.**
Legacy tests compile unchanged; a few test-local helpers were promoted to
real(8) where they receive state fields.

## 2. Lat/lon drift (Transition doc §4)

Mode flag: `OCEAN_SOURCE=reanalysis` (env, read lazily) or explicit
`iceberg_set_latlon_mode(.true.)` for `iceberg_run`. In lat/lon mode:
```
dlat =  v·dt/R,   dlon = u·dt/(R·cosφ)        (R = 6371 km; stored in degrees)
```
`state%latitude/longitude` are authoritative; `x/y` are not updated and the
`model_coords_to_latlon` overwrite is **blocked**. Longitude is wrapped to
[−180,180]. In model mode the legacy `x += u·dt`, `y += v·dt` +
`model_coords_to_latlon` path runs unchanged. Analytic helper
`geographic_increment` is public and unit-tested.

## 3. Standalone `iceberg_run` (second `[[executable]]` in `fpm.toml`)

```
fpm run iceberg_run -- lat0 lon0 L W H days dt out.nc [daily.nc] [static.nc] [era5.nc]
```
- Reanalysis ocean via `ocean_forcing_configure(SRC_REANALYSIS, daily, static)`
  and `get_ocean_profile(..., time_sec)`; time = Unix epoch (2020‑01‑01 =
  1 577 836 800 s), daily snapshots linearly interpolated by the reader
  (sub-daily dt supported).
- **IBCAO grounding:** `coup1()` builds the IBCAO‑derived grid; the iceberg
  lat/lon → model indices via `latlon_to_model_coords`; bathymetry =
  `ht(i,j)·10⁻² m` (land 8888 excluded). If the point is shallower than the
  draft, the iceberg is grounded (no drift) — verified at 75N/20E (40 m cell,
  88.5 m draft → grounded).
- Optional ERA5: if a file is passed and `era5_open` succeeds, `get_atmos_forcing`
  is used; otherwise a constant cold atmosphere is applied (documented).
- Output NetCDF: `time, latitude, longitude, mass, draft, T_ice` (double).
- Missing `daily.nc`/`grid.nc` → prints **SKIP** and exits 0 (CI‑safe).

## 4. Tests (`test/test_iceberg_run.f90`, CI‑safe)

| Test | Result |
|---|---|
| T1 lat/lon analytic (75N, u=0.1 m/s, 1 day) | `dlon = 0.3002151048°` = analytic to **1e‑12**; `dlat=0` |
| T2 real(8) energy, 100×600 s (no melt) | `E0=E1=2.848300e14 J`, **relative drift 0.0** (<1e‑8); mass/volume 64‑bit |
| T3 lat/lon mode | `x = 0` unchanged; longitude advances; lat/lon primary |
| T4 time linearity | `dlon(3600) = 2·dlon(1800)` to 1e‑13 |
| T5 data | full `.nc` run SKIPs when data absent |

**End‑to‑end smoke run** (local data, 74N 17E, 100 m cube, 1 day, dt=3600):
25 records; lat range **4.89e‑4°**, lon range **2.34e‑3°**, mass
9.100e8 → 8.987e8 kg (**−1.18 %**), draft 88.51 → 88.32 m; NetCDF written.
(This point is 250 m deep; the 75N/20E 40 m cell is grounded by design.)

Full battery: **exit 0, STOP 0 = 78, 0 failed**; strict build
(`-Wall -Wextra -fcheck=all -ffpe-trap`) clean; CI green.

## 5. Known limitations (12.6a)

- **Constant atmosphere** unless an ERA5 file is supplied (standalone path);
  ERA5 hourly interpolation is available via the existing reader.
- No wave erosion (12.6b), no sea‑ice drag, no tides.
- Grounding uses the **nearest** IBCAO model cell (13.89 km); no sub-grid
  bathymetry, no grounding/un-grounding dynamics.
- Lat/lon drift uses a first‑order update; no midpoint/Heun position update yet.
- No re-gridding of the ocean under the moving iceberg beyond bilinear provider
  sampling at each position.
- Real(8) migration changes model-mode round-off (~1e‑6 level); tolerances in
  legacy tests were left as-is because all passed.
