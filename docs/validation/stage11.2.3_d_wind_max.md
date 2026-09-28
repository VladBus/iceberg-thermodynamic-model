# 11.2.3 D — `wind_max` Definition (Source-Traced)

Status: Source traced (`main.f90` lines 1456-1507). Physical definition established. Not an ocean-current variable — atmospheric forcing diagnostic only.

Source definition (`app/main.f90`):
- Declaration: `real :: wind_max` (line 1456)
- Initialization: `wind_max = 0.0` (line 1468)
- Computation: `max(wind_max, wind(iw, jw))` over wet cells (line 1479)
- Source field: `wind(iw,jw)` = ERA5 10m wind (u10/v10) in cm/s (CGS)
- CSV export: `diag_unit = 82` format includes `wind_max` (line 1506)

Physical meaning: maximum atmospheric wind speed over ocean domain per model day; NOT ocean velocity (`U2`/`V2`); NOT thermal wind; NOT combined metric.
