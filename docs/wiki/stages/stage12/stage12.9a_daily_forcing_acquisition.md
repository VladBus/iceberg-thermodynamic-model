# Stage 12.9a — Daily-Forcing Acquisition

**Status:** **COMPLETE** (2026-11-07)
**Scope:** acquisition and provenance for the 2020 and 2024 reanalysis subsets.
**Decision:** D-51 (+D-52); workstream split recorded in `docs/validation/INDEX.md`.

## 1. Inventory

| Product | Months | Local form | Approx. size | Manifest |
| --- | ---: | --- | ---: | --- |
| ERA5 | 24/24 | Hourly CDS fields aggregated to monthly daily-mean NetCDF | 277 MB | `docs/validation/stage12.9_era5_manifest.json` |
| GLORYS12 | 24/24 | Monthly Barents subsets; annual 2020 merge retained | 18 GB | `docs/validation/stage12.9_glorys_manifest.json` |
| WAM | 24/24 | Monthly Barents wave subsets | 28 GB | `docs/validation/stage12.9_wam_manifest.json` |

Coverage is `2020-01…2020-12` and `2024-01…2024-12` for each product.

## 2. Verification

- Every manifest entry has a corresponding local file.
- Every manifest `size_bytes` value matches the local file size.
- The ERA5 manifest contains all 24 expected months, including `2024-12`.
- No missing months were found in the three manifests.
- Manifest SHA-256 values were not recomputed during this closure check.

## 3. Boundaries

This stage records **data acquisition and provenance only**. It does not
validate daily forcing or establish quantitative model skill. Stage 12.8 remains
the latest completed published validation, and Stage 12.9b thesis writing
remains GO only with explicit fallback labeling.

No further acquisition downloads are needed for the Stage 12.9 data contract.
The acquisition manifests remain in `docs/validation/` because the acquisition
tools use that path as their canonical provenance location.
