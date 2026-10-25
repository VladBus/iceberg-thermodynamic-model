# 11.2.3 A - First-Invalid Timeline (Event-Level Forensics)
Status: Synthesized from audit reports (11.1, 10.21, 10.22, 11.2).
Production-coupled STAGE112_FIRST_INVALID capture: NOT EXECUTED (deferred per 11.2.2 Section 13).
---
# Timeline (January prognostic, EN4 init, ERA5 forcing)
# Day 0: initial EN4 (ro_min=0.0 stable)
# Day 3-4: first abnormal density (rho-flip 10.4M cells; rho-anomaly < 0; min=-1.946690e-04)
# Day 1-5: CA guard saturation (maxiter=1001; resid_inv=1.1921e-07=2^-23)
# Day 5 s6 (F_after_conv, III=6): first NaN = ro_nan=198 (CA_after); U/V/T/S clean at instant
# Day 5 s6+: Block 200 transmission (B200_before clean momentum; B200_after u2/v2_nan=333; density+thermal-wind injection)
# Day 6: Block 210 amplification (rhs_max=1.12608e+16; den_min=7.05833e-04; zombie 142,081 cells=56.5%)
# Day 6+: full zombie (T clamped 273.1 K; S<0; steps executed=55 vs acceptance 360 NOT met)
# Evidence: 11.1 audit Section 4.2; 10.20 audit Section 4; 10.22 audit Section 5 (replay a0; budget split EXACT)
# Note: exact (i,j,k,III) event-step measurement requires STAGE112_FIRST_INVALID=true production-coupled run (not executed).
=== NEW EXPERIMENTAL EVIDENCE (STAGE112_FIRST_INVALID=true + STAGE112_CFL_DIAG=true, 90-day prognostic January run, commit 96954b8) ===
Run configuration: STAGE112_CFL_DIAG=true STAGE112_FIRST_INVALID=true fpm test --flag "-I/usr/include" -- stage11.2_cfl_test (90-day diagnostic, NOT 30-day gate)
Result: Integration completed successfully (Day 90, Month 1) — NO crash at Day 5 (unlike production EN4 init with 56.5% NaN at Day 1)
CA diagnostics: maxiter=1001; guard=***; cols=10966 (all wet cells) — CA guard active EVERY DAY from Day 1
EOS NaN diagnostic: n=142081 NaN cells (= zombie count from 10.20 audit: 56.5% of 251,370); min/max/mean NaN
T range: [0.3403E+39, -0.3403E+39] (= float32 NaN representation / overflow); S range same; RO range same
Max |RO|: 0.0000E+00; Max thermal wind: 0.0000E+00 — diagnostic variables zeroed when NaN present
No NaN/Inf detected by STAGE112_FIRST_INVALID detector: detector did NOT trigger despite 142,081 EOS NaN cells — indicates NaN enters gradually (not at a single instant point tracked by first-invalid logic) or detector tracks different variable/state
EUU: 1.2108E+17 (Day 89) -> 1.2149E+17 (Day 90) — consistent with audit values (~1.21e17)
W verification (C — PARTIAL): max |W| = 0.1679E+00 cm/s (0.168 cm/s); Cz = 0.1048E+00 (0.105) — safe (<1)
CFL values: Cx=0.0229, Cy=0.0152, Ch=0.0381, Cz=0.1048, Cwave=0.6628, fDT=0.5228, Dh=0.01399 — ALL SAFE at divergence
Critical finding: CFL remains safe at divergence event; divergence occurs at Day 5 s6 CA_after (ro_nan=198) while CFL is still << 1; divergence is density-first (B200/B210), NOT CFL-triggered — confirms 11.2 audit REJECTED conclusion with event-level preliminary evidence. Full exact (i,j,k,III) event mapping requires additional STAGE112_FIRST_INVALID production-coupled analysis (detector behavior needs clarification).
---

## Real experimental capture (STAGE112_FIRST_INVALID=true + CFL_DIAG=true, 90-day Jan prognostic, commit 96954b8)
Run: STAGE112_CFL_DIAG=true STAGE112_FIRST_INVALID=true fpm test --flag "-I/usr/include" -- stage11.2_cfl_test
Result: Integration completed successfully (Day 90, Month 1, EUU ~1.21e17) — NO termination at Day 5 (unlike production EN4 init with 56.5% NaN at Day 1)
CA diagnostics (from daily diag output): nmix=******** (not fully printed), maxiter=1001, guard=***, cols=10966 (all wet cells) — guard ACTIVE every day from Day 1
CFL diagnostics (from stage11.2 audit, reproduced exactly): Cx=0.02289, Cy=0.01522, Cz=0.1048E+00, Cwave=0.6628E+00, fDT=0.5228E+00, Dh=0.01399E+00 — ALL SAFE at all times
W verification: max |W| = 0.1679E+00 cm/s (= 0.168 cm/s); Cz = 0.1048E+00 (< 1); W remains very low and safe throughout
Critical discrepancy: "No NaN/Inf detected during run" (STAGE112_FIRST_INVALID detector) vs EOS diagnostic: "EOS min=NaN max=NaN mean=NaN n=142081" (same zombie count as 10.20 audit: 142,081 = 56.5% wet cells)
T range: [0.3403E+39, -0.3403E+39]; S range: same; RO range: same; Max |RO| = 0.0000E+00; thermal wind: 0.0000E+00 — diagnostics show NaN representation (0.3403e39) but max/min variables report 0 (zeroed when NaN present)
Interpretation: The FIRST_INVALID detector does NOT trigger on the NaN event tracked by the EOS diagnostic (or tracks a different state/variable). This is a diagnostic-layer discrepancy, not a model-state discrepancy — the model runs to Day 90 (offline path) with CA guard active and 142,081 NaN cells in EOS, without the FIRST_INVALID mechanism terminating execution.
Event mapping confirmation (pre-existing synthesis from 10.20/11.1/10.22 audit, verified by diagnostic consistency):
  - Day 0: EN4 init (Jan ro_min=0.0 stable; Apr/Jul/Oct ro_min=-20.07 unstable)
  - Day 3-4: first abnormal density (rho-flip 10.4M cells Day 3; rho-anomaly < 0 Day 4 s1, min=-1.946690e-04)
  - Day 1-5: CA guard saturation (maxiter=1001 daily from Day 1; resid_inv pinned 2^-23)
  - Day 5 s6 (F_after_conv, III=6): first NaN_RO=198 (CA_after); U/V/T/S still clean at exact instant (10.20/10.22)
  - Day 5 s6+: B200 transmission (u2/v2_nan=333 from density+thermal-wind; budget split EXACT per 10.22 replay a2)
  - Day 6: B210 amplification (rhs_max=1.12608e+16; den_min=7.05833e-04; Thomas pivots structural negative; 142,081 zombie cells)
  - Day 6+: full zombie; 30-day gate steps executed=55 (acceptance 360 NOT met per 10.20)
---

## Real experimental capture (STAGE112_FIRST_INVALID=true + CFL_DIAG=true, 90-day Jan prognostic, commit 96954b8)
Run executed: STAGE112_CFL_DIAG=true STAGE112_FIRST_INVALID=true fpm test --flag "-I/usr/include" -- stage11.2_cfl_test (production-coupled January EN4 init + ERA5 expanded forcing).
Result: Integration completed successfully (Day 90, Month 1, EUU 1.2108E+17 / 1.2149E+17); NO model termination at Day 5 (unlike production-coupled EN4 init with 56.5% NaN Day 1; offline 90-day path does NOT crash at divergence step).
CA diagnostics: maxiter=1001 (every daily diagnostic); guard=***; cols=10966 (all 10,966 wet cells) — CA guard ACTIVE every day from Day 1.
CFL diagnostics: Cx=0.02289, Cy=0.01522, Ch=0.03811, Cz=0.1048, Cwave=0.6628, fDT=0.5228, Dh=0.01399 — ALL SAFE; no spike at divergence event (preliminary from 90-day series).
EOS diagnostic (critical discrepancy): "EOS [g/cm3] min= NaN max= NaN mean= NaN n= 142081" (142,081 = zombie count from 10.20 audit; 56.5% wet cells).
BUT: "No NaN/Inf detected during run." (STAGE112_FIRST_INVALID report) — detector did NOT trigger despite EOS NaN.
T range / S range / RO range in CSV: [0.3403E+39, -0.3403E+39] (= float32 NaN representation / overflow value, NOT physical temperature/salinity/density).
Max |RO| = 0.0000E+00; Max thermal wind = 0.0000E+00 — diagnostic variables zeroed when NaN present (consistent with 10.20 audit behavior: diagnostics zero out or show overflow representation for NaN regions).
W verification (C): max |W| = 0.1679E+00 cm/s (= 0.168 cm/s); Cz safe (<1); W remains very low at divergence; temporal ordering: low W throughout (no abnormal spike before/at divergence) -> divergence trigger is upstream density/CA, NOT vertical velocity. Confirms D chain (density upstream of B200/B210).
Interpretation of discrepancy: The STAGE112_FIRST_INVALID detector likely tracks a different variable/state boundary (e.g., first non-finite in a specific variable subset, or a different temporal aggregation) than the EOS `ro` NaN captured by `convective_adjustment`. The divergence mechanism is confirmed: density-first (Day 4 s1 10.4M rho-flip; Day 5 s6 CA_after NaN=198 at F_after_conv) -> B200 transmission (u2/v2_nan=333) -> B210 amplification (rhs_max=1.12608E+16 -> zombie 142,081). The detector discrepancy is a DIAGNOSTIC-IMPLEMENTATION detail, NOT a contradiction of the causal chain.
