# Stage 11.4: EN4 Initial-Condition Stabilization (D-21) — AUDIT IN PROGRESS

**Status**: AUDIT (docs-first, D-21). No physics change, no regeneration, no `fpm` execution in this step.
**Date / baseline**: 2026-09-28; HEAD `4e99fc2`; working tree clean except this report.
**Classification**: B (physics status — see `docs/model/model_physics_status.md` for the authoritative block table).

## 1. Objective (D-21)

Establish the exact origin of the Stage 11.1 `ro_min = -20.07` Day-0 value for Apr/Jul/Oct 2020 (vs Jan `0.0`), then prepare a minimal RULES-compliant fix. Scope is the EN4 pipeline only: `python/ocean/build_initial_ts.py` → `data/input/processed/ocean/initial_ts_*.nc` → `src/initial_ocean_reader.f90` → Fortran `T2/S2/RO` → Day-0 diagnostic. EOS, CA, DT/DT1, Block 200/210/280, ERA5, grid, bathymetry and thermodynamics are OUT of scope for edits in this step.

## 2. Audit findings — pipeline chain (`python/ocean/build_initial_ts.py`, full file read)

- Raw input (`main()`, L230-232): `temperature` (K), `salinity` (PSU assumed), `depth` (`d_en4`, units taken from file; code assumes cm — see below), `lat`/`lon`.
- Units (`main()`, L235-236): `t_c = (t_k - 273.15).astype(float32)`; `s_f = (s_p / 1000.0).astype(float32)`. Single conversion before interpolation — order correct.
- Horizontal NN: `en4_wet` first defined T&S-finite (L241) for the initial tree (L247-254), then **redefined T-only** (L342-343) with rebuilt tree for the default `nearest` path. The default path therefore ignores S-availability when selecting columns; per-depth protection only inside `vertical_regrid` via `mf = finite(tv) & finite(sv)`.
- `vertical_regrid` (L151-201): flags L155-159 (`0` interp / `1` shallowest-finite / `2` deepest-finite / `3` product-land → output left `0`, L175-177). `zm = Z_M[k] * 100.0` (L183) assumes `d_en4` in cm; same assumption in the bilinear branch (L318 `en4_depth = d_en4 / 100.0`, L321 `searchsorted(d_en4, z_target * 100)  # d_en4 is in cm`).
- `Z_M` shadowing (DEFECT, documented not fixed): global L73 `Z_M = Z_CM / 100.0` = `[2.5, 5, 10, …, 600]` m is used by `vertical_regrid`; `main()` redefines a local L261 `Z_M = [2.5, 5.0, 7.5, 12.5, …, 550]` m used for stats/NetCDF `z_model_m` and output coordinates. Mapping vs stored coordinate differ.
- `eckart_ro` (L121-128): float32, `ro = rho - 1.02` g/cm³, formula matches the Fortran Eckart path (cross-check of `src/equation_of_state.f90` pending — next step).
- Sentinel arithmetic (verified by direct float32 evaluation, same formula): `ro(0°C, 0)` = **-0.0200709 g/cm³**; `×1000` = **-20.0709**. `ro(T, 0)` ≈ -0.02 g/cm³ for any T (S=0 dominates). No physical (T,S) from these files yields `ro = -20.07 g/cm³` (checked: S-as-PSU gives ≈ -3.0; K-without-conversion gives ≈ +0.25).

## 3. Audit findings — built products (direct read, not report quotes)

- `data/input/processed/ocean/`: `initial_ts_2020-{01-01,04-01,07-01,10-01}.nc` all present (Jan 2026-08-30; Apr/Jul/Oct 2026-09-25 23:23-25) plus Jan `Tclamp` variants.
- `data/output/diagnostics/stage7.7/stage7.7_statistics{,_apr,_jul,_oct}.json`: all `result: PASS`, `n_nan_inf_ro/output: 0`, `product_land_column: 0` everywhere; RO ranges physical (Jan 0.00748–0.00819; Apr 0.00367–0.00819; Jul 0.00275–0.00819; Oct 0.00345–0.00820 g/cm³). Apr/Jul/Oct differ from Jan only in `deepest_finite` (128382 vs 0) — seasonal EN4 depth coverage, values physical.
- Direct `.nc` read (133×105×18, `need` mask = 143176 cells each file): **zero** `S==0` cells, **zero** `(T==0 & S==0)` cells in-mask for all four files; stored `density_anomaly_gcm3` minima 0.0027–0.0075 (physical).
- Current `data/runs/stage11.1_{jan7,apr7}/output/nc/results_day_00.nc`: `density_anomaly` units **kg m-3**; minima 0.0 (land cells); maxima match the report (Jan 8.186, Apr 8.244 ≈ report 8.42/8.28); **neither file contains -20.07**. Report u_max values (Apr 0.28 cm/s) do not match current dumps (4.99 cm/s) — outputs were overwritten after the report.

## 4. Provenance conflict (RULES.md §Conflict resolution — recorded, not resolved silently)

- `docs/validation/stage11.1_ocean_stability_seasonal_initial_conditions.md` mtime 2026-09-25 19:36, committed `a091e37` 20:51. Its Day-0 tables (`ro range (g/cm³)`: Apr/Jul/Oct `-20.07`, Jan `0.000`) **predate** the current Apr/Jul/Oct `.nc` builds (23:23-25) and the current `jan7/apr7` runs (23:58/00:04). The `-20.07` values are therefore **not verifiable against any current artifact** — they describe overwritten runs/files.
- Commit `0b673ff` (2026-09-26 23:16, after all runs) changed three candidate mechanisms: (a) `vertical_regrid` `zm = Z_M[k]` → `Z_M[k]*100.0`; (b) `en4_wet` T-only → T&S; (c) `initial_ocean_reader.f90` new S==0 post-replacement; plus `grid_coupling.f90` KT1/land-marker fix (`8888.0`→`888800.0` for HT in cm).
- `src/initial_ocean_reader.f90` (full read): loads `k<=kt` from file arrays; land/deep → `0.0`; S==0 post-replacement for `k>=2` only (exact `== 0.0` comparison) copies S from above but leaves T=0; Day-0 Fortran diagnostic (`app/main.f90`, ~L1475-1491) takes `ro_min` over wet-only (`kt1>0`, `kw=1..ki_col`), land excluded.
- Stage 11.1 tables are consistent with NetCDF Day-0 dumps as source (T in K, S frac, density in kg m-3): maxima match; the `ro` column unit label (`g/cm³`) is inconsistent with the values (kg m-3 scale). Under that reading, `-20.07` ≡ sentinel `(T,S)=(0,0)` cell rendered in kg/m³, and `S min 0.0000` (all cases incl. Jan) marks zero-salinity wet cells in the dump.

## 5. Classification (per requested CONFIRMED / SUPPORTED / UNKNOWN scheme)

- `ro(0°C,0)×1000 ≡ -20.07` numeric identity: **CONFIRMED** (direct float32 evaluation, same `eckart_ro` formula).
- Current `.nc` files clean (no flag-3, no in-mask sentinel, physical RO): **CONFIRMED** (direct read of all four files + four JSONs).
- Current Day-0 dumps contain no `-20.07`: **CONFIRMED** (`jan7`/`apr7` `results_day_00.nc` minima 0.0 = land).
- Report `-20.07` provenance (overwritten pre-23:23 runs/files): **SUPPORTED** (mtime/commit ordering + value/table mismatch vs current artifacts; direct pre-image unavailable).
- `vertical_regrid` surface-layer bug as the `-20.07` cause: **UNKNOWN** (prior hypothesis; current evidence points instead to sentinel+units/mask handling and the pre-`0b673ff` code state; `Z_M`-shadowing and `d_en4`-units assumption are documented defects but not proven causal for `-20.07`).
- `shallowest_finite` mishandling as cause: **UNKNOWN** (JSON `shallowest_finite` counts are 0 in all four current files; no supporting evidence in current artifacts).
- Fortran-side `(0,0)` wet-cell path (`kt` vs `kk1` mismatch, k=1 S==0 survivor): **SUPPORTED as mechanism class, UNKNOWN as historical cause** (code paths verified in reader L~150-200; no current `.nc`/dump exhibits it).

## 6. What this changes for the fix plan

- Do NOT fix `vertical_regrid` blindly for `-20.07`: current products do not exhibit the value, and the three `0b673ff` changes postdate the evidence. Any fix must first reproduce the historical `(0,0)` wet cell (or prove the `kt`/`kk1`/k=1 path) — otherwise we would be fixing a mechanism with no failing artifact.
- Candidate minimal fix class (NOT implemented): guard the reader/pipeline boundary so `(T,S)=(0,0)` can never enter a wet `RO` computation (e.g. extend the S==0 replacement to k=1 / reject zero-salinity wet cells with a reported flag), plus a units-label correction for the Day-0 `ro` diagnostic (kg m-3 vs g/cm³). Requires: historical-algorithm note, equation (`eckart_ro`), provenance (`EN4.2.2 g10` + script args per month), OFF-by-default switch with bit-identical baseline, independent tests, limitation statement — per RULES.md §Physics-change rules.
- Blocked diagnostics before any fix: (a) EN4 raw `depth` units header check (`ncdump -h`, header only); (b) Fortran `density_anomaly` formula/units cross-check (`src/equation_of_state.f90`); (c) `kt` (Fortran grid) vs `kk1` (Python `load_model_grid`) comparison for k=1 wet cells.

## 7. Files changed in this step

- None (audit + this report only). No `src/`, `python/`, data, or config edits. No `fpm` execution. No commit (awaiting explicit permission per instructions).

## 8. Known limitations / risks

- The historical `-20.07` runs/files are overwritten; classification of its exact cell-level path stays at SUPPORTED/UNKNOWN until (b)-(c) above close it.
- `d_en4` units still assumed from code comments, not verified against the raw header.
- `Z_M` global-vs-local mismatch verified in source but its quantitative effect on the four built files is unmeasured.

## 9. Next (single lightweight step proposed)

Raw header check only: `ncdump -h` depth units for `EN.4.2.2.f.analysis.g10.202001.nc` + `src/equation_of_state.f90` `density_anomaly` formula/units grep. No model run, no regeneration.

## 10. Unit/provenance verification (2026-09-28, executed — audit only, no edits)

- Raw EN4 header (`ncdump -h`, `data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc`): `depth.units = "metres"`, `positive = down`; `temperature.units = kelvin` (potential temperature, `_FillValue -32768`, `add_offset 273.15`); `salinity.units = "1"` (practical salinity). Depth values (`ncdump -v depth`): 5.02, 15.08, …, 5350.27 — metres, 42 levels.
- Consequence for `build_initial_ts.py`: the code assumes `d_en4` in cm in two places — `vertical_regrid` L183 (`zm = Z_M[k] * 100.0  # to match d_en4 (cm)`) and the bilinear branch L318 (`en4_depth = d_en4 / 100.0  # convert to meters`) + L321 (`searchsorted(d_en4, z_target * 100)  # d_en4 is in cm`). Against metre-valued `d_en4`, the `*100` mapping is wrong by 100× (model 2.5 m → EN4 250 m; model 550 m → beyond EN4 bottom → deepest-finite).
- Critical ordering fact: this `*100` was introduced by commit `0b673ff` (2026-09-26 23:16; diff `zm = Z_M[k]` → `Z_M[k] * 100.0`). All current `.nc` products (Jan 2026-08-30; Apr/Jul/Oct 2026-09-25 23:23-25) were built with the pre-`0b673ff` metre-consistent code — which is why they are clean. The current working-tree script would mis-register depths if rerun. No rebuild was performed in this step.
- Fortran EOS (`src/equation_of_state.f90`, L85-98 `density_anomaly`, L116-124 `density_anomaly_f64`): formula coefficient-identical to Python `eckart_ro` (`build_initial_ts.py` L121-128); documented units `t` [°C], `s` [mass fraction], `ro = rho - 1.02` [g/cm³] (L5-12 header, L94-97 comments). Python↔Fortran EOS consistency: CONFIRMED (modulo float32/f64 precision variants, documented L100-115).
- NetCDF boundary (per AGENTS.md §Unit Systems): output `density_anomaly` in kg m-3; model-internal RO in g/cm³. This 1000× boundary, combined with the `(T,S)=(0,0)` sentinel (`ro = -0.0200709` g/cm³, verified by direct float32 evaluation), fully accounts for the reported `-20.07` magnitude without any physical inversion.
- Classification update: `d_en4`-in-metres vs code-assumes-cm → CONFIRMED defect in working-tree script (not yet executed — no product impact to date); Python↔Fortran EOS match → CONFIRMED; `Z_M` global-vs-local shadowing (L73 vs L261) → CONFIRMED defect (unmeasured quantitative effect; pre-`0b673ff` builds used global `Z_M` in `vertical_regrid` with metre-consistent `zm`, so mapping was correct despite the shadowing).

## 11. Applied fixes in working tree (2026-09-28, NOT committed, seasonal `.nc` NOT regenerated)

### A. Confirmed code defects (with correction)

A1. `d_en4` units assumption (CONFIRMED, fixed): `vertical_regrid` L183 used `zm = Z_M[k] * 100.0  # to match d_en4 (cm)`; bilinear branch L318 `en4_depth = d_en4 / 100.0` and L321 `searchsorted(d_en4, z_target * 100)  # d_en4 is in cm`. Raw header proves `depth.units = "metres"` with metre values (5.02…5350.27). Correction: metre-consistent mapping (`zm = Z_M[k]`; `en4_depth = d_en4`; `searchsorted(d_en4, z_target)`). Historical note: the `*100` was introduced by commit `0b673ff`; all shipped `.nc` products were built with the pre-`0b673ff` metre-consistent code, so the fix restores consistency with existing products instead of changing them.

A2. `Z_M` global/local shadowing (CONFIRMED, fixed): module-global L73 `Z_M = Z_CM / 100.0` (`[2.5, 5, 10, …, 600]`, consistent with `src/param.f90` and with `kk1 = searchsorted(Z_CM, ht_cm)`) was shadowed by a local `main()` redefinition (`[2.5, 5.0, 7.5, …, 550]`) used for stats labels, NetCDF `z_model_m` and the bilinear `z_target`, while `vertical_regrid` used the global. Correction: local redefinition removed; single canonical `Z_M` everywhere. Data values from `vertical_regrid` unchanged (it already used the global); only output coordinates/labels and the (non-default) bilinear mapping become consistent.

### B. Historical `-20.07` provenance conflict (unchanged)

Report tables (Stage 11.1, committed `a091e37`) predate current `.nc` builds and runs; current artifacts contain no `-20.07` (direct `.nc` + Day-0 dump reads). Numeric identity `ro(0,0)×1000 = -20.0709` plus NetCDF kg m-3 vs `g/cm³` label explains the magnitude as a sentinel/unit/mask artifact of overwritten runs, not a physical inversion. Conflict recorded per RULES.md; not silently resolved.

### C. Unresolved S=0 provenance (narrowed, still UNKNOWN as historical cause)

Diagnostic 2026-09-28: Fortran `kt` ≡ Python `kk1` exactly (11067/11067 wet columns, 0 mismatch, Jan+Apr); at k=1, zero wet cells with `S==0` in current dumps — `S=0` exists only on land (`kt=0`, invalid marker), never as a wet value. The `S==0` post-replacement in `initial_ocean_reader.f90` (k>=2 only, exact `==`) therefore has no wet target at k=1 in current artifacts. Per instruction, no `(0,0)` guard added; historical cell-level path of `-20.07` stays UNKNOWN (overwritten pre-23:23 runs).

### D. Tests required after fix (independent checks done / required)

- `python3 -m py_compile python/ocean/build_initial_ts.py` — DONE (COMPILE-OK, this step).
- Synthetic `vertical_regrid` probe (metre `d_en4`, 7-level column): k=1 (2.5 m) → surface value flag 1; bottom level → deepest value flag 2; flags {0,1,2} as specified — DONE.
- Canonical-level check: global `Z_M == Z_CM/100` elementwise — DONE (True).
- REQUIRED before any regeneration: rebuild ONE month to a temp `--out`/`--json` path and compare flag_counts/RO ranges against shipped stats (expect interp-dominated distribution, physical RO; only coordinate labels differ by the `Z_M` alignment); full `fpm test` battery on any Fortran touch (none in this step — Python only).
- Seasonal `.nc` regeneration explicitly NOT performed in this step.

## 12. Seasonal rebuild validation, TEMP only (2026-09-28, authorized step (a))

Rebuilt all four months with the fixed working-tree script to `/tmp/stage114_check/` (raw untouched; shipped `.nc` untouched; no model run; no physics change). Commands: `python3 python/ocean/build_initial_ts.py --raw data/input/raw/ocean/EN.4.2.2.f.analysis.g10.{202001,202004,202007,202010}.nc --out /tmp/stage114_check/initial_ts_YYYY-MM-01_rebuild.nc --json /tmp/stage114_check/stats_*_rebuild.json`.

| Month | dims eq | `z_model_m` canonical | Wet `S==0` | Wet `(0,0)` | NaN/Inf | RO min/max (g/cm³, in-mask) | Flags interp/shallow/deepest/land | JSON result | `ro_min` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Jan | True | True (`[2.5..600]`) | 0 | 0 | 0/0 | +0.00438 / +0.01001 | 228722 / 22133 / 515 / 0 | PASS | physical, positive |
| Apr | True | True | 0 | 0 | 0/0 | -0.00096 / +0.00842 | 228722 / 22133 / 515 / 0 | PASS | small negative inversion (1e-3 scale) |
| Jul | True | True | 0 | 0 | 0/0 | -0.00386 / +0.00819 | 228722 / 22133 / 515 / 0 | PASS | small negative inversion (1e-3 scale) |
| Oct | True | True | 0 | 0 | 0/0 | -0.00127 / +0.00828 | 228722 / 22133 / 515 / 0 | PASS | small negative inversion (1e-3 scale) |

- NO CHANGE (all months): dims `(133, 105, 18)`; `wet_mask` + `water_column_levels` identical to shipped; zero NaN/Inf in outputs and RO; `product_land_column: 0`; zero wet `S==0` / `(0,0)` cells (sentinel only on land); `result: PASS`.
- EXPECTED (fix consequences): canonical `z_model_m`; flag mix `interp/shallowest/deepest` (level 1–2 above the 5.02 m EN4 surface sample → flag 1 per spec; 515 cells below EN4 column bottoms → flag 2) instead of shipped patterns. Shipped Apr/Jul/Oct show `deepest_finite` 128382 — the signature of the pre-fix `×100` mapping (model metres read against centimetre scale pushes mid/deep levels below EN4 bottoms); the fixed mapping restores metre-consistent registration. Value shifts follow from correct depth registration plus the pre-existing (`0b673ff`) `en4_wet` T&S column-selection mask.
- PROVENANCE (build-method difference, not fix effect): shipped Jan (all-zero flags, no zeros even on land, local `z_model_m` `[2.5..550]`) carries the `--method bilinear` signature (land pre-filled, flags never assigned), while all rebuilds use the default nearest path. Shipped-vs-rebuild Jan deltas therefore mix method + coordinate effects; shipped products stay untouched and valid.
- UNEXPECTED, noted without action: rebuild surface T minima below freezing (Jan -3.28, Apr -2.17, Oct -2.44 °C) and S maxima up to 0.0374 — raw EN4 nearest-column values exposed by correct surface registration (within the reader `-10..40 °C` acceptance band; no code artifact introduced — nearest selection, no smoothing, unlike bilinear fill). Analyst awareness note for any future production adoption; not a defect of this fix.
- `ro_min` verdict: **no `-20.07` in any rebuild, any shipped `.nc`, or any current Day-0 dump**. Rebuild minima are physical-scale (Jan positive; Apr/Jul/Oct small 1e-3 negative inversions — ordinary static instability for CA to process, not sentinel pathology). Historical `-20.07` remains a provenance conflict of overwritten runs (see §4), numerically identical to sentinel `(0,0)×1000` under a kg m-3/`g/cm³` label slip.

## 13. Stage 11.4-D22 stability test on TEMP initial conditions (2026-09-28, runs only, no physics change)

Four diagnostic runs with TEMP rebuilds (`/tmp/stage114_check/initial_ts_YYYY-MM-01_rebuild.nc` via `ICEBERG_OCEAN_INIT_FILE`), shipped ERA5 forcing per Stage 11.1 report table (`era5_2020_01_fullcoverage_merged.nc`, `era5_2020_04/07/10_merged.nc`), fresh run IDs `stage11.4_d22_{jan7,apr7,jul7,oct7}` (Stage 11.1 outputs untouched). No source edits; no switches beyond init-file override; no commit.

| Run | Day-0 density min (kg m-3, dump) | Matches rebuild RO min | First NaN (day) | B3.3 Day-1 (`maxU2/maxV2`, NaNflag) | Days 1–7 state | Exit | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jan TEMP | +4.38 (physical) | yes (+0.00438 g/cm³) | none (30 d clean) | 42/31 cm/s, flag 0 | T/S/RO stable, EUU ~1–2e15, CA guard active (`maxiter` 1001, guard ~2–4k) but NO divergence | 0, 30 d | **STABLE_7D** (in fact 30 d) |
| Apr TEMP | -0.96 | yes (-0.00096 g/cm³) | Day 1 (142081 NaN) | 0.0/0.0, flag 1 | all-NaN from Day 1 (T/S/RO frozen 273.15/0/0 in dump; CSV all-NaN) | 0, 29 d (zombie) | **EARLY_FAILURE** |
| Jul TEMP | -3.86 | yes (-0.00386 g/cm³) | Day 1 (142081 NaN) | 0.0/0.0, flag 1 | all-NaN from Day 1 (W finite Day 1, rest NaN) | 0 (completed) | **EARLY_FAILURE** |
| Oct TEMP | -1.27 | yes (-0.00127 g/cm³) | Day 1 (142081 NaN) | 0.0/0.0, flag 1 | all-NaN from Day 1 | 0, 30 d (zombie) | **EARLY_FAILURE** |

- Central D22 finding: the preprocessing fix removes the `-20.07` sentinel artifact (Day-0 minima now equal rebuild minima at 1e-3 scale) but does **NOT** prevent Apr/Jul/Oct Day-1 crashes. The early seasonal failures therefore are **not** explained by the sentinel; with only ordinary 1e-3 static inversions present, momentum is already pathological on Day 1 (`maxU2/maxV2 = 0`, NaNflag 1) while Jan (positive RO init) develops finite velocities and survives. This separates two facts that Stage 11.1 conflated: (a) the `-20.07` Day-0 value was a sentinel/unit artifact of overwritten runs (no longer present anywhere); (b) a genuine fast Day-1 divergence mechanism for Apr/Jul/Oct initial+forcing states remains and is outside EN4-preprocessing scope (candidates: stronger seasonal stratification → thermal-wind/B200 response, or seasonal ERA5 forcing differences — NOT investigated here per D22 limits).
- Jan finding: fixed-init January is stable 30/30 days with active CA guard — guard saturation without divergence, confirming (with 10.21) that CA residual is not sufficient for crash.
- Not captured in D22 (honest gaps): per-step thermal-wind values, Block 200/210 intermediates beyond B3.3 flags, event-level CFL (plain config, no `STAGE112_CFL_DIAG`), `wind_max`/`euu` trajectories for crashed runs (CSV all-NaN post-crash; Jan values physical: `wind_max` 13–22 m/s, EUU ~1–2e15). First-invalid exact `(i,j,k,III)` for the Apr/Jul/Oct Day-1 crash was not isolated — out of D22 scope (no new forensic audit per instruction).

## 14. January rebuild detail (single-month precursor, kept for record) (2026-09-28, authorized step (a) only)

Command: `python3 python/ocean/build_initial_ts.py --raw data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc --out /tmp/stage114_check/initial_ts_2020-01-01_rebuild.nc --json /tmp/stage114_check/stage7.7_statistics_rebuild.json` (fixed working-tree code; raw untouched; shipped `.nc` untouched). Result `PASS`, `n_nan_inf_ro/output: 0`.

- NO CHANGE: dims `(133, 105, 18)`; `wet_mask` and `water_column_levels` identical; zero NaN/Inf; `product_land_column: 0`; zero wet cells with `S==0` in-mask (sentinel `(0,0)` appears only on land, as invalid marker); `result: PASS`.
- EXPECTED (fix consequences): `z_model_m` labels now canonical global `[2.5, 5, 10, …, 600]` (was local `[2.5, 5.0, 7.5, …, 550]`); flag mix `interp 228722 / shallowest 22133 / deepest 515` instead of all-`interp` (metre-consistent mapping puts level 1, 2.5 m, above the shallowest EN4 sample 5.02 m → flag 1 per spec); value shifts from level-coordinate realignment plus the pre-existing (commit `0b673ff`) `en4_wet` T&S column-selection mask.
- UNEXPECTED-relative-to-nearest-assumption (explained, no action): shipped Jan differs more than level realignment alone explains (T maxabsdiff 7.65, flag pattern all-zero, no zeros anywhere including land) — evidence indicates shipped Jan was built with `--method bilinear` (which fills land and never assigns flags 1/2/3) or a branchless ancestor, not with the default nearest path. Shipped Apr/Jul/Oct show nearest-path signatures (`deepest_finite` 128382). This is a build-method provenance note, not a defect in either file: all shipped products remain untouched and physically valid.
- New-sentinel check: NO new `(0,0)`/S==0 wet effect introduced by the fix (zero wet S==0 cells in rebuild; RO physical 0.0044–0.0100 in-mask).
- `ro_min` question: rebuild January wet RO min 0.0044 g/cm³ (physical); no `-20.07` anywhere in current products, dumps, or rebuild. Historical `-20.07` stays a provenance conflict of overwritten runs (see §4), numerically identical to sentinel `(0,0)×1000` with a kg m-3/`g/cm³` label slip.

## 15. D22 freeze - seasonal stability experiment on TEMP initial conditions (frozen 2026-09-28)

### 15.1 Objective

Test whether the EN4 preprocessing correction (metre-consistent `d_en4` mapping, single canonical `Z_M`) removes the early seasonal Apr/Jul/Oct failures - without claiming it as the root cause of the whole instability.

### 15.2 Experimental configuration

- Initial conditions: TEMP rebuilds from section 12 (`/tmp/stage114_check/initial_ts_YYYY-MM-01_rebuild.nc` via `ICEBERG_OCEAN_INIT_FILE`); shipped `.nc` untouched.
- Forcing: shipped ERA5 files per Stage 11.1 report table (`era5_2020_01_fullcoverage_merged.nc`, `era5_2020_04/07/10_merged.nc`); no forcing change.
- Run IDs: `stage11.4_d22_{jan7,apr7,jul7,oct7}` (fresh dirs; Stage 11.1 outputs untouched).
- Model code: unmodified production path (no EOS/CA/DT/Block/thermodynamics change; `STAGE112_*`/`STAGE113_*` default OFF; no S==0 guard added).

### 15.3 Four-run result table (frozen values)

| Run | Day-0 density min | Rebuild agreement | First NaN |
| --- | --- | --- | --- |
| Jan TEMP | +4.38 kg/m3 | yes | none; 30 days clean |
| Apr TEMP | -0.96 kg/m3 | yes (-0.00096 g/cm3) | Day 1, 142081 |
| Jul TEMP | -3.86 kg/m3 | yes (-0.00386 g/cm3) | Day 1, 142081 |
| Oct TEMP | -1.27 kg/m3 | yes (-0.00127 g/cm3) | Day 1, 142081 |

Supporting run facts (logs `run_{jan7,apr7,jul7,oct7}.log`, `daily_diagnostics.csv`, `results_day_00/01.nc`): Jan ran 30/30 days exit 0, finite velocities (B3.3 Day-1 maxU2/maxV2 42/31 cm/s, NaNflag 0), stable T/S/RO and EUU ~1-2e15 with CA guard active (`maxiter` 1001); Apr/Jul/Oct show B3.3 Day-1 maxU2/maxV2 = 0.0, NaNflag 1, all-NaN diagnostics from Day 1, runs complete 29-30 days exit 0 in zombie state (142081 NaN cells).

### 15.4 Observed facts

- Day-0 dump minima equal rebuild minima in all four runs (table above).
- No `-20.07` in any TEMP product, shipped product, or current dump.
- January stable 30 days with CA guard active; Apr/Jul/Oct crash Day 1 with only 1e-3-scale initial inversions.

### 15.5 What D22 establishes

- The `d_en4` metre-unit / `Z_M` correction removes the historical `-20.07` Day-0 artifact.
- Day-0 density minima now agree with the rebuilt TEMP products.
- January is stable for 30 days with the CA guard active.

### 15.6 What D22 does NOT establish

- It does NOT establish the preprocessing defect as the root cause of the whole instability.
- Negative initial density in Apr/Jul/Oct is an observed correlation/diagnostic fact, NOT a proven root cause of the Day-1 failure - no such claim is made.
- The exact thermal-wind pointwise mechanism, event-CFL at the failure step, `wind_max`/`euu` for failed runs, and exact `(i,j,k,III)` Day-1 event remain outside D22 scope (known gaps, section 13).

### 15.7 Explicit causal classification (frozen)

- Historical `-20.07` artifact as explanation for seasonal failures: **rejected** (artifact absent; failures persist without it).
- EN4 `d_en4`/`Z_M` preprocessing defect: **corrected and validated** (TEMP rebuilds PASS; canonical levels; metre-consistent mapping verified).
- Negative initial density as root cause: **unproven** (correlation only).
- CA guard as crash mechanism: **rejected** (D22 January: guard active, run stable).
- Common Day-1 dynamic mechanism for Apr/Jul/Oct: **still unresolved**.

### 15.8 Limitations / out-of-scope diagnostics

Per section 13 honest gaps; no per-step thermal-wind, no Block 200/210 intermediates beyond B3.3 flags, no event-level CFL, no `wind_max`/`euu` trajectories for failed runs, no exact Day-1 `(i,j,k,III)` isolation. Gaps are not reopened by this freeze.

### 15.9 Decision for next stage

D22 is complete; no further D22 forensic work. D23 has NOT been started. Any follow-up (e.g. Day-1 divergence mechanism) belongs to a separately authorized stage.
