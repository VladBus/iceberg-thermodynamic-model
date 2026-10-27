# Stage 11.10 — Prognostic Ocean, NetCDF Default, Tides, Disk Cleanup

**Status:** **PARTIAL** — infrastructure, cleanup, and physical-baseline
governance complete; N>1/OBC and real tides remain blockers.
**Date:** 2026-10-27
**Base:** `ae6260e`
**Post-closure remediation** — Stage 11 remains administratively closed, but
N=1 is explicitly **not** a final physical state.

## 1. Disk cleanup — EXECUTED

| Metric | Before | After |
|---|---:|---:|
| `data/runs/` | 82.583 GB | **0.510 GB** |
| Run directories | 289 | **26** |
| Removed | | **263** original + 8 regenerated test artifacts |

26 retained runs: 8 matrix, 6 90-day, 6 11.8B verification/reproducibility,
and 6 final T3/T4/T5/T6 evidence. Each kept run has only `config.env`, logs,
CSV, first `results_day_00.nc`, and last `results_day_final.nc`.
No data outside `data/runs/` was touched. Manifest:
`data/runs/KEEP_MANIFEST.json`; cleanup script: `scripts/cleanup_runs.py`.

## 2. NetCDF production I/O — DONE

- `grid.nc` is the default/only production grid reader.
- `seaice_initial.nc` is the default/only production sea-ice reader.
- Root `KOORD.DAT`, `hhh.bar`, and `1_*.ice` symlinks were removed.
- `STAGE117E_NETCDF_*` env gates were removed from the production readers.
- Legacy `.DAT`/`.bar`/`.ice` branches are offline regression only
  (`docs/LEGACY_IO_POLICY.md`).

Verification: default 1-day and 30-day runs report NetCDF grid/sea-ice
metadata; `data/validation/netcdf_default_verification.json`.

## 3. Physical baseline — D-50

Bit-identity with N=1 is **abolished as a physics gate** (refactor-only).
New baseline:

1. 90-day no NaN, S<0, or T>30 °C.
2. Volume/salt/heat drift <1e-4 (OBC-aware).
3. Post-CA N² ≥ −ε.
4. N=4/N=24 required; N=1 is diagnostic only.

Raw default 30-day N=1 result: max |U| **4.99 m/s**, S min **−26.05 PSU**,
RO min **−41.07**; **FAIL** physical baseline. It is retained only as audit
evidence in JSON, not as a run directory.

## 4. N>1/OBC — BLOCKER CONFIRMED

One-day diagnostics with Ah=2000 (no 30-day forensic run):

| Scheduler | max \|U\| | max \|V\| | T min | S min | Verdict |
|---|---:|---:|---:|---:|---|
| N=4 | **4352 m/s** | **14098 m/s** | −206.2 °C | 0 | **BLOWUP** |
| N=24 | **1.89 m/s** | 1.14 m/s | −1.96 °C | 0.0249 | **GROWING** |

OBC is the immediate blocker: Flather barotropic + radiation baroclinic +
T/S relaxation, applied every barotropic step. Full contract:
`docs/OBC_N4_N24_AUDIT.md`. N=1 remains the only validated scheduler, but is
not accepted as the final state.

## 5. Tides — PLAN + RED TEST

`tides.nc` is **null-tides** (all amplitudes/phases zero). Plan:
`docs/TIDES_IMPLEMENTATION_PLAN.md`; red test:
`python/tests/test_tide_propagation.py` (intentionally RED and not in CI).
Tidal forcing must use FES2014/TPXO, UTC phase, SI units, and be applied at
every barotropic step.

## 6. Acceptance status

| Criterion | Status |
|---|---|
| data/runs <5 GB | **PASS (0.510 GB)** |
| NetCDF default I/O | **PASS** |
| Legacy isolation | **PARTIAL** — production path is NetCDF; branches retained for offline fixtures |
| D-50 physical baseline documented | **PASS** |
| OBC implemented or immediate blocker documented | **PASS (blocker documented)** |
| Tide plan + red test | **PASS** |
| CI green | pending final commit |

**Stage 11.10 is not physically complete.** The next action is OBC/N>1
stabilization and real tidal forcing; Stage 12 remains gated.
