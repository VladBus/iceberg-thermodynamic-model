# Статус физических блоков модели

**Дата:** 2026-09-13
**Current repository stage:** Stage 10.11.3 — Deep Audit & Sensitivity of Natural-Convection Basal Melt
**Production baseline:** Stage 10.11 (three-equation + natural convection; unchanged by 10.11.3)
**FPM test targets:** 53
**Local status:** 53/53 PASS; strict build clean; `git diff --check` clean
**Stage 10.7 report:** `docs/validation/stage10.7_basal_melt_validation.md`
**Stage 10.8.1 report:** `docs/validation/stage10.8.1_python_validation.md`
**Stage 10.8.2 report:** `docs/validation/stage10.8.2_observational_validation.md`
**Stage 10.9 report:** `docs/validation/stage10.9_calibration_assessment.md`
**Stage 10.10 report:** `docs/validation/stage10.10_three_equation_interface.md`
**Stage 10.11.3 report:** `docs/validation/stage10.11.3_natural_convection_physics_audit.md`
**Stage 10.10.1 report:** `docs/validation/stage10.10.1_three_equation_interface.md`
**Stage 10.11 report:** `docs/validation/stage10.11_natural_convection.md`

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
| Basal melt | `m_basal = gamma_T * max(T-Tf,0)/(rho_ice*Lf)` (independently audited in Stage 10.7; independent Python layer in `python/validation/`, Stage 10.8.1; observational validation vs published melts, Stage 10.8.2; Stage 10.9: scalar coefficient **not identifiable** across the 10.8.2 sources — no calibration made) | B |
| Lateral melt | Depth-averaged thermal forcing; legacy/approximate closure | B |
| Three-equation interface | H&J99/J2010 closure; velocity-scale gamma_T=K_T·U, gamma_S=K_S·U (K_T=1.1e-3, K_S=3.1e-5); Eq. III corrected: `rho_w gamma_S (S_w - S_B) = rho_i m S_B` with `rho_i/rho_w = 910/1028` (Stage 10.10.1); separately selectable; conduction to T_i=-10 (model-selected constant, NOT from H&J99); independently validated (Fortran 25 + Python 65 checks, cross-language contract) | C |
| Natural convection | Horizontal-plate correlation (operative turbulent `0.15·Ra^(1/3)` from Lloyd & Moran 1974, NOT Fujii 1973) + Churchill 1977 mixing; double-diffusive Ra with thermal/haline buoyancy; L_char = iceberg length L (correlation scale is A/p); Ra cap 1e10; gamma_T_nat, gamma_S_nat added to forced convection via Churchill n=3 mixing; separately selectable as THREE_EQUATION_NATURAL; independently validated (Fortran 23 + Python 70 checks). **Stage 10.11.3 audit (B):** cap always active (uncapped Ra=5.7e19) → Nu pinned at 323.17, haline/Le term numerically inert, beta_T/beta_S inert, laminar branch latent; zero-flow m=1.4e-3 m/day is 7-700x BELOW the observed quiescent band (does NOT close the 10.8.2 gap); haline sign is opposite to the physical stabilizing role; coefficient attribution corrected; real mechanism is double-diffusive (Martin & Kauffman 1977; Keitzl et al. 2016; Middleton et al. 2021). Production physics UNCHANGED | B |
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
4. Lateral melt remains an approximate legacy closure and does not yet use the full three-equation ice-ocean interface formulation (the three-equation closure is implemented for the basal path; Stage 10.10).
5. The EOS-80 implementation computes freezing point only; it is not a full EOS-80/TEOS-10 density equation of state.
6. Some shortwave attenuation constants require stronger literature provenance/sensitivity documentation.
7. Independent observational validation of the full coupled thermodynamic evolution remains a future task.
8. Stored iceberg latitude/longitude are not currently updated from x/y during time stepping.
10. Three-equation closure (Stage 10.10/10.10.1) uses a constant internal ice temperature `T_i = -10` in the conduction term of Eq. II; this is a model-selected constant internal temperature, NOT from H&J99 (H&J99 solve conduction explicitly); physically consistent conduction requires internal thermal evolution (a future stage). Eq. III salt balance was corrected in Stage 10.10.1 from `gamma_S (S_w - S_B) = m S_B` to `rho_w gamma_S (S_w - S_B) = rho_i m S_B` (MOM6/PISM/MITgcm/H&J99 Eq.4 convention). Natural convection remains absent at zero relative flow as in the bulk closure. The `K_T`/`K_S` convention is U-based (Jenkins et al. 2010 Table 2) rather than a melt-driven `u*`-based Stanton; see `docs/validation/stage10.10_three_equation_interface.md` (superseded) and `docs/validation/stage10.10.1_three_equation_interface.md`.
11. Natural convection (Stage 10.11; audited in Stage 10.11.3, classification B). The closure uses a horizontal-plate correlation with a double-diffusive Rayleigh number and Churchill (1977) mixed-convection mixing. Stage 10.11.3 audit findings: (a) the operative turbulent coefficient `0.15*Ra^(1/3)` is from Lloyd & Moran (1974), not Fujii et al. (1973) (which is a theoretical laminar uniform-heat-flux study with `Nu ~ Ra^(1/5)`); (b) the Rayleigh cap `1e10` is ALWAYS active for realistic bergs (uncapped anchor `Ra=5.7e19`), so `Nu` is pinned at 323.17 and the laminar branch/transition (`Ra=1e7`, 113% discontinuity) are latent; (c) in the capped regime the haline term (including `Le=100`) and the values of `beta_T`/`beta_S` are numerically inert (dropping the haline term reproduces the same `m`); (d) the haline term is carried with a positive sign although meltwater freshening is gravitationally stabilizing — the physical minus sign gives `Ra<0 -> Nu=0 -> m=0`; (e) the characteristic length is `state%L`, whereas the source correlations use `L* = A/p`; (f) zero-flow melt is `m = 1.4e-3 m/day`, **7-700x below** the observed quiescent band 0.01-1 m/day, so Stage 10.11 did NOT close the 10.8.2 gap (the earlier "consistent with 0.01-1 m/day" claim was incorrect and is removed); (g) the real mechanism is double-diffusive / diffusion-limited convection (Martin & Kauffman 1977; Keitzl et al. 2016; Middleton et al. 2021), which the closure does not represent. Gayen et al. (2016) remains context only (vertical ice face). Production physics is unchanged by 10.11.3; the recommended follow-up is a future diffusion-limited low-flow parameterization. See `docs/validation/stage10.11.3_natural_convection_physics_audit.md`.

## Verification policy

Internal tests establish implementation and conservation identities. They do not establish observational validity. Each future physical modernization must provide: literature basis, equation/parameter provenance, independent analytical tests, regression tests, and an external validation target where applicable.

## References

See `docs/references/references.bib` and `docs/references/literature_matrix.md`. The private `work_references.bib` is a PDF-location aid and is intentionally not committed.