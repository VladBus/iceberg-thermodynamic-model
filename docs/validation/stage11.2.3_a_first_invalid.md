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
