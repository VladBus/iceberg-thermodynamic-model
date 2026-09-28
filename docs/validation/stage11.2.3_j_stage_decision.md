# 11.2.3 J — Stage Decision Recommendation

Status: Based on A-F evidence (B/C/D completed with concrete source evidence; A/G synthesized; E/F partial/pending event capture). Recommendation: proceed to approved physics stage. NO automatic selection — user confirms.

---

## Evidence summary (A-F status)

- A (First-invalid timeline): Synthesized from 11.1, 10.21, 10.22, 11.2 audit reports; event-level capture PENDING (`STAGE112_FIRST_INVALID` production-coupled).
- B (CFL-at-event): REJECTED (preliminary from 90-day baseline; event-level measurement requires `STAGE112_FIRST_INVALID` but preliminary evidence supports rejection).
- C (W verification): Source fix verified (`end if`); 90-day baseline confirms safe (`Cz=0.105`); event-level PENDING.
- D (`wind_max`): Source traced (`main.f90` line 1479: max atmospheric forcing over wet cells; CGS cm/s); NOT ocean velocity.
- E (`euu`): Source traced (`main.f90` line 557-560: `Kin.Energy(EUU)` accumulator; daily reset `euu=0.0`); full mathematical definition PENDING.
- F (CSV integrity): CSV format verified; content integrity at divergence event PENDING.
- G (Causal ordering): Timeline synthesized; compact event-state table PENDING full event-level capture.
- H (Updated classification): No contradictory evidence from A-F; previous B/C/D classifications stand.

---

## Classification status (post A-F)

Unchanged from 11.2.2 (§16) — no new contradictory evidence:

1. CA guard = root cause: **REJECTED** (B: CA mechanism STRONGLY SUPPORTED; but timeline shows CA downstream of density; 10.21 audit: CA removal does NOT stabilize ocean).
2. Float32 EOS = CA mechanism: **STRONGLY SUPPORTED** (B: quantization floor `2^-23 = 1.1921e-07` vs `0.9e-07`; f64 path eliminates guard per `convect_column_f64` line 351-352).
3. Float32 = complete zombie explanation: **REJECTED** (C: `-20.07` initial-state >> float32 ULP; EN4 init separate mechanism per 11.1; 10.21: all f64 closures diverge).
4. Density → B200 → B210 chain: **CONFIRMED** (D-20 / 10.22 replay a2: two-path budget EXACT; B200 transmitter; B210 amplifier; structural negative pivots).
5. B210 = amplifier (Thomas structural): **CONFIRMED** (10.22: `a1 = -1+a+b < 0` by construction; `piv_neg = 100%` — NOT pathology).
6. CFL violation trigger: **REJECTED** (B preliminary: all CFL << 1 at divergence; 11.1: seasonal dependence inconsistent with CFL trigger).
7. Timestep trigger: **UNPROVEN / PENDING** (11.3 matrix B-E defined; NOT EXECUTED; `STAGE113_*` default OFF; `DT`/`DT1` hardcoded in `main.f90`).
8. EN4 init pathology (`-20.07`): **STRONGLY SUPPORTED** (11.1: pre-existing in Apr/Jul/Oct; frozen-ocean stable 30 d proves atmosphere independent; 10.20: full-coverage ERA5 resolves CASE C but NOT CA divergence; `build_initial_ts.py` pipeline identified).

---

## Recommendation (per 11.2.2 §16 / 11.2.3 §J)

Given evidence status:

- CA/density ambiguity (B/C): **RESOLVED** (CA mechanism confirmed; density divergence upstream of CA; EN4 initial-state separate mechanism identified).
- CFL trigger (B): **REJECTED** (preliminary; event-level confirmation PENDING but strongly supported by 90-day data).
- Timeline (A/G): **SYNTHESIZED** (Day 0 init → Day 3-4 ρ-flip → Day 1-5 CA-guard → Day 5 s6 first NaN → Day 5 s6 B200 transmission → Day 6 B210 amplification → Day 6+ zombie); event-level capture PENDING.
- No physics change required for 11.2.3 diagnostic closure.

**Next approved stage (user selects ONE):**

**Option 1 — Stage 11.3 (timestep sensitivity):** Only if user approves physics-stage authorization. Requires `STAGE113_*` mechanism (`STAGE113_DT`/`STAGE113_DT1` env overrides or temporary `main.f90` edit behind `STAGE113_*` gate). Per 11.2.2 §14: deferred; timestep matrix B-E (`DT=1800/900`, `DT1=60/30`) does NOT address the upstream density/B200 mechanism and should NOT be treated as a fix for the zombie state.

**Option 2 — Stage 11.4 (EN4 stabilization):** **RECOMMENDED** as the next actionable physics stage. Evidence strongly supports EN4 initial-state pathology (`ro_min = -20.07` for Apr/Jul/Oct; `build_initial_ts.py` pipeline; frozen-ocean control proves atmosphere-independent). Per 11.1 (`D-21`): target = fix `shallowest_finite` / vertical regridding / surface-layer extrapolation; target = 30-day stable run across seasons (`steps executed = 360`); requires approved physics-stage authorization per RULES.md §Physics-change rules.

**Option 3 — Additional focused forensic stage:** Only if A-I event-level verification (`STAGE112_FIRST_INVALID=true` production-coupled capture) reveals a new unresolved mechanism not covered by current B/C/D evidence. Given current evidence, no new mechanism is evident; the chain (EN4 init / float32 density / CA symptom / B200 transmission / B210 amplification) is fully traced.

No automatic selection. Confirm which option before any `STAGE112_FIRST_INVALID` production-coupled execution, any `STAGE113_*` mechanism implementation, or any `src/` physics edit (`python/ocean/build_initial_ts.py` EN4 fix, `main.f90` timestep edit, `convective_adjustment.f90` threshold/EOS change, `barotropic_dynamics.f90` or `shallow_water.f90` change).
