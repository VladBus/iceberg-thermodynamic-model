# Stage 12.2 — Reanalysis Reader & Ocean Provider

**Status:** COMPLETE (implementation + unit/integration tests; default OFF).
**Date:** 2026-10-29
**Base:** `ef7d69e` (Stage 12.1). Decision authority: D-51 (reanalysis) + D-52 (this).
**Scope:** Fortran reader + provider + iceberg-forcing integration. **No Stage 11
ocean physics touched; new source OFF by default; `fpm.toml`/CI unchanged** (tests
auto-discovered).

## Objective

Provide an offline/prescribed GLORYS12 ocean-forcing path for the iceberg that
**replaces the frozen Stage 11 prognostic ocean** (D-51) without a one-way
feedback and without touching Stage 11 physics. The ocean does not feel the
iceberg.

## Architecture (3 layers)

```
iceberg_forcing.get_ocean_profile
        │  OCEAN_SOURCE env (default "model" → Stage 11 bit-identical)
        ├── model path      : unchanged (t2/s2/u2/v2 on model grid)
        └── reanalysis path : get_ocean_profile_reanalysis  (new, in iceberg_forcing.f90)
                    │  builds ocean_profile on native GLORYS depths surface→draft
                    ▼
              ocean_provider (src/ocean_provider.f90, new)
                    │  source_type 1=reanalysis, 2=model(no-op)
                    ▼
              reanalysis_reader (src/reanalysis_reader.f90, new)
                    │  NetCDF GLORYS12 (daily + static), packed int16 decode,
                    │  bilinear(lat,lon) + linear(depth) + linear(time), units, clip
                    ▼
              data/input/raw/reanalysis/glorys12/…
```

Pointwise provider API (per Stage 12.0 spec): `ocean_provider_get(provider, time,
lat, lon, depth, T,S,u,v,zos,siconc,sithick, ok)`. `time` is **UNIX seconds since
1970-01-01** (matches `model_time_sec`/`era5_time`).

## Reader contract (fixed by Stage 12.1 reconnaissance)

| Aspect | Handling |
|---|---|
| Grid | regular 1-D `latitude`(277)/`longitude`(901), 1/12°; **bilinear** on the 2×2 node block |
| Vertical | non-uniform `depth` (32 native levels, 0.494–541.09 m); **linear**, **clamp** at ends (no extrapolation) |
| Time | 31 daily steps, `hours since 1950-01-01` → converted to UNIX s at init (offset 631 152 000 s); **linear** between day snapshots |
| Dim order | netCDF-Fortran reverses CDL: `(time,depth,lat,lon)`→`(lon,lat,depth,time)`. Positions resolved by **dimid**, verified per variable (T-18), not assumed |
| Packed data | fields are **int16 + scale_factor/add_offset, `_FillValue=-32767`**. netCDF-Fortran does NOT auto-scale → reader reads raw int16 into an integer buffer and **decodes explicitly** (`raw*scale+offset`); `_FillValue`→NaN |
| Units | `thetao` °C (passthrough); `so` → **÷1000** → mass fraction; `uo/vo` m s⁻¹; `zos` m; `siconc` **clip [0,1]**; `sithick` m (≥0) |
| Land / NaN | NaN = land or below-seafloor; corner_bilinear **renormalises weights over sea+finite corners**; all-land → `ok=.false.`. No zero-fill |
| Bounds | lat/lon/time outside → `ok=.false.`; depth outside → clamp to boundary level |

## Provider source_type=2 (model)

`ocean_provider_get` returns `ok=.false.` for `SRC_MODEL` by design: the
prognostic ocean is read by the **unchanged legacy path directly**, not through
the provider. The provider abstracts only the reanalysis source; it never
overrides Stage 11.

## Integration (`iceberg_forcing.f90`)

- New module state + `OCEAN_SOURCE` env read **lazily and once**
  (`ocean_forcing_init_from_env`), default `model`.
- `get_ocean_profile` gained a **backward-compatible optional `time_sec`**; the
  model path ignores it, so every existing call site (main.f90, 12 iceberg
  tests) compiles and behaves **bit-identically** with the switch OFF.
- Reanalysis path builds `ocean_profile` on native GLORYS levels from the
  surface down to the draft in a **single deterministic pass**, stopping at the
  first invalid/NaN level (i.e. the local seafloor) — no extrapolation below the
  bottom. `u_rel` and layer `dz` computed as before.
- Public entry points for drivers/tests: `ocean_forcing_configure(source,
  daily_path, static_path)`, `ocean_forcing_init_from_env`,
  `ocean_forcing_is_reanalysis`.

## Unit + integration tests (all SKIP=exit 0 without the gitignored `.nc`)

Anchors are independent xarray `interp` values from `stage12.1_glorys12_validation.md`.

| Test | Checks | Key assertions | Result |
|---|---|---|---|
| `test_reanalysis_reader` | 9 | dims (31,32,277,901); T=−1.48164, **S=0.034889 (÷1000)**, u,v,zos,siconc match; vertical interp T(10)=2.2428→T(200)=2.8626; temporal interp T(00)=−1.4816→T(12)=−1.4981; land→ok=false; siconc clipped [0,1] | **PASS 9/9** |
| `test_ocean_provider` | 4 | model get→ok=false; reanalysis init+get T/S match anchors; land→ok=false | **PASS 4/4** |
| `test_iceberg_forcing_reanalysis` | 4 | profile 14 levels (0.49–25.2 m, stops at floor); all finite; S mass-fraction; u_rel≥0; land position→ok=false | **PASS 4/4** |

Full `fpm test` battery green (model path unaffected); no `src/`ocean, `app`,
`test` (other than the 3 new files) change under the default switch.

## Known limitations (documented, not solved)

1. **Packed-int16 decoding is reader-side** and relies on the per-variable
   `scale_factor/add_offset` (verified for the 7 daily fields). The static
   `mask` is read without scaling.
2. **Depth coverage 0.494–541 m** (native), not a full 600 m; drafts below
   the local seafloor are not extrapolated (profile stops at the floor).
3. **`siconc` may exceed 1 in the raw product** → reader clips to [0,1].
4. **Bathymetry not yet used to cap draft** — the profile simply stops at the
   first NaN (below-floor) level; an explicit `deptho` cap is a Stage 12.3+
   refinement.
5. The **reanalysis→iceberg thermodynamic coupling is only exercised by the
   integration test** for the forcing layer; end-to-end melt/drift validation
   with reanalysis belongs to later stages (12.3+).
6. No temporal extrapolation across the 31-day file boundary (out-of-range time
   → ok=false); a full-year pull (Stage 12.1 next) closes the annual gap.

## Files

- New: `src/reanalysis_reader.f90`, `src/ocean_provider.f90`,
  `test/test_reanalysis_reader.f90`, `test/test_ocean_provider.f90`,
  `test/test_iceberg_forcing_reanalysis.f90`.
- Modified: `src/iceberg_forcing.f90` (added provider integration + optional
  `time_sec`; model path unchanged/OFF default).
- Doc: this report, D-52, `docs/STAGE12_PREPARATION.md`,
  `docs/REANALYSIS_DATA_PLAN.md`.

## GO / NO-GO for Stage 12.3 (voxel thermal core)

| Gate | Result |
|---|---|
| Reader implemented (spatial+vertical+temporal interp, units, NaN/land) | **YES** |
| Provider abstraction (reanalysis vs model) | **YES** |
| Integration default-OFF, Stage 11 bit-identical, no ocean-code edits | **YES** |
| Unit + integration tests green; CI green | **YES** |
| Reanalysis forcing reaches `ocean_profile` cleanly | **YES** |

**GO for Stage 12.3.** The prescribed-ocean plumbing is in place; the voxel
thermal core can now be built on a verified ocean/T/S/u/v source. (Do NOT start
Stage 12.3 implementation in this stage.)
