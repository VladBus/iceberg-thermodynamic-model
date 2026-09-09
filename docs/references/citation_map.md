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
| Tabular iceberg basal melt | validation/comparison literature | `fitzmauriceSternBasalMeltTabular2018` | COMPARISON/VALIDATION |
| Ice-ocean three-equation formulation | future interface closure | `hollandJenkinsThermodynamicIceOcean1999` | FUTURE |
| Ice-shelf basal ablation / exchange | future comparison | `jenkinsNichollsCorrAblationRonne2010` | COMPARISON/FUTURE |
| Turbulent exchange over sea ice/MIZ | atmospheric/ocean exchange context | `andreasHorstGrachevSummerSeaIce2010` | SUPPORT |
| Interactive iceberg freshwater flux | coupled modelling context | `martinAdcroftInteractiveIcebergs2010` | BACKGROUND/FUTURE |

## Important scope statements

### Ocean heat transfer

The implemented `Nu(Re,Pr)` expressions are canonical flat-plate correlations. The repository must describe their use for an iceberg as an approximation. They must not be cited as though Eckert & Drake derived an iceberg-specific melt law.

### Iceberg basal melt

Weeks & Campbell and FitzMaurice & Stern are relevant because they concern iceberg melt parameterizations/observations. They are comparison and validation sources for the current bulk formulation, not interchangeable derivations of the flat-plate correlation.

### Three-equation physics

Holland & Jenkins (1999) and Jenkins et al. (2010) provide a literature basis for a future interface formulation. They are not evidence that the current Stage 10.6 closure already implements the three-equation boundary condition.

### Freezing point

Fofonoff & Millard (1983) is the primary EOS-80 freezing-point reference. The implementation uses pressure estimated from depth with a constant water density; therefore the citation supports the freezing-point polynomial, not a claim of a complete hydrostatic seawater EOS.

## Data citation policy

ERA5, EN4, IBCAO V5.2, OSI-SAF SIC CDR v3.1 and C3S CS2SMOS SIT L4 combined v1.1 are data-product dependencies. Their exact product/version citations should be recorded in experiment manifests and publication-facing documentation. A data-product citation must not be substituted by a generic scientific paper when reproducibility requires the actual dataset version.