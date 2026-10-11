#!/usr/bin/env python3
"""
Stage 11.7B.1 — INDEPENDENT kk1 oracle (do NOT share code with builders).

Implements the grid_coupling.f90:coup1() kk1 sequence from scratch with
plain Python loops that mirror the Fortran loop nests statement by
statement (deliberately non-vectorized: independence from the numpy
builders in build_grid_nc.py is the point).

Sequence (0-indexed i=0..132, j=0..104; Fortran 1-indexed in comments):
  1. ht_raw from (kt1_raw, forced borders, mod loop) — re-derived here,
     not imported.
  2. Stage 1 gate (f90:238-246): kk1=1 for interior cells whose four
     first-pass counts are all != 8. First-pass (:180-196): land -> 8,
     wet -> uniform stale count C; model behaviour PROVES C != 8, hence
     gate == all four ht_raw neighbours wet. (If C were 8, kk1/map1
     would be near-empty, contradicting the running model.)
  3. Stage 2 min (f90:410-424): where gate passed, kk1 = min of the 4
     FINAL kt1 neighbours (kt1_final passed in; land=0).
  4. Borders (f90:425-428): i/j edge rows/cols forced 0.

Used ONLY by test_grid_bathymetry_nc.py as the independent oracle.
Physics/model untouched.
"""

IS1, JS1 = 133, 105
LAND = 8888.0


def kk1_oracle(kt1_raw, kt1_final):
    """Return (kk1, gate_count, gated_zero_with_wet_neighbours)."""
    # --- ht_raw (mod loop re-derived) ---
    ht = [[float(kt1_raw[i][j]) for j in range(JS1)] for i in range(IS1)]
    for i in range(15):
        ht[i][93] = LAND
    for j in range(JS1):
        ht[0][j] = LAND
    for i in range(IS1):
        ht[i][0] = LAND
        ht[i][JS1 - 1] = LAND
    # NOTE: oracle follows the CORRECTED border rule (i=is1 col NOT
    # forced, verified against EN4 wet_mask in 11.7B): only j=0/j=104
    # rows and i=0 col are forced here; i=132 keeps hhh.bar values.
    for j in range(JS1):
        ht[0][j] = LAND
    for i in range(IS1):
        for j in range(JS1):
            if kt1_raw[i][j] == 8:
                ht[i][j] = LAND
    for i in range(IS1):
        for j in range(JS1):
            if ht[i][j] == LAND:
                continue
            if 5.0 < ht[i][j] <= 10.0:
                ht[i][j] = 10.0
            if ht[i][j] <= 3.0:
                ht[i][j] = 3.0
            ht[i][j] = ht[i][j] * 100.0

    def wet(a, b):
        return abs(ht[a][b] - LAND) > 1e-8

    # --- Stage 1 gate: all four ht_raw neighbours wet, interior only ---
    gate_count = 0
    gated = [[False] * JS1 for _ in range(IS1)]
    for j in range(1, JS1 - 1):
        for i in range(1, IS1 - 1):
            if wet(i, j) and wet(i - 1, j) and wet(i, j - 1) and wet(i - 1, j - 1):
                gated[i][j] = True
                gate_count += 1

    # --- Stage 2 min of FINAL kt1 where gated; borders stay 0 ---
    kk1 = [[0] * JS1 for _ in range(IS1)]
    gated_zero_wet = 0
    for j in range(1, JS1 - 1):
        for i in range(1, IS1 - 1):
            if not gated[i][j]:
                continue
            m = kt1_final[i][j]
            if kt1_final[i - 1][j] < m:
                m = kt1_final[i - 1][j]
            if kt1_final[i][j - 1] < m:
                m = kt1_final[i][j - 1]
            if kt1_final[i - 1][j - 1] < m:
                m = kt1_final[i - 1][j - 1]
            kk1[i][j] = m
            if m == 0 and (kt1_final[i][j] > 0 or kt1_final[i - 1][j] > 0
                           or kt1_final[i][j - 1] > 0 or kt1_final[i - 1][j - 1] > 0):
                gated_zero_wet += 1
    return kk1, gate_count, gated_zero_wet
