# Stage 11.8.0 T3 — Rest-State Diagnostic (Ocean Without Forcing)

**Status:** COMPLETE — **classification: UNSTABLE** (diagnostic result, not a
stage failure)
**Date:** 2026-10-24
**Base commit:** `8638741` (T3-PREP)
**Scope:** diagnostic model runs and analysis only. Forcing code was not
changed for the DEFAULT path; no physics, CA algorithm, EOS formula,
scheduler or numerical operator was modified. `EOS_MODE=LEGACY` remains the
default.

---

## 1. T3 configuration (forcing disabled method)

New **env-gated** mode in `app/main.f90`: `STAGE118_T3_REST_MODE=true`
(default OFF → previous behaviour unchanged). When enabled:

1. `kl1 = 0` — surface thermodynamics/heat/snowfall disabled (existing switch);
2. the two `era5_wind()` calls are skipped and a helper
   `zero_forcing_fields()` zeroes `windx1, windy1, wind, tx1, ty1, p1,
   dpx1, dpy1, tatm, patm, humid, cloud, era5_snowfall_rate` (and the
   `dpx/dpy/tx/ty/windx/windy` working copies);
3. after `init_thermal_wind()`, the 3-D velocities (`u1,u2,v1,v2,w`) and the
   barotropic transports (`up1,up2,vp1,vp2`) are zeroed, so the run starts
   from an exact state of rest.

Ocean dynamics remain active: advection (FCT), pressure gradient, Coriolis,
CA, Blocks 200/210/280, shallow water. Tides are null by default; iceberg is
OFF by default. ERA5 is still opened only to set the calendar (30-day run
length); no field is applied.

Method chosen: **Option A/C hybrid** — no new physics branches; the minimal
reversible gate uses the existing thermodynamics switch plus zeroed forcing
arrays and zeroed initial velocities.

---

## 2. LEGACY rest run (corrected EN4 January, canonical)

30 days, 360 steps, EOS LEGACY, N=1 scheduler, zero forcing.

| Metric | Value |
|---|---|
| Days completed | **30 / 30 (no NaN, exit 0)** |
| Max \|U\| over run | **3.859 m/s** |
| Max \|V\| over run | **5.912 m/s** |
| Max \|W\| over run | 0.041 m/s |
| KE day 0 / 15 / 30 | 0 → 2.18e14 → **1.32e16** (×1128 growth from day 1) |
| T RMS drift (day 30) | 0.405 °C |
| S RMS drift (day 30) | **3.40 PSU** (boundary cells at S=0) |
| min ρ anomaly (day 30) | −1.581 kg m⁻³ |
| min N² (day 30) | −1.83e-3 s⁻² (unstable stratification) |
| Conservation (vol / heat / salt) | 0.0 / **8.17e-3** / **1.46e-2** rel. |
| CA | nmix 5.74e6/day (158.5e6 total), maxiter 1001, **guard saturates every day** |
| Classification | **UNSTABLE** |

## 3. EOS80 rest run (same initial data and forcing)

| Metric | Value |
|---|---|
| Days completed | **30 / 30 (no NaN, exit 0)** |
| Max \|U\| / \|V\| over run | **4.481 / 4.706 m/s** |
| Max \|W\| | 0.049 m/s |
| KE day 0 / 15 / 30 | 0 → 1.07e14 → **9.74e15** (×911) |
| T / S RMS drift (day 30) | 0.254 °C / 3.38 PSU |
| min ρ anomaly / min N² | −0.527 kg m⁻³ / −1.86e-3 s⁻² |
| Conservation (vol / heat / salt) | 0.0 / **5.91e-3** / **1.33e-2** |
| CA | nmix ~3.3e4/day (633,450 total), maxiter 99, **guard 0 — CA converges** |
| Classification | **UNSTABLE** |

**Key comparison:** LEGACY (guard saturated, 5.7e6 mixings/day) and EOS80
(guard 0, 3.3e4 mixings/day) produce **nearly identical day-1/day-2 current
fields** (0.0678 vs 0.0674 m/s; 0.1322 vs 0.1313 m/s) and both diverge to
~4–6 m/s by day 30. **The rest-state blow-up is NOT CA-driven** — the T-25
in-situ criterion changes the mixing statistics but not the instability.

## 4. Rebuild vs canonical

`initial_ts_2020-01-01.nc` and `..._rebuild.nc` are **byte-identical**
(md5 `65508e0db5eaf9f67ffd2cf4968609fa`; the T3-PREP rebuild is a copy of the
regenerated canonical). The runs are therefore bit-identical (all metrics
match to the last digit). This confirms run determinism, not a distinct
pipeline; a genuine second pipeline no longer exists for Jan.

## 5. Spurious-current analysis (root causes)

**Where:** the fastest currents develop at the **Svalbard shelf break**
(i≈3–6, j≈15–22 → ≈69.3–69.6 °N, 14–15.5 °E), first at the bottom (k=17) on
day 1 and then spreading to the surface; by day 30 the maximum reaches
6.29 m/s (LEGACY) / 5.60 m/s (EOS80). Speeds >0.01 m/s appear within one day.

Two **interface/data defects** are present in every run and are shared by both
EOS modes (hence the identical early growth):

1. **T-28 — product/model wet-mask gap:** the product is built on the
   pre-smoothing mask (11067 columns / **143,176** level cells), but the
   runtime mask after `coup1` smoothing is **143,422** level cells. For
   **796 columns / 934 levels** the product contains T=S=0; the reader loads
   T=0 °C at those wet levels (it repairs S from the level above but not T).
   Day-0 state therefore contains **934 wet cells at 0 °C** (41 of them within
   8 cells of the shelf-break hot spot) → huge artificial gradients.
2. **T-29 — advection boundary zeroing:** `advection_3d_s/t` write back
   `s2,t2 = cd` for the whole array while `cd` is only updated on
   `1..is, 1..js`; the boundary row/column (`i=is1`, `j=js1`) is never
   written and becomes **zero** at the first advection call. By day 1,
   **1,341 boundary-column cells (i=is1)** have T=S=0 (day 0: none),
   injecting freshwater/0 °C at the domain edge.

Core dynamics then amplify these gradients: min N² is negative by day 30 in
both modes (unstable stratification), consistent with the T-03 family
(pressure-gradient/velocity instability). The volume is conserved exactly
(0.0), but heat and salt are not (0.6–1.5 % over 30 days).

**Diagnostic gap:** the printed `EUU` kinetic-energy diagnostic is hardcoded
to 0.0 in `app/main.f90`; T3 kinetic energy was therefore computed from the
NetCDF output.

## 6. T-25 caveat and interpretation

T-25 (CA compares in-situ density, not potential) is **not the primary T3
driver**: EOS-80, which masks the potential-density inversions CA would mix,
still blows up almost identically while its CA converges. T-25 remains a
critical core-physics correction (T2-CORRECTIVE, before T6), but fixing CA
alone will not produce a rest state; **T-28 and T-29 must be fixed first**.

## 7. New baseline

Run IDs (outputs under `data/runs/`, gitignored; stdout copied as
`stdout.log`):

- `data/runs/t3_legacy_canonical/` — 30 days, LEGACY, canonical Jan
- `data/runs/t3_eos80_canonical/` — 30 days, EOS80, canonical Jan
- `data/runs/t3_legacy_rebuild/` — 30 days, LEGACY, rebuild (identical)

Committed metrics: `docs/wiki/stages/stage11/evidence/t3_rest_result.json` (per-day series +
summary). This **replaces all pre-T3-PREP baselines** (which used the
wrong-grid products) but is a **defect baseline** demonstrating the
instability — it is NOT a validated rest-state reference.

## 8. Regression and CI

| Check | Result |
|---|---|
| Full `fpm test` (rest gate default OFF) | exit 0 — **59/59**, 0 failures |
| Strict build | exit 0 |
| ERA5 contract / sea-ice / provenance | 120 / 33 / 28 |
| Ice coverage / sea-ice provenance | 16 / 8 |
| Snowfall / EN4 T0 / EN4 correction | CONFIRMED_12H / CLEAN / CLEAN |
| ERA5 coverage | unchanged (T-21 accepted; H-2 for T4) |
| T1 spatial/temporal/wrap | WARNING / PASS / RED_CONFIRMED |
| T2 homogeneous/weak/conservation/compressibility | PASS / PASS / PASS / CRITICAL_CONFIRMED |
| `git diff --check` | clean |
| GitHub Actions | green on the pushed commit |

## 9. GO/NO-GO for T4 (wind forcing)

**NO-GO for T4.** The rest state does not exist: with zero forcing the model
reaches ~4–6 m/s in 30 days. T4 (wind) cannot be validated on an unstable
core, and the wind-rotation error (H-2, up to 81°) would be indistinguishable
from the core instability.

**Required before T4:**
1. **T-28** (mask gap: build the product on the runtime mask, or never load
   T=0 into wet cells — reader-side fallback/fatal check);
2. **T-29** (advection writeback must not zero the boundary row/column:
   update only `1..is,1..js` or copy the boundary);
3. re-run T3 until the rest test passes (|U|,|V| < 0.01 m/s, no KE growth,
   conservation to 1e-4);
4. T-23 (T1-CORRECTIVE wrap) and H-2 (wind rotation) remain T4 prerequisites.

T-25/T-27 stay in the T2-CORRECTIVE scope (before T6). No physics/EOS default
was modified in T3; `EOS_MODE=LEGACY` remains default.
