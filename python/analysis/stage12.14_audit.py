#!/usr/bin/env python3
"""Stage 12.14 post-processing: footprint and energy diagnostics.

Usage: python python/analysis/stage12.14_audit.py RUN.nc VOXEL.nc --outdir DIR
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import xarray as xr

RHO_ICE = 916.7
LF = 3.34e5


def nearest_time(times, t):
    return int(np.argmin(np.abs(times - t)))


def waterline_area(vox, snap=-1):
    phi = np.asarray(vox["phi"].isel(snapshot=snap).values)
    x = np.asarray(vox["x"].values); y = np.asarray(vox["y"].values); z = np.asarray(vox["z"].values)
    dx = float(x[1] - x[0]) if len(x) > 1 else 1.0
    dy = float(y[1] - y[0]) if len(y) > 1 else 1.0
    draft = float(vox["draft"].isel(snapshot=snap).values)
    solid = phi > 1e-2
    if not solid.any():
        return 0.0
    kb = int(np.argmax(solid.any(axis=(1, 2))))
    z_bottom = z[kb] - 0.5 * (z[1] - z[0]) if len(z) > 1 else z[kb] - 0.5
    z_wl = z_bottom + draft
    k = int(np.floor((z_wl - (z[0] - 0.5 * (z[1] - z[0]))) / (z[1] - z[0]))) if len(z) > 1 else kb
    k = min(max(k, 0), phi.shape[0] - 1)
    return float(solid[k].sum() * dx * dy)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_nc")
    p.add_argument("voxel_nc")
    p.add_argument("--outdir", required=True)
    a = p.parse_args()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    run = xr.open_dataset(a.run_nc); vox = xr.open_dataset(a.voxel_nc)
    try:
        prism_H = run["prism_draft"].values + run["prism_freeboard"].values
        prism_fp = np.divide(run["prism_volume"].values, prism_H,
                             out=np.zeros_like(prism_H), where=prism_H > 0)
        vt = vox.time.values
        rows = []
        for s in range(vox.sizes["snapshot"]):
            t = float(vt[s])
            i = nearest_time(run.time.values, t)
            vfp = waterline_area(vox, s)
            pfp = float(prism_fp[i])
            rows.append({"snapshot": s, "time_s": t, "prism_footprint_m2": pfp,
                         "voxel_waterline_m2": vfp, "abs_diff_m2": abs(pfp - vfp),
                         "rel_diff": abs(pfp - vfp) / max(vfp, 1e-30)})
        # Energy components: sensible + latent + flushed energy; boundary flux is
        # not accumulated by the present model, so this is an implied boundary.
        e0 = float(run["sensible_energy"].values[0]); e1 = float(run["sensible_energy"].values[-1])
        m0 = float(run["mass"].values[0]); m1 = float(run["mass"].values[-1])
        flush = float(run["flushed_energy"].values[-1])
        flush_mass = float(run["voxel_mass_loss_flush"].values[-1]) if "voxel_mass_loss_flush" in run else 0.0
        latent = LF * max(m0 - m1 - flush_mass, 0.0)
        implied_boundary = (e1 - e0) + latent + flush
        summary = {
            "footprint": rows,
            "energy": {
                "sensible_initial_J": e0, "sensible_final_J": e1,
                "sensible_change_J": e1 - e0,
                "mass_initial_kg": m0, "mass_final_kg": m1,
                "mass_loss_kg": m0 - m1,
                "flushed_mass_kg": flush_mass,
                "flushed_energy_J": flush,
                "latent_melt_J": latent,
                "implied_boundary_energy_J": implied_boundary,
                "initial_latent_equivalent_J": LF * m0,
                "implied_boundary_percent_initial_latent": 100.0 * implied_boundary / (LF * m0) if m0 else 0.0,
                "closure": "NOT_INDEPENDENT: no accumulated boundary heat flux in the model output",
            },
        }
        (out / "audit.json").write_text(json.dumps(summary, indent=2) + "\n")
        with open(out / "footprint.csv", "w") as f:
            f.write("snapshot,time_s,prism_footprint_m2,voxel_waterline_m2,abs_diff_m2,rel_diff\n")
            for r in rows:
                f.write(f"{r['snapshot']},{r['time_s']:.1f},{r['prism_footprint_m2']:.6f},"
                        f"{r['voxel_waterline_m2']:.6f},{r['abs_diff_m2']:.6f},{r['rel_diff']:.6e}\n")
        print(json.dumps(summary["energy"], indent=2))
        print(json.dumps(rows, indent=2))
    finally:
        run.close(); vox.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
