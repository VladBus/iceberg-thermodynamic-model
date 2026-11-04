# 11.8A Phase 1-ANALYSIS — Scheduler Ice Effect / CA / Heat

**Status:** COMPLETE — scheduler ice effect is an **ARTIFACT**; production
matrix cells are **NO-GO**; N=1 Phase 2 is **GO**.
**Date:** 2026-10-25
**Base:** `81691e8`

---

## 1. Scheduler ice effect

All four matrix cells used the **same real OSI-SAF/C3S initial ice**
(`STAGE117E_NETCDF_SEAICE=ON`); day-0 SIC/SIT are bit-identical (max diff 0.0).
H3 (initialization) is ruled out.

| Cell | Day-30 extent (10³ km²) | Volume (km³) | Mean thickness (m) | Ts mean (°C) |
|---|---|---|---|---|
| LEGACY N1 | 683.6 | 408.5 | 0.598 | 0.881 |
| EOS80 N1 | 687.4 | 412.8 | 0.600 | 0.849 |
| LEGACY Prod | **1,128.8** | 566.6 | 0.502 | **0.117** |
| EOS80 Prod | **1,182.5** | 577.7 | 0.489 | **0.059** |

- Production adds **466,124 km²** of ice relative to N1; the extra ice lies
  over N1 open water (mean N1 SIC **0.013**, production SIC **0.926**),
  spanning 65.1–81.4 °N / 13.4–75.4 °E — not a local ice-edge shift.
- Production surface ocean is **~0.76 °C colder** at day 30.
- Implied heat loss: N1 **−40.3 W/m²**, production **−268.6 W/m²**.
- Production CA runs at **576 passes/day** (6.63e9 mixings/month vs 2.11e7
  N1); N1 has one CA pass/day. Production `mm2=24` vs N1 48 thermodynamic
  steps/day.

**Hypothesis ranking:**
1. **H4 cadence (HIGH):** production 24 fires/day / 576 ocean-CA passes/day
   vs N1 48 thermo steps / 1 CA pass; ice and CA update cadence differ.
2. **H2 artifact/spurious cooling (HIGH):** −269 W/m² implied cooling is
   outside the T-34 (−50…−5 W/m²) range; extra ice appears over broad open
   water, not a physical ice-edge advance.
3. **H1 physical STALE effect (MEDIUM):** colder ocean/more ice is
   qualitatively consistent with altered coupling, but STALE would be expected
   to reduce heat exchange; observed heat loss is **larger**, so it is not a
   clean physical mechanism.
4. **H3 initialization (NONE):** day-0 ice identical.

**Conclusion: ARTIFACT** — production scheduler cadence/STALE coupling, not a
validated physical ice response. Production ice climatology must not be used
for D-29/11.8A ice validation without a scheduler fix.

## 2. CA diagnostics suppression

CA is **active** in production: `CA-PROBE` lines are present and the CSV
`ca_nmix` column contains real values. The console `nmix=********` is an
**I8 print-format overflow**: production daily totals reach **4.05e8**
(6.63e9 over 30 days), exceeding 8 digits. N1 totals are 2.11e7/1.87e7.

**Verdict:** CA physics **runs** (feature); the console print format is a
**diagnostic formatting bug**, not a CA bug. CSV is authoritative.

## 3. Heat conservation / T-34

| Cell | Heat drift | Implied mean flux | T-34 verdict |
|---|---|---|---|
| LEGACY N1 | −5.35 % | **−40.3 W/m²** | **VALID** |
| EOS80 N1 | −5.21 % | **−39.3 W/m²** | **VALID** |
| LEGACY Prod | −35.63 % | **−268.6 W/m²** | **INVALID** |
| EOS80 Prod | −34.64 % | **−261.2 W/m²** | **INVALID** |

N1 cooling is in the T-34 plausible range (−5…−50 W/m²). Production cooling is
~6.7× larger and outside the range; a direct surface-flux integral is not
archived, so the production heat drift cannot be separated from the scheduler
artifact. **T-34 closure remains valid for N=1 cells only.**

## 4. Decision

- **Production scheduler for ice: NOT physically validated** (artifact).
  Production matrix cells are **NO-GO**.
- **CA suppression: no physics bug**; only diagnostic print format. No fix in
  this analysis stage.
- **Heat conservation:** N1 valid; production invalid due scheduler artifact.

**Phase 2 (Apr/Jul/Oct): GO for N=1 only.** Production dimension is
**BLOCKED**; matrix becomes 2 EOS ×4 seasons = **8 N=1 cells** plus
production diagnostic cells only after a scheduler fix. D-29 assessment
continues on N=1; EOS80 remains candidate, no promotion.

## 5. Evidence

`ice_detailed_diagnostics.json`, `scheduler_ice_effect_analysis.json`,
`ca_diagnostics_analysis.json`, `heat_conservation_verification.json`.
No physics/EOS/scheduler code changed.
