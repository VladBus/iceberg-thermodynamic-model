# Stage 11.8.0 T2 — CA/EOS Core Diagnostics & Float64 Verification

**Status:** COMPLETE
**Date:** 2026-10-23
**Base commit:** `3fe8a03` (Stage 11.8.0 T1)
**Scope:** third ladder rung — CA/EOS core diagnostics. **Diagnostic only**:
no production physics, EOS formula, scheduler, numerical operator, wind
rotation, or EN4 data was changed. Every result below executes the production
`convective_adjustment` core.

---

## 1. Phase 0 — T-23 formalized (ERA5 longitude wrap)

Fortran harness builds a **narrow** synthetic ERA5 file (longitude 10..70 E,
latitude 60..70 N, `u10 == longitude`) and calls production
`era5_bilinear2d`:

| Query | Current actual | Correct behaviour |
|---|---|---|
| **75 E** (east of file) | **10.0 (WESTERN edge)** | clamp to 70.0 (eastern edge) |
| 5 E (west of file, control) | 10.0 | clamp to 10.0 |

**T-23 RED CONFIRMED.** The ±360 normalization subtracts 360 once
(75 → −285), lands outside the grid; the binary search pins column 1 and the
weight clamp returns the **first** column. Latent for today's production
domain (0 out-of-range cells, T0) but invalid behaviour for any narrow or
dateline-crossing forcing file.

**Required fix (recorded, NOT applied):** replace the cyclic wrap with
**edge-clamping** (or explicit out-of-range rejection) in
`era5_bilinear2d`; assign to T1-corrective/T4.
Test: `python/tests/ocean/test_era5_longitude_wrap.py` (characterization —
passes as RED_CONFIRMED, also passes as FIXED; unexpected values fail).

---

## 2. Phase 1 — Homogeneous column (smoke, float32 and float64 paths)

T = 4.0 °C, S = 0.035 at all 18 levels; production `convect_column` (f32) and
`convect_column_f64` (f64 internals), both EOS modes:

| EOS | path | ΔT max | ΔS max | iterations | nmix | status |
|---|---|---|---|---|---|---|
| LEGACY | f32 | **0.0** | **0.0** | 1 | 0 | PASS |
| LEGACY | f64-core | **0.0** | **0.0** | 1 | 0 | PASS |
| EOS80 | f32 | **0.0** | **0.0** | 1 | 0 | PASS |
| EOS80 | f64-core | **0.0** | **0.0** | 1 | 0 | PASS |

The f64 criterion (≤1e-14) is enforced by the test. **No spurious mixing of a
truly neutral column in either precision** — the float32 quantization does not
trigger false convection for a homogeneous profile (the A-2 mechanism needs a
near-neutral, non-identical profile).

---

## 3. Phase 2 — Weak inversion: exact conservation

Genuine inversion (dense over light): L1 T=1.5 °C S=0.0346 over L2 T=2.0 °C
S=0.0345; dz1 = 50 000 cm; z = 25/35 m (10 dbar — compression kept small so
both EOS modes see the inversion).

| Path / mode | nmix | heat rel. error | salt rel. error |
|---|---|---|---|
| production f32, LEGACY | 1 | **0.0** | **0.0** |
| production f64-core, LEGACY | 1 | **0.0** | **0.0** |
| production f32, EOS80 | 1 | **0.0** | **0.0** |
| production f64-core, EOS80 | 1 | **0.0** | **0.0** |
| **exact float64 reference, LEGACY** | 1 | **0.0** | **1.316e-16** |
| **exact float64 reference, EOS80** | 1 | **0.0** | **1.316e-16** |

**Algorithmic conservation < 1e-12 verified** (heat exactly 0; salt
1.3e-16). Stable control: the literal pair from the stage text
(L1 T=2.0/S=0.0345 over L2 T=1.5/S=0.0346) is **stable**, not an inversion —
the lower level is colder AND saltier; CA correctly leaves it unmixed
(nmix = 0). The genuinely unstable pair is the swapped one used above.

**Storage limitation (T-27):** `convect_column_f64` computes in real64 but
writes T/S back into `REAL(4)` arrays and returns `o_resid_inv` as `REAL(4)`.
Production conservation is therefore float32-limited in general (the exact
equal-weight 2-level case above happens to round exactly). The test-local
real64 reference proves the algorithm is conservative.

---

## 4. Phase 3 — Compressibility: in-situ vs potential density (Sonnet A-1)

Column: L1 T=3.0 °C S=0.0345 at 25 m over L2 T=3.6 °C S=0.0345 at 75 m
(50 dbar separation; warm/light below cold/dense).

| Quantity | LEGACY | EOS80 |
|---|---|---|
| σ₀ level 1 / level 2 | 7.4837e-3 / 7.4181e-3 | **7.4860e-3 / 7.4290e-3** |
| in-situ ρ level 1 / level 2 | same as σ₀ (no p) | **7.6031e-3 / 7.7790e-3** |
| potential-density unstable? | **YES** | **YES** (σ₀ decreases downward) |
| in-situ stable? | NO | **YES** (compression > thermal contrast) |
| nmix f32 / f64 | **1 / 1** | **0 / 0** |
| status | CONTROL_PASS | **CRITICAL_CONFIRMED** |

**Finding: `convective_adjustment.f90` compares IN-SITU density at each
level's own pressure** (`cr(k) = eos_density(ct(k), cs(k), z(k)*0.01)`), with
no potential-density (σ₀) criterion. Under EOS-80, compression over 50 dbar
(~2.3e-4 g/cm³) exceeds the thermal destabilisation (~1.2e-4 g/cm³), so a
column that is genuinely convective in potential density is **falsely
declared stable and left unmixed** (A-1 confirmed; false-stability direction,
not false mixing). Recorded as **T-25**; NOT changed in T2.

---

## 5. Regression and verification

| Check | Result |
|---|---|
| Full `fpm test` | exit 0 — **59/59** STOP-0 (57 + 2 new), 0 FAIL/ERROR-STOP |
| Named T2 targets × {LEGACY, EOS80} | 8/8 exit 0 |
| T2 drivers (homogeneous, weak, conservation, compressibility) | all PASS / CRITICAL recorded |
| T1 harness + spatial/temporal/wrap drivers | PASS / WARNING / RED_CONFIRMED |
| ERA5 contract | 120/120 |
| Sea-ice/tides | 33 checks, 0 errors |
| Provenance | 28/28 |
| Ice coverage / sea-ice provenance | 16/16 / 8/8 |
| Snowfall (T-19) | CONFIRMED_12H |
| T0 EN4 / ERA5 coverage | unchanged (T-20/T-22; T-21 accepted) |
| Strict build | exit 0 |
| `git diff --check` | clean |
| GitHub Actions | green on the pushed commit |

---

## 6. Summary — is the CA/EOS core physically correct?

| Question | Answer |
|---|---|
| Spurious mixing of a neutral column? | **No** (f32 and f64: ΔT=ΔS=0) |
| Conserves heat and salt? | **Yes** — algorithm exact (f64 reference ≤1e-12); production state limited by f32 storage |
| Detects a genuine weak inversion? | **Yes** (both EOS modes, both precisions) |
| Uses potential density? | **No — uses in-situ density at local depth** |
| Compressibility defect (A-1)? | **CONFIRMED** — EOS-80 falsely stabilises potential-unstable columns (T-25) |
| Float32 state storage in f64 path? | **Yes** (T-27) |

## 7. GO/NO-GO for T3-prep (EN4 data fixing)

**GO for T3-prep (EN4 data fixing)** — NOT for T3 itself:
**T-20 (shipped z-grid mismatch / missing Jul–Oct rebuilds) and T-22 (Jan
rebuild sub-freezing cells) MUST be fixed before T3 (Rest).** T-25/T-27 define
the core-physics correction scope after the data are clean; H-2 remains the T4
blocker; T-23 is assigned to T1-corrective/T4.

## 8. Confirmations

- No physics/EOS formula/scheduler/numerical-operator change; `EOS_MODE=LEGACY`
  remains default.
- No production data modified; no CA algorithm change.
- Wind rotation and EN4 data not touched.
- T3–T6 not implemented.
