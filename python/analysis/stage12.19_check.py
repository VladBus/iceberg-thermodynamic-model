#!/usr/bin/env python3
"""Stage 12.19 checks on the fixed FJL2 2020 control run."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from scipy.ndimage import label, generate_binary_structure


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=Path, default=Path("data/validation/stage12.19/FJL2_2020_fixed"))
    a = p.parse_args()
    d = a.run_dir
    out = {}
    with xr.open_dataset(d/"run.nc") as ds:
        t = ds.time.values/86400.0; m = ds.mass.values; m0 = m[0]
        draft = ds.draft.values
        b = float(ds.voxel_mass_loss_basal[-1]); l = float(ds.voxel_mass_loss_lateral[-1])
        s = float(ds.voxel_mass_loss_surface[-1]); fl = float(ds.voxel_mass_loss_flush[-1])
        ca = float(ds.calved_mass[-1]) if "calved_mass" in ds else 0.0
        out["days"] = float(t[-1]); out["mass_loss_pct"] = float(100*(1-m[-1]/m0))
        b0 = float(ds.voxel_mass_loss_basal[0]); l0 = float(ds.voxel_mass_loss_lateral[0])
        s0 = float(ds.voxel_mass_loss_surface[0]); fl0 = float(ds.voxel_mass_loss_flush[0])
        ca0 = float(ds.calved_mass[0]) if "calved_mass" in ds else 0.0
        out["mass_balance_residual_kg"] = float((m0-m[-1]) - ((b-b0)+(l-l0)+(s-s0)+(fl-fl0)+(ca-ca0)))
        out["mass_balance_residual_rel"] = out["mass_balance_residual_kg"]/m0
        out["calved_mass_kg"] = ca
        out["calved_events"] = int(ds.calved_events[-1]) if "calved_events" in ds else 0
        win = (t >= 239.0) & (t <= 243.0)
        out["max_draft_jump_239_243_m"] = float(np.max(np.abs(np.diff(draft[win])))) if win.sum() > 2 else None
    for day in (270, 365):
        f = d/f"run.nc_snap_{day:03d}.nc"
        if not f.exists(): continue
        with xr.open_dataset(f) as ds:
            phi = np.asarray(ds.phi.values, float)
        _, n = label(phi > 1e-12, structure=generate_binary_structure(3,1))
        out[f"components_day_{day}"] = int(n)
    # first snapshot mass fraction
    f0 = d/"run.nc_snap_000.nc"
    if f0.exists():
        with xr.open_dataset(f0) as ds: out["first_snapshot_mass_pct"] = float(100*ds.mass.values[0]/m0)
    # energy CSV
    ef = d/"run.nc_energy.csv"
    if ef.exists():
        e = pd.read_csv(ef)
        out["energy_residual_final_pct_latent"] = float(e["residual_pct_latent"].iloc[-1])
        out["energy_residual_max_abs_pct_latent"] = float(e["residual_pct_latent"].abs().max())
        out["energy_calved_final_J"] = float(e["calved_energy_J"].iloc[-1])
        out["mass_residual_final_kg"] = float(e["mass_residual_kg"].iloc[-1])
    print(json.dumps(out, indent=2))
    (d/"stage12.19_check.json").write_text(json.dumps(out, indent=2)+"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
