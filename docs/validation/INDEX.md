# Validation Index — Active Stage 11 Validation

Index of reports for the current work on iceberg thermodynamics (Stage 11).

**Stage 10 is now archived** to `docs/wiki/stages/stage10/` — see archived reports there.

## Active Stage 11 Reports

| Document                                               | Stage | Status                                  | Purpose                                                                                                                                             |
| ------------------------------------------------------ | ----- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `stage11.1_ocean_stability_seasonal_initial_conditions.md` | 11.1  | COMPLETED (seasonal stability characterization; no production change) | Seasonal ocean stability characterization across Jan/Apr/Jul/Oct 2020: instability is general to prognostic ocean evolution but timing depends on initial EN4 state; Jan survives 4 days (crash Day 5), Apr/Jul/Oct crash Day 1 with pre-existing negative ro (−20.07 g/cm³); frozen-ocean control 30 days stable (ro 0.0075–0.0082 g/cm³) — atmosphere alone does NOT cause instability; EN4 initial condition pathology identified for summer/autumn (identical ro_min = −20.07 g/cm³); D-21: next = EN4 initial condition stabilization (Stage 11.2); 4× 7-day runs + 30-day frozen control; full battery PASS; production physics UNCHANGED |
| `stage11.2_cfl_numerical_audit.md`                     | 11.2  | COMPLETED (diagnostic-only; no production change) | CFL + numerical time-discretization audit: all explicit CFL ≪ 1 (Cx=0.023, Cy=0.015, Ch=0.038, Cz=0.10, Cwave=0.66, f·DT=0.52); instability NOT caused by CFL violation; confirmed root cause = EOS float32 quantization → density inversions → thermal wind → Block 200/210 chain (per Stage 10.22); 90-day baseline run completed; timestep sensitivity matrix defined for Stage 11.3; diagnostic module `src/stage112_cfl_diagnostics.f90` added behind env `STAGE112_CFL_DIAG`/`STAGE112_FIRST_INVALID`; production physics UNCHANGED |
| `stage11.2.2_causal_instability_classification.md`      | 11.2.2| COMPLETED (classification based on B/C/D audit; no production change) | Causal instability classification per 11.2.2 report (GPT review): CA guard = REJECTED (symptom, NOT root cause); float32 EOS quantization = STRONGLY SUPPORTED (CA mechanism) / REJECTED (complete zombie explanation); density→B200→B210 chain = CONFIRMED; CFL violation = REJECTED; EN4 init pathology = STRONGLY SUPPORTED; timestep = PENDING; NO physics change |
| `stage11.3_timestep_sensitivity.md`                   | 11.3  | SETUP ONLY (matrix B–E defined; NOT EXECUTED) | Timestep sensitivity matrix (DT=1800/900, DT1=60/30) — deferred per 11.2.2 §14 (requires CA/density ambiguity resolved first); requires `STAGE113_*` env mechanism; NO production change |
| `stage11.4_en4_stabilization.md`                       | 11.4  | D22 FROZEN + D23 FROZEN + D24 FROZEN (forensic event capture complete; NO production change) | EN4 stabilization (D-21): `d_en4` metre-unit + canonical `Z_M` fix validated via TEMP rebuilds (PASS, §12); D22 seasonal runs frozen (§15); D23 controlled experiment frozen (§16): negative-density-as-cause REJECTED; D24 event capture frozen (§17): first invalid = S NaN from `advs()` Day 1 at (2,2,1,k=1) with T/RO finite (EOS-as-source REJECTED, momentum-first REJECTED); D25 advs audit frozen (§18): `advs` propagates pre-formed S1-NaN from `heat()` (only S1 writer; divisions unisolated); Day-1 mechanism internals unresolved; shipped products untouched |

## Setup / Deferred Reports

Stage 10 reports have been archived to `docs/wiki/stages/stage10/`. See the archive index at `../../wiki/stages/stage10/README.md`.

## Links to current documentation

- Physics status: `../model/model_physics_status.md`
- Equations: `../model/model_equation_ledger.md`
- Model description: `../model/model_description.md`
- Stage 10 modernization plan: `../model/stage10_modernization_plan.md`
- Decisions: `../DECISIONS.md`
- Archived completed stages: `../wiki/INDEX.md`

## Rules

- Reports here are not rewritten after stage completion (exception: technical navigational fixes).
- After Stage 11 as a whole is complete, the directory will be archived to `docs/wiki/stages/stage11/` with links and indexes updated.