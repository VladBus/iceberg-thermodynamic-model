# Current-state model document — Stage 12.22 audit

**Audited source:** `docs/references/Iceberg/Iceberg_Model_Current_State.tex`
(and its supplied PDF rendering).  
**Requested file:** `Моделирование_термодинамики_айсбергов.docx` — not present
in the repository or under `/home/vlad`; the supplied PDF/TeX pair was used as
the current-state substitute.  
**Scope:** documentation only. Stage 12.22 made **no Fortran changes**.
**Provenance:** Fortran/physics base is `cd33f0f` (Stage 12.20); `git diff
cd33f0f..34e1f89 -- src app` is empty. Validation-only commits are `18566e9`
(original Stage 12.22), `d7476bd` (12.22a), and `34e1f89` (12.22b);
none changes Fortran. Stage 12.22a corrected only Python post-processing
(`rho_ice` 916.7 → 910, reliability, Taylor/B3/B4 presentation); Stage 12.22b (`34e1f89`)
fixes whole-group B3 bootstrap, the B4 description, report/CSV consistency and
artifact regeneration. Neither changes model physics.

| Claim / item | Actual code | Action |
| --- | --- | --- |
| Ice density | `src/iceberg_types.f90`: `RHO_ICE=910.0`; `RHO_ICE_WATER_RATIO=910/1028` | The document already says 910; the Python validation was corrected from 916.7 to 910.0. |
| Connectivity interval | `voxel_iceberg_set_connectivity_hours` default **1 h**; environment `VOXEL_CONNECTIVITY_HOURS`; clamped to at most **6 h**; Stage 12.20 runs used **6 h** | Replaced the unconditional “every 6 h” statement by default/configuration/experiment values. |
| Grid | software defaults `VOXEL_NX/NY/NZ=10`, `VOXEL_DX/DY/DZ=10 m`; scientific target `100³/1 m`; Enderlin test grid `8³/12.5 m` | Separated default, scientific, and Enderlin configurations. |
| PCG maximum | `cg_maxit = 10*Nx*Ny*Nz` by default; `ICEBERG_CG_MAXIT` override; solver uses at least 10 iterations; `ICEBERG_CG_TOL=1e-10` | Replaced the fixed “1000 iterations” statement and table value. |
| `VOXEL_PHI_CONN` | default `0.3`; six-face components use cells with `phi > phi_conn` | Confirmed and retained. |
| `VOXEL_MELT_CAP` | default `0.20`; per-voxel cap, components scaled proportionally | Confirmed and retained. |
| `ICEBERG_THETA` | default `0.5` (CN); `1.0` = backward Euler; Rannacher after geometry change | Confirmed and retained. |
| Step order | interface flux → CN thermal solve → phase clamp → boundary melt/cap → flush/connectivity/compaction → dynamics → ledger | Confirmed; document order matches the implementation. |
| Atmosphere path | `voxel_model_step` passes `autonomous_air=.true.`; SW/LW/SH/LH are built from ERA5 or constant atmosphere; no double application of the bulk `Q_net` | Made explicit in the document. |
| Implemented / disabled / future | waves implemented but OFF by default; sea-ice drag, capsize, tides, two-way coupling, and subgrid melt are not implemented; future directions are in §14 | Confirmed; no change to formulas. |
| Monospace/Cyrillic | Courier New has no Cyrillic script coverage for polyglossia; Consolas has Cyrillic and is available on Windows | Build-required minimal change: Consolas is now the first `\setmonofont` choice, with the old fallback chain retained. |

## 12.22c build (current-state PDF)

The current PDF **was rebuilt** from the corrected `.tex` with the existing
Windows TeX Live 2026 installation:

- engine: `XeTeX 3.141592653-2.6-0.999998 (TeX Live 2026)`;
- executable: `D:\texlive\2026\bin\windows\xelatex.exe`;
- build directory: `/mnt/d/iceberg_tex_build_34e1f89`;
- source SHA256: `d6eac75035ce2d1bd817123a66ca25daf42f9e397a639368b510f32bc769b0f2`;
- PDF SHA256: `9134a75341d816a0c1b100240680822d9e79d0189478da9a9c5fd65afeea1ce9`;
- result: 17 pages, 213 290 bytes, A4, PDF 1.7;
- passes: first pass 16 pages with rerun warning; second pass 17 pages with
  “Label(s) may have changed”; final stabilization pass 17 pages with no
  undefined references, citations or labels. Only underfull horizontal boxes
  remain (typographic warnings, not missing content).
- fonts: Times New Roman, Consolas, CM math fonts; all embedded with Unicode
  maps. Consolas is the first monospace choice because Courier New lacks
  Cyrillic coverage for `polyglossia`; old fallback chain remains.
- PDF inspection: `pdfinfo`, `pdffonts`, `pdftotext`, `pdftoppm` from TeX Live;
  first pages, equations, long table, bibliography visually checked.
- old PDF backup (outside git):
  `/mnt/d/iceberg_tex_build_34e1f89/old_pre_12.22c.pdf`
  (SHA256 `26cad14bf808a0b438e39366585f12d66fb209cdc16e3fbfa1a9232e814ab961`).

The `.tex` uses `fontspec`, `polyglossia` (Russian), `amsmath`, `geometry`,
`setspace`, `booktabs`, `longtable`, `array`, `titlesec`, `hyperref` and TeX Gyre
fonts; all were present. The 12.22b commit (`34e1f89`) is validation/docs-only
and does not alter the model equations.
