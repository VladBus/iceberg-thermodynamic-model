"""Check the contents of the downloaded ERA5 data."""

import xarray as xr

ds = xr.open_dataset("data/input/raw/era5/era5_test.nc")

print("\n=== DIMENSIONS ===")
for name, size in ds.sizes.items():
    print(f"{name}: {size}")

print("\n=== COORDINATES ===")
for name, coord in ds.coords.items():
    print(f"{name}: shape={coord.shape}, dims={coord.dims}")
    print(coord.values)

print("\n=== VARIABLES ===")
for name, var in ds.data_vars.items():
    print(f"\n{name}")
    print(f"  shape: {var.shape}")
    print(f"  dims:  {var.dims}")
    print(f"  dtype: {var.dtype}")
    print(f"  attrs: {var.attrs}")
