#!/usr/bin/env python3
"""
Stage 11.7D — tides.nc builder (null-tides representation).

Creates data/input/processed/tides/tides.nc representing the current
production state: null-tides (zero amplitudes/phases for all four
constituents M2, S2, K1, O1).

Transcription rules (authoritative: src/tide_forcing.f90 + app/main.f90):
  - GRM2/GRS2/GRK1/GRO1 files are ABSENT in production.
  - Main.f90:432-460 reads GRM2 if present; otherwise initializes
    amp1=amp2=amp3=0, faz1=faz2=faz3=0 → null tides.
  - Constituents (qq): M2=28.9841042, S2=30.0, K1=15.041069, O1=13.943036 °/h.
  - Tides.nc represents the CURRENT production state: null-tides
    with explicit provenance flag.

Field ownership: tides.nc owns amplitude/phase arrays + provenance.
CF-1.10 metadata, dimension names (const, j, i).
"""

import hashlib
import os
import subprocess
import time

import numpy as np
from netCDF4 import Dataset

IS1, JS1 = 133, 105
N_CONST = 4  # M2, S2, K1, O1

# Constituent names and frequencies [deg/h]
CONST_NAMES = ["M2", "S2", "K1", "O1"]
QQ_DEG_H = np.array([28.9841042, 30.0, 15.041069, 13.943036], dtype=np.float64)

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
OUT_DIR = os.path.join(PROJECT, "data", "input", "processed", "tides")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "tides.nc")

    # Null-tides: zero amplitudes and phases
    amp = np.zeros((N_CONST, JS1, IS1), dtype=np.float32)  # [const, j, i]
    faz = np.zeros((N_CONST, JS1, IS1), dtype=np.float32)

    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT,
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "unknown"

    with Dataset(os.path.join(OUT_DIR, "tides.nc"), "w") as ds:
        ds.createDimension("const", N_CONST)
        ds.createDimension("j", JS1)
        ds.createDimension("i", IS1)

        v = ds.createVariable("constituent_name", "S1", ("const",))
        v.long_name = "tidal constituent name"
        v[:] = np.array(CONST_NAMES, dtype="S1")

        v = ds.createVariable("qq", "f8", ("const",))
        v.units = "degree/hour"
        v.long_name = "angular frequency of tidal constituents"
        v[:] = QQ_DEG_H

        v = ds.createVariable("amplitude", "f4", ("const", "j", "i"), fill_value=np.nan)
        v.units = "m"
        v.long_name = "tidal amplitude (0 = null-tides, GRM2 data unavailable)"
        v[:] = amp

        v = ds.createVariable("phase", "f4", ("const", "j", "i"), fill_value=np.nan)
        v.units = "radian"
        v.long_name = "tidal phase (0 = null-tides, GRM2 data unavailable)"
        v[:] = faz

        v = ds.createVariable("qq_rad_per_step", "f8", ("const",))
        v.units = "radian/step"
        v.long_name = "angular frequency per barotropic step (qq * dt1 / 3600 / 57.2958)"
        # dt1=120 s is the LEGACY barotropic timestep. If the barotropic
        # timestep ever changes, this value must be recomputed or treated
        # as reference-only (11.7D.2).
        dt1 = 120.0  # barotropic step [s]
        v[:] = QQ_DEG_H * (dt1 / 3600.0) / 57.2958
        ds.setncattr("reference_dt1_seconds", 120.0)

        ds.Conventions = "CF-1.10"
        ds.title = "Tidal forcing: amplitudes and phases (null-tides)"
        ds.index_mapping = ("dimensions are MODEL INDICES (CF cell indices): "
                            "const<->tidal constituent (4), j<->Fortran j (105), "
                            "i<->Fortran i (133); elementwise correspondence, NO transpose")
        ds.tidal_constituents = ", ".join(CONST_NAMES)
        ds.tidal_status = "null-tides (GRM2/GRS2/GRK1/GRO1 data unavailable)"
        ds.source_grm2 = "missing (GRM2/GRS2/GRK1/GRO1 files absent)"
        ds.builder_git_sha, ds.created = sha, time.strftime("%Y-%m-%dT%H:%M:%S")
        ds.history = ("built by python/tides/build_tides_nc.py (Stage 11.7D); "
                      "null-tides production state represented explicitly")
        ds.tidal_note = ("When real tidal data becomes available (TPXO, FES, etc.), "
                         "replace null-tides with actual amplitudes/phases, "
                         "re-validate tidal forcing, update tides.nc with real data.")

    print("tides.nc written:", os.path.join(OUT_DIR, "tides.nc"))

if __name__ == "__main__":
    import hashlib
    import os
    import subprocess
    import sys
    import pathlib
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()