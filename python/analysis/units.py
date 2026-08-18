"""Central unit-conversion helpers for the AARI iceberg model (Stage 5.5b).

The external NetCDF interface uses canonical SI units (written by
``src/netcdf_output.f90`` at the output boundary only; internal model state
remains CGS/Celsius):

  temperature / air_temp : K          (internal degC)
  u/v/w velocity, wind   : m s-1      (internal cm s-1)
  tau (stress)           : Pa         (internal dyn cm-2, 1 dyn/cm2 = 0.1 Pa)
  dp (pressure gradient) : Pa m-1     (internal hPa km-1, 1 hPa/km = 0.1 Pa/m)
  air_press              : Pa         (internal hPa)
  density_anomaly        : kg m-3     (internal g cm-3, anomaly rho-1.02 g/cm3)
  salinity_mass_fraction : 1 (kg/kg)  (NOT PSU)
  humidity / cloud       : 1
  era5_snowfall_rate     : m s-1 (water equivalent)

All presentation-side conversions live here so analysis/plotting scripts never
hard-code conversion factors.
"""

import numpy as np

ZERO_C_K = 273.15


def temperature_k_to_c(t_k):
    """K -> degC."""
    return np.asarray(t_k, dtype=np.float64) - ZERO_C_K


def temperature_c_to_k(t_c):
    """degC -> K."""
    return np.asarray(t_c, dtype=np.float64) + ZERO_C_K


def velocity_mps_to_cmps(v):
    """m s-1 -> cm s-1."""
    return np.asarray(v, dtype=np.float64) * 100.0


def velocity_cmps_to_mps(v):
    """cm s-1 -> m s-1."""
    return np.asarray(v, dtype=np.float64) * 0.01


def stress_pa_to_dyncm2(tau):
    """Pa -> dyn cm-2."""
    return np.asarray(tau, dtype=np.float64) * 10.0


def stress_dyncm2_to_pa(tau):
    """dyn cm-2 -> Pa."""
    return np.asarray(tau, dtype=np.float64) * 0.1


def dp_pam_to_hpakm(dp):
    """Pa m-1 -> hPa km-1."""
    return np.asarray(dp, dtype=np.float64) * 10.0


def dp_hpakm_to_pam(dp):
    """hPa km-1 -> Pa m-1."""
    return np.asarray(dp, dtype=np.float64) * 0.1


def pressure_pa_to_hpa(p):
    """Pa -> hPa."""
    return np.asarray(p, dtype=np.float64) * 0.01


def pressure_hpa_to_pa(p):
    """hPa -> Pa."""
    return np.asarray(p, dtype=np.float64) * 100.0


def density_anomaly_kgm3_to_gcm3(ro):
    """kg m-3 -> g cm-3 (still the anomaly rho-1.02 g/cm3)."""
    return np.asarray(ro, dtype=np.float64) * 0.001


def density_anomaly_gcm3_to_kgm3(ro):
    """g cm-3 -> kg m-3 (still the anomaly rho-1.02 g/cm3)."""
    return np.asarray(ro, dtype=np.float64) * 1000.0


def salinity_mass_fraction_to_gkg(s):
    """mass fraction (kg/kg) -> g/kg presentation."""
    return np.asarray(s, dtype=np.float64) * 1000.0