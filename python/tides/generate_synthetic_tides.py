#!/usr/bin/env python3
"""Generate synthetic FES2014-like M2 tides for the model grid (no download).

M2 amplitude 0.5 m; phase varies linearly from 0 at the western edge to pi at
the eastern edge; S2/K1/O1 are zero. Output has the existing tides.nc schema.
"""
from pathlib import Path
import numpy as np
import netCDF4 as nc

ROOT = Path(__file__).resolve().parents[2]
GRID = ROOT / "data/input/processed/grid/grid.nc"
OUT = ROOT / "data/input/processed/tides/tides.nc"

def main() -> None:
    with nc.Dataset(GRID) as g:
        lat = np.asarray(g["lat"][:], dtype=float).T   # (j,i)
        lon = np.asarray(g["lon"][:], dtype=float).T   # (j,i)
    names = ["M2", "S2", "K1", "O1"]
    amp = np.zeros((4, lat.shape[0], lat.shape[1]), dtype=np.float32)
    pha = np.zeros_like(amp)
    # Longitude-based half-wave: west edge 0, east edge pi.
    x = (lon - lon.min()) / max(lon.max() - lon.min(), 1e-12)
    amp[0, :, :] = 0.5
    pha[0, :, :] = np.pi * x
    with nc.Dataset(OUT, "w") as d:
        d.createDimension("const", 4)
        d.createDimension("j", lat.shape[0])
        d.createDimension("i", lat.shape[1])
        v = d.createVariable("constituent_name", "S1", ("const",))
        for i, n in enumerate(names): v[i] = n
        v = d.createVariable("amplitude", "f4", ("const", "j", "i"), zlib=True)
        v[:] = amp; v.units = "m"
        v = d.createVariable("phase", "f4", ("const", "j", "i"), zlib=True)
        v[:] = pha; v.units = "radians"
        v = d.createVariable("qq", "f8", ("const",))
        v[:] = [28.9841042, 30.0, 15.041069, 13.943036]; v.units = "degrees/hour"
        v = d.createVariable("qq_rad_per_step", "f8", ("const",))
        v[:] = [0, 0, 0, 0]
        d.tidal_status = "synthetic M2 (FES2014 unavailable)"
        d.source = "python/tides/generate_synthetic_tides.py"
        d.reference_dt1_seconds = 120.0
    print("wrote", OUT, "M2 amplitude=0.5 m; phase 0..pi")

if __name__ == "__main__":
    main()
