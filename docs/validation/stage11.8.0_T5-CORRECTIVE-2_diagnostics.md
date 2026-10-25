# Stage 11.8.0 T5-CORRECTIVE-2 — Storm-Time Diagnostics & Root Cause

**Status:** COMPLETE — root cause classified; **T6 NO-GO**
**Date:** 2026-10-25
**Base:** `f0e0cc3` (T5-CORRECTIVE)
**Scope:** diagnostic only. No ocean physics/EOS/scheduler/numerical-operator
change.

---

## 1. Reference document audit

`Dmitriev.txt`, `Nesterov_last.txt`, `model_all.txt`, and `Iceberg_1.docx`
are **absent** from the workspace (repository and adjacent work tree). No
storm-specific guidance can be extracted. The current code contains no storm
branch, adaptive Δt, radiation boundary, or salinity-positivity limiter; FCT
anti-diffusion is intentionally disabled (T-02). Full audit:
`docs/validation/t5c2_reference_audit.md`.

## 2. Detailed Config-1 rerun (dt=900, Ah=20000)

Run `data/runs/t5c2_config1_detailed/` (75-day Q1 forcing; release build;
daily output). It stays finite but corrupts progressively:

| day | T max (°C) | S min (PSU) | RO min (kg/m³) | RO<0 cells | Umax (m/s) | KE (J) |
|---|---|---|---|---|---|---|
| 29 | 7.08 | 23.67 | **−0.7** (first RO<0) | 1 | 0.3 | 3.4e14 |
| 46 | 7.08 | **−7.55** (first S<0) | −37.9 | 11 | ~0.4 | 3.5e14 |
| 55 | 7.08 | −109.4 | −102.9 | 127 | 0.69 | 5.38e14 |
| 60 | 24.1 | −446.2 | −317.6 | 344 | 0.71 | 6.23e14 |
| 63 | 192.3 | −3,561.5 | −1,852.3 | 746 | 1.80 | 1.20e15 |
| 64 | 470.6 | −8,714.9 | −17,836.3 | 890 | 28.3 | 2.28e16 |
| 65 | 532.4 | −9,859.1 | **−2.868e7** | 1,357 | 18,138 | 5.79e22 |

- **Onset:** RO<0 at day 29, S<0 at day 46, T>10 °C at day 57 — long before
  the KE collapse at days 63–65. This is a **cumulative tracer-corruption
  process**, not a sudden CFL break.
- The first negative cells appear at the surface near the lateral boundary and
  spread along the boundary.
- CA nmix stays ≈3.0–3.4e5/day (baseline range; no >1e6 spike). CA input
  inversions grow from 1e-3 to 8.9e-3 and then to 667 only after T/S are
  already corrupted. **CA is secondary/consequential.**
- Boundary max |U| exceeds interior on days 60–64 (e.g., day 64: 28.3 vs
  3.6 m/s), then the interior dominates at day 65; boundary reflection is an
  amplifier, not the initial source.
- Energy: wind work is 20–64 GW, Laplacian dissipation 24–102 GW; dKE is small
  until the collapse. **Wind work is not >> dissipation**; energy accumulation
  is not the primary cause.
- Thermo proxy: surface heat-flux proxy rises only after T blows up; ice
  volume stays ~3.3–3.5e11 m³; MLD ~95–101 m; no rapid ice/mixed-layer
  trigger.

Outputs: `t5c2_ca_diagnostics.json`, `t5c2_advection_diagnostics.json`,
`t5c2_thermo_diagnostics.json`, `t5c2_boundary_diagnostics.json`,
`t5c2_energy_budget.json`.

## 3. Root cause classification

**MULTIPLE — `ADVECTION_ERROR` primary; `BOUNDARY_REFLECTION` amplifier.**
CA inversion is secondary.

Evidence:
- Salinity becomes negative at day 46 and reaches −9,859 PSU; RO negative from
  day 29; T exceeds 10 °C from day 57. T/S are physically impossible long
  before the KE explosion.
- CA nmix is not anomalous; inversion growth follows the T/S corruption.
- Boundary max |U| exceeds interior during days 60–64, consistent with
  reflected storm energy amplifying the near-boundary error.
- Wind work vs dissipation does not show runaway energy input before collapse.

`data/validation/t5c2_root_cause.json`.

## 4. Storm timing

Q1 ERA5 peak wind is **2020-03-16 18 UTC, 26.86 m/s**, at model day **75**.
The Config-1 collapse occurs at days **63–65**, before the Q1 peak; the
corruption starts at day 29/46. Thus the failure is **not a single March-16
storm trigger**; it is cumulative advection error amplified by boundary
reflection, with the later storm merely one strong-forcing episode.

## 5. Literature review (potential fixes)

`docs/validation/t5c2_literature_review.md`:
- positive/monotone FCT or Sweby limiter for salinity advection (Zalesak 1979;
  Smolarkiewicz & Grabowski 1990);
- conservative salinity positivity constraint (not an arbitrary floor);
- radiation/open-boundary conditions or sponge (Chapman 1985; Marchesiello et
  al. 2001);
- CA sub-cycling/implicit CA as a secondary measure;
- adaptive dissipation alone is insufficient (T5-CORRECTIVE showed only delay).

## 6. Recommendation

**T5-CORRECTIVE-3** should implement a **monotone/positive salinity-advection
and boundary treatment**, with CA sub-cycling as a secondary check. Do not
promote a stronger Ah alone. **T6 remains NO-GO.** No fixes were implemented
in this diagnostic stage.

## 7. Regression

Full `fpm test` 60/60, strict build 0; H-2 PASS; T-23 FIXED; ERA5 120/120;
snowfall CONFIRMED_1H; `git diff --check` clean. No ocean physics/EOS/scheduler
change; T6 not started; no `data/runs/` data deleted.
