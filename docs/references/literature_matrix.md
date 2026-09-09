# Literature-to-Model Matrix

**Scope:** current repository state through Stage 10.7 (independent basal-melt validation).

The matrix is deliberately selective: a Zotero record is not automatically a model reference. The role describes how a source is used or should be used in the scientific documentation.

## Role legend

| Role | Meaning |
|---|---|
| CORE | Direct basis for a production equation or physical parameterization |
| VALIDATION | Independent benchmark, observation, or validation methodology |
| COMPARISON | Alternative/legacy parameterization used for scientific comparison |
| DATA | External forcing or observational data product |
| BACKGROUND | Scientific context; not a direct equation source |
| FUTURE | Relevant to planned modernization, not current production physics |
| SOFTWARE | Numerical/modeling documentation |
| PERSONAL | User's publications or project-specific material |
| CHECK | Metadata/reference requires later verification before being cited as a core source |

## Direct Stage 10 references

| Source | Model component | Status |
|---|---|---|
| Spencer 1971 | Solar declination/equation-of-time approximation | CORE |
| Murphy & Koop 2005 | Saturation vapour pressure over ice | CORE |
| Fofonoff & Millard 1983 | EOS-80 freezing-point equation | CORE |
| Gill 1982 | Supporting seawater/oceanographic formulation | CORE/SUPPORT |
| Eckert & Drake 1959 | Laminar/turbulent flat-plate heat-transfer correlations | CORE, approximation |
| Weeks & Campbell 1973 | Empirical iceberg basal-melt context | COMPARISON |
| FitzMaurice & Stern 2018 | Tabular iceberg basal-melt parameterization comparison | VALIDATION/COMPARISON |
| Holland & Jenkins 1999 | Three-equation ice-ocean thermodynamics | FUTURE/COMPARISON |
| Jenkins, Nicholls & Corr 2010 | Ice-ocean turbulent exchange / basal ablation | COMPARISON |
| Andreas et al. 2010 | Air-sea/ice turbulent exchange context | SUPPORT |
| Martin & Adcroft 2010 | Interactive iceberg freshwater flux in climate modelling | BACKGROUND/FUTURE |
| Cenedese & Straneo 2023 | Iceberg melt review; observed submarine melt band ~0.01–1 m/day | VALIDATION |

## Existing iceberg literature in the collection

The curated bibliography already contains important iceberg references including Bigg et al. (1997), NEMO-ICB/Marsh et al. (2015), FitzMaurice, Cenedese & Straneo (2018), Cenedese & Straneo (2023), and regional Arctic iceberg studies. These should be used for literature review, comparison, and future validation rather than retroactively being treated as sources for equations they do not actually establish.

## Current physical blocks

| Block | Current implementation | Literature status | Scientific classification |
|---|---|---|---|
| Geometry | Rectangular prism, prognostic L/W/H | Standard geometry assumption; iceberg literature provides alternatives | A |
| Dynamics | Wind drag, water drag, Coriolis, pressure-gradient terms | Existing iceberg-dynamics literature in collection | B |
| Solar geometry | Spencer-type astronomical approximation | Spencer 1971 | C |
| Shortwave attenuation | Rayleigh + water vapour + aerosol + cloud parameterization | Current constants need explicit provenance review | B |
| Sensible/latent atmospheric fluxes | Neutral bulk transfer; Murphy & Koop saturation over ice | Murphy & Koop 2005; transfer coefficients require scope caveat | C/B |
| Surface temperature | Prognostic mixed-layer-like surface heat capacity | Model-derived numerical closure; independent physical validation still limited | B |
| Phase change | Melt, sublimation/deposition and latent-heat partition | Thermodynamic accounting implemented; external validation pending | B |
| Freezing point | EOS-80/UNESCO equation with pressure term | Fofonoff & Millard 1983; Gill 1982 | C |
| Basal ocean heat transfer | Re/Nu correlation with laminar/turbulent transition | Eckert & Drake 1959; iceberg applicability is an approximation | B (independently audited in Stage 10.7) |
| Lateral melt | Legacy depth-averaged formulation | FitzMaurice laboratory literature provides evidence for shear/nonlinearity | B |
| Three-equation interface physics | Not implemented | Holland & Jenkins 1999; Jenkins et al. 2010 | FUTURE |
| Full seawater EOS | Not implemented; freezing point only | EOS-80/TEOS-10 literature | FUTURE |

## Dataset provenance to document

- **ERA5:** atmospheric reanalysis; preserve product name, variables, spatial/temporal resolution, retrieval date and CDS dataset identifier.
- **EN4:** ocean temperature/salinity profiles; preserve release/version and processing date.
- **IBCAO V5.2:** 400 m bathymetry used to reconstruct the real model grid; preserve product version, source and CRS EPSG:3996.
- **OSI-SAF SIC CDR v3.1:** SSMIS, EASE2-North 25 km, used for 2020-01-01 sea-ice concentration initialization.
- **C3S CS2SMOS sea-ice thickness L4 combined v1.1:** EASE2-North 12.5 km, used for 2020-01-01 sea-ice thickness initialization.

Exact dataset citations and machine-independent acquisition metadata belong in the experiment/run documentation before publication-grade validation.

## Metadata audit

The original Zotero collection contains 127 records. One incomplete Keghouche record is a duplicate of `keghoucheModelingDynamicsThermodynamics2010` and is excluded from the repository bibliography. The repository bibliography therefore retains 126 original records and adds 11 verified references required by the current model documentation, giving **137 unique records**.

The local `work_references.bib` may retain Zotero `file` paths for PDF lookup. Those paths are intentionally absent from the repository-facing bibliography because they are machine-specific and not reproducible.