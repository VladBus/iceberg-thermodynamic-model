# T5-CORRECTIVE-2 — Literature Review (advection/boundary instability)

**Scope:** potential fixes for the diagnosed `ADVECTION_ERROR` (salinity
positivity/negative density) with `BOUNDARY_REFLECTION` amplification.

## Diagnosis summary

The failure is not a CA-mixing spike: CA nmix remains ~3.0–3.4e5/day (baseline
range), while salinity first becomes negative at day 46 and reaches
−9,859 PSU by day 65; RO becomes negative from day 29. T/S corruption starts
at the surface near the boundary and then spreads. Stronger Δt/Ah only delays
the collapse.

## Established remedies

1. **Monotone/positive advection limiters.** FCT (Zalesak 1979) and
   monotone/sweby schemes (Smolarkiewicz & Grabowski 1990) constrain
   advective fluxes so tracers cannot undershoot; the present model's FCT
   anti-diffusion is intentionally disabled (T-02), which is the first
   suspect for negative salinity.
2. **Salinity positivity / conservative clipping.** A conservative,
   flux-based limiter (rather than an arbitrary floor) can preserve the
   global salt integral while preventing negative values. This requires a
   physics/numerics decision and is not implemented here.
3. **Open-boundary radiation/sponge.** Marchesiello, McWilliams &
   Shchepetkin (2001) and Chapman (1985) describe radiation conditions and
   sponge layers for regional ocean models; the present three-edge clamped η
   boundary reflects storm energy. A sponge alone only masks the boundary
   peak (T5-CORRECTIVE evidence).
4. **CA sub-cycling / implicit CA.** If CA inversions grow because of
   corrupted T/S, sub-cycling or an implicit CA may help the symptom, but the
   diagnostic shows CA is not the primary trigger; it should be secondary to
   the advection fix.
5. **Adaptive dissipation.** Increasing Ah (20000→50000) only delayed the
   first NaN by days; adaptive/storm-aware dissipation alone is insufficient.

## Recommendation

Prioritize **T5-CORRECTIVE-3: monotone/positive salinity advection and
boundary treatment**, with CA sub-cycling as a secondary check. Do not
promote stronger Ah as the fix. These are potential fixes only; none was
implemented in this diagnostic stage.
