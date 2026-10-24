#!/usr/bin/env python3
"""
Stage 11.8.0 T3-CORRECTIVE-2 — T-03 root-cause diagnosis.

Diagnostic only: reads the 30-day T3 rest run (t3c_legacy_canonical) and
characterises where/when the spurious current grows, checks whether the
initial T/S state is geostrophically balanced with u=v=0, documents the
Block-200 pressure-gradient discretisation, computes a KE/APE budget, and
checks boundary/topography localisation.

Outputs:
  data/validation/t3c2_spatial_diagnosis.json
  data/validation/figures/t3c2/*.png

Usage:
  python python/analysis/stage11.8.0_T3_CORRECTIVE2_diagnosis.py \
      --run t3c_legacy_canonical
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT = Path(__file__).resolve().parents[2]
RHO0 = 1027.0
G = 9.81
OMEGA = 7.2921e-5
DX = 13890.0  # m
DXC = 1389000.0  # cm
AREA = DX * DX


def load_day(nc_dir, day):
    path = nc_dir / f"results_day_{day:02d}.nc"
    with Dataset(path) as d:
        out = {
            "u": np.array(d["u_velocity"][:], dtype=np.float64),
            "v": np.array(d["v_velocity"][:], dtype=np.float64),
            "w": np.array(d["w_velocity"][:], dtype=np.float64),
            "T": np.array(d["temperature"][:], dtype=np.float64) - 273.15,
            "S": np.array(d["salinity_mass_fraction"][:], dtype=np.float64),
            "ro": np.array(d["density_anomaly"][:], dtype=np.float64),
            "lev": np.array(d["water_column_levels"][:], dtype=np.int32),
            "z": np.array(d["depth"][:], dtype=np.float64),
            "zw": np.array(d["depth_w"][:], dtype=np.float64),
            "lat": np.array(d["latitude"][:], dtype=np.float64),
            "lon": np.array(d["longitude"][:], dtype=np.float64),
        }
    kk = np.arange(out["T"].shape[0])[:, None, None]
    out["mask"] = (out["lev"][None, :, :] > 0) & (kk < out["lev"][None, :, :])
    out["dz"] = np.diff(out["zw"])
    out["vol"] = out["dz"][:, None, None] * AREA
    out["f"] = 2.0 * OMEGA * np.sin(np.deg2rad(out["lat"]))
    return out


def bathy(day0):
    """Approximate water depth at T points (last wet level + half layer)."""
    lev = day0["lev"]
    z = day0["z"]
    b = np.zeros(lev.shape, dtype=np.float64)
    wet = lev > 0
    idx = np.clip(lev - 1, 0, len(z) - 1)
    b[wet] = z[idx[wet]]
    return b


def max_loc(field, mask, day0, prefix=""):
    sm = np.where(mask, field, np.nan)
    if not np.isfinite(sm).any():
        return None
    k, y, x = map(int, np.unravel_index(np.nanargmax(sm), sm.shape))
    return {
        prefix + "value": float(sm[k, y, x]),
        "k": k + 1, "y": y + 1, "x": x + 1,
        "lat": float(day0["lat"][y, x]),
        "lon": float(day0["lon"][y, x]),
        "lev": int(day0["lev"][y, x]),
    }


def thermal_wind(day0, ref_k=18, double_count=False):
    """Reproduce the model thermal-wind stencil in CGS.

    Array layout from NetCDF is (k, y, x) = (k, j, i) in the model's
    Fortran indexing: the first horizontal index i is the model Y axis
    (length 133) and the second j is the model X axis (length 105), per the
    model convention X<->j<->u and Y<->i<->v.  Block 200 loops
    i=2..is (0-based 1..131) and j=2..js (0-based 1..103).
    Returns U,V [m/s] on the full grid.
    """
    ro = day0["ro"] / 1000.0  # kg/m3 -> g/cm3
    lev = day0["lev"]
    f = day0["f"]
    K, J, I = ro.shape
    u = np.zeros_like(ro)
    v = np.zeros_like(ro)
    c8 = 0.25 / DXC
    dzc = day0["dz"] * 100.0  # m -> cm
    for j in range(1, J - 1):
        for i in range(1, I - 1):
            ki = int(min(lev[j, i], lev[j, i - 1], lev[j - 1, i], lev[j - 1, i - 1]))
            if ki <= 0:
                continue
            # Output masks land density to 0; skip coastal stencils whose
            # neighbours are dry so the diagnostic does not create a fake
            # coastal gradient (the model's internal land RO is filled).
            if ref_k > ki:
                continue  # model sets u=v=0 for columns shallower than k_ref
            if min(lev[j, i - 1], lev[j - 1, i], lev[j - 1, i - 1]) <= 0:
                continue
            fv = f[j, i]
            if abs(fv) < 1e-12:
                continue
            c1f = 981.0 / fv
            sx = np.zeros(K)
            sy = np.zeros(K)
            a = (ro[0, j, i - 1] + ro[0, j, i]
                 - ro[0, j - 1, i - 1] - ro[0, j - 1, i])
            b = (ro[0, j - 1, i - 1] + ro[0, j, i - 1]
                 - ro[0, j - 1, i] - ro[0, j, i])
            if ki >= 2:
                a1 = (ro[1, j, i - 1] + ro[1, j, i]
                      - ro[1, j - 1, i - 1] - ro[1, j - 1, i])
                b1 = (ro[1, j - 1, i - 1] + ro[1, j, i - 1]
                      - ro[1, j - 1, i] - ro[1, j, i])
            else:
                a1, b1 = a, b
            if double_count:
                a1, b1 = a, b
            sx[0] = (a + a1) * c8 * dzc[0]
            sy[0] = (b + b1) * c8 * dzc[0]
            for k in range(1, min(ki, K)):
                a = (ro[k, j, i - 1] + ro[k, j, i]
                     - ro[k, j - 1, i - 1] - ro[k, j - 1, i])
                b = (ro[k, j - 1, i - 1] + ro[k, j, i - 1]
                     - ro[k, j - 1, i] - ro[k, j, i])
                if k + 1 < ki:
                    a1 = (ro[k + 1, j, i - 1] + ro[k + 1, j, i]
                          - ro[k + 1, j - 1, i - 1] - ro[k + 1, j - 1, i])
                    b1 = (ro[k + 1, j - 1, i - 1] + ro[k + 1, j, i - 1]
                          - ro[k + 1, j - 1, i] - ro[k + 1, j, i])
                else:
                    a1, b1 = a, b
                sx[k] = sx[k - 1] + (a + a1) * c8 * dzc[k]
                sy[k] = sy[k - 1] + (b + b1) * c8 * dzc[k]
            rk = ref_k - 1
            for k in range(min(ki, K)):
                vv = c1f * sx[k]
                uu = -c1f * sy[k]
                if 0 <= rk < ki:
                    vv -= c1f * sx[rk]
                    uu -= -c1f * sy[rk]
                u[k, j, i] = uu / 100.0
                v[k, j, i] = vv / 100.0
    return u, v


def pgf_block200(day, c1=981.0, double_count=True, fill_dry=False):
    """Block-200 baroclinic acceleration [m/s2] from RO.

    Same array convention as thermal_wind: (k, j=model X, i=model Y).
    fill_dry=False reproduces the model exactly: RO below a neighbour's
    bottom is zero (eos_diag skips k>kt1 and initial_conditions sets ro=0).
    fill_dry=True replaces those dry-level values by the bottom value of the
    same column, isolating the topographic pressure-gradient error.
    """
    ro = day["ro"] / 1000.0
    lev = day["lev"]
    K, J, I = ro.shape
    c8 = 0.25 / DXC
    dzc = day["dz"] * 100.0
    au = np.zeros_like(ro)
    av = np.zeros_like(ro)

    def rho(k, jj, ii):
        if lev[jj, ii] <= 0:
            return 0.0
        if fill_dry and k >= lev[jj, ii]:
            return ro[lev[jj, ii] - 1, jj, ii]
        return ro[k, jj, ii] if k < K else 0.0

    for j in range(1, J - 1):
        for i in range(1, I - 1):
            ki = int(min(lev[j, i], lev[j, i - 1], lev[j - 1, i], lev[j - 1, i - 1]))
            if ki <= 0:
                continue
            sx = 0.0
            sy = 0.0
            a = (rho(0, j, i - 1) + rho(0, j, i)
                 - rho(0, j - 1, i - 1) - rho(0, j - 1, i))
            b = (rho(0, j - 1, i - 1) + rho(0, j, i - 1)
                 - rho(0, j - 1, i) - rho(0, j, i))
            for k in range(min(ki, K)):
                if not double_count and k == 0 and ki >= 2:
                    a1 = (rho(1, j, i - 1) + rho(1, j, i)
                          - rho(1, j - 1, i - 1) - rho(1, j - 1, i))
                    b1 = (rho(1, j - 1, i - 1) + rho(1, j, i - 1)
                          - rho(1, j - 1, i) - rho(1, j, i))
                elif double_count and k == 0:
                    a1, b1 = a, b
                else:
                    a1 = (rho(k, j, i - 1) + rho(k, j, i)
                          - rho(k, j - 1, i - 1) - rho(k, j - 1, i))
                    b1 = (rho(k, j - 1, i - 1) + rho(k, j, i - 1)
                          - rho(k, j - 1, i) - rho(k, j, i))
                sx += (a + a1) * c8 * dzc[k]
                sy += (b + b1) * c8 * dzc[k]
                au[k, j, i] = -c1 * sx  # cm/s2
                av[k, j, i] = -c1 * sy
                a, b = a1, b1
    return au / 100.0, av / 100.0


def rms(a, mask):
    if not np.isfinite(a[mask]).any():
        return float("nan")
    return float(np.sqrt(np.nanmean(a[mask] ** 2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="t3c_legacy_canonical")
    ap.add_argument("--out", type=Path,
                    default=PROJECT / "data/validation/t3c2_spatial_diagnosis.json")
    ap.add_argument("--figdir", type=Path,
                    default=PROJECT / "data/validation/figures/t3c2")
    args = ap.parse_args()

    nc_dir = PROJECT / "data/runs" / args.run / "output/nc"
    if not (nc_dir / "results_day_00.nc").exists():
        raise SystemExit(f"no outputs in {nc_dir}")
    n_days = 0
    while (nc_dir / f"results_day_{n_days + 1:02d}.nc").exists():
        n_days += 1
    d0 = load_day(nc_dir, 0)
    bth = bathy(d0)
    wet = d0["mask"]
    hot = (18, 4)  # y,x (0-based) from day-30 max; updated below

    # ---- geostrophic balance from initial T/S --------------------------------
    u_geo, v_geo = thermal_wind(d0, ref_k=18, double_count=False)
    u_geo_b200, v_geo_b200 = thermal_wind(d0, ref_k=18, double_count=True)
    speed_geo = np.sqrt(u_geo ** 2 + v_geo ** 2)
    speed_geo_b200 = np.sqrt(u_geo_b200 ** 2 + v_geo_b200 ** 2)
    au_raw, av_raw = pgf_block200(d0, fill_dry=False)
    au_fill, av_fill = pgf_block200(d0, fill_dry=True)
    geo_stats = {
        "max_u_geo_m_s": float(np.nanmax(np.where(wet, np.abs(u_geo), np.nan))),
        "max_v_geo_m_s": float(np.nanmax(np.where(wet, np.abs(v_geo), np.nan))),
        "max_speed_geo_m_s": float(np.nanmax(np.where(wet, speed_geo, np.nan))),
        "max_speed_geo_block200_stencil_m_s": float(
            np.nanmax(np.where(wet, speed_geo_b200, np.nan))),
        "max_speed_geo_block200_ratio": float(
            np.nanmax(np.where(wet, speed_geo_b200, np.nan))
            / np.nanmax(np.where(wet, speed_geo, np.nan))),
        "max_pgf_raw_m_s2": float(np.nanmax(np.where(wet, np.hypot(au_raw, av_raw), np.nan))),
        "max_pgf_filled_m_s2": float(np.nanmax(np.where(wet, np.hypot(au_fill, av_fill), np.nan))),
        "initial_velocity_m_s": 0.0,
        "unbalanced": bool(np.nanmax(np.where(wet, speed_geo, np.nan)) > 0.01),
    }
    # depth-integrated transport of the balanced state (cm2/s -> m2/s)
    dzc = d0["dz"] * 100.0
    tr_u = np.nansum(np.where(wet, u_geo * 100.0 * dzc[:, None, None], 0.0), axis=0) / 1e4
    tr_v = np.nansum(np.where(wet, v_geo * 100.0 * dzc[:, None, None], 0.0), axis=0) / 1e4
    h = np.where(bth > 0, bth, np.nan)
    geo_stats.update({
        "max_depth_integrated_transport_u_m2_s": float(np.nanmax(np.abs(np.where(wet[0], tr_u, np.nan)))),
        "max_depth_integrated_transport_v_m2_s": float(np.nanmax(np.abs(np.where(wet[0], tr_v, np.nan)))),
        "max_barotropic_equivalent_u_m_s": float(np.nanmax(np.abs(np.where(wet[0], tr_u / h, np.nan)))),
        "max_barotropic_equivalent_v_m_s": float(np.nanmax(np.abs(np.where(wet[0], tr_v / h, np.nan)))),
        "transport_divergence_max_s-1": float(np.nanmax(np.abs(
            np.gradient(np.where(wet[0], tr_u, 0.0), DX, axis=1)
            + np.gradient(np.where(wet[0], tr_v, 0.0), DX, axis=0)))),
    })
    # initial Block-200 acceleration (baroclinic PGF) [m/s2]
    au0, av0 = pgf_block200(d0)
    geo_stats.update({
        "max_initial_pgf_accel_m_s2": float(np.nanmax(np.where(wet, np.hypot(au0, av0), np.nan))),
        "max_initial_pgf_accel_cm_s2": float(np.nanmax(np.where(wet, np.hypot(au0, av0), np.nan)) * 100.0),
        "max_1step_velocity_change_m_s": float(
            np.nanmax(np.where(wet, np.hypot(au0, av0), np.nan)) * 3600.0),
        "max_1day_velocity_change_m_s": float(
            np.nanmax(np.where(wet, np.hypot(au0, av0), np.nan)) * 86400.0),
    })
    # Rossby radius / Eady growth from the initial mean stratification
    rho_mean = np.nanmean(np.where(wet, d0["ro"], np.nan), axis=(1, 2))
    z = d0["z"]
    N2 = G / 1000.0 * np.gradient(rho_mean, z)
    N2 = np.where(np.isfinite(N2) & (N2 > 1e-8), N2, 1e-8)
    N = np.sqrt(N2)
    fmean = float(np.nanmean(np.abs(d0["f"][wet[0]])))
    H = float(np.nanmax(bth))
    Rd = float(np.sum(N * d0["dz"]) / (np.pi * fmean))
    eady = float(0.31 * fmean / np.sqrt(np.nanmean(N2)))
    geo_stats.update({
        "N2_mean_s-2": float(np.nanmean(N2)),
        "N_mean_s-1": float(np.nanmean(N)),
        "f_mean_s-1": fmean,
        "first_baroclinic_rossby_radius_km": Rd / 1000.0,
        "grid_spacing_km": DX / 1000.0,
        "rossby_radius_over_grid": Rd / DX,
        "eady_growth_rate_1_s": eady,
        "eady_growth_rate_1_day": eady * 86400.0,
    })

    # ---- daily spatial metrics ----------------------------------------------
    daily = []
    hot = (18, 4)
    for day in range(0, n_days + 1):
        d = d0 if day == 0 else load_day(nc_dir, day)
        m = d["mask"]
        u, v, w = d["u"], d["v"], d["w"]
        spd = np.hypot(u, v)
        ke_cell = 0.5 * RHO0 * (u * u + v * v) * d["vol"]
        ke = float(np.nansum(np.where(m, ke_cell, 0.0)))
        kez = np.nansum(np.where(m, ke_cell, 0.0), axis=(1, 2))
        # boundary band 5 cells
        bmask = np.zeros(m.shape[1:], dtype=bool)
        bmask[:5, :] = bmask[-5:, :] = bmask[:, :5] = bmask[:, -5:] = True
        ke_b = float(np.nansum(np.where(m & bmask[None], ke_cell, 0.0)))
        # quadrants (x = j, y = i)
        I, J = bmask.shape
        quads = {}
        for name, ys, xs in [
            ("SW", slice(0, I // 2), slice(0, J // 2)),
            ("SE", slice(0, I // 2), slice(J // 2, J)),
            ("NW", slice(I // 2, I), slice(0, J // 2)),
            ("NE", slice(I // 2, I), slice(J // 2, J)),
        ]:
            quads[name] = float(np.nansum(np.where(m[:, ys, xs], ke_cell[:, ys, xs], 0.0)))
        # APE proxy: perturbation density about the level horizontal mean
        rho = d["ro"]
        rho_mean_d = np.nanmean(np.where(m, rho, np.nan), axis=(1, 2))
        rho_p = rho - rho_mean_d[:, None, None]
        ape_cell = (G ** 2 * rho_p ** 2) / (2.0 * RHO0 * N2[:, None, None]) * d["vol"]
        ape = float(np.nansum(np.where(m, ape_cell, 0.0)))
        # PE anomaly
        pe = float(np.nansum(np.where(m, RHO0 * 9.81 * d["ro"] * d["z"][:, None, None]
                                      * d["vol"], 0.0)))
        # drift
        dT = np.sqrt(np.nanmean(np.where(m, (d["T"] - d0["T"]) ** 2, np.nan)))
        dS = np.sqrt(np.nanmean(np.where(m, (d["S"] - d0["S"]) ** 2, np.nan))) * 1000.0
        dTz = np.sqrt(np.nanmean(np.where(m, (d["T"] - d0["T"]) ** 2, np.nan), axis=(1, 2)))
        dSz = np.sqrt(np.nanmean(np.where(m, (d["S"] - d0["S"]) ** 2, np.nan), axis=(1, 2))) * 1000.0
        # grid-scale roughness of U (neighbour difference / rms)
        du = np.where(m[:, :, 1:] & m[:, :, :-1], (u[:, :, 1:] - u[:, :, :-1]) ** 2, np.nan)
        noise = float(np.sqrt(np.nanmean(du)) / (np.sqrt(np.nanmean(np.where(m, u * u, np.nan))) + 1e-12))
        # max speed location
        loc = max_loc(spd, m, d, "speed_")
        # shear and Ri
        duz = np.gradient(u, z, axis=0)
        dvz = np.gradient(v, z, axis=0)
        shear2 = duz ** 2 + dvz ** 2
        with np.errstate(divide="ignore", invalid="ignore"):
            ri = np.where(m & (shear2 > 1e-12), N2[:, None, None] / shear2, np.nan)
        daily.append({
            "day": day, "ke_j": ke, "ape_j": ape, "pe_j": pe,
            "ke_by_depth_j": kez.tolist(),
            "ke_boundary_fraction": ke_b / ke if ke > 0 else 0.0,
            "ke_quadrants": quads,
            "drift_T_rms": float(dT), "drift_S_rms_psu": float(dS),
            "drift_T_by_depth": dTz.tolist(), "drift_S_by_depth": dSz.tolist(),
            "grid_scale_noise": noise,
            "max_speed": loc,
            "ri_min": float(np.nanmin(ri)) if np.isfinite(ri).any() else None,
            "max_shear2": float(np.nanmax(shear2[m])) if m.any() else 0.0,
            "pe_total_j": float(np.nansum(np.where(m, -RHO0 * 9.81 * d["ro"] * d["z"][:, None, None]
                                                   * d["vol"], 0.0))),
            "te_total_j": float(np.nansum(np.where(m, -RHO0 * 9.81 * d["ro"] * d["z"][:, None, None]
                                                     * d["vol"], 0.0)) + ke),
            "max_density_gradient_kg_m4": float(np.nanmax(
                np.hypot(np.gradient(d["ro"], DX, axis=2), np.gradient(d["ro"], DX, axis=1))[m])) if m.any() else 0.0,
            "nan": int(np.isnan(u).sum() + np.isnan(v).sum()
                       + np.isnan(d["T"]).sum() + np.isnan(d["S"]).sum()),
        })
        if day > 0 and loc:
            hot = (loc["y"] - 1, loc["x"] - 1)
        if day == 0:
            ke0 = ke

    def pattern_corr(field_a, field_b, mask):
        a = np.where(mask, field_a, np.nan).ravel()
        b = np.where(mask, field_b, np.nan).ravel()
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < 10:
            return None
        return float(np.corrcoef(a[ok], b[ok])[0, 1])

    d1 = load_day(nc_dir, 1)
    d30 = load_day(nc_dir, n_days)
    geo_stats["pattern_corr_geo_day1"] = pattern_corr(
        speed_geo, np.hypot(d1["u"], d1["v"]), d1["mask"])
    geo_stats["pattern_corr_geo_day30"] = pattern_corr(
        speed_geo, np.hypot(d30["u"], d30["v"]), d30["mask"])
    geo_stats["pattern_corr_geo_day1_component"] = pattern_corr(
        u_geo, d1["u"], d1["mask"])
    # spectral high-wavenumber fraction (grid-scale noise)
    def high_waveno_fraction(u, k):
        arr = np.where(np.isfinite(u[k]), u[k], 0.0)
        f = np.fft.fftshift(np.abs(np.fft.fft2(arr)) ** 2)
        ny, nx = f.shape
        ky = np.abs(np.fft.fftshift(np.fft.fftfreq(ny)))[:, None]
        kx = np.abs(np.fft.fftshift(np.fft.fftfreq(nx)))[None, :]
        high = f[(np.maximum(ky, kx) > 0.25)].sum()
        return float(high / f.sum()) if f.sum() > 0 else None
    geo_stats["high_wavenumber_fraction_day30_k1"] = high_waveno_fraction(d30["u"], 0)
    geo_stats["high_wavenumber_fraction_day30_k17"] = high_waveno_fraction(d30["u"], 16)

    # ---- KE budget at selected days ----------------------------------------
    budget = []
    for day in (1, 2, 5, 10, 15, 20, 25, 30):
        if day > n_days:
            continue
        prev = load_day(nc_dir, max(0, day - 1))
        d = load_day(nc_dir, day)
        m = d["mask"]
        dke = (daily[day]["ke_j"] - daily[max(0, day - 1)]["ke_j"]) / 86400.0
        # baroclinic PGF work using the Block-200 stencil
        au, av = pgf_block200(d)
        w_pgf = float(np.nansum(np.where(m, RHO0 * (d["u"] * au + d["v"] * av) * d["vol"], 0.0)))
        # Coriolis work (should be zero; discrete residual)
        f = d["f"]
        w_cor = float(np.nansum(np.where(m, RHO0 * (d["u"] * f[None] * d["v"]
                                                    - d["v"] * f[None] * d["u"]) * d["vol"], 0.0)))
        # horizontal Laplacian work
        lapu = np.zeros_like(d["u"])
        lapv = np.zeros_like(d["v"])
        for k in range(d["u"].shape[0]):
            lapu[k] = (np.roll(d["u"][k], 1, 1) + np.roll(d["u"][k], -1, 1)
                       + np.roll(d["u"][k], 1, 0) + np.roll(d["u"][k], -1, 0)
                       - 4.0 * d["u"][k]) / DX ** 2
            lapv[k] = (np.roll(d["v"][k], 1, 1) + np.roll(d["v"][k], -1, 1)
                       + np.roll(d["v"][k], 1, 0) + np.roll(d["v"][k], -1, 0)
                       - 4.0 * d["v"][k]) / DX ** 2
        ah = 750.0  # m2/s (7.5e6 cm2/s)
        w_lap = float(np.nansum(np.where(m, RHO0 * ah * (d["u"] * lapu + d["v"] * lapv)
                                        * d["vol"], 0.0)))
        d_ape = (daily[day]["ape_j"] - daily[max(0, day - 1)]["ape_j"]) / 86400.0
        budget.append({
            "day": day, "dKE_dt_w": dke, "pgf_work_w": w_pgf,
            "coriolis_work_w": w_cor, "laplacian_work_w": w_lap,
            "dAPE_dt_w": d_ape, "conversion_minus_dAPE_w": -d_ape,
            "residual_w": dke - w_pgf - w_cor - w_lap,
            "ke_growth_rate_1_day": float(np.log(daily[day]["ke_j"] / daily[max(0, day - 1)]["ke_j"]))
            if daily[max(0, day - 1)]["ke_j"] > 0 else None,
        })

    # ---- boundary/topography localisation ----------------------------------
    dlast = load_day(nc_dir, n_days)
    m = dlast["mask"]
    spd = np.hypot(dlast["u"], dlast["v"])
    ke_cell = 0.5 * RHO0 * spd ** 2 * dlast["vol"]
    ke = float(np.nansum(np.where(m, ke_cell, 0.0)))
    I, J = m.shape[1:]
    dist = np.minimum.reduce([np.arange(I)[:, None] * np.ones((1, J)),
                              (I - 1 - np.arange(I))[:, None] * np.ones((1, J)),
                              np.ones((I, 1)) * np.arange(J)[None, :],
                              np.ones((I, 1)) * (J - 1 - np.arange(J))[None, :]])
    loc = max_loc(spd, m, dlast, "speed_")
    # bathy/slope
    slope = np.hypot(np.gradient(bth, DX, axis=0), np.gradient(bth, DX, axis=1))
    high = m & (spd > np.nanpercentile(np.where(m, spd, np.nan), 99))
    high2 = high.any(axis=0)
    boundary_stats = {
        "max_speed": loc,
        "distance_to_boundary_cells": int(dist[loc["y"] - 1, loc["x"] - 1]) if loc else None,
        "ke_fraction_within_5_cells": daily[n_days]["ke_boundary_fraction"],
        "ke_fraction_within_10_cells": float(np.nansum(
            np.where(m & (dist[None] <= 10), ke_cell, 0.0)) / ke),
        "mean_bathy_high_speed_m": float(np.nanmean(bth[high2])),
        "mean_bathy_domain_m": float(np.nanmean(bth[m[0]])),
        "mean_slope_high_speed": float(np.nanmean(slope[high2])),
        "mean_slope_domain": float(np.nanmean(slope[m[0]])),
        "quadrant_ke_fraction": {k: v / ke for k, v in daily[n_days]["ke_quadrants"].items()},
    }

    # ---- figures -----------------------------------------------------------
    args.figdir.mkdir(parents=True, exist_ok=True)
    fig_days = [1, 5, 15, 30]
    fig, axes = plt.subplots(2, 2, figsize=(13, 11))
    for ax, day in zip(axes.ravel(), fig_days):
        d = load_day(nc_dir, day)
        spd = np.hypot(d["u"][0], d["v"][0])
        pc = ax.pcolormesh(d["lon"], d["lat"], np.where(d["mask"][0], spd, np.nan),
                           shading="auto", cmap="turbo", vmin=0, vmax=max(0.01, np.nanmax(spd)))
        ax.set_title(f"day {day}: surface speed max={np.nanmax(spd):.3f} m/s")
        ax.set_xlabel("lon"); ax.set_ylabel("lat")
        fig.colorbar(pc, ax=ax, label="m/s")
    fig.tight_layout()
    fig.savefig(args.figdir / "surface_speed_maps.png", dpi=130)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(13, 11))
    for ax, day in zip(axes.ravel(), fig_days):
        d = load_day(nc_dir, day)
        spd = np.hypot(d["u"], d["v"])
        k = np.argmax(np.where(d["mask"], spd, -np.inf), axis=0)
        smax = np.nanmax(np.where(d["mask"], spd, np.nan), axis=0)
        pc = ax.pcolormesh(d["lon"], d["lat"], np.where(d["mask"].any(axis=0), k + 1, np.nan),
                           shading="auto", cmap="viridis")
        ax.set_title(f"day {day}: level of column max speed (max={np.nanmax(smax):.3f})")
        ax.set_xlabel("lon"); ax.set_ylabel("lat")
        fig.colorbar(pc, ax=ax, label="level")
    fig.tight_layout()
    fig.savefig(args.figdir / "level_of_max_speed.png", dpi=130)
    plt.close(fig)

    days = [r["day"] for r in daily]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.semilogy(days, [r["ke_j"] for r in daily], "o-", label="KE")
    ax.semilogy(days, [r["ape_j"] for r in daily], "s--", label="APE proxy")
    ax.set_xlabel("day"); ax.set_ylabel("J"); ax.legend(); ax.grid(True, which="both", alpha=0.3)
    ax.set_title("T3 rest state: KE and APE")
    fig.tight_layout(); fig.savefig(args.figdir / "ke_ape_timeseries.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(days, [100 * r["ke_boundary_fraction"] for r in daily], "o-", label="boundary 5 cells")
    for q in ("SW", "SE", "NW", "NE"):
        ax.plot(days, [100 * r["ke_quadrants"][q] / r["ke_j"] if r["ke_j"] > 0 else 0.0
                       for r in daily], "--", label=q)
    ax.set_xlabel("day"); ax.set_ylabel("% of KE"); ax.legend(); ax.grid(alpha=0.3)
    ax.set_title("KE localisation")
    fig.tight_layout(); fig.savefig(args.figdir / "ke_localisation.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    kez = np.array([r["ke_by_depth_j"] for r in daily])
    for k in range(kez.shape[1]):
        ax.plot(days, kez[:, k], label=f"k={k+1}")
    ax.set_xlabel("day"); ax.set_ylabel("KE [J]"); ax.legend(ncol=3, fontsize=7)
    ax.set_title("KE by depth level"); fig.tight_layout()
    fig.savefig(args.figdir / "ke_by_depth.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    for day in (1, 10, 20, 30):
        if day <= n_days:
            ax.plot(daily[day]["drift_S_by_depth"], d0["z"], "o-", label=f"day {day}")
    ax.invert_yaxis(); ax.set_xlabel("S RMS drift [PSU]"); ax.set_ylabel("depth [m]")
    ax.legend(); ax.grid(alpha=0.3); ax.set_title("Salinity drift by depth")
    fig.tight_layout(); fig.savefig(args.figdir / "drift_S_by_depth.png", dpi=130); plt.close(fig)

    # geostrophic speed map
    fig, ax = plt.subplots(figsize=(9, 7))
    pc = ax.pcolormesh(d0["lon"], d0["lat"], np.where(wet[0], speed_geo[0], np.nan),
                       shading="auto", cmap="turbo")
    ax.set_title("Initial thermal-wind speed (surface, m/s)")
    ax.set_xlabel("lon"); ax.set_ylabel("lat"); fig.colorbar(pc, ax=ax)
    fig.tight_layout(); fig.savefig(args.figdir / "initial_geostrophic_speed.png", dpi=130); plt.close(fig)

    result = {
        "stage": "11.8.0 T3-CORRECTIVE-2",
        "run": args.run,
        "days": n_days,
        "geostrophic": geo_stats,
        "daily": daily,
        "budget": budget,
        "boundary": boundary_stats,
        "hot_spot": {
            "y": hot[0] + 1, "x": hot[1] + 1,
            "lat": float(dlast["lat"][hot]), "lon": float(dlast["lon"][hot]),
            "bathy_m": float(bth[hot]), "lev": int(d0["lev"][hot]),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=float))
    print(json.dumps({k: result[k] for k in ("geostrophic", "boundary", "hot_spot")},
                     indent=2, default=float))
    print(f"Results: {args.out}")
    print(f"Figures: {args.figdir}")


if __name__ == "__main__":
    main()
