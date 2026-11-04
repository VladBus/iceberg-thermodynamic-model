# T5-CORRECTIVE-3 — Reference Findings

**Date:** 2026-10-25
**Sources:** `docs/references/Dmitriev_1995.txt`,
`docs/references/Nesterov_last.txt`, `docs/references/model_all.txt`.
`Iceberg_1.docx` and `Iceberg_Voxel_Thermal_Model.docx` are **absent** from the
workspace.

## Original advection scheme

`Nesterov_last.txt` (`module advs1`, lines 206–367) implements:

1. first-order **upwind** horizontal predictor (`CDX`, `CDY`);
2. anti-diffusive fluxes (`APX`, `APY`, `APZ`);
3. **Zalesak/FCT limiter** (`AMAX1(0., AMIN1(ABS(A), B*A1, B*B1))`);
4. corrected update `S2 = CD`.

`model_all.txt` contains the same `advS/advT` structure. The scheme is therefore
already **FCT with a Zalesak monotone limiter**, not central differences.
The current `src/advection_3d_s.f90` is the same FCT/Zalesak implementation
(T-29 fixed its boundary writeback). A separate Sweby limiter would duplicate
the existing monotone limiter; the new switch adds the explicit hard
positivity/no-new-extrema safety net instead.

## Original boundary treatment

`Nesterov_last.txt` "BOUNDARY CONDITIONS" (around line 2291) applies
no-gradient copies:

```
U2(:,1,:)=U2(:,2,:); V2(:,1,:)=V2(:,2,:)
U2(:,JS1,:)=U2(:,JS,:); V2(:,JS1,:)=V2(:,JS,:)
U2(1,:,:)=U2(2,:,:); V2(1,:,:)=V2(2,:,:)
```

There is no radiation condition, sponge, or characteristic boundary in the
original sources. The current clamped-η/no-gradient boundary is the legacy
behaviour; boundary reflection is an inherited limitation.

## Storm guidance

No storm-specific switch, storm-safe Δt, or boundary-sponge mechanism is
present in the reference sources. There is no documented guidance for extreme
forcing.
