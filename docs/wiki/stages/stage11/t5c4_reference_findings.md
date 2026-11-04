# T5-CORRECTIVE-4 — Reference Findings

**Date:** 2026-10-25
**Requested .docx files:** `Iceberg_1.docx`, `Iceberg_Voxel_Thermal_Model.docx`
— **not present** anywhere under `/home/vlad` (searched repository and home).
They could not be copied; this is recorded rather than fabricating a file.

**Available source:** `docs/references/Iceberg/Iceberg_Voxel_Thermal_Model_8.pdf`
(32 pages, Russian). Text extracted for review.

## What the PDF contains

- Voxel (cubic) iceberg thermal model: temperature per voxel, ice–ice
  conduction, ice–water Stefan/three-equation boundary, ice–air surface
  balance, voxel removal during melt.
- Numerical stability condition for the **ice heat-conduction** scheme
  (section 11: Δt ≤ C·c/Σ G_f; standard 3D explicit conduction limit).
- No ocean EOS, density (RO), salinity advection, CA, or storm-forcing
  guidance. Its stability discussion applies to the iceberg heat solver, not
  the ocean model.

## Conclusion

The added PDF is relevant to the future iceberg module, not to the ocean
density-repair problem. The requested .docx references are absent, so no
additional density/stability/storm guidance can be extracted from them.
