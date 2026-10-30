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

## Part B — three‑equation Stefan (see Part B section, appended on commit B)

## Known limitations (carried)
- No cavity/channel exchange, no spray/waterline band; γ coefficients
  uncalibrated; no natural convection at `u_rel→0`; no accretion (spec A5);
  `c_ice = 2100` kept for bulk consistency (PDF Appendix A suggests 2009 —
  open calibration question); φ_min = 0.01 retained (PDF 0.05 is an example).
- Model‑grid rotation neglected in `u_rel` (consistent with existing dynamics,
  which already treats `state%u,v` as east/north).
- `Q_net`‑based air flux: Ga linearisation deferred (see A2 note).
