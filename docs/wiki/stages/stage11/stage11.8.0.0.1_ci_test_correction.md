# Stage 11.8.0.0.1 — CI Fix, Real Tests, Snowfall Re-examination

**Status:** COMPLETE
**Date:** 2026-10-22
**Base commit:** `558cbca` (Stage 11.8.0.0)
**Scope:** correction only — no physics, EOS, scheduler, or snowfall-divisor change.

---

## 1. Why this stage

Commit `558cbca` broke CI (GitHub Actions run 39809341467, job *Python
Environment Check*, step 16 “Run homogeneous-column Fortran diagnostic”,
exit 127 `fpm: command not found`), left two diagnostic tests unable to fail,
and overstated the snowfall accumulation period as `CONFIRMED_12H`.

---

## 2. Phase 0 — CI fix

**Root causes found**

1. The homogeneous-column Fortran step (and its driver, which needs the
   fpm-built executable) were appended to the **`test-python` job**, which only
   installs Miniconda — `fpm` exists exclusively in the `test` (Fortran) job
   (`/usr/local/bin/fpm` from the release binary).
2. `fpm.toml` declared the test name `homogeneous_column`, while CI asked for
   `test_homogeneous_column`. Locally **`--target homogeneous_column` matches
   nothing and exits 0 (“No tests to run”)** — a silent false-green. The
   matching name is the program name `test_homogeneous_column`.

**Fixes applied**

* Fortran named-target steps + both-EOS-mode runs + the stdlib-only drivers
  moved into the **`test` job** (system `python3`, no conda needed).
* `fpm.toml` test names aligned with the CI requests:
  `[test.test_homogeneous_column]`, new `[test.test_weak_inversion]`.
  Verified locally: `fpm test --target test_homogeneous_column` /
  `test_weak_inversion` execute.
* A comment documents the silent-skip hazard; the Python drivers are the
  authoritative re-runs (they delete per-mode JSONs before each run, so a
  missing/renamed target cannot masquerade as a pass).
* `test_snowfall_period.py`, `test_ice_coverage.py` and
  `test_seaice_provenance.py` now **self-guard**: explicit `SKIP:` message and
  exit 0 when their inputs (raw NetCDF / binary) are absent; genuine threshold
  or attribute violations exit 1. No `||` masking anywhere.

**CI was green** on the pushed commit (verified via the GitHub Actions API after this push).

---

## 3. Phase 1 — T2 tests that genuinely fail

**Failure-path probe (homogeneous column):** `test_failed` temporarily forced
true → JSON `status=FAIL`, **process exit 1** → restored → PASS, exit 0. The
non-zero exit now genuinely turns CI red on invariant violation.

**Homogeneous column → reclassified as SMOKE control** (both modes:
ΔT = ΔS = 0, 1 iteration, nmix 0, exit 0). A homogeneous column is stable under
Eckart *and* UNESCO (deeper in-situ density increases monotonically), so the
11.8.0.0 “expected FAIL” premise was wrong; this test only proves CA does not
spuriously mix a stable column.

**Weak-inversion core test** `test/test_weak_inversion.f90` +
`python/tests/ocean/test_weak_inversion.py`: one localized inversion at
interface 2/3 in `T = [4.3, 3.9, 4.0, 3.8…]`, `S = 35 PSU`, uniform half-layers.

| Mode | nmix | iterations | changed levels | heat rel. err | salt abs. err | stable | status |
|---|---|---|---|---|---|---|---|
| LEGACY | 1 | 2 | exactly {2, 3} → both 3.95 | 0.0 | 0.0 | yes | **PASS** |
| EOS80 | 0 | 1 | none (in-situ density masks it) | 0.0 | 0.0 | yes | **PASS** |

**Heat/salt conservation: VERIFIED exactly (0.0 error) in both modes.**
Mode-dependent behaviour is the real T2 finding: the EOS-80 in-situ criterion
masks a genuine potential-density inversion (pressure-densification ≈ 1.2e-4
g/cm³ per 25 m ≫ thermal ≈ 1e-5). Recorded for 11.8 (potential-density
criterion is a candidate fix); **not fixed in this stage**.

---

## 4. Phase 2 — Snowfall accumulation period re-examination

Evidence (raw source files only; all months consistent):

| Fact | Value |
|---|---|
| `GRIB_stepType` | `accum` |
| `GRIB_dataType` | `fc` (forecast window, not analysis) |
| `GRIB_stepUnits` | 1 |
| `GRIB_startStep` / `GRIB_endStep` / `GRIB_stepRange` | **ABSENT** (cfgrib folded the single step per record into `valid_time`; `history` confirms only `stepType`/`stream` filters survived) |
| Records per day | exactly 2, spacing 43200 s |
| Jan domain-mean per record | 7.3e-5 m (max 3.96e-3 m) |

Contradiction found: `python/era5/download_era5.py` requests **hourly steps
1..24** at 00/12, yet every delivered artifact contains only **two 12-hourly
records/day**, and no CDS request log survives. Possible readings:

* each record = a 12-hour window (00→12, 12→00): 2/day covers the full day,
  divisor 43200 correct (self-consistent — the only layout where 2 samples/day
  represent the whole accumulation cycle);
* each record = a 1-hour window: 2/day would miss 22 hours of accumulation and
  the 43200 divisor would understate the rate **12×** (the Sonnet audit’s
  worst-case reading).

Per the evidence hierarchy (CONFIRMED requires step-range attributes), the
status is **`INFERRED_12H`** with documented uncertainty — the 11.8.0.0
`CONFIRMED_12H` claim is **superseded**. Manual verification (reproduce a small
CDS request, steps 1..24 vs step 12, compare magnitudes) is required before any
divisor change.

**Divisor 43200 NOT changed.** Recorded as **KNOWN_ISSUES T-19**, scheduled for
11.8 T0. The old “6-h mismatch” claim (11.7E.4.1) and the “CONFIRMED” claim
(11.8.0.0) are both corrected; `test_snowfall_period.py` no longer infers the
period from `valid_time` spacing alone and reports SKIP when the source file is
absent.

---

## 5. Phase 3 — Documentation and data fixes

* `PROJECT_ROADMAP.md`: duplicate 11.7E.5 `DEFERRED` status lines deduped
  (one remains); 11.8.0.0.1 section added; stage pointers updated.
* `stage11.8.0.0` report: duplicate `snowfall_period_result.json` deliverable
  removed; the `CONFIRMED_12H` verdict marked SUPERSEDED by this stage; the
  homogeneous section notes the exit-0 limitation fixed here.
* `stage11.8.0_ocean_diagnostic_plan.md`: 11.8.0.3 reclassified as SMOKE
  control; new 11.8.0.3b (weak-inversion core) recorded as created.
* `data/validation/*.json`: absolute `/home/vlad/...` paths → repo-relative;
  `ice_coverage_result.json` `checks` array populated (16 entries); the stale
  single-file `homogeneous_column_fortran.json` was already removed in 11.8.0.0.

---

## 6. Phase 4 — Regression (local, on this commit)

| Suite | Result |
|---|---|
| `fpm test` (full battery incl. both new T2 targets) | exit 0, 0 FAIL/ERROR-STOP lines |
| Named targets `test_homogeneous_column` / `test_weak_inversion` × {LEGACY, EOS80} | 4/4 exit 0 |
| `test_homogeneous_column.py` driver | 2/2 modes PASS, exit 0 |
| `test_weak_inversion.py` driver | 2/2 modes PASS, exit 0 |
| `test_stage11_7e3_era5_contract.py` | 120/120 |
| `test_seaice_tides_nc.py` | 33 checks, 0 errors |
| `test_provenance_attributes.py` | 28/28 |
| `test_ice_coverage.py` | 16/16 |
| `test_seaice_provenance.py` | 8/8 |
| `test_snowfall_period.py` | INFERRED_12H reported, exit 0 |
| Strict build (`-Wall -Wextra -fcheck=all -ffpe-trap=…`) | exit 0 |
| `git diff --check` | clean |

---

## 7. GO / NO-GO for 11.8.0 T0

**GO** for Stage 11.8.0 T0 (data and units verification). T0 scope now
explicitly includes the manual CDS verification of T-19 before any snowfall
divisor decision. Carried gates unchanged: ocean stabilization (55/360 →
360-step requirement), Jan-only sea ice, EOS-80 masking finding (this stage)
queued for the 11.8 core work.

## 8. Confirmations

* **NO physics, EOS formula, scheduler, or numerical operator changed.** The
  only `src/` edit in this stage is none; `test/` additions and CI/docs only.
* **`EOS_MODE=LEGACY` remains default.**
* **Snowfall divisor 43200 NOT changed** (recommendation recorded only).
* 11.7E.5 not started; T0–T6 implementation not started.
