#!/usr/bin/env python3
"""
Stage 10.22 — A5: independent Python replay of Block-200 (baroclinic pressure
gradient + semi-implicit Coriolis) and the ``s22_block200_budget`` metrics.

The Fortran model computes, each step, the B200 momentum update (app/main.f90
lines ~935-1035) and, with Stage 10.22 diagnostics enabled, appends one CSV
row per (day, step) with 19 budget/gradient/laplacian metrics
(src/stage1022_diagnostics.f90 ``s22_block200_budget``, lines ~207-360).

This module re-derives those numbers entirely offline from:

  * the model output NetCDF (density_anomaly, u_velocity, v_velocity, dp_x,
    dp_y, latitude, depth, water_column_levels),
  * the real-grid bathymetry file ``hhh.bar``,
  * the fixed model constants (dt, dx, ah, g, roc, 2*7.29e-5).

Bathymetry pipeline (mirrors src/grid_coupling.f90 ``coup1()`` exactly):

  read hhh.bar (7 blocks x 133 lines x 15I5) -> kt1(i,j)
  ht = real(kt1)
  boundary ht = 8888 (rows 1..15 col 94, col 105, col 1, row 1)
  land (kt1 == 8) -> ht = 8888
  depth clamps (wet only): 5 < ht <= 10 -> 10 ; ht <= 3 -> 3 ; ht *= 100 (cm)
  hu/hv cell-edge depths from clamped ht (both neighbours wet)
  kt1 boundary -> 8 ; kt1 wet/land mask
  ht smoothing: wet T-points -> mean of valid hu/hv neighbours
  kk1 4-corner wet flag (first pass)
  map1 = 0.25 * sum of the 4 smoothed corner depths (wet cells only)
  final kt1 = water-column level count (second pass, from smoothed ht)
  kk1 = min-4 of final kt1 (second pass)

The reconstructed water_column_levels must match the NetCDF field cell-for-cell
(100 %, hard gate) before any replay is attempted.

Then the replay applies the B200 stencil (u2/v2) and the exact budget metric
semantics: level-0 a/b seeded from level-1 corners with dzz=dz(1); coincidence
levels (|hht - z(k)| < 1e-6) skipped *before* any read; per-level trapezoid
cc_val = c8*dzz with the dzz/a/b carry-over; max_u1/v1/u2/v2 from |.| maxima
at processed levels only; slap evaluated at k=1 only; ro_min/max/mean over the
center cell ro at processed levels (float64 accumulation, float32 output as in
the Fortran real(...) casts); per-run flags: freeze_tw (A2, two-path: the
budget sums stay fully accumulated while the B200 *momentum* sum/sum1 are
zeroed at every level before auu/avv -- affects only max_u2/max_v2/amp) and
use_ref (A4, budget + B200 read the frozen initial ro instead of the live
field).

ERA5 dp_x/dp_y are temporally interpolated toward the next day's field
(main.f90: the day-start field is raw, each of the 12 daily steps advances
11/12 of the increment). The end-of-day NetCDF snapshot therefore stores
snap_{d-1} = raw_{d-1} + (11/12)*(raw_d - raw_{d-1}), while B200 at step 1 of
day d reads the *raw* day-d field. The replay reconstructs the raw chain
(raw_1 = day_00 snapshot, raw_d = raw_{d-1} + (12/11)*(snap_{d-1} - raw_{d-1}))
by default; pass --no-reconstruct-forcing for runs without ERA5 temporal
interpolation (e.g. ICEBERG_FROZEN_WIND=true, snap == raw).

Exactness: days with 0 metric failures are reproduced to rtol (default 1e-4)
for a1/a3/a4 across the full 30-day trajectory. Runs without frozen ro
(a0/a2) show a fixed ro-phase artifact: the snapshot ro predates the
pre-B200 evolution (heat/convective adjustment), so ro-derived metrics
(ro_*, sum_max, acc_bar, dp_ratio, and for a0 max_u2/v2/amp) fail at
ro-phase magnitude; this is a snapshot limitation, not a replay error.

Usage:
    conda run -n iceberg-thermodynamic-model python python/validation/block200_isolate.py \
        --run a0 --day 1 --step 1
    conda run -n iceberg-thermodynamic-model python python/validation/block200_isolate.py \
        --run a2 --all-days --rtol 1e-4
    conda run -n iceberg-thermodynamic-model python python/validation/block200_isolate.py \
        --run a4 --all-days --float32
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import netCDF4 as nc
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]

# Grid dimensions (src/param.f90).
IS1, JS1, KS = 133, 105, 18
IS, JS = IS1 - 1, JS1 - 1
N_BLOCKS_HHH = 7
COLS_PER_BLOCK = 15

# Model constants (app/main.f90 + src/grid_coupling.f90).
DT = 3600.0          # s
DX = 1389000.0       # cm
AH = 7.5e6           # cm^2/s
G = 981.0            # cm/s^2
ROC = 1.0            # g/cm^3 reference density
C1 = G / ROC
C3 = AH / (DX * DX)       # 7.5e6 / (1389000**2) ~ 3.8873e-6
C8 = 0.25 / DX            # ~ 1.7999e-7
OMEGA = 2.0 * 7.29e-5     # 1.458e-4 1/s
TINY1 = 1.0e-30           # ratio guards in the budget

# Land sentinel and tolerances (AGENTS.md: never == on reals).
LAND = 8888.0
EPS_HT = 1e-8             # |x - 8888| < EPS_HT -> land
EPS_Z = 1e-6              # |hht - z(k)| < EPS_Z -> coincidence (skip level)

METRIC_NAMES = [
    "ro_min", "ro_max", "ro_mean",
    "sum_max", "sum1_max",
    "acc_bar_u", "acc_bar_v", "acc_dp_u", "acc_dp_v",
    "acc_lap_u", "acc_lap_v",
    "dp_ratio_u", "dp_ratio_v",
    "max_u1", "max_v1", "max_u2", "max_v2",
    "amp_u", "amp_v",
]
N_METRICS = len(METRIC_NAMES)

RUN_DIRS = {
    "a0": "stage10.22_p30d_a0_diag",
    "a1": "stage10.22_p30d_a1_freeze_ro",
    "a2": "stage10.22_p30d_a2_no_tw",
    "a3": "stage10.22_p30d_a3_freeze_ts",
    "a4": "stage10.22_p30d_a4_frozen_ro",
}
RUN_FLAGS = {
    "a0": dict(freeze_tw=False, use_ref=False),
    "a1": dict(freeze_tw=False, use_ref=False),
    "a2": dict(freeze_tw=True,  use_ref=False),
    "a3": dict(freeze_tw=False, use_ref=False),
    "a4": dict(freeze_tw=False, use_ref=True),
}


# ----------------------------------------------------------------------
# Bathymetry and coup1() reconstruction
# ----------------------------------------------------------------------

def read_hhh_bar(path: Path) -> np.ndarray:
    """Read hhh.bar: N_BLOCKS_HHH blocks, each a header record then IS1 lines
    of 15I5. Line L (block = L//IS1, row = L%IS1) fills kt1(row, block*15..)."""
    kt1 = np.zeros((IS1, JS1), dtype=np.int32)
    with open(path) as fh:
        for block in range(N_BLOCKS_HHH):
            fh.readline()  # header record (free-format read in Fortran)
            for i in range(IS1):
                line = fh.readline()
                if not line:
                    raise ValueError(f"hhh.bar truncated at block {block + 1}, row {i + 1}")
                vals = [int(line[p * 5:p * 5 + 5]) for p in range(COLS_PER_BLOCK)]
                kt1[i, block * COLS_PER_BLOCK:(block + 1) * COLS_PER_BLOCK] = vals
    return kt1


def coup1(kt1_raw: np.ndarray, z: np.ndarray, dtype=np.float64) -> dict:
    """Replay of grid_coupling.f90 coup1() up to the kk1/map1/wcl fields.

    Returns dict with keys: ht (smoothed, cm), hu, hv, map1, wcl (int),
    kk1 (int), wet (bool land mask used by smooth/kk1).
    """
    kt1 = kt1_raw.copy()
    ht = kt1.astype(dtype)

    # Boundary ht = 8888 (Fortran rows/cols 1-based).
    ht[:15, 93] = LAND      # ht(1:15, 94)
    ht[:, 104] = LAND       # ht(:, js1)
    ht[:, 0] = LAND         # ht(:, 1)
    ht[0, :] = LAND         # ht(1, :)

    # Land: kt1 == 8 -> ht = 8888.
    land = kt1 == 8
    wet = ~land
    ht[land] = LAND

    # Depth clamps (wet cells only; guard on ht==8888, not kt1, because the
    # boundary ht was already forced to 8888 before this point).
    wet_ht = np.abs(ht - LAND) > EPS_HT
    m1 = wet_ht & (ht > 5.0) & (ht <= 10.0)
    m2 = wet_ht & (ht <= 3.0)
    ht = np.where(m1, 10.0, ht)
    ht = np.where(m2, 3.0, ht)
    ht = np.where(wet_ht, ht * 100.0, ht)

    # hu/hv cell-edge depths from the clamped ht (hu along j/X, hv along i/Y).
    hu = np.full_like(ht, LAND)
    hv = np.full_like(ht, LAND)
    jpair = (np.abs(ht[:, 0:104] - LAND) > EPS_HT) & (np.abs(ht[:, 1:105] - LAND) > EPS_HT)
    hu[:, 1:105] = np.where(jpair, 0.5 * (ht[:, 0:104] + ht[:, 1:105]), LAND)
    ipair = (np.abs(ht[0:132, :] - LAND) > EPS_HT) & (np.abs(ht[1:133, :] - LAND) > EPS_HT)
    hv[1:133, :] = np.where(ipair, 0.5 * (ht[0:132, :] + ht[1:133, :]), LAND)
    hu[:, 0] = LAND
    hu[:, 104] = LAND
    hv[0, :] = LAND
    hv[132, :] = LAND

    # kt1 boundary -> 8 (affects the kk1 4-corner wet flag; the smoothing loop
    # and the final kt1 pass never touch the outermost rows/cols anyway).
    kt1[:, 0] = 8
    kt1[:, 104] = 8
    kt1[0, :] = 8
    kt1[132, :] = 8

    # ht smoothing: wet T-points (i=1..is, j=1..js) -> mean of the valid
    # hu(i,j), hu(i,j+1), hv(i,j), hv(i+1,j); unchanged if no valid neighbour.
    cand = np.stack([
        hu[0:IS, 0:JS], hu[0:IS, 1:JS1],
        hv[0:IS, 0:JS], hv[1:IS1, 0:JS],
    ])
    valid = np.abs(cand - LAND) > EPS_HT
    cnt = valid.sum(axis=0)
    smooth_ok = (kt1[0:IS, 0:JS] != 8) & (cnt > 0)
    ht_sm = np.where(cnt > 0, np.where(valid, cand, 0.0).sum(axis=0) / np.maximum(cnt, 1),
                     ht[0:IS, 0:JS])
    ht = ht.copy()
    ht[0:IS, 0:JS] = np.where(smooth_ok, ht_sm, ht[0:IS, 0:JS])

    # kk1 first pass: 1 where the 4 corners are wet.
    kk1 = np.zeros((IS1, JS1), dtype=np.int32)
    c_wet = (kt1[1:IS1, 1:JS1] != 8) & (kt1[0:IS, 1:JS1] != 8) \
          & (kt1[1:IS1, 0:JS] != 8) & (kt1[0:IS, 0:JS] != 8)
    kk1[1:IS1, 1:JS1] = c_wet.astype(np.int32)

    # map1 = 0.25 * sum of the valid smoothed corner depths (kk1 cells only).
    map1 = np.full((IS1, JS1), LAND, dtype=dtype)
    corners = np.stack([
        ht[1:IS1, 1:JS1], ht[1:IS1, 0:JS], ht[0:IS, 1:JS1], ht[0:IS, 0:JS],
    ])
    corners_ok = np.abs(corners - LAND) > EPS_HT
    mapp = 0.25 * np.where(corners_ok, corners, 0.0).sum(axis=0)
    any_ok = corners_ok.any(axis=0) & (c_wet != 0)
    map1[1:IS1, 1:JS1] = np.where(any_ok, mapp, LAND)

    # Final kt1 = water-column level count from the smoothed ht.
    wet_sm = np.abs(ht - LAND) > EPS_HT
    wcl = np.sum(z[None, None, :] <= ht[..., None], axis=-1)
    wcl = np.where(wet_sm, wcl, 0).astype(np.int32)

    # kk1 second pass: min-4 of the final kt1 over the corners; edges -> 0.
    kk1 = np.zeros((IS1, JS1), dtype=np.int32)
    wcl_c = np.stack([
        wcl[1:IS1, 1:JS1], wcl[0:IS, 1:JS1], wcl[0:IS, 0:JS], wcl[1:IS1, 0:JS],
    ])
    kk1[1:IS1, 1:JS1] = np.where(c_wet, wcl_c.min(axis=0), 0)

    return dict(ht=ht, hu=hu, hv=hv, map1=map1, wcl=wcl, kk1=kk1, wet=wet)


# ----------------------------------------------------------------------
# NetCDF state loading (boundary conversions from netcdf_output.f90)
# ----------------------------------------------------------------------

def _conv3(var, scale, dtype):
    a = np.asarray(var[:], dtype=np.float64) * scale
    return a.transpose(2, 1, 0).astype(dtype)


def _conv2(var, scale, dtype):
    a = np.asarray(var[:], dtype=np.float64) * scale
    return a.T.astype(dtype)


def load_nc_state(path: Path, dtype=np.float64) -> dict:
    """Load one results_day_NN.nc into internal units:
    ro = density_anomaly*1e-3 (anomaly rho-1.02, g/cm^3, no +1.02);
    u/v = u_velocity*100 (cm/s); dpx/dpy = dp_x/y*10; z = depth*100 (cm)."""
    ds = nc.Dataset(path)
    try:
        state = dict(
            ro=_conv3(ds.variables["density_anomaly"], 1e-3, dtype),
            u1=_conv3(ds.variables["u_velocity"], 100.0, dtype),
            v1=_conv3(ds.variables["v_velocity"], 100.0, dtype),
            dpx=_conv2(ds.variables["dp_x"], 10.0, dtype),
            dpy=_conv2(ds.variables["dp_y"], 10.0, dtype),
            lat_deg=_conv2(ds.variables["latitude"], 1.0, dtype),
            z=np.asarray(ds.variables["depth"][:], dtype=np.float64) * 100.0,
            wcl_nc=_conv2(ds.variables["water_column_levels"], 1.0, np.int32),
        )
    finally:
        ds.close()
    return state


# ----------------------------------------------------------------------
# B200 stencil + budget metrics replay
# ----------------------------------------------------------------------

def replay_block200(state: dict, grid: dict, freeze_tw: bool = False,
                    dtype=np.float64) -> dict:
    """Replay s22_block200_budget + the B200 u2/v2 update for one state.

    state: dict from load_nc_state (or with ro swapped for use_ref runs).
    grid:  dict from coup1 (ht/map1/wcl/kk1).
    Returns all 19 metrics in CSV order plus u2/v2 diagnostic maxima.
    """
    z = state["z"].astype(dtype)
    dz = np.empty(KS, dtype=dtype)
    dz[0] = z[0]
    dz[1:] = np.diff(z)

    fku = (OMEGA * np.sin(state["lat_deg"] / 57.3)).astype(dtype)

    ro = state["ro"]
    u1, v1 = state["u1"], state["v1"]
    dpx, dpy = state["dpx"], state["dpy"]
    map1 = grid["map1"]
    kk1 = grid["kk1"]

    # Interior cells: Fortran i=2..is, j=2..js  ->  python (131, 103) window.
    # Center (i,j)      : [1:132, 1:104]
    # Neighbour i2/i-1  : [0:131, ...];  i1/i+1: [2:133, ...]
    # Neighbour j2/j-1  : [..., 0:103];  j1/j+1: [..., 2:105]
    ki = kk1[1:IS, 1:JS].astype(np.int32)              # (is-1, js-1)
    hht = map1[1:IS, 1:JS]
    active0 = (ki > 0) & (np.abs(hht - LAND) > EPS_HT)   # cells B200 processes

    asa1 = fku[1:IS, 1:JS] * 0.5 * DT
    asa = asa1 * asa1 + 1.0

    # Level-0 seed: corners at k=1, dzz = dz(1).
    ri2j = ro[0:131, 1:104, 0]
    rij = ro[1:132, 1:104, 0]
    ri2j2 = ro[0:131, 0:103, 0]
    rij2 = ro[1:132, 0:103, 0]
    a = ri2j + rij - ri2j2 - rij2
    b = ri2j2 + ri2j - rij2 - rij
    dzz = np.full((131, 103), dz[0], dtype=dtype)

    # Budget baroclinic sums (s22_block200_budget): full accumulation, the
    # Fortran subroutine maintains its own sum_x/sum_y and never zeroes them.
    sum_x = np.zeros((131, 103), dtype=dtype)
    sum_y = np.zeros((131, 103), dtype=dtype)
    # B200 momentum sums: same per-level accumulation, but Stage 10.22 A2
    # (freeze_tw) zeroes them at every level *before* auu/avv (main.f90
    # lines 1004-1021). Budget metrics are unaffected by the zeroing.
    sum_x_b = np.zeros((131, 103), dtype=dtype)
    sum_y_b = np.zeros((131, 103), dtype=dtype)

    neg_inf = np.full((131, 103), -np.inf, dtype=dtype)
    pos_inf = np.full((131, 103), np.inf, dtype=dtype)
    max_u1 = neg_inf.copy()
    max_v1 = neg_inf.copy()
    max_u2 = neg_inf.copy()
    max_v2 = neg_inf.copy()
    max_slap_u = neg_inf.copy()
    max_slap_v = neg_inf.copy()

    ro_min = pos_inf.copy()
    ro_max = neg_inf.copy()
    ro_sum = np.float64(0.0)
    ro_n = 0

    for kk in range(KS):
        coinc = np.abs(hht - z[kk]) < EPS_Z
        active_k = active0 & (ki > kk) & (~coinc)

        ric = ro[0:131, 1:104, kk]      # ri2j (i-1, j)
        rjc = ro[1:132, 0:103, kk]      # rij2 (i, j-1)
        rc = ro[1:132, 1:104, kk]       # rij  (i, j)
        rcc = ro[0:131, 0:103, kk]      # ri2j2 (i-1, j-1)
        a1 = ric + rc - rcc - rjc
        b1 = rcc + ric - rjc - rc

        cc = C8 * dzz
        add_x = (a + a1) * cc
        add_y = (b + b1) * cc
        # Budget path: full accumulation (s22_block200_budget never zeroes).
        sum_x = np.where(active_k, sum_x + add_x, sum_x)
        sum_y = np.where(active_k, sum_y + add_y, sum_y)
        # B200 momentum path: same accumulation, then Stage 10.22 A2
        # (freeze_tw) zeroes at every level -- thermal-wind term off for the
        # momentum only (main.f90: sums accumulate, then are zeroed, then
        # auu/avv read them).
        sum_x_b = np.where(active_k, sum_x_b + add_x, sum_x_b)
        sum_y_b = np.where(active_k, sum_y_b + add_y, sum_y_b)
        if freeze_tw:
            sum_x_b = np.where(active_k, 0.0, sum_x_b)
            sum_y_b = np.where(active_k, 0.0, sum_y_b)

        # B200 momentum: reads sum AFTER this level's contribution (and the
        # A2 zeroing) exactly as main.f90 does; coincident levels are skipped
        # so U2=V2=0 there (max_u2/v2 recorded only at processed levels).
        uij = u1[1:132, 1:104, kk]
        vij = v1[1:132, 1:104, kk]
        slapu = (u1[1:132, 0:103, kk] + u1[1:132, 2:105, kk]
                 + u1[0:131, 1:104, kk] + u1[2:133, 1:104, kk] - 4.0 * uij)
        slapv = (v1[2:133, 1:104, kk] + v1[0:131, 1:104, kk]
                 + v1[1:132, 2:105, kk] + v1[1:132, 0:103, kk] - 4.0 * vij)

        dpx_c = dpx[1:132, 1:104]
        dpy_c = dpy[1:132, 1:104]
        auu = uij + asa1 * vij + DT * (-C1 * sum_x_b - dpx_c + C3 * slapu)
        avv = vij - asa1 * uij + DT * (-C1 * sum_y_b - dpy_c + C3 * slapv)
        u2k = (auu + avv * asa1) / asa
        v2k = (avv - auu * asa1) / asa

        max_u1 = np.maximum(max_u1, np.where(active_k, np.abs(uij), neg_inf))
        max_v1 = np.maximum(max_v1, np.where(active_k, np.abs(vij), neg_inf))
        max_u2 = np.maximum(max_u2, np.where(active_k, np.abs(u2k), neg_inf))
        max_v2 = np.maximum(max_v2, np.where(active_k, np.abs(v2k), neg_inf))
        if kk == 0:   # Fortran: k == 1 (surface level only)
            max_slap_u = np.maximum(max_slap_u, np.where(active_k, np.abs(slapu), neg_inf))
            max_slap_v = np.maximum(max_slap_v, np.where(active_k, np.abs(slapv), neg_inf))

        # ro stats at the center cell ro(i,j,k), processed levels only.
        ro_min = np.minimum(ro_min, np.where(active_k, rc, pos_inf))
        ro_max = np.maximum(ro_max, np.where(active_k, rc, neg_inf))
        ro_sum += np.sum(np.where(active_k, rc, 0.0))
        ro_n += int(np.count_nonzero(active_k))

        # Carry-over: a/b/dzz advance only at processed levels. For kk = ks-1
        # the Fortran reads dz(k+1)=dz(19) (OOB); such a level is always
        # coincident (hht >= z(ks) = 60000 cm with hht = map1 <= 60000 ->
        # hht == z(ks)), so the cell is inactive here and dz(19) is never used.
        nxt = dz[kk + 1] if kk + 1 < KS else dzz
        dzz = np.where(active_k, nxt, dzz)
        a = np.where(active_k, a1, a)
        b = np.where(active_k, b1, b)

    max_sum = np.max(np.where(active0, np.abs(sum_x), neg_inf))
    max_sum1 = np.max(np.where(active0, np.abs(sum_y), neg_inf))
    max_dp_u = np.max(np.where(active0, np.abs(dpx[1:132, 1:104]), neg_inf))
    max_dp_v = np.max(np.where(active0, np.abs(dpy[1:132, 1:104]), neg_inf))
    max_slap_u = np.max(max_slap_u)
    max_slap_v = np.max(max_slap_v)
    max_u1 = np.max(max_u1)
    max_v1 = np.max(max_v1)
    max_u2 = np.max(max_u2)
    max_v2 = np.max(max_v2)
    ro_min = np.min(ro_min)
    ro_max = np.max(ro_max)
    ro_mean = float(ro_sum / ro_n) if ro_n > 0 else 0.0

    acc_bar_u = DT * C1 * max_sum
    acc_bar_v = DT * C1 * max_sum1
    acc_dp_u = DT * max_dp_u
    acc_dp_v = DT * max_dp_v
    acc_lap_u = DT * C3 * max_slap_u
    acc_lap_v = DT * C3 * max_slap_v
    dp_ratio_u = acc_bar_u / max(acc_dp_u, TINY1)
    dp_ratio_v = acc_bar_v / max(acc_dp_v, TINY1)
    amp_u = max_u2 / max(max_u1, TINY1)
    amp_v = max_v2 / max(max_v1, TINY1)

    # The Fortran writes ro_min/ro_max/ro_mean through real(...) (float32).
    metrics = [
        np.float32(ro_min), np.float32(ro_max), np.float32(ro_mean),
        np.float32(max_sum), np.float32(max_sum1),
        np.float32(acc_bar_u), np.float32(acc_bar_v),
        np.float32(acc_dp_u), np.float32(acc_dp_v),
        np.float32(acc_lap_u), np.float32(acc_lap_v),
        np.float32(dp_ratio_u), np.float32(dp_ratio_v),
        np.float32(max_u1), np.float32(max_v1),
        np.float32(max_u2), np.float32(max_v2),
        np.float32(amp_u), np.float32(amp_v),
    ]
    return dict(
        metrics=metrics,
        names=METRIC_NAMES,
        _internal=dict(
            max_sum=float(max_sum), max_sum1=float(max_sum1),
            max_dp_u=float(max_dp_u), max_dp_v=float(max_dp_v),
            max_slap_u=float(max_slap_u), max_slap_v=float(max_slap_v),
            max_u1=float(max_u1), max_v1=float(max_v1),
            max_u2=float(max_u2), max_v2=float(max_v2),
            acc_bar_u=float(acc_bar_u), acc_bar_v=float(acc_bar_v),
            ro_min=float(ro_min), ro_max=float(ro_max), ro_mean=float(ro_mean),
            ro_n=ro_n,
        ),
    )


# ----------------------------------------------------------------------
# CSV comparison
# ----------------------------------------------------------------------

def read_block200_csv(path: Path) -> tuple:
    """Return (header, rows); header[0:2] == day,step, header[2:] metrics."""
    lines = [ln.strip() for ln in open(path) if ln.strip()]
    header = [h.strip() for h in lines[0].split(",")]
    rows = []
    for ln in lines[1:]:
        parts = [p.strip() for p in ln.split(",")]
        day, step = int(parts[0]), int(parts[1])
        vals = [np.nan if p == "NaN" else float(p) for p in parts[2:]]
        rows.append((day, step, vals))
    return header, rows


def compare_metrics(replay: dict, csv_vals: list, rtol: float) -> list:
    """Per-metric comparison. CSV NaN <-> skip (not a failure)."""
    out = []
    for name, rv, cv in zip(replay["names"], replay["metrics"], csv_vals):
        if np.isnan(cv):
            out.append((name, cv, float(rv), np.nan, None))
            continue
        rel = abs(float(rv) - cv) / max(abs(cv), TINY1)
        out.append((name, cv, float(rv), rel, rel <= rtol))
    return out


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def resolve_paths(run, nc_path, csv_path, day):
    data = REPO_ROOT / "data" / "runs" / RUN_DIRS[run]
    if nc_path is None:
        nc_path = data / "output" / "nc" / f"results_day_{day - 1:02d}.nc"
    if csv_path is None:
        csv_path = data / "output" / "csv" / "stage1022_block200.csv"
    return Path(nc_path), Path(csv_path)


def reconstruct_raw_forcing(nc_dir: Path, day: int, dtype=np.float64) -> tuple:
    """Return (raw_dpx, raw_dpy) that B200 saw at step 1 of integration
    `day`, by inverting the ERA5 temporal interpolation of dp_x/dp_y.

    The snapshot written at the end of day d-1 stores

        snap_{d-1} = raw_{d-1} + (11/12) * (raw_d - raw_{d-1})

    (main.f90: the day-start field is raw, then each of the 12 daily steps
    advances 11/12 of the increment toward the next day's field). Because
    results_day_00.nc is written at init, pre-interpolation, raw_1 == snap_0,
    and the chain inverts as

        raw_1 = snap_0
        raw_d = raw_{d-1} + (12/11) * (snap_{d-1} - raw_{d-1})

    Valid only when the run used ERA5 temporal interpolation (the default);
    frozen-wind runs (snap == raw) must pass --no-reconstruct-forcing.
    """
    raw_dpx = raw_dpy = None
    for d in range(1, day + 1):
        snap = load_nc_state(nc_dir / f"results_day_{d - 1:02d}.nc", dtype=dtype)
        if d == 1:
            raw_dpx = snap["dpx"].copy()
            raw_dpy = snap["dpy"].copy()
        else:
            raw_dpx = raw_dpx + (12.0 / 11.0) * (snap["dpx"] - raw_dpx)
            raw_dpy = raw_dpy + (12.0 / 11.0) * (snap["dpy"] - raw_dpy)
    return raw_dpx, raw_dpy


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", choices=sorted(RUN_DIRS), default="a0")
    p.add_argument("--nc", help="NetCDF state file (default from --run/day)")
    p.add_argument("--hhh", default=str(REPO_ROOT / "hhh.bar"))
    p.add_argument("--csv", help="stage1022_block200.csv (default from --run)")
    p.add_argument("--day", type=int, default=1)
    p.add_argument("--step", type=int, default=1)
    p.add_argument("--all-days", action="store_true",
                   help="report days 1..30 (hard gate on every replayable day)")
    p.add_argument("--no-reconstruct-forcing", action="store_true",
                   help="disable the raw dp_x/dp_y temporal-interpolation "
                        "inversion (use for runs without ERA5 temporal "
                        "interpolation, e.g. ICEBERG_FROZEN_WIND=true)")
    p.add_argument("--rtol", type=float, default=1e-4)
    p.add_argument("--float32", action="store_true",
                   help="replay in float32 (Fortran working precision)")
    args = p.parse_args(argv)

    flags = RUN_FLAGS[args.run]
    dtype = np.float32 if args.float32 else np.float64
    hhh = Path(args.hhh)
    if not hhh.exists():
        print(f"FAIL: bathymetry {hhh} not found")
        return 3

    kt1_raw = read_hhh_bar(hhh)
    print(f"anchor hhh.bar: {hhh}")

    # nc_path / csv_path resolution happens per-day; hold the user overrides.
    nc_override, csv_override = args.nc, args.csv
    if nc_override is None and csv_override is None and not args.all_days:
        nc_override, csv_override = resolve_paths(args.run, None, None, args.day)

    if nc_override is None:
        pass  # resolved inside the day loop below

    # Day-0 reference ro for use_ref (A4): frozen initial density.
    ref_state = None
    if flags["use_ref"]:
        ref_nc, _ = resolve_paths(args.run, None, None, 1)
        ref_state = load_nc_state(ref_nc, dtype=dtype)

    if not args.all_days:
        days_steps = [(args.day, args.step)]
    else:
        days_steps = [(d, 1) for d in range(1, 31)]

    gate_ok = True
    # Raw (day-start) dp_x/dp_y chain for the temporal-interpolation
    # inversion; seeded by day 1 (snap_0 == raw_1) and carried forward.
    raw_dpx = raw_dpy = None
    for day, step in days_steps:
        if nc_override is None:
            nc_path, _ = resolve_paths(args.run, None, None, day)
        else:
            nc_path = Path(nc_override)
            if args.all_days:
                stem = nc_path.stem
                nc_path = nc_path.with_name(stem.rsplit("_", 1)[0] + f"_{day - 1:02d}.nc")
        csv_path = Path(csv_override) if csv_override else None
        if csv_path is None:
            _, csv_path = resolve_paths(args.run, None, None, day)

        if step != 1:
            print(f"day {day:2d} step {step:2d}: SKIP (only step=1 is replayable "
                  f"from end-of-day NetCDF state; in-day evolution not stored)")
            continue

        if not nc_path.exists():
            print(f"day {day:2d}: SKIP ({nc_path.name} missing)")
            continue

        state = load_nc_state(nc_path, dtype=dtype)
        if flags["use_ref"]:
            if ref_state is None:
                print(f"day {day:2d}: FAIL (use_ref requested but reference "
                      f"state unavailable)")
                gate_ok = False
                continue
            state["ro"] = ref_state["ro"]

        # Raw dp_x/dp_y inversion: B200 at step 1 of day d reads the raw
        # day-d field, while the end-of-day NetCDF stores the interpolated
        # snap_{d-1}. Seed raw_1 == snap_0 on day 1; then for each later day
        # invert raw_d = raw_{d-1} + (12/11)*(snap_{d-1} - raw_{d-1}).
        if not args.no_reconstruct_forcing and step == 1:
            if day == 1:
                raw_dpx = state["dpx"].copy()
                raw_dpy = state["dpy"].copy()
            elif raw_dpx is None:
                # Single-day mode starting at day >= 2: build the chain.
                raw_dpx, raw_dpy = reconstruct_raw_forcing(
                    nc_path.parent, day, dtype)
            else:
                raw_dpx = raw_dpx + (12.0 / 11.0) * (state["dpx"] - raw_dpx)
                raw_dpy = raw_dpy + (12.0 / 11.0) * (state["dpy"] - raw_dpy)
            state["dpx"] = raw_dpx
            state["dpy"] = raw_dpy

        grid = coup1(kt1_raw, state["z"], dtype=dtype)

        # Hard gate: reconstructed wcl == NetCDF water_column_levels.
        wcl_mismatch = int(np.count_nonzero(grid["wcl"] != state["wcl_nc"]))
        if wcl_mismatch:
            print(f"day {day:2d}: FAIL wcl reconstruction "
                  f"({wcl_mismatch} / {IS1 * JS1} cells differ)")
            gate_ok = False
            continue

        replay = replay_block200(state, grid, freeze_tw=flags["freeze_tw"],
                                 dtype=dtype)

        header, rows = read_block200_csv(csv_path)
        row = next((r for r in rows if r[0] == day and r[1] == step), None)
        if row is None:
            print(f"day {day:2d} step {step:2d}: FAIL (CSV row not found)")
            gate_ok = False
            continue
        csv_vals = row[2]

        cmp = compare_metrics(replay, csv_vals, args.rtol)
        n_skip = sum(1 for _, cv, _, _, ok in cmp if np.isnan(cv))
        n_fail = sum(1 for _, _, _, rel, ok in cmp if ok is False)
        worst = max((rel for _, _, _, rel, ok in cmp if ok is not None), default=0.0)
        if n_fail == 0:
            if day == 1:
                status = "PASS"
            elif not args.no_reconstruct_forcing:
                status = "PASS(rec)"   # reconstructed raw dp chain, full match
            else:
                status = "PASS(rep)"   # snapshot dp, report-only
        else:
            status = "FAIL"
        print(f"day {day:2d} step {step:2d}: {status}  "
              f"fail={n_fail} skip(NaN)={n_skip} worst_rel={worst:.3e}")
        if n_fail:
            gate_ok = False
            for name, cv, rv, rel, ok in cmp:
                if ok is False:
                    print(f"    {name:>12}: csv={cv:.6e} replay={rv:.6e} rel={rel:.3e}")
        elif day == 1:
            for name, cv, rv, rel, ok in cmp:
                if ok is not None:
                    print(f"    {name:>12}: csv={cv:.6e} replay={rv:.6e} rel={rel:.3e}")

    return 0 if gate_ok else 1


if __name__ == "__main__":
    sys.exit(main())