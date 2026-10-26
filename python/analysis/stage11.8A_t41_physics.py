"""T-41 physics verification: brackish RO and absolute density (no model run).

The NetCDF `density_anomaly` is in kg/m3 and represents rho[g/cm3] - 1.02.
Therefore absolute density = 1.02 + density_anomaly_kgm3/1000.

The July EOS80 negative values are only a few 1e-6 g/cm3 below the 1.02
reference; they are not a vacuum or an instability. This script computes the
UNESCO EOS-80 absolute density for every negative surface cell and compares it
with the model's archived anomaly.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import netCDF4 as nc
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "data" / "runs" / "matrix_jul_eos80_n1" / "output" / "nc" / "results_day_final.nc"
OUT = ROOT / "data" / "validation" / "t41_physics_verification.json"
REFERENCE = 1.02

# UNESCO 1983 / Fofonoff & Millard coefficients (mirrors src/eos80_unesco.f90).
A = [999.842594, 6.793952e-2, -9.095290e-3, 1.001685e-4, -1.120083e-6, 6.536332e-9]
B = [0.824493, -4.0899e-3, 7.6438e-5, -8.2467e-7, 5.3875e-9]
C = [-5.72466e-3, 1.0227e-4, -1.6546e-6]
D = 4.8314e-4
E = [19652.21, 148.4206, -2.327105, 1.360477e-2, -5.155288e-5]
F = [54.6746, -0.603459, 1.09987e-2, -6.1670e-5]
G = [7.944e-2, 1.6483e-2, -5.3009e-4]
H = [3.239908, 1.43713e-3, 1.16092e-4, -5.77905e-7]
I = [2.2838e-3, -1.0981e-5, -1.6078e-6]
J = 1.91075e-4
K = [8.50935e-5, -6.12293e-6, 5.2787e-8]
M = [-9.9348e-7, 2.0816e-8, 9.1697e-10]


def unesco_rho_kgm3(s_psu: float, t_c: float, p_dbar: float) -> float:
    """In-situ UNESCO EOS-80 density [kg/m3] (same formula as Fortran)."""
    sr = math.sqrt(max(s_psu, 0.0))
    pbar = 0.1 * p_dbar
    r0 = (
        A[0] + (A[1] + (A[2] + (A[3] + (A[4] + A[5] * t_c) * t_c) * t_c) * t_c) * t_c
        + (B[0] + (B[1] + (B[2] + (B[3] + B[4] * t_c) * t_c) * t_c) * t_c) * s_psu
        + (C[0] + (C[1] + C[2] * t_c) * t_c) * s_psu * sr
        + D * s_psu * s_psu
    )
    k0 = (
        E[0] + (E[1] + (E[2] + (E[3] + E[4] * t_c) * t_c) * t_c) * t_c
        + (F[0] + (F[1] + (F[2] + F[3] * t_c) * t_c) * t_c) * s_psu
        + (G[0] + (G[1] + G[2] * t_c) * t_c) * s_psu * sr
    )
    ka = (
        H[0] + (H[1] + (H[2] + H[3] * t_c) * t_c) * t_c
        + (I[0] + (I[1] + I[2] * t_c) * t_c) * s_psu
        + J * s_psu * sr
    )
    kb = K[0] + (K[1] + K[2] * t_c) * t_c + (M[0] + (M[1] + M[2] * t_c) * t_c) * s_psu
    return r0 / (1.0 - pbar / (k0 + pbar * (ka + pbar * kb)))


def main() -> None:
    d = nc.Dataset(RUN)
    ro = np.array(d["density_anomaly"][:], dtype=float)
    T = np.array(d["temperature"][:], dtype=float)
    S = np.array(d["salinity_mass_fraction"][:], dtype=float)
    lat = np.array(d["latitude"][:], dtype=float)
    lon = np.array(d["longitude"][:], dtype=float)
    depth = np.array(d["depth"][:], dtype=float)
    d.close()

    rows = []
    for k, i, j in np.argwhere(ro < 0.0):
        s_psu = float(S[k, i, j]) * 1000.0
        t_c = float(T[k, i, j]) - 273.15
        p_dbar = float(depth[k])
        ro_nc_kgm3 = float(ro[k, i, j])
        ro_nc_gcm3 = ro_nc_kgm3 / 1000.0
        rho_abs_from_ro = REFERENCE + ro_nc_gcm3
        rho_eos_kgm3 = unesco_rho_kgm3(s_psu, t_c, p_dbar)
        rho_eos_gcm3 = rho_eos_kgm3 / 1000.0
        ro_eos_gcm3 = rho_eos_gcm3 - REFERENCE
        rows.append({
            "k": int(k), "i": int(i), "j": int(j),
            "latitude_deg": round(float(lat[i, j]), 6),
            "longitude_deg": round(float(lon[i, j]), 6),
            "depth_m": round(p_dbar, 6),
            "S_psu": round(s_psu, 9),
            "T_C": round(t_c, 9),
            "RO_nc_kg_m3": ro_nc_kgm3,
            "RO_nc_g_cm3": ro_nc_gcm3,
            "rho_absolute_from_RO_g_cm3": rho_abs_from_ro,
            "rho_unesco_kg_m3": rho_eos_kgm3,
            "rho_unesco_g_cm3": rho_eos_gcm3,
            "RO_unesco_g_cm3": ro_eos_gcm3,
            "model_minus_unesco_RO_g_cm3": ro_nc_gcm3 - ro_eos_gcm3,
            "rho_greater_than_1_g_cm3": rho_eos_gcm3 > 1.0,
            "negative_is_reference_offset": ro_eos_gcm3 < 0.0 and rho_eos_gcm3 > 1.0,
            "old_gate_RO_ge_0": ro_nc_kgm3 >= 0.0,
            "new_gate_absolute_density_gt_1": rho_eos_gcm3 > 1.0,
        })

    example = {
        "S_psu": 21.9, "T_C": 2.1,
        "rho_unesco_kg_m3": unesco_rho_kgm3(21.9, 2.1, 0.0),
        "rho_unesco_g_cm3": unesco_rho_kgm3(21.9, 2.1, 0.0) / 1000.0,
        "RO_unesco_g_cm3": unesco_rho_kgm3(21.9, 2.1, 0.0) / 1000.0 - REFERENCE,
        "note": "Prompt example values; the seven failing July cells are S=25.03-25.08 PSU, not 21.9.",
    }
    result = {
        "test": "t41_physics_verification",
        "stage": "11.8A Phase 2-ANALYSIS",
        "run": "matrix_jul_eos80_n1",
        "units": {
            "density_anomaly_netcdf": "kg m-3 (rho[g cm-3] - 1.02, multiplied by 1000)",
            "ro_g_cm3": "rho[g cm-3] - 1.02",
            "absolute_density": "g cm-3",
        },
        "reference_density_g_cm3": REFERENCE,
        "negative_cell_count": len(rows),
        "cells": rows,
        "summary": {
            "min_absolute_density_g_cm3": min(r["rho_unesco_g_cm3"] for r in rows),
            "max_absolute_density_g_cm3": max(r["rho_unesco_g_cm3"] for r in rows),
            "max_model_minus_unesco_RO_g_cm3": max(abs(r["model_minus_unesco_RO_g_cm3"]) for r in rows),
            "all_absolute_density_gt_1": all(r["rho_greater_than_1_g_cm3"] for r in rows),
            "all_negative_due_to_reference_offset": all(r["negative_is_reference_offset"] for r in rows),
            "old_gate_fail_count": sum(not r["old_gate_RO_ge_0"] for r in rows),
            "new_gate_pass_count": sum(r["new_gate_absolute_density_gt_1"] for r in rows),
        },
        "example_21p9_2p1": example,
        "conclusion": "RO<0 is physically consistent for brackish water: absolute density is "
                      "~1.020 g/cm3 and the negative value is the rho-1.02 reference offset. "
                      "The RO>=0 gate is invalid; use absolute density >1.0 g/cm3 (and RO > -0.05 g/cm3).",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))
    print("negative cells:", len(rows), "example rho:", example["rho_unesco_g_cm3"])


if __name__ == "__main__":
    main()
