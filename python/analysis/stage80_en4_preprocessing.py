#!/usr/bin/env python3
"""
Stage 8.0 PHASE 1-7 — EN4 Preprocessing Audit with Multiple Interpolation Methods

Compares nearest-neighbor, bilinear, and smoothed interpolations for EN4 to model grid.
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import xarray as xr
from scipy.spatial import cKDTree
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter

PROJ_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJ_ROOT / "python" / "ice"))

from build_initial_ice import load_model_grid

# Model Z-level centres in cm (src/param.f90 data z / ...). Positive down.
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
KS = 18
IS1, JS1 = 133, 105
DX_M = 13890.0  # model grid spacing in meters

DEFAULT_RAW = pathlib.Path("data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc")
DEFAULT_OUT_DIR = pathlib.Path("data/output/diagnostics/stage8.0")


def eckart_ro(t_c, s_frac, dtype=np.float32):
    """Eckart density anomaly ro = rho - 1.02 [g/cm3] (float32, model-faithful)."""
    t = np.asarray(t_c, dtype=dtype)
    s = np.asarray(s_frac, dtype=dtype)
    aa = 1779.5 + (11.25 - 0.0745 * t) * t - (3800.0 + 10.0 * t) * s
    bb = 5891.0 + 3000.0 * s + (38.0 - 0.375 * t) * t
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_model_grid():
    """Load model grid (lat/lon at T-points) from build_initial_ice."""
    from build_initial_ice import load_model_grid as _load_model_grid

    return _load_model_grid()


def load_model_grid_data():
    """Load model grid (lat/lon at T-points)."""
    g = load_model_grid()
    lat = g["lat"]
    lon = g["lon"]
    depth_cm = g["water_depth_cm"]
    wet = g["wet"].astype(bool)
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
    kt1 = np.zeros_like(depth_cm, dtype=np.int32)
    for i in range(depth_cm.shape[0]):
        for j in range(depth_cm.shape[1]):
            if depth_cm[i, j] > 0:
                kt1[i, j] = np.searchsorted(Z_CM, depth_cm[i, j], side="right")
            else:
                kt1[i, j] = 0
    return lat, lon, kt1, wet


def load_en4_raw(raw_path):
    """Load raw EN4 data."""
    ds = xr.open_dataset(raw_path)
    t_k = ds["temperature"].isel(time=0).values  # K
    s_p = ds["salinity"].isel(time=0).values
    d_en4 = ds["depth"].values
    en4_lat = ds["lat"].values
    en4_lon = ds["lon"].values
    return t_k, s_p, d_en4, en4_lat, en4_lon


def load_en4_and_model_grid(raw_path):
    """Load EN4 raw data and model grid."""
    with xr.open_dataset(raw_path) as ds:
        t_k = ds["temperature"].isel(time=0).values.astype(np.float32)  # K
        s_p = ds["salinity"].isel(time=0).values.astype(np.float32)
        d_en4 = ds["depth"].values
        en4_lat = ds["lat"].values
        en4_lon = ds["lon"].values

    t_c = (t_k - 273.15).astype(np.float32)
    s_f = (s_p / 1000.0).astype(np.float32)

    model_lat, model_lon, kt1, wet = load_model_grid_data()
    return t_c, s_f, d_en4, en4_lat, en4_lon, model_lat, model_lon, kt1, wet


def nearest_neighbor_horizontal(
    t_c, s_f, d_en4, en4_lat, en4_lon, model_lat, model_lon, model_wet
):
    """Current nearest-neighbor horizontal interpolation (baseline)."""
    is1, js1 = IS1, JS1
    ks = KS

    # EN4 wet points
    en4_wet = np.any(np.isfinite(t_c), axis=0)
    en4_rc = np.argwhere(en4_wet)
    en4_pts = np.column_stack([en4_lat[en4_rc[:, 0]], en4_lon[en4_rc[:, 1]]])
    tree = cKDTree(en4_pts, compact_nodes=True, balanced_tree=True)

    model_pts = np.column_stack([model_lat.ravel(), model_lon.ravel()])
    dist, ind = tree.query(model_pts, k=1, workers=-1)
    ilat = en4_rc[ind, 0].reshape(IS1, JS1)
    ilon = en4_rc[ind, 1].reshape(IS1, JS1)

    t_out = np.zeros((IS1, JS1, KS), dtype=np.float32)
    s_out = np.zeros((IS1, JS1, KS), dtype=np.float32)

    for d in range(42):
        t_interp = t_c[d][ilat, ilon]
        s_interp = s_f[d][ilat, ilon]

    # Vertical interpolation
    en4_depth = d_en4 / 100.0  # convert to meters

    for k in range(KS):
        z_target = Z_M[k]
        depth_idx = np.searchsorted(d_en4, z_target * 100)  # d_en4 is in cm
        if depth_idx == 0:
            t_out[:, :, k] = t_c[0][ilat, ilon]
            s_out[:, :, k] = s_f[0][ilat, ilon]
        elif depth_idx >= len(d_en4):
            t_out[:, :, k] = t_c[-1][ilat, ilon]
            s_out[:, :, k] = s_f[-1][ilat, ilon]
        else:
            w = (z_target - en4_depth[depth_idx - 1]) / (
                en4_depth[depth_idx] - en4_depth[depth_idx - 1]
            )
            t_out[:, :, k] = (1 - w) * t_c[depth_idx - 1][ilat, ilon] + w * t_c[
                depth_idx
            ][ilat, ilon]
            s_out[:, :, k] = (1 - w) * s_f[depth_idx - 1][ilat, ilon] + w * s_f[
                depth_idx
            ][ilat, ilon]

    return t_out, s_out


def bilinear_horizontal(t_c, s_f, d_en4, en4_lat, en4_lon, model_lat, model_lon):
    """Bilinear interpolation from EN4 grid to model grid."""
    is1, js1 = IS1, JS1
    ks = KS

    # EN4 coordinates
    en4_lat = en4_lat
    en4_lon = en4_lon

    # Create interpolators for each depth level and evaluate on model grid
    interp_t_vals = np.zeros((42, IS1, JS1), dtype=np.float32)
    interp_s_vals = np.zeros((42, IS1, JS1), dtype=np.float32)

    for d in range(42):
        interp_t = RegularGridInterpolator(
            (en4_lat, en4_lon),
            t_c[d],  # EN4 is (lat, lon) = (173, 360), NO transpose
            method="linear",
            bounds_error=False,
            fill_value=np.nan,
        )
        interp_s = RegularGridInterpolator(
            (en4_lat, en4_lon),
            s_f[d],
            method="linear",
            bounds_error=False,
            fill_value=np.nan,
        )
        # Evaluate on model grid
        points = np.column_stack([model_lat.ravel(), model_lon.ravel()])
        interp_t_vals[d] = interp_t(points).reshape(IS1, JS1)
        interp_s_vals[d] = interp_s(points).reshape(IS1, JS1)

    # Now interpolate vertically to model levels
    t_out = np.zeros((IS1, JS1, KS), dtype=np.float32)
    s_out = np.zeros((IS1, JS1, KS), dtype=np.float32)

    Z_M = np.array(
        [
            2.5,
            5.0,
            7.5,
            12.5,
            17.5,
            25.0,
            40.0,
            50.0,
            62.5,
            75.0,
            100.0,
            125.0,
            175.0,
            225.0,
            275.0,
            350.0,
            450.0,
            550.0,
        ]
    )  # model level centers in m

    en4_depth = d_en4 / 100.0  # convert to meters

    for k in range(KS):
        z_target = Z_M[k]
        depth_idx = np.searchsorted(en4_depth, z_target)
        if depth_idx == 0:
            t_out[:, :, k] = interp_t_vals[0]
            s_out[:, :, k] = interp_s_vals[0]
        elif depth_idx >= len(en4_depth):
            t_out[:, :, k] = interp_t_vals[-1]
            s_out[:, :, k] = interp_s_vals[-1]
        else:
            w = (z_target - en4_depth[depth_idx - 1]) / (
                en4_depth[depth_idx] - en4_depth[depth_idx - 1]
            )
            t_out[:, :, k] = (1 - w) * interp_t_vals[depth_idx - 1] + w * interp_t_vals[
                depth_idx
            ]
            s_out[:, :, k] = (1 - w) * interp_s_vals[depth_idx - 1] + w * interp_s_vals[
                depth_idx
            ]

    return t_out, s_out


def gaussian_smooth_horizontal(t, s, sigma_km, dx_km=13.89):
    """Apply Gaussian smoothing to horizontal fields."""
    sigma_grid = sigma_km / dx_km
    t_smooth = np.zeros_like(t)
    s_smooth = np.zeros_like(s)
    for k in range(t.shape[2]):
        t_smooth[:, :, k] = gaussian_filter(t[:, :, k], sigma=sigma_grid)
        s_smooth[:, :, k] = gaussian_filter(s[:, :, k], sigma=sigma_grid)
    return t_smooth, s_smooth


def compute_density(t_c, s_f):
    """Compute density anomaly from T [°C] and S [frac]."""
    ro = np.zeros((IS1, JS1, KS), dtype=np.float32)
    for k in range(KS):
        for i in range(IS1):
            for j in range(JS1):
                ro[i, j, k] = eckart_ro(t_c[i, j, k], s_f[i, j, k])
    return ro


def compute_density_gradients(ro, dx_m=13890.0):
    """Compute horizontal density gradients on model grid (centered differences)."""
    is1, js1, ks = ro.shape
    grad_x = np.zeros_like(ro)
    grad_y = np.zeros_like(ro)

    for k in range(ks):
        grad_x[1:-1, 1:-1, k] = (ro[1:-1, 2:, k] - ro[1:-1, :-2, k]) / (2 * dx_m)
        grad_y[1:-1, 1:-1, k] = (ro[2:, 1:-1, k] - ro[:-2, 1:-1, k]) / (2 * dx_m)
    return grad_x, grad_y


def compute_dynamic_height(ro, z_m, ref_depth_m=600):
    """Compute dynamic height relative to reference depth.

    D(x,y) = -∫_{z_ref}^{0} (ρ(x,y,z) - ρ₀) / ρ₀ dz
    where ρ₀ = 1025 kg/m³
    ro is in g/cm³, so ρ = 1.02 + ro g/cm³ = 1020 + ro*1000 kg/m³
    """
    rho0 = 1025.0  # kg/m³
    is1, js1, ks = ro.shape
    D = np.zeros((is1, js1))

    # ro is in g/cm³, convert to kg/m³ anomaly: ro * 1000 kg/m³
    ro_si = ro * 1000.0  # kg/m³

    for k in range(ks):
        if z_m[k] <= ref_depth_m:
            # Layer thickness
            if k == 0:
                dz = z_m[0]
            else:
                dz = z_m[k] - z_m[k - 1]
            # Add contribution from this layer
            D -= (ro_si[:, :, k] / 1025.0) * dz
    return D


def compute_thermal_wind_from_ro(ro, dx_m=13890.0, f_cor=1.4e-4):
    """Compute thermal-wind velocity from density anomaly.

    f * v = (g/ρ₀) * ∫ ∂ρ/∂x dz
    f * u = -(g/ρ₀) * ∫ ∂ρ/∂y dz
    """
    g = 9.81
    rho0 = 1025.0
    f = f_cor

    # ro is in g/cm³, convert to kg/m³
    ro_si = ro * 1000.0  # kg/m³

    # Compute density gradients
    grad_x, grad_y = compute_density_gradients(ro)

    # Convert gradients to SI: g/cm³/m -> kg/m⁴
    grad_x_si = grad_x * 1000.0  # kg/m⁴
    grad_y_si = grad_y * 1000.0  # kg/m⁴

    # Vertical integration from surface to each level
    U = np.zeros((IS1, JS1, KS))
    V = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        # Integrate from surface to level k
        if k == 0:
            dz = Z_M[0]
        else:
            dz = Z_M[k] - Z_M[k - 1]

        # For first level, just use the surface gradient
        if k == 0:
            v_integral = grad_x_si[:, :, 0] * Z_M[0]
            u_integral = grad_y_si[:, :, 0] * Z_M[0]
        else:
            v_integral = np.sum(
                grad_x_si[:, :, : k + 1]
                * np.diff(np.concatenate([[0], Z_M[: k + 1]]))[:, None, None],
                axis=2,
            )
            u_integral = np.sum(
                grad_y_si[:, :, : k + 1]
                * np.diff(np.concatenate([[0], Z_M[: k + 1]]))[:, None, None],
                axis=2,
            )

        V[:, :, k] = (g / (rho0 * f)) * v_integral
        U[:, :, k] = -(g / (rho0 * f)) * u_integral

    return U, V


def compute_ssh_from_dynamic_height(D, dx_m=13890.0, f_cor=1.4e-4):
    """Compute SSH from dynamic height using geostrophic balance.

    f * v = g * ∂D/∂x
    f * u = -g * ∂D/∂y
    """
    g = 9.81
    f = f_cor

    # Compute gradients of dynamic height
    D_grad_x, D_grad_y = compute_density_gradients(D, dx_m=13890.0)

    # SSH from geostrophic balance
    # f * v = g * ∂D/∂x  =>  v = g/f * ∂D/∂x
    # f * u = -g * ∂D/∂y  =>  u = -g/f * ∂D/∂y
    V_ssh = g / f * D_grad_x
    U_ssh = -g / f * D_grad_y

    return U_ssh, V_ssh


def compute_thermal_wind_velocity(
    ro, f_cor=1.4e-4, u_ref=0.0, v_ref=0.0, ref_level_k=17
):
    """Compute thermal-wind velocity with reference level."""
    g = 9.81
    rho0 = 1025.0
    f = 1.4e-4

    # ro is in g/cm³, convert to kg/m³
    ro_si = ro * 1000.0  # kg/m³

    # Compute density gradients
    grad_x, grad_y = compute_density_gradients(ro)

    # Convert gradients to SI: g/cm³/m -> kg/m⁴
    grad_x_si = grad_x * 1000.0  # kg/m⁴
    grad_y_si = grad_y * 1000.0  # kg/m⁴

    # Thermal wind shear
    # f * ∂v/∂z = (g/ρ₀) * ∂ρ/∂x
    # f * ∂u/∂z = -(g/ρ₀) * ∂ρ/∂y
    # ∂v/∂z = (g/(ρ₀*f)) * grad_x_si
    # ∂u/∂z = -(g/(ρ₀*f)) * grad_y_si

    U = np.zeros((IS1, JS1, KS))
    V = np.zeros((IS1, JS1, KS))

    # Set reference level velocity
    U[:, :, ref_level_k] = u_ref * 100.0  # m/s to cm/s
    V[:, :, ref_level_k] = v_ref * 100.0

    # Integrate upward from reference level (k < ref_level_k)
    integral_x = 0.0
    integral_y = 0.0
    for k in range(ref_level_k - 1, -1, -1):
        if k < KS - 1:
            dz = Z_M[k + 1] - Z_M[k]
        else:
            dz = Z_M[k] - Z_M[k - 1] if k > 0 else Z_M[0]

        integral_x += grad_x[:, :, k] * 1000.0 * dz / 100.0  # convert to cm
        integral_y += grad_y[:, :, k] * 1000.0 * dz / 100.0

        V[:, :, k] = v_ref * 100.0 + (9.81 / (1025.0 * 1.4e-4)) * integral_x
        U[:, :, k] = u_ref * 100.0 - (9.81 / (1025.0 * 1.4e-4)) * integral_y

    # Integrate downward from reference level (k > ref_level_k)
    integral_x = 0.0
    integral_y = 0.0
    for k in range(ref_level_k + 1, KS):
        dz = Z_M[k] - Z_M[k - 1]
        integral_x += grad_x[:, :, k - 1] * 1000.0 * dz / 100.0
        integral_y += grad_y[:, :, k - 1] * 1000.0 * dz / 100.0

        V[:, :, k] = v_ref * 100.0 - (9.81 / (1025.0 * 1.4e-4)) * integral_x
        U[:, :, k] = u_ref * 100.0 + (9.81 / (1025.0 * 1.4e-4)) * integral_y

    return U, V


def compute_dynamic_height_ssh(ro, z_m, ref_depth_m=600):
    """Compute SSH from dynamic height."""
    D = compute_dynamic_height(ro, z_m, ref_depth_m)
    U_ssh, V_ssh = compute_ssh_from_dynamic_height(D)
    return D, U_ssh, V_ssh


def compute_statistics(arr, mask=None):
    """Compute statistics for an array."""
    if mask is not None:
        arr = arr[mask]
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return {"max": 0.0, "p99": 0.0, "p90": 0.0, "p50": 0.0, "mean": 0.0}
    return {
        "max": float(np.max(arr)),
        "p99": float(np.percentile(arr, 99)),
        "p90": float(np.percentile(arr, 90)),
        "p50": float(np.percentile(arr, 50)),
        "mean": float(np.mean(arr)),
    }


def compute_interpolation(
    method, t_c, s_f, d_en4, en4_lat, en4_lon, model_lat, model_lon, model_wet
):
    """Compute interpolation based on method."""
    if method == "nearest":
        return nearest_neighbor_horizontal(
            t_c, s_f, en4_lat, en4_lon, model_lat, model_lon, model_wet
        )
    elif method == "bilinear":
        return bilinear_horizontal(
            t_c, s_f, d_en4, en4_lat, en4_lon, model_lat, model_lon
        )
    else:
        raise ValueError(f"Unknown method: {method}")


def run_interpolation_and_diagnostics(
    method_name,
    t_c,
    s_f,
    d_en4,
    en4_lat,
    en4_lon,
    model_lat,
    model_lon,
    model_wet,
    kt1,
    wet,
    smooth_sigma_km=0,
):
    """Run interpolation and compute diagnostics."""
    # Apply smoothing if requested
    if smooth_sigma_km > 0:
        t_c_smooth, s_f_smooth = gaussian_smooth_horizontal(t_c, s_f, smooth_sigma_km)
    else:
        t_c_smooth, s_f_smooth = t_c, s_f

    # Interpolate
    if method_name == "nearest":
        t_out, s_out = nearest_neighbor_horizontal(
            t_c_smooth, s_f_smooth, d_en4, en4_lat, en4_lon, model_lat, model_lon, wet
        )
    elif method_name.startswith("bilinear"):
        t_out, s_out = bilinear_horizontal(
            t_c_smooth, s_f_smooth, d_en4, en4_lat, en4_lon, model_lat, model_lon
        )
    else:
        raise ValueError(f"Unknown method: {method_name}")

    # Compute density
    ro = compute_density(t_out, s_out)

    # Compute density gradients
    grad_x, grad_y = compute_density_gradients(ro)

    # Compute statistics
    wet_mask = model_wet & (kt1 > 0)

    stats = {
        "method": method_name,
        "smooth_sigma_km": smooth_sigma_km,
        "density": compute_statistics(ro),
        "grad_x": compute_statistics(grad_x),
        "grad_y": compute_statistics(grad_y),
        "grad_mag": compute_statistics(np.sqrt(grad_x**2 + grad_y**2)),
    }

    # Density gradient at each level
    for k in range(KS):
        mask = model_wet & (kt1 > k)
        stats[f"level_{k+1}_grad_mag"] = compute_statistics(
            np.sqrt(grad_x[:, :, k] ** 2 + grad_y[:, :, k] ** 2), mask
        )

    return stats, t_out, s_out, ro


def main():
    parser = argparse.ArgumentParser(description="Stage 8.0 EN4 Preprocessing Audit")
    parser.add_argument(
        "--raw",
        type=pathlib.Path,
        default="data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc",
    )
    parser.add_argument(
        "--out-dir", type=pathlib.Path, default="data/output/diagnostics/stage8.0"
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Load model grid
    print("Loading model grid...")
    model_lat, model_lon, kt1, wet = load_model_grid_data()

    # Load EN4 raw data
    print("Loading EN4 raw data...")
    t_c, s_f, d_en4, en4_lat, en4_lon, model_lat, model_lon, kt1, wet = (
        load_en4_and_model_grid(DEFAULT_RAW)
    )

    # Compute model grid wet mask
    model_wet = wet & (kt1 > 0)

    results = {}

    # Test different interpolation methods
    methods = [
        ("nearest", {"method": "nearest", "smooth_sigma_km": 0}),
        ("bilinear", {"method": "bilinear", "smooth_sigma_km": 0}),
        ("bilinear_sigma2", {"method": "bilinear", "smooth_sigma_km": 2}),
        ("bilinear_sigma5", {"method": "bilinear", "smooth_sigma_km": 5}),
    ]

    all_results = {}

    for method_name, method_kwargs in methods:
        print(f"\n=== Method: {method_name} ===")
        stats, t_out, s_out, ro = run_interpolation_and_diagnostics(
            method_name,
            t_c,
            s_f,
            d_en4,
            en4_lat,
            en4_lon,
            model_lat,
            model_lon,
            model_wet,
            kt1,
            wet,
            method_kwargs.get("smooth_sigma_km", 0),
        )
        all_results[method_name] = stats
        print(f"  Max density: {stats['density']['max']:.6f} g/cm^3")
        print(f"  Max |grad|: {stats['grad_mag']['max']:.2e} g/cm^3/m")
        max_u = stats.get("max_u", "N/A")
        if isinstance(max_u, (int, float)):
            print(f"  Max U: {max_u:.2f} m/s")
        else:
            print(f"  Max U: {max_u}")

    # Save results
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "en4_preprocessing_audit.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n=== Stage 8.0 EN4 Preprocessing Audit Complete ===")


if __name__ == "__main__":
    main()
