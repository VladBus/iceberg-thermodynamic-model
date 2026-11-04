# Stage 12.6b — Wave Erosion (Bigg 1997) + Optional Stokes Drift

**Status:** COMPLETE (implementation + CI-safe tests; no real wave-forcing run).
**Date:** 2026-10-31
**Decision:** D-58 (see `docs/DECISIONS.md`)
**Base:** `9e18deb` (Stage 12.6a, D-57)
**Scope:** wave erosion and Stokes drift only. Sea-ice drag and tides remain
open Stage 12.6b items.

## 1. Physics and NEMO verification

The Bigg et al. (1997) wave-erosion rate used here is the NEMO-ICB form
(`release-4.0/src/OCE/ICB/icbthm.F90`, eqn. M.A8):

```fortran
zMe = MAX( z1_12*(zSST+2.)*zSs*(1._wp+COS(rpi*(zIC**3))), 0._wp) * z1_rday
```

i.e.

```text
m_wave = max( (1/12) (T_w + 2) S_s [1 + cos(pi c^3)], 0 ) / 86400   [m/s]
```

where `c` is sea-ice concentration (0–1), `T_w` is surface ocean temperature
(°C), and `S_s` is the sea state. Consequences:

- `c = 0` (open water): factor `1 + cos(0) = 2` → **maximum** erosion.
- `c = 1` (full cover): factor `1 + cos(pi) = 0` → **zero** erosion.

**Correction to the Stage 12.6b task text.** The Test-2 expectations in the
task text (`c=0 → 1 m/day`, `c=1 → 2 m/day`) are inverted relative to both
Bigg (1997) and NEMO. The implementation and tests follow NEMO/Bigg; the
inversion is recorded here rather than encoded in the model.

**Sea-state source.** NEMO derives `S_s` from wind
(`zSs = 1.5*sqrt(U) + 0.1*U`). This stage uses the transition-document
Douglas mapping from significant wave height (`Hs`), because the intended
Arctic WAM product provides `Hs`. This is a documented difference, not a
formula change: the `[1+cos(pi c^3)]` structure is identical.

## 2. Implementation

### 2.1 New module `src/wave_forcing.f90`

- `wave_forcing_configure(path)`: opens a regular lat/lon wave file with
  variables `Hs`, `Tp`, `dir`, `u_stokes`, `v_stokes` on
  `(time, latitude, longitude)`. Time is interpreted as hours since
  1950-01-01 (same convention as GLORYS12); out-of-range/absent files return
  `ok=.false.`.
- `get_wave_forcing(lat, lon, time_sec, Hs, Tp, dir, u_stokes, v_stokes, ok)`:
  bilinear in space + linear in time, 2×2×2 hyperslab; no extrapolation.
- `hs_to_sea_state(Hs)`: Douglas/WMO 3700 bins (0–8).
- `bigg_wave_melt(Ss, c, T_w)`: NEMO/Bigg rate, clamped `m >= 0`.
- `ICEBERG_WAVE_EROSION` / `ICEBERG_STOKES_DRIFT` gates (default OFF), plus
  TEST-ONLY constant forcing and gate setters for CI.

### 2.2 Coupling

- `src/iceberg_types.f90`: `ocean_profile%siconc`; diagnostics `m_wave`,
  `wave_mass_loss`.
- `src/iceberg_forcing.f90`: reanalysis profile stores provider `siconc`;
  model path sets `siconc = 0` (sea-ice coupling not wired).
- `src/iceberg_thermodynamics.f90`: `apply_wave_erosion` after surface melt;
  reduces `L` and `W` by `m_wave*dt` (not `H`), records `m_wave` and
  `wave_mass_loss = rho_i (L_old W_old - L_new W_new) H`.
- `src/iceberg.f90`: `total_mass_loss` includes `wave_mass_loss`.
- `src/iceberg_dynamics.f90`: optional Stokes drift added to depth-averaged
  and layer currents before water drag (Method A, Method B, voxel branch).
- `app/iceberg_run.f90`: optional 12th argument `wave.nc`; sets the 2020
  epoch; writes `m_wave` (m s⁻¹) and `wave_mass_loss` (kg) to the trajectory
  NetCDF.

All gates default OFF; the 12.6a path is unchanged when they are unset.

## 3. Verification

`test/test_wave_erosion.f90` (CI-safe, synthetic, no `.nc`):

| Test | Result |
| --- | --- |
| Douglas bins (9 `Hs` values) | PASS |
| Bigg `c=0` → `2/86400 m/s`; `c=1` → 0; `c=0.5` → `1.9238795/86400`; `T=-10` → 0 | PASS |
| Gate OFF: `L`, `W`, `m_wave`, `wave_mass_loss` inert | PASS |
| Gate ON (`Hs=2`, `T_w=2`, `c=0`, `dt=3600 s`): `L=W=99.9166667 m`, `m_wave=2.3148e-5 m/s`, `wave_mass_loss ≈ 1.527e6 kg` | PASS |
| Stokes OFF → zero water force; ON (`u_st=0.05 m/s`) → positive x-force | PASS |

Full battery: **79 targets, 79 `STOP 0`, 0 failures**. Strict build
(`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`): clean.

## 4. Limitations

- **No real wave-forcing run.** No Arctic WAM file is present locally; the
  reader is implemented but not validated against product data. All
  verification uses the TEST-ONLY constant hook. A real run is deferred to
  12.7a when the wave product is staged.
- **`S_s` from `Hs` (Douglas), not wind** (NEMO uses wind). Documented above.
- **Sea-ice concentration:** reanalysis path only; model path uses `0`
  (no model sea-ice coupling).
- Wave erosion removes `L`/`W` only; no undercut/calving or shape change.
- No calibration; literature coefficients unchanged.
- `dir` and `Tp` are read and stored but not yet used (directional wave
  forcing is a later refinement).
- Sea-ice drag and tides are still not implemented.

## 5. Acceptance checklist

- [x] Formula matches NEMO `icbthm.F90`; task-text inversion documented.
- [x] `ICEBERG_WAVE_EROSION` and `ICEBERG_STOKES_DRIFT` default OFF;
      OFF path unchanged.
- [x] Wave mass loss added to the budget and NetCDF diagnostics.
- [x] `iceberg_run` accepts `wave.nc` (optional 12th argument).
- [x] CI-safe tests; full battery + strict build green.
- [ ] Real wave-forcing trajectory (deferred; no data).

## 6. Next

Stage 12.6b remaining: sea-ice drag, tides. Stage 12.7a: observational
validation with real wave forcing once the Arctic WAM subset is staged.
