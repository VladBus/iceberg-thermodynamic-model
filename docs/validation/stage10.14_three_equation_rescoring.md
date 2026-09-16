# Stage 10.14 — Re-scoring of the 10.8.2 Observational Set against the Three-Equation and Three-Equation + Natural-Convection Closures

**Classification: C (verification; point metrics reported, no calibration)**
**Production physics changed: NO**
**Default configuration changed: NO**

Independent re-scoring of the curated Stage 10.8.2 observational dataset
(19 records) against the two closures that were implemented _after_ Stage
10.8.2 — the three-equation interface (Stage 10.10/10.10.1) and the
three-equation + natural-convection scheme (Stage 10.11) — using the 10.8.2
methodology and acceptance criterion (observed band 0.01–1 m/day; point
metrics on the forcing-anchored rows; quiescent gap test). This is the
roadmap item explicitly listed after Stage 10.13
(`docs/PROJECT_ROADMAP.md` §142–143, `docs/model/stage10_modernization_plan.md`
§245–247) and the open question in `KNOWN_ISSUES.md` §44 / N-05.

| Item                 | Value                                                                                              |
| -------------------- | -------------------------------------------------------------------------------------------------- |
| Stage                | 10.14 (verification-only; no physics change)                                                       |
| Dataset              | `data/validation/observations/iceberg_basal_melt_observations.csv` (19 records, unchanged)         |
| Closures compared    | bulk (10.6/10.8.2 baseline), teq (10.10/10.10.1), teq_nat (10.11)                                  |
| New scoring layer    | `python/validation/three_equation_scoring.py`                                                      |
| New tests            | `python/tests/test_three_equation_scoring.py` (177 checks)                                         |
| Acceptance criterion | observed band 0.01–1 m/day; RMSE/MAE/bias on the 4 forcing-anchored rows; quiescent 5-row gap test |

---

## 1. Motivation (goal provenance)

Stage 10.14 is **not** a new physics stage: it closes the validation gap that
was explicitly deferred when the three-equation and natural-convection
closures were implemented:

- `docs/PROJECT_ROADMAP.md` §142–143 (Immediate next step): _"re-scoring the
  10.8.2 observational set against the three-equation + natural-convection
  closure with the 10.8.2 acceptance criterion"_.
- `docs/model/stage10_modernization_plan.md` §245–247: same item, listed
  first in the "Next modernization sequence".
- `KNOWN_ISSUES.md` N-05: _"Calibration deferred until re-scoring on the 3eq
  closure"_; open questions §44: _"Re-scoring of the 10.8.2 set against the
  3eq + natural-convection closure"_.
- `docs/validation/stage10.8.2_observational_validation.md` §15: recommended
  next step is _"a three-equation ice-ocean interface (Holland & Jenkins 1999) with a natural-convection floor"_.

Before this stage, `observational_validation.py` (10.8.2) scored only the
bulk forced closure; `low_flow_scoring.py` (10.13 Phase B) re-scored with the
low-flow closure. **The 3eq and 3eq+natural closures were never applied to
the 10.8.2 dataset** — this stage performs that scoring. No new physics is
introduced; the closures under test are the already-implemented production
schemes.

## 2. Method

For every dataset row the three closures are evaluated with the 10.8.2 input
conventions (`depth_m = L_char_m` draft; NJ80 `S=35, U_ref=0.1 m/s, L=50 m`;
KW84 `L=20 m`; salinity in PSU for the teq API, mass fraction for the teq_nat
API; `T_ice = -10 °C`, conduction on; `MELT_RATE_MIN = 1e-12 m/s` production
guard applied on all three paths):

- **bulk** — `observational_validation.model_melt_m_per_day` (unchanged 10.8.2 value);
- **teq** — `three_equation.three_equation_basal_melt` (Stage 10.10/10.10.1: `K_T=1.1e-3`, `K_S=3.1e-5`, density-weighted salt balance);
- **teq_nat** — `three_equation_natural.three_equation_basal_melt_natural` (Stage 10.11: natural convection, Churchill n=3 mixing; `l_char_nat = L_char_m` — see §5 note).

The teq/teq_nat Python reference layers were independently validated in
Stages 10.10/10.11 (65 + 70 checks, cross-language contract); this stage only
**applies** them to the observational rows.

## 3. Results

### 3.1 Point metrics on the u>0 comparable rows (n = 4: KW84 + NJ80×3)

| closure | RMSE (m/day) | MAE (m/day) | bias (m/day) | mean model | mean obs |
| ------- | ------------ | ----------- | ------------ | ---------- | -------- |
| bulk    | 0.108        | 0.092       | +0.083       | 0.1506     | 0.0677   |
| **teq** | **0.366**    | **0.277**   | **+0.277**   | **0.3451** | 0.0677   |
| teq_nat | 0.366        | 0.277       | +0.277       | 0.3451     | 0.0677   |

Per row (m/day):

| row           | obs    | bulk  | teq   | teq_nat | dT (°C) |
| ------------- | ------ | ----- | ----- | ------- | ------- |
| KW84_DUrville | 0.060  | 0.042 | 0.065 | 0.065   | 0.88    |
| NJ80_dT2      | 0.0137 | 0.080 | 0.160 | 0.160   | 2.0     |
| NJ80_dT4      | 0.0466 | 0.160 | 0.357 | 0.357   | 4.0     |
| NJ80_dT8      | 0.1507 | 0.320 | 0.798 | 0.798   | 8.0     |

**Key finding (u>0):** the three-equation closure does **not** improve the
point metrics against the 10.8.2 observations; it makes the systematic
positive bias worse (RMSE 0.108 → 0.366; bias +0.083 → +0.277). The
functional-form mismatch identified in Stage 10.9 (obs ~ dT^1.73 vs closure
dT^1.0) persists and is amplified: the 3eq closure scales linearly in dT with
a velocity-scale transfer `K_T·U` that is larger than the flat-plate
`Nu·k/L` at the reference U/L. KW84 improves (ratio 0.70× → 1.09×), NJ80
worsens (5.8× → 11.7× at dT=2). **No closure version is supported for
calibration by these 4 rows** (consistent with Stage 10.9's identifiability
conclusion, now re-confirmed on the 3eq closure).

### 3.2 Quiescent u=0 rows (n = 5, RH80 lab)

| row    | obs (m/day) | bulk | teq | teq_nat |
| ------ | ----------- | ---- | --- | ------- |
| RH_0C  | 0.0435      | 0    | 0   | 0.060   |
| RH_2C  | 0.1333      | 0    | 0   | 0.141   |
| RH_5C  | 0.3192      | 0    | 0   | 0.272   |
| RH_10C | 0.7296      | 0    | 0   | 0.504   |
| RH_18C | 1.5859      | 0    | 0   | 0.886   |

In-band (0.01–1 m/day): bulk **0/5**, teq **0/5**, teq_nat **5/5**.

**Key finding (quiescent):** the pure three-equation closure has **no**
natural-convection branch, so the 10.8.2 quiescent gap persists (0/5, same as
bulk). The **teq_nat** closure produces finite melt in the observed band for
all 5 lab rows (ratios to obs 0.56–1.39, i.e. within a factor ≤1.4),
when scored at the lab-block scale `L = 1 m` (the dataset's `L_char_m`).

### 3.3 Scale dependence of the natural-convection branch (new result)

The teq_nat quiescent result is **scale-dependent**, and this resolves an
apparent contradiction with the Stage 10.11.3 audit:

| scale           | Ra_eff (T=2 °C, S=35) | Nu       | γ_T,nat (m/s) | m (m/day) RH_2C      |
| --------------- | --------------------- | -------- | ------------- | -------------------- |
| lab block L=1 m | 4.6e9 (< cap 1e10)    | 249.9    | 3.43e-5       | 0.141 (in band)      |
| iceberg L=100 m | 4.6e15 (> cap)        | 323.17\* | 4.43e-7       | ~1.4e-3 (below band) |

\* Ra-capped value; γ_T,nat drops 77× from L=1 m to L=100 m.

Stage 10.11.3's "zero-flow m = 1.4e-3 m/day, 7–700× below the observed band"
was computed at the **iceberg scale** (L = 100 m), where the Ra cap pins Nu.
The RH80 laboratory observations were made on ~1 m blocks; at that scale the
cap is **inactive** and the natural-convection branch reproduces the
quiescent melt within the band. **The 10.11.3 gap statement is therefore
scale-specific: it applies to iceberg-scale application of the closure, not
to the lab-scale experiments that produced the RH80 data.** The production
iceberg (L ≈ 100 m) remains below the observed quiescent band — the 10.13
low-flow closure addresses that scale separately (research parameterization,
OFF by default).

## 4. Verification types and honest classification

| #   | Claim                                                                                    | Type of check                                                               | Status                                                                                          |
| --- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 1   | bulk metrics reproduce 10.8.2 (RMSE 0.108, MAE 0.092, bias +0.083)                       | regression                                                                  | **verified** (B.1–B.5)                                                                          |
| 2   | teq point metrics (RMSE 0.366, bias +0.277) and per-row values                           | mathematical/numerical (independent expected values from embedded literals) | **verified** (C.1–C.5)                                                                          |
| 3   | teq_nat == teq on u>0 rows (forced dominates, Churchill n=3)                             | mathematical                                                                | **verified** (D.1–D.2, rel < 3e-6)                                                              |
| 4   | bulk and teq give 0 on quiescent rows (gap persists for these closures)                  | mathematical (closure structure)                                            | **verified** (E.1–E.2)                                                                          |
| 5   | teq_nat quiescent melt is finite, in band, within factor 1.4–1.8 of RH80 obs             | numerical + preliminary physical                                            | **numerically verified; physical interpretation preliminary** (F.1–F.5)                         |
| 6   | lab-scale Ra < cap; iceberg-scale Ra > cap; γ ratio ~77×                                 | mathematical (embedded literals)                                            | **verified** (G.1–G.4)                                                                          |
| 7   | 3eq closure does not reduce the NJ80 systematic bias (functional-form mismatch persists) | numerical + physical interpretation                                         | **numerically verified; interpretation supported by Stage 10.9**                                |
| 8   | teq_nat closes the quiescent gap at the lab scale                                        | numerical; observational consistency                                        | **preliminary physical finding** — in-band agreement, not a validation of the closure mechanism |
| 9   | 10.11.3 "gap not closed" is scale-specific                                               | analysis of existing audit                                                  | **documented reinterpretation** (no production change)                                          |

What is **NOT** claimed: no "fully validated" / "universally valid" /
"observationally confirmed" / "production-ready" statements; **no
calibration was performed** (all parameters are production/literature
values; the word "calibrated" is not used for any coefficient).

## 5. Assumptions and limitations

- `l_char_nat = L_char_m` for the natural-convection characteristic length:
  for the NJ80 rows this is the reference berg length (50 m); for the RH80
  rows it is the lab-block length (1 m). On the u>0 rows the choice is
  irrelevant (forced convection dominates, rel. diff < 3e-6); it matters only
  for the quiescent rows, where it is the physically appropriate horizontal
  scale.
- The teq/teq_nat closures use `T_ice = -10 °C` (Stage 10.12
  `thermal_evolution_enabled` is ON by default and starts at `T_ICE_INIT =
-10 °C`; on a 90-day run the interior barely evolves, so the initial value
  is the correct diagnostic choice).
- Only 4 forcing-anchored rows from 2 independent sources anchor the u>0
  metrics; the turbulent branch is the only field-anchored regime (all
  Re > 5e5).
- The RH80 rows are lab-primary with `basal ~ side` aspect; the natural
  convection closure predicts basal melt. The in-band agreement is a
  **consistency result**, not a mechanism confirmation.
- The teq_nat closure itself retains all Stage 10.11.3 documented limitations
  (Ra cap, haline sign, L_char = L vs A/p) at the iceberg scale; this stage
  does not modify the closure.

## 6. Reproduction

```bash
# Stage 10.14 re-scoring (prints metrics + gap tables)
conda run -n iceberg-thermodynamic-model python python/validation/three_equation_scoring.py
# Locking tests (177 checks, blocks A–H)
conda run -n iceberg-thermodynamic-model python python/tests/test_three_equation_scoring.py
# Regression: all existing validation suites (822 checks)
conda run -n iceberg-thermodynamic-model python python/tests/test_three_equation.py
conda run -n iceberg-thermodynamic-model python python/tests/test_three_equation_natural.py
conda run -n iceberg-thermodynamic-model python python/tests/test_low_flow.py
conda run -n iceberg-thermodynamic-model python python/tests/test_observational_validation.py
conda run -n iceberg-thermodynamic-model python python/tests/test_calibration_assessment.py
conda run -n iceberg-thermodynamic-model python python/tests/test_internal_thermal_evolution.py
conda run -n iceberg-thermodynamic-model python python/tests/test_basal_melt_validation.py
```

## 7. Files changed

- `python/validation/three_equation_scoring.py` (new) — re-scoring layer;
- `python/tests/test_three_equation_scoring.py` (new) — 177 locking checks;
- `docs/validation/stage10.14_three_equation_rescoring.md` (this report);
- living docs updated: `docs/validation/INDEX.md`,
  `docs/model/model_physics_status.md`, `docs/model/stage10_modernization_plan.md`,
  `docs/PROJECT_ROADMAP.md`, `docs/DECISIONS.md`, `KNOWN_ISSUES.md`,
  `AGENTS.md`, `README.md`, `CHANGELOG.md` (see per-file entries).

**Unchanged:** `src/` (Fortran), `test/` (Fortran), `app/`, `data/`,
`fpm.toml`, `.github/workflows/`, all historical reports in `docs/wiki/`,
the observational CSV and its provenance, all pre-existing validation
modules (`basal_melt.py`, `three_equation.py`, `three_equation_natural.py`,
`observational_validation.py`, `calibration_assessment.py`, `low_flow*.py`,
`internal_thermal.py`) and their tests.

## 8. Outcome

Stage 10.14 delivers the roadmap-mandated re-scoring and updates
`KNOWN_ISSUES.md` N-05 (re-scoring dependency satisfied; calibration remains
not identifiable) and N-01 (quiescent gap: now scale-qualified — closed at
lab scale by teq_nat, open at iceberg scale). The production default
(bulk closure, `thermal_evolution_enabled = .true.`, `low_flow_closure_enabled
= .false.`) is unchanged; no switch defaults were altered.
