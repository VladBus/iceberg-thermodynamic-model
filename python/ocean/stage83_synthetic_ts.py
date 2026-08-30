#!/usr/bin/env python3
"""
Stage 8.3: Create synthetic T/S NetCDF files for model stability testing.

Generates synthetic temperature/salinity fields that produce known density structures,
compatible with the model's initial_ocean_reader.
"""

import argparse
import json
import pathlib
import sys
import numpy as np
import xarray as xr

PROJ_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ_ROOT / "python" / "ice"))

from build_initial_ice import load_model_grid

# Model Z-level centres in cm
Z_CM = np.array(
    [
        250,
        500,
        1000,
        1500,
        2000,
        2500,
        3000,
        4000,
        5000,
        7500,
        10000,
        15000,
        20000,
        25000,
        30000,
        40000,
        50000,
        60000,
    ]
)
Z_M = Z_CM / 100.0
KS = len(Z_M)


def eckart_density(t_c, s_frac):
    """Eckart EOS matching the model's equation_of_state.f90"""
    t = np.asarray(t_c, dtype=np.float32)
    s = np.asarray(s_frac, dtype=np.float32)
    aa = 1779.5 + (11.25 - 0.0745 * t) * t - (3800.0 + 10.0 * t) * s
    bb = 5891.0 + 3000.0 * s + (38.0 - 0.375 * t) * t
    return 1.0 / (0.698 + aa / bb) - 1.02  # g/cm³


def create_synthetic_ts(
    lat, lon, L_m, T_bg=2.0, S_bg=0.0349, A_rho=0.005, sigma_cells=0
):
    """
    Create synthetic T/S fields that produce a density front.

    Uses linear approximation: Δρ ≈ -αΔT + βΔS
    For cold water: α ≈ 0.15 kg/m³/°C, β ≈ 0.78 kg/m³/psu

    We'll create a temperature front: ΔT = A_rho / α * tanh(x/L)
    """
    from scipy.ndimage import gaussian_filter

    # Thermal expansion coefficient (approx for cold water)
    alpha = 0.15  # kg/m³/°C
    # Haline contraction coefficient
    beta = 0.78  # kg/m³/psu

    # Convert to model units
    # 1 kg/m³ = 0.001 g/cm³ for density anomaly
    # 1 psu = 0.001 mass fraction

    # Temperature anomaly to produce density anomaly A_rho g/cm³
    # A_rho [g/cm³] = alpha * ΔT [°C] * 0.001?
    # Actually: α = -1/ρ ∂ρ/∂T ≈ 0.15 kg/m³/°C = 1.5e-4 g/cm³/°C
    # So ΔT = A_rho / 1.5e-4 °C

    alpha_gcm3 = 1.5e-4  # g/cm³/°C
    delta_T_max = A_rho / alpha_gcm3  # °C

    is1, js1 = lat.shape

    # Create horizontal temperature field
    lat_rad = np.deg2rad(lat)
    x_m = (lon - lon.min()) * 111000.0 * np.cos(lat_rad)
    x_center = (x_m.max() + x_m.min()) / 2.0

    T_anom = delta_T_max * np.tanh((x_m - x_center) / L_m)
    T_field = T_bg + T_anom

    # Salinity constant
    S_field = np.full_like(T_field, S_bg)

    # Apply Gaussian smoothing if requested
    if sigma_cells > 0:
        T_field = gaussian_filter(T_field, sigma=sigma_cells, mode="nearest")
        S_field = gaussian_filter(S_field, sigma=sigma_cells, mode="nearest")

    # Apply wet mask
    T_field = np.where(wet, T_field, 0.0)
    S_field = np.where(wet, S_field, 0.0)

    # Create 3D fields
    T_3d = np.zeros((is1, js1, KS), dtype=np.float32)
    S_3d = np.zeros((is1, js1, KS), dtype=np.float32)
    rho_3d = np.zeros((is1, js1, KS), dtype=np.float32)

    for k in range(KS):
        T_3d[:, :, k] = T_field
        S_3d[:, :, k] = S_field
        rho_3d[:, :, k] = eckart_density(
            T_field, S_field / 1000.0
        )  # S in mass fraction

    return T_3d, S_3d, rho_3d


def write_synthetic_ts_nc(T_3d, S_3d, rho_3d, run_id, output_dir):
    """Write synthetic T/S to NetCDF format compatible with initial_ocean_reader."""

    grid = load_model_grid()
    lat = grid["lat"]
    lon = grid["lon"]
    wet = grid["wet"]
    depth_cm = grid["water_depth_cm"]
    is1, js1 = lat.shape

    # Compute kt1 (water column levels) from depth
    kt1 = np.zeros((is1, js1), dtype=np.int64)
    for i in range(is1):
        for j in range(js1):
            if depth_cm is not None and depth_cm[i, j] != 8888.0 and depth_cm[i, j] > 0:
                kt1[i, j] = np.searchsorted(Z_CM, depth_cm[i, j], side="right")
            else:
                kt1[i, j] = 0

    # Create regrid_flag (all interpolated)
    flag = np.zeros((is1, js1, KS), dtype=np.int8)
    flag[wet] = 0  # interp

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{run_id}.nc"

    ds = xr.Dataset(
        data_vars={
            "temperature_celsius": (("i", "j", "k"), T_3d),
            "salinity_mass_fraction": (("i", "j", "k"), S_3d),
            "density_anomaly_gcm3": (("i", "j", "k"), rho_3d),
            "regrid_flag": (("i", "j", "k"), flag),
            "water_column_levels": (("i", "j"), kt1),
            "wet_mask": (("i", "j"), wet.astype(np.int8)),
            "lat": (("i", "j"), lat),
            "lon": (("i", "j"), lon),
        },
        coords={
            "k": ("k", np.arange(KS) + 1),
            "z_model_m": ("k", Z_M),
            "i": np.arange(is1) + 1,
            "j": np.arange(js1) + 1,
        },
        attrs={
            "title": f"Synthetic initial ocean T/S for Stage 8.3 ({run_id})",
            "source": "synthetic_front_generator.py",
            "conversion": "T_degC = T_K - 273.15; S_frac = S_psu / 1000",
            "regridding": "synthetic tanh front with configurable width and smoothing",
            "regrid_flag_labels": "0=interp 1=shallowest-finite 2=deepest-finite 3=product-land-column",
            "model_land_convention": "wet_mask==1; land cells contain 0 (never NaN)",
            "eos": "Eckart (src/equation_of_state.f90) float32; anomaly rho-1.02",
        },
    )
    ds.to_netcdf(out_file)
    print(f"Wrote synthetic T/S to {out_file}")

    return out_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic T/S for Stage 8.3 stability tests"
    )
    parser.add_argument("--L-km", type=float, default=50.0, help="Front width in km")
    parser.add_argument(
        "--A-rho", type=float, default=0.001, help="Density anomaly amplitude [g/cm³]"
    )
    parser.add_argument(
        "--sigma", type=int, default=0, help="Gaussian smoothing sigma [cells]"
    )
    parser.add_argument(
        "--run-id", type=str, default="synth_L50_sigma0", help="Run identifier"
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=pathlib.Path(
            "/home/vlad/Programing_work/vscode_work/iceberg-thermodynamic-model/data/input/processed/ocean/stage83_synthetic"
        ),
    )
    args = parser.parse_args()

    # Load model grid
    grid = load_model_grid()
    global lat, lon, wet, depth_cm, is1, js1, kt1
    lat = grid["lat"]
    lon = grid["lon"]
    wet = grid["wet"]
    depth_cm = grid["water_depth_cm"]
    is1, js1 = lat.shape

    # Compute kt1 (water column levels) from depth
    # kt1 = number of model levels with depth > z(k)
    kt1 = np.zeros((is1, js1), dtype=np.int64)
    for i in range(is1):
        for j in range(js1):
            if depth_cm is not None and depth_cm[i, j] != 8888.0 and depth_cm[i, j] > 0:
                kt1[i, j] = np.searchsorted(Z_CM, depth_cm[i, j], side="right")
            else:
                kt1[i, j] = 0

    print(
        f"Generating synthetic T/S: L={args.L_km} km, A_rho={args.A_rho} g/cm³, σ={args.sigma}"
    )

    T_3d, S_3d, rho_3d = create_synthetic_ts(
        lat, lon, L_m=args.L_km * 1000.0, A_rho=args.A_rho, sigma_cells=args.sigma
    )

    # Print diagnostics
    print(f"T range: {np.min(T_3d):.2f} - {np.max(T_3d):.2f} °C")
    print(f"S range: {np.min(S_3d):.6f} - {np.max(S_3d):.6f}")
    print(f"rho range: {np.min(rho_3d):.6f} - {np.max(rho_3d):.6f} g/cm³")

    # Write NetCDF
    out_file = write_synthetic_ts_nc(T_3d, S_3d, rho_3d, args.run_id, args.output_dir)

    # Also write a JSON with metadata
    meta = {
        "run_id": args.run_id,
        "L_km": args.L_km,
        "A_rho_gcm3": args.A_rho,
        "sigma_cells": args.sigma,
        "T_bg": 2.0,
        "S_bg": 0.0349,
        "file": str(out_file),
        "rho_min": float(np.min(rho_3d)),
        "rho_max": float(np.max(rho_3d)),
        "T_min": float(np.min(T_3d)),
        "T_max": float(np.max(T_3d)),
        "S_min": float(np.min(S_3d)),
        "S_max": float(np.max(S_3d)),
    }
    with open(args.output_dir / f"{args.run_id}_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Generated: {out_file}")


if __name__ == "__main__":
    main()
