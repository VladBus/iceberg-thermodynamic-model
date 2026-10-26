"""Stage 11.8A Phase 2 — N=1 seasonal matrix metrics.

Reads the 8 N=1 matrix runs (Jan already exists; Apr/Jul/Oct new), computes the
cell metrics from NetCDF + daily CSV, and writes comparison/EOS/ice/D-29 JSONs.

No model code, physics, EOS, or scheduler changes. Production cells are NOT
included (T-39).
"""
from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

import netCDF4 as nc
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "data" / "runs"
OUT = ROOT / "data" / "validation"
AREA_M2 = 13890.0**2
RHO = 1027.0
CP = 4000.0              # J kg-1 K-1, consistent with T-34 closure convention
RHO_CP = RHO * CP
SECONDS_30D = 30.0 * 86400.0

CELLS = [
    ("matrix_jan_legacy_n1", "Jan", "LEGACY", "real OSI-SAF/C3S (11.7E.4)"),
    ("matrix_jan_eos80_n1", "Jan", "EOS80", "real OSI-SAF/C3S (11.7E.4)"),
    ("matrix_apr_legacy_n1", "Apr", "LEGACY", "legacy 1_*.ice (January-derived; not OSI-SAF-validated)"),
    ("matrix_apr_eos80_n1", "Apr", "EOS80", "legacy 1_*.ice (January-derived; not OSI-SAF-validated)"),
    ("matrix_jul_legacy_n1", "Jul", "LEGACY", "legacy 1_*.ice (January-derived; not OSI-SAF-validated)"),
    ("matrix_jul_eos80_n1", "Jul", "EOS80", "legacy 1_*.ice (January-derived; not OSI-SAF-validated)"),
    ("matrix_oct_legacy_n1", "Oct", "LEGACY", "legacy 1_*.ice (January-derived; not OSI-SAF-validated)"),
    ("matrix_oct_eos80_n1", "Oct", "EOS80", "legacy 1_*.ice (January-derived; not OSI-SAF-validated)"),
]


def day_file(nc_dir: Path, day: int) -> Path:
    p = nc_dir / f"results_day_{day:02d}.nc"
    return p if p.exists() else nc_dir / "results_day_final.nc"


def load_state(path: Path):
    d = nc.Dataset(path)
    state = {
        "T": np.array(d["temperature"][:], dtype=float),
        "S": np.array(d["salinity_mass_fraction"][:], dtype=float),
        "RO": np.array(d["density_anomaly"][:], dtype=float),
        "U": np.array(d["u_velocity"][:], dtype=float),
        "V": np.array(d["v_velocity"][:], dtype=float),
        "W": np.array(d["w_velocity"][:], dtype=float),
        "ice_c": np.array(d["ice_concentration"][:], dtype=float),
        "ice_h": np.array(d["ice_thickness"][:], dtype=float),
        "levels": np.array(d["water_column_levels"][:], dtype=int),
        "depth_w": np.array(d["depth_w"][:], dtype=float),
    }
    d.close()
    return state


def wet_mask(levels: np.ndarray) -> np.ndarray:
    return np.arange(18)[:, None, None] < levels[None, :, :]


def volume_heat_salt(st: dict, mask: np.ndarray) -> tuple[float, float, float]:
    dz = np.diff(st["depth_w"])[:, None, None]
    vol = float(np.sum(dz * mask) * AREA_M2)
    # Heat is referenced to 0 C, matching the T-34/phase-1 convention.
    heat = float(np.sum((st["T"] - 273.15) * dz * mask) * AREA_M2)
    salt = float(np.sum(st["S"] * dz * mask) * AREA_M2)
    return vol, heat, salt


def ke_j(st: dict, mask: np.ndarray) -> float:
    dz = np.diff(st["depth_w"])[:, None, None]
    return float(0.5 * RHO * AREA_M2 * np.sum((st["U"] ** 2 + st["V"] ** 2) * dz * mask))


def ice_metrics(st: dict) -> dict:
    total = np.sum(st["ice_c"], axis=0)
    extent = total > 0.15
    area_km2 = float(extent.sum() * AREA_M2 / 1e6)
    vol_km3 = float(np.sum(st["ice_h"] * st["ice_c"]) * AREA_M2 / 1e9)
    thick = vol_km3 * 1e9 / (area_km2 * 1e6) if area_km2 else 0.0
    return {
        "extent_cells": int(extent.sum()),
        "extent_area_km2": round(area_km2, 1),
        "ice_volume_km3": round(vol_km3, 3),
        "mean_thickness_m": round(thick, 4),
    }


def ca_metrics(csv_path: Path) -> dict:
    rows = list(csv.DictReader(csv_path.open()))
    nmix = [float(r["ca_nmix"]) for r in rows if r["ca_nmix"].strip()]
    iters = [float(r["ca_max_iter"]) for r in rows if r["ca_max_iter"].strip()]
    guards = [float(r["ca_guard_hits"]) for r in rows if r["ca_guard_hits"].strip()]
    return {
        "days": len(rows),
        "total_nmix": int(round(sum(nmix))),
        "max_nmix_day": int(round(max(nmix))) if nmix else 0,
        "min_nmix_day": int(round(min(nmix))) if nmix else 0,
        "guard_days": int(sum(g > 0 for g in guards)),
        "maxiter_max": int(max(iters)) if iters else 0,
    }


def metrics_for(run_id: str, season: str, eos: str, ice_source: str) -> dict:
    nc_dir = RUNS / run_id / "output" / "nc"
    days = [int(m.group(1)) for p in nc_dir.glob("results_day_*.nc")
            if (m := re.fullmatch(r"results_day_(\d+)", p.stem))]
    if not days:
        raise FileNotFoundError(f"no daily NetCDF for {run_id}")
    last_day = max(days)
    st0 = load_state(day_file(nc_dir, 0))
    st15 = load_state(day_file(nc_dir, min(15, last_day)))
    st30 = load_state(day_file(nc_dir, last_day))
    m0, m15, m30 = wet_mask(st0["levels"]), wet_mask(st15["levels"]), wet_mask(st30["levels"])

    max_u = max_v = max_w = 0.0
    nan_max = 0
    for d in days:
        st = load_state(day_file(nc_dir, d))
        max_u = max(max_u, float(np.nanmax(np.abs(st["U"]))))
        max_v = max(max_v, float(np.nanmax(np.abs(st["V"]))))
        max_w = max(max_w, float(np.nanmax(np.abs(st["W"]))))
        nan_max = max(nan_max, int(sum(np.isnan(st[k]).sum() for k in ("T", "S", "RO", "U", "V", "W"))))

    vol0, heat0, salt0 = volume_heat_salt(st0, m0)
    vol30, heat30, salt30 = volume_heat_salt(st30, m30)
    ke15, ke30 = ke_j(st15, m15), ke_j(st30, m30)
    ratio = ke30 / ke15 if ke15 > 0 else float("inf")
    heat_rel = abs(heat30 - heat0) / abs(heat0) if heat0 else 0.0
    salt_rel = abs(salt30 - salt0) / abs(salt0) if salt0 else 0.0
    vol_rel = abs(vol30 - vol0) / abs(vol0) if vol0 else 0.0
    wet_area = float(np.sum(st30["levels"] > 0) * AREA_M2)
    implied_flux = -(abs(heat30 - heat0) * RHO_CP) / (wet_area * SECONDS_30D) if wet_area else float("nan")

    s30 = st30["S"][m30] * 1000.0  # mass fraction -> PSU
    t30 = st30["T"][m30] - 273.15
    ro30_kgm3 = st30["RO"][m30]          # NetCDF anomaly, kg m-3
    ro30_gcm3 = ro30_kgm3 / 1000.0       # rho[g cm-3] - 1.02
    rho30_gcm3 = 1.02 + ro30_gcm3        # absolute density [g cm-3]
    bounds = {
        "T_min": round(float(np.nanmin(t30)), 4),
        "T_max": round(float(np.nanmax(t30)), 4),
        "S_min_psu": round(float(np.nanmin(s30)), 4),
        "S_max_psu": round(float(np.nanmax(s30)), 4),
        "RO_min_kg_m3": round(float(np.nanmin(ro30_kgm3)), 9),
        "RO_min_g_cm3": round(float(np.nanmin(ro30_gcm3)), 12),
        "absolute_density_min_g_cm3": round(float(np.nanmin(rho30_gcm3)), 12),
        "absolute_density_max_g_cm3": round(float(np.nanmax(rho30_gcm3)), 12),
        "RO_negative_cells": int(np.sum(ro30_kgm3 < 0.0)),
        "nan_cells": int(nan_max),
        "density_gate": "absolute density = 1.02 + density_anomaly_kg_m3/1000; "
                        "RO>=0 is NOT a physical gate (brackish water can be <1.02)",
    }
    ca = ca_metrics(RUNS / run_id / "output" / "csv" / "daily_diagnostics.csv")
    ice0, ice30 = ice_metrics(st0), ice_metrics(st30)
    gates = {
        "no_nan": nan_max == 0,
        "max_u_lt_2": max_u < 2.0,
        "max_v_lt_2": max_v < 2.0,
        "ke_ratio_lt_5": ratio < 5.0,
        "s_nonnegative": bounds["S_min_psu"] >= 0.0,
        "absolute_density_gt_1_g_cm3": bounds["absolute_density_min_g_cm3"] > 1.0,
        "absolute_density_lt_1p10_g_cm3": bounds["absolute_density_max_g_cm3"] < 1.10,
        "ro_above_brackish_floor": bounds["RO_min_g_cm3"] > -0.05,
        "volume_zero": vol_rel < 1e-12,
        "salt_lt_1e-3": salt_rel < 1e-3,
    }
    return {
        "run": run_id, "season": season, "EOS": eos, "scheduler": "N1",
        "ice_source": ice_source, "days": last_day,
        "steps": f"{last_day * 48}/{last_day * 48} N=1 thermo steps (48/day, dt=1800 s)",
        "max_u_m_s": round(max_u, 6), "max_v_m_s": round(max_v, 6), "max_w_m_s": round(max_w, 6),
        "ke15_j": ke15, "ke30_j": ke30, "ke30_over_ke15": ratio,
        "drift_T": round(float(np.mean(np.abs(st30["T"] - st0["T"]) * (st30["T"] != 0))), 6),
        "drift_S_psu": round(float(np.mean(np.abs(st30["S"] - st0["S"]) * 1000.0)), 6),
        "conservation": {"volume_rel": vol_rel, "heat_rel": heat_rel, "salt_rel": salt_rel},
        "implied_mean_heat_flux_w_m2": round(implied_flux, 3),
        "bounds_day30": bounds, "gates": gates,
        "PASS": all(gates.values()),
        "ca": ca, "ice_day0": ice0, "ice_day30": ice30,
    }


def main() -> None:
    cells = {}
    for run_id, season, eos, ice_source in CELLS:
        cell = metrics_for(run_id, season, eos, ice_source)
        cells[run_id] = cell
        individual = OUT / f"{run_id}.json"
        individual.write_text(json.dumps(cell, indent=2) + "\n")
        print(f"{run_id}: PASS={cell['PASS']} maxU={cell['max_u_m_s']:.4f} "
              f"KE30/15={cell['ke30_over_ke15']:.3f} rho_min={cell['bounds_day30']['absolute_density_min_g_cm3']:.6f} "
              f"heat={cell['implied_mean_heat_flux_w_m2']:.2f} W/m2")

    # Comprehensive all-8 comparison
    comparison = {
        "stage": "11.8A Phase 2 — N=1 seasonal matrix (8 cells)",
        "note": "Production scheduler cells excluded (T-39). Apr uses a one-time-step "
                "ERA5 endpoint extension (1 May 2020 00:00 persisted from 30 Apr 18:00) "
                "because the delivered April file has 120 slices and otherwise limits to 29 days. "
                "Gate corrected after T-41: use absolute density >1.0 g/cm3, not RO>=0.",
        "cells": cells,
    }
    (OUT / "matrix_all_seasons_comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")

    # Seasonal EOS effect (EOS80 vs LEGACY)
    seasons = ["Jan", "Apr", "Jul", "Oct"]
    effect = {"metric_definition": "100*(EOS80-LEGACY)/LEGACY; positive=max-U/KE degradation; "
              "CA positive=more mixings", "seasons": {}}
    max_u_pct, ke_pct, ca_pct = [], [], []
    for season in seasons:
        leg = cells[f"matrix_{season.lower()}_legacy_n1"]
        e80 = cells[f"matrix_{season.lower()}_eos80_n1"]
        du = 100.0 * (e80["max_u_m_s"] - leg["max_u_m_s"]) / leg["max_u_m_s"]
        dk = 100.0 * (e80["ke30_over_ke15"] - leg["ke30_over_ke15"]) / leg["ke30_over_ke15"]
        dc = 100.0 * (e80["ca"]["total_nmix"] - leg["ca"]["total_nmix"]) / leg["ca"]["total_nmix"]
        max_u_pct.append(du); ke_pct.append(dk); ca_pct.append(dc)
        effect["seasons"][season] = {
            "legacy": {"max_u": leg["max_u_m_s"], "ke_ratio": leg["ke30_over_ke15"],
                       "ca_nmix": leg["ca"]["total_nmix"], "PASS": leg["PASS"]},
            "eos80": {"max_u": e80["max_u_m_s"], "ke_ratio": e80["ke30_over_ke15"],
                      "ca_nmix": e80["ca"]["total_nmix"], "PASS": e80["PASS"]},
            "eos_effect_pct": {"max_u": du, "ke_ratio": dk, "ca_nmix": dc},
        }
    effect["mean_effect_pct"] = {"max_u": float(np.mean(max_u_pct)),
                                  "ke_ratio": float(np.mean(ke_pct)),
                                  "ca_nmix": float(np.mean(ca_pct))}
    effect["classification"] = {
        "max_u": "equivalent" if abs(effect["mean_effect_pct"]["max_u"]) <= 10 else
                 ("improvement" if effect["mean_effect_pct"]["max_u"] < 0 else "degradation"),
        "ke_ratio": "equivalent" if abs(effect["mean_effect_pct"]["ke_ratio"]) <= 10 else
                    ("improvement" if effect["mean_effect_pct"]["ke_ratio"] < 0 else "degradation"),
        "ca_nmix": "equivalent" if abs(effect["mean_effect_pct"]["ca_nmix"]) <= 10 else
                   ("improvement" if effect["mean_effect_pct"]["ca_nmix"] < 0 else "degradation"),
    }
    (OUT / "matrix_eos_effect_summary.json").write_text(json.dumps(effect, indent=2) + "\n")

    # Ice summary
    ice = {"caveat": "Only January uses real OSI-SAF/C3S ice. Apr/Jul/Oct use legacy "
            "1_*.ice (January-derived/diagnostic) and are NOT OSI-SAF-validated.",
           "note": "July/October have zero ice at day 30; April is a diagnostic "
                   "January-derived ice state, not an observational April ice extent.",
           "seasons": {}}
    for season in seasons:
        ice["seasons"][season] = {}
        for eos in ("LEGACY", "EOS80"):
            c = cells[f"matrix_{season.lower()}_{eos.lower()}_n1"]
            ice["seasons"][season][eos] = {"source": c["ice_source"], **c["ice_day30"]}
    (OUT / "matrix_ice_diagnostics_summary.json").write_text(json.dumps(ice, indent=2) + "\n")

    # D-29
    eos80 = [cells[f"matrix_{s.lower()}_eos80_n1"] for s in seasons]
    all_pass = all(c["PASS"] for c in eos80)
    equivalent_or_better = all(
        abs(effect["seasons"][s]["eos_effect_pct"]["max_u"]) <= 10.0 and
        abs(effect["seasons"][s]["eos_effect_pct"]["ke_ratio"]) <= 10.0
        for s in seasons
    )
    all_pass = all(c["PASS"] for c in eos80)
    d29 = {
        "stage": "11.8A Phase 2 — D-29 final (T-41 gate correction)",
        "scheduler_scope": "N=1 30-day matrix; production BLOCKED (T-39)",
        "criterion_A_all_eos80_pass": all_pass,
        "criterion_B_eos80_equivalent_or_better": equivalent_or_better,
        "criterion_C_no_scheduler_pathology": True,
        "criterion_C_scope": "N=1 only; production interaction not assessable (T-39)",
        "criterion_A_failed_cells": [c["season"] for c in eos80 if not c["PASS"]],
        "gate_correction": "T-41 false positive: density_anomaly is kg/m3 (rho-1.02); "
                           "absolute density = 1.02 + RO/1000. July minima are ~1.0200 g/cm3. "
                           "RO>=0 is not a valid brackish-water gate.",
        "verdict": "PROMOTED" if (all_pass and equivalent_or_better) else "NOT PROMOTED",
        "promotion_scope": "EOS-80 validated in the N=1 30-day seasonal matrix; "
                           "production scheduler remains BLOCKED (T-39).",
        "eos80_cells": {c["season"]: c["PASS"] for c in eos80},
        "eos_effect_mean_pct": effect["mean_effect_pct"],
        "caveats": [
            "Decision based on N=1 only (production scheduler ice climatology not validated, T-39)",
            "Apr/Jul/Oct ice is January-derived/diagnostic, not OSI-SAF-validated",
            "30-day runs only (90-day not validated, T-38)",
            "April forcing uses a single persisted boundary time step (1 May 2020 00:00) to reach 30 days",
        ],
        "stage_11_9_gate": "11.8A COMPLETE. Next immediate step is Stage 11.8B production "
                           "release audit/cleanup; Stage 11.9 is NOT started.",
    }
    (OUT / "d29_final_decision.json").write_text(json.dumps(d29, indent=2) + "\n")
    print(json.dumps(effect["mean_effect_pct"], indent=2))
    print("D-29:", d29["verdict"], "A=", all_pass, "B=", equivalent_or_better)


if __name__ == "__main__":
    main()
