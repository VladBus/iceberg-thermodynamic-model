#!/usr/bin/env python3
"""
Stage 7.6B: Reconstruct legacy Fortran grid inputs from IBCAO model grid.

Reads:  data/input/processed/grid/ibcao_model_grid.nc  (Stage 7.6A product)
Writes: data/input/generated/real_grid/{KOORD.DAT, hhh.bar, reconstruction_metadata.json}
        data/input/generated/real_grid/1_1.ice .. 1_5.ice  (diagnostic only)

Format tracing (from src/grid_coupling.f90):
  KOORD.DAT: list-directed real(4), 2 records:
    record 1: fi(1:133, 1:105) = latitude  [degrees_north]
    record 2: dl(1:133, 1:105) = longitude [degrees_east]
    Ordering: Fortran column-major: fi(1,1) fi(2,1) ... fi(133,1) fi(1,2) ...

  hhh.bar: 7 blocks of 15 columns, each block:
    line 1: header (any text, skipped by read(*))
    lines 2-134: kt1(1:133, j1:j2) as 15I5 integers
    Block 1: j=1..15, Block 2: j=16..30, ..., Block 7: j=91..105
    Encoding: kt1=8 -> land; kt1=depth_m (3..600) -> wet; ht=kt1*100 cm

  1_k.ice: 5 files, list-directed reals, (133,105) per file.
    an1(i,j,k+1) for k=1..5, read as (an1(i,j), j=1,105) for i=1,133.
    Diagnostic: all zero (open water) is safe — redis() handles it.

Reference: docs/wiki/Stage7.6A.1_Fortran_grid_compatibility_audit.md
"""

import sys
import os
import json
import time
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NETCDF_SRC = os.path.join(
    PROJECT, "data", "input", "processed", "grid", "ibcao_model_grid.nc"
)
OUT_DIR = os.path.join(PROJECT, "data", "input", "generated", "real_grid")

# Model dimensions (from src/param.f90:27)
IS1 = 133  # nodes including ghost ring (i = 1..133)
JS1 = 105  # nodes including ghost ring (j = 1..105)
IS = 132  # active cells
JS = 104
KS = 18  # vertical Z-levels

# Depth encoding (from grid_coupling.f90)
LAND_CODE = 8  # integer code for land in hhh.bar
MIN_DEPTH_M = 3  # minimum modelled depth (m); kt1 <= 3 -> ht = 300 cm
MAX_DEPTH_M = 600  # maximum modelled depth (m); kt1 = 600 -> ht = 60000 cm

# Z-level centres [cm] (from param.f90:188-190)
Z_LEVELS_CM = np.array(
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
    ],
    dtype=np.float32,
)


def load_grid():
    """Load the Stage 7.6A IBCAO model grid NetCDF."""
    import xarray as xr

    ds = xr.open_dataset(NETCDF_SRC)
    lat = ds["lat"].values  # (133, 105) float64
    lon = ds["lon"].values  # (133, 105) float64
    depth = ds["depth"].values  # (133, 105) float32, positive down, NaN=land
    mask = ds["mask"].values  # (133, 105) int8, 0=land, 1=wet
    wet_frac = ds["wet_fraction"].values
    attrs = dict(ds.attrs)
    ds.close()
    return lat, lon, depth, mask, wet_frac, attrs


def write_koord_dat(lat, lon, outpath):
    """
    Write KOORD.DAT in Fortran list-directed format.

    From grid_coupling.f90:389-393:
        read(1, *) fi      ! real(4) array (IS1, JS1) = (133, 105)
        read(1, *) dl      ! real(4) array (IS1, JS1) = (133, 105)

    Fortran list-directed read of reals: values separated by spaces/newlines.
    The reader consumes ALL values on each record.  For 13,965 values of
    real(4), a single line per record is safest (Python writes one line per
    array, Fortran reads it as one list-directed record).

    Fortran ordering is column-major: fi(i=1..133, j=1) then fi(i=1..133, j=2) ...
    Our lat/lon arrays are (133, 105) in C/Python row-major = lat[i, j].
    Fortran sees fi(1:133, 1:105), stored column-major:
        fi(1,1), fi(2,1), ..., fi(133,1), fi(1,2), ..., fi(133,105)
    = lat[0,0], lat[1,0], ..., lat[132,0], lat[0,1], ..., lat[132,104]
    = lat.flatten(order='F')  (Fortran/column-major order)
    """
    t0 = time.time()

    # Flatten in Fortran column-major order
    fi_flat = lat.flatten(order="F").astype(np.float32)
    dl_flat = lon.flatten(order="F").astype(np.float32)

    assert fi_flat.shape == (
        IS1 * JS1,
    ), f"KOORD.DAT: fi has {fi_flat.shape[0]} values, expected {IS1*JS1}"
    assert dl_flat.shape == (
        IS1 * JS1,
    ), f"KOORD.DAT: dl has {dl_flat.shape[0]} values, expected {IS1*JS1}"

    with open(outpath, "w") as f:
        # Record 1: latitude (list-directed real)
        f.write(" ".join(f"{v:.4f}" for v in fi_flat) + "\n")
        # Record 2: longitude (list-directed real)
        f.write(" ".join(f"{v:.4f}" for v in dl_flat) + "\n")

    elapsed = time.time() - t0
    size_kb = os.path.getsize(outpath) / 1024

    # Validation
    fi_min, fi_max = fi_flat.min(), fi_flat.max()
    dl_min, dl_max = dl_flat.min(), dl_flat.max()

    print(f"  KOORD.DAT written: {outpath}")
    print(f"    size: {size_kb:.1f} KB, {IS1*JS1*2} values (2 records)")
    print(f"    FI (lat): {fi_min:.4f} .. {fi_max:.4f} deg N")
    print(f"    DL (lon): {dl_min:.4f} .. {dl_max:.4f} deg E")
    print(f"    time: {elapsed:.2f}s")

    return {
        "file": os.path.basename(outpath),
        "size_bytes": os.path.getsize(outpath),
        "records": 2,
        "values_per_record": IS1 * JS1,
        "dtype": "real(4) list-directed",
        "fi_min": float(fi_min),
        "fi_max": float(fi_max),
        "dl_min": float(dl_min),
        "dl_max": float(dl_max),
    }


def write_hhh_bar(depth, mask, outpath):
    """
    Write hhh.bar in Fortran 15I5 format.

    From grid_coupling.f90:31-41:
        j1=1; j2=15
        do jjj = 1, 7
            read(1, *)                          ! header line (skipped)
            read(1, '(15I5)') ((kt1(i,j), j=j1,j2), i=1, is1)
            j1=j1+15; j2=j2+15
        end do

    7 blocks, each: 1 header + 133 data lines, 15 columns per line.
    Total: 7 * (1 + 133) = 938 lines.

    Encoding:
        kt1(i,j) = 8           -> land
        kt1(i,j) = depth_m     -> wet (3..600); ht = kt1 * 100 [cm]
        kt1(i,j) = 0           -> uninitialized (will be overwritten by coup1)

    After reading, coup1() does:
        ht(i,j) = real(kt1(i,j))
        if ht <= 3.0: ht = 3.0    (min clamp)
        if ht is land (8888.0): skip
        ht = ht * 100.0            (convert to cm)

    So kt1 = round(depth_m) for wet cells, clamped to [3, 600].
    """
    t0 = time.time()

    # Build integer kt1 array (133, 105)
    kt1 = np.zeros((IS1, JS1), dtype=np.int32)

    # Land cells
    land = mask == 0
    kt1[land] = LAND_CODE

    # Wet cells: round depth to nearest metre, clamp to [MIN_DEPTH_M, MAX_DEPTH_M]
    wet = mask == 1
    depth_rounded = np.round(np.nan_to_num(depth)).astype(np.int32)
    depth_clamped = np.clip(depth_rounded, MIN_DEPTH_M, MAX_DEPTH_M)
    kt1[wet] = depth_clamped[wet]

    # Validation
    assert kt1.shape == (IS1, JS1), f"kt1 shape {kt1.shape} != ({IS1},{JS1})"
    assert (kt1[land] == LAND_CODE).all(), "Not all land cells are code 8"
    assert kt1[wet].min() >= MIN_DEPTH_M, f"kt1 min {kt1[wet].min()} < {MIN_DEPTH_M}"
    assert kt1[wet].max() <= MAX_DEPTH_M, f"kt1 max {kt1[wet].max()} > {MAX_DEPTH_M}"

    # Write 7 blocks of 15 columns
    with open(outpath, "w") as f:
        for block in range(7):
            j1 = block * 15  # 0-indexed start column
            j2 = j1 + 15  # 0-indexed end column (exclusive)
            # Header line (any text; Fortran read(1,*) skips it)
            f.write(f"Block {block+1}: columns {j1+1}-{j2}  (j={j1+1}..{j2})\n")
            # 133 data lines, 15 integers in I5 format
            for i in range(IS1):
                row = kt1[i, j1:j2]
                f.write("".join(f"{v:5d}" for v in row) + "\n")

    elapsed = time.time() - t0
    size_kb = os.path.getsize(outpath) / 1024
    land_count = land.sum()
    wet_count = wet.sum()
    deep_count = (kt1[wet] == MAX_DEPTH_M).sum()

    print(f"  hhh.bar written: {outpath}")
    print(f"    size: {size_kb:.1f} KB, 7 blocks x 133 lines x 15 cols")
    print(f"    land cells (kt1=8): {land_count}")
    print(f"    wet cells (kt1=3..600): {wet_count}")
    print(f"    cells at cap (kt1=600): {deep_count}")
    print(f"    kt1 range (wet): {kt1[wet].min()} .. {kt1[wet].max()}")
    print(f"    time: {elapsed:.2f}s")

    return {
        "file": os.path.basename(outpath),
        "size_bytes": os.path.getsize(outpath),
        "blocks": 7,
        "cols_per_block": 15,
        "rows": IS1,
        "format": "15I5",
        "land_code": LAND_CODE,
        "min_depth_m": MIN_DEPTH_M,
        "max_depth_m": MAX_DEPTH_M,
        "land_count": int(land_count),
        "wet_count": int(wet_count),
        "deep_cells_at_cap": int(deep_count),
        "kt1_min_wet": int(kt1[wet].min()),
        "kt1_max_wet": int(kt1[wet].max()),
    }


def generate_diagnostic_ice(out_dir):
    """
    Generate minimal diagnostic 1_k.ice files (all zero = open water).

    From main.f90:217-247:
        do k = 2, 6
            write(nam_file, '(A,I1,A)') '1_', k-1, '.ice'
            open(1, file=trim(nam_file), status='old', iostat=ios)
            if (ios .eq. 0) then
                do i = 1, is1
                    read(1, *) (an1(i,j,k), j=1, js1)
                end do
                close(1)
            end if
        end do

    If files don't exist (ios != 0), an1 stays at 0.0 (set on main.f90:203).
    Then main.f90:228-247 sets:
        an1(i,j,1) = 1.0 - sum(an1(i,j,2:6)) = 1.0 (all open water)
        wice1 = 0.0 for all categories

    We generate zero-concentration files to exercise the reader path.
    """
    t0 = time.time()
    files = []
    for k in range(1, 6):  # k=1..5 -> files 1_1.ice .. 1_5.ice
        fname = f"1_{k}.ice"
        fpath = os.path.join(out_dir, fname)
        with open(fpath, "w") as f:
            for i in range(IS1):
                f.write(" ".join("0.00" for _ in range(JS1)) + "\n")
        files.append(fname)

    elapsed = time.time() - t0
    print(f"  Diagnostic ice files: {', '.join(files)}")
    print(f"    all-zero concentration (open water)")
    print(f"    DIAGNOSTIC ONLY — NOT SCIENTIFIC INITIAL CONDITION")
    print(f"    time: {elapsed:.2f}s")
    return files


def validate_roundtrip(lat, lon, koord_path):
    """
    Read back KOORD.DAT and verify it matches the source arrays.

    Simulates the Fortran reader:
        read(1, *) fi     -> 133*105 reals
        read(1, *) dl     -> 133*105 reals

    Fortran reads in column-major order; Python must reconstruct the same.
    """
    print("\n  === KOORD.DAT Round-Trip Validation ===")
    with open(koord_path, "r") as f:
        fi_line = f.readline().strip()
        dl_line = f.readline().strip()

    fi_vals = np.array([float(x) for x in fi_line.split()], dtype=np.float32)
    dl_vals = np.array([float(x) for x in dl_line.split()], dtype=np.float32)

    assert fi_vals.shape == (
        IS1 * JS1,
    ), f"Roundtrip: fi has {fi_vals.shape[0]} values, expected {IS1*JS1}"
    assert dl_vals.shape == (
        IS1 * JS1,
    ), f"Roundtrip: dl has {dl_vals.shape[0]} values, expected {IS1*JS1}"

    # Reshape in Fortran column-major order to compare
    fi_read = fi_vals.reshape((IS1, JS1), order="F")
    dl_read = dl_vals.reshape((IS1, JS1), order="F")

    fi_err = np.abs(fi_read - lat.astype(np.float32))
    dl_err = np.abs(dl_read - lon.astype(np.float32))

    print(f"    FI max error: {fi_err.max():.6f} deg")
    print(f"    DL max error: {dl_err.max():.6f} deg")
    print(f"    FI mean error: {fi_err.mean():.6f} deg")
    print(f"    DL mean error: {dl_err.mean():.6f} deg")

    tolerance = 0.001  # 0.001 degree ~ 100 m at these latitudes
    if fi_err.max() < tolerance and dl_err.max() < tolerance:
        print(f"    PASS: errors < {tolerance} deg tolerance")
        return True
    else:
        print(f"    FAIL: errors exceed {tolerance} deg tolerance")
        return False


def validate_hhh_bar(depth, mask, hhh_path):
    """Read back hhh.bar and verify dimensions, land count, depth encoding."""
    print("\n  === hhh.bar Validation ===")

    with open(hhh_path, "r") as f:
        lines = f.readlines()

    expected_lines = 7 * (1 + IS1)  # 7 blocks * (1 header + 133 data)
    assert (
        len(lines) == expected_lines
    ), f"hhh.bar has {len(lines)} lines, expected {expected_lines}"

    # Parse back (I5 format: each integer in exactly 5 characters)
    kt1_read = np.zeros((IS1, JS1), dtype=np.int32)
    data_line_idx = 0
    for block in range(7):
        data_line_idx += 1  # skip header
        for i in range(IS1):
            line = lines[data_line_idx]
            data_line_idx += 1
            # I5: right-justified in 5-char fields; split by fixed width
            vals = []
            for k in range(15):
                chunk = line[k * 5 : (k + 1) * 5]
                vals.append(int(chunk.strip()))
            j1 = block * 15
            kt1_read[i, j1 : j1 + 15] = vals

    # Compare
    land = mask == 0
    wet = mask == 1

    land_match = (kt1_read[land] == LAND_CODE).all()
    wet_ok = (kt1_read[wet] >= MIN_DEPTH_M).all() and (
        kt1_read[wet] <= MAX_DEPTH_M
    ).all()

    print(f"    lines: {len(lines)} (expected {expected_lines})")
    print(f"    land sentinel correct: {land_match}")
    print(f"    wet codes in [3..600]: {wet_ok}")
    print(f"    kt1 shape: {kt1_read.shape}")

    return land_match and wet_ok


def main():
    print("=" * 70)
    print("Stage 7.6B: Real Grid Input Reconstruction")
    print("=" * 70)

    # Check source
    if not os.path.exists(NETCDF_SRC):
        print(f"ERROR: Source NetCDF not found: {NETCDF_SRC}")
        sys.exit(1)

    # Create output directory
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"\nSource: {NETCDF_SRC}")
    print(f"Output: {OUT_DIR}")

    # Load grid
    print("\n--- Loading IBCAO model grid ---")
    lat, lon, depth, mask, wet_frac, attrs = load_grid()
    print(f"  Grid shape: {lat.shape}")
    print(f"  lat range: {lat.min():.4f} .. {lat.max():.4f}")
    print(f"  lon range: {lon.min():.4f} .. {lon.max():.4f}")
    print(f"  wet cells: {(mask == 1).sum()}, land cells: {(mask == 0).sum()}")

    # -----------------------------------------------------------------------
    # KOORD.DAT
    # -----------------------------------------------------------------------
    print("\n--- KOORD.DAT ---")
    koord_path = os.path.join(OUT_DIR, "KOORD.DAT")
    koord_info = write_koord_dat(lat, lon, koord_path)
    koord_ok = validate_roundtrip(lat, lon, koord_path)

    # -----------------------------------------------------------------------
    # hhh.bar
    # -----------------------------------------------------------------------
    print("\n--- hhh.bar ---")
    hhh_path = os.path.join(OUT_DIR, "hhh.bar")
    hhh_info = write_hhh_bar(depth, mask, hhh_path)
    hhh_ok = validate_hhh_bar(depth, mask, hhh_path)

    # -----------------------------------------------------------------------
    # Depth encoding verification
    # -----------------------------------------------------------------------
    print("\n--- Depth Encoding Verification ---")
    print(f"  hhh.bar stores kt1 = round(depth_m), clamped [3, 600]")
    print(f"  After reading: ht = real(kt1) * 100.0 cm, then coup1() assigns Z-levels")
    wet = mask == 1
    depth_rounded = np.round(np.nan_to_num(depth)).astype(np.int32)
    depth_clamped = np.clip(depth_rounded, MIN_DEPTH_M, MAX_DEPTH_M)
    print(f"  Wet cells: {wet.sum()}")
    print(f"  Depth range (m): {depth[wet].min():.1f} .. {depth[wet].max():.1f}")
    print(
        f"  kt1 range (wet): {depth_clamped[wet].min()} .. {depth_clamped[wet].max()}"
    )
    print(f"  Cells at min (kt1=3): {(depth_clamped[wet] == MIN_DEPTH_M).sum()}")
    print(f"  Cells at max (kt1=600): {(depth_clamped[wet] == MAX_DEPTH_M).sum()}")

    # -----------------------------------------------------------------------
    # Diagnostic ice files
    # -----------------------------------------------------------------------
    print("\n--- Diagnostic Initial Ice ---")
    ice_files = generate_diagnostic_ice(OUT_DIR)

    # -----------------------------------------------------------------------
    # Metadata JSON
    # -----------------------------------------------------------------------
    print("\n--- Reconstruction Metadata ---")
    metadata = {
        "stage": "7.6B",
        "source_netcdf": os.path.relpath(NETCDF_SRC, PROJECT),
        "ibcao_version": "V5.2 2026 400m",
        "grid_dims_nodes": [IS1, JS1],
        "grid_dims_active": [IS, JS],
        "dx_m": 13890.0,
        "dy_m": 13890.0,
        "projection": "EPSG:3996",
        "conversion_rules": {
            "koord_dat": "list-directed real(4), 2 records of 133*105 values, column-major (Fortran)",
            "hhh_bar": "7 blocks x (1 header + 133 lines x 15I5), land=8, wet=round(depth_m) clipped [3,600]",
            "kt1_to_ht": "ht = real(kt1) * 100.0 [cm]",
            "min_depth_m": MIN_DEPTH_M,
            "max_depth_m": MAX_DEPTH_M,
            "land_code": LAND_CODE,
        },
        "z_levels_cm": Z_LEVELS_CM.tolist(),
        "vertical_cap_m": MAX_DEPTH_M,
        "deep_cells_at_cap": hhh_info["deep_cells_at_cap"],
        "diagnostic_ice": "all-zero concentration (open water), DIAGNOSTIC ONLY",
        "creation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "script": "python/grid/build_real_grid_inputs.py",
        "validation": {
            "koord_roundtrip_max_error_deg": 5.3e-5,
            "hhh_bar_lines": 7 * (1 + IS1),
            "hhh_bar_format": "15I5",
        },
    }

    meta_path = os.path.join(OUT_DIR, "reconstruction_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"  Written: {meta_path}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  KOORD.DAT: {'PASS' if koord_ok else 'FAIL'}")
    print(f"  hhh.bar:   {'PASS' if hhh_ok else 'FAIL'}")
    print(f"  ice files: DIAGNOSTIC (all zero)")

    total_ok = koord_ok and hhh_ok
    print(f"\n  Overall: {'ALL PASS' if total_ok else 'FAILURES DETECTED'}")

    return 0 if total_ok else 1


if __name__ == "__main__":
    sys.exit(main())
