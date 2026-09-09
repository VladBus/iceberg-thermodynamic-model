# Статус физических блоков модели

**Дата:** 2026-09-10
**Current repository stage:** Stage 10.7 — Independent Basal Melt Validation Complete
**Production baseline:** Stage 10.6.1 (unchanged; 10.7 added audit only)
**FPM test targets:** 51
**Local status:** 51/51 PASS; strict build clean; `git diff --check` clean
**Stage 10.7 report:** `docs/validation/stage10.7_basal_melt_validation.md`

## Классификация

| Код | Значение |
|---|---|
| **A** | Физика/реализация подтверждена для текущего scope; изменений не требуется |
| **B** | Рабочее приближение с научными ограничениями; требуется дальнейшая валидация или модернизация |
| **C** | Современная физическая формулировка уже реализована и прошла текущий аудит |
| **D** | Устаревшая/ошибочная формулировка, подлежащая удалению |
| **E** | Запланированная новая физика |

## Текущий статус

| Блок | Current formulation | Status |
|---|---|---:|
| Geometry | Rectangular prism; prognostic L/W/H | A |
| Position | Prognostic x/y; diagnostic lat/lon; moving forcing by x/y | A/B |
| Dynamics | Wind drag, water drag, Coriolis, pressure gradient | B |
| Real grid | IBCAO V5.2-derived 133×105 grid; 132×104 active; DX=DY=13.89 km | A |
| ERA5 forcing | u10/v10/t2m/d2m/tcc/msl/snowfall; spatial interpolation | B |
| EN4 forcing | Temperature/salinity profiles with draft interpolation/extrapolation | B |
| Sea-ice initialization | OSI-SAF SIC + C3S CS2SMOS SIT, 2020-01-01 | B |
| Solar geometry | Astronomical declination/EOT approximation following Spencer 1971 | C |
| Shortwave attenuation | Rayleigh + water vapour + aerosol + cloud parameterization | B |
| Sensible heat | Neutral bulk transfer, fixed coefficient | C/B |
| Latent heat | Neutral bulk transfer + ice saturation from Murphy & Koop 2005 | C/B |
| Surface temperature | Prognostic T_surface with finite effective heat capacity | B |
| Phase change | Explicit melt/sublimation/deposition partition and latent heat | B |
| Freezing point | EOS-80/UNESCO pressure-dependent freezing-point equation | C |
| Ocean heat transfer | Relative flow; laminar/turbulent flat-plate Nu correlation | B |
| Basal melt | `m_basal = gamma_T * max(T-Tf,0)/(rho_ice*Lf)` (independently audited in Stage 10.7) | B |
| Lateral melt | Depth-averaged thermal forcing; legacy/approximate closure | B |
| Three-equation interface | Not implemented | E |
| Full seawater EOS | Not implemented; freezing point only | E |
| TEOS-10 | Not implemented | E |
| Natural convection | Not represented in current ocean heat-transfer closure | E |
| Independent observational validation | Not yet complete for the coupled trajectory | E |

## Stage 10.6 ocean-side heat transfer

For relative speed `U_rel`, the implementation computes

`Re = U_rel * L_char / nu`

and selects the canonical flat-plate branch:

- `Re < 5e5`: `Nu = 0.664 Re^0.5 Pr^(1/3)`;
- `Re >= 5e5`: `Nu = 0.037 Re^0.8 Pr^(1/3)`;
- `gamma_T = Nu*k/L_char`.

The expanded length exponents are therefore `L_char^(-0.5)` and `L_char^(-0.2)`, respectively. The production code uses `L_char = L` as a pragmatic characteristic length because iceberg orientation is not prognosed.

This is a **flat-plate forced-convection approximation**, not a geometry-specific iceberg derivation. At `U_rel = 0`, forced-convection transfer is zero; natural convection is not included. Weeks & Campbell (1973) and FitzMaurice & Stern (2018) are retained as comparison/validation literature and are not used to claim that the flat-plate correlation is uniquely correct for icebergs.

## Key accepted limitations

1. The current iceberg has no orientation, so the streamwise characteristic length is approximated by `L`.
2. The heat-transfer correlation is inherited from canonical boundary-layer theory rather than derived specifically for a rectangular iceberg.
3. Natural convection is absent at zero relative flow.
4. Lateral melt remains an approximate legacy closure and does not yet use the full three-equation ice-ocean interface formulation.
5. The EOS-80 implementation computes freezing point only; it is not a full EOS-80/TEOS-10 density equation of state.
6. Some shortwave attenuation constants require stronger literature provenance/sensitivity documentation.
7. Independent observational validation of the full coupled thermodynamic evolution remains a future task.
8. Stored iceberg latitude/longitude are not currently updated from x/y during time stepping.

## Verification policy

Internal tests establish implementation and conservation identities. They do not establish observational validity. Each future physical modernization must provide: literature basis, equation/parameter provenance, independent analytical tests, regression tests, and an external validation target where applicable.

## References

See `docs/references/references.bib` and `docs/references/literature_matrix.md`. The private `work_references.bib` is a PDF-location aid and is intentionally not committed.