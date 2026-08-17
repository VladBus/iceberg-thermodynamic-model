"""Analysis of AARI model NetCDF output and Fortran daily diagnostics.

Modules
-------
diagnostics  : read daily model output, compute per-day summaries
statistics   : monthly statistics from daily summaries
profiles     : vertical profiles from 3D snapshots
generate_report : assemble monthly_summary.txt

Python does NOT perform model-grid interpolation, EOS, or any physical
model calculation - those belong to the Fortran model.
"""
