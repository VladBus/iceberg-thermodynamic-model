"""Stage 6.2 §14: SI round-trip unit-conversion test.

Verifies that the canonical-SI <-> presentation-unit conversions in
``python/analysis/units.py`` are exact inverses within float64 tolerance.

For each physical field, the round trip

    SI -> presentation -> SI

must reproduce the original value to within float64 round-off (the external
NetCDF interface stays canonical SI; presentation units are only used in
analysis/plotting).

Run:
    conda run -n iceberg-thermodynamic-model \
        python -m pytest python/tests/test_units_roundtrip.py -v

(or: python python/tests/test_units_roundtrip.py)
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
import units  # noqa: E402

# Tolerance: 32x float64 machine epsilon (relative). All conversions are exact
# scalar multiplications/additions, so error is pure round-off.
RTOL = 32 * np.finfo(np.float64).eps

# (name, forward, inverse, representative SI values)
ROUND_TRIPS = [
    ("temperature K <-> degC", units.temperature_k_to_c, units.temperature_c_to_k,
     np.array([173.15, 253.15, 273.15, 293.15, 320.0])),
    ("velocity m/s <-> cm/s", units.velocity_mps_to_cmps, units.velocity_cmps_to_mps,
     np.array([0.0, 1e-3, 1.0, 25.0, 60.0])),
    ("stress Pa <-> dyn/cm2", units.stress_pa_to_dyncm2, units.stress_dyncm2_to_pa,
     np.array([0.0, 0.01, 0.1, 1.0, 5.0])),
    ("dp Pa/m <-> hPa/km", units.dp_pam_to_hpakm, units.dp_hpakm_to_pam,
     np.array([0.0, 1e-4, 1e-3, 0.1, 2.0])),
    ("pressure Pa <-> hPa", units.pressure_pa_to_hpa, units.pressure_hpa_to_pa,
     np.array([50000.0, 95000.0, 101325.0, 110000.0])),
    ("density_anomaly kg/m3 <-> g/cm3",
     units.density_anomaly_kgm3_to_gcm3, units.density_anomaly_gcm3_to_kgm3,
     np.array([-30.0, -1.0, 0.0, 0.5, 10.0])),
    ("salinity mass fraction -> g/kg (inverse = /1000)",
     units.salinity_mass_fraction_to_gkg,
     lambda gkg: np.asarray(gkg, dtype=np.float64) * 0.001,
     np.array([0.0, 0.025, 0.033, 0.035, 0.04])),
]


def test_round_trip_all():
    for name, fwd, inv, vals in ROUND_TRIPS:
        si = np.asarray(vals, dtype=np.float64)
        back = inv(fwd(si))
        np.testing.assert_allclose(
            back, si, rtol=RTOL, atol=0.0,
            err_msg=f"{name}: SI -> presentation -> SI failed",
        )


def test_temperature_offset_identity():
    """degC <-> K uses an offset; 273.15 K must map to 0 degC and back."""
    t_k = np.array([200.0, 273.15, 300.0])
    np.testing.assert_allclose(
        units.temperature_c_to_k(units.temperature_k_to_c(t_k)), t_k,
        rtol=RTOL, atol=0.0,
    )
    np.testing.assert_allclose(units.temperature_k_to_c(273.15), 0.0, atol=RTOL)


if __name__ == "__main__":
    test_round_trip_all()
    test_temperature_offset_identity()
    print("OK: all SI -> presentation -> SI round trips pass (float64 tolerance)")