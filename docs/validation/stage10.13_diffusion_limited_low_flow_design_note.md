# Stage 10.13 — Phase A Design Note: Diffusion-limited / double-diffusive low-flow closure

**Status**: Phase A — scientific formulation and literature audit only.
**Production code**: NOT changed (verified: `git status` shows no src/test/python-production modifications from this phase).
**Commit policy**: no add/commit/push in Phase A.
**Date**: 2026-09-15
**Baseline commit**: 14c5fee (stage10.12, pushed)

Epistemic labels used throughout:
`[source]` = established directly from the cited publication/verified metadata;
`[repo]` = verified in the repository (code/tests/docs);
`[analytic]` = derived analytically in this note;
`[inferred]` = reasonable interpretation, not directly proven;
`[unresolved]` = open question.

---

## 1. Status and classification

| Item           | Value                                                              |
| -------------- | ------------------------------------------------------------------ |
| Phase          | A (design/research)                                                |
| Scope          | scientific formulation + literature audit                          |
| Production     | UNCHANGED (no Fortran/Python production edits)                     |
| Tests          | UNCHANGED (no Stage 10.10–10.12 suites re-run — no source touched) |
| Commit         | none                                                               |
| Classification | Research/design; decision expected, not a formula proof            |

---

## 2. Motivation

### 2.1 Exact limitation inherited from Stage 10.11.3 `[repo]`

The Stage 10.11 natural-convection closure
(`docs/validation/stage10.11.3_natural_convection_physics_audit.md`) has
established:

1. The uncapped Rayleigh number for the representative case is
   `Ra ≈ 5.68e19`, nine orders of magnitude above the production cap
   `Ra_max = 1e10` → the cap is **always active** for realistic icebergs.
2. `Nu` is pinned at `0.15·(1e10)^(1/3) = 323.17`; the production zero-flow
   result `m = 1.638e-8 m/s = 1.4e-3 m/day` is therefore **cap-determined**,
   not a function of the physical state.
3. The zero-flow floor is **7–700× below** the observed quiescent band
   `0.01–1 m/day` (Stage 10.8.2 dataset) → the gap is NOT closed.
4. The haline term enters with a **destabilizing sign**
   (`+β_S·ΔS·Le`); physically the fresh meltwater is gravitationally
   **stabilizing** at the horizontal base. With the physically motivated
   (minus) sign the closure gives `Ra<0 → Nu=0 → m=0` — no finite quiescent
   floor at all.
5. The laminar branch (`Ra < 1e7`) and the transition are numerically
   **latent** for production geometries.
6. The recommended direction (Q10 verdict) is a diffusion-limited /
   double-diffusive low-flow parameterization, NOT an extrapolation of the
   existing closure.

### 2.2 Why raising `Ra_max` is not acceptable `[repo] + [inferred]`

The Ra-sweep in the 10.11.3 audit (tables H/I) shows `m` scales with the cap
(`1.4e-4 m/day` at cap 1e7 → `2.53 m/day` uncapped at L=100 m). Raising
`Ra_max` to reach the observed band would require `Ra_max ≳ 1e13` — nine
orders of magnitude beyond the Fujii/Lloyd–Moran correlation's validated
range. The correlation is for classical single-species horizontal-plate
convection; the basal ice-ocean interface has _opposed_ thermal (destabilizing)
and haline (stabilizing) buoyancy, which the classical `Ra` does not represent.
Adjusting the cap to force the observed numbers would be **numerical
retrofitting**, not physics.

---

## 3. Current baseline (repository) `[repo]`

### 3.3 Three-equation interface (Stage 10.10 / 10.10.1) — preserved framework

```
(I)    T_B = Tf(S_B, P)
(II)   rho_w c_w gamma_T (T_w - T_B) = m rho_i [L_f + c_i max(T_B - T_i, 0)]
(III)  rho_w gamma_S (S_w - S_B) = rho_i m S_B          (mass-conserving form)
gamma_T = K_T U_rel,  gamma_S = K_S U_rel   (U-based, Jenkins et al. 2010 Table 2)
```

Stage 10.13 must preserve this framework; the low-flow branch only replaces the
_source of transfer coefficients_ `γ_T`, `γ_S` in the low-flow regime.

### 3.2 Natural-convection addition (Stage 10.11)

```
Ra_eff = g L^3 / (nu alpha) * [beta_T (T_w - T_B) + beta_S (S_w - S_B) Le]
Nu = 0.27 Ra^0.25 (Ra<1e7) ; 0.15 Ra^(1/3) (Ra>=1e7), capped at Ra_max=1e10
gamma_T_nat = Nu k / (L rho_w c_w),  gamma_S_nat = gamma_T_nat (K_S/K_T)
gamma_T_eff = (gamma_T_forced^3 + gamma_T_nat^3)^(1/3)   (Churchill n=3)
```

Limitations (10.11.3): cap-determined; haline sign inverted; L = iceberg length
(not the boundary-layer scale of the mechanism).

### 3.3 Internal thermal evolution (Stage 10.12) — orthogonal, unchanged

`q_cond`, `q_bot`, `C_int dT_i/dt` remain as delivered; Stage 10.13 touches only
the basal heat/salt transfer at the interface, not the interior.

---

## 4. Literature matrix

Verification status: MK77, Keitzl16 and Middleton21 verified via DOI metadata
(Crossref DOIs recorded in repo bib) + abstracts; Keitzl/Middleton quantitative
laws from full-text excerpts; H&J99/J2010 verified via repo (DOIs + equations in
ledger §10.2); PNAS-2021 verified via DOI metadata and abstract (adjacent).

| Source                                                                       | Mechanism                                                                                                                                                                                                                                                                                    | Geometry                                                                              | Equation / law                                                                                                                                                                               | Validity                                                                                  | Applicability                                                                                |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | --- | ------------------------------ | ------------------- | ------------------------------------------------------------------------------------------------- |
| Martin & Kauffman 1977 (JPO 7(2):272–283) `[source]`                         | Convection under horizontal ice sheet: (1) saline BL just below ice, (2) double-diffusive + thermal convective BL, (3) deep thermal convection; melt ≈ 2× purely diffusive                                                                                                                   | **Horizontal ice sheet on top**, warm salty water (S > 25‰); lab + 1-D theory         | melt ≈ 2× diffusive model; regime set by S,T (`T_max_density < T_freeze`)                                                                                                                    | lab, seawater-like                                                                        | **Directly applicable** (quiescent regime); enhancement factor ~2–2.5                        |
| Keitzl, Mellado & Notz 2016 (JPO 46(4):1171–1187) `[source]`                 | Thermally driven convection beneath horizontal ice–water interface; **molecular-diffusion-limited inner layer** (diffusive shield) + turbulent outer layer; `z0 ~ (k^2/                                                                                                                      | b_m                                                                                   | )^(1/3)`; 3 regimes: diffusive (linear), intermediate (4/3), high-T (5/3); `w_f/w_d`governed by Richardson`Ri*`; `w_f ∝ Ri*^-0.42` (conjecture); at 4.33 °C enhancement ≈ 3.1 (vs MK77 ~2.5) | **Horizontal ice bottom**; DNS + lab; **freshwater** (no salt; T_m = 3.98 °C density max) | Eq. (21) param of melt rate in T∞ only; `z0 ∝ (k^2/                                          | b_m | )^(1/3)`, `Ri* = Δb z0 / w*^2` | DNS/lab, freshwater | **Partially applicable** (geometry exact; salt absent; proposes Ri\* framework for shear systems) |
| Middleton, Vreugdenhil, Holland & Taylor 2021 (JPO 51(2):403–418) `[source]` | Melt-driven double-diffusive (diffusive-convection) fluxes in forced-turbulence BL; two regimes: DDC-dominated vs turbulence-inhibited; criterion: DDC if depth of `Re_b=1` deeper than depth of `R_ρ = κ_S/κ_T`; κ_T/κ_S ≈ 110; **saline sublayer grows in time → **time-dependent melt\*\* | **Horizontal ice shelf base**; LES; seawater-like (salt); forced isotropic turbulence | criterion `R_ρ > κ_S/κ_T` + `Re_b < 1` (upgradient diapycnal flux); melt **lower** than shear-only parameterizations                                                                         | LES, seawater, ice shelf                                                                  | **Directly applicable** (mechanism; regime map; time-dependence)                             |
| PNAS 2021 `10.1073/pnas.2007541118` (adjacent; DOI verified) `[source]`      | LES Ross Ice Shelf: DDC first-order at T\* ≥ 0.15 °C, U0 ≤ 2 cm/s; staircase; melt lower than shear parameterizations                                                                                                                                                                        | horizontal ice shelf base; seawater                                                   | qualitative + staircase                                                                                                                                                                      | LES, seawater                                                                             | **Partially applicable** (same mechanism; shows DDC dominates at low U in geophysical scale) |
| Holland & Jenkins 1999 (JPO 29(8):1787–1800) `[repo]`                        | three-equation interface; framework                                                                                                                                                                                                                                                          | ice shelf base (3-D model context)                                                    | Eqs (I-III)                                                                                                                                                                                  | framework                                                                                 | **Framework** (preserved)                                                                    |
| Jenkins, Nicholls & Corr 2010 (JPO 40(10):2298–2312) `[repo]`                | transfer coefficients `K_T, K_S` (Table 2 U-based)                                                                                                                                                                                                                                           | ice shelf base                                                                        | `γ_T=K_T U`, `γ_S=K_S U`                                                                                                                                                                     | field + parameterization                                                                  | **Framework** (U-based convention)                                                           |
| Keitzl, Mellado & Notz 2017 (JGR 121:8419–8431) `[unresolved]`               | heat/salt flux ratio at ice–ocean interface                                                                                                                                                                                                                                                  | horizontal                                                                            | flux ratio                                                                                                                                                                                   | —                                                                                         | adjacent (found in J2010 refs; **not directly verified** — only title seen)                  |
| Fernando & Hunt 1997 `[unresolved]`                                          | Richardson-number framework cited by Keitzl16                                                                                                                                                                                                                                                | general entrainment                                                                   | `Ri*` framework                                                                                                                                                                              | theory                                                                                    | context/context (referenced by Keitzl16)                                                     |

Sources `[source]` marked `[unresolved]` were NOT directly accessed/verified beyond metadata or citation; they are listed as adjacent only.

---

## 5. Candidate mechanisms

### 5.1 A — Diffusion-limited boundary-layer closure `[source, analytic]`

- Transport limited by **molecular diffusion** through a sublayer at the ice
  interface; Keitzl16: "molecular diffusion sets and limits the energy exchange
  at the ice interface for all far-field temperatures."
- Sublayer thickness: diagnosed (Keitzl `z0 ~ (k²/|b_m|)^(1/3)` for the
  stably-stratified shield; Middleton: saline sublayer growing as
  `δ_S ~ (κ_S t)^(1/2`).
- Flux form: `q = k_w ΔT / δ` with molecular `k_w`; enhancement factor
  `f` (2–2.5 MK77; 2.5–3.1 Keitzl at 4.3 °C; possibly Ri\*-dependent).
- Well-behaved as `ΔT→0`: `q→0` linearly; finite melt at `U=0`.
- Coupling to 3eq: replaces `γ_T` in the low-flow regime; `γ_S` via the same
  `f`/Lewis ratio.

### 5.2 B — Double-diffusive (diffusive-convection) closure `[source, analytic]`

- Mechanism (Middleton/PNAS): meltwater freshens AND cools near the base.
  Freshening → **stabilizing**; cooling → **destabilizing**. Near the
  interface freshening dominates → stable sublayer; but `κ_T/κ_S ≈ 100–110`
  lets the thermal BL outgrow the saline BL → the cooled-but-not-yet-freshened
  water above the saline sublayer becomes denser → convective overturn
  (**diffusive convection**, DC, not salt-fingering).
- Governing criterion: DC active where `R_ρ > κ_S/κ_T` and `Re_b < 1`
  (Middleton), i.e., in quiescent low-turbulence conditions. Staircase
  formation caps sublayer growth → quasi-steady flux.
- Time dependence: saline sublayer grows → melt rate time-dependent
  (Middleton; PNAS) — challenges steady-state assumption in the 1-h timestep
  model `[unresolved]`.

### 5.3 C — Hybrid (recommended candidate `[inferred]`)

- Forced branch: existing 3eq + forced `γ_T = K_T U` (unchanged).
- Low-flow branch: diffusion-limited shield + DC enhancement, active when
  forced turbulence is weak (`Re_b < 1` / `U_rel` small); joined smoothly to
  the forced branch (continuity at transition; no double counting).
- Replaces ONLY the Stage 10.11 Ra-natural part; the Churchill mixing is not
  re-used as-is if the DC branch is scale-separated (DC acts at the sublayer
  scale, not at iceberg-L).

### 5.4 D — Rejected / deferred

| Alternative                    | Why rejected/deferred                                                                                    |
| ------------------------------ | -------------------------------------------------------------------------------------------------------- |
| Raise `Ra_max`                 | unjustified extrapolation beyond correlation validity (see §2.2) `[repo]`                                |
| Bulk-Ra with haline minus sign | gives `Ra<0 → m=0` at U=0 — no floor; mechanism is not bulk overturn but BL/DC `[repo]`                  |
| Salt-fingering                 | wrong regime: fresh-over-salty + cold-over-warm is **diffusive convection**, not salt fingers `[source]` |
| Plume parameterization         | not needed at U=0; plume physics belongs to advanced ocean-side item `[inferred]`; deferred              |

---

## 6. Dimensionless analysis `[analytic]`

| Group                        | Definition (units)                                                                       | Role                                                                                                                   |
| ---------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `Le = κ_T/κ_S`               | 93–110 (production 100; Middleton 110; scratch 93.3 with κ_T=1.4e-7, κ_S=1.5e-7, 1.5e-9) | sets relative growth of thermal vs saline sublayer; DC threshold                                                       |
| `R_ρ = αΔT/βΔS`              | α≈3e-5/K, β≈7.8e-4/PSU (repo)                                                            | stability ratio; DC active for `R_ρ > κ_S/κ_T` (i.e. `R_ρ Le > 1`); in DC regime `R_ρ ∈ (1, 1/τ)` bounded `[analytic]` |
| `Ri* = Δb z0 / w*^2`         | Keitzl                                                                                   | shield strength vs turbulence; enhancement `w_f/w_d ∝ Ri*^-0.42` (conjecture)                                          |
| `Re_b = ε/(νN^2)`            | Middleton                                                                                | buoyancy Reynolds; `Re_b<1` near ice (laminar sublayer)                                                                |
| `m_d = k_w ΔT/(δ_S ρ_i L_f)` | k_w≈0.57 W/(m K) (ρ_w=1028, c_w=3974, κ_T=1.4e-7)                                        | pure-diffusion asymptote `[analytic]`                                                                                  |

**Signs `[analytic, verified]`:** thermal gradient destabilizing (cooling top → top-heavy) outside the saline sublayer; haline gradient stabilizing inside it. Production 10.11 uses the wrong sign for the haline term in a bulk-Ra — structurally cannot represent DC.

**Scratch numbers `[analytic]`** (Phase A check, python one-liner):

| δ_S (growth time) | ΔT    | m_d [m/day] | ×2–3        |
| ----------------- | ----- | ----------- | ----------- |
| 11.4 mm (1 d)     | 1–4 K | 0.014–0.057 | 0.029–0.171 |
| 36 mm (1 d)       | 1–4 K | 0.005–0.018 | 0.009–0.054 |

Observed quiescent band 0.01–1 m/day (10.8.2); current 10.11 floor 0.0014.
**Result: diffusion-limited + DC enhancement lands inside the band over a
physically justified parameter range (1-day–10-day sublayer growth; DC 2–3×).**

---

## 7. Candidate equation set (design only; NOT implemented)

```
Diffusion-limited asymptote (basis):
    m_d = k_w (T_w - T_B) / (δ_S ρ_i L_f)            [m/s]
    δ_S(t) = max(δ_min, (κ_S t)^(1/2))              (growing saline sublayer; δ_min floor;
                                                     DC staircase cap δ_cap quasi-steady)
    k_w = ρ_w c_w κ_T

Double-diffusive enhancement factor (regime-dependent):
    f = 2.0–3.1   (MK77 ~2–2.5; Keitzl 3.1 at 4.33 °C; Ri*-dependent conjecture f ∝ Ri*^-0.42)
    active only when DC criterion met (R_ρ > κ_S/κ_T near interface, Re_b < 1 near base);
    else f → 1 (pure diffusive; transition continuous)

Coupling to 3eq (design intent):
    γ_T_low = γ_T_forced, U small  (keep U-based branch)
    γ_T_low_flow = f m_d ...        (γ_S = γ_T (K_S/K_T) or flux-ratio; unresolved)
Continuity: max/mixed formula between forced and low-flow branch at transition
(no double counting; the low-flow branch replaces Ra-natural part).
```

Ambiguities (NOT resolved silently `[unresolved]`): steady vs growing sublayer
in 1-h timestep; DC flux-ratio vs `K_S/K_T` scaling for γ_S; f constant vs
Ri\*-dependent; α,β constant vs EOS-80; Le value 93–110.

Comparison table:

| Mechanism             | Governing quantity                | Required inputs                        | Zero-flow behavior    | Validity                                                  | Main uncertainty                          | Production readiness |
| --------------------- | --------------------------------- | -------------------------------------- | --------------------- | --------------------------------------------------------- | ----------------------------------------- | -------------------- |
| A diffusion-limited   | k_w ΔT/δ, δ diagnosed             | T_w, T_B, κ_S, κ_T, t (or δ_cap)       | finite, m_d > 0       | molecular sublayer; lab/DNS; freshwater & seawater (MK77) | δ (growth vs cap); f                      | design               |
| B DC/double-diffusive | R_ρ, Re_b, κ_T/κ_S, staircase cap | T_w, T_B, S_w, S_B, ε (or U_rel), α, β | finite (f·m_d)        | LES seawater; ice shelf; lab                              | ε at low U; time dependence; steady-state | design               |
| C hybrid (A+B+forced) | regime switch                     | all above                              | finite, continuous    | broad                                                     | switch criterion; continuity              | design (recommended) |
| D bulk-Ra (10.11)     | Ra capped                         | L, T_w, S_w                            | cap-determined 0.0014 | cap artifact                                              | cap; sign                                 | exists, deficient    |

---

## 8. Unresolved questions

1. **Steady vs time-dependent sublayer**: Middleton/PNAS show growing saline
   sublayer → time-dependent melt; Keitzl steady-state DNS/`z0`; MK77 lab
   quasi-steady layers. Which representation for a 1-h timestep production
   model? `[unresolved]`
2. **Sublayer thickness**: prescribed, diagnosed (`z0 ∝ (k²/|b_m|)^(1/3)`),
   or capped by staircase dynamics? `[unresolved]`
3. **Salt flux in DC**: `γ_S` via `K_S/K_T` ratio (existing convention) or
   DC flux-ratio (Keitzl16 JGR 2017; Middleton)? `[unresolved]`
   3b. **Le value**: production `Le=100`; Middleton ~110; scratch 93.3 (κ_S=1.5e-9);
   parameter not to be changed in Phase A — record as documented parameter
   uncertainty, not a hidden fix `[unresolved]`
4. **α, β**: constant (10.11) vs EOS-80 S,T-dependent in `R_ρ`; impacts `R_ρ`
   threshold `[unresolved]`
5. **ε/w\*** at U=0\*_: buoyancy-driven w\* from DC (Keitzl w_ definition) —
   needs closure closure `[unresolved]`
6. \*\*Time-dependence handling in 3eq (Eq.II/III) — steady form with growing δ
   — same interface; salt flux (III) time-dependent? `[unresolved]`

---

## 9. Phase B proposal

Phase B (research, no production integration):

1. Independent Python implementation `python/validation/low_flow.py` — float64
   replica of the candidate hybrid closure + analytic asymptote.
2. Analytic tests: `m→0` as ΔT→0; δ growth asymptotic; f bounded; regime switch
   continuity; regime map (R_ρ vs Re_b/U);
3. Parameter sweep over scientifically justified ranges only:
   T_w ∈ [1,8] °C (Arctic), S_w ∈ [30,35] g/kg, U ∈ [0,0.1] m/s, t ∈ [1h,10 d].
   No arbitrary calibration.
4. Comparison: candidate vs Stage 10.11 floor; vs 10.8.2 quiescent rows
   (10.8.2 (NJ80 rows, KW84); re-scoring only with explicit uncertainty.
5. Fortran integration deferred until acceptance criteria met.

---

## 10. Acceptance criteria (objective gate for production integration)

**Physical:**

- horizontal basal geometry; haline buoyancy stabilizing (correct sign);
- limits: m→0 as ΔT→0; finite at U=0; no unjustified extrapolation;
- no double counting forced vs low-flow.

**Numerical:**

- finite, continuous through low-flow transition; no NaN/Inf; bounded
  coefficients; stable coupling to 3eq.

**Validation:**

- independent Python reference; Fortran/Python anchor (cross-language);
  ≥1 analytic/asymptotic test; literature comparison (MK77 2–3×, Keitzl
  regime law, Middleton regime map); 10.8.2 re-scoring with uncertainty;
  explicit uncertainty statement.

**Software:**

- selectable scheme; OFF preserves legacy; no changes to existing schemes;
  focused tests only for changed behavior; full regression only at integration.

---

## 11. Non-goals

- No change to three-equation framework/ salt convention;
- no change to forced-convection closure; no change to Ra_max/K_ICE/CP_ICE_3EQ;
- no calibration;
- no production integration; no full regression in Phase A; no commit/push;
- no new calibration of α,β, κ_T, κ_S beyond justified literature ranges.

---

## 12. File/reference checks (Phase A)

- Design note: `docs/validation/stage10.13_diffusion_limited_low_flow_design_note.md` (this file)
- Roadmap: `docs/PROJECT_ROADMAP.md` — focused corrections only (header counts
  17→21 / 50→54 / 137→156; 10.13 row + Phase A block; Longer-term link; no
  historical rewrites)
- Production/tests/CI: UNCHANGED (`git status` clean of src/test/.github)
- Tests actually run in Phase A: NONE (no source change) except the
  one-line scratch python calculation in §6 (reproduced in this note).
