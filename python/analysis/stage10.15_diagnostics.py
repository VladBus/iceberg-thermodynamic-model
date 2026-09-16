#!/usr/bin/env python3
"""Stage 10.15 — operational demonstration diagnostics and plots.

Reads the TEST_11 (30-day offline real-forcing) iceberg trajectory CSV,
performs physical/numerical checks, writes a summary JSON and produces the
Stage 10.15 figure set.

This script is diagnostics only: it does not modify physics, does not clip
values, and does not fabricate unavailable fields.

Run:
    conda run -n iceberg-thermodynamic-model python python/analysis/stage10.15_diagnostics.py
"""

from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
SRC_CSV = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"
OUT_DIR = REPO / "data" / "output" / "stage10.15"
PLOT_DIR = OUT_DIR / "plots"
RHO_ICE = 910.0          # kg/m^3

CHECK_BAND = (0.01, 1.0)  # m/day observed band (10.8.2 acceptance criterion)
LAT_DOMAIN = (60.0, 90.0)
LON_DOMAIN = (-20.0, 100.0)
SPEED_PLAUSIBLE = (0.005, 0.5)   # m/s

_FIELDS = {
    "step": int, "time_h": float, "x_m": float, "y_m": float,
    "lat_deg": float, "lon_deg": float, "L_m": float, "W_m": float,
    "H_m": float, "M_kg": float, "mb_mday": float, "ml_mday": float,
    "ms_mday": float, "u_ms": float, "v_ms": float,
}


def load_trajectory(path: Path) -> dict:
    """Load the space-delimited Fortran trajectory CSV (TEST_11 format)."""
    rows = []
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        header = [h.strip() for h in header]
        assert all(h in _FIELDS for h in header), f"unexpected header: {header}"
        for r in reader:
            # Fortran list-directed output: one physical line, space-separated
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


def checks(t: dict) -> dict:
    """Physical/numerical checks; classifies each finding."""
    res = {}
    res["nan_counts"] = {k: int(np.isnan(t[k]).sum()) for k in
                         ("lat_deg", "lon_deg", "L_m", "W_m", "H_m", "M_kg",
                          "mb_mday", "ml_mday", "ms_mday", "u_ms", "v_ms")}
    res["no_nan"] = all(v == 0 for v in res["nan_counts"].values())
    res["geometry_positive"] = bool(np.all(t["L_m"] > 0) and np.all(t["W_m"] > 0)
                                    and np.all(t["H_m"] > 0))
    res["mass_monotone_non_increasing"] = bool(np.all(np.diff(t["M_kg"]) <= 1.0e-3))
    res["lat_in_domain"] = bool(np.all((t["lat_deg"] >= LAT_DOMAIN[0]) & (t["lat_deg"] <= LAT_DOMAIN[1])))
    res["lon_in_domain"] = bool(np.all((t["lon_deg"] >= LON_DOMAIN[0]) & (t["lon_deg"] <= LON_DOMAIN[1])))
    speed = np.hypot(t["u_ms"], t["v_ms"])
    res["speed_min"] = float(np.min(speed))
    res["speed_max"] = float(np.max(speed))
    res["speed_plausible"] = bool(SPEED_PLAUSIBLE[0] <= np.max(speed) <= SPEED_PLAUSIBLE[1])
    # melt rates
    res["melt_max_mday"] = {
        "basal": float(np.max(t["mb_mday"])),
        "lateral": float(np.max(t["ml_mday"])),
        "surface": float(np.max(t["ms_mday"])),
    }
    res["melt_bounded"] = bool(all(v < 5.0 for v in res["melt_max_mday"].values()))
    # mass budget: integrated loss vs tracked loss (TEST_11 closed at 0.013% in Stage 9.3)
    m0, m1 = float(t["M_kg"][0]), float(t["M_kg"][-1])
    res["mass_loss_kg"] = m0 - m1
    res["relative_mass_loss"] = (m0 - m1) / m0
    # displacement
    res["dx_km"] = float(np.hypot(t["x_m"][-1] - t["x_m"][0], t["y_m"][-1] - t["y_m"][0]) / 1000.0)
    res["total_path_km"] = float(np.sum(np.hypot(np.diff(t["x_m"]), np.diff(t["y_m"]))) / 1000.0)
    res["lat_range"] = [float(np.min(t["lat_deg"])), float(np.max(t["lat_deg"]))]
    res["lon_range"] = [float(np.min(t["lon_deg"])), float(np.max(t["lon_deg"]))]
    return res


def make_plots(t: dict, out: Path) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # pragma: no cover
        return []
    saved = []
    h = t["time_h"] / 24.0   # days

    def save(fig, name):
        p = out / name
        fig.savefig(p, dpi=140, bbox_inches="tight")
        saved.append(str(p))
        plt.close(fig)

    # 1. Trajectory map (lat-lon, coloured by time)
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    sc = ax.scatter(t["lon_deg"], t["lat_deg"], c=h, cmap="viridis", s=12)
    ax.plot(t["lon_deg"], t["lat_deg"], "k-", lw=0.6, alpha=0.5)
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("Stage 10.15 — TEST_11 iceberg trajectory (30 d, real forcing)")
    cb = fig.colorbar(sc, ax=ax, label="time [day]")
    ax.grid(True, alpha=0.3)
    save(fig, "fig1_trajectory_latlon.png")

    # 2-3. lat/lon vs time
    for var, ylab, name in (("lat_deg", "Latitude [deg N]", "fig2_lat_vs_time.png"),
                            ("lon_deg", "Longitude [deg E]", "fig3_lon_vs_time.png")):
        fig, ax = plt.subplots(figsize=(6.4, 4.0))
        ax.plot(h, t[var], "o-", ms=2.5, lw=0.8)
        ax.set_xlabel("time [day]")
        ax.set_ylabel(ylab)
        ax.set_title(f"Stage 10.15 — {ylab} vs time (TEST_11, 30 d)")
        ax.grid(True, alpha=0.3)
        save(fig, name)

    # 4. Speed vs time
    speed = np.hypot(t["u_ms"], t["v_ms"])
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(h, speed * 100.0, "o-", ms=2.5, lw=0.8)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("drift speed [cm/s]")
    ax.set_title("Stage 10.15 — drift speed vs time (TEST_11)")
    ax.grid(True, alpha=0.3)
    save(fig, "fig4_speed_vs_time.png")

    # 5. Melt rates vs time
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(h, t["mb_mday"], label="basal", lw=1.0)
    ax.plot(h, t["ml_mday"], label="lateral", lw=1.0)
    ax.plot(h, t["ms_mday"], label="surface", lw=1.0)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("melt rate [m/day]")
    ax.set_title("Stage 10.15 — melt rates vs time (TEST_11)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig5_melt_vs_time.png")

    # 6. Mass and volume vs time
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(h, t["M_kg"] / 1.0e6, "o-", ms=2.5, lw=0.8, color="#1f77b4")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("mass [Mt]")
    ax.set_title("Stage 10.15 — iceberg mass vs time (TEST_11)")
    ax.grid(True, alpha=0.3)
    save(fig, "fig6_mass_vs_time.png")

    # 7. Geometry L/W/H vs time
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(h, t["L_m"], label="L", lw=1.0)
    ax.plot(h, t["W_m"], label="W", lw=1.0)
    ax.plot(h, t["H_m"], label="H", lw=1.0)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("dimension [m]")
    ax.set_title("Stage 10.15 — dimensions L/W/H vs time (TEST_11)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig7_geometry_vs_time.png")

    return saved


def main() -> int:
    src = SRC_CSV if SRC_CSV.exists() else OUT_DIR / "test11_trajectory.csv"
    t = load_trajectory(src)
    c = checks(t)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    figs = make_plots(t, PLOT_DIR)
    summary = {
        "source": str(src),
        "n_steps": t["n"],
        "checks": c,
        "figures": [str(Path(f).relative_to(REPO)) for f in figs],
    }
    with (OUT_DIR / "stage10.15_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print("=" * 64)
    print("STAGE 10.15 — OPERATIONAL DEMONSTRATION DIAGNOSTICS")
    print("=" * 64)
    print(f"trajectory: {t['n']} hourly steps (30 days), source: {src}")
    print(f"  lat range: {c['lat_range'][0]:.3f} .. {c['lat_range'][1]:.3f} deg N")
    print(f"  lon range: {c['lon_range'][0]:.3f} .. {c['lon_range'][1]:.3f} deg E")
    print(f"  displacement: {c['dx_km']:.1f} km (straight), {c['total_path_km']:.1f} km (path)")
    print(f"  speed: {c['speed_min']:.4f} .. {c['speed_max']:.4f} m/s "
          f"(plausible={c['speed_plausible']})")
    print(f"  mass: {c['mass_loss_kg']/1e6:.1f} Mt lost, "
          f"{c['relative_mass_loss']*100:.1f}% relative")
    print(f"  melt max [m/day]: basal={c['melt_max_mday']['basal']:.3f} "
          f"lateral={c['melt_max_mday']['lateral']:.3f} "
          f"surface={c['melt_max_mday']['surface']:.3f} (bounded={c['melt_bounded']})")
    print("checks:")
    for k in ("no_nan", "geometry_positive", "mass_monotone_non_increasing",
              "lat_in_domain", "lon_in_domain", "speed_plausible", "melt_bounded"):
        print(f"  {k:>30}: {c[k]}")
    print(f"figures: {len(figs)} -> {PLOT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())