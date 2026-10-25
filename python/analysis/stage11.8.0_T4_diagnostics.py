#!/usr/bin/env python3
"""Stage 11.8.0 T4 — diagnostics for the first forced run.

Reads data/runs/t4_wind_forcing/results_day_XX.nc and produces:
  data/validation/t4_ekman_analysis.json
  data/validation/t4_energy_budget.json
  data/validation/t4_comparison_t3.json
Basic metrics/NaN/conservation: t4_wind_forcing_metrics.json (existing script).
"""
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

P = Path(__file__).resolve().parents[2]
RUN = P / "data/runs/t4_wind_forcing/output/nc"
RHO0 = 1027.0
AREA = 13890.0**2
DX = 13890.0
AH = 10750.0  # 750 legacy + 10000 T3-CORRECTIVE-4


def load(day):
    with Dataset(RUN / f"results_day_{day:02d}.nc") as d:
        out = {k: np.array(d[k][:], dtype=np.float64) for k in
               ["u_velocity", "v_velocity", "w_velocity", "temperature",
                "salinity_mass_fraction", "density_anomaly", "water_column_levels",
                "depth", "depth_w", "tau_x", "tau_y", "wind_x", "wind_y",
                "wind_speed"]}
    kk = np.arange(out["temperature"].shape[0])[:, None, None]
    out["mask"] = (out["water_column_levels"][None] > 0) & (kk < out["water_column_levels"][None])
    out["dz"] = np.diff(out["depth_w"])
    out["vol"] = out["dz"][:, None, None] * AREA
    return out


def circ_mean(a):
    return float(np.rad2deg(np.angle(np.mean(np.exp(1j*np.deg2rad(a))))))


def ekman(days=(1, 15, 30)):
    rows = []
    for day in days:
        d = load(day)
        m = d["mask"][0]
        tx, ty = d["tau_x"], d["tau_y"]
        u, v = d["u_velocity"][0], d["v_velocity"][0]
        tau_mag = np.hypot(tx, ty)
        spd = np.hypot(u, v)
        sel = m & (tau_mag > 0.01) & (spd > 1e-3) & np.isfinite(tx) & np.isfinite(ty)
        ang = np.rad2deg(np.arctan2(tx*v - ty*u, tx*u + ty*v))
        # right turn in NH: angle < 0 (clockwise from stress to current)
        right = sel & (ang < 0.0) & (ang > -90.0)
        ek = sel & (ang > -75.0) & (ang < -15.0)
        rows.append({
            "day": day, "n_cells": int(sel.sum()),
            "mean_angle_deg": circ_mean(ang[sel]) if sel.any() else None,
            "median_angle_deg": float(np.median(ang[sel])) if sel.any() else None,
            "fraction_right": float(right.sum()/sel.sum()) if sel.any() else None,
            "fraction_15_75_right": float(ek.sum()/sel.sum()) if sel.any() else None,
            "mean_wind_stress_pa": float(np.mean(tau_mag[sel])) if sel.any() else None,
            "mean_surface_speed_m_s": float(np.mean(spd[sel])) if sel.any() else None,
        })
    for r in rows:
        r["ekman_observed_day"] = bool(
            r["mean_angle_deg"] is not None and r["mean_angle_deg"] < 0.0
            and (r["fraction_right"] or 0) > 0.5)
    out = {"test": "t4_ekman", "stage": "11.8.0 T4",
            "definition": "angle = atan2(tau_x*v - tau_y*u, tau_x*u + tau_y*v); negative = right of wind",
            "days": rows,
            "ekman_observed": any(r["ekman_observed_day"] for r in rows),
            "conclusion": ("rightward turning observed during spin-up" if any(
                r["ekman_observed_day"] for r in rows) else "no robust rightward turning")}
    return out


def energy(days=(1, 5, 10, 15, 20, 25, 30)):
    rows = []
    prev = None
    for day in days:
        d = load(day)
        m = d["mask"][0]
        u0, v0 = d["u_velocity"][0], d["v_velocity"][0]
        tx, ty = d["tau_x"], d["tau_y"]
        wind_work = float(np.nansum(np.where(m, tx*u0 + ty*v0, 0.0))*AREA)  # W
        m3 = d["mask"]
        ke = float(np.nansum(np.where(m3, 0.5*RHO0*(d["u_velocity"]**2 + d["v_velocity"]**2)*d["vol"], 0.0)))
        ke_prev = None
        if prev is not None:
            dp = load(prev)
            ke_prev = float(np.nansum(np.where(dp["mask"], 0.5*RHO0*(dp["u_velocity"]**2 + dp["v_velocity"]**2)*dp["vol"], 0.0)))
        dke_dt = (ke - ke_prev)/((day-prev)*86400.0) if ke_prev is not None else None
        # Laplacian dissipation (positive), horizontal gradients
        diss = 0.0
        for k in range(d["u_velocity"].shape[0]):
            mm = d["mask"][k]
            if not mm.any():
                continue
            du_dx = np.gradient(d["u_velocity"][k], DX, axis=1)
            du_dy = np.gradient(d["u_velocity"][k], DX, axis=0)
            dv_dx = np.gradient(d["v_velocity"][k], DX, axis=1)
            dv_dy = np.gradient(d["v_velocity"][k], DX, axis=0)
            diss += np.nansum(np.where(mm, RHO0*AH*(du_dx**2 + du_dy**2 + dv_dx**2 + dv_dy**2)*d["vol"][k], 0.0))
        rows.append({"day": day, "wind_work_w": wind_work, "ke_j": ke,
                     "dke_dt_w": dke_dt, "laplacian_dissipation_w": float(diss),
                     "mean_wind_speed_m_s": float(np.nanmean(np.where(m, d["wind_speed"], np.nan)))})
        prev = day
    return {"test": "t4_energy", "stage": "11.8.0 T4", "Ah_m2_s": AH,
            "days": rows,
            "mean_wind_work_w": float(np.mean([r["wind_work_w"] for r in rows])),
            "wind_work_positive": all(r["wind_work_w"] > 0 for r in rows)}


def compare_t3():
    import json as _json
    t3 = _json.loads((P / "data/validation/t3c4_final_results.json").read_text())["chosen"]
    t4 = _json.loads((P / "data/validation/t4_wind_forcing_metrics.json").read_text())["runs"]["t4_wind_forcing"]
    ke4 = t4["ke_day0_day15_day30"][2]
    ke3 = t3["ke_day30_j"]
    return {"test": "t4_vs_t3", "t4_ke30_j": ke4, "t3_ke30_j": ke3,
            "ke_ratio_t4_over_t3": ke4/ke3,
            "ke_increase_percent": 100.0*(ke4-ke3)/ke3,
            "t4_max_u_m_s": t4["max_u_over_run"], "t3_max_u_m_s": t3["max_u_m_s"],
            "surface_current_increase_m_s": t4["max_u_over_run"]-t3["max_u_m_s"]}


def main():
    outdir = P / "data/validation"
    ek = ekman()
    en = energy()
    cmp = compare_t3()
    (outdir / "t4_ekman_analysis.json").write_text(json.dumps(ek, indent=2))
    (outdir / "t4_energy_budget.json").write_text(json.dumps(en, indent=2))
    (outdir / "t4_comparison_t3.json").write_text(json.dumps(cmp, indent=2))
    print(json.dumps({"ekman": ek["days"], "energy": en["days"],
                      "comparison": cmp}, indent=2, default=float))


if __name__ == "__main__":
    main()
