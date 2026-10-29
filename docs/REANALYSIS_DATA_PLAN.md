# Reanalysis Data Plan — Stage 12.1

**Status:** PLAN — no data downloaded in Stage 12.0.
**Date:** 2026-10-29
**Decision:** D-51. **Implementation:** not started.
**Purpose:** define the exact ocean/sea-ice source and validation gate for the
Stage 12 voxel iceberg. The atmosphere remains ERA5.

## 1. Product selection

Primary:

| Field | Value |
|---|---|
| Product | `GLOBAL_MULTIYEAR_PHY_001_030` (Global Ocean Physics Reanalysis) |
| DOI | `10.48670/moi-00021` |
| Dataset | `cmems_mod_glo_phy_my_0.083deg_P1D-m` |
| Version | `202311` (catalogue at probe time) |
| Resolution | 1/12° (~8 km), daily means |
| Static dataset | `cmems_mod_glo_phy_my_0.083deg_static` (`deptho`, `mask`) |
| Service | Copernicus Marine Data Store (`copernicusmarine` CLI 2.5.0) |

Why: GLORYS12 is the finest daily global reanalysis available through the
project’s Copernicus access, resolves the Barents boundary currents better than
the 1° EN4 analysis, and provides coherent T/S/current/sea-ice/SSH fields.

Fallback / independent cross-check only:

| Field | Value |
|---|---|
| Product | `ARCTIC_MULTIYEAR_PHY_002_003` (Arctic Ocean Physics Reanalysis) |
| DOI | `10.48670/moi-00007` |
| Dataset | `cmems_mod_arc_phy_my_topaz4_P1D-m` |
| Version | `202506` (catalogue at probe time) |
| Resolution | 12.5 km, daily |

Do not blend TOPAZ4 and GLORYS12 inside one Stage 12 run.

## 2. Variables and units

| Variable | Meaning | Native unit | Required conversion |
|---|---|---|---|
| `thetao` | potential temperature | °C | none (model uses °C) |
| `so` | salinity | 1e−3 (PSU) | ×0.001 → mass fraction at reader boundary |
| `uo` | eastward velocity | m s⁻¹ | ×100 → cm s⁻¹ only if internal CGS path is reused |
| `vo` | northward velocity | m s⁻¹ | ×100 → cm s⁻¹ only if internal CGS path is reused |
| `zos` | sea surface height | m | none |
| `siconc` | sea-ice area fraction | 0–1 | none |
| `sithick` | sea-ice thickness | m | none |
| `deptho` | bathymetric depth | m | none |
| `mask` | land/sea mask | flag | use product mask; never zero-fill land |

The reanalysis reader must own the unit conversion. Do not scatter conversion
factors through the voxel solver.

## 3. Domain, time, depth

| Item | Value |
|---|---|
| Model domain | `64.21–85.04°N`, `8.33–76.32°E` |
| Download domain | `63–86°N`, `5–80°E` (guard margin) |
| Period | `2020-01-01` … `2020-12-31` |
| Cadence | daily mean |
| Depth | surface … at least 600 m; preserve native levels |
| Time zone | UTC, no local-time shift |

The guard margin prevents edge clamping when the iceberg drifts near the model
boundary. The reader must reject a file whose bbox does not contain the full
model domain.

## 4. Acquisition command (Stage 12.1 only)

Credentials live in the Copernicus Marine configuration
(`~/.copernicusmarine/`); never commit them.

```bash
# Template — do not run in Stage 12.0. Verify storage first.
copernicusmarine subset \
  --dataset-id cmems_mod_glo_phy_my_0.083deg_P1D-m \
  --variable thetao --variable so --variable uo --variable vo \
  --variable zos --variable siconc --variable sithick \
  --minimum-longitude 5 --maximum-longitude 80 \
  --minimum-latitude 63 --maximum-latitude 86 \
  --minimum-depth 0 --maximum-depth 600 \
  --start-datetime 2020-01-01T00:00:00 \
  --end-datetime 2020-12-31T00:00:00 \
  --output-directory data/input/raw/reanalysis/glorys12/2020
```

Static fields use `cmems_mod_glo_phy_my_0.083deg_static` with `deptho` and
`mask` over the same bbox. A monthly split is preferred after the first
dry-run size check; it keeps retries and storage bounded.

## 5. Storage and naming

Expected uncompressed size: roughly **35–70 GB** for the four 3-D fields over
the 600 m subset, depending on the number of native levels and packing. Verify
the actual byte count with one month before a full-year transfer.

Proposed layout (gitignored):

```text
data/input/raw/reanalysis/glorys12/2020/
  glorys12_barents_2020_01_3d.nc
  glorys12_barents_2020_01_2d.nc
  ...
  glorys12_barents_static.nc
data/input/processed/reanalysis/glorys12/2020/
  glorys12_barents_2020_01_model.nc   # reader-ready, float32, deflate
```

Do not commit NetCDF files (`*.nc` is gitignored).

## 6. Validation gate for Stage 12.1

A download is accepted only if all checks pass:

1. Product/dataset IDs and version match this plan.
2. Time axis covers every day of 2020; no duplicate or missing day.
3. Bbox contains `63–86°N, 5–80°E`; grid is regular in longitude/latitude.
4. `thetao` and `so` are finite on every wet cell; no 0-fill on land.
5. Mask agrees with `deptho`; no wet cell has depth ≤0.
6. T is above the freezing point on wet cells (flag/clamp with documented
   tolerance, as in Stage 11 EN4).
7. `uo/vo` are finite and bounded (<5 m/s) on wet cells.
8. `so` conversion reproduces 35 PSU → 0.035 mass fraction.
9. A second independent read of one month matches the first bit-for-bit after
   unpacking.
10. Catalogued variable names/units/bbox are recorded in a manifest with the
    retrieval timestamp.

Fail closed: a missing field, time gap, or mask mismatch aborts Stage 12.1;
there is no synthetic fill.

## 7. Relationship to Stage 11

- Stage 11 N=24 ocean is **not** used as Stage 12 truth.
- Stage 11 ERA5 atmosphere path is retained.
- Stage 11 limitations (N², tides, 90-day, T-39) remain documented; changing
  the ocean source does not erase them.
- Stage 12 is one-way/offline. Two-way coupling requires a separate stage.

## 8. Reproducibility

- `python/reanalysis/copernicus_probe.py` verifies catalogue availability and
  required variables without downloading data.
- Store the probe JSON and the per-file SHA-256 manifest with the processed
  subset.
- Record the exact `copernicusmarine` version and retrieval date.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Product version changes | pin `202311`; record catalogue JSON |
| Full-year size exceeds disk | one-month pilot + exact byte count; monthly chunks |
| `so` unit mistaken for mass fraction | explicit conversion test; 35 PSU anchor |
| Land/edge fill corrupts forcing | mask/depth gate; fail closed |
| Mixing TOPAZ4 and GLORYS12 | one product per run; cross-check only |
| Reanalysis currents too weak/strong for drift | document; validate drift, do not tune silently |
| Product not covering 2020 end | check exact `time_coverage_end` before download |
