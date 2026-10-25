# Stage 11.4.1 — EOS-80 Impact Validation (detailed comparative analysis)

Frozen 2026-09-30. No physics changes (diagnostic U/V already written;
added `alpha_thermal`/`beta_haline` via active-EOS central FD in
`netcdf_output.f90`, read-only). 8 re-runs (4 leg + 4 eos, EN4-guarded,
logs saved). Per-cell CA maps + Tf-vs-model deferred with rationale below.

## 1. Methodology

Final-state `.nc` compared leg-vs-eos per season: ΔT/ΔS/Δρ-anomaly/ΔU/ΔV/ΔW/
Δα/Δβ (min/max/mean/std/P5/P95); April top-10 cells + column profile +
EUU(t) from saved logs. LEGACY numerics re-verified (day_00 bit-identical
to D33 all seasons). NOTE (method): first 11.4.1 batch ran on SYNTHETIC
fallback (/tmp wipe) and was DISCARDED in full; all results below are from
guarded EN4 re-runs (`Realistic ocean` confirmed per log).

## 2. All-season Δ statistics (eos − leg, final state)

- Δρ mean +0.21..0.23 kg/m³ all seasons (compressibility); p95 ~1.13;
  max +7.1..8.9 (deep), min −3.4..−4.6 (localized lighter water).
- ΔT: means ±0.06 K, std ~0.3, extrema ±4..6 K (heavy tails = few cells).
- ΔS: means +4e-5, std ~3e-4 (tight).
- ΔU/ΔV: means ~0, std 0.09–0.13, p5/p95 ±0.03–0.05, extrema ±3..5 m/s
  (reorganized currents; heavy tails).
- ΔW: std ~5e-4 m/s, extrema ±0.03..0.06.
- Δα mean ≈ −1e-5 (EOS-80 less expansive); Δβ mean ≈ −0.004 (less contractive).
- 0 NaN in all fields/seasons/modes.

## 3. April deep dive (EUU −7.0%)

- Top |Δρ|: entire water column (j=15,i=109) @81.6°N,35.7°E, +6.6..7.1 from
  surface to k=14 (0 at k=15 = below bottom). Deep part = compressibility;
  surface part = diverged water mass (legacy unmixed vs EOS-80 mixed —
  legacy CA saturated/struggled there).
- Top |ΔU|: surface cells (k=0..2, j=5, i=53) ±3 m/s; (j=19–21, i=21–22)
  ∓2.9 m/s — shifted jets/eddies, not basin-wide acceleration.
- EUU(t): day10 −3.1%, day20 −0.8%, day29 −7.0% — GRADUAL divergence
  (circulation adjustment to new baroclinicity), not an event.
- Mechanism: denser deep water → altered baroclinic pressure gradients →
  thermal-wind adjustment → reorganized surface currents → −7% kinetic energy.
  Plausible physics, unvalidated vs observations.

## 4. Physical realism

- Deep +6.7 kg/m³ at ~2–4 km: correct sign/magnitude for compressibility
  (ρ·p/K); legacy Eckart has NO pressure dependence (unphysical at depth).
- CA convergence (maxiter ~90 vs 1001, guard 0) indicates resolvable,
  physical stratification instead of quantization-pinned residuals.
- Surface differences are state-divergence (mixing history), not EOS error.
- α/β weaker than Eckart-implied — consistent with crude-legacy bias.
- NOT assessed: per-cell CA geography (global nmix discriminates 100–300×;
  driver plumbing disproportionate — deferred), model-vs-EOS80 Tf (Zubov
  unchanged in-model → ΔTf≡0 by construction; UNESCO Tf tested in 11.4),
  WOA profile comparison (no WOA in repo — future work).

## 5. Recommendation: OPTIONAL (unchanged from 11.4)

Keep LEGACY default; `EOS_MODE=EOS80` for process studies. Promotion needs:
(a) April −7% process review against observations, (b) WOA T/S-profile
validation, (c) full battery + seasonal re-validation under EOS-80.
No impact on 11.5/11.6/12.0 designs (EOS choice orthogonal).
