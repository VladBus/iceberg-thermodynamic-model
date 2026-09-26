# Stage 10.18A — Lateral Melt Parameterization Research Audit

**Date:** 2026-09-18
**Status:** COMPLETE — research/sensitivity/parameterization audit; **no production physics change**
**Commit:** `022f871` baseline → this stage
**Scope:** quantify how much the dominance of lateral melt in the production model
depends on the legacy constant-coefficient formulation `m_l = C_LATERAL · ⟨ΔT⟩_D`.
Research layer: `python/validation/lateral_melt.py`; tests:
`python/tests/test_lateral_melt_parameterizations.py`; analysis:
`python/analysis/stage10_18a_lateral_melt.py`; outputs (gitignored):
`data/output/stage10.18a/`.

---

## 1. Objective

Answer, quantitatively and without changing production physics:

> Is the dominance of lateral melt in the current model (96.8 % of 30-day mass
> loss, Stage 10.17) a physically robust result, or in significant part a
> consequence of the specific legacy parameterization
> `m_l = C_LATERAL · ⟨ΔT⟩_D`, `C_LATERAL = 1e-6 m/(s·K)`?

Compare (1) the legacy velocity-independent formulation, (2) velocity-dependent
formulations (model-consistent bulk closure; Bigg et al. 1997 forced
convection; FitzMaurice–Cenedese–Straneo 2017 plume regime; Neshyba–Josberger
buoyant term), (3) the submerged-area vs full-height geometry conventions,
(4) wave erosion (assess availability), and (5) the resulting mass/geometry
evolution over the 30-day real-forcing TEST_11.

Stage 10.18A is a **research / sensitivity / parameterization audit**, not a
production physics replacement (explicit stage rule). Production Fortran is
**byte-identical** after this stage (git diff on `src/` and `test/` is empty).

## 2. Baseline (from Stage 10.17, preserved)

| Quantity | Value | Source |
| --- | --- | --- |
| Legacy formula | `m_l = C_LATERAL · ⟨ΔT⟩_D`, `C_LATERAL = 1e-6 m/(s·K)` | `src/iceberg_thermodynamics.f90` (compute_lateral_melt) |
| `⟨ΔT⟩_D` (depth-average) in TEST_11 | 3.008 K (recovered from `ml_mday`) | data/output/stage10.17 |
| Lateral melt rate (TEST_11) | 0.2599 m/day, near-constant (±0.15 % as draft shrinks) | stage10.17 |
| 30-day mass change | −15.41 % (M0 909.80 → 769.58 Mt) | stage10.17 |
| Component shares | lateral 96.8 %, basal 3.0 %, surface 0.12 %, vapor 0.08 % | stage10.17 |
| 90-day diagnostic | −42.2 % (Q1 atmosphere; ocean frozen at January; **annual extrapolation premature**) | stage10.17 (F11) |
| Mass consistency | `M ≡ ρ_i·L·W·H` (max 1.5e-5 rel); model budget closure 5e-4 % (30 d) | stage10.17 |
| Production geometry update | `dL = dW = −m_l·dt`; `dH = −dt·(m_b + m_s − m_v/ρ_i)`; `dV_lat = H(L+W)·m_l·dt` | `src/iceberg.f90` (iceberg_update_geometry) |
| Dead helpers' convention | `A_lat = 2(L+W)·D` (submerged full perimeter) | `src/iceberg_geometry.f90` (compute_mass_budget / melt_volume_rates, unused) |
| Stage 10.17 F2 | lateral full-height vs submerged-depth convention ⇒ H/D = 1.13 (~13 % of lateral loss) | stage10.17 report |

## 3. Production implementation (exact)

Exact from source (not reconstructed from docs):

```fortran
! src/iceberg_forcing.f90
function depth_averaged_thermal_forcing(prof, draft) result(delta_t_avg)
    ! <ΔT>_D = (1/D) ∫₀ᴰ max(0, T(z) − Tf(z)) dz
    ! piecewise-constant layers (mid-level T/S, layer thickness Δz),
    ! deepest-level constant extrapolation below max model level
    integral = 0.0; total_depth = 0.0
    do k = 1, prof%nlevels
        z_top = prof%z(k) − 0.5·dz(k); z_bot = min(z(k)+0.5·dz(k), draft)
        if (z_top ≥ draft) exit
        ΔT = T(k) − Tf(S(k), z(k)); if (ΔT > 0) integral += ΔT·(z_bot−z_top)
        total_depth += (z_bot − z_top)
    end do
    if (draft > max(z))  integral += (T_deep − Tf_deep)·(draft − max(z))
    delta_t_avg = integral / total_depth

! src/iceberg_thermodynamics.f90
subroutine compute_lateral_melt(prof, draft, delta_t_avg, m_lateral)
    delta_t_avg = depth_averaged_thermal_forcing(prof, draft)
    if (delta_t_avg > 0.0) then; m_lateral = C_LATERAL·delta_t_avg
    else; m_lateral = 0.0; delta_t_avg = 0.0; end if

! src/iceberg.f90 — iceberg_update_geometry
state%H = H − dt·(m_basal + m_surface − m_vapor/ρ_i)
state%L = L − dt·m_lateral
state%W = W − dt·m_lateral
dV_lateral = (H_old·W_old + L_old·H_old)·dt·m_lateral   ! = H(L+W)·m_l·dt
```

Facts fixed in §3:

| Item | Value |
| --- | --- |
| Formula | `m_l = C_LATERAL·⟨ΔT⟩_D` (m/s), `C_LATERAL = 1.0e-6 m/(s·K)` |
| Driving ΔT | depth-averaged over the draft, `⟨ΔT⟩_D`, EOS-80-inconsistent per layer (T(k) − Tf(S(k), z(k))), non-negative |
| Area used in update | full-height half-perimeter equivalent `A = H(L+W)` (perimeter 2(L+W)·H is NOT used; L and W each shrink at m_l) |
| L/W/H update | L, W both `−m_l·dt`; H from basal+surface+vapor only |
| Mass–volume link | `diag%lateral_mass_loss = ρ_i·(H·W+L·H)·dt·m_lateral` |
| U_rel dependence | **none** (formula has no velocity argument) |
| Depth dependence | only through `⟨ΔT⟩_D` (integration domain); melt rate applied to full H |
| Wave effects | **absent** |
| Coupling with thermal model | **none** (lateral not in `q_cond`/`q_bot`; T_ice not used) |

Correctness of the legacy formula implementation: **VERIFIED** — the
independent Python reference layer reproduces the production `ml_mday` exactly
(replay reconstructs production cumulative lateral mass loss; baseline replay
matches production 30-day state to 0.02 pp).

## 4. Literature basis

Verified sources (full audit: `python/validation/lateral_melt.py` provenance +
this section; unverified items are explicitly marked).

| Parameterization | Equation | Provenance | Validity / conventions |
| --- | --- | --- | --- |
| Weeks & Campbell 1973 | turbulent flat-plate heat transfer `q = h·A·ΔT`, `R = h·ΔT/(L·ρ_i)`; submerged face, relative free-stream velocity; **numerical Nu correlation not recoverable from accessible copy** | J. Glaciol. 12(66) 495–507 | thermal forced convection; not mechanical erosion |
| Bigg-type forced convection (Bigg et al. 1997; coefficient quoted by FitzMaurice et al. 2017) | `M_b = K·|u_i − u_o|^0.8·(T_a − T_i)/L^0.2`, `K ≈ 0.58` (ocean, m/day units), `K ≈ 0.75` (lab) | Cold Reg. Sci. Technol. 26(2) 113–135; GRL 44 5637–5644 | relative iceberg–ocean velocity; thermal forced convection; original 1997 notation **not independently verified** |
| Neshyba–Josberger buoyant convection (fit quoted in Cenedese & Straneo 2023) | `M_v = a·ΔT + b·ΔT²`, `a = 7.62e-3 m/day/°C`, `b = 1.29e-3 m/day/°C²` | Annu. Rev. Fluid Mech. 55 377–402 | velocity-independent buoyant convection; often small in polar seas; ~0.2 m/day at upper parameterized values |
| FitzMaurice–Cenedese–Straneo 2017 (GRL, plume regime) | attached (`U < w`): `M = K·w^0.8·(T_p − T_i)/D^0.2`; detached (`U ≥ w`): `M = K·U^0.8·(T_a − T_i)/L^0.2`; `w ≈ 2.5 cm/s` (lab) | GRL 44 5637–5644 | relative velocity; highest uncertainty in plume temperature `T_p` (not a model state); lab-derived |
| Martin & Adcroft 2010 | buoyant-convection side melt `M_s = M_v` (only); full implementation details **not independently verified** | Ocean Modelling 34 111–124 (via C&S 2023 review) | — |
| White, Spaulding & Gammon 1980 (wave erosion); Kubat et al. 2007 (operational) | **equations/coefficients NOT retrievable** from primary sources during this audit → **NOT used** | — | wave erosion is mechanical; would require wave forcing absent from ERA5 Q1 |
| Cenedese & Straneo 2023 typical open-ocean *parameterized* maxima | basal ~1 m/day; side ~0.2 m/day; wave erosion 0.5–1.0 m/day | Annu. Rev. Fluid Mech. 55 | empirical parameterizations, sparse field validation; NOT universal validation |
| FitzMaurice et al. 2017 (Sermilik, Greenland) | mean side melt 0.06–0.10 m/day (attached regime); area-averaged observational estimate ~0.39 m/day | GRL 44 | fjord setting; tabular Greenland icebergs |

Repository literature matrix records (already at `docs/references/literature_matrix.md`,
Stage 10.9-verified DOIs): Weeks & Campbell 1973, Bigg 1997, FitzMaurice &
Stern 2018, Cenedese & Straneo 2023, Martin & Adcroft 2010 (keys present in
`docs/references/references.bib`).

## 5. Legacy formulation (Question A — is the formula implemented correctly?)

Reference implementation (independent NumPy, no production code import):
`python/validation/lateral_melt.py::legacy_lateral_melt_rate` +
`depth_averaged_thermal_forcing`.

Analytic checks (all pass, 458 checks total in the stage suite):

| Check | Result |
| --- | --- |
| `⟨ΔT⟩_D = 0` → `m_l = 0` (guard) | ✓ |
| linear scaling `m_l ∝ ΔT` (C_LATERAL constant) | ✓ (exponent dln m/dln ΔT = 1.000) |
| velocity independence (no U argument in formula) | ✓ (dln m/dln U = 0.000) |
| size independence (no L/D argument in formula) | ✓ (dln m/dln L = 0.000) |
| monotone non-decreasing in ΔT; non-negative; finite | ✓ |
| depth-average on synthetic profiles (single layer, uniform, extrapolation) | ✓ |
| **production reproduction**: recovered `⟨ΔT⟩_D` = 3.0080 K from `ml_mday`; replay reproduces Stage 10.17 (dM 15.43 % vs 15.41 %, lateral 96.83 % vs 96.8 %, L_f 92.21 m exact) | ✓ |

**Answer A: VERIFIED** — the legacy formula is implemented correctly relative to
its own definition. The constant coefficient (no velocity, no size, no wave
dependence) is a documented legacy simplification (Stage 9.1 §14), not a bug.

## 6. Full-height vs submerged geometry (Question B — geometry convention)

Exact comparison at the TEST_11 reference state (L = W = H = 100 m,
D = 88.521 m = H·ρ_i/ρ_w, m_l = 3.008e-6 m/s):

| Quantity | Full-height production `H(L+W)` | Submerged full-perimeter `2(L+W)·D` | Submerged half-perimeter `(L+W)·D` |
| --- | --- | --- | --- |
| Area [m²] | 20,000 | 35,409 | 17,704 |
| dV/dt [m³/s] | 0.06016 | 0.10651 | 0.05325 |
| Ratio vs production | 1.000 | **1.7704 = 2·ρ_i/ρ_w** | 0.8852 = ρ_i/ρ_w |

Three distinct conventions are telling *different* things:

1. **Depth convention (Stage 10.17 F2)** — same half-perimeter, H vs D: ratio
   `H/D = 1.1297`, i.e. production's full-height interpretation removes ~13 %
   more lateral volume than a submerged-depth interpretation *at the same
   perimeter convention*. This is the F2 quantity.
2. **Perimeter convention** — full perimeter `2(L+W)` vs the production
   "dimension-shrink" equivalent `(L+W)`: a factor 2 (each face retreats; the
   prism update encodes `dL = dW`, i.e. half the perimeter).
3. **Combined (submerged full-perimeter, the dead-helper convention)**:
   factor `2·ρ_i/ρ_w = 1.770` over production.

Volume-preserving prism representation: a per-face normal retreat `m_l` over the
submerged depth only removes `2(L+W)·D·m_l·dt`; mapped onto the prism
`(dL = dW = −r·dt)`, this requires `r = m_l·(2D/H) = m_l·1.7704`. The freeboard
is not physically eroded — the prism cannot represent a tapered (mushroom)
iceberg; this is an inherent representability limitation (documented).

**Answer B: DIAGNOSTIC/RESEARCH** — the production convention (full height,
half-perimeter) is internally consistent and correctly implemented; it differs
from the model's own dead-helper/documented submerged convention by a factor
1.77 (volume) and from a submerged-depth-only picture by 1.13. This is a
**modeling-choice ambiguity** (not a software bug), exactly as classified in
Stage 10.17 F2/F8.

## 7. Velocity-dependent formulations (Question C — sensitivity to velocity)

Three literature-based velocity-dependent variants were implemented
independently (see §4 for provenance):

| Variant | Formula (m/s unless noted) | Results in 30-day TEST_11 replay |
| --- | --- | --- |
| `BULK_FORCED` | `γ_T·⟨ΔT⟩_D/(ρ_i·L_f)`, `γ_T = Nu·k/D`, flat-plate Nu (Re < 5e5 lam `0.664Re^0.5Pr^(1/3)`, else turb `0.037Re^0.8Pr^(1/3)`), `Re = U_rel·D/ν` | `m_l` mean 0.0126 m/day (max 0.0377); dM 1.28 %; lateral share 60.6 % |
| `BIGG1997` | `K·U_rel^0.8·ΔT/L^0.2`, `K = 0.58` (m/day units) | `m_l` mean 0.0169 m/day; dM 1.54 %; lateral share 67.3 % |
| `BIGG_PLUS_BUOY` | Bigg + `aΔT + bΔT²` (Neshyba–Josberger) | `m_l` mean 0.0515 m/day; dM 3.58 %; lateral share 86.2 % |
| `FITZMAURICE_PLUME` | plume-regime piecewise (attached: plume-speed & D; detached: U & L; `T_p` approximated by ambient ΔT — documented) | `m_l` mean 0.0372 m/day; dM 2.74 %; lateral share 81.9 % |

**Scalings** (numeric exponents from the sensitivity matrix, independent of
assumed exponents):

| Variant | dln m/dln U | dln m/dln ΔT | dln m/dln L |
| --- | --- | --- | --- |
| LEGACY_FULL_HEIGHT | 0.000 | 1.000 | 0.000 |
| LEGACY_SUBMERGED | 0.000 | 1.000 | 0.000 |
| BULK_FORCED (turbulent) | 0.800 | 1.000 | 0.000 (side D-based); D⁻⁰² (γ_T ∝ D^(-0.2)) |
| BIGG1997 | 0.800 | 1.000 | −0.200 |
| BIGG_PLUS_BUOY | 0.663 | 1.050 | −0.150 |
| FITZMAURICE_PLUME | 0.800 | 1.000 | −0.200 |

The U^0.8 / U^0.5 exponents and the D^-0.2 / D^-0.5 size exponents match the
forced-convection closure and the laboratory literature (FitzMaurice et al.
2017). The legacy U^0 exponent is confirmed empirically.

**Key quantitative result (Question C):**

> The legacy constant `C_LATERAL = 1e-6 m/(s·K)` implies a side heat-transfer
> coefficient `γ_T = ρ_i·L_f·C_LATERAL = 304 W/(m²·K)`. Equating the
> model-consistent bulk forced-convection closure to this value at the TEST_11
> draft (D = 88.5 m) gives **U_eq = 0.30 m/s** relative flow. The simulated
> TEST_11 relative velocity at the draft is **0.005–0.027 m/s** (drift is
> Coriolis-limited, Stage 10.16). The legacy constant therefore behaves as if
> forced convection were acting at ~0.30 m/s — **10–60× the actual simulated
> relative speed**. At the actual TEST_11 speeds, every literature-based
> velocity-dependent formulation (bulk, Bigg, plume) yields mean lateral melt
> 0.013–0.052 m/day vs the legacy 0.26 m/day — a factor 5–20 lower.

Velocity convention used throughout: relative velocity between ocean and ice at
the draft, `U_rel = |u_ocean − u_ice|` (not iceberg drift speed, not a surface
current) — the convention required by the formulations. At TEST_11, U_rel is
small because both the drift and the (climatological, January-frozen) deep
current are small.

## 8. Wave erosion assessment

| Question | Answer |
| --- | --- |
| Wave erosion present in the model? | **No** (no wave term in `iceberg_thermodynamics`). |
| Wave forcing available? | **No** — ERA5 Q1 2020 merged file contains wind/msl/t2m/d2m/tcc/precip/sf only; no significant wave height/period. |
| Literature parameterization verified? | **No** — White et al. 1980 and Kubat et al. 2007 equations could not be retrieved from primary sources (librarian audit); not useable. |
| Observed erosion vs thermal melt? | Published "deterioration" contributions (e.g., Barents/Shtokman studies in `references.bib`) mix thermal melt and mechanical wave erosion; not partitionable with current forcing. |

**Verdict: NOT TESTABLE with the current forcing** — documented, no
implementation performed (explicit stage rule: do not implement wave erosion
without data/parameterization). Any future wave-erosion component needs (a) wave
hindsast forcing and (b) a verified primary-source formulation.

## 9. Sensitivity experiments

`data/output/stage10.18a/sensitivity_matrix.csv`: full grid ΔT ∈
{0.5, 1, 2, 3, 4, 6} K × U ∈ {0, 0.001, 0.01, 0.03, 0.1, 0.3, 1.0} m/s ×
L ∈ {10, 50, 100, 200, 300} m (D = 88.5 m) — 210 rows × 6 variants.
`parameterization_comparison.csv` gives rates/area/volume/mass at the reference
state (ΔT = 3 K, U = 0.1 m/s, L = W = H = 100 m):

| Variant | m [m/day] at ref state | A [m²] | dV/dt [m³/s] | dM/dt [Mt/day] |
| --- | --- | --- | --- | --- |
| LEGACY_FULL_HEIGHT | 0.2592 | 20,000 | 0.0600 | 0.471 |
| LEGACY_SUBMERGED | 0.2592 (rate) / 0.4590 (effective shrink) | 20,000 | 0.1062 | 0.834 |
| BULK_FORCED | 0.1066 | 20,000 | 0.0247 | 0.194 |
| BIGG1997 | 0.1097 | 20,000 | 0.0254 | 0.199 |
| BIGG_PLUS_BUOY | 0.1442 | 20,000 | 0.0334 | 0.262 |
| FITZMAURICE_PLUME | 0.1097 | 20,000 | 0.0254 | 0.199 |

Figures 1–4 visualise the ΔT, U, size dependences (see `plots/`).

## 10. TEST_11 comparison (30-day real-forcing, offline replay)

Production Fortran was NOT modified; the research comparison is an **offline
replay** through `python/validation/lateral_melt.py` on the production
trajectory (documented per stage rule: a velocity-dependent formulation cannot
be integrated into the existing forcing without changing production). The replay
uses the model's own update rule (`dL = dW = −m·dt`, `dH` from
basal+surface+vapor) and holds basal/surface/vapor rates and U_rel at
production values — a controlled first-order comparison. The replay baseline is
validated: it reproduces Stage 10.17 exactly (dM 15.43 % vs 15.41 %, lateral
96.83 % vs 96.8 %, L_f 92.21 m).

| Variant | ΔM [%] | lateral | basal | surface | vapor | L_f [m] | H_f [m] | mean m_l [m/day] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LEGACY_FULL_HEIGHT (production) | 15.43 | 96.83 % | 2.96 % | 0.12 % | 0.08 % | 92.21 | 99.47 | 0.2597 |
| LEGACY_SUBMERGED | 26.08 | 98.13 % | 1.70 % | 0.07 % | 0.05 % | 86.20 | 99.47 | 0.4599* |
| BULK_FORCED | 1.28 | 60.59 % | 36.88 % | 1.48 % | 1.05 % | 99.62 | 99.47 | 0.0126 |
| BIGG1997 | 1.54 | 67.34 % | 30.57 % | 1.22 % | 0.87 % | 99.49 | 99.47 | 0.0169 |
| BIGG_PLUS_BUOY | 3.58 | 86.21 % | 12.90 % | 0.52 % | 0.37 % | 98.46 | 99.47 | 0.0515 |
| FITZMAURICE_PLUME | 2.74 | 81.92 % | 16.92 % | 0.68 % | 0.48 % | 98.88 | 99.47 | 0.0372 |

\* effective horizontal shrink for the submerged full-perimeter convention
(`m_l·2·ρ_i/ρ_w`); the per-face submerged rate is the legacy 0.2592 m/day.

Figures 5–7: m_l(t), M(t), L/W/H/D(t) for all variants; Figure 8: mass-budget
stacked fractions; Figure 9: relative differences vs baseline; Figure 10:
model vs literature ranges.

**Interpretation (Question C quantified):** switching from the legacy constant
to any literature-based velocity-dependent formulation reduces the 30-day mass
loss from 15.4 % to 1.3–3.6 % and the lateral share from 96.8 % to 60–86 % at
TEST_11 conditions. The lateral share remains the largest single component in
most variants (because basal is also partly velocity-limited and the actual
U_rel is small everywhere), but the *absolute* lateral rate drops by 5–20×.
Conversely, adopting the submerged full-perimeter geometry with the same legacy
rate *increases* the loss by 1.7× (26.1 %). The result spans 1.3–26.1 % purely
through formulation choice: **the dominance of lateral melt is not a robust
physical outcome of the current model; it is dominated by the legacy constant
(≈ U_eq 0.30 m/s behaviour).**

## 11. Mass-budget consequences

For every applicable variant `M = ρ_i·L·W·H` is exact by construction (the
replay re-derives mass from the evolved geometry; production consistency is
unchanged). Budget closure per variant equals the production closure plus the
replay truncation (< 0.1 %). The key output is the collapse of the 30-day mass
loss from 15.4 % (legacy) to 1.3–3.6 % (velocity-dependent research variants) —
i.e. the qualitative conclusion of Stage 10.17/10.16 (near-linear lateral
erosion ⇒ L → 1 m in ~1 year under the legacy constant) is itself
formulation-dependent and does not robustly extrapolate.

## 12. Observational / literature comparison

Careful comparison (no direct `m_lateral_model` vs "observed total melt"
conflation; each entry states what is measured):

| Quantity | Value | What it is | Geometry / environment |
| --- | --- | --- | --- |
| Legacy model m_l (TEST_11) | 0.26 m/day | thermal side melt, depth-averaged, velocity-independent, full height | 100 m cube, Barents Q1 (ocean frozen Jan), U_rel 0.005–0.027 m/s |
| BULK/BIGG/PLUME (TEST_11 U) | 0.013–0.052 m/day | thermal forced convection (bulk/Bigg) or plume-closure side melt | same |
| C&S 2023 typical parameterized max | side ~0.2 m/day | thermal side melt (parameterized upper bound) | open ocean, sparse validation |
| FitzMaurice 2017 Sermilik mean | 0.06–0.10 m/day | thermal side melt (lab-derived attached-plume) | Greenland fjord, tabular icebergs |
| FitzMaurice 2017 area-averaged obs estimate | ~0.39 m/day | observational area-averaged side melt | Sermilik |
| C&S 2023 wave erosion max | 0.5–1.0 m/day | mechanical wave erosion | open ocean (not in model; not testable) |

The legacy 0.26 m/day lies *within* the broad literature range (between the
Sermilik model mean 0.06–0.10 and the observational estimate 0.39), but the
literature values are **not validation**: they come from a different region,
regime and definition, and the model's U- and wave-dependence is absent. No
claim of observational consistency is made (explicit stage rule).

## 13. Findings

| # | Finding | Classification | Evidence |
| --- | --- | --- | --- |
| L-01 | Legacy formula `m_l = C_LATERAL·⟨ΔT⟩_D` is implemented correctly (matches its own definition; production reproduced by independent reference layer) | VERIFIED | replay dM 15.43 %/lat 96.83 % vs production 15.41 %/96.8 %; `⟨ΔT⟩_D` = 3.008 K recovered |
| L-02 | Legacy is velocity- and size-independent (U⁰, L⁰, ΔT¹) | VERIFIED | numeric exponents 0.000/0.000/1.000 |
| L-03 | **Legacy constant is equivalent to forced-convection side melt at U_eq ≈ 0.30 m/s** (γ_T = 304 W/(m²·K), vs actual U_rel 0.005–0.027 m/s → factor 10–60) | RESEARCH FINDING | γ_T = ρ_i·L_f·C_L; U_eq solved from bulk closure |
| L-04 | At TEST_11 speeds every velocity-dependent research variant gives mean lateral melt 0.013–0.052 m/day (5–20× below legacy 0.26); 30-day ΔM 1.3–3.6 % vs 15.4 % | RESEARCH FINDING | 30-day replay, 6 variants |
| L-05 | Lateral share remains dominant (60–86 %) in most velocity variants at TEST_11 only because basal is also weak at low U_rel; the *absolute* lateral rate collapses | RESEARCH FINDING | replay component shares |
| L-06 | Geometry convention ambiguity confirmed quantitatively: submerged full-perimeter vs production full-height = factor 2·ρ_i/ρ_w = 1.77 (volume); depth-only H vs D = 1.13 (Stage 10.17 F2); dead helpers use submerged full-perimeter | DIAGNOSTIC (modeling choice, not bug) | exact geometry comparison |
| L-07 | Submerged full-perimeter with legacy rate raises 30-day ΔM to 26.1 % (1.7×) — same *per-face* rate, different area | RESEARCH FINDING | replay LEGACY_SUBMERGED |
| L-08 | Scalings of research variants (U^0.8 turb / U^0.5 lam, D^-0.2/D^-0.5, ΔT-linear) match the literature/analysis | VERIFIED | sensitivity matrix exponents |
| L-09 | Wave erosion: absent from model; no wave forcing; primary-source equation not retrievable → NOT TESTABLE | NOT TESTABLE | ERA5 Q1 variable list; librarian audit |
| L-10 | Empirical side-melt literature (Sermilik 0.06–0.10 model, 0.39 obs; C&S max 0.2) brackets the legacy 0.26 but does NOT validate it (different region/regime/definition) | REQUIRES FUTURE VALIDATION | §12 |
| L-11 | T-07 untouched: lateral-melt conclusions do not modify drift analysis (melt change is not drift evidence) | VERIFIED (scope) | drift terminology in replay unchanged; no trajectory-physics claim made |

No production-implementation bug was found (no `IMPLEMENTATION BUG` findings);
per stage rule, no Fortran regression test was created (no Fortran change).

## 14. Limitations

- **Offline replay**: research variants were not integrated into production
  Fortran; the trajectory forcing (U_rel, basal/surface/vapor, ⟨ΔT⟩_D recovered,
  at-draft/below-draft conventions) is held at production values, so per-variant
  geometry feedback on U_rel/forcing is neglected (first-order comparison).
- **ΔT in replay**: for the velocity variants the depth-averaged driving
  recovered from `ml_mday` is used; the at-draft `delta_t_ocean` = 3.885 K vs
  ⟨ΔT⟩_D = 3.008 K difference is a documented driver-proxy effect.
- `T_p` (plume temperature) is not a model state; the FitzMaurice attached
  branch uses the ambient ΔT proxy (documented approximation).
- Free-convection (buoyant) side melt at U → 0 is only represented in the
  Neshyba–Josberger term; the bulk/Bigg forced-convection closures give zero at
  U = 0 (identical limitation to the production basal closure).
- Literature: Bigg 1997 original notation, White 1980 / Kubat 2007 wave
  equations, Martin & Adcroft 2010 full implementation — not independently
  verified from primary sources; marked UNVERIFIED in §4.
- No wave data (ERA5 Q1) and no seasonal ocean cycle (ocean frozen at January)
  ⇒ wave erosion and annual statements remain outside scope.
- No observational dataset for lateral melt is versioned in the repository;
  observational claims are preliminary literature comparisons only.

## 15. Decision for next stage

Decision matrix (as required):

| Finding | Evidence | Classification | Production action |
| --- | --- | --- | --- |
| Legacy formula | reference layer reproduces production exactly | VERIFIED | **none** (correct implementation of a legacy approximation) |
| Full-height geometry | exact area/volume comparison; ratio 1.77 vs submerged full-perimeter, 1.13 vs submerged depth | DIAGNOSTIC (modeling choice) | **none/research** |
| Submerged geometry | replay LEGACY_SUBMERGED ΔM 26.1 % | RESEARCH | **none/research** |
| Velocity dependence | U_eq 0.30 m/s vs actual 0.005–0.027; replay ΔM 1.3–3.6 %; U^0.8 scaling | RESEARCH | **none/research** |
| Wave erosion | no forcing, no verified parameterization | NOT TESTABLE | **none** |
| Observational consistency | literature brackets legacy but does not validate; multiple plausible formulations | REQUIRES FUTURE VALIDATION | **preliminary only** |

**Main question — should production lateral-melt physics change?**
**DO NOT CHANGE PRODUCTION PHYSICS in this stage.** Evidence is diagnostic /
research-grade: multiple literature-based formulations remain plausible, no
unique observational constraint selects one, the geometry convention is a
modeling choice, and wave erosion is untestable offline. The quantitative
conclusions (L-03/L-04: legacy ≡ ~0.3 m/s forced convection; lateral dominance
is formulation-dependent) justify a **dedicated** physics/validation stage,
not an ad-hoc coefficient replacement.

**This stage selects OPTION D** — multiple parameterizations remain plausible;
a dedicated observational validation / calibration assessment is required
before any production change.

## 16. Reproducibility

```bash
# Independent reference layer tests (458 checks)
conda run -n iceberg-thermodynamic-model \
    python python/tests/test_lateral_melt_parameterizations.py

# Analysis + figures + machine-readable outputs
conda run -n iceberg-thermodynamic-model \
    python python/analysis/stage10_18a_lateral_melt.py
# writes data/output/stage10.18a/ (baseline_results.csv,
# sensitivity_matrix.csv, parameterization_comparison.csv,
# geometry_comparison.csv, test11_comparison.csv, literature_comparison.csv,
# summary.json, plots/fig01..fig10.png, reproducibility.log)

# Full Python suite (all stage tests, standalone scripts)
for t in python/tests/test_*.py; do conda run -n iceberg-thermodynamic-model python "$t"; done

# Full Fortran battery (production unchanged; same result as Stage 10.17)
rm -rf build && fpm test --flag "-I/usr/include"
```

Environment: conda env `iceberg-thermodynamic-model` (Python 3.12, numpy,
pandas, matplotlib); Fortran gfortran + netcdf.mod at `/usr/include`
(`-I/usr/include`). Baseline trajectory:
`data/output/diagnostics/stage9.3/test11_trajectory.csv` (byte-identical to the
Stage 10.16/10.17 copy).

## 17. Classification

| Item | Classification |
| --- | --- |
| Legacy formula implementation | **VERIFIED** |
| Velocity/size/ΔT scalings (legacy & research) | **VERIFIED** |
| Geometry convention ambiguity (full-height vs submerged) | **DIAGNOSTIC** (modeling choice, not a bug) |
| Legacy constant equivalence to ~0.30 m/s forced convection | **RESEARCH FINDING** |
| Dominance of lateral melt formulation-dependent (ΔM 1.3–26.1 % across variants) | **RESEARCH FINDING** |
| Velocity-dependent formulations (bulk/Bigg/plume/buoyant) | **RESEARCH FINDING** (literature-based; not validated) |
| Wave erosion | **NOT TESTABLE** (no forcing, no verified parameterization) |
| Observational consistency | **REQUIRES FUTURE VALIDATION** (preliminary comparison only) |
| Production physics | **UNCHANGED** (git diff on `src/`, `test/` empty) |
| T-07 drift anomaly | **UNCHANGED** (verification-only interplay checked) |