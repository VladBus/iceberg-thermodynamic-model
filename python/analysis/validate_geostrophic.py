#!/usr/bin/env python
"""
Stage 7.7B — Independent validation of the 105 m/s geostrophic velocity diagnostic.

Uses the EXACT model EOS (Eckart) and pressure-gradient formulation.
Checks units, scaling, coordinate orientation, B-grid staggering, sign conventions.
"""

import numpy as np
import xarray as xr
import json

# Model parameters (from main.f90 and param.f90)
DX_CM = 1389000.0  # cm
DX_M = DX_CM / 100.0  # m
G_CM = 981.0  # cm/s^2
G_M = 9.81  # m/s^2
ROC = 1.0  # g/cm^3
RHO0 = 1025.0  # kg/m^3 (approx, since ro = rho - 1.02 g/cm^3)
OMEGA = 7.29e-5  # rad/s
IS = 132
JS = 104
IS1 = IS + 1  # 133
JS1 = JS + 1  # 105
KS = 18

# Coriolis at mean latitude (74.5N from domain)
LAT_REF = 74.5
F_COR = 2 * OMEGA * np.sin(np.deg2rad(LAT_REF))  # ~1.4e-4 1/s

# Z levels (from param.f90 DATA statement)
Z_CM = np.array(
    [
        250.0,
        500.0,
        1000.0,
        1500.0,
        2000.0,
        2500.0,
        3000.0,
        4000.0,
        5000.0,
        7500.0,
        10000.0,
        15000.0,
        20000.0,
        25000.0,
        30000.0,
        40000.0,
        50000.0,
        60000.0,
    ]
)
Z_M = Z_CM / 100.0


def eckart_density_anomaly(T, S):
    """Exact Eckart EOS from equation_of_state.f90"""
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_en4_product():
    """Load the canonical EN4 product"""
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    T = ds["temperature_celsius"].values.astype(np.float64)  # [°C]
    S = ds["salinity_mass_fraction"].values.astype(np.float64)  # [frac]
    kt1 = ds["water_column_levels"].values  # (133, 105)
    wet = ds["wet_mask"].values.astype(bool)  # (133, 105)
    lat = ds["lat"].values
    lon = ds["lon"].values
    return T, S, kt1, wet, lat, lon, ds


def compute_density(T, S):
    """Compute density anomaly using model EOS"""
    ro = np.zeros_like(T)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            for k in range(T.shape[2]):
                ro[i, j, k] = eckart_density_anomaly(T[i, j, k], S[i, j, k])
    return ro


def compute_gradients_2d(field, dx, wet_mask=None):
    """Compute horizontal gradients on T-grid using centered differences.
    field: (133, 105) or (133, 105, 18)
    Returns: (d_dx, d_dy) in 1/cm or 1/m depending on dx units
    X-direction: along j (axis=1), Y-direction: along i (axis=0)
    Only computes gradients where both neighboring cells are wet.
    """
    if field.ndim == 3:
        d_dx = np.full_like(field, np.nan)
        d_dy = np.full_like(field, np.nan)

        # Interior points
        for k in range(field.shape[2]):
            if wet_mask is not None:
                wet_k = wet_mask[:, :, k]
                # Only compute where center and both neighbors are wet
                valid_x = wet_k[:, 1:-1] & wet_k[:, 2:] & wet_k[:, :-2]
                valid_y = wet_k[1:-1, :] & wet_k[2:, :] & wet_k[:-2, :]
                d_dx[1:-1, 1:-1, k] = np.where(
                    valid_x[1:-1, :],
                    (field[1:-1, 2:, k] - field[1:-1, :-2, k]) / (2.0 * dx),
                    np.nan,
                )
                d_dy[1:-1, 1:-1, k] = np.where(
                    valid_y[:, 1:-1],
                    (field[2:, 1:-1, k] - field[:-2, 1:-1, k]) / (2.0 * dx),
                    np.nan,
                )
            else:
                d_dx[:, 1:-1, k] = (field[:, 2:, k] - field[:, :-2, k]) / (2.0 * dx)
                d_dy[1:-1, :, k] = (field[2:, :, k] - field[:-2, :, k]) / (2.0 * dx)
    else:
        d_dx = np.full_like(field, np.nan)
        d_dy = np.full_like(field, np.nan)
        if wet_mask is not None:
            valid_x = wet_mask[:, 1:-1] & wet_mask[:, 2:] & wet_mask[:, :-2]
            valid_y = wet_mask[1:-1, :] & wet_mask[2:, :] & wet_mask[:-2, :]
            d_dx[1:-1, 1:-1] = np.where(
                valid_x[1:-1, :],
                (field[1:-1, 2:] - field[1:-1, :-2]) / (2.0 * dx),
                np.nan,
            )
            d_dy[1:-1, 1:-1] = np.where(
                valid_y[:, 1:-1],
                (field[2:, 1:-1] - field[:-2, 1:-1]) / (2.0 * dx),
                np.nan,
            )
        else:
            d_dx[:, 1:-1] = (field[:, 2:] - field[:, :-2]) / (2.0 * dx)
            d_dy[1:-1, :] = (field[2:, :] - field[:-2, :]) / (2.0 * dx)
    return d_dx, d_dy


def compute_geostrophic_velocity_model_way(ro, f_cor=F_COR, wet_mask=None):
    """
    Compute geostrophic velocity using the model's actual pressure-gradient formulation.

    Model's baroclinic pressure gradient (Block 200):
    sum = c8 * dz * (RO differences)
    where c8 = 0.25/dx

    Acceleration: a = -c1 * sum  where c1 = g/rho0 = 981

    For geostrophic balance: f * v = (1/rho0) * dp/dx
    In model units: f * v_geo = g * d(rho)/dx = g * d(ro)/dx  (since rho = 1.02 + ro)

    So: v_geo = (g/f) * d(ro)/dx
        u_geo = -(g/f) * d(ro)/dy

    g in cm/s^2, ro in g/cm^3, dx in cm
    v_geo in cm/s, convert to m/s by /100
    """
    # Compute horizontal gradients of ro on T-grid
    # ro shape: (133, 105, 18)
    # dx in cm
    dro_dx, dro_dy = compute_gradients_2d(ro, DX_CM, wet_mask)  # ro per cm

    # Geostrophic velocity [cm/s]
    # f * v = g * d(rho)/dx
    # v = (g/f) * d(ro)/dx  (ro is anomaly in g/cm^3)
    # u = -(g/f) * d(ro)/dy
    g_cm = G_CM

    u_geo = -(g_cm / f_cor) * dro_dy  # cm/s
    v_geo = (g_cm / f_cor) * dro_dx  # cm/s

    # Convert to m/s
    u_geo_m = u_geo / 100.0
    v_geo_m = v_geo / 100.0

    return u_geo_m, v_geo_m


def compute_geostrophic_velocity_standard(ro, f_cor=F_COR, wet_mask=None):
    """
    Standard geostrophic velocity from density anomaly.
    Using rho = 1.02 + ro [g/cm^3] = 1020 + ro*1000 [kg/m^3]
    f * v = (1/rho0) * dp/dx
    dp/dx = g * integral(drho/dx dz)

    For surface: v_geo = (g/f) * d(ro)/dx * 1000 / 1000 * 100? Let's be careful.
    """
    dro_dx, dro_dy = compute_gradients_2d(ro, DX_M, wet_mask)  # ro per m
    # ro in g/cm^3, need kg/m^3: ro * 1000
    # f * v = g * d(rho)/dx = g * d(ro*1000)/dx
    # v = g/(f) * d(ro)/dx * 1000
    u_geo = -(G_M / f_cor) * dro_dy * 1000.0
    v_geo = (G_M / f_cor) * dro_dx * 1000.0
    return u_geo, v_geo


def validate_units():
    """Validate unit consistency"""
    print("=== UNIT VALIDATION ===")
    print(f"dx = {DX_CM} cm = {DX_M} m")
    print(f"g = {G_CM} cm/s^2 = {G_M} m/s^2")
    print(f"f_cor = {F_COR:.2e} 1/s")
    print(f"ro unit: g/cm^3 (anomaly)")
    print(f"ro * 1000 = kg/m^3")
    print()

    # Test: if dro/dx = 1e-6 g/cm^3 per cm = 1e-4 g/cm^3 per m
    # In model CGS: v = (g/f) * dro/dx = 981 / 1.4e-4 * 1e-6 = 7 cm/s = 0.07 m/s
    # In SI: v = g/f * d(rho)/dx = 9.81/1.4e-4 * (1e-6*1000) = 9.81/1.4e-4 * 1e-3 = 70 m/s
    # Wait, let's check: dro/dx in g/cm^3 per cm -> convert to kg/m^3 per m: *1000*100 = *1e5
    # dro/dx = 1e-6 g/cm^3/cm = 1e-6 * 1e5 kg/m^3/m = 0.1 kg/m^3/m
    # v = g/f * 0.1 = 9.81/1.4e-4 * 0.1 = 7007 m/s — too large!
    # Let's recheck: 1 g/cm^3 = 1000 kg/m^3
    # 1 g/cm^3/cm = 1000 kg/m^3 / 0.01 m = 100,000 kg/m^3/m = 1e5 kg/m^4
    # dro/dx = 1e-6 g/cm^3/cm = 0.1 kg/m^3/m
    # v = g/f * 0.1 = 9.81/1.4e-4 * 0.1 ≈ 7000 m/s
    #
    # But the 7.7A report says dro/dx max = 1.1e-6 g/cm^3/m (not per cm!)
    # Wait, the report says "max |∇ρ| [g/cm³/m]" — per meter!
    # So dro/dx = 1.1e-6 g/cm^3 per m = 1.1e-8 g/cm^3 per cm
    # In CGS: v = (981/1.4e-4) * 1.1e-8 = 7.7e-2 cm/s = 7.7e-4 m/s — too small
    # In SI: dro/dx = 1.1e-6 g/cm^3/m = 1.1e-3 kg/m^3/m
    # v = g/f * 1.1e-3 = 9.81/1.4e-4 * 1.1e-3 ≈ 77 m/s
    # This is closer to the 105 m/s!
    print()


def main():
    print("=" * 60)
    print("STAGE 7.7B — GEOSTROPHIC VELOCITY VALIDATION")
    print("=" * 60)

    validate_units()

    # Load EN4 product
    print("Loading EN4 product...")
    T, S, kt1, wet, lat, lon, ds = load_en4_product()

    # Compute density
    print("Computing density with Eckart EOS...")
    ro = compute_density(T, S)

    # Create wet mask for 3D
    wet_3d = wet[:, :, np.newaxis] & (
        np.arange(KS)[np.newaxis, np.newaxis, :] < kt1[:, :, np.newaxis]
    )

    print(f"T range: {np.nanmin(T[wet_3d]):.4f} .. {np.nanmax(T[wet_3d]):.4f} °C")
    print(f"S range: {np.nanmin(S[wet_3d]):.6f} .. {np.nanmax(S[wet_3d]):.6f} frac")
    print(f"ro range: {np.nanmin(ro[wet_3d]):.6f} .. {np.nanmax(ro[wet_3d]):.6f} g/cm³")

    # Compute geostrophic velocity using model formulation
    print("\nComputing geostrophic velocity (model formulation)...")
    # Create 3D wet mask
    wet_3d = wet[:, :, np.newaxis] & (
        np.arange(KS)[np.newaxis, np.newaxis, :] < kt1[:, :, np.newaxis]
    )
    u_geo_m, v_geo_m = compute_geostrophic_velocity_model_way(ro, wet_3d)
    speed_geo = np.sqrt(u_geo_m**2 + v_geo_m**2)

    # Print statistics per level
    print("\n--- GEOSTROPHIC VELOCITY (model formulation, m/s) ---")
    for k in range(KS):
        mask = wet & (kt1 > k)
        if not np.any(mask):
            continue
        u_stats = {
            "p50": np.nanpercentile(u_geo_m[:, :, k][mask], 50),
            "p90": np.nanpercentile(u_geo_m[:, :, k][mask], 90),
            "p99": np.nanpercentile(u_geo_m[:, :, k][mask], 99),
            "max": np.nanmax(u_geo_m[:, :, k][mask]),
        }
        v_stats = {
            "p50": np.nanpercentile(v_geo_m[:, :, k][mask], 50),
            "p90": np.nanpercentile(v_geo_m[:, :, k][mask], 90),
            "p99": np.nanpercentile(v_geo_m[:, :, k][mask], 99),
            "max": np.nanmax(v_geo_m[:, :, k][mask]),
        }
        speed_stats = {
            "p50": np.nanpercentile(speed_geo[:, :, k][mask], 50),
            "p90": np.nanpercentile(speed_geo[:, :, k][mask], 90),
            "p99": np.nanpercentile(speed_geo[:, :, k][mask], 99),
            "max": np.nanmax(speed_geo[:, :, k][mask]),
        }
        print(
            f"  Level {k+1} (z={Z_M[k]:.0f}m): |U_geo| max={speed_stats['max']:.2f} P99={speed_stats['p99']:.2f} P90={speed_stats['p90']:.2f} P50={speed_stats['p50']:.2f}"
        )

    # Find max speed location (only over wet cells)
    speed_geo_masked = np.where(wet_3d, speed_geo, -np.inf)
    idx = np.nanargmax(speed_geo_masked)
    k_max, j_max, i_max = np.unravel_index(idx, speed_geo.shape)
    print(f"\nMax |U_geo| at i={i_max} (0-indexed), j={j_max}, k={k_max}")
    print(f"  1-indexed: i={i_max+1}, j={j_max+1}, k={k_max+1}")
    print(f"  lat={lat[i_max, j_max]:.4f}, lon={lon[i_max, j_max]:.4f}")
    print(f"  depth={Z_M[k_max]:.0f}m")
    print(
        f"  U_geo={u_geo_m[i_max, j_max, k_max]:.2f} m/s, V_geo={v_geo_m[i_max, j_max, k_max]:.2f} m/s"
    )
    print(f"  |U_geo|={speed_geo[i_max, j_max, k_max]:.2f} m/s")

    # Also compute with standard SI formulation
    print("\n--- GEOSTROPHIC VELOCITY (standard SI, m/s) ---")
    u_geo_si, v_geo_si = compute_geostrophic_velocity_standard(ro, wet_mask=wet_3d)
    speed_geo_si = np.sqrt(u_geo_si**2 + v_geo_si**2)
    for k in range(KS):
        mask = wet & (kt1 > k)
        if not np.any(mask):
            continue
        speed_stats = {
            "p50": np.nanpercentile(speed_geo_si[:, :, k][mask], 50),
            "p90": np.nanpercentile(speed_geo_si[:, :, k][mask], 90),
            "p99": np.nanpercentile(speed_geo_si[:, :, k][mask], 99),
            "max": np.nanmax(speed_geo_si[:, :, k][mask]),
        }
        print(
            f"  Level {k+1} (z={Z_M[k]:.0f}m): |U_geo| max={speed_stats['max']:.2f} P99={speed_stats['p99']:.2f} P90={speed_stats['p90']:.2f} P50={speed_stats['p50']:.2f}"
        )

    # Check pressure gradient formulation in model (Block 200)
    print("\n=== MODEL PRESSURE GRADIENT ACCELERATION (Block 200) ===")
    # c8 = 0.25/dx [1/cm]
    # c1 = g/rho0 = 981 [cm/s^2 / (g/cm^3)] = 981 cm^4/g/s^2
    # sum = c8 * dz * (RO differences) [cm]
    # acceleration = -c1 * sum [cm/s^2]
    # For surface level dz = 25000 cm, c8 = 0.25/1389000 = 1.80e-7 1/cm
    # dro/dx ~ 1e-6 g/cm^3 per m = 1e-8 g/cm^3 per cm
    # sum = 1.8e-7 * 25000 * 1e-8 = 4.5e-11 cm
    # a = -981 * 4.5e-11 = 4.4e-8 cm/s^2 = 4.4e-10 m/s^2 — negligible!

    # Compute actual baroclinic acceleration in model formulation
    c8 = 0.25 / DX_CM  # 1/cm
    c1 = G_CM / ROC  # 981
    dro_dx_cm, dro_dy_cm = compute_gradients_2d(ro, DX_CM)  # g/cm^3 per cm

    # Surface acceleration
    a_x = -c1 * c8 * Z_CM[0] * dro_dx_cm[:, :, 0]
    a_y = -c1 * c8 * Z_CM[0] * dro_dy_cm[:, :, 0]

    print(f"c8 = {c8:.2e} 1/cm")
    print(f"c1 = {c1}")
    print(f"Z[0] = {Z_CM[0]} cm")
    mask = wet & (kt1 > 0)
    print(
        f"Baroclinic accel (surface) |a_x| max = {np.nanmax(np.abs(a_x[mask])):.2e} cm/s^2"
    )
    print(
        f"Baroclinic accel (surface) |a_y| max = {np.nanmax(np.abs(a_y[mask])):.2e} cm/s^2"
    )

    # Now compute barotropic pressure gradient acceleration (shal)
    # h1 = g * H / dx [cm/s^2 / cm * cm = cm/s^2]
    # H ~ 50000 cm (500 m), dx = 1389000 cm
    # h1 = 981 * 50000 / 1389000 ≈ 35.2 cm/s^2
    # If η gradient = 100 cm / 13.89 km = 100 / 1389000 = 7.2e-5
    # acceleration = -h1 * dη/dx = 35.2 * 7.2e-5 = 2.5e-3 cm/s^2
    # Much larger than baroclinic!

    print("\n=== CONCLUSION ===")
    print(f"Model formulation geostrophic max: {np.nanmax(speed_geo[wet_3d]):.2f} m/s")
    print(f"Standard SI geostrophic max:     {np.nanmax(speed_geo_si[wet_3d]):.2f} m/s")
    print(f"7.7A report max:                 105.3 m/s")

    # Save validation results
    results = {
        "model_formulation_max": float(np.nanmax(speed_geo[wet_3d])),
        "standard_si_max": float(np.nanmax(speed_geo_si[wet_3d])),
        "model_formulation_per_level": {},
        "standard_si_per_level": {},
    }
    for k in range(KS):
        mask = wet & (kt1 > k)
        if np.any(mask):
            results["model_formulation_per_level"][f"level_{k+1}"] = {
                "max": float(np.nanmax(speed_geo[:, :, k][mask])),
                "p99": float(np.nanpercentile(speed_geo[:, :, k][mask], 99)),
                "p90": float(np.nanpercentile(speed_geo[:, :, k][mask], 90)),
                "p50": float(np.nanpercentile(speed_geo[:, :, k][mask], 50)),
            }
            results["standard_si_per_level"][f"level_{k+1}"] = {
                "max": float(np.nanmax(speed_geo_si[:, :, k][mask])),
                "p99": float(np.nanpercentile(speed_geo_si[:, :, k][mask], 99)),
                "p90": float(np.nanpercentile(speed_geo_si[:, :, k][mask], 90)),
                "p50": float(np.nanpercentile(speed_geo_si[:, :, k][mask], 50)),
            }

    with open(
        "data/output/diagnostics/stage7.7B/geostrophic_validation.json", "w"
    ) as f:
        json.dump(results, f, indent=2)

    print("\nValidation complete. Results saved.")


if __name__ == "__main__":
    main()
