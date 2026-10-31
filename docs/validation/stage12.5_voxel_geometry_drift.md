# Stage 12.5 — Voxel Geometry Driving Drift + Frontal Area

**Status:** COMPLETE (implementation + tests; `VOXEL_ENABLED` default OFF).
**Base:** `5a016be` (Stage 12.4). **Decision:** D‑56.
**Scope:** voxel geometry → drift forces (mass, frontal/wetted areas, draft);
metacentric estimate. No Stage 11 ocean / reanalysis reader / provider change;
bulk drift path unchanged when `VOXEL_ENABLED=OFF`.

## 1. Frontal area (PDF §13.2)

New `voxel_iceberg_get_frontal_area(vox, flow_angle, A_perp, A_sub_proj)`.
For every solid voxel (`φ > 10⁻¹²`) the neighbour **in the flow direction** is
tested; if it is empty/outside the domain the voxel contributes
`φ·A_face·|cosθ|` (x‑face, `A=dy·dz`) and/or `φ·A_face·|sinθ|` (y‑face,
`A=dx·dz`). For an arbitrary angle both contributions are summed:
```
A_perp     = Σ_solid      φ·( |cosθ|·dy·dz·[x-exposed] + |sinθ|·dx·dz·[y-exposed] )
A_sub_proj = same sum restricted to submerged voxels
```
`A_perp` is the whole projected silhouette; `A_sub_proj` is the submerged
projection used for water drag. The flow direction is uniform over the
iceberg (documented approximation; depth‑resolved direction is a 12.6 item).

**Correction to the prompt’s Test‑2:** at 45° a cube’s true projected
silhouette is `a²(|cos|+|sin|) = 14142 m²`, not `7071 m²` (which is only the
single upstream face and ignores the orthogonal face). The implementation and
test use the physical silhouette (14142, 1%); this is documented as a
prompt‑vs‑physics correction (PDF §13.2 “projected area”).

## 2. Drift integration (one‑way, gated)

`iceberg_dynamics.f90` now imports:
`voxel_geometry_active`, `voxel_geometry_mass`, `voxel_geometry_draft`,
`voxel_geometry_drag_areas` (from `iceberg_thermodynamics`). When
`VOXEL_ENABLED=ON`:
- **mass** = voxel mass (not `ρ L W H`);
- **draft** = voxel Archimedes draft (used to build the forcing profile);
- **wind drag** `A_sail` = total exposed voxel surface (`exposed_area`, PDF
  §13.3);
- **water drag** `A = A_sub_proj` at the angle of the depth‑averaged relative
  current (`atan2(Δv,Δu)`), for both Method A and Method B. (Method A’s
  per‑layer prism side areas are replaced by the projected‑area form when the
  voxel geometry is active; the bulk path is untouched.)
When `VOXEL_ENABLED=OFF` (default) every one of these branches is skipped and
the prism formulas run **bit‑identically**.

```
F_water = ½ ρ_w C_Dw A_sub_proj |u_rel| u_rel
F_wind  = ½ ρ_a C_Da A_sail     |v_rel| v_rel
a       = F / M_voxel
```

## 3. Metacentric stability (PDF §13.4) — estimate, no capsize dynamics

`voxel_iceberg_get_stability(vox, GM, BM, BG, I_wp, V_sub)`:
`V_sub = mass/ρ_w`; waterplane extents from submerged voxels;
`I_wp = L_eff·W_eff³/12` (transverse); `BM = I_wp/V_sub`;
`z_g` = φ‑weighted centroid; `z_b = draft/2`; `BG = z_g − z_b`;
`GM = BM − BG`. For the 100 m test cube `GM ≈ 3.67 m` (positive/stable).
`GM < 0` is **reported, never acted on** (no capsize dynamics — out of scope).

## 4. Phase‑6 explicit‑scheme bug — already fixed

The explicit phase‑change clamp in `solve_heat_conduction` already uses the
energy‑consistent `dφ = φ·c·(T−T_f)/L` (fixed in Stage 12.4A, commit
`3e3ec4a`). No further change was needed; verified by inspection and by the
A‑T6 closure tests.

## 5. Tests (`test/test_voxel_drift.f90`, CI‑safe synthetic)

| Test | Result |
|---|---|
| T1 cubic 10³, θ=0 | `A_perp = 10000.00 m²` (analytic 10000, <1%); `A_sub_proj=9000` (submerged only, ≤ A_perp) |
| T2 cubic, θ=45° | `A_perp = 14142.14 m²` = analytic silhouette (1%); the prompt’s 7071 is a single‑face projection (documented) |
| T3 melted half‑width | `A_perp 10000 → 5000 m²` (exactly halves) |
| T4 integration (10×3600 s, profile) | no NaN; mass 4.6592e8→4.6329e8 kg; draft 70.82→70.42 m; `A_perp 6400→6319.5`; `A_sail=9600` |
| T5 stability | `GM=3.6746`, `BM=9.4139`, `BG=5.7393 m`, `V_sub=8.85e5 m³` |
| T6 gated drift interface (TEST‑ONLY enable hook) | active; `mass=9.10e8 kg`, `draft=88.52 m`, `A_sub=9000`, `A_sail=14000` |
| `test_voxel_integration` | added A_perp check: 29595 m² (>0, finite); still PASS |

Full `fpm test` battery: **exit 0, STOP 0 = 77, 0 failed**; strict build
(`-Wall -Wextra -fcheck=all -ffpe-trap=invalid,zero,overflow`) clean.

## 6. Known limitations

- **Uniform flow direction** over the iceberg; no depth‑resolved projected
  area / per‑layer voxel drag (12.6).
- **A_sail = total exposed surface** (PDF §13.3), not a projected sail area;
  this over‑estimates wind drag for oblique wind (documented).
- **Metacentric estimate** uses waterplane extents, not the exact second
  moment of the waterplane; no capsize/roll dynamics.
- Grid rotation (~50°) neglected in `u_rel` (consistent with existing
  dynamics).
- Concave silhouettes can double‑count exposed faces (convex assumption);
  the iceberg is typically convex.
- One‑way: no feedback to ocean/atmosphere (D‑51).

## 7. Files

- Modified: `src/voxel_iceberg.f90` (frontal area, stability),
  `src/iceberg_thermodynamics.f90` (public geometry wrappers + TEST‑ONLY
  enabler), `src/iceberg_dynamics.f90` (gated use of voxel mass/draft/areas).
- New test: `test/test_voxel_drift.f90`; `test_voxel_integration.f90` updated.
- Docs: this report, D‑56, `STAGE12_PREPARATION.md`,
  `model_physics_status.md`, `KNOWN_ISSUES.md`, `AGENTS.md`, `CHANGELOG.md`,
  `README.md`.
