"""Stage 10.8.1 independent Python validation layer.

Pure Python re-implementation of the production iceberg basal-melt
formulation for independent cross-validation. See ``basal_melt.py``.
"""

from .basal_melt import (
    MELT_RATE_MIN,
    PRANDTL_NUMBER,
    REYNOLDS_CRITICAL,
    RHO_ICE,
    RHO_WATER,
    EOS_FP_A0,
    EOS_FP_A1,
    EOS_FP_A2,
    EOS_FP_BP,
    GRAVITY,
    LATENT_HEAT,
    KINEMATIC_VISCOSITY,
    THERMAL_CONDUCTIVITY,
    basal_melt_rate,
    ocean_freezing_point,
    ocean_heat_transfer_coefficient,
    nusselt_number,
    relative_velocity,
    reynolds_number,
    thermal_driving,
)

__all__ = [
    "MELT_RATE_MIN",
    "PRANDTL_NUMBER",
    "REYNOLDS_CRITICAL",
    "RHO_ICE",
    "RHO_WATER",
    "EOS_FP_A0",
    "EOS_FP_A1",
    "EOS_FP_A2",
    "EOS_FP_BP",
    "GRAVITY",
    "LATENT_HEAT",
    "KINEMATIC_VISCOSITY",
    "THERMAL_CONDUCTIVITY",
    "basal_melt_rate",
    "ocean_freezing_point",
    "ocean_heat_transfer_coefficient",
    "nusselt_number",
    "relative_velocity",
    "reynolds_number",
    "thermal_driving",
]