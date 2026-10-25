# Stage 11.4 — EOS-80 Controlled Experiment (UNESCO 1983 density)

Frozen 2026-09-30. Code (physics ONLY density; no architecture change):
new `src/eos80_unesco.f90` (pure f64 UNESCO EOS: rho/freezing-point/FD
derivatives) + `equation_of_state.f90` (`eos80_mode`, `eos80_configure()`
on env `EOS_MODE`, `eos_density/eos_density_f64` dispatchers, anomaly
convention rho/1000−1.02 preserved) + 5 `convective_adjustment.f90` call
sites passing `p = z[cm]×0.01 [dbar]` + `eos_diag` gating + 1-line
`main.f90` configure call + `test/eos80_verify.f90` (8/8 PASS).
S model (mass fraction) ×1000 → PSU; T °C ≈ IPTS-68 (documented approx).

## 1. Reference verification (`eos80_verify`, 8/8)

rho(0,5,0)=999.9668 (±0.01); rho(35,5,0)=1027.6755 (±0.02, hand-verified
term-by-term); Δrho(1000 dbar)∈[4.0,5.5]; Tf(35,0)=−1.9223 (±0.005);
drho/dT<0, drho/dS>0; FD step-halving <5%; anomaly convention exact.
Coefficients web-verified against UNESCO Tech Paper 44 excerpts (bulk
i/j/m-series corrected from memory: A-term S-coeffs are
2.2838e-3/−1.0981e-5/−1.6078e-6, S^1.5 const 1.91075e-4).

## 2. LEGACY validation (EOS_MODE unset → default)

Jan 32/32 + Apr 31/31 + Jul 32/32 + Oct 32/32 `.nc` md5-MATCH D33 baselines
(127 files). OFF path = identical legacy call (proven, not asserted).

## 3. EOS-80 experiments (all EXIT 0, 0 NaN in T/S/ro/ice finals)

| Season | EUU eos80 | EUU legacy | Δ | CA nmix (maxiter) eos80 | CA nmix (maxiter) legacy | ro eos80 | ro legacy |
|---|---|---|---|---|---|---|---|
| Jan 30 d | 1.954e15 | 1.947e15 | +0.4% | 94,715 (94) | 10,482,693 (1001) | [−0.00192, 0.01088] | [−0.00061, 0.00890] |
| Apr 29 d | 1.941e15 | 2.087e15 | −7.0% | 61,747 (90) | 9,070,170 (1001) | [−0.00084, 0.01083] | [−0.00087, 0.00821] |
| Jul 30 d | 0.885e15 | 0.893e15 | −0.9% | 30,989 (90) | 2,601,478 (1001) | [−0.00410, 0.01087] | [−0.00420, 0.00872] |
| Oct 30 d | 2.084e15 | 2.122e15 | −1.8% | 46,614 (92) | 3,854,823 (1001) | [−0.00129, 0.01088] | [−0.00134, 0.00829] |

## 4. Analysis

- CA TRANSFORMED: maxiter 1001→~90, nmix 100–300× lower, guard hits 0
  everywhere. Physical (pressure-compressible) stratification produces
  resolvable gradients; the float32-quantization floor no longer binds.
  (Note: CA still compares in f32-rounded values — improvement is formula,
  not precision.)
- Density shifts up with depth (max 0.0109 vs 0.0089; mean +0.0004) —
  compressibility, expected sign/magnitude.
- EUU within ±7% (April −7.0% largest: circulation response to new
  baroclinicity; needs process study, not alarming).
- Freezing point stays Zubov in-model (UNESCO Tf implemented + tested,
  NOT wired — charter scope: density only). Derivatives implemented +
  tested (diagnostic capability; not consumed by dynamics).
- Conservation: CA mixing path untouched (volume-weighted integrals
  preserved by construction); no new NaN/Inf in any field/season.
- Limitation: per-cell ΔU/ΔV/ΔW maps unavailable (velocities not in output
  contract — see 11.3B gap); EUU + ro-bounds serve as proxies.

## 5. Recommendation: make EOS-80 OPTIONAL (user choice), NOT default — yet

Keep LEGACY default (all baselines/validations reference it); EOS-80
available via `EOS_MODE=EOS80` for process studies. Promotion to default
requires: (a) April −7% EUU process review, (b) per-cell velocity-impact
maps (needs output-contract extension, 11.3E), (c) full test-battery +
seasonal re-validation under EOS-80. No impact on 11.5 (temporal), 11.6
(inputs), 12.0 (voxel) designs — EOS choice is orthogonal.
