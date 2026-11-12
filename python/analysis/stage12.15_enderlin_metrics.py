#!/usr/bin/env python3
"""Stage 12.15: Enderlin current-code metrics, strata and scatter."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

def metrics(df):
    obs=df.observed_melt_rate.to_numpy(float); mod=df.modeled_melt_rate_voxel.to_numpy(float)
    ok=np.isfinite(obs)&np.isfinite(mod)&(obs>0)
    if ok.sum()==0: return {"n":0}
    r=mod[ok]/obs[ok]
    return {"n":int(ok.sum()),"median_ratio":float(np.median(r)),"mean_ratio":float(np.mean(r)),
            "spearman":float(stats.spearmanr(mod[ok],obs[ok]).statistic),
            "mae_m_per_day":float(np.mean(np.abs(mod[ok]-obs[ok]))),
            "rmse_m_per_day":float(np.sqrt(np.mean((mod[ok]-obs[ok])**2))),
            "bias_m_per_day":float(np.mean(mod[ok]-obs[ok])),
            "median_observed":float(np.median(obs[ok])),"median_modeled":float(np.median(mod[ok]))}

def main():
    p=argparse.ArgumentParser(); p.add_argument("results"); p.add_argument("manifest"); p.add_argument("--out",type=Path,required=True); p.add_argument("--figure",type=Path,required=True); a=p.parse_args()
    df=pd.read_csv(a.results); man=pd.read_csv(a.manifest)
    d=df.merge(man[["case_id","surface_area","draft"]],on="case_id",how="left")
    d["size_m"]=np.sqrt(d.surface_area)
    d["size_bin"]=pd.cut(d.size_m,[0,100,300,1e9],labels=["<=100 m","100-300 m",">300 m"])
    d["depth_bin"]=pd.cut(d.draft,[0,100,300,1e9],labels=["<=100 m","100-300 m",">300 m"])
    total=d.mass_loss_basal_voxel+d.mass_loss_lateral_voxel+d.mass_loss_surface_voxel+d.mass_loss_wave_voxel
    d["f_basal"]=d.mass_loss_basal_voxel/total.replace(0,np.nan)
    d["f_lateral"]=d.mass_loss_lateral_voxel/total.replace(0,np.nan)
    d["f_surface"]=d.mass_loss_surface_voxel/total.replace(0,np.nan)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name,g in [("overall",d),("size",None),("depth",None)]:
        if g is not None: rows.append({"stratum":"overall",**metrics(g),"f_basal":float(g.f_basal.median()),"f_lateral":float(g.f_lateral.median()),"f_surface":float(g.f_surface.median())})
    for by in ["size_bin","depth_bin"]:
        for k,g in d.groupby(by,observed=True):
            rows.append({"stratum":f"{by}:{k}",**metrics(g),"f_basal":float(g.f_basal.median()),"f_lateral":float(g.f_lateral.median()),"f_surface":float(g.f_surface.median())})
    pd.DataFrame(rows).to_csv(a.out,index=False)
    fig,ax=plt.subplots(figsize=(6.5,5.5))
    ax.scatter(d.observed_melt_rate,d.modeled_melt_rate_voxel,s=14,alpha=.65)
    lim=[max(1e-3,min(d.observed_melt_rate.min(),d.modeled_melt_rate_voxel.min())*.7),max(d.observed_melt_rate.max(),d.modeled_melt_rate_voxel.max())*1.4]
    ax.plot(lim,lim,'k--',lw=1,label='1:1')
    ax.plot(lim,[2*x for x in lim],'k:',lw=.8,label='factor 2')
    ax.plot(lim,[.5*x for x in lim],'k:',lw=.8)
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel('observed submarine melt [m/day]'); ax.set_ylabel('current voxel melt [m/day]')
    ax.set_title('Enderlin23 current code (n=190)'); ax.grid(alpha=.25); ax.legend()
    a.figure.parent.mkdir(parents=True,exist_ok=True); fig.tight_layout(); fig.savefig(a.figure,dpi=180); plt.close(fig)
    print(pd.DataFrame(rows).to_string(index=False)); return 0
if __name__=="__main__": raise SystemExit(main())
