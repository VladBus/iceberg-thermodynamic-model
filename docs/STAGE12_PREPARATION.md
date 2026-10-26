# Stage 12 Preparation

**Status:** PREPARATION ONLY — Stage 12 implementation has **NOT** started.
**Date:** 2026-10-26
**Base:** `531bbfa` (Stage 11 closed)

## Objective

Implement a voxel-based iceberg thermodynamics model integrated with the
Stage 11 ocean model. The target is a thermally resolved iceberg body with
per-voxel temperature and ice fraction, coupled to the validated ocean,
atmosphere, and drift dynamics.

## Prerequisites (COMPLETED)

- Ocean stabilization (Stage 11; T3-CORRECTIVE chain)
- EOS-80 validation and runtime default (D-29/D-47/D-48)
- Forcing validation (T4–T6; wind rotation, longitude clamp, snowfall)
- 8/8 N=1 seasonal matrix PASS and bit-identical reproducibility
- Stage 11 closure declaration and final review

## Reference review

Available:
- `docs/references/Iceberg/Iceberg_Voxel_Thermal_Model_8.pdf` (32 pages) —
  full voxel thermal specification. It defines a regular cubic voxel grid
  with per-voxel temperature `T` and remaining-ice fraction `φ`; finite-volume
  conduction through shared ice faces; Stefan/three-equation ice-water
  boundary fluxes; air-surface heat balance; geometric erosion and voxel
  removal (`φ_min`); hydrostatic waterline; and a drift-dynamics interface.
- `docs/references/Dmitriev_model/` — original model/reference texts.

Not available:
- `Iceberg_1.docx`
- `Iceberg_Voxel_Thermal_Model.docx`

**Important:** the PDF is a model specification, not an observational
validation. Its own limitations include calibration needs for turbulent
coefficients, cavity exchange, spray/waterline zone, and no coupled
ocean/atmosphere feedback in the thermal formulation.

## Key tasks (tentative)

1. Review the voxel specification and freeze the numerical design:
   grid resolution `h`, time step, explicit/stable conduction limit,
   boundary-flux and phase-change treatment.
2. Design the iceberg↔ocean coupling interface: per-face depth, ocean
   `T/S/u/v`, freezing point, and the existing Stage 11 forcing contract.
3. Implement voxel thermodynamics: conduction, ice–water Stefan/three-equation
   flux, ice–air surface balance, per-voxel `T/φ` update.
4. Implement geometric erosion and hydrostatic waterline/voxel removal.
5. Integrate the existing Lagrangian drift module with voxel-derived mass,
   draft, areas, and added-mass/drag diagnostics.
6. Design conservation/energy budgets and voxel-level diagnostics.
7. Validate against the available observational constraints; do not claim
   production calibration without data.
8. Decide whether the initial Stage 12 coupling is one-way (prescribed ocean)
   or two-way; two-way coupling requires a dedicated approved stage.

## Estimated effort

| Work package | Estimate |
|---|---|
| Literature/specification review | 1–2 weeks |
| Numerical/interface design | 1–2 weeks |
| Implementation | 4–8 weeks |
| Validation and diagnostics | 2–4 weeks |
| **Total** | **8–16 weeks** |

## Dependencies

- Stage 11 ocean model and forcing (COMPLETED)
- Voxel model specification (PDF available; DOCX absent)
- Observational data for validation (availability to be assessed)
- Explicit approval before any two-way coupling or production default change

## Guardrails

- Do not change Stage 11 EOS/scheduler/physics defaults during Stage 12
  preparation.
- Keep Stage 12 implementation behind a dedicated switch/branch.
- Preserve the Stage 11 closure baselines and reproducibility evidence.
- Do not claim voxel validation before a documented observational comparison.

## Next action

Stage 12 planning/literature review only. **No implementation has started.**
