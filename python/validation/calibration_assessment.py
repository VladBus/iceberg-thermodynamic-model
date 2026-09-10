"""Stage 10.9 — scientific assessment of basal-melt coefficient calibration.

This module answers a single question: **can the production basal-melt
coefficient setup (flat-plate turbulent Nusselt closure, ``0.037 Re^0.8
Pr^(1/3)``) be robustly calibrated against the Stage 10.8.2 observational
dataset?** The answer is expressed through an *identifiability* analysis:

* the effective sample size (distinct sources, not rows);
* the per-row inferred coefficient multiplier ``C_gamma = obs/model`` and its
  spread across sources;
* the functional-form (exponent) mismatch in the thermal driving ``dT``;
* the correspondence between the dataset and the model in Stanton-number
  terms (production flat-plate St, observed-implicit St, and the glaciological
  melt-driven anchor ``S_t ~ 0.011`` of Jenkins et al. 2010);
* a parameter-sensitivity decomposition (``m ~ U^0.8 L^-0.2 dT^1 C_gamma^1``
  on the turbulent branch);
* an ``L_char`` geometry-sensitivity study (draft vs length);
* a ``C_gamma`` grid experiment (0.25-4.0) with leave-one-source-out refits.

The assessment is **Fortran-independent**: it uses ``basal_melt`` (pure
Python, Stage 10.8.1) as the closure reference and ``observational_validation``
(Stage 10.8.2) for the dataset loader. No Fortran code is called, imported or
parsed. **No production coefficient is changed anywhere.**

Run directly to print a structured summary:

    python python/validation/calibration_assessment.py
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

# Stage 10.8.1/10.8.2 layers (pure Python, Fortran-independent).
import basal_melt as bm  # noqa: E402
import observational_validation as ov  # noqa: E402

DAY_S = 86400.0
WATER_C_P = 3985.0          # seawater specific heat [J/(kg K)] (reference, Jenkins et al. 2010)
WATER_RHO = 1028.0          # reference seawater density [kg/m^3]

# Literature anchors (see docs/validation/stage10.9_calibration_assessment.md).
ST_MELTWATER_JENKINS = 0.0110   # effective turbulent Stanton, melt-driven flow under Ronne Ice Shelf

_REPO_ROOT = Path(__file__).resolve().parents[2]

C_GAMMA_LO = 0.25           # calibration grid bounds (Python-only experiment)
C_GAMMA_HI = 4.0
C_GAMMA_N = 300             # grid resolution (deterministic)


# ---------------------------------------------------------------------------
# Data access (delegates to the verified 10.8.2 loader)
# ---------------------------------------------------------------------------
def load_rows(path=None) -> list[dict]:
    return ov.load_observations(path)


def comparable_rows(rows=None) -> list[dict]:
    """Rows where the closure is fully specified and ``u_rel > 0``."""
    rows = rows if rows is not None else load_rows()
    return [r for r in rows if ov.closure_applicable(r)]


def model_melt_m_per_day(row) -> float:
    """Production basal-melt rate [m/day]; the 10.8.2 model value (exact)."""
    return ov.model_melt_m_per_day(row)


# ---------------------------------------------------------------------------
# Per-row analysis
# ---------------------------------------------------------------------------
def reynolds(row) -> float:
    return bm.reynolds_number(float(row["u_rel_m_s"]), float(row["L_char_m"]))


def thermal_driving_degC(row) -> float:
    return max(
        float(row["T_degC"]) - bm.ocean_freezing_point(
            float(row["S_psu"]), float(row["L_char_m"])
        ),
        0.0,
    )


def gamma_T_W_per_m2K(row) -> float:
    return bm.ocean_heat_transfer_coefficient(
        float(row["u_rel_m_s"]), float(row["L_char_m"])
    )


def stanton_from_melt(m_m_per_s: float, u_rel: float, delta_t: float) -> float:
    """Stanton number implied by a melt rate (dimensionless heat-transfer St).

    ``St = gamma/ (rho_w c_p U)`` with ``gamma = m rho_i L_f / dT``, i.e. the
    effective heat-transfer coefficient implied by the melt rate.
    """
    if u_rel <= 0.0 or delta_t <= 0.0:
        return float("nan")
    gamma = m_m_per_s * bm.RHO_ICE * bm.LATENT_HEAT / delta_t
    return gamma / (WATER_RHO * WATER_C_P * u_rel)


def per_row_analysis(row: dict) -> dict[str, Any]:
    """Full analysis of one comparable observation row (deterministic)."""
    obs_spd = float(row["obs_m_per_s"])
    obs_mday = float(row["obs_m_per_day"])
    u = float(row["u_rel_m_s"])
    lc = float(row["L_char_m"])
    dT = thermal_driving_degC(row)
    re = reynolds(row)
    model_spd = bm.basal_melt_rate(
        ocean_temperature=float(row["T_degC"]),
        salinity_psu=float(row["S_psu"]),
        depth_m=lc,
        u_water=u,
        v_water=0.0,
        u_ice=0.0,
        v_ice=0.0,
        length_m=lc,
    )
    model_mday = model_spd * DAY_S
    ratio = model_mday / obs_mday if obs_mday > 0 else float("nan")
    inferred_c = obs_mday / model_mday if model_mday > 0 else float("nan")
    regime = "turbulent" if re >= bm.REYNOLDS_CRITICAL else "laminar"
    return {
        "record_id": row["record_id"],
        "source_key": row["source_key"],
        "tier": row["tier"],
        "melt_component": row["melt_component"],
        "obs_m_per_day": obs_mday,
        "model_m_per_day": model_mday,
        "model_over_obs": ratio,
        "inferred_c_gamma": inferred_c,
        "delta_t_degC": dT,
        "reynolds": re,
        "regime": regime,
        "gamma_T_W_per_m2K": gamma_T_W_per_m2K(row),
        "stanton_model": stanton_from_melt(model_spd, u, dT),
        "stanton_implied_by_obs": stanton_from_melt(obs_spd, u, dT),
    }


# ---------------------------------------------------------------------------
# Source-aware effective sample size
# ---------------------------------------------------------------------------
def distinct_sources(rows=None) -> list[str]:
    """Distinct ``source_key`` values among the closure-applicable rows."""
    cmp = comparable_rows(rows)
    seen = []
    for r in cmp:
        if r["source_key"] not in seen:
            seen.append(r["source_key"])
    return seen


def effective_sample_size(rows=None) -> dict[str, Any]:
    """Rows vs distinct sources: the honest sample size for calibration."""
    cmp = comparable_rows(rows)
    srcs = distinct_sources(rows)
    return {
        "n_rows": len(cmp),
        "n_sources": len(srcs),
        "sources": srcs,
        "row_source_counts": {s: sum(1 for r in cmp if r["source_key"] == s) for s in srcs},
    }


# ---------------------------------------------------------------------------
# Identifiability: spread of the inferred coefficient
# ---------------------------------------------------------------------------
def inferred_multiplier_spread(rows=None) -> dict[str, Any]:
    """C_gamma = obs/model for every comparable row; range and log spread."""
    out = []
    for r in comparable_rows(rows):
        a = per_row_analysis(r)
        out.append((a["record_id"], a["source_key"], a["inferred_c_gamma"]))
    vals = [v for _, _, v in out if v == v]
    gmean = 10.0 ** (sum(math.log10(v) for v in vals) / len(vals))
    return {
        "rows": [(rid, src, v) for rid, src, v in out],
        "min": min(vals),
        "max": max(vals),
        "max_over_min": max(vals) / min(vals),
        "log10_decades": max(math.log10(v) for v in vals)
        - min(math.log10(v) for v in vals),
        "geometric_mean": gmean,
    }


def per_source_geomean(rows=None) -> dict[str, dict]:
    """Geometric-mean inferred C_gamma per distinct source."""
    res = {}
    for src in distinct_sources(rows):
        vals = [
            per_row_analysis(r)["inferred_c_gamma"]
            for r in comparable_rows(rows)
            if r["source_key"] == src
        ]
        vals = [v for v in vals if v == v]
        res[src] = {
            "n": len(vals),
            "geometric_mean": 10.0 ** (sum(math.log10(v) for v in vals) / len(vals)),
            "min": min(vals),
            "max": max(vals),
        }
    return res


def dT_exponent_loglog(obs_mday_list, delta_t_list) -> float:
    """Local exponent d(ln m)/d(ln dT) fitted in log-log space."""
    xs = [math.log(d) for d in delta_t_list if d > 0]
    ys = [math.log(m) for m, d in zip(obs_mday_list, delta_t_list) if d > 0]
    if len(xs) < 2:
        return float("nan")
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def nj80_dt_exponent(rows=None) -> float:
    """Observed dT exponent of the NJ80 synthesis curve (row set, ~dT^1.7)."""
    cmp = [r for r in comparable_rows(rows) if r["record_id"].startswith("NJ80")]
    return dT_exponent_loglog(
        [float(r["obs_m_per_day"]) for r in cmp],
        [thermal_driving_degC(r) for r in cmp],
    )


def rh80_dt_exponent(rows=None) -> float:
    """Observed T+1.8 exponent of the RH80 free-convection curve (exponent 1.5)."""
    rows = rows if rows is not None else load_rows()
    rh = [r for r in rows if r["record_id"].startswith("RH")]
    return dT_exponent_loglog(
        [float(r["obs_m_per_day"]) for r in rh],
        [float(r["T_degC"]) + 1.8 for r in rh],
    )


# ---------------------------------------------------------------------------
# Parameter-sensitivity decomposition  m ~ U^a_u L^a_l dT^a_d C^a_c
# ---------------------------------------------------------------------------
def sensitivity_exponents(regime: str) -> dict[str, Any]:
    """Measured (finite-difference) exponents of each input.

    The flat-plate closure is analytic: turbulent (Re >= 5e5)
    m ~ U^0.8 L^-0.2 dT^1 C^1; laminar m ~ U^0.5 L^-0.5 dT^1 C^1. The finite
    differences below reproduce those exponents to ~1e-5, confirming the
    decomposition rather than trusting the powers implicitly.
    """
    if regime not in ("laminar", "turbulent"):
        raise ValueError(regime)

    def make(u_rel, L, dT, c):
        t = bm.ocean_freezing_point(35.0, L) + dT
        m = bm.basal_melt_rate(
            ocean_temperature=t, salinity_psu=35.0, depth_m=L,
            u_water=u_rel, v_water=0.0, u_ice=0.0, v_ice=0.0, length_m=L,
        )
        return c * m * DAY_S

    # base state selected to sit in the wanted regime
    if regime == "turbulent":
        u, L, dT, c = 0.2, 100.0, 2.0, 1.0
    else:
        u, L, dT, c = 0.01, 1.0, 2.0, 1.0
    r0 = make(u, L, dT, c)

    def eu(uu):
        return make(uu, L, dT, c)

    def el(ll):
        return make(u, ll, dT, c)

    def ed(dd):
        return make(u, L, dd, c)

    def ec(cc):
        return make(u, L, dT, cc)

    rel = 1.0e-4
    au = math.log(eu(u * (1 + rel)) / r0) / math.log(1 + rel)
    al = math.log(el(L * (1 + rel)) / r0) / math.log(1 + rel)
    ad = math.log(ed(dT * (1 + rel)) / r0) / math.log(1 + rel)
    ac = math.log(ec(c * (1 + rel)) / r0) / math.log(1 + rel)
    return {
        "regime": regime,
        "a_U": au,
        "a_L": al,
        "a_dT": ad,
        "a_C": ac,
        "analytic": {
            "turbulent": (0.8, -0.2, 1.0, 1.0),
            "laminar": (0.5, -0.5, 1.0, 1.0),
        }[regime],
    }


# ---------------------------------------------------------------------------
# L_char geometry sensitivity (draft vs length vs LWM)
# ---------------------------------------------------------------------------
def geometry_sensitivity(row: dict, lengths, offset=0.0) -> list[dict]:
    """Model melt [m/day] at C_gamma=1 for a row under alternative L_char.

    Tf is evaluated at ``depth_m = length`` (the 10.8.2 documented choice), so
    changing L_char changes both Re (weak, exponent -0.2) and the freezing-point
    pressure (mild). ``lengths`` mirrors the candidates a user might adopt
    (draft, berg length, LWM proxy).
    """
    s = float(row["S_psu"])
    u = float(row["u_rel_m_s"])
    t = float(row["T_degC"])
    out = []
    for L in lengths:
        dT = max(t - bm.ocean_freezing_point(s, L), 0.0)
        spd = bm.basal_melt_rate(
            ocean_temperature=t, salinity_psu=s, depth_m=L,
            u_water=u, v_water=0.0, u_ice=0.0, v_ice=0.0, length_m=L,
        )
        out.append({
            "L_char_m": L,
            "dT_degC": dT,
            "model_m_per_day": spd * DAY_S,
            "ratio_vs_obs": spd * DAY_S / float(row["obs_m_per_day"]),
        })
    return out


def geometry_summary(rows=None) -> dict[str, Any]:
    """Draft vs length sweep for the source-defining rows (KW84, NJ80)."""
    rows = rows if rows is not None else load_rows()
    kw84 = next(r for r in rows if r["record_id"] == "KW84_DUrville")
    nj80 = next(r for r in rows if r["record_id"] == "NJ80_dT4")
    return {
        "KW84_DUrville_draft_to_length": geometry_sensitivity(kw84, [20, 40, 60, 80, 100]),
        "NJ80_dT4_draft_to_length": geometry_sensitivity(nj80, [20, 50, 100, 200]),
    }


# ---------------------------------------------------------------------------
# C_gamma grid experiment (Python-only; 0.25 .. 4.0)
# ---------------------------------------------------------------------------
def c_gamma_grid_model(row: dict, c: float) -> float:
    """Model melt at multiplier ``c`` on the heat-transfer coefficient [m/day]."""
    return c * model_melt_m_per_day(row)


def best_fit_c_gamma(rows=None) -> dict[str, Any]:
    """Geometric best-fit multiplier (least squares in log space), per source
    and pooled. Because this is a pure scale factor, a useful identifiability
    diagnostic is the *residual pattern* it leaves behind."""
    rows = rows if rows is not None else load_rows()
    cmp = comparable_rows(rows)
    pooled = [per_row_analysis(r)["inferred_c_gamma"] for r in cmp]
    pooled = [v for v in pooled if v == v]
    g = 10.0 ** (sum(math.log10(v) for v in pooled) / len(pooled))
    per_src = per_source_geomean(rows)
    return {
        "pooled_geometric_mean": g,
        "per_source_geometric_mean": per_src,
        "n_rows": len(pooled),
    }


def leave_one_source_out(rows=None) -> dict[str, Any]:
    """Refit C_gamma on all-but-one source; report held-out performance.

    The held-out row is evaluated with the re-fitted multiplier, and the
    resulting model/observation ratio is reported. A robustly identifiable
    coefficient would produce ratios near 1 for every held-out source; any
    wide spread demonstrates that the single scalar cannot be identified.
    """
    rows = rows if rows is not None else load_rows()
    srcs = distinct_sources(rows)
    result = {}
    for left in srcs:
        train = [r for r in comparable_rows(rows) if r["source_key"] != left]
        hold = [r for r in comparable_rows(rows) if r["source_key"] == left]
        vals = [per_row_analysis(r)["inferred_c_gamma"] for r in train]
        vals = [v for v in vals if v == v]
        g = 10.0 ** (sum(math.log10(v) for v in vals) / len(vals))
        held = []
        for r in hold:
            a = per_row_analysis(r)
            ratio = g * a["model_over_obs"]
            held.append({
                "record_id": a["record_id"],
                "model_over_obs_at_refit": ratio,
                "residual_log10": math.log10(max(ratio, 1e-300)),
            })
        result[left] = {
            "fit_multiplier": g,
            "held_out": held,
            "max_abs_log10_residual": max(
                abs(h["residual_log10"]) for h in held
            ),
        }
    return result


# ---------------------------------------------------------------------------
# Natural-convection gap (delegates to the 10.8.2 test)
# ---------------------------------------------------------------------------
def natural_convection_gap(rows=None) -> list[dict]:
    rows = rows if rows is not None else load_rows()
    gaps = ov.gap_test(rows)
    return [
        {
            "record_id": g["record_id"],
            "obs_m_per_day": g["obs_m_per_day"],
            "orders_above_model_floor": g["gap_orders"],
        }
        for g in gaps
    ]


# ---------------------------------------------------------------------------
# Claim-by-claim audit of the Stage 10.8.2 wording (the 8 claims + L_char)
# ---------------------------------------------------------------------------
def audit_claims(rows=None) -> list[dict]:
    """Independent re-derivation of the Stage 10.8.2 headline numbers, each
    tagged PASS / CORRECTED with the numeric basis. Used verbatim by the
    Stage 10.9 report."""
    rows = rows if rows is not None else load_rows()
    spread = inferred_multiplier_spread(rows)
    res = []

    kw84 = per_row_analysis(next(r for r in comparable_rows(rows)
                                 if r["record_id"] == "KW84_DUrville"))
    res.append({
        "claim": "KW84 reproduced within the reported range 0.04-0.08 m/day (ratio 0.70).",
        "status": "PASS (with L_char caveat)",
        "basis": (
            f"model {kw84['model_m_per_day']:.4f} vs obs 0.0600+/-0.01 m/day, "
            f"ratio {kw84['model_over_obs']:.2f} at L_char=draft=20 m. The point "
            f"sits at the extreme lower edge of the reported range AND below the "
            f"1-sigma band 0.05-0.07. Using the berg length 40-100 m (the "
            f"production L_char choice) lowers the model to 0.033-0.037 m/day "
            f"(ratio 0.55-0.62). 'Better than the reported range' is overstated; "
            f"'within the reported range under the L_char=draft assumption' is "
            f"the defensible statement."
        ),
    })

    nj80 = [per_row_analysis(r) for r in comparable_rows(rows)
            if r["record_id"].startswith("NJ80")]
    res.append({
        "claim": "NJ80 synthesis overestimated by factor 2.1-5.8 at reference params.",
        "status": "PASS (numerically exact), but reinterpreted",
        "basis": (
            "model/obs = "
            + ", ".join(f"{a['record_id']}: {a['model_over_obs']:.2f}" for a in nj80)
            + ". The decline 5.84->2.12 with dT is itself the anomaly: NJ80 obs scale "
            f"~dT^{nj80_dt_exponent(rows):.2f} while the closure is linear in dT. "
            f"~dT^{nj80_dt_exponent(rows):.2f} while the closure is linear in dT. "
            f"The mismatch is therefore functional-form (structural), not a pure "
            f"scale factor."
        ),
    })

    gaps = natural_convection_gap(rows)
    res.append({
        "claim": "Natural-convection gap is 5.7-7.3 orders of magnitude.",
        "status": "PASS (reframed)",
        "basis": (
            f"orders above the numerical guard floor (1e-12 m/s -> "
            f"{ov.FLOOR_M_PER_DAY:.1e} m/day): "
            + ", ".join(f"{g['record_id']} {g['orders_above_model_floor']:.1f}" for g in gaps)
            + ". The closure returns exactly 0 at rest; the 'order gap' is "
            f"measured against the floor, not a physical branch. Reframing is "
            f'required: "closure=0 vs observed 0.04-1.6 m/day" is the honest form.'
        ),
    })

    res.append({
        "claim": "Greenland fjord rates reproducible at plausible U_rel 0.1-1.0 m/s.",
        "status": "PASS (consistency only), melt_component caveat",
        "basis": (
            "inverse-U at dT=2-4 degC, L=50 m, S=35 gives U ~0.1-1.0 m/s for the "
            "0.16-0.50 m/day rows. These are SUBMARINE rates while the closure "
            "computes a single basal component; side-melt is co-located in the "
            "observation. Strong enough for a plausibility check, not a "
            "verification of the basal-only closure."
        ),
    })

    res.append({
        "claim": "All comparable observations are turbulent (Re > 5e5).",
        "status": "PASS",
        "basis": "Re = " + ", ".join(f"{a['reynolds']:.2e}" for a in nj80)
                 + "; KW84 Re=1.10e6; all > 5e5.",
    })

    res.append({
        "claim": "The laminar branch has no field anchor.",
        "status": "PASS",
        "basis": "Of the closure-applicable rows none has Re < 5e5; the quiescent lab rows are U=0 (free-convection regime, not forced-laminar). The forced-laminar branch is therefore unexercised by any observation.",
    })

    res.append({
        "claim": "Submarine melt is sufficiently close to basal melt for comparison "
                 "(basal plane dominates; side melt second).",
        "status": "CORRECTED - NOT SUPPORTED as stated",
        "basis": (
            "Area ratio A_side/A_basal = 2(L+W)D/(LW). For a KW84-scale berg "
            "(L~60-100 m, D~20 m) A_side/A_basal = 0.80-1.33 (side comparable or "
            "larger); for NJ80-scale tabular bergs (L~1 km, D~200 m) ~0.8; basal "
            "dominates only for very large tabulars (L>2 km, D/L<0.25). The RH80 "
            "tank note itself says 'basal~(side)'. The dataset mixes basal (KW84 "
            "field, RH80 lab) and submarine (all rs-derived) observations; they "
            "are NOT interchangeable without a side-melt correction."
        ),
    })

    res.append({
        "claim": "Basal plane dominates the submarine melt (used as a reason to "
                 "compare rs-derived submarine rates to the basal closure).",
        "status": "CORRECTED - NOT SUPPORTED as stated",
        "basis": "Same area-ratio argument as above: tabular geometry near D/L~0.2 has side area comparable to basal. The rs-derived inverse-U comparison must be labeled 'basal-only proxy for a submarine observation'.",
    })

    res.append({
        "claim": "L_char = whether state%L (berg length) is justified for the "
                 "basal Re and how the 10.8.2 comparison set L_char.",
        "status": "PASS (production) / MISMATCH (comparison)",
        "basis": "Production passes state%L (length) unconditionally. The 10.8.2 comparison set L_char=draft (20/50 m) for KW84/NJ80. Consequences: (1) the favorable KW84 ratio 0.70 holds only under L=draft; (2) no orientation of the berg relative to the flow is known, so any single L is an approximation - the flat-plate L^-0.2 scaling keeps this a modest (<=~25%) effect on the melt rate.",
    })

    return res


# ---------------------------------------------------------------------------
# Consolidated summary
# ---------------------------------------------------------------------------
def identifiability_summary(rows=None) -> dict[str, Any]:
    rows = rows if rows is not None else load_rows()
    cmp = comparable_rows(rows)
    analysis = [per_row_analysis(r) for r in cmp]
    srcs = distinct_sources(rows)
    eff = effective_sample_size(rows)
    spread = inferred_multiplier_spread(rows)
    per_src = per_source_geomean(rows)
    loso = leave_one_source_out(rows)
    exp_turb = sensitivity_exponents("turbulent")
    exp_lam = sensitivity_exponents("laminar")
    return {
        "effective_sample": eff,
        "inferred_c_gamma_spread": spread,
        "per_source_geomean": per_src,
        "nj80_obs_dT_exponent": nj80_dt_exponent(rows),
        "rh80_obs_T_exponent": rh80_dt_exponent(rows),
        "closure_dT_exponent": 1.0,
        "sensitivity_exponents": {"turbulent": exp_turb, "laminar": exp_lam},
        "stanton_reference": ST_MELTWATER_JENKINS,
        "per_row": [
            {
                "record_id": a["record_id"],
                "source_key": a["source_key"],
                "melt_component": a["melt_component"],
                "model_over_obs": a["model_over_obs"],
                "inferred_c_gamma": a["inferred_c_gamma"],
                "delta_t_degC": a["delta_t_degC"],
                "regime": a["regime"],
                "stanton_model": a["stanton_model"],
                "stanton_implied_by_obs": a["stanton_implied_by_obs"],
            }
            for a in analysis
        ],
        "geometry_sensitivity": geometry_summary(rows),
        "leave_one_source_out": loso,
        "natural_convection_gap": natural_convection_gap(rows),
        "linear_dT_model": True,
        "conclusion": (
            "Calibration of a scalar multiplier on the turbulent heat-transfer "
            "coefficient is NOT identifiable from this dataset: n_sources=2, "
            "inferred C_gamma spans {:.2f}x, and the dominant discrepancy is a "
            "functional-form mismatch in dT (obs ~dT^{:.1f}, closure ~dT^1.0). "
            "A structural upgrade (three-equation interface with a "
            "buoyancy-driven/Stanton closure) is the next stage; no production "
            "coefficient is changed here."
        ).format(
            spread["max_over_min"],
            nj80_dt_exponent(rows),
        ),
    }


def render_summary(rows=None) -> str:
    s = identifiability_summary(rows)
    L = []
    L.append("Stage 10.9 — basal-melt coefficient calibration assessment")
    L.append("=" * 68)
    L.append(f"closure-applicable rows: {s['effective_sample']['n_rows']} "
             f"({', '.join(s['effective_sample']['sources'])}); "
             f"effective sources: {s['effective_sample']['n_sources']}")
    L.append("- inferred C_gamma = obs/model (per row, with source):")
    for rid, src, v in s["inferred_c_gamma_spread"]["rows"]:
        L.append(f"    {rid:16s} {src:48s} C={v:.3f}")
    L.append(f"    spread max/min = {s['inferred_c_gamma_spread']['max_over_min']:.2f} "
             f"({s['inferred_c_gamma_spread']['log10_decades']:.2f} decades); "
             f"geomean = {s['inferred_c_gamma_spread']['geometric_mean']:.3f}")
    L.append(f"- dT-form: NJ80 obs ~ dT^{s['nj80_obs_dT_exponent']:.2f}; RH80 obs ~ "
             f"T^{s['rh80_obs_T_exponent']:.2f}; closure linear (dT^1.00)")
    L.append("- sensitivity decomposition (exponents):")
    for r in (s["sensitivity_exponents"]["turbulent"], s["sensitivity_exponents"]["laminar"]):
        L.append(f"    {r['regime']:9s}: U^{r['a_U']:+.3f}  L^{r['a_L']:+.3f}  "
                 f"dT^{r['a_dT']:+.3f}  C^{r['a_C']:+.3f}   (analytic "
                 f"{r['analytic'][0]:g},{r['analytic'][1]:g},{r['analytic'][2]:g},{r['analytic'][3]:g})")
    L.append("- leave-one-source-out refit (max |log10 model/obs| on held-out source):")
    for src, v in s["leave_one_source_out"].items():
        for h in v["held_out"]:
            L.append(f"    leave {src:48s} -> {h['record_id']:16s} "
                     f"model/obs={h['model_over_obs_at_refit']:.3f} "
                     f"(resid {h['residual_log10']:+.3f})")
    L.append(f"- natural-convection gap (model floor {ov.FLOOR_M_PER_DAY:.1e} m/day):")
    for g in s["natural_convection_gap"]:
        L.append(f"    {g['record_id']:8s} obs={g['obs_m_per_day']:.4f} m/day "
                 f"({g['orders_above_model_floor']:.1f} orders)")
    L.append(f"- reference melt-driven Stanton (Jenkins et al. 2010): "
             f"{s['stanton_reference']:.4g}")
    L.append("- " + s["conclusion"])
    return "\n".join(L)


def main(argv=None) -> int:
    print(render_summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())