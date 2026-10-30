# Stage 12.4 — Crank–Nicolson Core + Three-Equation Stefan Interface

**Status:** **PART A COMPLETE** (CN core + geometry fix + flush); **PART B** (three-equation Stefan, Part B) committed separately.
**Base:** `d608973` + docs commit `4b34a4c` (`Stage12_Iceberg_Transition.md`).
**Authority:** Transition doc §6.2 / §7; PDF §4.2, 5.2–5.3, 6.1–6.10, 8.1, 9.1–9.4, 11.1–11.2, 12.1–12.2.

## Part A — Crank–Nicolson thermal core + 3D geometry fix

### A1/A2. θ‑scheme and PCG solver
For active voxels (`φ > 10⁻¹²`) with `C_i = φ_i ρ_ice c_ice V`:

```
(C_i/Δt) (T_i^{n+1} − T_i^n) = θ F_i(T^{n+1}) + (1−θ) F_i(T^n),  θ = ICEBERG_THETA = 0.5
```

The symmetric positive‑definite 7‑diagonal system is solved with **PCG + Jacobi**,
relative‑residual tolerance `ICEBERG_CG_TOL = 1e−10`, warm start `T^n`.
`θ = 1` is backward Euler (used by Rannacher). Diagnostics: CG iterations and
final residual per step (getter `voxel_iceberg_get_solver`).

Boundary conditions are **inside the matrix** (doc §6.2 item 4):
- **Submerged face** (Dirichlet): `G_b = 2 k_ice A_f / h_norm`, `T_b = Tf(S,P)`
  at face depth; `θG_b` on the diagonal, `G_b T_b − (1−θ)G_b T^n` on the RHS.
- **Exposed face** (Robin, linearised): sensible `h_s A_f` fully implicit
  (`h_s = C_D ρ_air c_p max(wind, 0.1)`), `A_f Q_net` explicit.
  **No Ga term:** `Q_net` (= `diag%q_net_surface`) already contains net
  LW/SW/latent from the Stage‑10.2 balance; a local `4εσT̄³` linearisation
  would double‑count. (If `Q_net` is ever computed locally against the voxel
  `T_s`, the PDF §11.1 linearisation must be added — recorded limitation.)
- `Tf(S,P)` reuses the existing `ocean_freezing_point(salinity_mass, depth_m)`
  (PDF eq 8.1; S in kg/kg → ×1000 PSU internally, P = ρ_w g d/10⁴ dbar):
  `Tf(35,0) = −1.9223 °C`, `ΔTf(100 dbar) = −0.0753 °C` (unit‑tested).

### A3. Rannacher smoothing
After **any geometry change** (voxel removal), the next **2 steps use θ = 1**
(backward Euler), then return to CN. Verified: `rannacher_left = 2 → 1 → 0`
after a removal (A‑T8).

### A4/A5. Single clamp + geometry fix
Step order (doc §6.2 item 5 / PDF §12): state → boundary quantities from `T^n`
→ CN solve → **one** enthalpy clamp (`T>0 → dφ = φ c T/L`, `T=0`) → apply
boundary melt `φ −= Σ A_f m_f Δt/V` with per‑voxel **melt cap 0.20** (clip
counter) → erosion/flush → recompute state.

**Critical 3D fix (12.3 defect #1):** per‑face normal dimension
`h_norm = dx|dy|dz` for x|y|z faces; `dφ = m Δt/h_norm` and
`dT = q Δt/(ρ c h_norm)`. Proven with a non‑cubic voxel (`dx=50, dz=5`):
lateral/basal φ‑loss ratio = `dz/dx = 0.1` to 1e−12 (A‑T7).

**Energy‑consistent clamp:** because `C_i ∝ φ`, the clamp uses
`dφ = φ c T/L` (the pure `cT/L` form over‑melts when `φ<1`; this was found by
the analytical ablation audit, which now closes exactly).

### A6. Freezing / erosion / flush
`m ≥ 0` everywhere (spec assumption A5; no accretion). The 12.3 sub‑Tf freezing
test is rewritten to assert `m = 0`, φ unchanged.
On `φ < φ_min` the voxel is removed **with energy transfer** (doc §6.2 item v):
- `flushed_mass += φ̃ ρ V`;
- `flushed_energy += φ̃ ρ V [L_f + c(0 − T̃)]` (PDF eq 9.3);
- residual sensible `φ̃ ρ V c T̃` is distributed **equally to still‑active
  face‑neighbours** (`ΔT = share/C_nb`), conserving `Σ C_i T_i`; if no active
  neighbour exists, it is added to `flushed_energy`.

### A7. Configuration (all default to the new physics; explicit path intact)
`VOXEL_THERMAL_SCHEME = cn|explicit` (default **cn**); `ICEBERG_THETA` (0.5);
`ICEBERG_CG_TOL` (1e−10); `ICEBERG_CG_MAXIT` (10·N); `VOXEL_MELT_CAP` (0.20).
`VOXEL_THERMAL_SCHEME=explicit` reproduces the 12.3 sub‑stepped explicit path
(with the geometry fix and `m≥0`).

### Part A tests (CI‑safe, synthetic, no `.nc`)
| Test | Result |
|---|---|
| A‑T1 adiabatic closed box, 100×3600 s | `ΣC_iT_i` drift **1.58e−10** (<1e−8); φ unchanged |
| A‑T2 dt = 1e6 s | stable, no NaN, T within initial [min,max] |
| A‑T3 temporal order (dt=3000 vs 1500) | err 2.995e−6 / 7.495e−7, **ratio 3.996** (~2nd order) |
| A‑T4 CN vs explicit (Fo≈1e−4) | `max|ΔT| = 2.65e−8` (≤1e−6) |
| A‑T5 steady two‑face Dirichlet | max deviation from linear **5.6e−12** |
| A‑T6i exact ablation (T₀=0, T_b=+2) | melt depth = E_in/(ρL) to **<1e−6**; vs q₀t/(ρL) within 2% (CN O(dt)) |
| A‑T6ii cold ice (T₀=−5) | global energy balance closes (flux = latent + sensible + sensible of melted mass); fitted exponent **1.23** reported — **fallback**: half‑cell fixed‑T_b is constant‑flux, whose late melt is linear, not √t (fixed‑T similarity deferred to 12.7a) |
| A‑T7 non‑cubic geometry | lateral/basal ratio = **0.100000000** (1e−12) |
| A‑T8 Rannacher after removal | flag 2→1→0; no NaN |
| A‑T9 both schemes | 12.3 behaviour (melt, φ_min removal) passes for `cn` and `explicit` |

CG statistics (tests): adiabatic 6³ cube → 3 iterations/step; steady profile
and phase tests converge in a few iterations; residual always < 1e−10.
Full `fpm test` battery and strict build are run for the commit.

## Part B — three‑equation Stefan + profiles + u_rel

### B1. Profile API
`voxel_iceberg_step_profile(vox, dt, ocean_profile, v_ice_u, v_ice_v, atmos_T,
atmos_Q, atmos_wind, basal, lateral, surface)` uses the **same `ocean_profile`
the bulk path receives**. `profile_at(prof, d)` linearly interpolates
`T,S,u,v` between levels (PDF eq 6.4); below the deepest level it uses the last
wet level with `u=v=0`; above the shallowest it uses the first level.
`iceberg_thermodynamics` passes the profile it already has and
`state%u,state%v` as the iceberg velocity (the existing module already treats
those as east/north; the ~50° grid rotation is neglected — documented).

### B2. Three‑equation interface (PDF 6.1–6.10, 8.1)
For each **submerged face** at depth `d_f = draft − z_face`, with
`γ_T = KT·u_rel`, `γ_S = KS·u_rel`, `KT=1.1e-3`, `KS=3.1e-5`:
```
S_B(m) = ρ_w γ_S S_w / (ρ_w γ_S + ρ_ice m)                    [S_ice=0]
T_B(m) = Tf(S_B, P_f),   P_f = ρ_w g d_f / 1e4                 [dbar]
F(m)   = ρ_w c_w γ_T (T_w − T_B) − ρ_ice L_f m
         − (2 k_ice/h_norm)(T_B − T_voxel)                     [W/m²]
```
`ocean_freezing_point` takes salinity **mass fraction** and depth [m] and
converts internally (`S_PSU=S_kgkg·1000`, `P=ρgH/1e4`); the conversion happens
at the profile boundary, exactly once. **F(m) is strictly decreasing**;
if `F(0) ≤ 0` then `m = 0` (**no accretion**, spec A5). Otherwise
`m_hi=1e-5` is doubled (≤50×) then **bisection** (≥60 iterations, until
`Δm<1e-13` or `|F|<1e-9`). `γ_S=0` (`u_rel=0`) is guarded explicitly → `m=0`.
`m` updates `φ` via `Σ_f A_f m_f Δt/V` with the A6 melt cap. The converged
`T_B` is fed into the CN matrix as the submerged Dirichlet value
(`tb_override`), so the interface is implicit.
Part A's forcing‑convection melt remains selectable; it now uses **per‑face
`l_char`** (basal/top: `max(nx dx, ny dy)`; lateral: `max(draft, dz)`), fixing
12.3 defect #3. The three‑equation Stanton form is length‑independent, so
`l_char` does not appear there.

### B4/B5. Diagnostics
Per step: mean `T_B`, `S_B`, `u_rel` over submerged faces, deepest‑face and
waterline‑adjacent `T_B`, number of faces, CG iterations/residual, clip count,
flushed mass/energy, melt by component (basal/lateral/surface, **kg/s**).
Getter `voxel_iceberg_get_stefan` (+ existing `get_solver/get_flush/get_melt`).

### Part B tests
| Test | Result |
|---|---|
| B‑T1 single face vs brute‑force 200‑iter bisection | `m = 4.1319e‑6 m/s`, diff **7.4e‑14**; `S_B=0.01606 < S_w`; `Tf(S_w,P) < T_B=-0.8839 < 0` |
| B‑T2 PDF §6.2 worked example (`S_w=35`, `ΔT=3 K`, `u_rel=0.1`, `h=0.5`) | `m/m_ref = 0.993` (m≈0.248 m/day), `S_B=19.23 PSU`, `T_B=−1.041 °C` — all within 20% |
| B‑T3 salinity guard | `Tf(35,0)=−1.9223`; kg/kg-as-PSU gives `|Tf|=0.002` (order guard) |
| B‑T4 pressure | `ΔTf(300 m)=−0.2277 °C` (−0.226±0.005); **m increases with depth** because `Tf` falls with `P` (PDF eq 8.1; the prompt's “decreases” is physically inverted) |
| B‑T5 u_rel | `m(0.2)/m(0.1)=2.03` ∈ [1.3,2.5]; co‑moving → `u_rel=0 → m=0` |
| B‑T6 stratified profile | `m_top=3.56e‑6` vs `m_deep=6.78e‑7` (>3×); per‑depth forcing used |
| B‑T7 no accretion | sub‑Tf ocean → `m = 0` |
| B‑T8 integration (24×3600 s, profile API) | no NaN, φ∈[0,1], mass 4.6592e8→4.6051e8 kg, draft 70.82→69.99 m; **mass budget closes to 8.96e‑16** (melt rates + flushed mass) |

**CG statistics:** the 6³ adiabatic problem converges in **3 PCG iterations**
per step at residual <1e‑10; the 1D/steady/phase problems converge in a few
iterations (<10). Temporal order (A‑T3) **3.996**; Rannacher sequence **2→1→0**.

### Documented deviations / corrections
1. **No Ga longwave linearisation** (doc §6.2): `Q_net` already contains net
   LW/SW/latent; adding `4εσT̄³` would double‑count.
2. **A‑T6(ii)**: the half‑cell fixed‑`T_b` boundary is **constant‑flux**, whose
   late‑time melt is linear, not `√t` (that is the fixed‑surface‑temperature
   Neumann solution). Per the approved fallback, the test asserts the global
   energy balance and reports the fitted exponent (1.23); the exact fixed‑T
   similarity stays deferred to 12.7a.
3. **B‑T4**: melt increases with depth for identical `T_w` (PDF eq 8.1), not
   decreases as the prompt stated.
4. **Energy‑consistent clamp** `dφ=φcT/L` (the pure `cT/L` over‑melts when
   φ<1; found via A‑T6i and fixed).

## Known limitations (carried)
- No cavity/channel exchange, no spray/waterline band; γ coefficients
  uncalibrated; no natural convection at `u_rel→0`; no accretion (spec A5);
  `c_ice = 2100` kept for bulk consistency (PDF Appendix A suggests 2009 —
  open calibration question); φ_min = 0.01 retained (PDF 0.05 is an example).
- Model‑grid rotation neglected in `u_rel` (consistent with existing dynamics,
  which already treats `state%u,v` as east/north).
- `Q_net`‑based air flux: Ga linearisation deferred (see A2 note).
