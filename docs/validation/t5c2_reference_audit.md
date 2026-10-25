# T5-CORRECTIVE-2 — Reference Document Audit

**Date:** 2026-10-25
**Scope:** search for storm-stabilization guidance in the original model
references.

## Files searched

| Reference | Present in workspace? | Result |
|---|---|---|
| `Dmitriev.txt` | **No** | no source file found under the repository or adjacent workspace |
| `Nesterov_last.txt` | **No** | no source file found |
| `model_all.txt` | **No** | no source file found |
| `Iceberg_1.docx` | **No** | no source file found |

`find` over the repository and `/home/vlad/Programing_work/vscode_work` (max
depth 4) returned no copies. The repository only contains citations and
historical comments referring to these documents.

## What the current code contains

- FCT advection (`advection_3d_s/t`) with the historical anti-diffusion term
  intentionally disabled (`CDY*0`, T-02).
- CA with the historical `0.9e-7` density threshold and a 1000-iteration
  guard; potential-density CA and f64/N² variants exist behind OFF switches
  (T-25/T-27).
- No storm-specific branch, gust handling, adaptive Δt, boundary radiation, or
  salinity-positivity limiter.
- Boundary conditions: clamped η on three edges (zero tidal forcing), no
  radiation condition; velocity no-gradient.

## Conclusion

**No reference for storm stabilization is available in this checkout.** The
original source files are absent, so no claim can be made that the historical
model contained a storm-safe mechanism. The existing storm behaviour must be
treated as an undocumented legacy limitation and diagnosed from the code and
outputs (Phase 2/3).
