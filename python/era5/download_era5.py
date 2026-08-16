"""Download ERA5 reanalysis data using the CDS API."""

import cdsapi

dataset = "reanalysis-era5-single-levels"

request = {
    "product_type": ["reanalysis"],
    "variable": [
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "2m_temperature",
        "mean_sea_level_pressure",
    ],
    "year": ["2020"],
    "month": ["01"],
    "day": [
        "01",
        "02",
        "03",
    ],
    "time": [
        "00:00",
        "06:00",
        "12:00",
        "18:00",
    ],
    "data_format": "netcdf",
    "download_format": "unarchived",
    "area": [90, -180, 65, 180],
}


client = cdsapi.Client()

client.retrieve(
    dataset,
    request,
).download("data/input/raw/era5/era5_test.nc")
