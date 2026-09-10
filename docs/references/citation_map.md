# Equation Citation Map

This file prevents literature references from being used more strongly than the source supports. A source listed as comparison is not automatically a derivation source for the production equation.

| Production component | Repository implementation | Citation key | Role |
|---|---|---|---|
| Solar declination / equation of time | `src/iceberg_thermodynamics.f90` | `spencerFourierSeriesPositionSun1971` | CORE |
| Ice saturation vapour pressure | `src/iceberg_thermodynamics.f90` | `murphyKoopReviewVapourPressures2005` | CORE |
| Seawater freezing point | `ocean_freezing_point` in `src/iceberg_types.f90` | `fofonoffMillardAlgorithmsFundamental1983` | CORE |
| Supporting oceanographic freezing-point reference | EOS-80 documentation | `gillAtmosphereOceanDynamics1982` | SUPPORT |
| Laminar flat-plate heat transfer | `ocean_heat_transfer_coeff` in `src/iceberg_types.f90` | `eckertDrakeHeatMassTransfer1959` | CORE, approximation |
| Turbulent flat-plate heat transfer | `ocean_heat_transfer_coeff` in `src/iceberg_types.f90` | `eckertDrakeHeatMassTransfer1959` | CORE, approximation |
| Empirical iceberg basal melt context | basal melt comparison | `weeksCampbellIcebergsFreshWater1973` | COMPARISON |
| Bulk melt-law basis (closed-form) | closed-form melt/draft basis | `biggModellingDynamicsThermodynamics1997` | COMPARISON |
| Tabular iceberg basal melt | validation/comparison literature | `fitzmauriceSternBasalMeltTabular2018` | COMPARISON/VALIDATION |
| Ice-ocean three-equation formulation | Eq. I-III closure + conduction term of `solve_three_equation_interface` (Stage 10.10/10.10.1); Eq. III corrected: `rho_w gamma_S (S_w - S_B) = rho_i m S_B` (Stage 10.10.1) | `hollandJenkinsThermodynamicIceOcean1999` | CORE, IMPLEMENTED (Stage 10.10/10.10.1) |
| Ice-shelf basal ablation / exchange | melt-driven Stanton anchor (St = 0.011) — different convention from the U-based `K_T` implemented in Stage 10.10 | `jenkinsNichollsCorrAblationRonne2010` | COMPARISON/FUTURE (convention) |
| MOM6 mom_ice_shelf salt budget | salt-budget convention `rho_w gamma_S (S_w - S_B) = rho_i m S_B` confirming Stage 10.10.1 | (Losch et al. 2019; Griffies et al.) | VALIDATION |
| PISM basal-melt salt flux | mass-flux convention `Q_S^B = rho_I S^B dh/dt` confirming Stage 10.10.1 | PISM documentation | VALIDATION |
| MITgcm shelfice salt flux | mass-flux form `rho_c gamma_S (S - S_b) = -q (S_b - S_I)` confirming Stage 10.10.1 | (Losch 2008 et seq.) | VALIDATION |
| Natural convection horizontal plate | Fujii et al. 1973 Nu-Ra correlations for downward-facing heated plate | `fujiiHondaMoriokaNaturalConvection1973` | CORE, IMPLEMENTED (Stage 10.11) |
| Melt-driven convection horizontal ice | LES of natural convection under horizontal ice (Gayen et al. 2016) | `gayenGriffithsKerrMeltDrivenConvection2016` | VALIDATION (supports L_char = D) |
| Churchill mixed convection | Comprehensive correlating equation for mixed convection | `churchillComprehensiveCorrelatingEquation1977` | CORE, IMPLEMENTED (Stage 10.11) |
| Turbulent exchange over sea ice/MIZ | atmospheric/ocean exchange context | `andreasHorstGrachevSummerSeaIce2010` | SUPPORT |
| Interactive iceberg freshwater flux | coupled modelling context | `martinAdcroftInteractiveIcebergs2010` | BACKGROUND/FUTURE |
| Observed iceberg submarine-melt band | validation band for basal melt (0.01–1 m/day) | `cenedeseIcebergsMelting2023` | VALIDATION |
| Lab submarine melt | observational dataset (Stage 10.8.2) | `russefl-headMELTINGFREEDRIFTINGICEBERGS` | VALIDATION |
| Lab melt-driven convection | context for lab plume/melt interpretation | `josbergerIcebergMeltDrivenConvection1980` | VALIDATION |
| Field submarine melt (Southern Ocean) | forcing-anchored field rate (KW84), 10.8.2 | `keysWilliamsFieldMeasurementsSubmarine1984` | VALIDATION |
| Antarctic sub-antarctic melt synthesis | synthesis curve NJ80, 10.8.2 | `neshybaEstimationAntarcticIceberg1980` | VALIDATION |
| Greenland fjord melt remotely sensed | inverse-U analysis rows, 10.8.2 | `enderinHamiltonIcebergSubmarineMelt2014` | VALIDATION |
| Greenland fjord meltwater fluxes | inverse-U analysis rows, 10.8.2 | `enderinIcebergMeltwaterFluxes2016` | VALIDATION |
| Antarctic iceberg melt synthesis (review) | rs-derived rows + context, 10.8.2 | `enderinAntarcticIcebergMeltRate2023` | VALIDATION |
| Giant-iceberg life expectancy | exclusion rationale; context only | `orheimPhysicalCharacteristicsLife1980` | CONTEXT |
| Calving-face melt rates | explicitly excluded (not submarine melt), 10.8.2; source discussed in `stage10.8.2_observational_validation.md` §1 | (Rignot et al. 2010 — not in bibliography) | CONTEXT/EXCLUDED |

## Important scope statements

### Ocean heat transfer

The implemented `Nu(Re,Pr)` expressions are canonical flat-plate correlations. The repository must describe their use for an iceberg as an approximation. They must not be cited as though Eckert & Drake derived an iceberg-specific melt law.

### Iceberg basal melt

Weeks & Campbell and FitzMaurice & Stern are relevant because they concern iceberg melt parameterizations/observations. They are comparison and validation sources for the current bulk formulation, not interchangeable derivations of the flat-plate correlation.

### Three-equation physics

Holland & Jenkins (1999) and Jenkins et al. (2010) provide the literature basis
for the Stage 10.10/10.10.1 three-equation interface, which is implemented
(`set_basal_melt_scheme(BASAL_MELT_SCHEME_THREE_EQUATION)` +
`solve_three_equation_interface` in `src/iceberg_thermodynamics.f90`) and
independently validated in the Stage 10.10 Fortran and Python test layers and
report (`docs/validation/stage10.10_three_equation_interface.md` superseded by
`stage10.10.1_three_equation_interface.md`). The implemented exchange
coefficients are the **U-based** J2010 Table 2 values
(`K_T = sqrt(C_d)*Gamma_T = 1.1e-3`, `K_S = sqrt(C_d)*Gamma_S = 3.1e-5`);
the melt-driven `u*`-based Stanton anchor St = 0.011 remains a documented
open convention question for calibration (Stage 10.9), not an implemented
choice. The salt balance (Eq. III) was corrected in Stage 10.10.1 from the
equal-density reduction `gamma_S (S_w - S_B) = m S_B` to the physically
consistent mass-conserving form `rho_w gamma_S (S_w - S_B) = rho_i m S_B`
(with `rho_i/rho_w = 910/1028 = 0.8852...`); this matches the MOM6
`mom_ice_shelf`, PISM, and MITgcm shelfice documented conventions, and the
Holland & Jenkins (1999) Eq. (4) brine salt flux. The bulk flat-plate closure
of Stage 10.6 remains the unchanged baseline for the non-selected paths.

### Stage 10.9 DOI verification

The roles above for Weeks & Campbell 1973, Bigg 1997, Holland & Jenkins 1999, Jenkins & Nicholls 2010, FitzMaurice & Stern 2018, Cenedese & Straneo 2023 and Martin & Adcroft 2010 were confirmed by Crossref bibliographic verification in Stage 10.9 (`docs/validation/stage10.9_calibration_assessment.md` §9). No new bibliography keys were added.

### Freezing point

Fofonoff & Millard (1983) is the primary EOS-80 freezing-point reference. The implementation uses pressure estimated from depth with a constant water density; therefore the citation supports the freezing-point polynomial, not a claim of a complete hydrostatic seawater EOS.

## Data citation policy

ERA5, EN4, IBCAO V5.2, OSI-SAF SIC CDR v3.1 and C3S CS2SMOS SIT L4 combined v1.1 are data-product dependencies. Their exact product/version citations should be recorded in experiment manifests and publication-facing documentation. A data-product citation must not be substituted by a generic scientific paper when reproducibility requires the actual dataset version.