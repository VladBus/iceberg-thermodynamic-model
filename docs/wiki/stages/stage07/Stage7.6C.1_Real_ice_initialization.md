# Stage 7.6C.1: Real Ice Initialization — OSI-SAF SIC + C3S SIT → 1_k.ice

**Classification: A** — All diagnostics pass cleanly. Satellite sea-ice fields are
regridded onto the real IBCAO grid with machine-precision conservation, and the
full Fortran init chain `1_k.ice → an1 → wice1 → redis()` reproduces the
reconstruction exactly.

**Date:** 2026-08-27  
**Prerequisites:** Stages 7.6A / 7.6A.1 (grid), 7.6B (KOORD.DAT + hhh.bar real-grid inputs)  
**Next:** Stage 7.6C.2 (ERA5 forcing-domain expansion for the 5.2 % of wet cells outside the forcing domain, then a real-ice hot run)

---

## 1. Executive Summary

The model's legacy sea-ice initialization files `1_1.ice … 1_5.ice` were
generated from real satellite products for model **day_00 = 2020-01-01**:

- **SIC**: OSI-SAF Sea Ice Concentration CDR v3.1 (SSMIS, EASE2-North 25 km, 432×432)
- **SIT**: C3S Climate Data Store CS2SMOS sea-ice thickness, L4 combined product v1.1 (EASE2-North 12.5 km, 864×864)

Both were regridded onto the 133×105 IBCAO model grid with a **coup1-consistent
ocean mask** (parsed from `hhh.bar`, replicated exactly as `grid_coupling.f90`
derives `HT`, then restricted to the active computational domain i≤is, j≤js).
A **2-bin exact reconstruction** places all ice into the two categories bracketing
each cell's thickness h and solves the 2×2 linear system symbolically, giving
`ΣA_k = SIC` and `Σ(A_k·H_k) = SIC·SIT` to machine precision.

Key numbers (init date 2020-01-01):

| Metric                                          | Value             |
| ----------------------------------------------- | ----------------- |
| Active wet cells (model mask)                   | 10,966            |
| Ice-covered cells (ANS ≥ 0.005)                 | 4,402             |
| Mean ANS over ice                               | 0.8313            |
| Mean SIT / reconstructed HICES over ice         | 0.600 m / 0.598 m |
| Total ice volume                                | 4.50·10¹¹ m³      |
| max \|ΣA − SIC\| (reconstruction domain)        | 1.1·10⁻¹⁶         |
| max \|ΣA·H − SIC·SIT\| (non-clamped)            | 2.2·10⁻¹⁶         |
| Cells clamped below H₀=0.20 m / above H₄=2.50 m | 279 / 15          |

Fortran validation (`fpm test ice_init_test`) reproduces these values **exactly**:
4402 ice cells, mean ANS 0.8313, mean HICES 0.5977, Σwices 2333.6 m — confirming
that the 4-decimal legacy file format, float32 arithmetic and `redis()` do not
distort the satellite reconstruction.

---

## 2. Forensic Audit of the 1_k.ice Init Chain

Documented from `app/main.f90` + `src/ice_redis.f90` + `src/grid_coupling.f90`
before any data was produced:

- **File format** (main.f90:272–281): plain text, list-directed; 133 records
  (i=1..is1) × 105 space-separated reals (j=1..js1); no header. File `1_m.ice` is
  read into `an1(:,:,m+1)` (m=1..5), i.e. category concentration.
- **Cleaning** (main.f90:283–293): `9.99 → 0` (missing), `≥1.0 → 1.0`; if ΣA<1e-8
  the cell is marked open water `an1(:,:,1)=1.0`.
- **Thickness init** (main.f90:296–300): `wice1(k) = H_k·an1(k+1)` with
  **H = (0.20, 0.40, 0.95, 1.60, 2.50) m**. Latent inconsistency: `param%hst(2)=0.5`
  differs from the hard-coded H₂=0.40 — **not fixed** (no physics changes; the code
  path actually applied is H).
- **Category bounds** (param.f90:319): hmax = (0.3, 0.7, 1.2, 2.0, 50.0).
- **Conservation / redistribution** (ice_redis.f90): redis() enforces `ΣA_k ≤ 1`
  via its redistribution loop; `an1(:,:,1)=1−ΣA`; cells with aggregated ANS<0.005
  are zeroed (open-water gate). Snow is **not** part of the file format (init
  starts with `hsnow=0`, built from ERA5 `sf`).
- **Land mask**: the true ocean mask is **not** the `8` values in `hhh.bar` — `coup1()`
  derives `HT` (cm) from hhh.bar and re-computes `kt1` as the number of wet
  Z-levels (grid_coupling.f90:300–310); **land ≡ kt1==0**, and `redis()` skips
  kt1==0. 11 cells in the netCDF `mask` disagreed with the hhh.bar-derived HT
  (would carry frozen ice on land); the pipeline now uses the **coup1-consistent mask**.

---

## 3. Input Data & Download

CDS OGC-API v2 forms are at
`https://cds.climate.copernicus.eu/api/retrieve/v1/processes/{dataset}`.

| Product | Dataset id                        | Key request fields                                                                                   | Result                                                            |
| ------- | --------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| SIC     | `satellite-sea-ice-concentration` | sensor=ssmis, region=northern_hemisphere, cdr_type=cdr, temporal_aggregation=daily, version=3_1      | `ice_conc_nh_ease2-250_cdr-v3p1_202001011200.nc` (EASE2-250)      |
| SIT     | `satellite-sea-ice-thickness`     | version=1_1, processing_level=level_4, satellite_mission=combined_product, temporal_resolution=daily | `ice_thickness_nh_ease2-125_cs3smos-v1p1_20200101.nc` (EASE2-125) |

Notes:

- CDS returns a **zip wrapper** even for netCDF requests; `download_sea_ice.py`
  unzips the single member into `data/input/raw/ice/{osisaf,c3s_sit}/`.
- SIT is CS2SMOS 12.5 km (daily combined L4), the only valid daily combo (newer
  SICCI L4 versions 3_0/4_0 are rejected by the server for daily products).
- `~/.cdsapirc` present; **no credentials** in tracked files.
- Manifest: `data/input/raw/ice/download_manifest_20200101.json`.

---

## 4. Pipeline

- `python/ice/download_sea_ice.py` — CDS downloader (`--year --month --day --skip-sic/--skip-sit`).
- `python/ice/build_initial_ice.py` — regrid + QC + 2-bin reconstruction + writers:
  1. Parse `hhh.bar` → HT replica → model wet mask (10,966 active cells).
  2. SIC bilinear (`/100`, clip to 0..1); SIT **nearest** (avoids edge smearing / NaN spreading).
  3. QC & drop policy: cells with SIC>0 but no positive SIT are **dropped**
     (SIC→0, no invented thickness) — 284 cells, 2.59 % of wet cells;
     430 cells have SIT>0 where SIC≈0 (finer 12.5 km detail vs 25 km SIC) —
     all zeroed (ice may not exist without measured concentration).
  4. **2-bin reconstruction**: bracket h in a category pair, solve
     `a=A·(hu−h)/(hu−hl)`, `b=A·(h−hl)/(hu−hl)`; h<0.20 → cat1, h>2.50 → cat5
     (clamps counted); A<0.005 → open water.
  5. Writers: `1_k.ice` (133×105, 4 decimals), `sic_model.nc`, `sit_model.nc`,
     `category_concentrations_20200101.nc`, `reconstruction_metadata.json`,
     `stage7.6C.1_statistics.json`, diagnostics PNGs.

---

## 5. Validation

`test/ice_init_test.f90` (`fpm test --flag "-I/usr/include" ice_init_test`)
executes the exact production init sequence: `coup1()` → `ikuv()` → read 1_k.ice
→ cleaning → `wice1 = H·an1` → `redis()`, then asserts:

1. `Σ_k an1(k) ≤ 1` everywhere (≤ 1.0 + 1e-5)
2. Land (`kt1==0`) carries zero ice; all categories ≥ 0
3. Per-category thickness inside `(hmax(k-1), hmax(k)]`
4. Aggregates match the reconstruction: 4402 ± 50 ice cells, mean ANS & HICES ± 1 %

Actual Fortran result: **4402 / 0.8313 / 0.5977 m / Σwices 2333.6 m** — exact match.

Full suite `fpm run fpm test` passes with exit 0 (conv 15, snowfall 9,
cold-ice/snow, eos 7, thermo-input 13, eos-precision, check, ice-init).
`python/tests/test_units_roundtrip.py`: OK (SI→presentation→SI round trips).

---

## 6. Files

| File                                                                                          | Location                                                                                                |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `1_1.ice … 1_5.ice`                                                                           | `data/input/generated/real_grid/ice_2020-01-01/` (+ symlinks at project root, `1_*.ice` now gitignored) |
| `reconstruction_metadata.json`                                                                | `data/input/generated/real_grid/ice_2020-01-01/`                                                        |
| `sic_model.nc`, `sit_model.nc`, `stage7.6C.1_statistics.json`, `category_concentrations_*.nc` | `data/input/processed/ice/`                                                                             |
| `sic_model.png`, `sit_model.png`, `hices_reconstructed.png`                                   | `data/output/diagnostics/stage7.6C.1/`                                                                  |
| `download_sea_ice.py`, `build_initial_ice.py`                                                 | `python/ice/`                                                                                           |
| `ice_init_test.f90`                                                                           | `test/`                                                                                                 |

---

## 7. Caveats & Next Steps

- **Margin cells dropped**: 284 (2.59 %) of wet cells have SIC>0 but no CS2SMOS
  thickness and are set to open water; a halved gate is not applied.
- **Clamps**: 279 thin (< 0.20 m) and 15 thick (> 2.50 m) cells carry the bin's
  thickness — a bounded, reported volume bias.
- **4-decimal legacy format** adds ≤ 5·10⁻⁵ rounding per category by design.
- **Next (7.6C.2)**: expand ERA5 download/domain (≥64°N, ≥77°E) so all 10,966
  wet cells are inside the forcing domain (currently 5.2 %: 591 / 11,330), then a
  real-ice Q1 hot run with `kl1=1` and comparison against satellite SIC/SIT.
