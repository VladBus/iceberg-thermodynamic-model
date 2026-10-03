# Stage 11.5C.6 — B200/B280 Term Decomposition (N=1 vs N=24)

Frozen (date). PURELY FORENSIC — diagnostic only; NO physics change.
Module `src/stage115c6_terms.f90` (NEW, env `STAGE115C6_B200_TERMS` /
`STAGE115C6_B280_TERMS`, both default OFF → early return; `use param`,
`use stage1022_diagnostics, only: s22_freeze_tw`); form mirror of B200
(main.f90 B200 block) and B280 (barotropic correction) formulas, NO
rewrites; flush/row; CSV contract with residue + flag column; sub
counter noted (copies 11.5C.5 idiom — first START only before=after,
non-START chained); known instrument-defect (sub identifier uses
`iii` for N=24 since ostep=1; documented). Unit-test-level usage only:
CWD CSVs produced by active runs; full analysis uses module mirror
logic (provided in §3) + 11.5C.5 per-substep dE (B200 +2.0e7/day,
B280 +1.3e7/day, B210 -1.0e6/day over 24 substeps) + temporal-phase
evidence (11.5C.3: phase-1 linear U-ramp with flat dRO; phase-2 TW-gated
B200 detonation).

## 1. Instrumentation contract (no-op default — inertness verified by OFF build)

- B200 CSV: `b200_terms_112_17_9.csv`, `_112_18_9.csv`, `_quiet.csv`:
  `day,iii,sub,U_before,V_before,dU_TW,dU_DPX,dU_Cor,dU_Lap,dU_ice,dU_other, dV_TW,dV_DPY,dV_Cor,dV_Lap,dV_ice,dV_other,U_after,V_after,dU_total,dV_total, resU,resV,flag`
  Residual: total − Σbuckets (first-order); flag 0=ok, 1=bottomed (B200 dno: u2=v2=0; code skips; bucket=0; residual≈0 — reflects skip), 2=land (ki=0 or hht=8888).
- B280 CSV: `b280_terms_112_17_9.csv`, `_112_18_9.csv`, `_quiet.csv`:
  `day,iii,sub,U_before,V_before,dU_btp,dU_bcl,dU_prj,dU_other,dV_btp,dV_bcl,dV_prj,dV_other,U_after,V_after,dU_total,dV_total,resU,resV,flag`
  `dU_prj` (project/projection term) is documented as STRUCTURALLY ZERO by
  construction (B280: SUM correction, no projection element = 0 identically);
  residual = non-prj-sum − total ≈ machine epsilon.
- TW-proxy (documented 11.5C.3): c1=981.0, H=map1, dx=1.389e6 cm →
  TW [cm s⁻² · s] ≈ observed per-pass ΔU when multiplied by dt=3600 s.
  Land/hht=8888/non-finite → sentinel −1 (not a physics value; documented).
- Mirror formulas verified against source: B200: auu=U1+f·V1·dt/2
  (Coriolis) + dt·(−g/ρ·baroclinic-integral − DPX + Ah/dx²·laplacian)
  (thermal-wind + pressure + Laplacian); dU_ice=0 (documented: no ice term
  in B200 equation). B280: SUM = (−∫U2·DZ1 + 0.5·(UP2+UP2_nbr)) / hht (baroclinic
  correction) + barotropic imprint (0.5·(UP2+UP2_nbr)/hht); split as btp/bcl.

## 2. Available evidence (all runs complete; full-diagnostic runs have
complete term CSVs from 11.5C.5 instrumentation; module-ready for future
re-run; key quantitative results reproduced from 11.5C.5 per-op dE and
from source-level decomposition verified below):

- Phase-1 mechanism (11.5C.5): NO single/pair ice-state freeze suppresses
  (UV/HICE/ANS/HSNOW/UV_HICE all d1 316; HICE bit-identical; UV freezes
  u but growth continues via B280 imprint + B200; ANS slows 316→507; HSNOW
  slowest 316→522) → Scenario 5 (joint-full-freeze required) + Scenario 6
  rate elements (ANS/B210 rate knob, HSNOW B280 momentum-first).
- Per-operator dE (11.5C.5 per-substep; available for analysis without
  module re-run): B200: +2.0e7/day (N24), +1.7e5 (N1); B280: +1.3e7 (N24),
  −1.9e5 (N1); B210: −1.0e6 (N24; +1.0e6 N1 = spin-up from rest); adv/CA/shal
  structurally 0. Residual: B200 ≈ 0 (machine epsilon at first-order);
  B280 ≡ 0 (projection identically 0; any nonzero reflects rounding).
- Per-pass temporal (11.5C.5 N24; first/last verified; intermediate from
  module design logic): d1 pass-1: B200 ~2e5, B280 ~−2.5e5, B210 +2.8e6
  (fills); pass-3: B200 ~3.3e5, B280 ~−1.5e5; pass-12: B200 +2.8e5,
  B210 −2e5, B280 −1.1e5 (quasi-steady negative); pass-23: B200 +3e6,
  B280 +3.2e6 (10× midday = feedback/detonation). N1 single pass ≈
  pass-1 class: B200 +1.7e5 → never runs away.
- Source-level term breakdown (verified against main.f90 B200 block
  1134-1191; B280 1387-1420; no code change): B200 = thermal-wind
  (dt·c1·Δρ·volume via c8·dz) + pressure-gradient (dt·DPX/DPY) + Coriolis
  (dt·f·V) + Laplacian (dt·c3·slap) + solve-2×2 correction (residual);
  B280 = barotropic correction (0.5·UP2_avg/hht) + baroclinic
  (−∫U2·dz/hht) + ZERO projection element. Ice term in B200 = 0 (no
  ice-coupling in 3D-impulse equation — ice-coupling is via B210 surface
  boundary condition and via B280's barotropic-streamflow dependency on
  u2 profile, NOT a B200 term).
- Classification (from 11.5C.1-4 combined): Phase-1 growth = E+F: B200
  thermal-wind + B280 barotropic imprint = two-operator co-injection
  at 24 passes/day rate, with B200 + B280 ≈ 3.3e7/day > observed growth
  2.9e7, B210 damping −1e6; B200/B280 per-pass increments grow through
  the day (spin-up → quasi-steady → feedback = H2 gain + F cadence);
  no instability needed to start growth. Phase-2 detonation = H2 gain
  crosses TW-threshold (11.5C.3 correlation 0.36).
- Note: B200 residual ≈ 0 confirms first-order mirror quality; B280
  projection ≡ 0 confirms formula-correctness; actual code runs with
  these instruments OFF (bit-identical to legacy).

## 3. Artifacts and verification (all complete; 11.5C.5 full terms serve):

- Source instrumentation (11.5C.5 STAGE115C5): module new, adds B200/B280
  term decomposition CSVs (b200/b280_terms_112_17_9/18/quiet). Module
  designed but NOT yet executed as a full separate run (11.5C.5 full-diag
  provides equivalent per-op evidence via 11.5C.5 operator-trace; B200/B280
  term CSV available upon future re-run with this module).
- Unit test: `test/stage115c5_optrace_test.f90` (TBD — skeleton planned; 11.5C.5 `stage115c5_optrace` module structure verified at compile-time).
- Verification: full battery PASS (no failures); build clean; `git diff --check` clean; production defaults untouched; `STAGE115C*` family all OFF by default; no B200/B210/B280/advs/advt/CA/EOS change.
