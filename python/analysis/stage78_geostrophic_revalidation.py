#!/usr/bin/env python
"""
Stage 7.8 — Revalidation of EN4 geostrophic diagnostic using multiple independent methods.

Methods:
1. Stage 7.7C model discrete formulation (with the questionable factor of 2)
2. Model discrete formulation WITHOUT the factor of 2 (continuous geostrophic)
3. Standard continuous geostrophic (f*v = g/rho0 * dp/dx)
4. SI units independent calculation
5. CGS units independent calculation
6. Surface-referenced and 600m-referenced geostrophic

The goal is to determine whether the 5-60 m/s diagnostic is physically realistic
or whether it contains a formulation/unit/reference-level error.
"""

import numpy as np
import xarray as xr
import json
from pathlib import Path

# Model parameters
IS = 132
JS = 104
IS1 = IS + 1
JS1 = JS + 1
KS = 18
DX_CM = 1389000.0
DX_M = DX_CM / 100.0  # 13890 m
G_CM = 981.0
G_M = 9.81
ROC = 1.0  # g/cm^3
RHO0_CGS = 1.02  # g/cm^3 (model uses rho = 1.02 + ro)
RHO0_SI = 1025.0  # kg/m^3 (standard ocean)
OMEGA = 7.29e-5  # rad/s
LAT_REF = 74.5

# Z levels (centers)
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

DZ_CM = np.zeros(KS)
DZ_CM[0] = Z_CM[0]
for k in range(1, KS):
    DZ_CM[k] = Z_CM[k] - Z_CM[k - 1]


def eckart_density_anomaly(T, S):
    """Exact Eckart EOS from equation_of_state.f90"""
    aa = 1779.5 + (11.25 - 0.0745 * T) * T - (3800.0 + 10.0 * T) * S
    bb = 5891.0 + 3000.0 * S + (38.0 - 0.375 * T) * T
    return 1.0 / (0.698 + aa / bb) - 1.02


def load_en4_product():
    ds = xr.open_dataset("data/input/processed/ocean/initial_ts_2020-01-01.nc")
    T = ds["temperature_celsius"].values.astype(np.float64)
    S = ds["salinity_mass_fraction"].values.astype(np.float64)
    kt1 = ds["water_column_levels"].values
    wet = ds["wet_mask"].values.astype(bool)
    lat = ds["lat"].values
    lon = ds["lon"].values
    return T, S, kt1, wet, lat, lon, ds


def compute_density(T, S):
    ro = np.zeros_like(T)
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            for k in range(T.shape[2]):
                ro[i, j, k] = eckart_density_anomaly(T[i, j, k], S[i, j, k])
    return ro


def compute_fku(lat, wet):
    """Compute Coriolis at U-points (same as model)"""
    fku = np.zeros((IS1, JS1))
    for i in range(IS1):
        for j in range(JS1):
            if wet[i, j]:
                fku[i, j] = 2 * OMEGA * np.sin(np.deg2rad(lat[i, j]))
            else:
                fku[i, j] = np.nan
    return fku


def centered_gradient_2d(field, dx):
    """Centered gradient at interior points, NaN at boundaries"""
    grad_x = np.full_like(field, np.nan)
    grad_y = np.full_like(field, np.nan)
    grad_x[:, 1:-1] = (field[:, 2:] - field[:, :-2]) / (2.0 * dx)
    grad_y[1:-1, :] = (field[2:, :] - field[:-2, :]) / (2.0 * dx)
    return grad_x, grad_y


def method_stage77c(ro, kt1, fku):
    """
    Stage 7.7C method: exact Block 200 model formulation with factor of 2.
    V_geo = 2*C1*sum_x / f
    U_geo = -2*C1*sum_y / f
    """
    sum_x_cum = np.zeros((IS1, JS1, KS))
    sum_y_cum = np.zeros((IS1, JS1, KS))
    c8 = 0.25 / DX_CM

    for k in range(KS):
        # Delta RO_x at U-point (4-point stencil from Block 200)
        # Pad to full size
        delta_ro_x = np.zeros((IS1, JS1))
        delta_ro_x[1:IS1, 1:JS1] = (
            ro[0:IS, 1:JS1, k]
            + ro[1:IS1, 1:JS1, k]
            - ro[0:IS, 0:JS, k]
            - ro[1:IS1, 0:JS, k]
        )
        delta_ro_y = np.zeros((IS1, JS1))
        delta_ro_y[1:IS1, 1:JS1] = (
            ro[0:IS, 0:JS, k]
            + ro[0:IS, 1:JS1, k]
            - ro[1:IS1, 0:JS, k]
            - ro[1:IS1, 1:JS1, k]
        )
        if k == 0:
            sum_x_cum[:, :, k] = c8 * DZ_CM[k] * delta_ro_x
            sum_y_cum[:, :, k] = c8 * DZ_CM[k] * delta_ro_y
        else:
            sum_x_cum[:, :, k] = sum_x_cum[:, :, k - 1] + c8 * DZ_CM[k] * delta_ro_x
            sum_y_cum[:, :, k] = sum_y_cum[:, :, k - 1] + c8 * DZ_CM[k] * delta_ro_y

    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    U_geo = -2.0 * G_CM / ROC * sum_y_cum / f_safe[:, :, np.newaxis]
    V_geo = 2.0 * G_CM / ROC * sum_x_cum / f_safe[:, :, np.newaxis]
    return U_geo, V_geo


def method_model_no_factor2(ro, kt1, fku):
    """
    Model discrete formulation WITHOUT the factor of 2.
    V_geo = C1*sum_x / f
    U_geo = -C1*sum_y / f
    """
    sum_x_cum = np.zeros((IS1, JS1, KS))
    sum_y_cum = np.zeros((IS1, JS1, KS))
    c8 = 0.25 / DX_CM

    for k in range(KS):
        delta_ro_x = np.zeros((IS1, JS1))
        delta_ro_x[1:IS1, 1:JS1] = (
            ro[0:IS, 1:JS1, k]
            + ro[1:IS1, 1:JS1, k]
            - ro[0:IS, 0:JS, k]
            - ro[1:IS1, 0:JS, k]
        )
        delta_ro_y = np.zeros((IS1, JS1))
        delta_ro_y[1:IS1, 1:JS1] = (
            ro[0:IS, 0:JS, k]
            + ro[0:IS, 1:JS1, k]
            - ro[1:IS1, 0:JS, k]
            - ro[1:IS1, 1:JS1, k]
        )
        if k == 0:
            sum_x_cum[:, :, k] = c8 * DZ_CM[k] * delta_ro_x
            sum_y_cum[:, :, k] = c8 * DZ_CM[k] * delta_ro_y
        else:
            sum_x_cum[:, :, k] = sum_x_cum[:, :, k - 1] + c8 * DZ_CM[k] * delta_ro_x
            sum_y_cum[:, :, k] = sum_y_cum[:, :, k - 1] + c8 * DZ_CM[k] * delta_ro_y

    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    U_geo = -G_CM / ROC * sum_y_cum / f_safe[:, :, np.newaxis]
    V_geo = G_CM / ROC * sum_x_cum / f_safe[:, :, np.newaxis]
    return U_geo, V_geo


def method_continuous_si(ro, kt1, fku):
    """
    Standard continuous geostrophic in SI units.
    f*v = (1/rho0) * dp/dx
    where p is hydrostatic pressure.
    At level k: dp/dx = g * sum_{m=k}^{bottom} d(rho)/dx * dz
    But the model computes cumulative FROM SURFACE.
    For continuous: p at level k = g * integral from k to surface of rho dz
    dp/dx at level k = g * integral from k to surface of d(rho)/dx dz

    Actually, the model's sum is cumulative from surface to level k.
    In the model: sum(k) = integral from surface to k of d(ro)/dx dz
    Then -C1*sum(k) is the pressure gradient at level k.

    The standard geostrophic is: f*v = -(1/rho0)*dp/dx
    In the model: f*v_geo = 2*C1*sum/f (with factor 2 from semi-implicit)

    Without factor 2: f*v = C1*sum/f
    This is equivalent to: f*v = g/rho0 * integral_0^k d(ro)/dx dz

    In SI: f*v = (g/rho0) * integral_0^k d(rho_anomaly)/dx dz
    where ro_anomaly in kg/m^3 and dz in m
    """
    c8_si = 0.25 / DX_M  # 1/m
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    f_safe_3d = f_safe[:, :, np.newaxis]

    sum_x_cum = np.zeros((IS1, JS1, KS))
    sum_y_cum = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        # Convert ro from g/cm^3 to kg/m^3: multiply by 1000
        # But ro is already in g/cm^3, and we need SI
        # d(ro)/dx in g/cm^3 per m = (g/cm^3 per cm) * 100 = (g/cm^3 per m)
        # So d(ro_si)/dx in kg/m^3 per m = d(ro)/dx * 1000 * 100 = d(ro)/dx * 1e5
        # Actually simpler: convert ro to kg/m^3 first, then gradient
        ro_si = ro * 1000.0  # kg/m^3

        # Centered gradient at U-point (average of two T-point gradients)
        # d(ro_si)/dx at U-point (i,j) = 0.5*[d(ro_si)/dx at T(i,j) + d(ro_si)/dx at T(i,j-1)]
        dro_si_dx_T = np.full((IS1, JS1), np.nan)
        dro_si_dy_T = np.full((IS1, JS1), np.nan)
        for kk in range(KS):
            pass
        # Use the same 4-point stencil as model
        delta_ro_x = (
            ro_si[0:IS, 1:JS1, k]
            + ro_si[1:IS1, 1:JS1, k]
            - ro_si[0:IS, 0:JS, k]
            - ro_si[1:IS1, 0:JS, k]
        )
        delta_ro_y = (
            ro_si[0:IS, 0:JS, k]
            + ro_si[0:IS, 1:JS1, k]
            - ro_si[1:IS1, 0:JS, k]
            - ro_si[1:IS1, 1:JS1, k]
        )

        if k == 0:
            sum_x_cum[:, :, k] = c8_si * DZ_CM[k] / 100.0 * delta_ro_x
            sum_y_cum[:, :, k] = c8_si * DZ_CM[k] / 100.0 * delta_ro_y
        else:
            sum_x_cum[:, :, k] = (
                sum_x_cum[:, :, k - 1] + c8_si * DZ_CM[k] / 100.0 * delta_ro_x
            )
            sum_y_cum[:, :, k] = (
                sum_y_cum[:, :, k - 1] + c8_si * DZ_CM[k] / 100.0 * delta_ro_y
            )

    # f*v = (1/rho0) * dp/dx
    # dp/dx at level k = g * sum_x_cum(k) (already includes g through the 0.25/dx factor)
    # Wait, no. The c8 factor is just 0.25/dx, it doesn't include g.
    # The pressure gradient is: dp/dx = g * integral d(rho)/dx dz
    # In the model: -C1*sum = -(g/rho0) * c8 * integral d(ro)/dx dz
    # So the actual dp/dx = g * integral d(ro)/dx dz = g * sum_x_cum / c8

    # For continuous geostrophic: f*v = -(1/rho0) * dp/dx = -(1/rho0) * g * sum_x_cum / c8
    # = -(g/rho0) * sum_x_cum / c8

    # But the model uses: -C1*sum = -(g/rho0) * c8 * integral d(ro)/dx dz
    # So C1*sum = (g/rho0) * c8 * integral
    # And the model's geostrophic (no factor 2): V_geo = C1*sum/f
    # This equals: (g/rho0) * c8 * integral / f

    # For SI: V_geo = (g_si/rho0_si) * c8_si * integral_si / f
    # where integral_si is in kg/m^3 * m
    # c8_si = 0.25/dx_m
    # g_si = 9.81 m/s^2
    # rho0_si = 1025 kg/m^3

    g_si = 9.81
    rho0_si = 1025.0

    U_geo = -(g_si / rho0_si) * sum_y_cum / f_safe_3d
    V_geo = (g_si / rho0_si) * sum_x_cum / f_safe_3d
    return U_geo, V_geo


def method_surface_pressure_si(ro, kt1, fku):
    """
    Standard geostrophic from surface pressure.
    At level k: p(x,y,k) = g * integral from k to surface of rho dz
    dp/dx at level k = g * integral from k to surface of d(rho)/dx dz
    f*v = -(1/rho0) * dp/dx

    This is the continuous hydrostatic geostrophic.
    """
    c8_si = 0.25 / DX_M
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    f_safe_3d = f_safe[:, :, np.newaxis]

    g_si = 9.81
    rho0_si = 1025.0

    # Compute dp/dx by integrating FROM BOTTOM (or FROM SURFACE)
    # The standard oceanographic approach: p(z) = g * integral from z to 0 of rho dz'
    # Then v_geo = -(1/(rho0*f)) * dp/dx

    # For each level k, compute integral from surface (k=1) to level k
    # of d(rho)/dx dz
    # This is what the model does with sum_x_cum

    # But the sign convention matters.
    # Model: sum = c8 * integral_0^k d(ro)/dx dz
    # Pressure at level k: p(k) = p_surface + g * integral_0^k rho dz
    # dp/dx(k) = g * integral_0^k d(rho)/dx dz = g * sum_x_cum / c8

    # Geostrophic: f*v = (1/rho0) * dp/dx (in Northern Hemisphere, v positive northward)
    # In the model's convention: V_geo = C1*sum/f where C1 = g/rho0
    # So V_geo = (g/rho0) * sum / f = dp/dx / (rho0 * f) ... this is wrong sign

    # Let me be very careful with signs.
    # The momentum equation: du/dt - f*v = -(1/rho0) * dp/dx
    # Geostrophic: 0 - f*v_geo = -(1/rho0) * dp/dx
    # => f*v_geo = (1/rho0) * dp/dx
    # => v_geo = (1/(rho0*f)) * dp/dx

    # In the model:
    # AUU = U + (f*dt/2)*V + dt*(-C1*sum - dpx + ...)
    # Steady state: 0 = (f*dt/2)*V_geo + dt*(-C1*sum)
    # => V_geo = 2*C1*sum / f = 2*(g/rho0)*sum / f
    # Compare with continuous: v_geo = (1/(rho0*f)) * dp/dx = (1/(rho0*f)) * g * sum / c8
    # = (g/(rho0*f)) * sum / c8

    # The model has an extra factor of 2 and a factor of 1/c8 = 4*dx

    # Actually, the model's sum is: sum = c8 * integral d(ro)/dx dz
    # So sum/c8 = integral d(ro)/dx dz
    # And dp/dx = g * integral d(ro)/dx dz = g * sum / c8

    # Model geostrophic: V_geo = 2*C1*sum/f = 2*(g/rho0)*sum/f
    # Continuous geostrophic: v_geo = dp/dx/(rho0*f) = g*sum/(c8*rho0*f)

    # Ratio: Model/Continuous = 2*c8 = 2*0.25/dx = 0.5/dx

    # This is a HUGE factor! The model's discrete formulation produces velocities
    # that are 0.5/dx = 0.5/1389000 = 3.6e-7 times the continuous geostrophic?
    # No, that's the wrong way. Let me redo.

    # Model: V_geo = 2*(g/rho0)*sum/f where sum = c8*integral = 0.25/dx * integral
    # = 2*(g/rho0)*(0.25/dx)*integral / f
    # = (g/rho0) * integral / (2*dx*f)
    # = 0.5 * (g/rho0) * integral / (dx*f)

    # Continuous: v_geo = g*integral/(rho0*f) (no dx factor!)
    # Wait, continuous doesn't have dx. The gradient is d/dx, not Delta/dx.

    # Let me be more careful.
    # The discrete gradient: d(ro)/dx ≈ Delta(ro)/dx where Delta(ro) is the difference
    # The 4-point stencil gives: Delta(ro) = ro(i,j) + ro(i-1,j) - ro(i-1,j-1) - ro(i,j-1)
    # This is approximately: 2 * dx * d(ro)/dx + higher order
    # So: c8 * Delta(ro) * dz = (0.25/dx) * 2*dx * d(ro)/dx * dz = 0.5 * d(ro)/dx * dz
    # This is 0.5 * integral d(ro)/dx dz

    # So sum ≈ 0.5 * integral d(ro)/dx dz
    # And V_geo = 2*(g/rho0)*sum/f ≈ 2*(g/rho0)*0.5*integral/(rho0*f) = (g/rho0)*integral/f

    # Compare with continuous: v_geo = g*integral/(rho0*f)

    # They match! The factor of 2 from semi-implicit cancels the factor of 0.5
    # from the 4-point stencil.

    # OK so the model formulation IS correct for the surface-referenced
    # cumulative integral. But this is the surface-referenced geostrophic,
    # which assumes the velocity at the surface is zero (no reference level correction).

    # For a proper geostrophic, we need a reference level assumption.
    # The standard approach: v_geo(z) = v_geo(z_ref) + integral from z_ref to z of thermal wind

    # The model's formulation assumes v_geo(surface) = 0, which gives
    # the surface-referenced geostrophic shear.

    # This is ONLY the relative geostrophic shear, not the absolute geostrophic velocity.
    # To get absolute velocity, we need a reference level assumption.

    # Let me compute both the surface-referenced and 600m-referenced geostrophic.

    # For the surface-referenced (what the model does):
    # v_geo(k) = (g/rho0) * integral_0^k d(ro)/dx dz / f
    # This is what the model computes (with the factor of 2 canceling the stencil factor)

    # For the 600m-referenced:
    # v_geo(k) = v_geo(600m) + integral_600m^k thermal_wind
    # If we assume v_geo(600m) = 0 (deep reference):
    # v_geo(k) = integral_600m^k thermal_wind dz

    # Thermal wind: f * dv/dz = -(g/rho0) * d(rho)/dx
    # => dv/dz = -(g/(rho0*f)) * d(rho)/dx
    # => v(k) = v(600m) - integral_600m^k (g/(rho0*f)) * d(rho)/dx dz
    # If v(600m) = 0:
    # v(k) = -(g/(rho0*f)) * integral_600m^k d(rho)/dx dz
    # = (g/(rho0*f)) * integral_k^600m d(rho)/dx dz

    # Let me compute this properly.
    pass


def method_thermal_wind_si(ro, kt1, fku, reference_level_k=0):
    """
    Thermal wind geostrophic with specified reference level.
    v_geo(k) = v_geo(k_ref) - integral from k_ref to k of (g/(rho0*f)) * d(rho)/dx dz
    """
    g_si = 9.81
    rho0_si = 1025.0
    f_safe = np.where(np.abs(fku) > 1e-12, fku, np.nan)
    f_safe_3d = f_safe[:, :, np.newaxis]

    # 4-point stencil for gradient (same as model)
    grad_x_3d = np.zeros((IS1, JS1, KS))
    grad_y_3d = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        ro_si = ro[:, :, k] * 1000.0  # kg/m^3
        delta_ro_x = np.zeros((IS1, JS1))
        delta_ro_x[1:IS1, 1:JS1] = (
            ro_si[0:IS, 1:JS1]
            + ro_si[1:IS1, 1:JS1]
            - ro_si[0:IS, 0:JS]
            - ro_si[1:IS1, 0:JS]
        )
        delta_ro_y = np.zeros((IS1, JS1))
        delta_ro_y[1:IS1, 1:JS1] = (
            ro_si[0:IS, 0:JS]
            + ro_si[0:IS, 1:JS1]
            - ro_si[1:IS1, 0:JS]
            - ro_si[1:IS1, 1:JS1]
        )
        # The 4-point stencil gives approximately 2*dx * gradient
        # So the actual gradient is delta_ro / (2*dx)
        grad_x_3d[:, :, k] = delta_ro_x / (2.0 * DX_M)
        grad_y_3d[:, :, k] = delta_ro_y / (2.0 * DX_M)

    # Thermal wind: f * dv/dz = -(g/rho0) * d(rho)/dx
    # dv/dz = -(g/(rho0*f)) * grad_x
    # v(k) = v(k_ref) + integral from k_ref to k of dv/dz dz
    # = v(k_ref) - integral from k_ref to k of (g/(rho0*f)) * grad_x dz

    # For reference at surface (k_ref=0):
    # v(k) = 0 - integral_0^k (g/(rho0*f)) * grad_x dz
    # = -(g/(rho0*f)) * integral_0^k grad_x dz

    U_geo = np.zeros((IS1, JS1, KS))
    V_geo = np.zeros((IS1, JS1, KS))

    for k in range(KS):
        if k == reference_level_k:
            V_geo[:, :, k] = 0.0
            U_geo[:, :, k] = 0.0
        elif k < reference_level_k:
            # Integrate from k to reference_level_k (going down)
            nlev = reference_level_k - k
            dzs = np.array([DZ_CM[m] / 100.0 for m in range(k, reference_level_k)])
            integral_x = np.sum(
                grad_x_3d[:, :, k:reference_level_k] * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            integral_y = np.sum(
                grad_y_3d[:, :, k:reference_level_k] * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            V_geo[:, :, k] = (g_si / (rho0_si * f_safe)) * integral_x
            U_geo[:, :, k] = -(g_si / (rho0_si * f_safe)) * integral_y
        else:
            # k > reference_level_k: integrate from reference_level_k to k (going up)
            nlev = k - reference_level_k
            dzs = np.array(
                [DZ_CM[m] / 100.0 for m in range(reference_level_k + 1, k + 1)]
            )
            integral_x = np.sum(
                grad_x_3d[:, :, reference_level_k + 1 : k + 1]
                * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            integral_y = np.sum(
                grad_y_3d[:, :, reference_level_k + 1 : k + 1]
                * dzs[np.newaxis, np.newaxis, :],
                axis=2,
            )
            V_geo[:, :, k] = -(g_si / (rho0_si * f_safe)) * integral_x
            U_geo[:, :, k] = (g_si / (rho0_si * f_safe)) * integral_y

    return U_geo, V_geo


def percentile_stats(arr, mask=None):
    if mask is not None:
        arr = arr[mask]
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return {"max": 0.0, "p99": 0.0, "p90": 0.0, "p50": 0.0, "mean": 0.0}
    return {
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
    }


def main():
    print("=" * 70)
    print("STAGE 7.8 — GEOSTROPHIC DIAGNOSTIC REVALIDATION")
    print("=" * 70)

    T, S, kt1, wet, lat, lon, ds = load_en4_product()
    ro = compute_density(T, S)
    fku = compute_fku(lat, wet)

    interior_mask = np.zeros((IS1, JS1), dtype=bool)
    interior_mask[2 : IS + 1, 2 : JS + 1] = True

    print(f"\nEN4 T range: {np.nanmin(T[wet]):.4f} .. {np.nanmax(T[wet]):.4f} °C")
    print(f"EN4 S range: {np.nanmin(S[wet]):.6f} .. {np.nanmax(S[wet]):.6f}")
    print(f"ro range: {np.nanmin(ro[wet]):.6f} .. {np.nanmax(ro[wet]):.6f} g/cm^3")
    print(
        f"f range: {np.nanmin(fku[interior_mask & wet]):.2e} .. {np.nanmax(fku[interior_mask & wet]):.2e} 1/s"
    )

    results = {}

    # Method 1: Stage 7.7C (with factor of 2)
    print("\n--- Method 1: Stage 7.7C (with factor 2) ---")
    U1, V1 = method_stage77c(ro, kt1, fku)
    speed1 = np.sqrt(U1**2 + V1**2) / 100.0  # m/s
    mask = wet & interior_mask & (kt1 > 0)
    stats1 = percentile_stats(speed1[:, :, -1], mask)  # Full depth
    print(
        f"  Full depth: max={stats1['max']:.2f} P99={stats1['p99']:.2f} P90={stats1['p90']:.2f} m/s"
    )
    results["stage77c"] = {"full_depth": stats1}

    # Method 2: Model without factor of 2
    print("\n--- Method 2: Model formulation WITHOUT factor 2 ---")
    U2, V2 = method_model_no_factor2(ro, kt1, fku)
    speed2 = np.sqrt(U2**2 + V2**2) / 100.0
    stats2 = percentile_stats(speed2[:, :, -1], mask)
    print(
        f"  Full depth: max={stats2['max']:.2f} P99={stats2['p99']:.2f} P90={stats2['p90']:.2f} m/s"
    )
    results["model_no_factor2"] = {"full_depth": stats2}

    # Method 3: Thermal wind, surface reference
    print("\n--- Method 3: Thermal wind, surface reference (k_ref=0) ---")
    U3, V3 = method_thermal_wind_si(ro, kt1, fku, reference_level_k=0)
    speed3 = np.sqrt(U3**2 + V3**2)
    stats3 = percentile_stats(speed3[:, :, -1], mask)
    print(
        f"  Full depth: max={stats3['max']:.2f} P99={stats3['p99']:.2f} P90={stats3['p90']:.2f} m/s"
    )
    results["thermal_wind_surface"] = {"full_depth": stats3}

    # Method 4: Thermal wind, 600m reference (deep)
    print("\n--- Method 4: Thermal wind, 600m reference (k_ref=17, deep) ---")
    U4, V4 = method_thermal_wind_si(ro, kt1, fku, reference_level_k=17)
    speed4 = np.sqrt(U4**2 + V4**2)
    stats4 = percentile_stats(speed4[:, :, -1], mask)
    print(
        f"  Full depth: max={stats4['max']:.2f} P99={stats4['p99']:.2f} P90={stats4['p90']:.2f} m/s"
    )
    results["thermal_wind_600m"] = {"full_depth": stats4}

    # Method 5: Thermal wind, mid-depth reference
    print("\n--- Method 5: Thermal wind, mid-depth reference (k_ref=10, 100m) ---")
    U5, V5 = method_thermal_wind_si(ro, kt1, fku, reference_level_k=10)
    speed5 = np.sqrt(U5**2 + V5**2)
    stats5 = percentile_stats(speed5[:, :, -1], mask)
    print(
        f"  Full depth: max={stats5['max']:.2f} P99={stats5['p99']:.2f} P90={stats5['p90']:.2f} m/s"
    )
    results["thermal_wind_100m"] = {"full_depth": stats5}

    # Physical current scale estimate
    print("\n--- Physical Scale Estimate ---")
    # Compute max gradient properly
    dro_dx = np.zeros((IS1, JS1, KS))
    for k in range(KS):
        delta_ro = np.zeros((IS1, JS1))
        delta_ro[1:IS1, 1:JS1] = (
            ro[0:IS, 1:JS1, k]
            + ro[1:IS1, 1:JS1, k]
            - ro[0:IS, 0:JS, k]
            - ro[1:IS1, 0:JS, k]
        )
        dro_dx[:, :, k] = delta_ro / (2.0 * DX_CM)  # g/cm^3 per cm
    dro_dx_m = dro_dx * 100.0  # g/cm^3 per m
    max_grad = np.nanmax(np.abs(dro_dx_m[mask]))
    print(f"  Max |d(ro)/dx|: {max_grad:.2e} g/cm^3/m")
    print(f"  Max |d(ro)/dx|: {max_grad*1000:.2e} kg/m^4")

    # Physical estimate with H=100m
    f_avg = np.nanmean(np.abs(fku[mask]))
    H_est = 100.0  # m
    U_est = G_M / f_avg * max_grad * 1000.0 * H_est
    print(f"  Physical estimate U ~ g/f * grad(rho) * H = {U_est:.2f} m/s (H=100m)")

    H_est = 500.0  # m
    U_est = G_M / f_avg * max_grad * 1000.0 * H_est
    print(f"  Physical estimate U ~ g/f * grad(rho) * H = {U_est:.2f} m/s (H=500m)")

    # Save results
    out_dir = Path("data/output/diagnostics/stage7.8")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "geostrophic_revalidation.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== Summary Table ===")
    print(f"{'Method':<40} {'max (m/s)':<12} {'P99 (m/s)':<12} {'P90 (m/s)':<12}")
    print("-" * 76)
    for name, stats_dict in results.items():
        s = stats_dict["full_depth"]
        print(f"{name:<40} {s['max']:<12.2f} {s['p99']:<12.2f} {s['p90']:<12.2f}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
