# OBC / N>1 Stability Audit (Stage 11.10)

**Status:** BLOCKER CONFIRMED — no production N>1 scheduler promoted.
**Date:** 2026-10-27
**Base:** `ae6260e`
**Evidence:** `data/validation/n4_n24_audit.json`

## Configuration

- NetCDF grid/sea-ice; EOS80; `dt=1800 s`; 24 fires/day (`STAGE113_MM2=24`).
- `STAGE115C_OCEAN_SUBSTEPS=4` / `24`.
- Ah reduced to **2000 m²/s** (target range 2000–5000; not the 10000 legacy damping).
- One-day diagnostic forcing only; no 30-day forensic run was created.

## Results

| Scheduler | Days | max \|U\| | max \|V\| | T min | S min | RO min | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| N=4 | 1 | **4352 m/s** | **14098 m/s** | −206.2 °C | 0 PSU | −5.11 g/cm³ | **BLOWUP** |
| N=24 | 1 | **1.89 m/s** | 1.14 m/s | −1.96 °C | 0.0249 PSU | 9.5e-7 | **GROWING/UNSTABLE TREND** |

N=4 fails within the first day. N=24 is less violent but is already growing
from the N=1 baseline and is not acceptable as a production scheduler.

## Interpretation

The N>1 failure is not solved by lowering Ah. The immediate blocker is the
open/high-frequency boundary and fast-wave treatment: the domain uses a
legacy lateral boundary treatment (clamped/no-gradient with partial sponge),
which reflects/amplifies barotropic and baroclinic signals as the firing
cadence increases. A proper OBC implementation is required before N=4/N=24
can be promoted.

## OBC implementation specification (next blocker)

1. **Barotropic Flather:** at open lateral cells, combine sea level and
   depth-mean normal velocity using the external gravity-wave speed
   `sqrt(gH)`; do not copy both fields.
2. **Baroclinic radiation:** Orlanski/radiation condition for normal
   baroclinic velocity with a bounded phase speed.
3. **T/S relaxation:** 5–10 cell sponge toward EN4 climatology, with a
   time scale longer than the tidal period; do not apply at land.
4. **Every barotropic step:** apply OBC in `shal()`/`barotropic_dynamics`,
   not once per day.
5. **Stability gate:** N=4 and N=24 30-day runs with no NaN, S≥0, T≤30 °C,
   N² ≥ −ε, and volume/salt/heat drift <1e-4 after boundary accounting.

## Decision

**N=1 remains the only validated scheduler**; it is **not** accepted as the
final physical state. N=4/N=24 and OBC are an immediate Stage 12 prerequisite.
No OBC source change was made in this audit; this document records the
implementation contract and the measured blocker.
