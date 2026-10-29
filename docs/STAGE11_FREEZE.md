# Stage 11 — Frozen Research Artifact

**Status:** **FROZEN / RESEARCH ONLY** — not a production-validated ocean.
**Freeze date:** 2026-10-29
**Frozen source commit:** `386c850` (`11.11.2: trace boundary heat/caps, iterative CA, synthetic tide control`)
**Git tag:** `stage11-final-frozen` — annotated tag on the freeze-record commit
(contains source `386c850` plus this document)
**Supersedes for physical claims:** `docs/STAGE11_CLOSURE_DECLARATION.md` (administrative closure)
**Living state:** `docs/STAGE11_STATE.md`

## 1. What is frozen

The Stage 11 ocean is preserved as a reproducible **30-day, N=24, no-tide
research baseline**. It is not promoted to production and does not satisfy the
full D-50 physical baseline.

The frozen configuration is the `obc_n24_thermo_30d` family:

- N=24 vertical levels; 13.89 km horizontal grid; 30 simulation days.
- Stage 11.10.4 thermodynamic core: hard T/S limits, implicit vertical
  diffusion, heat-flux clipping, post-CA smoothing.
- OBC + Rayleigh drag/boundary clip, EOS-80 runtime default.
- No real tidal forcing. `tides.nc` is null-tides; the only tide experiment is
  a 10-day synthetic M2 control (0.5 m, 12.42 h).

The ancillary 10-day synthetic-tide control (`tides_n24_10d_pot2`) is frozen
with the baseline as a **numerical experiment**, not as tide validation.

## 2. Verified outcome

Primary 30-day no-tide run (`docs/wiki/stages/stage11/evidence/n24_30day_final_with_tides.json`,
`n24_30day_thermo_rewrite_results.json`):

| Metric | Frozen value | Verdict |
|---|---:|---|
| NaN cells at day 30 | 0 | PASS for 30 days |
| max \|U\| | 1.999 m/s | bounded |
| max CFL | 0.518 | below 1 |
| T range | −1.94 … 30.00 °C | hard cap reached |
| S range | 0.00 … 37.05 PSU | hard lower cap reached |
| RO min | −11.736 kg/m³ anomaly (ρ_abs = 1008.264 kg/m³) | unit-correct, physically positive |
| KE after day 10 | decays (`ke_stable_after_day10=true`) | bounded |
| wet S<0.1 at T<0 | 0 cells | PASS |

These numbers are the complete, honest Stage 11 stability result. They do
**not** establish a correct ocean climatology.

## 3. Unresolved physical gates

| Gate | Result | Consequence |
|---|---|---|
| Stratification N² ≥ −1e−6 | **FAIL**: 9,813 wet interfaces below threshold in the 10-day tide control; N² min −0.01639 s⁻² | density structure is not physically closed |
| 30-day tide validation | **NOT RUN**: no FES2014/TPXO; synthetic M2 is schema/reader evidence only | tides are not validated |
| 90-day forced run | **NOT VALIDATED** (T-38) | no long-run claim |
| N=4 | **FAIL** (blow-up; CFL ≫ 1) | N=24 only |
| Hard caps | day 10 first cap at `k=0,i=1,j=93` (80.61°N, 19.53°E), T=30/S=40 | boundary-surface heat/CA interaction remains |
| Production scheduler | **BLOCKED** (T-39 ice/cadence artifact) | N=1/production matrix not a validated physical baseline |
| N=1 | diagnostic only | not the frozen production state |

The first cap is documented in `docs/wiki/stages/stage11/evidence/heat_first_appearance.json`;
the N² failure in `docs/wiki/stages/stage11/evidence/tide_integration_test.json`; tide absence in
`docs/wiki/stages/stage11/evidence/n24_30day_final_with_tides.json`.

## 4. What this freeze means

- The code and evidence at `386c850` are **reproducible and referenceable**
  for Stage 11.
- The N=24 no-tide 30-day configuration is the **numerical fallback** for
  later work that needs a bounded ocean state.
- The Stage 11 ocean is **not** a validated physical ocean and must not be
  cited as one.
- Stage 12 changes the ocean source (see D-51) and must not silently reuse
  Stage 11 climatology as truth.

## 5. Stage 12 consequence (D-51)

Stage 12 uses **GLORYS12 reanalysis + ERA5**, not the Stage 11 prognostic
ocean, for iceberg forcing:

- Ocean: `GLOBAL_MULTIYEAR_PHY_001_030` / `cmems_mod_glo_phy_my_0.083deg_P1D-m`
  (daily, 1/12°, `thetao`, `so`, `uo`, `vo`, `zos`, `siconc`, `sithick`).
- Atmosphere: ERA5 as already validated.
- Coupling: offline/prescribed; no two-way ocean feedback in Stage 12.
- The Stage 11 ocean remains a frozen research artifact and a numerical
  cross-check, not the Stage 12 forcing.

## 6. Reproduction

```bash
git checkout stage11-final-frozen
fpm test --flag "-I/usr/include"          # full battery; exit 0 expected
```

Evidence anchors:

- `docs/wiki/stages/stage11/evidence/n24_30day_final_with_tides.json`
- `docs/wiki/stages/stage11/evidence/n24_30day_thermo_rewrite_results.json`
- `docs/wiki/stages/stage11/evidence/tide_integration_test.json`
- `docs/wiki/stages/stage11/evidence/stratification_verification.json`
- `docs/wiki/stages/stage11/evidence/heat_first_appearance.json`
- `docs/validation/stage11.11.2_heat_forensics_root_cause.md`
- `docs/validation/stage11.11_physical_validation_tides.md`

## 7. Data footprint

`data/runs` occupies **4.6 GB across 54 top-level run directories** at freeze
time. The frozen baseline retains first/last NetCDF plus diagnostics; it does
not include a 90-day validated run.

## 8. Freeze rule

No further changes to Stage 11 physics, EOS defaults, scheduler semantics, or
the frozen evidence are permitted under this label. Any change requires a new
decision and a new validation stage. Documentation links may be corrected
without changing the frozen code or evidence.
