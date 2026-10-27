#!/usr/bin/env python3
"""RED TEST (intentionally not in CI): tide propagation is not integrated.

Target behavior: a 1 m M2 elevation at an open boundary propagates into the
domain with phase speed sqrt(gH) and no reflection. Current `tides.nc` is
null-tides and `shal()` has no tidal forcing. This script exits RED until the
implementation in docs/TIDES_IMPLEMENTATION_PLAN.md lands.
"""
from pathlib import Path
import sys

import netCDF4 as nc
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TIDES = ROOT / "data/input/processed/tides/tides.nc"

def main() -> int:
    if not TIDES.exists():
        print("RED: tides.nc missing")
        return 1
    with nc.Dataset(TIDES) as d:
        amp = np.asarray(d["amplitude"][:], dtype=float)
        names = [str(x) for x in d["constituent_name"][:]]
        status = getattr(d, "tidal_status", "UNKNOWN")
    print(f"RED: tidal_status={status}; constituents={names}; max amplitude={amp.max():.6g} m")
    if amp.max() <= 0.0:
        print("RED: null-tides; no M2 boundary wave can propagate.")
        return 1
    print("RED: tidal amplitudes exist, but the Fortran tide forcing/OBC integration is absent.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
