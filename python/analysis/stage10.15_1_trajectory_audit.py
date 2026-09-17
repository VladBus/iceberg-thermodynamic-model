#!/usr/bin/env python3
"""Stage 10.15.1 — trajectory continuity and output integrity audit.

Audits the Stage 10.15/10.15.2 TEST_11 30-day Lagrangian iceberg trajectory
CSV (``data/output/stage10.15/test11_trajectory.csv``; the raw Fortran output
is ``data/output/diagnostics/stage9.3/test11_trajectory.csv``).

Deterministic: operates only on the actual model output, never modifies the
original CSV, writes derived outputs to ``data/output/stage10.15_1/``.

Stage 10.15.1 findings (historical, pre-fix):
  * model coordinates (``x_m``, ``y_m``) are continuous and kinematically
    consistent with the reported velocity;
  * the geographic columns (``lat_deg``, ``lon_deg``) contained 8 real
    discontinuities of ~0.17 deg (~19 km) at model-cell boundary crossings,
    caused by transposed bilinear weights in ``model_coords_to_latlon`` /
    ``bilinear_interp_3d`` (x-weight applied to the i index, y-weight to the
    j index, while the declared mapping is j <-> X, i <-> Y).

Stage 10.15.2 (this source state): the transposed cross terms were fixed in
``src/iceberg_forcing.f90``. This script now verifies the POST-FIX contract:
  * the CSV lat/lon must match the index-consistent (production) formula;
  * the geographic trajectory must be continuous (0 jumps > 0.05 deg);
  * implied geographic speed must match the reported model speed.
  The pre-fix (transposed) formula is reproduced as a regression oracle: the
  CSV must NOT match it anymore. Pre-fix CSV copies are preserved under
  ``data/output/stage10.15_2/pre_fix/``.

Run:
    conda run -n iceberg-thermodynamic-model \\
        python python/analysis/stage10.15_1_trajectory_audit.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
SRC_CSV = REPO / "data" / "output" / "stage10.15" / "test11_trajectory.csv"
RAW_CSV = REPO / "data" / "output" / "diagnostics" / "stage9.3" / "test11_trajectory.csv"
KOORD = REPO / "data" / "input" / "generated" / "real_grid" / "KOORD.DAT"
OUT_DIR = REPO / "data" / "output" / "stage10.15_1"
PLOT_DIR = OUT_DIR / "plots"

DX = 13890.0          # model grid spacing [m] (param.f90 / grid conventions)
IS1, JS1 = 133, 105   # grid nodes (i=1..133, j=1..105), i <-> Y, j <-> X

# ---------------------------------------------------------------------------
# Thresholds (documented; separated by class — see report §4)
# ---------------------------------------------------------------------------
# Hard data-integrity:
EXPECTED_ROWS = 720             # 24 h * 30 d, dt = 1 h
DT_HOURS = 1.0
LAT_DOMAIN = (60.0, 90.0)       # existing Stage 10.15 convention
LON_DOMAIN = (-20.0, 100.0)
MASS_MONO_EPS = 1.0e-3          # existing Stage 10.15 convention (kg)
# Diagnostic warning / discontinuity detection:
JUMP_DEG = 0.05                 # |d(lat)| or |d(lon)| > 0.05 deg between
                                # consecutive rows -> discontinuity flag.
                                # Justification: the corrected formula has
                                # max step 0.0007 deg lat / 0.0034 deg lon;
                                # 0.05 deg is > 10x the corrected max and
                                # ~1 grid-cell jump (~0.12-0.17 deg).
DISP_JUMP_M = 5000.0            # displacement > 5 km in one step -> anomaly
SPEED_MISMATCH_MS = 0.01        # |implied - reported| > 0.01 m/s -> warning
SPEED_IMPL_MAX_MS = 0.5         # implied speed > 0.5 m/s -> warning
# Model-specific plausibility (existing TEST_11 / Stage 10.15 conventions):
SPEED_BAND = (0.005, 0.5)       # m/s (TEST_11 check 4)
MELT_MAX_MDAY = 5.0             # m/day (TEST_11 check 5)

_FIELDS = {
    "step": int, "time_h": float, "x_m": float, "y_m": float,
    "lat_deg": float, "lon_deg": float, "L_m": float, "W_m": float,
    "H_m": float, "M_kg": float, "mb_mday": float, "ml_mday": float,
    "ms_mday": float, "u_ms": float, "v_ms": float,
}


# ---------------------------------------------------------------------------
# Grid loading and interpolation (faithful reproductions)
# ---------------------------------------------------------------------------
def load_grid(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load KOORD.DAT: fi (lat) and dl (lon), Fortran column-major (IS1, JS1)."""
    with path.open() as fh:
        fi_line = fh.readline().strip()
        dl_line = fh.readline().strip()
    fi = np.array([float(x) for x in fi_line.split()], dtype=np.float32) \
           .reshape((IS1, JS1), order="F").astype(float)
    dl = np.array([float(x) for x in dl_line.split()], dtype=np.float32) \
           .reshape((IS1, JS1), order="F").astype(float)
    return fi, dl


def model_coords_to_indices(xm: float, ym: float) -> tuple[int, int, bool]:
    """Faithful reproduction of model_coords_to_indices (src/iceberg_forcing.f90).

    j_idx = floor(x/DX) + 1   (j <-> X)
    i_idx = floor(y/DX) + 1   (i <-> Y)
    """
    j_idx = int(math.floor(xm / DX)) + 1
    i_idx = int(math.floor(ym / DX)) + 1
    in_domain = 1 <= i_idx < IS1 and 1 <= j_idx < JS1
    return i_idx, j_idx, in_domain


def interp_latlon(xm: float, ym: float, fi: np.ndarray, dl: np.ndarray,
                  corrected: bool) -> tuple[float | None, float | None]:
    """Bilinear interpolation of fi/dl at (xm, ym).

    ``corrected=False``: exact reproduction of the formula as written in
    ``model_coords_to_latlon`` / ``bilinear_interp_3d`` (weights wx on the
    i index, wy on the j index — transposed relative to the j<->X, i<->Y
    mapping).

    ``corrected=True``: index-consistent bilinear (x-weight wx varies j,
    y-weight wy varies i):
        lat = wx1*wy1*fi(i1,j1) + wx*wy1*fi(i1,j2)
            + wx1*wy*fi(i2,j1) + wx*wy*fi(i2,j2)
    """
    i_idx, j_idx, in_domain = model_coords_to_indices(xm, ym)
    if not in_domain:
        return None, None
    i1, i2 = i_idx, i_idx + 1
    j1, j2 = j_idx, j_idx + 1
    x_j1 = (j1 - 1) * DX
    x_j2 = (j2 - 1) * DX
    y_i1 = (i1 - 1) * DX
    y_i2 = (i2 - 1) * DX
    if abs(x_j2 - x_j1) < 1.0 or abs(y_i2 - y_i1) < 1.0:
        return None, None
    wx = max(0.0, min(1.0, (xm - x_j1) / (x_j2 - x_j1)))
    wy = max(0.0, min(1.0, (ym - y_i1) / (y_i2 - y_i1)))
    wx1, wy1 = 1.0 - wx, 1.0 - wy
    if corrected:
        lat = (wx1 * wy1 * fi[i1 - 1, j1 - 1] + wx * wy1 * fi[i1 - 1, j2 - 1] +
               wx1 * wy * fi[i2 - 1, j1 - 1] + wx * wy * fi[i2 - 1, j2 - 1])
        lon = (wx1 * wy1 * dl[i1 - 1, j1 - 1] + wx * wy1 * dl[i1 - 1, j2 - 1] +
               wx1 * wy * dl[i2 - 1, j1 - 1] + wx * wy * dl[i2 - 1, j2 - 1])
    else:
        # as-written formula (transposed cross terms)
        lat = (wx1 * wy1 * fi[i1 - 1, j1 - 1] + wx * wy1 * fi[i2 - 1, j1 - 1] +
               wx1 * wy * fi[i1 - 1, j2 - 1] + wx * wy * fi[i2 - 1, j2 - 1])
        lon = (wx1 * wy1 * dl[i1 - 1, j1 - 1] + wx * wy1 * dl[i2 - 1, j1 - 1] +
               wx1 * wy * dl[i1 - 1, j2 - 1] + wx * wy * dl[i2 - 1, j2 - 1])
    if lon > 180.0:
        lon -= 360.0
    if lon < -180.0:
        lon += 360.0
    return lat, lon


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance [m] (local-distance approximation for ~0.2 deg)."""
    r_earth = 6371.0e3
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = np.radians(np.asarray(lat2) - np.asarray(lat1))
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return 2.0 * r_earth * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_trajectory(path: Path) -> dict:
    """Load the space-delimited Fortran trajectory CSV (TEST_11 format)."""
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


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
def audit(t: dict, fi: np.ndarray, dl: np.ndarray) -> dict:
    """Run all checks; return structured results (deterministic)."""
    n = t["n"]
    res = {"row_count": n, "expected_rows": EXPECTED_ROWS}
    res["checks"] = {}

    # --- Time ---------------------------------------------------------------
    c = res["checks"]
    steps = t["step"]
    c["time_steps_monotonic"] = bool(np.all(np.diff(steps) == 1))
    c["time_duplicates"] = int(n - len(np.unique(steps)))
    c["time_interval_constant"] = bool(
        np.all(np.abs(np.diff(t["time_h"]) - DT_HOURS) < 1e-6))
    c["total_duration_h"] = float(t["time_h"][-1] - t["time_h"][0] + 1.0)
    c["time_rows_exact"] = bool(n == EXPECTED_ROWS)

    # --- Coordinates --------------------------------------------------------
    lat, lon = t["lat_deg"], t["lon_deg"]
    c["lat_finite"] = bool(np.all(np.isfinite(lat)))
    c["lon_finite"] = bool(np.all(np.isfinite(lon)))
    c["lat_in_domain"] = bool(np.all((lat >= LAT_DOMAIN[0]) & (lat <= LAT_DOMAIN[1])))
    c["lon_in_domain"] = bool(np.all((lon >= LON_DOMAIN[0]) & (lon <= LON_DOMAIN[1])))

    # Reproduction of the as-written formula from x/y
    lat_repro = np.full(n, np.nan)
    lon_repro = np.full(n, np.nan)
    lat_corr = np.full(n, np.nan)
    lon_corr = np.full(n, np.nan)
    cell_i = np.zeros(n, dtype=int)
    cell_j = np.zeros(n, dtype=int)
    for k in range(n):
        i_idx, j_idx, _ = model_coords_to_indices(t["x_m"][k], t["y_m"][k])
        cell_i[k], cell_j[k] = i_idx, j_idx
        la, lo = interp_latlon(t["x_m"][k], t["y_m"][k], fi, dl, corrected=False)
        if la is not None:
            lat_repro[k], lon_repro[k] = la, lo
        la, lo = interp_latlon(t["x_m"][k], t["y_m"][k], fi, dl, corrected=True)
        if la is not None:
            lat_corr[k], lon_corr[k] = la, lo

    res["repro_max_err_lat"] = float(np.nanmax(np.abs(lat_repro - lat)))
    res["repro_max_err_lon"] = float(np.nanmax(np.abs(lon_repro - lon)))
    c["csv_matches_aswritten_formula"] = bool(
        res["repro_max_err_lat"] < 1e-3 and res["repro_max_err_lon"] < 1e-3)
    # Post-fix contract (Stage 10.15.2): the CSV must match the corrected
    # (production) formula. The as-written (pre-fix, transposed) reproduction
    # must NOT match — it is the regression oracle for the old bug.
    res["repro_corr_max_err_lat"] = float(np.nanmax(np.abs(lat_corr - lat)))
    res["repro_corr_max_err_lon"] = float(np.nanmax(np.abs(lon_corr - lon)))
    c["csv_matches_corrected_formula"] = bool(
        res["repro_corr_max_err_lat"] < 1e-3 and res["repro_corr_max_err_lon"] < 1e-3)
    c["csv_does_not_match_transposed"] = bool(
        res["repro_max_err_lat"] > 1e-3 or res["repro_max_err_lon"] > 1e-3)

    # Coordinate jumps (consecutive rows)
    dlat = np.abs(np.diff(lat))
    dlon = np.abs(np.diff(lon))
    dlat_c = np.abs(np.diff(lat_corr))
    dlon_c = np.abs(np.diff(lon_corr))
    jump = (dlat > JUMP_DEG) | (dlon > JUMP_DEG)
    jump_idx = np.where(jump)[0] + 1  # step (1-based) of the second row
    res["coord_jumps"] = {
        "threshold_deg": JUMP_DEG,
        "count": int(jump.sum()),
        "steps": [int(t["step"][k]) for k in jump_idx - 1],
        "max_dlat_deg": float(dlat.max()),
        "max_dlon_deg": float(dlon.max()),
    }
    c["coord_no_jumps"] = bool(jump.sum() == 0)
    res["corrected_max_step_dlat_deg"] = float(dlat_c.max())
    res["corrected_max_step_dlon_deg"] = float(dlon_c.max())
    res["corrected_continuous"] = bool(
        dlat_c.max() < JUMP_DEG and dlon_c.max() < JUMP_DEG)

    # Cell-boundary crossings coincide with jumps?  (Every jump must occur
    # at a step where the model cell index changes — evidence that the
    # discontinuity comes from the interpolation stencil switching cells.)
    cell_change = np.diff(cell_i) != 0
    cell_change |= np.diff(cell_j) != 0
    res["jumps_at_cell_crossings"] = bool(
        jump.sum() == 0 or bool(np.all(~jump | cell_change)))

    # --- Kinematics ---------------------------------------------------------
    u, v = t["u_ms"], t["v_ms"]
    c["vel_finite"] = bool(np.all(np.isfinite(u)) and np.all(np.isfinite(v)))
    v_rep = np.hypot(u, v)
    c["speed_finite"] = bool(np.all(np.isfinite(v_rep)))
    res["speed_reported"] = {
        "max_ms": float(v_rep.max()),
        "min_ms": float(v_rep.min()),
        "plausible_band": SPEED_BAND,
        "plausible": bool(SPEED_BAND[0] <= v_rep.max() <= SPEED_BAND[1]),
    }

    dxm = np.diff(t["x_m"])
    dym = np.diff(t["y_m"])
    dt_s = np.diff(t["time_h"]) * 3600.0
    dist_xy = np.hypot(dxm, dym)
    v_impl_xy = dist_xy / dt_s
    res["speed_implied_from_xy"] = {
        "max_ms": float(v_impl_xy.max()),
        "max_displacement_m": float(dist_xy.max()),
    }
    c["implied_speed_from_xy_matches_reported"] = bool(
        np.abs(v_impl_xy - v_rep[:-1]).max() < SPEED_MISMATCH_MS)

    # Geographic implied speed using the CORRECTED coordinates (diagnostic)
    geo_dist = haversine_m(lat_corr[:-1], lon_corr[:-1], lat_corr[1:], lon_corr[1:])
    v_impl_geo = geo_dist / dt_s
    res["speed_implied_geographic_corrected"] = {
        "max_ms": float(np.nanmax(v_impl_geo)),
        "max_mismatch_vs_reported_ms": float(np.nanmax(np.abs(v_impl_geo - v_rep[:-1]))),
    }

    res["max_mismatch_implied_vs_reported_ms"] = float(
        np.abs(v_impl_xy - v_rep[:-1]).max())

    # Anomalous intervals (displacement threshold)
    anom = dist_xy > DISP_JUMP_M
    res["anomalous_intervals"] = {
        "threshold_m": DISP_JUMP_M,
        "count": int(anom.sum()),
        "steps": [int(t["step"][k]) for k in np.where(anom)[0]],
    }

    # --- Thermodynamics -----------------------------------------------------
    c["mass_finite"] = bool(np.all(np.isfinite(t["M_kg"])))
    c["geometry_positive"] = bool(
        np.all(t["L_m"] > 0) and np.all(t["W_m"] > 0) and np.all(t["H_m"] > 0))
    c["mass_monotone_non_increasing"] = bool(np.all(np.diff(t["M_kg"]) <= MASS_MONO_EPS))
    c["melt_finite"] = bool(
        np.all(np.isfinite(t["mb_mday"])) and np.all(np.isfinite(t["ml_mday"]))
        and np.all(np.isfinite(t["ms_mday"])))
    c["melt_non_negative"] = bool(
        np.all(t["mb_mday"] >= 0) and np.all(t["ml_mday"] >= 0)
        and np.all(t["ms_mday"] >= 0))
    res["melt_max_mday"] = {
        "basal": float(t["mb_mday"].max()),
        "lateral": float(t["ml_mday"].max()),
        "surface": float(t["ms_mday"].max()),
    }
    c["melt_bounded"] = bool(
        all(v < MELT_MAX_MDAY for v in res["melt_max_mday"].values()))
    c["timeseries_length_consistent"] = bool(
        len(t["M_kg"]) == len(t["L_m"]) == len(t["lat_deg"]) == n)

    # Per-step diagnostics table
    res["per_step"] = {
        "step": t["step"].astype(int).tolist(),
        "time_h": t["time_h"].tolist(),
        "x_m": t["x_m"].tolist(),
        "y_m": t["y_m"].tolist(),
        "cell_i": cell_i.tolist(),
        "cell_j": cell_j.tolist(),
        "lat_deg_csv": lat.tolist(),
        "lon_deg_csv": lon.tolist(),
        "lat_deg_repro_aswritten": lat_repro.tolist(),
        "lon_deg_repro_aswritten": lon_repro.tolist(),
        "lat_deg_corrected": lat_corr.tolist(),
        "lon_deg_corrected": lon_corr.tolist(),
        "dist_xy_m": np.concatenate([[0.0], dist_xy]).tolist(),
        "v_implied_xy_ms": np.concatenate([[0.0], v_impl_xy]).tolist(),
        "v_reported_ms": v_rep.tolist(),
        "jump_flag": np.concatenate([[False], jump]).tolist(),
    }
    return res


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def make_plots(t: dict, res: dict, out: Path) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # pragma: no cover
        return []
    saved = []
    h = t["time_h"] / 24.0
    lat, lon = t["lat_deg"], t["lon_deg"]
    lat_c = np.array(res["per_step"]["lat_deg_corrected"])
    lon_c = np.array(res["per_step"]["lon_deg_corrected"])
    jump_idx = np.array(res["coord_jumps"]["steps"], dtype=int) - 1  # 0-based rows (row before jump)
    n = t["n"]

    def save(fig, name):
        p = out / name
        fig.savefig(p, dpi=140, bbox_inches="tight")
        saved.append(str(p))
        plt.close(fig)

    # 1. Original plot reproduced exactly (same code as Stage 10.15 fig1)
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    sc = ax.scatter(lon, lat, c=h, cmap="viridis", s=12)
    ax.plot(lon, lat, "k-", lw=0.6, alpha=0.5)
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("10.15.1 fig1 — original reproduction (as Stage 10.15 fig1)")
    fig.colorbar(sc, ax=ax, label="time [day]")
    ax.grid(True, alpha=0.3)
    save(fig, "fig1_original_reproduction.png")

    # 2. Single continuous trajectory, chronological order, breaks at jumps
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    seg_start = 0
    for j in np.concatenate([jump_idx, [n - 1]]):
        seg_end = j
        if seg_end > seg_start:
            ax.plot(lon[seg_start:seg_end + 1], lat[seg_start:seg_end + 1],
                    "-", lw=0.9, color="#1f77b4")
        seg_start = j + 1
    ax.scatter(lon, lat, c=h, cmap="viridis", s=10)
    for j in jump_idx:
        ax.plot([lon[j], lon[j + 1]], [lat[j], lat[j + 1]], "r--", lw=1.2)
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("10.15.1 fig2 — chronological order, breaks (red) at jumps")
    ax.grid(True, alpha=0.3)
    save(fig, "fig2_chronological_breaks.png")

    # 3. Corrected (index-consistent) continuous trajectory
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.plot(lon_c, lat_c, "-", lw=1.0, color="#2ca02c")
    ax.scatter(lon_c, lat_c, c=h, cmap="viridis", s=10)
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("10.15.1 fig3 — corrected bilinear: continuous trajectory")
    ax.grid(True, alpha=0.3)
    save(fig, "fig3_corrected_continuous.png")

    # 4. Points only (no connecting line)
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.scatter(lon, lat, c=h, cmap="viridis", s=14)
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("10.15.1 fig4 — points only (no connectors)")
    ax.grid(True, alpha=0.3)
    save(fig, "fig4_points_only.png")

    # 5. Start / end markers
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.plot(lon, lat, "-", lw=0.6, alpha=0.4, color="gray")
    ax.plot(lon[0], lat[0], "g^", ms=14, label="start (step 1)")
    ax.plot(lon[-1], lat[-1], "rv", ms=14, label="end (step 720)")
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("10.15.1 fig5 — start/end markers")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig5_start_end_markers.png")

    # 6. Intervals where displacement exceeds threshold
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.plot(lon, lat, "-", lw=0.5, alpha=0.3, color="gray")
    anom_steps = np.array(res["anomalous_intervals"]["steps"]) - 1
    for j in anom_steps:
        ax.plot([lon[j], lon[j + 1]], [lat[j], lat[j + 1]], "r-", lw=2.5)
    ax.set_xlabel("Longitude [deg E]")
    ax.set_ylabel("Latitude [deg N]")
    ax.set_title("10.15.1 fig6 — intervals with displacement > "
                 f"{res['anomalous_intervals']['threshold_m']/1000:.0f} km")
    ax.grid(True, alpha=0.3)
    save(fig, "fig6_anomaly_segments.png")

    # 7. Implied coordinate speed vs reported model speed
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    per = res["per_step"]
    ax.plot(h, per["v_implied_xy_ms"], "-", lw=0.9, label="implied from x/y")
    ax.plot(h, per["v_reported_ms"], "--", lw=0.9, label="reported u/v")
    ax.set_xlabel("time [day]")
    ax.set_ylabel("speed [m/s]")
    ax.set_title("10.15.1 fig7 — implied vs reported speed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save(fig, "fig7_implied_vs_reported_speed.png")

    # 8. Time-step length vs time
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    dt_h = np.diff(t["time_h"])
    ax.plot(h[1:], dt_h, "o-", ms=2.5, lw=0.8)
    ax.set_xlabel("time [day]")
    ax.set_ylabel("dt [h]")
    ax.set_ylim(0, 2.0)
    ax.set_title("10.15.1 fig8 — time-step length vs time")
    ax.grid(True, alpha=0.3)
    save(fig, "fig8_timestep_length.png")

    # 9. CSV lat/lon vs corrected lat/lon (cause demonstration)
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0))
    axes[0].plot(h, lat, "-", lw=0.8, label="CSV (as-written formula)")
    axes[0].plot(h, lat_c, "--", lw=0.8, label="corrected formula")
    axes[0].set_xlabel("time [day]")
    axes[0].set_ylabel("latitude [deg N]")
    axes[0].set_title("10.15.1 fig9a — latitude: CSV vs corrected")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(h, lon, "-", lw=0.8, label="CSV (as-written formula)")
    axes[1].plot(h, lon_c, "--", lw=0.8, label="corrected formula")
    axes[1].set_xlabel("time [day]")
    axes[1].set_ylabel("longitude [deg E]")
    axes[1].set_title("10.15.1 fig9b — longitude: CSV vs corrected")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    save(fig, "fig9_csv_vs_corrected_latlon.png")

    return saved


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def write_audit_csv(res: dict, out: Path) -> Path:
    per = res["per_step"]
    path = out / "audit_per_step.csv"
    cols = ["step", "time_h", "x_m", "y_m", "cell_i", "cell_j",
            "lat_deg_csv", "lon_deg_csv", "lat_deg_repro_aswritten",
            "lon_deg_repro_aswritten", "lat_deg_corrected", "lon_deg_corrected",
            "dist_xy_m", "v_implied_xy_ms", "v_reported_ms", "jump_flag"]
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for k in range(len(per["step"])):
            w.writerow([per[c][k] for c in cols])
    return path


def write_corrected_csv(t: dict, res: dict, out: Path) -> Path:
    """Derived trajectory: model coordinates + corrected geographic position.

    This is a DIAGNOSTIC reconstruction of what the reverse projection would
    report with index-consistent bilinear weights — NOT a new model run.
    """
    per = res["per_step"]
    path = out / "corrected_trajectory.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["step", "time_h", "x_m", "y_m",
                    "lat_deg_corrected", "lon_deg_corrected",
                    "lat_deg_csv_original", "lon_deg_csv_original"])
        for k in range(len(per["step"])):
            w.writerow([per["step"][k], per["time_h"][k], per["x_m"][k],
                        per["y_m"][k], per["lat_deg_corrected"][k],
                        per["lon_deg_corrected"][k],
                        per["lat_deg_csv"][k], per["lon_deg_csv"][k]])
    return path


# ---------------------------------------------------------------------------
def main() -> int:
    src = SRC_CSV if SRC_CSV.exists() else RAW_CSV
    if not src.exists():
        print(f"ERROR: trajectory CSV not found: {src}")
        return 1
    if not KOORD.exists():
        print(f"ERROR: KOORD.DAT not found: {KOORD}")
        return 1

    t = load_trajectory(src)
    fi, dl = load_grid(KOORD)
    res = audit(t, fi, dl)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    figs = make_plots(t, res, PLOT_DIR)
    audit_csv = write_audit_csv(res, OUT_DIR)
    corrected_csv = write_corrected_csv(t, res, OUT_DIR)

    c = res["checks"]
    summary = {
        "stage": "10.15.1/10.15.2",
        "classification": (
            "coordinate mapping and bilinear interpolation fix verified — "
            "CSV matches the corrected (production) formula; geographic "
            "trajectory continuous; transposed pre-fix formula no longer "
            "matches (Stage 10.15.2)") if res["checks"]["csv_matches_corrected_formula"] else
            ("pre-fix state detected: CSV matches the transposed (as-written) "
             "formula — trajectory contains real coordinate discontinuities "
             "(Stage 10.15.1 findings)"),
        "source_csv": str(src.relative_to(REPO)),
        "koord_dat": str(KOORD.relative_to(REPO)),
        "n_rows": res["row_count"],
        "time": {
            "monotonic": c["time_steps_monotonic"],
            "duplicates": c["time_duplicates"],
            "constant_dt": c["time_interval_constant"],
            "total_duration_h": res["checks"]["total_duration_h"],
        },
        "coordinates": {
            "csv_matches_aswritten_formula": c["csv_matches_aswritten_formula"],
            "csv_matches_corrected_formula": c["csv_matches_corrected_formula"],
            "csv_does_not_match_transposed": c["csv_does_not_match_transposed"],
            "coord_jumps": res["coord_jumps"],
            "jumps_at_cell_crossings": res["jumps_at_cell_crossings"],
            "corrected_continuous": res["corrected_continuous"],
            "corrected_max_step_dlat_deg": res["corrected_max_step_dlat_deg"],
            "corrected_max_step_dlon_deg": res["corrected_max_step_dlon_deg"],
        },
        "kinematics": {
            "max_reported_speed_ms": res["speed_reported"]["max_ms"],
            "max_implied_speed_from_xy_ms": res["speed_implied_from_xy"]["max_ms"],
            "max_displacement_m": res["speed_implied_from_xy"]["max_displacement_m"],
            "max_mismatch_implied_vs_reported_ms": res["max_mismatch_implied_vs_reported_ms"],
            "geographic_implied_speed_corrected_max_ms": res["speed_implied_geographic_corrected"]["max_ms"],
            "geographic_implied_vs_reported_max_mismatch_ms": res["speed_implied_geographic_corrected"]["max_mismatch_vs_reported_ms"],
            "anomalous_intervals": res["anomalous_intervals"],
        },
        "thermodynamics": {
            "mass_finite": c["mass_finite"],
            "geometry_positive": c["geometry_positive"],
            "mass_monotone_non_increasing": c["mass_monotone_non_increasing"],
            "melt_finite": c["melt_finite"],
            "melt_non_negative": c["melt_non_negative"],
            "melt_max_mday": res["melt_max_mday"],
            "melt_bounded": c["melt_bounded"],
        },
        "figures": [str(Path(f).relative_to(REPO)) for f in figs],
        "audit_csv": str(audit_csv.relative_to(REPO)),
        "corrected_trajectory_csv": str(corrected_csv.relative_to(REPO)),
    }
    with (OUT_DIR / "audit_summary.json").open("w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    # Console report
    print("=" * 72)
    print("STAGE 10.15.1 — TRAJECTORY CONTINUITY AND OUTPUT INTEGRITY AUDIT")
    print("=" * 72)
    print(f"source: {src.relative_to(REPO)}  ({res['row_count']} rows)")
    print("\n-- time --")
    for k in ("time_rows_exact", "time_steps_monotonic", "time_duplicates",
              "time_interval_constant"):
        print(f"  {k:>24}: {c[k]}")
    print(f"  total duration: {c['total_duration_h']:.0f} h "
          f"({c['total_duration_h']/24:.1f} d)")
    print("\n-- coordinates --")
    print(f"  csv matches corrected (production) formula: {c['csv_matches_corrected_formula']}"
          f" (max err {res['repro_corr_max_err_lat']:.2e} deg lat)")
    print(f"  csv matches transposed (pre-fix) formula: {c['csv_matches_aswritten_formula']}"
          f" (max err {res['repro_max_err_lat']:.2e} deg lat)")
    j = res["coord_jumps"]
    print(f"  coordinate jumps > {j['threshold_deg']} deg: {j['count']} "
          f"(max dlat {j['max_dlat_deg']:.4f}, max dlon {j['max_dlon_deg']:.4f})")
    print(f"  jump steps: {j['steps']}")
    print(f"  corrected formula continuous: {res['corrected_continuous']} "
          f"(max step {res['corrected_max_step_dlat_deg']:.5f} deg lat / "
          f"{res['corrected_max_step_dlon_deg']:.5f} deg lon)")
    print("\n-- kinematics --")
    print(f"  max reported speed: {res['speed_reported']['max_ms']:.4f} m/s")
    print(f"  max implied speed (x/y): {res['speed_implied_from_xy']['max_ms']:.4f} m/s")
    print(f"  max |implied - reported|: {res['max_mismatch_implied_vs_reported_ms']:.4f} m/s")
    print(f"  max geographic implied (corrected): "
          f"{res['speed_implied_geographic_corrected']['max_ms']:.4f} m/s")
    print(f"  anomalous intervals (> {res['anomalous_intervals']['threshold_m']/1000:.0f} km/step): "
          f"{res['anomalous_intervals']['count']}")
    print("\n-- thermodynamics --")
    for k in ("mass_finite", "geometry_positive", "mass_monotone_non_increasing",
              "melt_finite", "melt_non_negative", "melt_bounded"):
        print(f"  {k:>30}: {c[k]}")
    print(f"  melt max [m/day]: {res['melt_max_mday']}")
    print("\n-- classification --")
    print(summary["classification"])
    print(f"\noutputs -> {OUT_DIR.relative_to(REPO)}/")
    print(f"  figures: {len(figs)}")
    print(f"  audit CSV: {audit_csv.name}")
    print(f"  corrected trajectory CSV: {corrected_csv.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())