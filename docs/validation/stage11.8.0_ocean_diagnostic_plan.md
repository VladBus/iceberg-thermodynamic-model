# Stage 11.8.0 — Ocean Diagnostic Plan

**Date:** 2026-10-21
**Status:** PLAN (created in Stage 11.7E.4.1)
**Based on:** Ocean Stage 11 Audit methodology (A-1 through AC-5)

---

## 1. Problem Statement

The production ocean model remains unstable:
- **Failure mode:** Density-first divergence → NaN cascade → zombie state (all cells NaN)
- **Current limit:** 55/360 steps before NaN (Stage 10.20, 10.22)
- **Root cause chain (D-20):** CA/EOS float32 quantization (2⁻²³ = 1.1921E-07) → density inversions (ρ < 0) → thermal wind → Block 200 (transmitter) → Block 210 (amplifier) → NaN cascade
- **Seasonal dependence (D-21):** All seasons crash; Jan survives 4 days, Apr/Jul/Oct crash Day 1 with pre-existing ρ < 0 (historical −20.07 g/cm³ was a unit/sentinel artifact of overwritten runs, corrected in Stage 11.1/11.4; **current Day-0 files do not exhibit −20.07**). Actual cause of seasonal collapse requires verification of current seasonal files.
- **Frozen-ocean control:** 30 days stable (ro 0.0075–0.0082 g/cm³) → atmosphere alone is stable
- **EOS-80 (D-29):** OPTIONAL, not default; ice amplification unvalidated; decision deferred to 11.8A

**Acceptance gate (from D-20):** 30-day run with `steps executed = 360` (12 steps/day × 30), no NaN, physically valid trajectory.

---

## 2. Diagnostic Ladder (from Audit AC-3)

Each tier isolates one subsystem. Proceed only when previous tier passes.

| Tier | Name | Scope | Duration | Key Question |
|------|------|-------|----------|--------------|
| **T0** | Data Scan | Input NetCDF/ice: zeros, NaN, T<Tf, inversions, axis order, coverage, units | No model run | Are inputs clean? |
| **T1** | Forcing | ERA5 read on every wet cell & timestep; interpolator only | No model run | Is forcing correctly interpolated? |
| **T2** | CA/EOS Core | Homogeneous column, weak real inversion, analytical mixing solution | CA, EOS, float64 | Does CA introduce spurious mixing? |
| **T3** | Rest (ocean without wind/fluxes) | Dynamics without forcing, from real T/S, 30 days | 30 days | Is advection/CA/B200/B210 stable without forcing? |
| **T4** | Wind | Homogeneous wind along axes and at angle | Forced ocean without T/S coupling, 5-10 days | Does wind rotation cause instability? |
| **T5** | Time | CFL scan of dt and shal frequency | Core + forcing, 7 days | What dt/shal combinations are stable? |
| **T6** | Full | ERA5 + ice + EN4 | Seasonal initial conditions, 30 → 90 → 365 days | Is full system stable? |

---

## 3. Intervention Order (from Audit AC-4)

Ordered by causal priority (fix upstream first):

| # | Intervention | Target | Rationale |
|---|-------------|--------|-----------|
| **1. Data (T0/T1)** | Rebuild init T/S from smoothed grid with QC; θ→T, T≥Tf; ERA5 by domain bbox + margin ≥1°; clamp longitude instead of wrap; snowfall divisor change ONLY after T-19 confirms the accumulation period from source GRIB metadata or the CDS probe (`t19_cds_probe.py`) | T0, T1 | Eliminates pre-existing ρ<0 (Apr/Jul/Oct) if real, resolves the snowfall divisor on evidence, removes longitude wrap artifacts |
| **2. Core (T2)** | CA and EOS in float64; criterion on potential density; freezing point UNESCO everywhere | T2 | Eliminates float32 quantization floor (2⁻²³); potential density criterion is physically correct |
| **3. Geometry (T0)** | Remove ring/hack 73×94; unified axis order ('k','j','i'); field angle(i,j) | T0 | Removes axis-order confusion (T-13/T-18 legacy); consistent NetCDF-Fortran mapping |
| **4. Wind (T4)** | Rotation to grid (model coords) | T4 | Fixes wind forcing direction (T-13 resolved but verify in new geometry) |
| **5. Time (T5)** | Ocean every step; symmetric ice-ocean coupling; shal every step | T5 | Eliminates cadence mismatch (N=1 vs substepped); symmetric coupling prevents drift |
| **6. Tides** | FES/TPXO/EOT20 data → tides.nc in SI; phase by UTC; OBC on all open boundaries | T6 | Realistic tidal forcing for full validation |
| **7. Ice** | Real SIC/SIT for 4 seasons (Jan/Apr/Jul/Oct) | T6 | Seasonal validation gate (D-27) |

**Ordering principle:** Each intervention must pass its tier test before the next is attempted. No intervention is applied to production until the full ladder passes.

---

## 4. Acceptance Criteria (from Audit AC-1)

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Stability** | 365-day run without NaN, without guard triggers, without fallback substitutions | `steps executed = 4380` (12 steps/day × 365) |
| **Volume conservation** | Closed basin: volume to 1e-6 relative | Σ(u·h·dx·dy) balance |
| **Heat/salt conservation** | Total heat/salt with flux correction to 1e-4 relative | Budget closure diagnostics |
| **Stable stratification** | N² ≥ -ε on potential density after CA in all cells every step | `N²_min ≥ -1e-8` post-CA |
| **Rest stability** | **T3a** homogeneous column: max |u|<1e-6 m/s, ΔT<1e-6 °C. **T3b** real EN4 + zero forcing: max |U|<0.5 m/s, KE30/KE15<5.0, no exponential growth (bounded geostrophic adjustment). | T2/T3 tier tests |
| **Physical plausibility** | T ≥ Tf(S,p), 0 ≤ S ≤ 42, |u| < 3 m/s (sea) / < 5 m/s straits | Daily diagnostic bounds |
| **Reproducibility** | Repeated run with same config file gives same output hash manifest | MD5 of daily_diagnostics.csv identical |

**Milestone gates:**
- **T2 gate (ALL THREE required, 11.8.0 T0 correction):**
  (a) homogeneous-column SMOKE test PASS (CA does not modify a stable column);
  (b) weak-inversion CORE test PASS (inversion mixed, confinement, stability);
  (c) analytical mixing solution PASS to 1e-12 (known two-/three-layer
  volume-weighted mixing, float64 reference).
- **T3 gate:** T3a pure rest (|u|<1e-6) and T3b adaptation (|U|<0.5 m/s, KE30/KE15<5.0, no exponential growth); no NaN.
- **T6 gate:** 30-day full run stable → 90-day → 365-day

---

## 4. Decision Policy (from Audit AC-5)

| Branch | Purpose | Rules |
|--------|---------|-------|
| **legacy-frozen** | Current code with all switches OFF | Bit-identity preserved ONLY as protection against accidental refactoring. NO physics changes. |
| **stage11-physics** | Sanctioned physics changes with new reference | New reference + criteria AC-1. Results compared by PHYSICAL METRICS (not bit-for-bit). |

**Decision gate D-33:** Fix this policy in DECISIONS.md before any physics changes land on stage11-physics branch.

**Comparison protocol:** Results of (b) are NOT compared bit-for-bit with (a). Comparison is by physical metrics (AC-1). Bit-for-bit equivalence is ONLY required within legacy-frozen branch.

---

## 5. Immediate Next Steps (Stage 11.8.0 Implementation)

### 11.8.0.1 — T0 Data Scan Implementation
- Create `python/tests/ocean/test_data_scan.py`:
  - Scan all input NetCDF (ERA5, EN4, ice, bathymetry) for: zeros, NaN, T<Tf(S,p), static inversions (∂ρ/∂z > 0), axis order (i/j/k vs j/i/k), coverage gaps, units.
  - **Verify actual T/S fields and units in current seasonal initial files (2020-01, 2020-04, 2020-07, 2020-10)** — confirm no −20.07 sentinel artifacts remain.
  - Output: `data/validation/data_scan_report.json`
- Run on all seasonal EN4 products (Jan/Apr/Jul/Oct) and ERA5 fullcoverage.

### 11.8.0.2 — T1 Forcing Interpolator Test
- Create `python/tests/ocean/test_forcing_interpolator.py`:
  - Verify ERA5 bilinear + lon-wrap on EVERY wet cell, EVERY timestep.
  - Compare Fortran interpolator vs independent Python (xarray) on all wet cells.
  - Check lon-wrap clamping vs wrapping.

### 11.8.0.3 — T2 Homogeneous Column SMOKE Test
- **Created in 11.7E.4.1, made real in 11.8.0.0.1:**
  `test/test_homogeneous_column.f90` + `python/tests/ocean/test_homogeneous_column.py`
- Classification (11.8.0.0.1 correction): SMOKE control — a homogeneous column
  is stable under both EOS modes, so PASS is the expected result; the test must
  FAIL (non-zero exit) only if CA spuriously mixes a stable column.
- **Not** the CA-defect red test: that role belongs to 11.8.0.3b.

### 11.8.0.3b — T2 Weak-Inversion Core Test (CREATED in 11.8.0.0.1)
- `test/test_weak_inversion.f90`: one localized inversion at interface 2/3;
  verifies heat/salt conservation (<1e-5 rel), stability, confinement of mixing.
  LEGACY: must mix levels 2-3; EOS80: in-situ pressure term masks the
  inversion (documented 11.8 finding — potential-density criterion is a
  candidate fix under intervention #2).

### 11.8.0.4 — T2 Analytical Mixing Solution
- Create `python/tests/ocean/test_analytical_mixing.py`:
  - Weak real inversion: linear T/S gradient with known analytical CA solution.
  - Compare Fortran CA output to analytical solution (float64 reference).
  - Test both EOS modes.

### 11.8.0.5 — T3 Rest Run (T3a pure / T3b adaptation)
- Create `python/tests/ocean/test_rest_run.py`:
  - 30-day ocean-only run from real T/S, zero forcing (wind=0, flux=0).
  - Check: no NaN, |ΔT|<1e-6, |u|<1e-6 over 30 days.
  - This is the T3 gate.

---

## 6. Deliverables

| Deliverable | Path | Status |
|-------------|------|--------|
| Diagnostic Plan (this doc) | `docs/validation/stage11.8.0_ocean_diagnostic_plan.md` | **THIS DOC** |
| T0 Data Scan Test | `python/tests/ocean/test_data_scan.py` | TODO |
| T1 Forcing Interpolator Test | `python/tests/ocean/test_forcing_interpolator.py` | TODO |
| T2 Homogeneous Column Red Test | `python/tests/ocean/test_homogeneous_column.py` | **DONE** (Phase 1) |
| T2 Analytical Mixing Test | `python/tests/ocean/test_analytical_mixing.py` | TODO |
| T3 Rest Run Test | `python/tests/ocean/test_rest_run.py` | TODO |
| Red Test Results | `data/validation/homogeneous_column_result.json` | PENDING |
| Ice Coverage Test | `python/tests/ocean/test_ice_coverage.py` | **DONE** (Phase 2) |
| Snowfall Period Test | `python/tests/ocean/test_snowfall_period.py` | **DONE** (Phase 3) |
| Snowfall Period Results | `data/validation/snowfall_period_result.json` | PENDING |

---

## 7. Integration with Stage 11.7E.4.1

This plan document is the **primary deliverable of Phase 4** of Stage 11.7E.4.1.

The red tests from Phases 1–3 provide the baseline defect evidence:
- **Phase 1 (Homogeneous Column):** Expected FAIL → proves CA defect
- **Phase 2 (Ice Coverage):** Expected PASS → verifies 11.7E.4 real ice connection
- **Phase 3 (Snowfall Period):** Reports finding → informs T0/T1 data fixes

These tests form the **baseline defect evidence** that the 11.8 diagnostic ladder must resolve.

---

## 8. References

- Ocean Stage 11 Audit: `docs/validation/stage11.1_ocean_stability_seasonal_initial_conditions.md`
- Causal isolation: `docs/validation/stage10.22_ocean_density_thermal_wind_block200_audit.md`
- Precision investigation: `docs/validation/stage10.21_convective_precision_stabilization.md`
- Ocean init stabilization: `docs/validation/stage10.20_ocean_initialization_numerical_stabilization.md`
- EN4 seasonal stability: `docs/validation/stage11.1_ocean_stability_seasonal_initial_conditions.md`
- Audit methodology: `docs/validation/stage11.2_cfl_numerical_audit.md` (AC-1 through AC-5)
- Decision records: `docs/DECISIONS.md` (D-17 through D-32)

---

**End of Plan — Ready for 11.8.0 Implementation**