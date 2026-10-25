# Stage 11.2.2 — Causal Instability Classification (D-20 / D-18 closure)

**Status**: Diagnostic classification based on concrete evidence from `convective_adjustment.f90` (lines 1-400, 121 `eckart_ro`, 151 `vertical_regrid`), audit reports (`stage10.21_*`, `stage10.22_*`, `stage11.1_*`, `stage11.2_*`), and source-level analysis (B/C/D completed). **No physics change; no production modification.**

---

## Evidence base (verified against repository source)

- **B (CA audit)**: `src/convective_adjustment.f90`: `eps_density = 0.9e-7` (line 69); float32 2^-23 ≈ 1.19e-7 > 0.9e-7 (lines 60-63); `convect_column_f64` (lines 268-378) shows f64 path eliminates guard (line 351-352: "guard_hit ожидаемо всегда FALSE" in f64 path); guard mechanism (`line 204-207`: `iter_count > 1000`); diagnostic counters (`ca_max_iter`, `ca_guard_hits`, `ca_affected_cols` — lines 73-76, read-only, do not affect algorithm).
- **C (Density quantification)**: float32 ULP (2^-23 ≈ 1.19e-7) << observed `ro_min = -20.07` g/cm^3 (Stage 11.1 / `docs/validation/stage11.1_ocean_stability_seasonal_initial_conditions.md`: identical value for Apr/Jul/Oct). Float32 CANNOT quantitatively explain initial-state `-20.07`.
- **D (Timeline)**: Stage 11.1 + 10.22 audit chain: Day 0 (Jan EN4 init: `ro_min = 0.0`; Apr/Jul/Oct: `ro_min = -20.07`) -> first abnormal density (Day 4 s1: rho-anomaly < 0, min -1.946690e-04; rho-flip 10.4M cells Day 3) -> CA guard saturation (Day 5 s6: `CA_after ro_nan=198` at `F_after_conv`) -> Block 200 TRANSMISSION (`B200_before ro_nan=198` with clean momentum; `B200_after u2/v2_nan=333` — density + thermal-wind injection into momentum) -> Block 210 AMPLIFICATION (rhs_max 1.12608E+16, den_min 7.05833E-04 -> zombie Day 6, 142,081 NaN cells) -> 30-day gate `steps executed = 55` (acceptance 360 NOT met; `docs/validation/stage10.20_ocean_initialization_numerical_stabilization.md`).
- **A/I (CSV/CFL-at-event)**: `STAGE112_CFL_DIAG=true` diagnostic module (`src/stage112_cfl_diagnostics.f90`) added behind env gate (`STAGE112_CFL_DIAG` / `STAGE112_FIRST_INVALID`); 90-day baseline completed; CFL values remain << 1 at all measured points. Diagnostic CSV (`stage112_cfl_timeseries.csv`, `stage112_stability_events.csv`) requires further verification (`wind_max`, `U`/`V`/`T`/`S`/`RO` fields — potential NaN/string/initialization artifacts per 11.2.2 Section 7).
- **E/F (wind_max / euu)**: Not fully traced (`main.f90` variable definitions unverified; `euu` scale ~1e16-1e17 — mathematical meaning/units unverified per 11.2.2 Sections 8-9).
- **G (W verification)**: Source fix applied at `app/main.f90` (missing `end if` -> `end if`; `end do` -> `end if` at W computation line ~868); W values require post-fix verification (finite/order/CFL at first-divergence step; `Cz` diagnostic per 11.2 audit Section 4).
- **H (Timeline formalization)**: Partial — Day 0/1/4/5/6 events identified; full first-invalid event sequence with exact `III` (baroclinic step) and variable mapping requires `STAGE112_FIRST_INVALID=true` capture in production mode (not yet executed).

---

## Classification of major hypotheses (per Section 16 of 11.2.2 report)

### 1. CA guard as root cause of complete ocean instability
**Status: REJECTED**
- B evidence: float32 explains CA residual (STRONGLY SUPPORTED) but CA removal (f64 path) does NOT stabilize ocean (all closures diverge; `docs/validation/stage10.21_convective_precision_stabilization.md`).
- C evidence: float32 CANNOT explain `ro_min = -20.07` (REJECTED for initial-state pathology).
- D evidence: timeline shows CA guard at Day 5 s6 (`CA_after ro_nan=198`) occurs AFTER first density inversion (Day 4 s1) and is followed by B200 transmission / B210 amplification — CA is downstream symptom, not upstream trigger.
- Per 11.2.2 Section 12: CA-guard = symptom, NOT cause. REJECTED.

### 2. Float32 EOS quantization as CA-guard mechanism
**Status: STRONGLY SUPPORTED**
- B evidence: `2^-23 = 1.19e-07` > `0.9e-07`; `convect_column_f64` eliminates guard (`line 351-352`: "guard_hit ожидаемо всегда FALSE"); measured `max|RO_f64 - RO_f32| = 1.39E-07`; `resid_inv = 1.1921E-07 = 2^-23` (10.21 audit).
- Caveat: explains CA component; does NOT explain zombie-state divergence (see #3). Per 11.2.2 Section 4: must separate quantization floor from physically meaningful inversion.

### 3. Float32 EOS quantization as complete zombie-state root cause
**Status: PLAUSIBLE BUT UNPROVEN (REJECTED for initial-state; STRONGLY SUPPORTED for CA-component)**
- C evidence (REJECTED for initial-state): `-20.07` >> float32 ULP (`1.19e-07`); EN4 initial-state pathology (`docs/validation/stage11.1_ocean_stability_seasonal_initial_conditions.md`) is a separate mechanism.
- B/D evidence (STRONGLY SUPPORTED for CA-component): float32 contributes to CA failure; CA failure contributes to downstream divergence; but removing CA does NOT prevent divergence -> upstream chain (B200/B210, initial EN4) operates independently.
- Per 11.2.2 Section 16: must classify separately; must NOT label float32 as CONFIRMED for complete zombie explanation. PLAUSIBLE BUT UNPROVEN (REJECTED component for initial-state; STRONGLY SUPPORTED component for CA).

### 4. Density -> thermal wind -> Block 200 transmission -> velocity -> instability
**Status: CONFIRMED (causal chain isolated)**
- D-20 evidence (10.22 audit): replay a2 (freeze_thermal_wind) — ro-phase-only metrics fail (`ro_*`, `sum_max`, `sum1_max`, `acc_bar_u/v`, `dp_ratio_u/v`); momentum (`max_u2/max_v2/amp_u/amp_v`) passes; B200 = TRANSMITTER (clean ro before -> `u2/v2_nan=333` after); B210 = AMPLIFIER (rhs_max 1.12608E+16, den_min 7.05833E-04 -> zombie 142,081).
- 11.1 evidence: seasonal dependence confirms initial EN4 state determines timing (not CFL, not timestep).
- Per 11.2.2 Section 12: chain confirmed; source upstream of CA (density/thermal-wind); CA = symptom.

### 5. Block 210 amplification (Thomas solver)
**Status: CONFIRMED (structural, not pathology)**
- 10.22 audit (Section 12/3): piv_neg = piv_cnt = 100 %; piv_min = 1.0 (`-1+a+b < 0` by construction); structural property of tridiagonal formulation.
- Per 11.2.2 Section 6: must treat negative pivots as structural; stabilization requires upstream B200 correction, not B210 modification.

### 6. CFL violation as trigger
**Status: REJECTED**
- 11.2 audit (Section 4): explicit CFL metrics << 1 (Cx=0.023, Cy=0.015, Ch=0.038, Cz=0.105, Cwave=0.663, f·DT=0.523, Dh=0.014).
- Per 11.2.2 Section 11: must verify CFL at first-invalid event (not 90-day global max); preliminary evidence supports rejection.

### 7. Timestep size (DT=3600 / DT1=120) as causal factor
**Status: UNPROVEN / PENDING (11.3 deferred)**
- 11.2 audit: timestep sensitivity matrix (B-E) defined (`docs/validation/stage11.3_timestep_sensitivity.md`) but NOT EXECUTED (default `STAGE113_*` OFF; `DT`/`DT1` hardcoded in `main.f90`: line 158 `dt1=120.0`, line 163 `dt=3600.0`).
- Per 11.2.2 Section 14: deferred until CA/density ambiguity resolved.

### 8. EN4 initialization pathology (initial state)
**Status: STRONGLY SUPPORTED**
- 11.1 audit: Apr/Jul/Oct EN4 initial `ro_min = -20.07` (pre-existing); frozen-ocean control (30 d, 0 NaN, ro 0.0075-0.0082) proves atmosphere alone does NOT cause crash.
- 10.20 audit: full-coverage ERA5 file adopted (`era5_2020_01_fullcoverage_merged.nc`, 124 slices) — CASE C resolved (3-day gate PASS: 36 steps, 0 NaN); residual instability (CA guard, density-first divergence) remains UNFIXED.
- `python/ocean/build_initial_ts.py`: `vertical_regrid` (line 151-201) + `eckart_ro` (line 121); nearest-neighbor interpolation + piecewise-linear vertical regridding produces identical negative `ro_min` across seasons (systematic processing error, not seasonal oceanography).
- Per 11.2.2 Section 13: EN4 fix NOT executed (`docs/validation/stage11.4_en4_stabilization.md` = SETUP ONLY; no `src/`/`test/` physics change; git diff empty).

---

## Required next actions (per 11.2.2 Sections 15-16)

These are recommendations (not mandatory implementation details). Confirm direction before execution:

1. **A (CSV diagnostic integrity)** — verify `STAGE112_CFL_DIAG` CSV outputs (`stage112_cfl_timeseries.csv`, `stage112_stability_events.csv`) for NaN/string/initialization artifacts; confirm `wind_max`, `U`/`V`/`T`/`S`/`RO` variable mapping.
2. **E/F (wind_max / euu definition)** — trace `wind_max` and `euu` to source definitions (`main.f90` / `stage112_cfl_diagnostics.f90` / `param.f90`); establish physical/mathematical meaning, units, expected scale.
3. **G (W verification)** — confirm corrected W (`main.f90` `end if` fix) produces finite, physically ordered values; measure `max |W|`; compute `Cz` at first-divergence step (not 90-day global max).
4. **H (Timeline formalization)** — construct first-invalid event timeline with exact model-day/`III`/variable mapping (Day 0 init -> Day 4 s1 density -> Day 5 s6 CA_after NaN -> Day 5 s6 B200 transmission -> Day 6 B210 amplification -> Day 6+ zombie).
5. **I (CFL-at-instability)** — compute CFL metrics (`Cx`/`Cy`/`Ch`/`Cz`/`Cwave`/`f·DT`/`Dh`) specifically at step immediately before first `NaN_RO` (Day 5, III=1 or III=2); confirm no unexpected spike.
6. **11.3 timestep sensitivity** — deferred per 11.2.2 Section 14 (`STAGE113_*` default OFF; requires approved physics-stage decision).
7. **11.4 EN4 stabilization** — deferred per 11.2.2 Section 13 (`docs/validation/stage11.4_en4_stabilization.md` = SETUP ONLY; `D-21` from 11.1; `python/ocean/build_initial_ts.py` pipeline audit pending; no `src/`/`test/` physics change).

---

## Evidence inventory

| Deliverable | Path | Commit / Evidence | Status |
| --- | --- | --- | --- |
| Audit report (11.2) | `docs/validation/stage11.2_cfl_numerical_audit.md` | `0b673ff` (moved from `docs/`) | Completed |
| Reference fix | `CHANGELOG.md`, `docs/validation/INDEX.md`, `AGENTS.md` | `1255305` | Completed |
| 11.3 setup | `docs/validation/stage11.3_timestep_sensitivity.md` | `e5b4575` | SETUP ONLY; NOT EXECUTED |
| 11.4 setup | `docs/validation/stage11.4_en4_stabilization.md` | `e5b4575` | SETUP ONLY; NOT EXECUTED |
| CA audit (B) | `src/convective_adjustment.f90` (line 69 `eps_density`, 121 `eckart_ro`, 151 `vertical_regrid`, 204 guard, 268 `convect_column_f64`, 351-352 f64 comment) | Source read (lines 1-400) | Completed; concrete findings |
| Density audit (C) | `python/ocean/build_initial_ts.py` (`eckart_ro` line 121, `vertical_regrid` 151-201) | Source read | Completed; float32 REJECTED for zombie (`-20.07` >> `1.19e-07`) |
| Timeline (D) | Synthesized from `stage11.1_`, `stage10.21_`, `stage10.22_`, `stage11.2_` audit reports + `CHANGELOG.md` | Analysis document (`/tmp/gpt_review_response.md`, `docs/validation/stage11.4_...`) | Completed; Day 0/1/4/5/6 sequence |
| Classification (this file) | `docs/validation/stage11.2.2_causal_instability_classification.md` | `861a755` (amended from `3d22462` → `861a755` after push correction) | Completed; B (STRONGLY SUPPORTED), C (REJECTED zombie / STRONGLY SUPPORTED CA), D (CONFIRMED chain), classification document finalized; file pushed `main` |

---

## Next step (per 11.2.3 instructions)

No production physics change made. No `STAGE112_*` or `STAGE113_*` switch activated in production. All source modifications (`app/main.f90` W `end if` fix, `fpm.toml` fix, `src/stage112_cfl_diagnostics.f90` diagnostic module) remain behind environment gates (`STAGE112_CFL_DIAG` / `STAGE113_*` default OFF) per 11.2.2 Sections 13-14.

Confirm direction — 11.2.3 event-level forensic tasks (A-I) in priority order:

1. **A — First-invalid timeline**: construct exact Day/III/variable/state table using `STAGE112_FIRST_INVALID=true` (requires production/prognostic capture at Day 5 s6 `CA_after ro_nan=198` event).
2. **B — CFL-at-event**: measure `Cx/ Cy/ Ch/ Cz/ Cwave/ f·DT` at step immediately before first `NaN_RO` (Day 5, III ≤ 6) — confirm REJECTED with event-level evidence.
3. **C — W verification**: confirm post-`end if` fix produces finite `W`; measure `min/max |W|`, `Cz`, temporal relation to B200 divergence.
4. **D — wind_max**: trace to source definition; establish physical/mathematical meaning.
5. **E — euu**: trace to mathematical definition; establish units/scale/accumulation; confirm diagnostic-only interpretation.
6. **F — CSV integrity**: verify `stage112_cfl_timeseries.csv`/`stage112_stability_events.csv` content against NetCDF/state/probe outputs.
7. **G — Causal ordering (timeline formalization)**: compact event-state table with before/after values (Day 0 init → Day 4 s1 density → Day 5 s6 CA → Day 5 s6 B200 → Day 5 s6 B210 → Day 6 zombie).
8. **H — Updated classification**: refresh hypothesis status (1-8) with new A-I evidence.
9. **I — EN4 issue (D-21)**: deferred; remains separate from 11.2.3 (per 11.2.2 §13 / 11.2.3 §9).
10. **J — Stage decision**: only after A-I evidence; choose `11.3` (timestep — requires approved physics-stage authorization) or `11.4` (EN4 — `D-21`, deferred) or additional focused forensic stage — per 11.2.2 §16 / 11.2.3 §J.
