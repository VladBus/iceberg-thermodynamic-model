# Migration Guide — EOS-80 Is Now the Runtime Default (Stage 11.8B)

**Date:** 2026-10-26
**Breaking change:** `EOS_MODE` unset now means **EOS80**, not LEGACY.

## Why the default changed

Stage 11.8A validated the N=1 30-day seasonal matrix after the T-41 gate
correction:

- 8/8 matrix cells PASS under the corrected absolute-density gate.
- July EOS80 surface values are physically valid brackish water:
  absolute density **1.0199975–1.0199999 g/cm³**, raw anomaly
  −2.504e-3…−7.5e-5 kg/m³ (not a g/cm³ anomaly).
- EOS-80 is the physically appropriate equation of state for brackish water;
  the old `RO >= 0` gate was invalid, not the EOS.
- EOS80 is dynamically equivalent to LEGACY in the matrix:
  mean max |U| −0.14 %, KE30/KE15 +0.33 %, CA nmix −12.85 %.

D-29 therefore **PROMOTES EOS-80 for the N=1 30-day validated model**. See
`docs/validation/stage11.8A_phase2_seasonal_results.md` and
`docs/DECISIONS.md` (D-47/D-48).

## What changed

`src/equation_of_state.f90::eos80_configure()`:

| `EOS_MODE` | Result |
|---|---|
| unset / empty | **EOS80** (new default) |
| `EOS80`, `eos80`, `true`, `1` | EOS80 |
| `LEGACY`, `legacy`, `Eckart`, `eckart`, `false`, `0` | LEGACY Eckart fallback |
| any other non-empty value | EOS80 + warning (never silently LEGACY) |

The NetCDF global attribute `eos_mode` records the actual mode (`EOS80` or
`LEGACY`) for every run.

## Revert to LEGACY

```bash
export EOS_MODE=LEGACY
fpm run --flag "-I/usr/include" -- <run_id> [era5_file]
```

Or set it only for one command:

```bash
EOS_MODE=LEGACY fpm run --flag "-I/usr/include" -- <run_id> [era5_file]
```

Unset it to return to the new default:

```bash
unset EOS_MODE
```

**Do not** set `EOS_MODE=LEGACY` in shared production configuration unless a
LEGACY regression comparison is intended; label such runs clearly.

## Impact

- New runs with no `EOS_MODE` will have `eos_mode=EOS80` and will not be
  bit-identical to pre-11.8B default-legacy outputs.
- Existing LEGACY outputs remain valid as historical evidence. Re-run with
  `EOS_MODE=LEGACY` for a bit-identical comparison to those outputs.
- EOS80 and LEGACY share the same output schema and units; no post-processing
  migration is required.
- Production scheduler remains **BLOCKED** (T-39); this change only affects the
  EOS selection, not the scheduler or physics switches.
- Stage 11.8B verification: default = explicit EOS80 = matrix EOS80
  bit-identical (32/32 NetCDF files); LEGACY fallback = matrix LEGACY
  bit-identical. See `docs/wiki/stages/stage11/evidence/default_eos80_verification.json`.

## Recommended workflow

1. Start from the new default (omit `EOS_MODE`).
2. For regression/comparison, run `EOS_MODE=LEGACY` explicitly and retain both
   output trees.
3. Check `eos_mode` in `results_day_00.nc` before comparing runs.
4. Do not use production scheduler cells; they remain T-39-blocked.

## Related decisions

- D-29: EOS-80 promotion rule.
- D-47: T-41 gate correction; EOS-80 validated for N=1.
- D-48: runtime default change (this guide).
- T-39: production scheduler ice/cadence artifact — future work.
