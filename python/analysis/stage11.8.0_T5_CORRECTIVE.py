#!/usr/bin/env python3
"""T5-CORRECTIVE: configuration search, storm analysis, deliverables."""
import json, re
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

P=Path(__file__).resolve().parents[2]; V=P/"data/validation"

def metrics(run):
    p=V/f"{run}_metrics.json"
    if p.exists():
        return json.loads(p.read_text())["runs"][run]
    return None

def first_nan(m):
    for r in m["daily"]:
        if r["nan"]>0:
            return r["day"]
    return None

def result(run, label, dt, ah, fpe=None):
    m=metrics(run)
    if m is None: return None
    daily=m["daily"]; n=first_nan(m)
    def at(day):
        return daily[day] if day <= m["days_completed"] else None
    ke30=at(30); ke60=at(60); ke90=at(90)
    out={"run":run,"label":label,"dt_s":dt,"Ah_m2_s":ah,
         "days_completed":m["days_completed"],"first_nan_day":n,
         "max_u_m_s":m["max_u_over_run"],"max_v_m_s":m["max_v_over_run"],
         "ke30_j":ke30["ke"] if ke30 else None,"ke60_j":ke60["ke"] if ke60 else None,
         "ke90_j":ke90["ke"] if ke90 else None,
         "ke60_over_ke30":(ke60["ke"]/ke30["ke"]) if (ke60 and ke30) else None,
         "ke90_over_ke60":(ke90["ke"]/ke60["ke"]) if (ke90 and ke60) else None,
         "fpe_after_day":fpe}
    out["PASS"]=bool(m["days_completed"]>=90 and n is None and out["max_u_m_s"]<5.0
                     and out["ke90_over_ke60"] is not None and out["ke90_over_ke60"]<5.0)
    return out

def storm():
    p=P/"data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc"
    with Dataset(p) as d:
        u=np.array(d["u10"][:],dtype=np.float64); v=np.array(d["v10"][:],dtype=np.float64)
        t=np.array(d["valid_time"][:],dtype=np.int64)
    ws=np.hypot(u,v); mx=np.nanmax(ws,axis=(1,2)); im=int(np.argmax(mx))
    date=str(np.datetime64(int(t[im]),'s'))
    # model response from config3 around the storm
    m=metrics("t5c_config3"); daily=m["daily"]
    resp=[]
    for day in range(65,73):
        if day<=m["days_completed"]:
            r=daily[day]; resp.append({"day":day,"max_u_m_s":r["umax"],"max_v_m_s":r["vmax"],
                                       "ke_j":r["ke"],"nan_cells":r["nan"]})
    # max model wind stress near storm
    d=nc_model_day("t5c_config3",69)
    tau=np.hypot(d["tau_x"],d["tau_y"])
    return {"storm_peak_utc":date,"max_wind_speed_m_s":float(mx[im]),
            "max_u10_m_s":float(np.nanmax(np.abs(u[im]))),"max_v10_m_s":float(np.nanmax(np.abs(v[im]))),
            "model_tau_max_pa_day69":float(np.nanmax(tau)),
            "model_response_days_65_72":resp,
            "storm_trigger":"March 2020 Q1 wind maximum; day 69-70 in model"}

def nc_model_day(run,day):
    with Dataset(P/f"data/runs/{run}/output/nc/results_day_{day:02d}.nc") as d:
        return {k:np.array(d[k][:],dtype=np.float64) for k in ["tau_x","tau_y"]}

def main():
    rows=[result("t5c_config1","config1",900,20000,fpe=64),
          result("t5c_config2","config2",900,30000),
          result("t5c_config3","config3",600,30000),
          result("t5c_config4","config4 (exploratory)",600,50000)]
    rows=[r for r in rows if r]
    for r in rows:
        (V/f"{r['run']}_results.json").write_text(json.dumps(r,indent=2))
    st=storm()
    (V/"t5c_storm_analysis.json").write_text(json.dumps(st,indent=2))
    # April baseline from T5 (no configuration passed, so this is the seasonal reference)
    apr=json.loads((V/"t5_april_results.json").read_text())
    (V/"t5c_april_results.json").write_text(json.dumps({
        "note":"No 90-day configuration passed; April 30-day below is the T5 baseline (dt=1800, Ah=10000), retained as seasonal reference.",
        "configuration":"baseline T5","result":apr},indent=2))
    summary={"stage":"11.8.0 T5-CORRECTIVE","configs":rows,"chosen":None,
             "PASS":False,"storm":st["storm_peak_utc"],
             "reason":"All prescribed configs fail: config1 FPE after day63; config2/3/4 NaN by day68-70; max |U| >>5 m/s.",
             "T6":"NO-GO","next":"T5-CORRECTIVE-2"}
    (V/"t5c_summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2,default=float))

if __name__=="__main__": main()
