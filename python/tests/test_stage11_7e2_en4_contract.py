"""
Stage 11.7E.2 — EN4 ocean-initial contract verification (verify-only).

Verifies the EN4 passthrough product consumed by src/initial_ocean_reader.f90
against the 11.7A contract.

Two product families exist (documented in docs/validation/
stage11.4_en4_stabilization.md §11, line 111):

  * ``*_rebuild.nc``  — built with the D-21-fixed script, ``--method`` default
    (nearest). STRICT: full 11.7A contract, incl. ``z_model_m`` == DATA z/100
    (elementwise) and land/below-bottom == 0.0 (never NaN).
  * shipped ``initial_ts_YYYY-MM-01.nc`` — built with the older bilinear
    producer; carries the bilinear signature (land pre-filled with nearest
    values, ``z_model_m`` label ``[2.5 .. 550]``). These clauses are
    PROVENANCE-LEVEL: the reader maps file k <-> model k 1:1 by dimids and
    never reads ``z_model_m``/``wet_mask``, so they do not affect the runtime
    contract. Reported as INFO, not FAIL.

Hard (STRICT) clauses for every product:
  * dims i=133 / j=105 / k=18 (== model is1/js1/ks) — reader verified explicitly
  * ``temperature_celsius`` / ``salinity_mass_fraction`` present, float32
  * wet-cell T/S finite and inside the reader range guards
    T[-10,40] / S[-0.002,0.1]

Exit code 0 = no STRICT violation; 1 = strict violation.

Usage:
    conda run -n iceberg-thermodynamic-model python \
        python/tests/test_stage11_7e2_en4_contract.py
"""

import hashlib
import os
import sys
from datetime import datetime

import numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from netCDF4 import Dataset
except ImportError:  # pragma: no cover
    print("ERROR: netCDF4 unavailable (activate conda env iceberg-thermodynamic-model)")
    sys.exit(1)

# Canonical model grid (src/param.f90: is=132, js=104, ks=18; is1/js1 stagger)
IS1, JS1, KS = 133, 105, 18
# src/param.f90 DATA z [cm]
Z_CM = np.array([250., 500., 1000., 1500., 2000., 2500., 3000., 4000.,
                 5000., 7500., 10000., 15000., 20000., 25000., 30000.,
                 40000., 50000., 60000.])
Z_M_EXPECTED = Z_CM / 100.0

# (relative path, strict)
FILES = [
    ("data/input/processed/ocean/initial_ts_2020-01-01.nc", False),
    ("data/input/processed/ocean/initial_ts_2020-04-01.nc", False),
    ("data/input/processed/ocean/initial_ts_2020-01-01_rebuild.nc", True),
    ("data/input/processed/ocean/initial_ts_2020-04-01_rebuild.nc", True),
]

# Expected coordinate ranges for the Barents domain
LAT_MIN, LAT_MAX = 64.0, 86.0
LON_MIN, LON_MAX = 5.0, 80.0

CHECKS = 0
ERRORS = 0
INFOS = 0
FILES_FOUND = 0
FILES_MISSING = 0


def check(cond, label, detail=""):
    global CHECKS, ERRORS
    CHECKS += 1
    if cond:
        print("PASS %s" % label)
    else:
        ERRORS += 1
        print("FAIL %s %s" % (label, detail))


def info(label):
    global INFOS
    INFOS += 1
    print("INFO %s" % label)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path, strict, file_index):
    global FILES_FOUND, FILES_MISSING
    base = os.path.basename(path)
    print("=" * 72)
    print("EN4 CONTRACT [%s]: %s" % ("STRICT" if strict else "SHIPPED", base))
    print("=" * 72)
    if not os.path.exists(path):
        FILES_MISSING += 1
        info("SKIP file absent (gitignored product)")
        return
    FILES_FOUND += 1
    print("md5 = %s" % md5(path))
    with Dataset(path) as ds:
        dims = {n: len(ds.dimensions[n]) for n in ds.dimensions}
        print("dims = %s" % dims)
        check(dims.get("i") == IS1, "%s dim i == 133" % base, str(dims))
        check(dims.get("j") == JS1, "%s dim j == 105" % base, str(dims))
        check(dims.get("k") == KS, "%s dim k == 18" % base, str(dims))

        # --- Verify ALL claimed variables exist with correct dtypes ---
        required_vars = {
            "temperature_celsius": np.float32,
            "salinity_mass_fraction": np.float32,
            "density_anomaly_gcm3": np.float32,
            "wet_mask": np.int8,
            "water_column_levels": np.int64,
            "lat": np.float64,
            "lon": np.float64,
            "z_model_m": np.float64,
        }
        for v, expected_dtype in required_vars.items():
            check(v in ds.variables, "%s has %s" % (base, v))
            if v in ds.variables:
                check(ds.variables[v].dtype == expected_dtype,
                      "%s %s dtype == %s" % (base, v, expected_dtype),
                      "got %s" % ds.variables[v].dtype)

        # Verify dimensions of each variable
        dim_checks = {
            "temperature_celsius": ("i", "j", "k"),
            "salinity_mass_fraction": ("i", "j", "k"),
            "density_anomaly_gcm3": ("i", "j", "k"),
            "wet_mask": ("i", "j"),
            "water_column_levels": ("i", "j"),
            "lat": ("i", "j"),
            "lon": ("i", "j"),
            "z_model_m": ("k",),
        }
        for v, expected_dims in dim_checks.items():
            if v in ds.variables:
                check(ds.variables[v].dimensions == expected_dims,
                      "%s %s dims == %s" % (base, v, str(expected_dims)),
                      "got %s" % str(ds.variables[v].dimensions))

        # Load T/S data
        if "temperature_celsius" not in ds.variables:
            return
        t = np.asarray(ds.variables["temperature_celsius"][:], dtype=np.float64)
        s = np.asarray(ds.variables["salinity_mass_fraction"][:], dtype=np.float64)

        # Load wet_mask and water_column_levels for proper bottom masking
        wet_2d = None
        wcl = None
        if "wet_mask" in ds.variables:
            wet_2d = np.asarray(ds.variables["wet_mask"][:])
            check(wet_2d.shape == (IS1, JS1), "%s wet_mask shape (133,105)" % base)
        if "water_column_levels" in ds.variables:
            wcl = np.asarray(ds.variables["water_column_levels"][:])
            check(wcl.shape == (IS1, JS1), "%s water_column_levels shape (133,105)" % base)

        # --- Build proper 3D wet mask using water_column_levels ---
        # A cell (i,j,k) is wet if k <= water_column_levels[i,j]
        # This correctly handles bottom masking (levels below bathymetry are dry)
        wet_3d = None
        if wcl is not None:
            wet_3d = np.zeros((IS1, JS1, KS), dtype=bool)
            for i in range(IS1):
                for j in range(JS1):
                    n_wet = wcl[i, j]
                    if n_wet > 0:
                        wet_3d[i, j, :min(n_wet, KS)] = True
            total_active = int(wet_3d.sum())
            print("active 3D cells (from water_column_levels) = %d" % total_active)
        elif wet_2d is not None:
            # Fallback: broadcast 2D wet_mask to all levels (legacy behavior)
            wet_3d = np.broadcast_to(wet_2d.astype(bool)[:, :, None], t.shape)
            print("active 3D cells (legacy broadcast wet_mask) = %d" % int(wet_3d.sum()))
        else:
            info("no wet_mask or water_column_levels - cannot count wet cells")

        # --- HARD clauses (always apply) ---
        if wet_3d is not None:
            check(np.isfinite(t[wet_3d]).all(), "%s wet T finite" % base)
            check(np.isfinite(s[wet_3d]).all(), "%s wet S finite" % base)
            check(t[wet_3d].min() >= -10.0 and t[wet_3d].max() <= 40.0,
                  "%s wet T in reader guard [-10,40]" % base,
                  "%.4f..%.4f" % (t[wet_3d].min(), t[wet_3d].max()))
            check(s[wet_3d].min() >= -0.002 and s[wet_3d].max() <= 0.1,
                  "%s wet S in reader guard [-0.002,0.1]" % base,
                  "%.6f..%.6f" % (s[wet_3d].min(), s[wet_3d].max()))
            dry_3d = ~wet_3d
            dry_t_zero = bool(np.all(t[dry_3d] == 0.0) and np.all(s[dry_3d] == 0.0))
            if strict:
                check(dry_t_zero, "%s land/below-bottom == 0.0 (never NaN)" % base)
            else:
                info("land/below-bottom == 0.0: %s -> %s "
                     "(bilinear producer signature; reader ignores dry cells; "
                     "documented stage11.4 §11)"
                     % (base, "yes" if dry_t_zero else "NO (nonzero pre-fill)"))

        # Verify lat/lon coordinate ranges
        if "lat" in ds.variables and "lon" in ds.variables:
            lat = np.asarray(ds.variables["lat"][:], dtype=np.float64)
            lon = np.asarray(ds.variables["lon"][:], dtype=np.float64)
            check(lat.shape == (IS1, JS1), "%s lat shape (133,105)" % base)
            check(lon.shape == (IS1, JS1), "%s lon shape (133,105)" % base)
            check(lat.min() >= LAT_MIN and lat.max() <= LAT_MAX,
                  "%s lat range [%s, %s]" % (base, LAT_MIN, LAT_MAX),
                  "got %.2f..%.2f" % (lat.min(), lat.max()))
            check(lon.min() >= LON_MIN and lon.max() <= LON_MAX,
                  "%s lon range [%s, %s]" % (base, LON_MIN, LON_MAX),
                  "got %.2f..%.2f" % (lon.min(), lon.max()))
            print("lat range: %.2f .. %.2f" % (lat.min(), lat.max()))
            print("lon range: %.2f .. %.2f" % (lon.min(), lon.max()))

        # Verify z_model_m
        if "z_model_m" in ds.variables:
            z = np.asarray(ds.variables["z_model_m"][:], dtype=np.float64)
            print("z_model_m = %s" % z.tolist())
            check(z.shape == (KS,), "%s z_model_m length 18" % base)
            z_ok = bool(np.allclose(z, Z_M_EXPECTED, atol=1e-9))
            if strict:
                check(z_ok, "%s z_model_m == DATA z/100 (elementwise)" % base,
                      "%s vs %s" % (z.tolist(), Z_M_EXPECTED.tolist()))
            else:
                info("z_model_m == DATA z/100: %s -> %s "
                     "(bilinear producer label; reader maps k<->k 1:1 by dimids, "
                     "never reads z_model_m; documented stage11.4 §11)"
                     % (base, "yes" if z_ok else "NO"))
        else:
            check(False, "%s has z_model_m" % base)

        # Verify density_anomaly_gcm3
        if "density_anomaly_gcm3" in ds.variables:
            ro = np.asarray(ds.variables["density_anomaly_gcm3"][:], dtype=np.float64)
            check(bool(np.isfinite(ro).all()), "%s density_anomaly finite" % base)
            print("density_anomaly_gcm3: min=%.6g max=%.6g negatives=%d"
                  % (ro.min(), ro.max(), int((ro < 0).sum())))

        # Verify coordinate variables exist
        for cv in ("i", "j", "k"):
            if cv in ds.variables:
                check(ds.variables[cv].dimensions == (cv,),
                      "%s coord var %s dims == (%s,)" % (base, cv, cv))


def main():
    global CHECKS, ERRORS, INFOS, FILES_FOUND, FILES_MISSING
    print("Stage 11.7E.2 — EN4 ocean-initial contract verification")
    print("Default file path (from initial_ocean_reader.f90): data/input/processed/ocean/initial_ts_2020-01-01.nc")

    for idx, (rel, strict) in enumerate(FILES):
        verify(os.path.join(PROJECT, rel), strict, idx)

    print("=" * 72)
    print("FILES FOUND: %d  FILES MISSING: %d" % (FILES_FOUND, FILES_MISSING))
    print("TOTAL CHECKS: %d  PASSED: %d  FAILED: %d  INFO: %d" %
          (CHECKS, CHECKS - ERRORS, ERRORS, INFOS))
    print("=" * 72)

    # SKIP behavior: if NO files found, explicit SKIP with exit 0
    # If SOME files missing but some found, report partial and exit 1
    if FILES_FOUND == 0:
        print("SKIP: no EN4 products available (expected in clean clone)")
        return 0
    elif FILES_MISSING > 0:
        print("FAIL: partial EN4 products - %d missing" % FILES_MISSING)
        return 1

    if CHECKS == 0:
        print("NO CHECKS RAN")
        return 1

    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())