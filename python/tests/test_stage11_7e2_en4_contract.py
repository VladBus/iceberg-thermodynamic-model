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

CHECKS = 0
ERRORS = 0
INFOS = 0


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


def verify(path, strict):
    base = os.path.basename(path)
    print("=" * 72)
    print("EN4 CONTRACT [%s]: %s" % ("STRICT" if strict else "SHIPPED", base))
    print("=" * 72)
    if not os.path.exists(path):
        info("SKIP file absent (gitignored product)")
        return
    print("md5 = %s" % md5(path))
    with Dataset(path) as ds:
        dims = {n: len(ds.dimensions[n]) for n in ds.dimensions}
        print("dims = %s" % dims)
        check(dims.get("i") == IS1, "%s dim i == 133" % base, str(dims))
        check(dims.get("j") == JS1, "%s dim j == 105" % base, str(dims))
        check(dims.get("k") == KS, "%s dim k == 18" % base, str(dims))

        for v in ("temperature_celsius", "salinity_mass_fraction"):
            check(v in ds.variables, "%s has %s" % (base, v))
        if "temperature_celsius" not in ds.variables:
            return
        check(ds.variables["temperature_celsius"].dtype == np.float32,
              "%s T dtype float32" % base)

        t = np.asarray(ds.variables["temperature_celsius"][:], dtype=np.float64)
        s = np.asarray(ds.variables["salinity_mass_fraction"][:], dtype=np.float64)

        wet = None
        if "wet_mask" in ds.variables:
            check(ds.variables["wet_mask"].dimensions == ("i", "j"),
                  "%s wet_mask dims (i,j)" % base)
            wet = np.asarray(ds.variables["wet_mask"][:])
        if wet is not None:
            wet_bool = np.broadcast_to(wet.astype(bool)[:, :, None], t.shape)
            print("wet cells = %d" % wet_bool.sum())

        # --- HARD clauses (always apply) ---
        if wet is not None:
            check(np.isfinite(t[wet_bool]).all(), "%s wet T finite" % base)
            check(np.isfinite(s[wet_bool]).all(), "%s wet S finite" % base)
            check(t[wet_bool].min() >= -10.0 and t[wet_bool].max() <= 40.0,
                  "%s wet T in reader guard [-10,40]" % base,
                  "%.4f..%.4f" % (t[wet_bool].min(), t[wet_bool].max()))
            check(s[wet_bool].min() >= -0.002 and s[wet_bool].max() <= 0.1,
                  "%s wet S in reader guard [-0.002,0.1]" % base,
                  "%.6f..%.6f" % (s[wet_bool].min(), s[wet_bool].max()))
            dry = ~wet_bool
            dry_t_zero = bool(np.all(t[dry] == 0.0) and np.all(s[dry] == 0.0))
            if strict:
                check(dry_t_zero, "%s land/below-bottom == 0.0 (never NaN)" % base)
            else:
                info("land/below-bottom == 0.0: %s -> %s "
                     "(bilinear producer signature; reader ignores dry cells; "
                     "documented stage11.4 §11)"
                     % (base, "yes" if dry_t_zero else "NO (nonzero pre-fill)"))

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

        if "density_anomaly_gcm3" in ds.variables:
            ro = np.asarray(ds.variables["density_anomaly_gcm3"][:], dtype=np.float64)
            check(bool(np.isfinite(ro).all()), "%s density_anomaly finite" % base)
            print("density_anomaly_gcm3: min=%.6g max=%.6g negatives=%d"
                  % (ro.min(), ro.max(), int((ro < 0).sum())))


def main():
    print("Stage 11.7E.2 — EN4 ocean-initial contract verification")
    for rel, strict in FILES:
        verify(os.path.join(PROJECT, rel), strict)
    print("=" * 72)
    print("TOTAL CHECKS: %d ERRORS: %d INFO: %d" % (CHECKS, ERRORS, INFOS))
    print("=" * 72)
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
