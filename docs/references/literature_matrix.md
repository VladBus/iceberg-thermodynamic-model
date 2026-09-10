# Literature-to-Model Matrix

**Scope:** current repository state through Stage 10.10.1 (three-equation salt-balance correction).

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
| Holland & Jenkins 1999 | Three-equation ice-ocean thermodynamics (Eqs. I-III, conduction term; Eq. 4 brine salt flux) | CORE, IMPLEMENTED (Stage 10.10/10.10.1) |
| Jenkins, Nicholls & Corr 2010 | Ice-ocean turbulent exchange / basal ablation; Table 2 velocity-scale `K_T`/`K_S` | CORE/COMPARISON, IMPLEMENTED (Stage 10.10/10.10.1) |
| MOM6 mom_ice_shelf (Losch et al. 2019; also published in Griffies et al.) | Three-equation salt budget `rho_w gamma_S (S_w - S_B) = rho_i m S_B` convention | VALIDATION (confirms Stage 10.10.1 correction) |
| PISM basal-melt documentation | Salt flux `Q_S^B = rho_I S^B dh/dt`; melt `w_b = gamma_S rho_W (S^W - S^B)/(rho_I S^B)` | VALIDATION (confirms Stage 10.10.1 correction) |
| MITgcm shelfice (Losch 2008 et seq.) | Mass-flux form `rho_c gamma_S (S - S_b) = -q (S_b - S_I)` with `S_I = 0` | VALIDATION (confirms Stage 10.10.1 correction) |
| Fujii, Honda & Morioka 1973 | Natural convection heat transfer from downward-facing horizontal surfaces | CORE, IMPLEMENTED (Stage 10.11) |
| Gayen, Griffiths & Kerr 2016 | Melt-driven convection under a horizontal ice face (LES) | VALIDATION (supports L_char = D for natural convection) |
| Churchill 1977 | Comprehensive correlating equation for forced, natural and mixed convection | CORE, IMPLEMENTED (Stage 10.11 mixed convection) |
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
| Three-equation interface physics | Basal closure, separately selectable; U-based `K_T`/`K_S` (1.1e-3/3.1e-5); Eq. III corrected: `rho_w gamma_S (S_w - S_B) = rho_i m S_B` (Stage 10.10.1) | Holland & Jenkins 1999; Jenkins et al. 2010 Table 2; MOM6/PISM/MITgcm confirm density-weighted convention | C (Stage 10.10.1; natural-convection floor and internal thermal evolution remain future) |
| Full seawater EOS | Not implemented; freezing point only | EOS-80/TEOS-10 literature | FUTURE |

## Dataset provenance to document

- **ERA5:** atmospheric reanalysis; preserve product name, variables, spatial/temporal resolution, retrieval date and CDS dataset identifier.
- **EN4:** ocean temperature/salinity profiles; preserve release/version and processing date.
- **IBCAO V5.2:** 400 m bathymetry used to reconstruct the real model grid; preserve product version, source and CRS EPSG:3996.
- **OSI-SAF SIC CDR v3.1:** SSMIS, EASE2-North 25 km, used for 2020-01-01 sea-ice concentration initialization.
- **C3S CS2SMOS sea-ice thickness L4 combined v1.1:** EASE2-North 12.5 km, used for 2020-01-01 sea-ice thickness initialization.

Exact dataset citations and machine-independent acquisition metadata belong in the experiment/run documentation before publication-grade validation.

## Metadata audit

The original Zotero collection contains 127 records. One incomplete Keghouche record is a duplicate of `keghoucheModelingDynamicsThermodynamics2010` and is excluded from the repository bibliography. The repository bibliography therefore retains 126 original records and adds 19 verified references required by the current model documentation (11 from the earlier stages, 8 JSON/DOI-verified additions from Stage 10.8.2: Enderlin & Hamilton 2014, Enderlin et al. 2016, Enderlin et al. 2023, Josberger & Neshyba 1980, Keys & Williams 1984, Neshyba & Josberger 1980, Orheim 1980, Schild et al. 2021), giving **145 unique records**. The legacy misspelled key `russefl-headMELTINGFREEDRIFTINGICEBERGS` is retained for citation compatibility but its record was corrected (author, journal, volume, DOI; see `references.bib`).

Stage 10.9 additionally confirmed via Crossref the DOIs of Weeks & Campbell 1973, Bigg 1997, Holland & Jenkins 1999, Jenkins, Nicholls & Corr 2010, FitzMaurice & Stern 2018, Cenedese & Straneo 2023 and Martin & Adcroft 2010 (all already present as keys, so the record count is unchanged at 145); see `docs/validation/stage10.9_calibration_assessment.md` §9.

The local `work_references.bib` may retain Zotero `file` paths for PDF lookup. Those paths are intentionally absent from the repository-facing bibliography because they are machine-specific and not reproducible.