# Current-state model document — Stage 12.22 audit

**Audited source:** `docs/references/Iceberg/Iceberg_Model_Current_State.tex`
(and its supplied PDF rendering).  
**Requested file:** `Моделирование_термодинамики_айсбергов.docx` — not present
in the repository or under `/home/vlad`; the supplied PDF/TeX pair was used as
the current-state substitute.  
**Scope:** documentation only. Stage 12.22 made **no Fortran changes**.

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

The PDF rendering was not rebuilt because no LaTeX engine (`xelatex`,
`lualatex`, `pdflatex`, `tectonic`) is installed on this workstation. The source
`.tex` is corrected; the supplied PDF remains the pre-audit rendering.
