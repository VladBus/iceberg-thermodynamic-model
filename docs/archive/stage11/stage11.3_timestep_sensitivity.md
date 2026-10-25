# Stage 11.3: Timestep Sensitivity Matrix (Setup — NOT EXECUTED)

**Status**: Setup completed; experiments deferred to user direction.
**Constraint (per audit D-19)**: Diagnostic only; production physics unchanged; default `STAGE112_*` switches OFF.

## 1. Matrix Definition (from `docs/validation/stage11.2_cfl_numerical_audit.md` §6)

| Exp | DT (s) | DT1 (s) | Change vs A (baseline) | Purpose |
|-----|--------|---------|------------------------|---------|
| A (baseline) | 3600 | 120 | — | Reference (audit completed) |
| B | 1800 | 120 | DT/2 | Halve baroclinic step |
| C | 900 | 120 | DT/4 | Quarter baroclinic step |
| D | 3600 | 60 | DT1/2 | Halve barotropic step |
| E | 3600 | 30 | DT1/4 | Quarter barotropic step |

## 2. Implementation Note — Hardcoded Parameters

`DT` (baroclinic) and `DT1` (barotropic) are hardcoded constants in `app/main.f90` (lines 158–168):

```
dt1 = 120.0         ! [с]
dt  = 3600.0         ! [с]
mm2 = 12             ! 12 шагов термодинамики в сутках
mm3 = 30             ! 30 баротропных микрошагов
```

Changing them requires either:
- (a) Modifying `main.f90` (invasive — affects production), or
- (b) Using environment-controlled overrides if added, or
- (c) Creating separate test builds.

**Recommendation (per audit)**: Option (b) — add `STAGE113_DT` / `STAGE113_DT1` environment variables read in `main.f90`, defaulting to 3600/120. This keeps production unchanged when variables are unset.

## 3. Next Action Required

Confirm direction:
- **(A)** Run timestep matrix experiments B–E (requires `STAGE113_*` env mechanism or temporary `main.f90` edit behind a flag).
- **(B)** Skip timestep experiments; proceed to EN4 initial-condition stabilization (D-21 from Stage 11.1 — real fix path).

No production changes made; `fpm test` remains 59 PASS.
