# Stage 11.4: EN4 Initial-Condition Stabilization (D-21) — SETUP ONLY

**Status**: SETUP; not executed (pending user direction or Stage 11.3 confirmation).
**Root cause** (from Stage 11.1 + 10.22 audit): EN4 initial T/S contains statically unstable density (`ro_min = -20.07 g/cm³` for Apr/Jul/Oct; Jan initially stable but diverges on Day 5).
**Evidence**:
- Frozen-ocean control (30 d, `ICEBERG_FROZEN_DENSITY=true`, `STAGE1022_FREEZE_RO=true`): 0 NaN, `ro` 0.0075–0.0082 g/cm³ — atmosphere alone does NOT cause crash.
- April/July/October EN4: crash Day 1 with pre-existing `ro_min = -20.07`.
- January EN4: initially `ro_min = 0.0`, diverges by Day 5 via prognostic evolution (EOS float32 quantization chain).

**Source of pathology**: `python/ocean/build_initial_ts.py` — nearest-neighbor interpolation from EN4 1° grid to model grid, plus vertical piecewise-linear regridding. Surface layer (level 1, 2.5 m) uses EN4 0–10 m layer; deepest-finite value used when model deeper than EN4 column bottom. The identical `ro_min = -20.07` across seasons suggests systematic surface-layer processing error (excessive extrapolation or incorrect unit conversion).

**Next action required**: Confirm whether to proceed with EN4 pipeline audit / fix, or complete timestep matrix (11.3) first.
