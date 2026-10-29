# Stage 10.18D per-iceberg dataset — provenance

Directory: `data/validation/observations/stage10.18d/` (version-controlled).

Files:
- `enderlin23_per_iceberg.csv` (743 rows) — per-iceberg Enderlin23 dataset
  with regional attribution, geographic coordinates, melt/geometry metrics;
- `raw/Antarctic-iceberg-csvs.zip` — verbatim copy of the USAP-DC archive
  (MD5 `821bed51660957b65a896c42fb88a057`, verified 2026-09-20);
- `raw/Antarctic-iceberg-csvs/` — 54 extracted per-observation CSVs
  (`{SITE}_{YYYYMMDDhhmmss}-{YYYYMMDDhhmmss}_iceberg_meltinfo.csv`);
- `sources.csv` — source metadata;
- `provenance.md` — this file.

## Data acquisition (2026-09-20) — method

The Stage 10.18C report recorded the Enderlin23 individual-iceberg dataset
(USAP-DC 10.15784/601679, `Antarctic-iceberg-csvs.zip`) as
"account-gated, NOT retrieved". **This is now corrected: the dataset is
publicly downloadable without an account** via a direct HTTP POST to the
USAP-DC zip endpoint with the file URL as `dl_checkbox`:

```
POST https://www.usap-dc.org/zip/usapdc_601679_download_*.zip
    dl_checkbox=https://www.usap-dc.org/dataset/usap-dc/601679/
        2023-04-04T19:54:46.1Z/Antarctic-iceberg-csvs.zip
```

The page-level JavaScript reCAPTCHA gate is not enforced by the zip
endpoint. The response is a zip-in-zip: the inner
`Antarctic-iceberg-csvs.zip` (129 755 bytes) matches the published MD5
checksum `821bed51660957b65a896c42fb88a057` exactly.

Dataset metadata (from the USAP-DC landing page, accessed 2026-09-20):
- Title: "Remotely-sensed iceberg geometries and meltwater fluxes";
- Citation: Enderlin, E., Aberle, R., Dickson, A., Dryak, M., Miller, E.,
  & Oliver, C. (2022) USAP-DC, doi:10.15784/601679;
- License: CC BY 4.0 (attribution required);
- Version 2, created 2023-04-06; 15 study sites around Antarctica,
  2011-2022 WorldView stereo DEM time series;
- NSF awards 1643455 and 1933764.

## Row-by-row provenance

| Field | Value -> CSV | Assumptions / transformations |
|---|---|---|
| melt_rate | `VolumeChangeRate / SubmergedArea_mean` [m/day] | Volume change rate [m³/day] is the paper's submarine meltwater flux (volume change corrected for surface mass balance and creep thinning); divided by the mean submerged area [m²] to give an area-averaged submarine melt rate. `melt_definition=SUBMARINE_TOTAL` (side+basal) — never lateral. |
| draft | `MedianDraft_mean` [m] | Keel depth from the paper's DEM-based geometry (per-iceberg, from file). |
| volume_i / volume_f | `Volume_i` / `Volume_f` [m³] | Initial/final iceberg volume from the DEM differencing. |
| density | `Density_i` [kg m⁻³] | Firn-density-model estimate (Ligtenberg et al. 2011, per README). |
| surface_area / submerged_area | `SurfaceArea_mean` / `SubmergedArea_mean` [m²] | From the DEM geometry (README: mean/range/uncert columns). |
| lat/lon | EPSG:3031 (Antarctic Polar Stereo) inverse transform of `X_i,Y_i` / `X_f,Y_f` via pyproj | Geographic coordinates of the iceberg position on the two observation dates. |
| date_start / date_end | First 8 digits of the file-name timestamps (YYYYMMDDhhmmss) | Three files contain a truncated trailing `X` in the second timestamp (`TG_..._2018011510481X`, `TG_..._2020012315423X`, `TG_..._2020100715430X`); `X` replaced by `0` for the date extraction only — the melt computation uses the file's `TimeSeparation` value, not the parsed dates. |
| region | Site -> region map (see below) | From the paper text (ocean-observation sites) + geography for the remaining sites. |
| independent_case | TRUE (all rows) | Each row is a distinct iceberg observation. NOTE: the same physical iceberg may appear in successive files of a site (repeated observations); `independence_group=ENDERLIN23_{SITE}` marks the site-level cluster for statistics. The 10.18C independence rule (no inflation of independent units) is preserved: 15 site groups, not 743 independent units. |

## Site -> region map

From Enderlin23 (2023) text ("There are ocean observations for 10 of 15
locations ... Leonardo, Blanchard, Cadman, Widdowson and Heim glaciers along
the WAP; Thwaites Glacier along the WAIS; Mertz, Totten and Filchner ice
shelves along the EAIS; and Edgeworth Glacier along the EAP"):

| Site | Region | Basis |
|---|---|---|
| LG Leonardo, BG Blanchard, CG Cadman, WG Widdowson, HG Heim | WAP | paper text |
| SG Seller, FG Ferrigno | WAP | geography (western peninsula coast) |
| TG Thwaites | WAIS | paper text |
| RI Ronne | WAIS | geography (West Antarctica) |
| MI Mertz, TI Totten, FI Filchner | EAIS | paper text |
| PT Polar Times | EAIS | geography (East Antarctica) |
| LA Edgeworth (Larsen A) | EAP | paper text |
| LB Cadman (Larsen B) | EAP | geography (eastern peninsula) |

Regional maxima per the paper: WAP ~50, WAIS ~40, EAIS ~5, EAP ~5 m/a.
The paper excludes from its own analysis: icebergs along the eastern margins
of the Thwaites and Mertz floating ice tongues, and anomalously deep
icebergs near the Edgeworth terminus (plume shear). The dataset retains ALL
rows; the analysis flags the Mertz plume outliers where relevant.

## Known limitations

- No ocean velocity in the dataset — `U_rel` is NOT observed; the
  velocity-resolved upgrade is the ADCP-equipped campaign design
  (report section 10.18D).
- Thermal forcing is NOT per-iceberg in the raw files; the analysis uses
  paper-reported regional representative depth-averaged thermal forcing
  (WAP 1.5, WAIS/Thwaites 0.2-1.6, EAIS 0.6, EAP 0.3 degC) and the Thwaites
  inversion melt/24 for the TF test. Uncertainties are documented in the
  analysis.
- Melt definition: SUBMARINE_TOTAL (side+basal). Comparison with the model's
  lateral-only legacy coefficient is a bounded comparison, not a direct
  lateral match.
- Site-level cluster: rows of one site share `independence_group`; do not
  inflate N=743 into 743 independent units for statistics.