# Stage 7.7 — Phase 2: Dataset Selection for Realistic Initial Ocean T/S

**Classification: A (selection)** — decision made with justification, environment
constraints, and reproducibility plan. Chosen product is **EN4.2.2** monthly
objective analysis (Gouretski–Reseghetti `g10` corrections), **January 2020**.

**Date:** 2026-08-27

---

## 1. Requirements the dataset must satisfy (from the Stage 7.7 brief)

1. **Time**: representative of approximately **2020-01-01** (model run start).
   Monthly or daily resolution acceptable within ±1 month; year-specific 2020
   strongly preferred over climatology.
2. **Coverage**: entire model domain 64.2–85.0°N, 8.3–76.3°E (Barents + Nordic
   Seas), i.e. a regular grid that fully contains it with margin (no edge
   artefacts at the model boundary).
3. **Vertical range**: down to **≥ 600 m** (model Z(18) = 600 m) with several
   levels above 50 m (model top layer 2.5 m); realistic ESA telescopes toward
   the surface.
4. **Physical fields**: temperature (→ °C in-situ-like) and salinity (→ mass
   fraction 0.033–0.035).
5. **Access**: must be downloadable **from this environment** (ERA5 via CDS was
   fine; **no CMEMS/OceanProducts credentials exist**), ideally without new
   accounts, and reproducible on a fresh clone.
6. **Size**: modest (single month, not a 10+ GB global reanalysis download).
7. **Licence**: usable for the master's thesis (research/non-commercial).

## 2. Candidates evaluated

| Product                                       | Res. (horiz) | Vertical           | Time                             | Auth needed              | Verdict                                                   |
| --------------------------------------------- | ------------ | ------------------ | -------------------------------- | ------------------------ | --------------------------------------------------------- |
| **EN4.2.2 analyses** (`g10`)                  | 1°×1°        | 42 levels 5–5350 m | monthly (month-specific)         | none (HTTP)              | **SELECTED**                                              |
| CMEMS GLORYS12 _GLOBAL_MULTIYEAR_PHY_001_030_ | 1/12°        | 50 levels          | daily                            | CMEMS scihub credentials | **Rejected – no credentials in env**                      |
| WOA18 (NOAA NCEI)                             | 1/4°×1/4°    | 43 levels          | Jan-mean climatology (1981–2010) | none (HTTP)              | **Rejected – climatology, not 2020**                      |
| WOD/Argo raw profiles                         | point data   | n/a                | monthly                          | none                     | Rejected – not an analysis; winter Arctic data too sparse |

### 2.1 EN4.2.2 — selected

- Met Office Hadley Centre "EN4" quality-controlled ocean temperature & salinity:
  monthly **objective analyses** on a regular 1° grid over 360×173 lat/lon
  (lat −83…89°N, lon 1…360°E), **42 depth levels 5.0–5350 m**.
- January 2020 file: `EN.4.2.2.f.analysis.g10.202001.nc`, time = **mid-month
  (2020-01-16)** — closest available month-specific state to 2020-01-01.
- Variables: `temperature` = **potential temperature [K]**, `salinity`
  [practical, "units: 1"], plus uncertainty & observation-weight fields
  (useful for QC reporting).
- Bias corrections: **Gouretski & Reseghetti (2010) XBT / Gouretski & Cheng
  (2020) MBT** (`g10` ensemble member) — the standard open-data choice.
- Licence: **Non-Commercial Government Licence v2** (research OK — thesis fits).
- **Why not GLORYS12 (finer, daily)?** It is the scientific ideal, but its
  download requires a CMEMS/SciHub account; this environment holds none and it
  cannot be created non-interactively. 3-day runs are insensitive to ≤15-day
  initial-state drift, making EN4's monthly step acceptable (see §5).
- **Why not WOA18?** 0.25° climatology of 1981–2010 January means. Barents
  winter temperature anomaly vs 2020 can reach ±1 °C; a climatology would inject
  a year-averaged bias that a month-specific analysis does not.

## 3. Acquisition mechanics (executed & reproducible)

- EN4 publishes yearly zips only (`EN.4.2.2.analyses.g10.2020.zip`, 302 MB for
  the 12-month set). A **surgical HTTP range extraction** was implemented
  (temp. proof, `/tmp/opencode/en4_extract_probe.py`):
  1. HEAD → `accept-ranges: bytes`, total size from `Content-Range`.
  2. Fetch last 64 KiB → locate End-Of-Central-Directory → central-directory
     offset/size (1,236 B for 12 members).
  3. Parse central directory → local header offset & compressed size of member
     `*202001*` → fetch local header + deflate stream (~26.4 MB) → inflate →
     CRC32 verify → netCDF.
  4. Result: `/tmp/opencode/EN.4.2.2.f.analysis.g10.202001.nc`
     (26,522,706 B inflated, CRC verified), ≈ **1/12 of the full-archive
     transfer**.
- This will be finalized as `python/ocean/download_initial_ts.py` (Stages
  P3/P15) with the check-step baked in.

## 4. Verified content summary (this run)

- `temperature` units **kelvin** (potential), `salinity` units **1** (practical).
- time = `2020-01-16T12:00:00`; depth n=42: 5.0 … 5350 m (covers model 2.5–600 m
  except the 0–2.5 m top strip — see §5).
- Whole-product valid stats: T ∈ [−4.21 … +31.24] °C (n≈1.545 M), S ∈ [4.59 …
  40.78] — global plausible.
- Region check 64–86°N, 8–77°E (surface): T ≈ **−3.3 … +7.9 °C**, S ≈ **7.9 …
  37.4** — physically reasonable for January Barents/Nordic (Atlantic Water
  inflow 5–8 °C at surface in the western flank; cold, fresh melt-influenced
  cells present).
- Grid fully contains the model domain with ≥ ~8° east/west margin; lat range
  −83…89°N leaves the domain interior (no clipping).

## 5. Known caveats & mitigations (documented, not hidden)

| Caveat                                                             | Severity | Mitigation / note                                                                                                                                                                                                  |
| ------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Potential temperature (θ) used with the model's in-situ-Eckart EOS | low      | θ − T_in-situ ≤ 600 m is < ~0.02–0.05 °C (K≈273 at Arctic T); record θ in provenance; model treats T as its state variable.                                                                                        |
| Practical salinity → mass fraction (÷1000)                         | low      | Exactly the model's documented unit (AGENTS.md); Eckart coefficients use the same scaling.                                                                                                                         |
| Mid-month (Jan 16) vs target (Jan 01)                              | low      | Propagation of a ±15-day offset over 3 model days is negligible for T/S volumes; noted in QC narrative.                                                                                                            |
| 1° resolution smooths fronts                                       | moderate | Cannot resolve Barents Sea fronts at 1°; acceptable for _initial_ state of a coarse (≈13 km equivalent) model; decision documented.                                                                                |
| Top 2.5 m strip                                                    | low      | EN4 level 1 centre = 5.02 m (layer 0–10 m). Model needs 2.5 m. Vertical regridding (P6) linear-interpolates nothing above 5 m → use level-1 value for model level 1 (surface-mixed assumption), not extrapolation. |
| Land/coast mismatch (1° vs 13 km IBCAO)                            | moderate | Horizontal regridding (P5) is mask-respecting: every model wet cell is filled from the nearest wet EN4 cell (nearest-neighbour, no cross-land interpolation, no fill over land gap > 1 EN4 cell → report).         |

## 6. Decision

**Acquire `EN.4.2.2.f.analysis.g10.202001.nc`** (EN4.2.2, g10, 2020-01).
Backup order if the Met Office host becomes unreachable: (a) ICDC mirror
(www.cen.uni-hamburg.de) → (b) WOA18-Jan climatology (with bias note).

## 7. References

- Good, Martin, Rayner (2013), _JGR Oceans_ — EN4 method.
- https://www.metoffice.gov.uk/hadobs/en4/ and en4/download-en4-2-2.html
- Non-Commercial Government Licence v2.
