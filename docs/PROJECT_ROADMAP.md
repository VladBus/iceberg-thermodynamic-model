# PROJECT ROADMAP — Iceberg Thermodynamic Model

**Last Updated:** 2026-09-07  
**Current Stage:** Stage 10.3 Complete — Modern Turbulent Heat & Moisture Exchange  
**Repository Baseline:** a1fc859 "Correct Stage 10.2 analytical validation" + Stage 10.3 changes

---

## PHASE I — ICEBERG MODEL COMPLETION

Complete the iceberg model scientifically before expanding scope.

### Stage 10.1 — Solar Radiation
| Substage | Status | Description |
|----------|--------|-------------|
| 10.1.1 | ✅ DONE | Astronomical solar geometry (Spencer 1971) |
| 10.1.2 | ✅ DONE | Atmospheric attenuation/cloud parameterization |

### Stage 10.2 — Prognostic Surface Temperature
| Substage | Status | Description |
|----------|--------|-------------|
| 10.2 | ✅ DONE | C_eff·dT/dt = Q_net_non_melt with phase change at T_melt=0°C |

### Stage 10.3 — Modern Turbulent Heat & Moisture Exchange
| Substage | Status | Description |
|----------|--------|-------------|
| 10.3 | ✅ DONE | Neutral bulk SH/LH with C_H=C_E=1.5e-3, ice saturation, L_s=2.835e6 J/kg |

### Stage 10.4 — Phase Change & Surface Ablation
| Substage | Status | Description |
|----------|--------|-------------|
| 10.4 | ⬜ TODO | Partition Q_net_non_melt into melt/sublimation/deposition mass fluxes |

### Stage 10.5 — Ocean Thermal Forcing
| Substage | Status | Description |
|----------|--------|-------------|
| 10.5 | ⬜ TODO | Modern basal/lateral melt with physics-based coefficients |

### Stage 10.6 — Basal Melt Modernization
| Substage | Status | Description |
|----------|--------|-------------|
| 10.6 | ⬜ TODO | Replace C_BASAL with three-equation or Stanton-based parameterization |

### Stage 10.7 — Lateral Melt Modernization
| Substage | Status | Description |
|----------|--------|-------------|
| 10.7 | ⬜ TODO | Replace C_LATERAL with physics-based parameterization |

### Stage 10.8 — Integrated Thermodynamic Coupling
| Substage | Status | Description |
|----------|--------|-------------|
| 10.8 | ⬜ TODO | Exact timestep operation order, energy/mass conservation |

### Stage 10.9 — Integrated Physical Validation
| Substage | Status | Description |
|----------|--------|-------------|
| 10.9 | ⬜ TODO | Complete validation matrix (Table in stage10_modernization_plan.md) |

**Goal:** Self-consistent, traceable, independently tested iceberg model.

---

## PHASE II — COMPLETE / STABILIZE THE GENERAL OCEAN-SEA-ICE MODEL

After the iceberg subsystem is scientifically stable:

- Return to the general ocean/sea-ice model
- Resolve known initialization incompatibilities
- Address EN4-driven dynamics
- Investigate numerical stability systematically
- Reproduce previous failure/blow-up cases
- Identify root causes rather than masking symptoms
- Document every stability mechanism
- Preserve known protective guards until scientifically reviewed

### Known Historical Issues (Must Remain Visible)

| Issue | Description | Status |
|-------|-------------|--------|
| Convective adjustment / float32 threshold | EOS quantization 2^-23 ≈ 1.19e-7 vs threshold 0.9e-7 | Documented, monitored |
| FCT anti-diffusion instability | CDY*0 in barotropic_dynamics — enabling causes blowup | Guard in place |
| Ice-ocean drag singularity | hht ~ 0.01m causes positive feedback | Guard hht<0.01 → u=v=0 |
| Thomas vertical-viscosity matrix conditioning | Reaches 8.5e5 cm²/s at k=2 with realistic EN4 init | Do not "fix" without physics review |
| Realistic EN4 init vs zero velocity | Dynamically incompatible | Requires 3D geostrophic init (Stage 7.8+) |
| Previous model blow-ups | Stage 7.7B: U_max ~ 5740 m/s by Day 2 | Root cause: barotropic adjustment |

---

## PHASE III — MODEL DIAGNOSTICS AND VISUALIZATION

Once the model is scientifically stable:

Build a serious post-processing and visualization layer.

### Targets
- Publication-quality maps (iceberg trajectories, T/S fields, sea-ice)
- Iceberg trajectories and velocity fields
- Temperature/salinity cross-sections and vertical profiles
- Forcing fields (ERA5, EN4, IBCAO)
- Melt-rate maps and time series
- Animation frames (GIF/MP4)
- Side-by-side diagnostics
- Automated figures from reproducible run manifests

### Infrastructure
- Prefer existing Python infrastructure (`python/analysis/`)
- Do not pollute Fortran model with visualization logic
- Use run manifests (`python/analysis/run_manifest.py`) for reproducibility

---

## PHASE IV — COMPLETE MATHEMATICAL / PHYSICAL TUTORIAL

After equations and implementation stabilize:

Create a complete LaTeX tutorial/documentation of the model.

### Required Sections
1. Physical problem definition
2. Coordinate systems
3. Grid
4. Ocean equations
5. Sea-ice equations
6. Thermodynamics
7. Iceberg geometry
8. Iceberg momentum equations
9. Wind/water drag
10. Coriolis
11. ERA5 forcing
12. EN4 forcing
13. Bathymetry
14. Solar geometry
15. Radiation
16. Turbulent heat/moisture exchange
17. Surface temperature
18. Melting
19. Sublimation/deposition
20. Numerical schemes
21. Boundary conditions
22. Initial conditions
23. Stability limitations
24. Validation tests
25. Complete variable/units table
26. References

**Requirement:** LaTeX document generated from actual implemented model, not idealized description.

---

## PHASE V — LONG RUN / SCIENTIFIC EXPERIMENT

After model stabilization and reproducible diagnostics:

Perform a long realistic experiment, initially targeting approximately one year.

### Define
- Forcing period
- Initial conditions
- Iceberg population/scenarios
- Output frequency
- Diagnostics
- Restart strategy
- Quality-control checks

### Analyze
- Iceberg trajectories and velocity
- Dimensions and mass/volume evolution
- Basal/lateral/surface melt rates
- Sublimation/deposition
- Atmospheric/ocean forcing
- Seasonal cycle
- Spatial distributions
- Energy/mass budgets
- Numerical stability

### Produce
- Reproducible run manifest
- Publication-quality figures
- Animations
- Statistical analysis
- Scientific interpretation

**Distinction:** Engineering milestone ≠ Scientific validation milestone

---

## ROADMAP MAINTENANCE RULES

This roadmap is a living document. Update it when:
- A milestone is completed
- A new major blocker is discovered
- The architecture changes
- A long-term dependency becomes clear

**Single source of truth:** `docs/PROJECT_ROADMAP.md`

Do not create multiple competing roadmaps.

---

## CURRENT COMMIT STATE

| Commit | Description |
|--------|-------------|
| a1fc859 | Correct Stage 10.2 analytical validation |
| (Stage 10.3) | Modern turbulent heat & moisture exchange |

### Files Changed in Stage 10.3
- `src/iceberg_types.f90` — Modern constants (CP_AIR, L_S, C_H_NEUTRAL, C_E_NEUTRAL, Murphy-Koop)
- `src/iceberg_thermodynamics.f90` — Modern bulk SH/LH in compute_surface_melt
- `test/iceberg_test_surface_melt_audit.f90` — 9 new Stage 10.3 analytical tests
- `docs/model/model_equation_ledger.md` — Updated SH/LH equations
- `docs/model/model_physics_status.md` — Sensible/latent heat status C
- `docs/model/stage10_modernization_plan.md` — Stage 10.3 marked complete
- `AGENTS.md` — Stage 10.3 facts recorded

### Tests (All PASS)
- 41/41 fpm tests PASS
- `iceberg_test_surface_melt_audit` (26 checks)
- `iceberg_test_solar_radiation_geometry`
- `iceberg_test_surface_energy_balance`
- `iceberg_test_11_30day_offline`
- All regression tests

### Key Constants (Stage 10.3)
| Constant | Value | Source |
|----------|-------|--------|
| CP_AIR | 1004.0 J/(kg·K) | Standard |
| L_S | 2.835e6 J/kg | Sublimation at 0°C |
| C_H_NEUTRAL | 1.5e-3 | Andreas et al. 2010, Arctic sea ice |
| C_E_NEUTRAL | 1.5e-3 | Same as C_H |
| MURPHY_KOOP A-D | 9.550426, 5723.265, 3.53068, 0.00728332 | Murphy & Koop (2005) |

### Remaining Limitations
- Neutral bulk only (no stability correction)
- Q_LH = energy flux only (no mass change)
- L_s fixed (no T-dependence)
- No calibration against TEST_11

---

## NEXT PRIORITIES

1. **Stage 10.4** — Phase change partitioning (sublimation/deposition mass fluxes)
2. **Stage 10.5** — Ocean thermal forcing modernization
3. **Documentation** — Wiki page for Stage 10.3 audit
