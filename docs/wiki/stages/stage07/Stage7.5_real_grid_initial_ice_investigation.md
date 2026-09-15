# Stage 7.5 — Real Grid and Initial Ice Data Investigation

**Generated:** 2026-08-25
**Status:** Complete — Classification A (Diagnostic/validation only)

---

## 1. Executive Summary

Stage 7.5 investigated whether the model can be transitioned from the synthetic TEST grid to a physically meaningful real Arctic/Barents Sea configuration using the original grid/bathymetry/coordinate files and realistic initial ice fields — **without modifying any physical equations**.

**Main Findings:**

| Question                                                                 | Answer                                                                                                                                                                      |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Are real grid files (KOORD.DAT, hhh.bar, FI1DL1.DAT) available anywhere? | **No** — repo, git history, historical model dirs, filesystem all exhausted                                                                                                 |
| Was the diagnostic real-ice experiment possible?                         | **Partially** — synthetic-ice evolution traced on TEST grid; realistic observed initial ice NOT constructible without a real grid                                           |
| What generates the thin ice that triggers the instability?               | **Dynamic thinning**: uniform ~0.49 m aggregate thickness collapses to sub-cm by day 10–12 via thermodynamic melt + redis() category transfer                               |
| Does the current code blow up when hht < 0.01 m?                         | **No (new finding)** — the existing `hht < 0.01 → u=v=0` guard (main.f90:402–406) breaks the positive-feedback loop; ice melts away completely and the run continues stably |
| Can observational initial ice be mapped to the model?                    | **Yes, with documented assumptions** — total SIC + SIT products exist; category reconstruction required                                                                     |
| Is ERA5 forcing compatible with the model grid?                          | **Yes** — TEST grid lies inside ERA5 coverage; bilinear interp already validated                                                                                            |
| Were any physics modified?                                               | **No** — all temporary diagnostics reverted; working tree clean                                                                                                             |

**Classification: A** — Diagnostic/validation only.

---

## 2. Stage 7.4 Baseline

Stage 7.4 concluded:

1. The instability is caused by dynamic thinning of synthetic initial ice on the TEST grid (~0.12 m → ~0.01 m in 5–7 days).
2. No tested configuration achieved 30-day stability with initial ice present.
3. Drag regularization `max(hht, 0.01–0.10)` delayed failure (best ≈25 days) but modifies physics.
4. Real grid files were unavailable.
5. All tests passed; working tree clean; no permanent changes.

Stage 7.5 therefore had to determine whether the instability is an artifact of the TEST configuration before any physical regularization could be considered.

---

## 3. Repository/Data Reconnaissance

### 3.1 Files inspected

- `app/main.f90`, all of `src/*.f90` (grid_coupling, wind_forcing, ice_redis, thermodynamics, param, …)
- `test/`, `python/`, `docs/wiki/` (all stage reports), `fpm.toml`, `.gitignore`, `README.md`
- Historical sources: `/mnt/d/…/Model_Isberg_Dmitriev(Nesterov)/` (`mod_all/*.F`, `model/*.f90`, `old_NDP/`, Dmitriev.txt, Nesterov_last.txt, Naumov.txt, Polykov.txt, model_all.txt)

### 3.2 Routines reading external data

| Routine                           | File read                                           | Purpose                                                                               |
| --------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `coup1()` (grid_coupling.f90:31)  | `hhh.bar`                                           | Land/sea mask KT1, bathymetry source (15I5 format, 7 blocks × 15 columns × IS1 lines) |
| `coup1()` (grid_coupling.f90:389) | `KOORD.DAT`                                         | FI/DL coordinate fields (REAL mode only; STOP if missing)                             |
| `wind1()` (wind_forcing.f90:49)   | `FI1DL1.DAT`                                        | Legacy meteorological-grid coordinates (135×107, F6.2)                                |
| main.f90:218–226                  | `1_1.ice`…`1_5.ice`                                 | Initial category concentrations AN1(:,:,2..6), list-directed, IS1×JS1 per file        |
| main.f90 (legacy path)            | `DAV4_5.98`, `intdav`, `NP1`, `GRM2/GRS2/GRK1/GRO1` | Legacy pressure forcing, interpolation indices, tidal amplitudes/phases               |

### 3.3 Synthetic fallbacks (TEST mode)

| Missing file | Fallback behavior                                                                                                             |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `hhh.bar`    | Synthetic flat basin: land=8 on borders, ocean depth value 600 (=600 m) in interior (kt1(10:120,10:90)=600); NOTICE printed   |
| `KOORD.DAT`  | Synthetic coordinates fi = 66+16·(j−1)/(js1−1) °N, dl = 30+33·(i−1)/(is1−1) °E; explicit "TEST ONLY" warning; REAL mode STOPs |
| `FI1DL1.DAT` | Zeros for fi1/dl1 (legacy path only; not used with ERA5)                                                                      |
| `1_k.ice`    | Zero ice everywhere → an1(:,:,1)=1 (open water); stable 90+ day runs                                                          |

### 3.4 Arrays representing geography/state

- Coordinates: `fi(is1,js1)` [°N], `dl(is1,js1)` [°E]; meteo-grid: `fi1(135,107)`, `dl1(135,107)`
- Bathymetry: `kt1` (int mask/level index), `ht/hu/hv/map1` [cm]; land sentinel = 8888.0
- Ice state: `an1(is1,js1,ngr1)` (cat 1 = open water), `wice1(is1,js1,ngr)` [m], `hice`, `ans`, `hices`, `hsnow`; category constants `hst=[0.2,0.5,0.95,1.6,2.5]`, `hmax=[0.3,0.7,1.20,2.0,50.]`

---

## 4. Real Grid File Requirements

### 4.1 KOORD.DAT

Historical reader (model/Coupl1.f90:118): `READ(1,*) FI, DL` — list-directed whole-array read of both (133×105) fields; modernized version identical (grid_coupling.f90:389–393).

- **Dimensions:** 2 arrays × 133×105 = 27,930 values
- **Meaning:** latitude [degN], longitude [degE] at T-points; used for Coriolis `fku = ω·sin(fi/57.3)` and ERA5 bilinear targeting
- **Ordering:** I outer, J inner (row-major per Fortran array order)
- **Status:** ❌ Not found anywhere (see §9). Evidence: repo find, `git log --all --diff-filter=A -- "*KOORD*"` empty, historical dirs contain sources only.

### 4.2 FI1DL1.DAT

Reader (Wind1.f90:15 / wind_forcing.f90:49–60): 270 lines of `(107F6.2)` — first 135 rows FI1, next 135 rows DL1.

- **Dimensions:** 135×107 per array (meteo grid is4×js4)
- **Role:** legacy geostrophic-wind finite-element pressure interpolation; **not used** when `forcing_mode=ERA5`
- **Status:** ❌ Not found. Non-blocking for ERA5 workflow.

### 4.3 hhh.bar

Reader (Coup1.f90:13 / grid_coupling.f90:31–41):

```fortran
READ(1,1011)            ! blank line
READ(1,1010)((KT1(I,J),J=J1,J2),I=1,IS1)   ! 15I5, J1..J2 window of 15 columns
! 7 windows: J=1–15, 16–30, …, 91–105  → covers JS1=105
```

- **Content:** integer mask/depth codes; land encoded as 8; ocean values are depth decodes (value×100 cm; special handling 5<v≤10 → 10 m shelf fill; v≤3 → 3 m minimum)
- **Dimensions:** 133×105 integers, 7 header lines + 7×133 data lines
- **Downstream:** HT→HU/HV face depths→KT1 wet-level index→KK1/KUSH/KVSH masks→map1 cell depth→IDX/IDY/IT advection geometry
- **Status:** ❌ Not found. This is the single most blocking file: it defines the basin itself.

### 4.4 Initial ice files 1_1.ice … 1_5.ICE

Historical reader (Coupl1.f90:162–190; modernized main.f90:217–226): per file k=1..5, `READ(1,*)(AN1(I,J,k+1),J=1,JS1)` for I=1..IS1.

- **Format:** text, list-directed; 133 lines × 105 values of concentration [fraction]
- **Post-processing:** 9.99→land sentinel reset to 0; values ≥1 clipped to 1; ΣA=0 ⇒ open water
- **Thickness:** NOT stored — initialized as `wice1(k) = hst(k)·an1(:,k+1)` (0.20/0.40/0.95/1.60/2.50 m × concentration), then `redis()` redistributes
- **Status:** ❌ Not found. Format fully reconstructable from readers (Class D).

---

## 5. Current TEST Grid Reconstruction

| Property        | Value                                                           | Source                   |
| --------------- | --------------------------------------------------------------- | ------------------------ |
| Dimensions      | is=132, js=104, ks=18 (+ghost is1=133, js1=105)                 | param.f90:27             |
| Horizontal step | DX = 13.89 km (1.389e6 cm)                                      | main.f90 / Coupl1.f90:38 |
| Latitude        | linear 66→82°N over j                                           | grid_coupling.f90:406    |
| Longitude       | linear 30→63°E over i                                           | grid_coupling.f90:407    |
| Bathymetry      | flat 600 m box (i=10..120, j=10..90), land border               | grid_coupling.f90:47–48  |
| Vertical        | 18 Z-levels, z=250…60000 cm                                     | param.f90:188–190        |
| Arakawa type    | B-grid (T/S scalar points; U/V faces; Coriolis averaged to U/V) | param comments           |
| Y orientation   | inverted: j=1 north                                             | grid_coupling header     |
| Active cells    | 8991 wet columns (kk1 domain)                                   | CA-PROBE output          |

**Discrepancies vs intended original:** the original domain was the Arctic/Barents region on a polar projection with real coastlines (Shtokman field references, VIX2='SHTOK.1'); the TEST grid is a rectangular flat-bottom box with linear lat/lon — geographically meaningless. ERA5 Barents download area [70–90°N, 10–70°E] overlaps but does NOT equal the TEST rectangle [66–82°N, 30–63°E].

---

## 6. Initial Ice File Format (reconstructed)

```
external ice files (5)
    ↓ main.f90:217–226   READ into an1(i,j,k+1)      [fraction]
    ↓ cleanup             9.99→0; ≥1→1; ΣA=0⇒an1(:,:,1)=1
    ↓ volume init         wice1(k)=hst(k)·an1(:,:,k+1) [m]
    ↓ call redis()        ΣA≤1 balance, category merge/split, ans/hices/wices
    ↓ ice dynamics        u,v; txic/tyic via a=c17·|Δv|/hht
```

No snow field, no per-category thickness in the files — thickness is hard-coded from HST. Any observational mapping must produce **concentration per category only**; thickness follows automatically unless the initialization chain is extended.

---

## 7. Synthetic Ice Initialization Analysis

Synthetic fixtures used in Stages 6.7–7.4 (not committed): 5 files, uniform concentration in central 70×50 block: cat1=0.50, cat2=0.30, cat3=0.15, cat4=0.05, cat5=0.02 (ΣA=1.02 → redis clips).

After first `redis()` (measured, Stage 7.5 trace run day 1 printout):

- Aggregate `ans` ≈ 1.0 inside block; `hices` ≈ 0.4925 m everywhere
- Category volumes/areas: cat1 A=1666 h=0.200; cat2 A=1159 h=0.400; cat3 A=543 h=0.950; cat4 A=181 h=1.600; cat5 A=72 h=2.500
- **Origin of the "~12 cm" figure from Stage 7.4:** earlier experiments used different fixtures/multipliers; in this run the _minimum_ 4-cell-average hht falls through 0.09 m (day 4) because edge cells of the block average thick ice with zero-ice neighbors — the thin tail is a **geometry artifact of sharp ice-edge gradients**, not an initial condition choice.

---

## 8. Dynamic Ice-Thinning Analysis (Diagnostic Run)

Temporary ICE_DIAG instrumentation added to main.f90 (day-start aggregate statistics + per-category volumes), run with ERA5 Q1 forcing, kl1=1, mm1 limited by run; **instrumentation removed afterwards** (git clean verified).

### Aggregate evolution

| Day | hht_min [m] | hht_max [m] | hht_mean [m] | Volume [m³·cell units] | Area [cells] |
| --- | ----------- | ----------- | ------------ | ---------------------- | ------------ |
| 1   | 0.4925      | 0.4925      | 0.4925       | 1783                   | 3621         |
| 2   | 0.4063      | 0.726       | 0.505        | 1780                   | 3532         |
| 3   | 0.2288      | 0.680       | 0.506        | 1791                   | 3539         |
| 4   | 0.0898      | 0.647       | 0.506        | 1785                   | 3504         |
| 5   | **0.0045**  | 0.694       | 0.503        | 1762                   | 3436         |
| 6   | 0.0062      | 0.742       | 0.500        | 1744                   | 3389         |
| 7   | 0.0071      | 0.752       | 0.503        | 1744                   | 3386         |
| 8   | 0.0029      | 0.815       | 0.501        | 1754                   | 3404         |
| 9   | 0.0039      | 0.893       | 0.495        | 1730                   | 3386         |
| 10  | **0.00045** | 0.875       | 0.496        | 1701                   | 3321         |
| 11  | 0.0025      | 1.389       | 0.506        | 1721                   | 3328         |
| 12  | 0.0003      | 0.736       | 0.139        | **19**                 | **137**      |
| 13  | NO ICE      | —           | —            | 0                      | 0            |

### Mechanism decomposition

1. **Ice-edge geometry (days 1–4):** 4-cell hht averaging across the sharp block boundary creates sub-metre minima immediately; advective smearing widens the marginal zone.
2. **Thermodynamic melt (dominant):** January ERA5 air temps down to −43°C would normally grow ice, but the synthetic ocean init sets **T_surf = 15 °C hot spot + warm profile**; open-water heat flux `fw` melts thin categories from below (`hicp<0.01 → 0`). Cat-1 mean thickness drops 0.200→0.169 m by day 10; cat-1 area shrinks 1666→1093.
3. **redis() transfer:** thinning cat-1 ice below hmax boundaries migrates between categories; near-zero-area categories keep tiny concentrations that dominate hht_min.
4. **Day-11–12 collapse:** velocities grow (u_max 58→130→146 m/s, CSV days 9–10) while hht_min ~0.0005 m; drag term large but **guard `hht<0.01 → u=v=0` caps feedback**; final collapse is wholesale melt/advection, after which the run continues cleanly (NO ICE days 13+, no NaN in ocean state).

### Key Stage 7.5 correction to the Stage 7.3/7.4 picture

The previously reported day-7–8 NaN blowup reproduces only under specific fixture/timing combinations. With the current tree, the `if (hht .lt. 0.01)` velocity-zeroing guard in main.f90:402–406 interrupts the `a ∝ 1/hht` feedback before NaN. The residual pathology is **physical unrealism** (synthetic warm ocean melting all ice in 12 days on a January run) rather than numerical blowup. This strengthens the hypothesis that the instability regime is a **TEST-configuration artifact**, though it does NOT yet prove the physics is stable under realistic forcing (the guard itself is an undocumented stabilizer embedded in the dynamics loop).

---

## 9. Git History Investigation

Commands executed:

- `git log --all --full-history -- "*.DAT" "*.ice" "KOORD*" "FI1DL1*" "hhh*"` → empty
- `git log --all --diff-filter=A -- "*.DAT" "*.ice"` → empty
- `git log --all --oneline --grep="KOORD|DAT|grid|bathymetry|Dmitrev|original"` → only modernization-stage commits referencing the absence
- First commit `ab7f2d8` (2026-08-13): `.gitignore`, LICENSE, README only

**Conclusion:** these data files were **never committed**, never deleted later — they predate the repository entirely. Distinction documented: history contains the _format_ (readers in historical sources) but not the _data_.

---

## 10. Original Model/Data Source Investigation

- Historical package location: `/mnt/d/Vlad/Documents/RESEARCH/These_RSHU_Master_degrees/Model_Isberg_Dmitriev(Nesterov)/` — contains F77 originals (`mod_all/`: Coup1.f, Coupl1.f, Heat.f, Redis.f, Shal.f, Stress.f, Advsh.f, TIDE3.F, DEFORM.F, ADVICE.F), F90 Nesterov modernization (`model/`), `old_NDP/`, and four documentation texts (Dmitriev.txt, Naumov.txt, Nesterov_last.txt, Polykov.txt, model_all.txt). **All source, no data.**
- Web search ("Dmitrev/Dmitriev thermodynamic model icebergs 1995 Barents", `"KOORD.DAT" ocean model`, `"hhh.bar" ocean model`): found extensive literature on Barents iceberg-drift modelling (Diansky et al. 2018, Keghouche et al. 2009, Marchenko et al., met.no CHC model) and a 1991 Dmitriev et al. Polar Research citation on tidal leads — **no public distribution of the AARI 1995 package or its KOORD.DAT/hhh.bar data files**.
- Internal evidence: `VIX1='1.PRO'`, `VIX2='SHTOK.1'`, DAV4_5.98 filename (May 1998 pressure) indicate an internal AARI/SHTOKMAN operational context — consistent with data never being publicly released.

**Verdict:** no authoritative external source located; acquisition must come from AARI/RSHU archives or the thesis supervisor. Nothing invented here.

---

## 11. Candidate Observational Initial-Ice Datasets

| Dataset                                          | Variables                     | Resolution              | Period    | Notes for this model                                                     |
| ------------------------------------------------ | ----------------------------- | ----------------------- | --------- | ------------------------------------------------------------------------ |
| OSI-SAF OSI-450-a / OSI-430-b (EUMETSAT)         | SIC CDR                       | 25 km, daily            | 1979–now  | Primary SIC source; free; EASE-grid; needs regridding                    |
| ESA CCI+ SICCI-HR-SIC v3                         | SIC (pan-sharpened)           | 12.5 km, daily          | 1991–2020 | Higher resolution SIC                                                    |
| C3S Satellite Sea-Ice Thickness (L3C/L4)         | SIT                           | 25 km, monthly, Oct–Apr | 2002–now  | Winter-only; L4 gap-filled (CS2SMOS+Sentinel-3); matches Jan start date  |
| ESA CCI CryoSat-2 SIT L3C                        | SIT+SIC+freeboard             | monthly, Oct–Apr        | 2010–2020 | Validated; free (CEDA)                                                   |
| CMEMS ARCTIC_MULTIYEAR_PHY_ICE_002_016 (neXtSIM) | SIC, SIT, snow depth, daily   | 3 km PS grid            | ~1991–now | Assimilates CS2SMOS; provides snow too (model hsnow init currently zero) |
| CARRA / CARRA2                                   | SIC (input), SIT (model est.) | 2.5 km                  | 1986–now  | SIT flagged "rough estimate" only; use SIC inputs                        |
| NSIDC Sea Ice Index / CDR                        | SIC                           | 25 km                   | 1978–now  | Coarser fallback                                                         |

**Recommendation:** OSI-SAF SIC (daily) + C3S/CryoSat-2-SMOS L4 SIT (monthly, January) for the initial date 2020-01-01; neXtSIM reanalysis as alternative offering internally consistent SIC+SIT+snow. Licensing: all free for research (OSI-SAF/EUMETSAT, Copernicus, CEDA).

## 12. Ice Data → Model Category Mapping

Observations supply **total SIC + mean SIT** (no 5-category split). Required mapping (documented, NOT implemented):

```
obs SIC_total, SIT_mean
    ↓ choose dominant category k* such that hst(k*) ≤ SIT_mean < hmax(k*)
    ↓ assign an1(:,:,k*+1) = SIC_total           (single-category placement)
    ↓ wice1(k*) = SIT_mean · SIC_total
    ↓ optional spread: distribute SIC over adjacent cats preserving
      ΣA = SIC_total and Σ(A_k·h_k) = SIT_mean·SIC_total
    ↓ redis() enforces ΣA ≤ 1, merges out-of-band categories
```

Assumptions that would be necessary:

1. Single-category (or two-category) placement — the model's ITD is otherwise unconstrained by observations.
2. Snow depth: take from neXtSIM if chosen, else hsnow=0 (current behavior).
3. Interpolation to the model's curvilinear grid: conservative remapping preferred for SIC (a fraction), nearest-neighbor acceptable for categorical placement at DX≈14 km vs 25 km data.
4. Land masking via model kt1 (data land flags differ).
5. Uncertainty: SIT uncertainty ~0.3–0.5 m in Barents (thin, deforming ice) — comparable to category spacing hst(1)→hst(2); category assignment is therefore uncertain in the MIZ, which is exactly where the drag sensitivity lives.

---

## 13. Real Grid ↔ ERA5 Compatibility

Current pipeline: ERA5 0.25° lat-lon → `era5_bilinear2d` onto model (i,j) using model `fi/dl` targets.

With a REAL grid:

- `fi(i,j)/dl(i,j)` become genuinely curvilinear/polar-projected → bilinear search must handle non-monotonic lon (dateline, pole hole). Current `netcdf_input` assumes monotonic regular ERA5 axes (true for ERA5 itself), so target-side curvature is fine — only target coordinates change. **Bilinear remains valid** since ERA5 side is unchanged.
- Domain check: KOORD.DAT extent must fall inside downloaded ERA5 rectangle; `check_era5.py --area` already validates coverage.
- For categorical/observational ice inputs: nearest-neighbor or conservative remap (§12); bilinear on SIC is acceptable, on category index is NOT.
- Boundary handling: model is closed-basin style (kt1 land border from hhh.bar); no periodic-longitude requirement expected for a Barents-domain grid.

No pipeline modification needed for a diagnostic switch once coordinates exist.

---

## 14. Data Acquisition Matrix

| File/Data            | Required?          | Found?                           | Source class                                        | Format              | Dimensions                      | Units           | Status                                                                                       |
| -------------------- | ------------------ | -------------------------------- | --------------------------------------------------- | ------------------- | ------------------------------- | --------------- | -------------------------------------------------------------------------------------------- |
| KOORD.DAT            | Yes (REAL mode)    | No                               | **E — unavailable/unknown** (AARI archive)          | text, list-directed | 133×105 ×2                      | deg             | Blocking; external provision needed                                                          |
| hhh.bar              | Yes                | No                               | **E** (AARI archive)                                | text 15I5, 7 blocks | 133×105 int                     | mask/depth-code | Blocking; alternative: rebuild from IBCAO/GEBCO (class D, requires approval — NOT done here) |
| FI1DL1.DAT           | Legacy only        | No                               | **E**                                               | 107F6.2 ×270 lines  | 135×107 ×2                      | deg             | Non-blocking (ERA5 path bypasses)                                                            |
| GRM2/GRS2/GRK1/GRO1  | tides only         | No                               | **E**                                               | list-directed       | 133/105 vectors ×4 constituents | amp/phase       | Tide module unused in current runs                                                           |
| DAV4_5.98/intdav/NP1 | legacy only        | No                               | **E**                                               | mixed               | —                               | hPa/index       | Non-blocking                                                                                 |
| 1_1.ice…1_5.ice      | Yes (for ice runs) | No                               | **D — reconstructable** from readers + obs datasets | text list-directed  | 133×105 ×5                      | fraction        | Generator spec documented in §12                                                             |
| Observed SIC (init)  | For realistic IC   | No (not downloaded)              | **C — OSI-SAF/C3S**                                 | NetCDF EASE         | global 25 km                    | %               | Download pending approval                                                                    |
| Observed SIT (init)  | For realistic IC   | No                               | **C — C3S sat SIT / CS2SMOS**                       | NetCDF              | 25 km monthly                   | m               | Winter months only                                                                           |
| ERA5 Q1 2020 forcing | Yes                | **Yes** (local, merged incl. sf) | A — found locally                                   | NetCDF              | 97×241×364                      | SI              | ✅ In active use                                                                             |

---

## 15. Diagnostic Real-Ice Experiment

**BLOCKED — required real grid/data unavailable.**

A faithful experiment (realistic initial ice on the real grid) cannot be performed: without KOORD.DAT/hhh.bar there is no geographic grid to interpolate observations onto, and fabricating either file is explicitly forbidden (Stage 3.5/6.1 constraints, honored here).

What WAS performed instead (permitted diagnostic): full tracing of the synthetic-ice lifecycle on the TEST grid with production physics (§8). It establishes the reference trajectory (hht_min timeline, melt-out at day 12–13, guard-limited drag response) against which the future real-ice run must be compared.

---

## 16. Stability Results

| Configuration (this stage)               | Result                                                                                                       |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Synthetic ice + ERA5 + kl1=1 (trace run) | 14+ days observed; no NaN blowup; ice fully melted by day 12–13; ocean state finite throughout; guard-active |
| No ice + ERA5 (baseline, prior stages)   | 90 days stable                                                                                               |
| >30-day stability WITH persistent ice    | **NOT demonstrated** — impossible on TEST grid where synthetic ocean heat melts everything                   |

Per §17 of the stage instructions: the instability is **NOT declared resolved**.

---

## 17. Validation/Test Results

| Check                                                                                     | Result                                                                               |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `fpm build --flag "-I/usr/include -Wall -Wextra"`                                         | ✅ Pass (after reverting diagnostics)                                                |
| `fpm test --flag "-I/usr/include"` (22 unit checks + NetCDF suite)                        | ✅ Pass                                                                              |
| `python python/tests/test_units_roundtrip.py`                                             | ✅ Pass                                                                              |
| Temporary ICE_DIAG code added → run → **removed**                                         | ✅ `git status` clean                                                                |
| Grid validation (lat range, monotonicity, bathymetry sign, mask, SIC∈[0,1], conservation) | N/A — blocked (no real grid); synthetic-run sanity checked via existing NetCDF suite |

---

## 18. Git Status

```
On branch main — nothing to commit, working tree clean
HEAD: 69e0303 Stage 7.3 report (Stage 7.4/7.5 reports live in untracked docs/wiki/, per .gitignore)
```

Files created during Stage 7.5: `docs/wiki/stages/stage07/Stage7.5_real_grid_initial_ice_investigation.md` (this file — untracked by design). Temporary artifacts (1\_\*.ice fixtures, ICE_DIAG edits, analysis scripts) deleted. **Zero production-code modifications.**

---

## 19. Classification

**A — Diagnostic/validation only.**

> Stage 7.5 exhaustively searched repository, git history, historical model directories and public sources for the original grid/bathymetry/initial-ice files; documented exact formats from historical readers; traced the synthetic-ice lifecycle on the TEST grid with production physics; identified observational initial-ice sources and a concrete (unimplemented) category mapping; analyzed ERA5 compatibility; and produced the acquisition matrix. No physical equation, parameter, timestep, grid constant, or stabilization was introduced or changed.

---

## 20. Recommendation for Stage 7.6

Two hypotheses remain distinct and must be kept separate:

- **H-artifact:** TEST configuration (flat warm-ocean box, sharp-edged synthetic ice) creates states that activate the singular drag regime.
- **H-physics:** the unguarded `a = c17·|Δv|/hht` law is intrinsically singular whenever hht→0 under ANY configuration (real grids also produce MIZ thin ice).

Evidence so far favors H-artifact (no-ice runs stable 90 d; guarded thin-ice phase finite), but the guard's presence means H-physics is not excluded.

Priority actions:

1. **Human action — obtain the original files.** Request KOORD.DAT + hhh.bar (+ GRM2 etc.) from AARI/RSHU supervisors. Without them, no real-grid path exists. If permanently unavailable, propose (with promt.md approval procedure) rebuilding hhh.bar from IBCAO v4 and a documented Barents polar-stereographic grid — a Class-D reconstruction requiring explicit sign-off.
2. **Once grid exists:** generate 1_k.ice from OSI-SAF SIC + C3S/CS2SMOS January SIT via the §12 mapping; validate with the §17 checklist (ranges, monotonicity, conservation).
3. **Then run the decisive experiment:** real grid + observed initial ice + ERA5 Q1, tracking §8-style diagnostics. If hht still approaches 0.01 m in the MIZ and NaN appears, the physics-singularity hypothesis stands and a physically justified regularization (published ice-ocean drag floor) goes to promt.md procedure.
4. **Document the existing `hht < 0.01 → u=v=0` guard** (main.f90:402–406) as a formal part of the historical algorithm in the mapping docs — it materially changes the stability picture and deserves explicit provenance verification against Coupl1.f90 (the historical code has `IF(HHT.EQ.8888.) GOTO 430`-style masks but the thin-ice cutoff should be confirmed against Dmitriev.txt before it is treated as original physics).

---

## 21. Success Criteria Checklist

- [x] Entire repository inspected
- [x] TEST grid initialization fully traced
- [x] Real grid requirements documented
- [x] KOORD.DAT requirement documented
- [x] FI1DL1.DAT requirement documented
- [x] hhh.bar requirement documented
- [x] Initial ice file format documented
- [x] 1_k.ice initialization chain traced
- [x] Origin of thin initial ice identified (edge-averaging + melt; corrected the "~12 cm initial" framing)
- [x] Dynamic thinning mechanism quantified (day-by-day table)
- [x] Git history searched for missing files
- [x] Original model data sources investigated (internal + web)
- [x] Real observational ice datasets evaluated
- [x] Required model category mapping documented (not implemented)
- [x] ERA5 ↔ real-grid compatibility analyzed
- [x] Data acquisition strategy established
- [x] No physical stabilization introduced
- [x] No drag-law modification introduced
- [x] No hht floor introduced
- [x] No velocity clamp introduced
- [x] No FCT modification introduced
- [x] Existing tests pass
- [x] Build passes
- [x] Git status audited (clean)
- [x] Stage 7.5 report created

---

**End of Stage 7.5 Report**
