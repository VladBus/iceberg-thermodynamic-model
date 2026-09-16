# Stage 4 — ERA5 integration, convective cycle, EOS precision

ERA5 forcing integration, convective-cycle root cause (float32 EOS quantization), precision study.

## Reports (5)

ERA5 on the TEST grid (4.1), January 2020 (4.2), convective-cycle root cause (4.3), float EOS precision (4.3b), precision criterion (4.4).

| File                                | Report                                                                      |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `Stage4.1_monthly_era5_test.md`     | Stage 4.1 — Monthly ERA5 Integration on TEST Grid                           |
| `Stage4.2_january2020.md`           | Stage 4.2 — January 2020 ERA5 Integration + Python Analysis Workflow        |
| `Stage4.3_convective_root_cause.md` | Stage 4.3 — Root-Cause Analysis: Convective-Adjustment Guard Cycling        |
| `Stage4.3b_eos_precision.md`        | Stage 4.3b — IEEE-754 / Float-Precision Verification of the EOS Root Cause  |
| `Stage4.4_precision_study.md`       | Stage 4.4 — Precision-Safe Convective Criterion: Controlled Numerical Study |

## Status

- **ARCHIVED** — stage materials are complete and not edited retroactively.
- Current model state: `../../../model/`; decisions: `../../../DECISIONS.md`.
- General navigation: `../../README.md` → `../../INDEX.md`.
