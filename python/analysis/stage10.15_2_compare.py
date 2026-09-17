#!/usr/bin/env python3
"""Stage 10.15.2 — pre-fix / post-fix trajectory comparison.

Compares the Stage 10.15 (pre-fix, transposed bilinear weights) TEST_11
trajectory with the Stage 10.15.2 (post-fix, corrected) trajectory:

  * coordinate continuity (jumps, max geographic step);
  * implied geographic speed vs reported model speed (correlation);
  * model-coordinate kinematics (x/y implied speed, displacement);
  * thermodynamics (mass, geometry, melt);
  * drift-scaling outcome (T-07 re-evaluation, if files present).

Deterministic; reads only the preserved pre-fix CSV and the fresh post-fix
CSV; writes outputs to ``data/output/stage10.15_2/`` (gitignored).

Run:
    conda run -n iceberg-thermodynamic-model \\
        python python/analysis/stage10.15_2_compare.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PRE_CSV = REPO / "data" / "output" / "stage10.15_2" / "pre_fix" / "test11_trajectory_pre_fix.csv"
POST_CSV = REPO / "data" / "output" / "stage10.15_2" / "test11_trajectory_post_fix.csv"
RAW_CSV = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"
OUT_DIR = REPO / "data" / "output" / "stage10.15_2"
PLOT_DIR = OUT_DIR / "plots"

R_EARTH = 6371.0e3
JUMP_DEG = 0.05

_FIELDS = {
    "step": int, "time_h": float, "x_m": float, "y_m": float,
    "lat_deg": float, "lon_deg": float, "L_m": float, "W_m": float,
    "H_m": float, "M_kg": float, "mb_mday": float, "ml_mday": float,
    "ms_mday": float, "u_ms": float, "v_ms": float,
}


def load(path: Path) -> dict:
    rows = []
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        header = [h.strip() for h in header]
        for r in reader:
            cells = r[0].split() if len(r) == 1 else r
            if len(cells) != len(header):
                continue
            rows.append({k: _conv(v, _FIELDS[k]) for k, v in zip(header, cells)})
    out = {}
    for k in _FIELDS:
        out[k] = np.array([r[k] for r in rows], dtype=float)
    out["n"] = len(rows)
    return out


def _conv(value: str, caster):
    try:
        return caster(value)
    except (TypeError, ValueError):
        return float("nan")


def haversine_m(lat1, lon1, lat2, lon2) -> np.ndarray:
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = np.radians(np.asarray(lat2) - np.asarray(lat1))
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2.0 * R_EARTH * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def stats(t: dict, label: str) -> dict:
    n = t["n"]
    lat, lon = t["lat_deg"], t["lon_deg"]
    u, v = t["u_ms"], t["v_ms"]
    v_rep = np.hypot(u, v)

    dlat = np.abs(np.diff(lat))
    dlon = np.abs(np.diff(lon))
    jump = (dlat > JUMP_DEG) | (dlon > JUMP_DEG)

    dxm = np.diff(t["x_m"])
    dym = np.diff(t["y_m"])
    dt_s = np.diff(t["time_h"]) * 3600.0
    dist_xy = np.hypot(dxm, dym)
    v_impl_xy = dist_xy / dt_s

    geo_dist = haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:])
    v_impl_geo = geo_dist / dt_s

    return {
        "label": label,
        "n": n,
        "jumps_count": int(jump.sum()),
        "jump_steps": [int(t["step"][k]) for k in np.where(jump)[0]],
        "max_dlat_deg": float(dlat.max()),
        "max_dlon_deg": float(dlon.max()),
        "max_geographic_step_m": float(geo_dist.max()),
        "max_implied_geo_speed_ms": float(v_impl_geo.max()),
        "max_reported_speed_ms": float(v_rep.max()),
        "max_implied_xy_speed_ms": float(v_impl_xy.max()),
        "max_implied_vs_reported_ms": float(np.abs(v_impl_xy - v_rep[:-1]).max()),
        "corr_geo_vs_reported": float(np.corrcoef(v_impl_geo, v_rep[:-1])[0, 1])
        if np.std(v_impl_geo) > 0 else float("nan"),
        "displacement_straight_km": float(np.hypot(
            t["x_m"][-1] - t["x_m"][0], t["y_m"][-1] - t["y_m"][0]) / 1000.0),
        "path_length_km": float(np.sum(dist_xy) / 1000.0),
        "lat_range": [float(lat.min()), float(lat.max())],
        "lon_range": [float(lon.min()), float(lon.max())],
        "mass_initial_Mt": float(t["M_kg"][0] / 1e6),
        "mass_final_Mt": float(t["M_kg"][-1] / 1e6),
        "mass_change_pct": float((t["M_kg"][-1] - t["M_kg"][0]) / t["M_kg"][0] * 100.0),
        "L_final": float(t["L_m"][-1]),
        "H_final": float(t["H_m"][-1]),
        "melt_max_mday": {
            "basal": float(t["mb_mday"].max()),
            "lateral": float(t["ml_mday"].max()),
            "surface": float(t["ms_mday"].max()),
        },
    }


def make_plots(pre: dict, post: dict, out: Path) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # pragma: no cover
        return []
    saved = []
    h = post["time_h"] / 24.0

    def save(fig, name):
        p = out / name
        fig.savefig(p, dpi=140, bbox_inches="tight")
        saved.append(str(p))
        plt.close(fig)

    # 1. Pre vs post trajectory
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.plot(pre["lon_deg"], pre["lat_deg"], "-", lw=0.8, color="gray",
            label="pre-fix (8 jumps)")
    ax.plot(post["lon_deg"], post["lat_deg"], "-", lw=1.2, color="#1f77b4",
            label="post-fix (corrected)")
    ax.plot(pre["lon_deg"][0], pre["lat_deg"][0], "ks", ms=6)
    ax.plot(post["lon_deg"][0], post["lat_deg"][0], "g^", ms=9, label="start")
    ax.plot(post["lon_deg"][-1], post["lat_deg"][-1], "rv", ms=9, label="end")
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("Stage 10.15.2 — pre-fix vs post-fix trajectory (TEST_11)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig1_pre_vs_post_trajectory.png")

    # 2. Geographic step size
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    gpre = haversine_m(pre["lat_deg"][:-1], pre["lon_deg"][:-1],
                       pre["lat_deg"][1:], pre["lon_deg"][1:])
    gpost = haversine_m(post["lat_deg"][:-1], post["lon_deg"][:-1],
                        post["lat_deg"][1:], post["lon_deg"][1:])
    ax.plot(h[1:], gpre / 1000.0, "-", lw=0.8, color="gray", label="pre-fix")
    ax.plot(h[1:], gpost / 1000.0, "-", lw=0.8, color="#1f77b4", label="post-fix")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("geographic step [km]")
    ax.set_yscale("log")
    ax.set_title("Stage 10.15.2 — geographic step size (log scale)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig2_geographic_step_size.png")

    # 3. Implied vs reported speed
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    vpost = np.hypot(post["u_ms"], post["v_ms"])
    ax.plot(h, vpost, "--", lw=0.9, label="reported u/v (post-fix)")
    ax.plot(h[1:], gpost / np.diff(post["time_h"]) / 3600.0, "-", lw=0.9,
            label="implied geographic (post-fix)")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("speed [m/s]")
    ax.set_title("Stage 10.15.2 — reported vs implied geographic speed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig3_reported_vs_implied_speed.png")

    # 4. x/y model trajectory (both runs)
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.plot(pre["x_m"] / 1000.0, pre["y_m"] / 1000.0, "-", lw=0.8, color="gray",
            label="pre-fix x/y")
    ax.plot(post["x_m"] / 1000.0, post["y_m"] / 1000.0, "-", lw=1.2,
            color="#2ca02c", label="post-fix x/y")
    ax.set_xlabel("x [km]")
    ax.set_ylabel("y [km]")
    ax.set_title("Stage 10.15.2 — model-coordinate trajectory (x/y)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig4_xy_trajectory.png")

    # 5. Mass comparison
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(h, pre["M_kg"] / 1e6, "-", lw=0.8, color="gray", label="pre-fix")
    ax.plot(h, post["M_kg"] / 1e6, "-", lw=1.0, color="#1f77b4", label="post-fix")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("mass [Mt]")
    ax.set_title("Stage 10.15.2 — mass comparison")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig5_mass_comparison.png")

    return saved


def write_per_step_csv(pre: dict, post: dict, out: Path) -> Path:
    path = out / "per_step_comparison.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["step", "time_h",
                    "pre_x_m", "pre_y_m", "pre_lat", "pre_lon",
                    "post_x_m", "post_y_m", "post_lat", "post_lon",
                    "post_u_ms", "post_v_ms",
                    "geo_step_pre_m", "geo_step_post_m",
                    "implied_geo_speed_pre_ms", "implied_geo_speed_post_ms",
                    "reported_speed_post_ms"])
        n = min(pre["n"], post["n"])
        gpre = haversine_m(pre["lat_deg"][:-1], pre["lon_deg"][:-1],
                           pre["lat_deg"][1:], pre["lon_deg"][1:])
        gpost = haversine_m(post["lat_deg"][:-1], post["lon_deg"][:-1],
                            post["lat_deg"][1:], post["lon_deg"][1:])
        dt_s = np.diff(post["time_h"]) * 3600.0
        vpost = np.hypot(post["u_ms"], post["v_ms"])
        for k in range(n):
            gs_pre = gpre[k - 1] if k > 0 else 0.0
            gs_post = gpost[k - 1] if k > 0 else 0.0
            vi_pre = gs_pre / dt_s[k - 1] if k > 0 else 0.0
            vi_post = gs_post / dt_s[k - 1] if k > 0 else 0.0
            w.writerow([
                int(post["step"][k]), post["time_h"][k],
                f"{pre['x_m'][k]:.2f}", f"{pre['y_m'][k]:.2f}",
                f"{pre['lat_deg'][k]:.6f}", f"{pre['lon_deg'][k]:.6f}",
                f"{post['x_m'][k]:.2f}", f"{post['y_m'][k]:.2f}",
                f"{post['lat_deg'][k]:.6f}", f"{post['lon_deg'][k]:.6f}",
                f"{post['u_ms'][k]:.6f}", f"{post['v_ms'][k]:.6f}",
                f"{gs_pre:.2f}", f"{gs_post:.2f}",
                f"{vi_pre:.6f}", f"{vi_post:.6f}",
                f"{vpost[k]:.6f}",
            ])
    return path


def load_drift_scaling() -> dict:
    """Load drift-scaling diagnostics (pre-fix archive) if present."""
    out = {}
    path = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "drift_scaling.json"
    if path.exists():
        try:
            out["drift_scaling_json"] = json.loads(path.read_text())
        except Exception:
            out["drift_scaling_json"] = None
    return out


def main() -> int:
    if not PRE_CSV.exists() or not POST_CSV.exists():
        print(f"ERROR: need pre-fix CSV ({PRE_CSV}) and post-fix CSV ({POST_CSV})")
        return 1

    pre = load(PRE_CSV)
    post = load(POST_CSV)
    s_pre = stats(pre, "pre-fix")
    s_post = stats(post, "post-fix")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    figs = make_plots(pre, post, PLOT_DIR)
    per_step = write_per_step_csv(pre, post, OUT_DIR)

    drift = load_drift_scaling()

    summary = {
        "stage": "10.15.2",
        "pre_fix_csv": str(PRE_CSV.relative_to(REPO)),
        "post_fix_csv": str(POST_CSV.relative_to(REPO)),
        "pre": s_pre,
        "post": s_post,
        "difference": {
            "jumps": s_pre["jumps_count"] - s_post["jumps_count"],
            "max_geographic_step_m": s_pre["max_geographic_step_m"] - s_post["max_geographic_step_m"],
            "max_implied_geo_speed_ms": s_pre["max_implied_geo_speed_ms"] - s_post["max_implied_geo_speed_ms"],
            "corr_geo_vs_reported": s_pre["corr_geo_vs_reported"] - s_post["corr_geo_vs_reported"],
            "mass_final_Mt": s_pre["mass_final_Mt"] - s_post["mass_final_Mt"],
        },
        "t07": {
            "status": "OPEN — drift anomaly not resolved by this fix; see drift-scaling comparison",
            "pre_fix_archive": drift.get("drift_scaling_json"),
        },
        "per_step_csv": str(per_step.relative_to(REPO)),
        "figures": [str(Path(f).relative_to(REPO)) for f in figs],
    }
    with (OUT_DIR / "comparison_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print("=" * 72)
    print("STAGE 10.15.2 — PRE-FIX vs POST-FIX COMPARISON")
    print("=" * 72)
    for s in (s_pre, s_post):
        print(f"\n--- {s['label']} ---")
        print(f"  jumps: {s['jumps_count']}  steps: {s['jump_steps']}")
        print(f"  max dlat: {s['max_dlat_deg']:.5f} deg, max dlon: {s['max_dlon_deg']:.5f} deg")
        print(f"  max geographic step: {s['max_geographic_step_m']:.1f} m")
        print(f"  max implied geo speed: {s['max_implied_geo_speed_ms']:.4f} m/s")
        print(f"  max reported speed: {s['max_reported_speed_ms']:.4f} m/s")
        print(f"  max implied (x/y) speed: {s['max_implied_xy_speed_ms']:.4f} m/s")
        print(f"  max |implied - reported| (x/y): {s['max_implied_vs_reported_ms']:.4f} m/s")
        print(f"  corr(geo, reported): {s['corr_geo_vs_reported']:.4f}")
        print(f"  displacement: {s['displacement_straight_km']:.2f} km straight, "
              f"{s['path_length_km']:.2f} km path")
        print(f"  lat: {s['lat_range'][0]:.4f}..{s['lat_range'][1]:.4f}, "
              f"lon: {s['lon_range'][0]:.4f}..{s['lon_range'][1]:.4f}")
        print(f"  mass: {s['mass_initial_Mt']:.1f} -> {s['mass_final_Mt']:.1f} Mt "
              f"({s['mass_change_pct']:.2f}%)")
        print(f"  L final: {s['L_final']:.2f} m, H final: {s['H_final']:.2f} m")
        print(f"  melt max [m/day]: {s['melt_max_mday']}")
    print(f"\noutputs -> {OUT_DIR.relative_to(REPO)}/")
    print(f"  figures: {len(figs)}")
    print(f"  per-step CSV: {per_step.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())