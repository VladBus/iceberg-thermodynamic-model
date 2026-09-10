# Stage 10 — Physics Modernization Plan

**Updated:** 2026-09-10
**Current stage:** 10.8.2 (observational validation of basal melt; production unchanged)
**Current classification:** B — PASS WITH LIMITATIONS

## Purpose

Stage 10 replaces selected legacy thermodynamic closures with physically explicit formulations while preserving the legacy model's interfaces and regression behaviour wherever the new physics is not in scope. Every physics stage is required to have a literature basis, explicit equations, parameter provenance, independent tests, and a documented limitation statement.

## Completed stages

### 10.1 — Atmospheric shortwave radiation

**10.1.1 Solar geometry:** astronomical declination and equation-of-time approximation following Spencer (1971), UTC convention, longitude east-positive, polar-night handling.

**10.1.2 Atmospheric attenuation/cloud:** shortwave flux is assembled from solar zenith geometry, clear-sky attenuation, water vapour, aerosol and cloud terms. The current constants require stronger provenance/sensitivity documentation.

### 10.2 — Prognostic surface temperature

`T_surface` is prognostic with an effective surface heat capacity and explicit treatment of the transition to melting. Independent analytical tests were added; the discrete crossing treatment remains an identified validation target under extreme fluxes.

### 10.3 — Atmospheric sensible and latent heat

Neutral bulk-transfer formulation with fixed transfer coefficients, modern latent heat of sublimation and Murphy & Koop (2005) saturation vapour pressure over ice. The formulation is not yet stability-resolved.

### 10.4 — Phase-change partitioning

Surface energy is partitioned explicitly between non-latent heat, latent vapour flux and melt. Sublimation/deposition are represented through a prognostic atmospheric vapour mass diagnostic. Stage 10.4.2.1 added direct `Q_surface` diagnostics to remove a circular test dependency. The remaining limitation is that the vapour-flux physics itself still requires independent external validation.

### 10.5 — EOS-80 freezing point

The ocean freezing point is computed from the UNESCO/Fofonoff–Millard pressure-dependent equation. The function is used consistently at iceberg draft and in depth-dependent ocean thermal forcing. This is a freezing-point implementation only; a complete seawater density EOS is not implemented.

### 10.6 — Relative ocean flow and ocean-side heat transfer

Basal ocean-side heat transfer uses depth-dependent relative velocity between the iceberg and ocean current. The transfer coefficient is calculated from canonical flat-plate correlations with a laminar/turbulent transition at `Re = 5e5`. Stage 10.6.1 independently audited the formulation and corrected the documented length exponents.

## Stage 10.6.1 accepted limitations

- `L_char = L` is an approximation because iceberg orientation is not prognostic.
- Flat-plate correlations are not a geometry-specific derivation for an iceberg.
- Forced-convection transfer vanishes at zero relative speed; natural convection is not represented.
- Weeks & Campbell (1973) and FitzMaurice & Stern (2018) indicate that iceberg-specific melt behaviour can differ from simple flat-plate closures.
- Lateral melt remains a separate approximate closure.

## Stage 10.7 — Independent scientific validation of basal melt (DONE)

Independent scientific audit of the basal-melt chain (Re/Nu/γ_T/Tf/ΔT/m) with all expected values computed from embedded literals, not from production diagnostics. 17 independent checks (cases A–J) PASS; classification remains **B — PASS WITH LIMITATIONS**. Production Fortran unchanged. Findings:

- Formulation matches Weeks & Campbell (1973)/Eckert & Drake (1959) to float32 precision; `L_char = L` is supported by FitzMaurice & Stern (2018) for tabular icebergs.
- Turbulent branch (m ∝ U^0.8·L^−0.2·ΔT) is the realistic regime for Arctic icebergs (Re ≈ 5.5e5–2.7e8); laminar only for small bergs / weak flow.
- Order-of-magnitude agreement with in-repo three-equation estimate (St·u*, St=0.011 commented): factor ≈1.8 at U=0.1 m/s; observed submarine-melt band 0.01–1 m/day reproduced.
- Documented limitations unchanged: no natural convection (m→0 at U_rel=0), `L_char=L` orientation approximation, no three-equation closure.

Validation report: `docs/validation/stage10.7_basal_melt_validation.md`. Test: `iceberg_test_10p7_basal_melt_validation` (17 checks).

## Stage 10.8.1 — Independent Python validation layer (DONE)

A minimal, pure-Python re-implementation of the production basal-melt chain
(EOS-80 Tf, `U_rel`, Re, Nu, `gamma_T`, `DeltaT`, `m_basal`) that is
mathematically independent of the Fortran code (no Fortran calling/import/
output parsing). Located in `python/validation/basal_melt.py`, with a 44-check
analytical suite in `python/tests/test_basal_melt_validation.py` (plain-Python
runner; pytest-compatible). Production Fortran unchanged; classification remains
**B — PASS WITH LIMITATIONS** (numerical consistency validated, not
observational validity). Cross-check reproduces the Stage 10.7 float32
reference `m = 1.5852e-6 m/s` (residual ≈ 2.8e-5, reference-digit rounding;
raw float32-vs-float64 ≈ 1.3e-7). Report:
`docs/validation/stage10.8.1_python_validation.md`.

## Stage 10.8.2 — Observational validation of basal melt (DONE)

Curated 19-record observational dataset of published, DOI-verified submerged
melt rates (lab-primary Russell & Head 1980; field-primary Keys & Williams
1984; synthesis Neshyba & Josberger 1980; remote-sensing Enderlin & Hamilton
2014, Enderlin et al. 2016/2023; context Orheim/Budd et al. — Rignot et al.
2010 explicitly excluded as calving not submarine). `python/validation/
observational_validation.py` evaluates the **production** closure bit-identical
to the 10.8.1 layer and reports:

- point metrics on the 4 forcing-anchored rows: RMSE 0.108, MAE 0.092,
  bias +0.083 m/day; KW84 reproduced within range (ratio 0.70); NJ80 synthesis
  overestimated by factor 2.1-5.8 (dT 8 -> 2 °C);
- natural-convection gap: quiescent-lab melt 0.04-1.59 m/day vs model 0.0 —
  5.7-7.3 orders above the model floor;
- inverse-U: Greenland fjord rates (0.16-0.5 m/day) reproducible at plausible
  U_rel 0.1-1.0 m/s (dT 2-4 °C);
- all comparable observations fall in the turbulent regime (Re > 5e5); laminar
  branch has no field anchor.

Checks: `python/tests/test_observational_validation.py` (15 blocks, 229
checks). Report: `docs/validation/stage10.8.2_observational_validation.md`.
Classification of the validation pass: **C (pass with documented systematic
limitations)**; production physics UNCHANGED. Reference metadata added to
`docs/references/references.bib` (Enderlin x3, Josberger, Keys, Neshyba,
Orheim, Schild) and `russefl-head` mis-keyed entry corrected (author, journal,
volume, DOI).

## Next modernization sequence

### 10.9 — Calibration and/or three-equation closure

Stage 10.8.2 completed the observational validation pass (report above). The
next stage should:

1. calibrate the turbulent heat-transfer coefficient against the 10.8.2
   observational set (production-coefficient change — separate stage requiring
   sign-off; targets the observed factor 0.7-5.8 spread), or implement the
   three-equation ice-ocean interface formulation (Holland & Jenkins 1999;
   Jenkins et al. 2010) with independent confirmation of the Γ_T/Γ_S Stanton
   convention;
2. address natural convection at low relative flow (melt plumes) — quantified
   as the largest structural gap by 10.8.2;

Priority candidates (unchanged ordering, refreshed after 10.7):

1. independent validation of basal/lateral melt against published observations or laboratory results;
2. assessment of the three-equation ice-ocean interface formulation (Holland & Jenkins 1999; Jenkins et al. 2010);
3. improved treatment of iceberg-specific ocean heat transfer and natural convection;
4. improved atmospheric stability/transfer treatment if validation demonstrates a material need;
5. modern seawater thermodynamics, including a full EOS-80/TEOS-10 pathway, only as a dedicated future stage.

### Data and validation foundation

Real-data validation should preserve exact product/version metadata for ERA5, EN4, IBCAO V5.2, OSI-SAF SIC CDR v3.1 and C3S CS2SMOS SIT L4 combined v1.1. Observational iceberg tracks, melt observations and published benchmark cases should be incorporated before calibration is attempted.

### Future numerical/scientific infrastructure

A Python analysis/visualization layer should be developed as a validation and reproducibility tool, not as a replacement for the Fortran production model. A future literature matrix and bibliography remain the authoritative mapping from equations and parameters to sources.

## Rules for future stages

1. No calibration of TEST_11 to hide unexplained physical anomalies.
2. No production-physics changes without an explicit equation and source.
3. Independent analytical tests must not derive both sides from the same production diagnostic.
4. Regression tests and scientific validation must be reported separately.
5. Preserve the current legacy interface unless an interface change is explicitly justified.
6. Keep EOS-80/TEOS-10, advanced turbulence, iceberg orientation and Python validation as roadmap items until their own scientific scope is defined.

## Documentation references

- `docs/model/model_description.md` — narrative model description.
- `docs/model/model_equation_ledger.md` — mathematical specification.
- `docs/model/model_physics_status.md` — maturity/status of physical blocks.
- `docs/references/references.bib` — machine-independent bibliography.
- `docs/references/literature_matrix.md` — source-to-model mapping.
