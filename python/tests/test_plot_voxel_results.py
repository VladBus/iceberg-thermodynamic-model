#!/usr/bin/env python3
"""Regression tests for plot_voxel_results slice consistency checks."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "plot_voxel_results", ROOT / "python/analysis/plot_voxel_results.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic_field(nx=7, ny=6, nz=5, ns=2):
    i, j, k = np.meshgrid(
        np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij"
    )
    data = np.empty((ns, nx, ny, nz), dtype=float)
    for s in range(ns):
        data[s] = 100.0 * i + 10.0 * j + k + s
    return xr.DataArray(
        data,
        dims=("snapshot", "nx", "ny", "nz"),
        coords={"snapshot": np.arange(ns), "nx": np.arange(nx),
                "ny": np.arange(ny), "nz": np.arange(nz)},
    )


def main() -> None:
    T = synthetic_field()
    mod._check_temperature_slices(T)
    # Transposing a field changes the axis order and must be caught by the
    # caller/plot code, not silently treated as the same field.
    wrong = T.transpose("snapshot", "nz", "ny", "nx")
    assert wrong.dims != ("snapshot", "nx", "ny", "nz")
    try:
        mod._check_temperature_slices(wrong)
    except ValueError:
        pass
    else:
        raise AssertionError("transposed temperature field was not rejected")
    print("SUCCESS: synthetic temperature slice checks passed")


if __name__ == "__main__":
    main()
