#!/usr/bin/env python3
"""Stage 10.16 — drift dynamics and T-07 investigation: analysis + plots.

Reads the controlled-experiment outputs produced by
``test/iceberg_test_drift_dynamics.f90``, the drift-scaling test outputs,
and the Stage 10.15.2 TEST_11 trajectory; generates the Stage 10.16 figure
set, machine-readable summaries, and synthetic-experiment tables.

Deterministic; output bundle ``data/output/stage10.16/`` (gitignored).

Run:
    conda run -n iceberg-thermodynamic-model \\
        python python/analysis/stage10.16_drift_analysis.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "output" / "stage10.16"
PLOTS = OUT / "plots"

# Constants (mirror iceberg_types.f90 — diagnostic reference only)
RHO_ICE = 910.0
RHO_WATER = 1028.0
RHO_AIR = 1.225
CD_AIR = 1.3e-3
CD_WATER = 2.0e-3
OMEGA = 7.2921150e-5

_FIELDS = {
    "step": int, "time_h": float, "x_m": float, "y_m": float,
    "lat_deg": float, "lon_deg": float, "L_m": float, "W_m": float,
    "H_m": float, "M_kg": float, "mb_mday": float, "ml_mday": float,
    "ms_mday": float, "u_ms": float, "v_ms": float,
}


def load_traj(path: Path) -> dict:
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


def load_fb(path: Path) -> dict:
    """Load force-balance CSV (space-delimited, no header)."""
    cols = ["step", "time_h", "u", "v", "u10", "v10", "u_cur", "v_cur",
            "f_wind_x", "f_wind_y", "f_water_x", "f_water_y",
            "f_cor_x", "f_cor_y", "rel_wind_speed", "rel_water_speed", "ax", "ay"]
    vals = np.loadtxt(path)
    out = {c: vals[:, i] for i, c in enumerate(cols)}
    out["speed"] = np.hypot(out["u"], out["v"])
    out["f_wind"] = np.hypot(out["f_wind_x"], out["f_wind_y"])
    out["f_water"] = np.hypot(out["f_water_x"], out["f_water_y"])
    out["f_cor"] = np.hypot(out["f_cor_x"], out["f_cor_y"])
    out["accel"] = np.hypot(out["ax"], out["ay"])
    return out


def haversine_m(lat1, lon1, lat2, lon2) -> np.ndarray:
    r = 6371.0e3
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = np.radians(np.asarray(lat2) - np.asarray(lat1))
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


# ---------------------------------------------------------------------------
def make_plots(traj: dict, fb: dict, ts: dict, size: dict) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # pragma: no cover
        return []
    saved = []

    def save(fig, name):
        p = PLOTS / name
        fig.savefig(p, dpi=140, bbox_inches="tight")
        saved.append(str(p))
        plt.close(fig)

    # 1. Force balance timeseries (B1: wind + Coriolis)
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    d1 = fb["B1_wind_cor"]
    t = d1["time_h"] / 24.0
    ax.plot(t, d1["f_wind"], "-", lw=1.0, label="wind drag |F_wind|")
    ax.plot(t, d1["f_water"], "-", lw=1.0, label="water drag |F_water|")
    ax.plot(t, d1["f_cor"], "-", lw=1.0, label="Coriolis |F_cor|")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("force [N]")
    ax.set_title("Stage 10.16 — force balance, wind 10 m/s + Coriolis (B1)")
    ax.legend()
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3)
    save(fig, "force_balance_timeseries.png")

    # 2. Wind-only response (B1 vs B2: with/without Coriolis)
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 3.8))
    for name, ax in (("B1_wind_cor", axes[0]), ("B2_wind_nocor", axes[1])):
        d = fb[name]
        tt = d["time_h"] / 24.0
        ax.plot(tt, d["u"], "-", lw=1.0, label="u (X)")
        ax.plot(tt, d["v"], "-", lw=1.0, label="v (Y)")
        ax.plot(tt, d["speed"], "--", lw=1.0, label="speed")
        ax.set_xlabel("time [day]")
        ax.set_ylabel("velocity [m/s]")
        ax.set_title("B1 wind+Coriolis" if name.startswith("B1") else "B2 wind, no Coriolis")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    fig.suptitle("Stage 10.16 — wind-only response (10 m/s, +X)")
    save(fig, "wind_only_response.png")

    # 3. Current-only response (C1 vs C2)
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 3.8))
    for name, ax in (("C1_current_cor", axes[0]), ("C2_current_nocor", axes[1])):
        d = fb[name]
        tt = d["time_h"] / 24.0
        ax.plot(tt, d["u"], "-", lw=1.0, label="u (X)")
        ax.plot(tt, d["v"], "-", lw=1.0, label="v (Y)")
        ax.plot(tt, d["speed"], "--", lw=1.0, label="speed")
        ax.axhline(0.1, color="gray", ls=":", lw=0.8, label="current 0.1 m/s")
        ax.set_xlabel("time [day]")
        ax.set_ylabel("velocity [m/s]")
        ax.set_title("C1 current+Coriolis" if name.startswith("C1") else "C2 current, no Coriolis")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    fig.suptitle("Stage 10.16 — current-only response (0.1 m/s, +X)")
    save(fig, "current_only_response.png")

    # 4. Combined forcing response (D)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    d = fb["D_combined"]
    tt = d["time_h"] / 24.0
    ax.plot(tt, d["u"], "-", lw=1.0, label="u (X)")
    ax.plot(tt, d["v"], "-", lw=1.0, label="v (Y)")
    ax.plot(tt, d["speed"], "--", lw=1.0, label="speed")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("velocity [m/s]")
    ax.set_title("Stage 10.16 — combined wind 10 m/s + current 0.1 m/s (D)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "combined_forcing_response.png")

    # 5. Timestep sensitivity (H)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.semilogx(ts["dt_s"], ts["final_speed_ms"], "o-", lw=1.2)
    ax.axhline(0.009, color="gray", ls=":", lw=0.9, label="continuous limit F/(Mf) ≈ 0.009")
    ax.set_xlabel("time step [s]")
    ax.set_ylabel("final speed [m/s]")
    ax.set_title("Stage 10.16 — timestep sensitivity, wind 10 m/s + Coriolis (H)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "timestep_sensitivity.png")

    # 6. Size sensitivity (I)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    w = size[size["current_speed_ms"] == 0]
    c = size[size["wind_speed_ms"] == 0]
    ax.loglog(w["size_m"], w["wind_ratio"], "o-", lw=1.2, label="wind ratio")
    ax.loglog(c["size_m"], c["current_ratio"], "s-", lw=1.2, label="current ratio")
    ax.set_xlabel("iceberg size L [m]")
    ax.set_ylabel("drift ratio")
    ax.set_title("Stage 10.16 — size sensitivity (I); dashed = 1/L scaling")
    s10 = float(w[w["size_m"] == 10.0]["wind_ratio"].iloc[0]) if len(w) else 0.001
    ax.loglog(w["size_m"], s10 * 10.0 / w["size_m"], "k--", lw=0.8, label="1/L reference")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "size_sensitivity.png")

    # 7. Drift scaling comparison (pre/post + expected bands)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot([5, 10, 15], [0.0004, 0.0008, 0.0012], "o-", lw=1.2, label="wind+Coriolis (measured)")
    ax.plot([5, 10, 15], [0.0298, 0.0341, 0.0345], "s-", lw=1.2, label="wind no-Coriolis (measured)")
    ax.axhspan(0.01, 0.02, color="gray", alpha=0.2, label="'expected' 1-2% band")
    ax.set_xlabel("wind speed [m/s]")
    ax.set_ylabel("drift ratio")
    ax.set_title("Stage 10.16 — drift scaling wind (T-07 comparison)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    save(fig, "drift_scaling_comparison.png")

    # 8. TEST_11 trajectory (post-fix, authoritative)
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    h = traj["time_h"] / 24.0
    sc = ax.scatter(traj["lon_deg"], traj["lat_deg"], c=h, cmap="viridis", s=10)
    ax.plot(traj["lon_deg"], traj["lat_deg"], "-", lw=0.7, color="#1f77b4", alpha=0.6)
    ax.plot(traj["lon_deg"][0], traj["lat_deg"][0], "g^", ms=12, label="start (day 1)")
    ax.plot(traj["lon_deg"][-1], traj["lat_deg"][-1], "rv", ms=12, label="end (day 30)")
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("Stage 10.16 — TEST_11 30-day trajectory (corrected run)")
    fig.colorbar(sc, ax=ax, label="time [day]")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "trajectory_pre_post_stage10.16.png")

    # 9. Speed timeseries (TEST_11)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    speed = np.hypot(traj["u_ms"], traj["v_ms"])
    ax.plot(h, speed, "-", lw=0.7, label="reported u/v")
    if len(speed) >= 48:
        # clearly labelled rolling mean (24 h window) as an additional curve
        win = 24
        k = np.ones(win) / win
        roll = np.convolve(speed, k, mode="valid")
        ax.plot(h[win - 1:], roll, "-", lw=1.4, color="C1", label="24 h rolling mean")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("speed [m/s]")
    ax.set_title("Stage 10.16 — TEST_11 drift speed vs time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "speed_timeseries.png")

    # 10. Relative-velocity timeseries (B1)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    d = fb["B1_wind_cor"]
    tt = d["time_h"] / 24.0
    ax.plot(tt, d["rel_wind_speed"], "-", lw=1.0, label="relative wind speed")
    ax.plot(tt, d["rel_water_speed"], "-", lw=1.0, label="relative water speed")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("relative speed [m/s]")
    ax.set_title("Stage 10.16 — relative velocities, wind 10 m/s + Coriolis (B1)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "relative_velocity_timeseries.png")

    return saved


# ---------------------------------------------------------------------------
def write_synthetic_csv(fb: dict, ts: dict, size: dict, out: Path) -> Path:
    path = out / "synthetic_experiments.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["experiment", "parameter", "value", "final_speed_ms", "ratio"])
        # B1/B2/C1/C2/D: final values
        for name, label, u_ref in (
                ("B1_wind_cor", "wind_coriolis_on", 10.0),
                ("B2_wind_nocor", "wind_coriolis_off", 10.0),
                ("C1_current_cor", "current_coriolis_on", 0.1),
                ("C2_current_nocor", "current_coriolis_off", 0.1),
                ("D_combined", "wind_current_combined", 10.0)):
            d = fb[name]
            sp = d["speed"][-1]
            w.writerow([label, "-", "-", f"{sp:.6f}", f"{sp/u_ref:.6f}"])
        # H
        for i in range(len(ts["dt_s"])):
            w.writerow(["timestep", "dt_s", f"{ts['dt_s'][i]:.0f}",
                        f"{ts['final_speed_ms'][i]:.6f}", f"{ts['ratio'][i]:.6f}"])
        # I
        for i in range(len(size)):
            r = size.iloc[i]
            ratio = float(r["wind_ratio"]) if float(r["current_speed_ms"]) == 0 else float(r["current_ratio"])
            w.writerow(["size", "L_m", f"{float(r['size_m']):.0f}",
                        f"{float(r['final_speed_ms']):.6f}", f"{ratio:.6f}"])
    return path


def write_drift_scaling_csv(out: Path) -> Path:
    path = out / "drift_scaling_comparison.csv"
    # measured from drift_scaling_wind / current / no_cor (post-fix runs)
    rows = [
        ["wind_with_coriolis", 5.0, 0.002004, 0.0004],
        ["wind_with_coriolis", 10.0, 0.008011, 0.0008],
        ["wind_with_coriolis", 15.0, 0.018012, 0.0012],
        ["wind_no_coriolis", 5.0, 0.148956, 0.0298],
        ["wind_no_coriolis", 10.0, 0.341317, 0.0341],
        ["wind_no_coriolis", 15.0, 0.517092, 0.0345],
        ["current_with_coriolis", 0.02, 0.000025, 0.0013],
        ["current_with_coriolis", 0.05, 0.000157, 0.0031],
        ["current_with_coriolis", 0.10, 0.000624, 0.0062],
        ["current_with_coriolis", 0.20, 0.002484, 0.0124],
    ]
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "forcing_ms", "iceberg_speed_ms", "ratio"])
        w.writerows(rows)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)

    # Load force-balance series
    fb = {}
    for name in ("B1_wind_cor", "B2_wind_nocor", "C1_current_cor",
                 "C2_current_nocor", "D_combined"):
        p = OUT / f"force_balance_timeseries_{name}.csv"
        if p.exists():
            fb[name] = load_fb(p)

    ts = {c: [] for c in ("dt_s", "steps", "final_speed_ms", "ratio")}
    with (OUT / "timestep_sensitivity.csv").open() as fh:
        for row in csv.reader(fh):
            if not row or not row[0].strip() or row[0].startswith("dt"):
                continue
            cells = row[0].split() if len(row) == 1 else row
            for i, c in enumerate(ts):
                ts[c].append(float(cells[i]))
    ts = {k: np.array(v) for k, v in ts.items()}

    import pandas as pd
    size = pd.read_csv(
        OUT / "size_sensitivity.csv", sep=r"\s+", header=None, skiprows=1,
        names=["size_m", "wind_speed_ms", "current_speed_ms",
               "final_speed_ms", "wind_ratio", "current_ratio"])

    # TEST_11 trajectory (post-fix authoritative)
    traj_path = REPO / "data" / "output" / "stage10.15_2" / "test11_trajectory_post_fix.csv"
    if not traj_path.exists():
        traj_path = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"
    traj = load_traj(traj_path)

    figs = make_plots(traj, fb, ts, size)
    synth_csv = write_synthetic_csv(fb, ts, size, OUT)
    drift_csv = write_drift_scaling_csv(OUT)

    # size rows as plain lists (no pandas dependency in the summary)
    wind_rows = size[size["current_speed_ms"] == 0][["size_m", "wind_ratio"]].values.tolist()
    curr_rows = size[size["wind_speed_ms"] == 0][["size_m", "current_ratio"]].values.tolist()

    # Summary
    summary = {
        "stage": "10.16",
        "mechanism": (
            "Coriolis-limited drift: at equilibrium the wind force is balanced "
            "by the Coriolis force (F_wind ~ M*f*|u|), NOT by water drag. "
            "For a 100-m cube (M=9.1e8 kg, f=1.42e-4 s-1, Mf=1.29e5 kg/s) the "
            "equilibrium speed u ~ F_wind/(Mf) = 0.009 m/s at 10 m/s wind "
            "(0.09%). The 1-2% literature wind ratio assumes a drag-limited "
            "balance (small mass or weak Coriolis) or a wind-driven surface "
            "current (Ekman), which the offline model does not include."),
        "experiments": {
            "A_zero_forcing": "velocity stays 0 (no artificial acceleration)",
            "B1_wind_coriolis": {"final_speed_ms": float(fb["B1_wind_cor"]["speed"][-1]),
                                 "ratio": float(fb["B1_wind_cor"]["speed"][-1] / 10.0)},
            "B2_wind_no_coriolis": {"final_speed_ms": float(fb["B2_wind_nocor"]["speed"][-1]),
                                    "ratio": float(fb["B2_wind_nocor"]["speed"][-1] / 10.0)},
            "C1_current_coriolis": {"final_speed_ms": float(fb["C1_current_cor"]["speed"][-1]),
                                    "ratio": float(fb["C1_current_cor"]["speed"][-1] / 0.1)},
            "C2_current_no_coriolis": {"final_speed_ms": float(fb["C2_current_nocor"]["speed"][-1]),
                                       "ratio": float(fb["C2_current_nocor"]["speed"][-1] / 0.1)},
            "D_combined": {"final_speed_ms": float(fb["D_combined"]["speed"][-1])},
            "E_wind_rotation": "consistent (90-deg rotation reproduces components)",
            "F_current_rotation": "consistent",
            "G_coriolis_on_off": "Coriolis ON 0.008 m/s vs OFF 0.345 m/s (43x suppression)",
            "H_timestep": {"dt_s": ts["dt_s"].tolist(),
                           "speed_ms": ts["final_speed_ms"].tolist()},
            "I_size_wind_ratio": wind_rows,
            "I_size_current_ratio": curr_rows,
        },
        "force_balance_B1_equilibrium": {
            "wind_N": float(fb["B1_wind_cor"]["f_wind"][-1]),
            "water_N": float(fb["B1_wind_cor"]["f_water"][-1]),
            "coriolis_N": float(fb["B1_wind_cor"]["f_cor"][-1]),
            "speed_ms": float(fb["B1_wind_cor"]["speed"][-1]),
            "comment": "wind ~ Coriolis >> water drag -> Coriolis-limited",
        },
        "t07_status": "PARTIALLY EXPLAINED",
        "t07_explanation": (
            "The low wind-drift ratio (0.04-0.13%) is the physically correct "
            "Coriolis-limited equilibrium of the implemented momentum balance "
            "for a 100-m cube (u ~ F_wind/(Mf)); the 1-2% reference assumes a "
            "drag-limited regime or wind-driven surface current absent from "
            "this offline model. Secondary numerical damping of the "
            "semi-implicit Coriolis scheme (equilibrium depends on dt: "
            "0.0087/0.0080/0.0063 m/s at dt=1800/3600/7200 s) contributes "
            "~10-30% at dt=3600 s and is documented; the primary cause is "
            "physical (Coriolis), verified by size scaling (ratio ~ 1/L) and "
            "the force balance."),
        "figures": [str(Path(f).relative_to(REPO)) for f in figs],
        "synthetic_csv": str(synth_csv.relative_to(REPO)),
        "drift_scaling_csv": str(drift_csv.relative_to(REPO)),
    }
    with (OUT / "stage10.16_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print("=" * 72)
    print("STAGE 10.16 — DRIFT DYNAMICS AND T-07 INVESTIGATION")
    print("=" * 72)
    for k in ("A_zero_forcing", "B1_wind_coriolis", "B2_wind_no_coriolis",
              "C1_current_coriolis", "C2_current_no_coriolis", "D_combined"):
        v = summary["experiments"][k]
        print(f"  {k:24s}: {v}")
    print(f"  G: {summary['experiments']['G_coriolis_on_off']}")
    print(f"  H: dt={summary['experiments']['H_timestep']['dt_s']} "
          f"speed={summary['experiments']['H_timestep']['speed_ms']}")
    print(f"  I wind ratio: {summary['experiments']['I_size_wind_ratio']}")
    print(f"  I current ratio: {summary['experiments']['I_size_current_ratio']}")
    fb1 = summary["force_balance_B1_equilibrium"]
    print(f"  B1 equilibrium: wind={fb1['wind_N']:.1f} N, water={fb1['water_N']:.3f} N, "
          f"cor={fb1['coriolis_N']:.1f} N, speed={fb1['speed_ms']:.5f} m/s")
    print(f"  T-07 status: {summary['t07_status']}")
    print(f"  figures: {len(figs)} -> {PLOTS.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())