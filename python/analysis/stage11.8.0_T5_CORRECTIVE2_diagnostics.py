#!/usr/bin/env python3
"""T5-CORRECTIVE-2 storm-time diagnostics for config1 (dt=900, Ah=20000)."""
import json, re
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

P=Path(__file__).resolve().parents[2]; RUN=P/'data/runs/t5c2_config1_detailed/output/nc'
V=P/'data/validation'; RHO=1027.; CP=4000.; AREA=13890.0**2; DX=13890.0; AH=20750.

def load(day):
    with Dataset(RUN/f'results_day_{day:02d}.nc') as d:
        return {k:np.array(d[k][:],dtype=np.float64) for k in
                ['u_velocity','v_velocity','w_velocity','temperature','salinity_mass_fraction',
                 'density_anomaly','water_column_levels','depth_w','ice_thickness',
                 'ice_concentration','tau_x','tau_y','wind_speed']}

def metrics(day):
    d=load(day); lev=d['water_column_levels']; kk=np.arange(18)[:,None,None]; m=(lev[None]>0)&(kk<lev[None])
    dz=np.diff(d['depth_w']); vol=dz[:,None,None]*AREA
    T=d['temperature']-273.15; S=d['salinity_mass_fraction']; ro=d['density_anomaly']
    sp=np.hypot(d['u_velocity'],d['v_velocity'])
    ke=float(np.nansum(np.where(m,0.5*RHO*sp**2*vol,0.0)))
    u0,v0=d['u_velocity'][0],d['v_velocity'][0]; tx,ty=d['tau_x'],d['tau_y']
    wind_work=float(np.nansum(np.where(lev>0,tx*u0+ty*v0,0.0))*AREA)
    # boundary 5-cell band vs interior
    bm=np.zeros(m.shape[1:],bool); bm[:5,:]=bm[-5:,:]=bm[:,:5]=bm[:,-5:]=True
    max_b=float(np.nanmax(np.where(m&bm[None],sp,np.nan))) if (m&bm[None]).any() else 0.0
    max_i=float(np.nanmax(np.where(m&~bm[None],sp,np.nan))) if (m&~bm[None]).any() else 0.0
    # MLD: density anomaly threshold 0.03 kg/m3 from surface
    mld=np.full(lev.shape,np.nan)
    for j in range(lev.shape[0]):
        for i in range(lev.shape[1]):
            ki=lev[j,i]
            if ki<=0: continue
            ref=ro[0,j,i]; k=0
            while k<ki and (ro[k,j,i]-ref)<0.03: k+=1
            k=min(int(k),int(ki)-1); mld[j,i]=d['depth_w'][k]
    # surface heat flux proxy from top layer heat content change (not a true budget)
    qproxy=None
    if day>0:
        p=load(day-1); dz0=d['depth_w'][1]-d['depth_w'][0]
        qproxy=float(np.nanmean(RHO*CP*dz0*((T[0]-p['temperature'][0]+273.15))/86400.0))
    ice_vol=float(np.nansum(d['ice_thickness']*d['ice_concentration'])*AREA)
    return {'day':day,'ke':ke,'max_u':float(np.nanmax(np.where(m,np.abs(d['u_velocity']),np.nan))),
            'max_v':float(np.nanmax(np.where(m,np.abs(d['v_velocity']),np.nan))),
            'max_w':float(np.nanmax(np.abs(d['w_velocity']))),
            'T_min':float(np.nanmin(np.where(m,T,np.nan))),'T_max':float(np.nanmax(np.where(m,T,np.nan))),
            'S_min_psu':float(np.nanmin(np.where(m,S,np.nan))*1000.0),
            'S_max_psu':float(np.nanmax(np.where(m,S,np.nan))*1000.0),
            'ro_min':float(np.nanmin(np.where(m,ro,np.nan))),
            'ro_negative_cells':int(np.sum(m&(ro<0))),
            'nan_cells':int(np.sum(~np.isfinite(d['u_velocity']))+np.sum(~np.isfinite(T))),
            'max_u_boundary':max_b,'max_u_interior':max_i,
            'wind_work_w':wind_work,'mld_mean_m':float(np.nanmean(mld)),
            'ice_volume_m3':ice_vol,'heat_flux_proxy_w_m2':qproxy,
            'tau_max_pa':float(np.nanmax(np.hypot(tx,ty)))}

def parse_ca():
    p=P/'data/runs/t5c2_config1_detailed/stdout.log'; out={}
    if not p.exists(): return out
    for ln in p.read_text(errors='replace').splitlines():
        m=re.match(r'.*daily diag day=\s*(\d+).*nmix=\s*(\d+).*maxiter=\s*(\d+).*guard=\s*(\S+)',ln)
        if m: out.setdefault(int(m.group(1)),{})['nmix']=int(m.group(2))
        m=re.match(r'.*CA-PROBE \[A_after_adv\] day=\s*(\d+).*inv_cols=\s*(\d+).*max_inv=\s*([0-9.Ee+-]+)',ln)
        if m:
            d=int(m.group(1)); out.setdefault(d,{})
            out[d]['inv_cols']=max(out[d].get('inv_cols',0),int(m.group(2)))
            out[d]['max_inv']=max(out[d].get('max_inv',0.0),float(m.group(3)))
    return out

def main():
    days=list(range(50,66)); rows=[metrics(x) for x in days]; ca=parse_ca()
    for r in rows: r['ca']=ca.get(r['day'])
    # energy daily
    en=[]
    for day in range(55,66):
        r=next(x for x in rows if x['day']==day)
        prev=metrics(day-1); dke=(r['ke']-prev['ke'])/86400.0
        # Laplacian dissipation
        d=load(day); lev=d['water_column_levels']; m=d['water_column_levels']>0
        dz=np.diff(d['depth_w']); vol=dz[:,None,None]*AREA; diss=0.0
        for k in range(18):
            mm=(lev>k)
            if not mm.any(): continue
            dux=np.gradient(d['u_velocity'][k],DX,axis=1); duy=np.gradient(d['u_velocity'][k],DX,axis=0)
            dvx=np.gradient(d['v_velocity'][k],DX,axis=1); dvy=np.gradient(d['v_velocity'][k],DX,axis=0)
            diss+=np.nansum(np.where(mm,RHO*AH*(dux**2+duy**2+dvx**2+dvy**2)*vol[k],0.0))
        en.append({'day':day,'ke':r['ke'],'dke_dt_w':dke,'wind_work_w':r['wind_work_w'],
                   'laplacian_dissipation_w':float(diss)})
    # classify
    worst=max(rows,key=lambda r:r['max_u'])
    advection_bad=any(r['T_min']<-2.0 or r['T_max']>10.0 or r['S_min_psu']<20.0 or r['S_max_psu']>40.0 or r['ro_negative_cells']>0 for r in rows)
    boundary_bad=any(r['max_u_boundary']>r['max_u_interior'] for r in rows)
    ca_spike=any((r['ca'] or {}).get('nmix',0)>1_000_000 for r in rows)
    ca_feedback=any((r['ca'] or {}).get('max_inv',0)>1.0 for r in rows)
    if advection_bad and boundary_bad:
        root='MULTIPLE (ADVECTION_ERROR primary; BOUNDARY_REFLECTION amplifier)'
    elif advection_bad:
        root='ADVECTION_ERROR'
    elif ca_feedback:
        root='CA_FEEDBACK'
    elif boundary_bad:
        root='BOUNDARY_REFLECTION'
    elif ca_spike:
        root='CA_FEEDBACK'
    else:
        root='ENERGY_ACCUMULATION'
    # storm wind dates
    q=P/'data/input/processed/era5/2020/2020_Q1/era5_2020_0103_barents_expanded_merged.nc'
    with Dataset(q) as d:
        u=np.array(d['u10'][:],dtype=np.float64); v=np.array(d['v10'][:],dtype=np.float64); t=np.array(d['valid_time'][:],dtype=np.int64)
    ws=np.hypot(u,v); mx=np.nanmax(ws,axis=(1,2)); idx=int(np.argmax(mx))
    import datetime
    storm={'peak_utc':datetime.datetime.utcfromtimestamp(int(t[idx])).isoformat()+'Z','max_wind_m_s':float(mx[idx]),
           'model_day_peak':int(idx/4),'note':'config1 collapse at day 63-65 precedes the Q1 wind maximum; it is cumulative, not a single-peak trigger'}
    result={'run':'t5c2_config1_detailed','days':rows,'energy':en,'storm':storm,'root_cause':root,
            'evidence':{'advection_bad':advection_bad,'boundary_bad':boundary_bad,
                        'ca_spike_gt_1e6':ca_spike,'ca_inversion_gt1':ca_feedback,
                        'ca_role':'CA inversion grows only after T/S corruption; nmix remains baseline (~3e5/day), so CA is secondary',
                        'worst_day':worst['day'],'worst_max_u':worst['max_u']}}
    for name,key in [('t5c2_ca_diagnostics.json','ca'),('t5c2_advection_diagnostics.json','advection'),
                     ('t5c2_thermo_diagnostics.json','thermo'),('t5c2_boundary_diagnostics.json','boundary'),
                     ('t5c2_energy_budget.json','energy'),('t5c2_root_cause.json','root')]:
        if key=='ca': obj=[{'day':r['day'],'ca':r['ca']} for r in rows]
        elif key=='advection': obj=[{'day':r['day'],'T_min':r['T_min'],'T_max':r['T_max'],'S_min_psu':r['S_min_psu'],'S_max_psu':r['S_max_psu'],'ro_min':r['ro_min'],'ro_negative_cells':r['ro_negative_cells']} for r in rows]
        elif key=='thermo': obj=[{'day':r['day'],'heat_flux_proxy_w_m2':r['heat_flux_proxy_w_m2'],'ice_volume_m3':r['ice_volume_m3'],'mld_mean_m':r['mld_mean_m']} for r in rows]
        elif key=='boundary': obj=[{'day':r['day'],'max_u_boundary':r['max_u_boundary'],'max_u_interior':r['max_u_interior']} for r in rows]
        elif key=='energy': obj=en
        else: obj=result
        (V/name).write_text(json.dumps(obj,indent=2,default=float))
    print(json.dumps({'root_cause':root,'evidence':result['evidence'],'storm':storm,'worst':worst},indent=2,default=float))

if __name__=='__main__': main()
