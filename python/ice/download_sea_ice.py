"""Download satellite sea-ice fields for the Stage 7.6C.1 real-ice initialization.

Products (Copernicus Climate Data Store, new CDS OGC API v2):

1. Sea ice concentration (SIC) -- OSI SAF product redistributed by C3S.
   - Dataset : satellite-sea-ice-concentration
   - Sensor  : ssmis   (the OSI-SAF SSMIS Climate Data Record, 1979-2025)
   - cdr_type: cdr     (reprocessed CDR, recommended for research use)
   - Grid    : 25 km polar stereographic north (NSIDC), daily, variable ice_conc
   - DOI     : 10.24381/cds.3cd8b812

2. Sea ice thickness (SIT) -- C3S SICCI-25km combined daily product.
   - Dataset           : satellite-sea-ice-thickness
   - processing_level  : level_4       (gridded 25 km EASE2-North, not along-track)
   - satellite_mission : combined_product (blend incl. CryoSat-2 / SMOS)
   - temporal_resolution : daily
   - Variable          : sea_ice_thickness [m] = mean thickness over ice-covered
     area fraction of the grid cell (matches the model's HICES = WICES/ANS).
   - Note: the CDS daily combined level_4 product is only available for CDS
     dataset version 1_1 (SICCI-25km v2.1 combined CDR, 2010-2021 winter half
     year, October-April). Later versions (3_0/4_0) on the new API are not
     served as combined daily L4 and were rejected by the server.
   - DOI               : 10.24381/cds.6679a99a

Init date rationale: the model's day_00 is 2020-01-01 (ERA5 Q1 forcing starts
2020-01-01T00:00, file era5_2020_0103_barents_expanded_merged.nc). The initial
ice state is therefore reconstructed for 2020-01-01, exactly matching the first
thermodynamic forcing instant. Both products cover early January (winter CDR:
SIT is produced October-April).

NetCDF files land in the raw hierarchy (gitignored):
    data/input/raw/ice/osisaf/sic_osisaf_YYYYMMDD.nc
    data/input/raw/ice/c3s_sit/sit_c3s_YYYYMMDD.nc

Credentials: read by cdsapi from ~/.cdsapirc (never committed).
"""

import argparse
import datetime as _dt
import json
import pathlib
import shutil
import zipfile

import cdsapi

RAW_ICE = pathlib.Path("data") / "input" / "raw" / "ice"

SIC_DIR = RAW_ICE / "osisaf"
SIT_DIR = RAW_ICE / "c3s_sit"

SIC_DATASET = "satellite-sea-ice-concentration"
SIT_DATASET = "satellite-sea-ice-thickness"


def sic_request(year, month, day):
    """CDS v2 request form for the OSI-SAF (ssmis) SIC CDR."""
    return {
        "variable": "all",
        "sensor": "ssmis",
        "region": ["northern_hemisphere"],
        "cdr_type": ["cdr"],
        "temporal_aggregation": "daily",
        "year": [f"{year}"],
        "month": [f"{month:02d}"],
        "day": [f"{day:02d}"],
        "version": ["3_1"],
    }


def sit_request(year, month, day):
    """CDS v2 request form for the C3S SICCI-25km combined daily SIT."""
    return {
        "processing_level": ["level_4"],
        "satellite_mission": ["combined_product"],
        "variable": ["sea_ice_thickness"],
        "temporal_resolution": ["daily"],
        "year": [f"{year}"],
        "month": [f"{month:02d}"],
        "day": [f"{day:02d}"],
        "version": ["1_1"],
    }


def unzip_to(path):
    """The new CDS OGC API ignores download_format and returns a zip wrapper
    even for data_format=netcdf. If ``path`` is actually a zip archive, extract
    the single member and overwrite ``path`` with the real NetCDF file."""
    if zipfile.is_zipfile(path):
        tmp = path.with_suffix(path.suffix + ".zip")
        path.replace(tmp)
        with zipfile.ZipFile(tmp) as z:
            names = z.namelist()
            if len(names) != 1:
                raise RuntimeError(f"unexpected zip members: {names}")
            with z.open(names[0]) as src, open(path, "wb") as dst:
                shutil.copyfileobj(src, dst)
        tmp.unlink()
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--month", type=int, default=1)
    parser.add_argument("--day", type=int, default=1)
    parser.add_argument("--skip-sic", action="store_true", help="skip the SIC download")
    parser.add_argument("--skip-sit", action="store_true", help="skip the SIT download")
    args = parser.parse_args()

    ymd = f"{args.year:04d}{args.month:02d}{args.day:02d}"
    date = _dt.date(args.year, args.month, args.day)
    print(f"Init date: {date}")

    client = cdsapi.Client(progress=True, verify=False)
    manifests = {}

    if not args.skip_sic:
        out = SIC_DIR / f"sic_osisaf_{ymd}.nc"
        out.parent.mkdir(parents=True, exist_ok=True)
        req = sic_request(args.year, args.month, args.day)
        print("SIC dataset :", SIC_DATASET)
        print("SIC request :", json.dumps(req))
        print("SIC output  :", out)
        client.retrieve(SIC_DATASET, req).download(str(out))
        unzip_to(out)
        manifests["sic"] = {"dataset": SIC_DATASET, "request": req, "file": str(out)}
        print("SIC download finished:", out)

    if not args.skip_sit:
        out = SIT_DIR / f"sit_c3s_{ymd}.nc"
        out.parent.mkdir(parents=True, exist_ok=True)
        req = sit_request(args.year, args.month, args.day)
        print("SIT dataset :", SIT_DATASET)
        print("SIT request :", json.dumps(req))
        print("SIT output  :", out)
        client.retrieve(SIT_DATASET, req).download(str(out))
        unzip_to(out)
        manifests["sit"] = {"dataset": SIT_DATASET, "request": req, "file": str(out)}
        print("SIT download finished:", out)

    man_path = RAW_ICE / f"download_manifest_{ymd}.json"
    with open(man_path, "w") as f:
        json.dump({"init_date": str(date), **manifests}, f, indent=2)
    print("Manifest:", man_path)


if __name__ == "__main__":
    main()
