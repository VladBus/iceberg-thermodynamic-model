#!/usr/bin/env python3
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from scipy.ndimage import distance_transform_edt
st=xr.open_dataset('data/input/static/glorys_static_barents.nc')
lat=st.latitude.values; lon=st.longitude.values; dep=st.deptho.values; mask=st.mask.values[0]>0; st.close()
dist=distance_transform_edt(mask)
centers={'FJL':(81.0,55.0),'NZ':(76.0,57.5),'SV':(76.5,20.5)}
rows=[]
for src,(la,lo) in centers.items():
 valid=mask&(dep>=200)&(dist>=8)&(dist<=16)
 # 20-80 km ring approximated by 8-16 GLORYS cells; keep source region
 valid &= (abs(lat[:,None]-la)<=4.0)&(abs(lon[None,:]-lo)<=4.0)
 cand=np.argwhere(valid)
 if len(cand)==0: continue
 # farthest-point sampling, 8 candidates per source
 pts=[cand[np.argmin((lat[cand[:,0]]-la)**2+(lon[cand[:,1]]-lo)**2)]]
 while len(pts)<min(8,len(cand)):
  best=None
  for k in range(len(cand)):
   if any(np.array_equal(cand[k],p) for p in pts): continue
   dmin=min((lat[cand[k,0]]-lat[p[0]])**2+((lon[cand[k,1]]-lon[p[1]])*np.cos(np.deg2rad(la)))**2 for p in pts)
   if best is None or dmin>best[1]: best=(k,dmin)
  pts.append(cand[best[0]])
 for p in pts:
  j,i=p; rows.append({'source':src,'lat':float(lat[j]),'lon':float(lon[i]),'depth_m':float(dep[j,i]),'dist_cells':float(dist[j,i])})
out=Path('data/validation/stage12.20/candidates.csv'); out.parent.mkdir(parents=True,exist_ok=True); pd.DataFrame(rows).to_csv(out,index=False); print(out); print(pd.DataFrame(rows).to_string(index=False))
