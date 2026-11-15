#!/usr/bin/env python3
"""Stage 12.20 figures: whole-cube snapshots, profiles, series, GIFs, tracks.

Layout is checked programmatically: white 3-pixel border, contained/non-overlapping
text bboxes, and constant GIF frame size.  Read one snapshot at a time.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from PIL import Image
from scipy.ndimage import binary_erosion, generate_binary_structure, label
from scipy.special import erf
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm, colors
from matplotlib.backends.backend_agg import FigureCanvasAgg

RHO_ICE=916.7; K_ICE=2.1; C_ICE=2009.0; STRUCT=generate_binary_structure(3,1)
RUNS={
 "FJL_A_2020":("FJL","2020","data/validation/stage12.20/final/FJL_A_2020"),
 "NZ_A_2020":("NZ","2020","data/validation/stage12.20/final/NZ_A_2020"),
 "NZ_B_2020":("NZ","2020","data/validation/stage12.20/final/NZ_B_2020"),
 "FJL_A_2024":("FJL","2024","data/validation/stage12.20/final/FJL_A_2024"),
 "NZ_A_2024":("NZ","2024","data/validation/stage12.20/final/NZ_A_2024"),
 "NZ_B_2024":("NZ","2024","data/validation/stage12.20/final/NZ_B_2024"),
 "CTRL_FJL2_2020":("FJL","2020","data/validation/stage12.20/controls/FJL2_2020_phi030"),
 "CTRL_FJL2_2024":("FJL","2024","data/validation/stage12.20/controls/FJL2_2024_phi030"),
}

def snaps(root): return sorted(Path(root).glob("run.nc_snap_*.nc"))
def day_of(f):
    with xr.open_dataset(f) as ds: return float(ds.time.values[0]/86400.0)
def nearest(files, day): return min(files, key=lambda f: abs(day_of(f)-day))
def block(a,t):
    a=np.asarray(a,float); f=[max(1,int(np.ceil(n/t))) for n in a.shape]; pad=[(-n)%f[i] for i,n in enumerate(a.shape)]
    if any(pad): a=np.pad(a,((0,pad[0]),(0,pad[1]),(0,pad[2])))
    nz,ny,nx=a.shape; return a.reshape(nz//f[0],f[0],ny//f[1],f[1],nx//f[2],f[2]).mean((1,3,5))
def load(f,target=None):
    with xr.open_dataset(f) as ds:
        p=np.asarray(ds.phi.values,float); T=np.asarray(ds.T.values,float); S=np.asarray(ds.S_B.values,float)
        x=np.asarray(ds.x.values,float); y=np.asarray(ds.y.values,float); z=np.asarray(ds.z.values,float)
        m=float(ds.mass.values[0]) if "mass" in ds else np.nan; t=float(ds.time.values[0])
    if target:
        p0=p.copy(); p=block(p0,target); tmp=block(p0*T,target); T=tmp/np.maximum(p,1e-6); S=block(S,target)
    return p,T,S,x,y,z,m,t
def axes3(ax,nx,ny,nz,L):
    ax.set_xlim(0,nx); ax.set_ylim(0,ny); ax.set_zlim(0,nz); ax.set_box_aspect((1,1,1))
    ax.set_xticks([0,nx]); ax.set_yticks([0,ny]); ax.set_zticks([0,nz])
    ax.set_xticklabels([0,round(L)]); ax.set_yticklabels([0,round(L)]); ax.set_zticklabels([0,round(L)])
    ax.view_init(22,-60)
def check_png(path):
    a=np.asarray(Image.open(path).convert("RGB")); b=np.concatenate([a[:3].ravel(),a[-3:].ravel(),a[:, :3].ravel(),a[:,-3:].ravel()])
    if np.any(b<245): raise RuntimeError(f"non-white border: {path}")
def check_text(fig,path):
    fig.canvas.draw(); r=fig.canvas.get_renderer(); boxes=[]
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_visible() or not t.get_text().strip(): continue
        b=t.get_window_extent(renderer=r); boxes.append((t,b))
    W,H=fig.canvas.get_width_height()
    for t,b in boxes:
        if b.x0 < -2 or b.y0 < -2 or b.x1 > W+2 or b.y1 > H+2:
            print("OUTSIDE",repr(t.get_text()),b.x0,b.y0,b.x1,b.y1,"canvas",W,H); raise RuntimeError(f"text outside {path}: {t.get_text()}")
    for i in range(len(boxes)):
        for j in range(i+1,len(boxes)):
            a,b=boxes[i]; c,d=boxes[j]
            ab=a.get_window_extent(r); cb=c.get_window_extent(r)
            ix=max(0.0,min(ab.x1,cb.x1)-max(ab.x0,cb.x0)); iy=max(0.0,min(ab.y1,cb.y1)-max(ab.y0,cb.y0))
            if ix*iy > 4.0:
                print("OVERLAP",repr(a.get_text()),ab.bounds,repr(c.get_text()),cb.bounds); raise RuntimeError(f"text overlap {path}: {a.get_text()} / {c.get_text()}")

def snapshot_matrix(tag,root,out,target=32,L=100.0):
    fs=snaps(root); days=(0,90,180,270,350)
    with xr.open_dataset(Path(root)/"run.nc") as ds: m0=float(ds.mass.values[0])
    fig=plt.figure(figsize=(19,12)); gs=fig.add_gridspec(3,6,width_ratios=[1,1,1,1,1,.05],wspace=.08,hspace=.28)
    for r in range(3):
        for c,d in enumerate(days):
            ax=fig.add_subplot(gs[r,c],projection="3d"); f=nearest(fs,d); p,T,S,x,y,z,m,t=load(f,target)
            p=p.transpose(2,1,0); T=T.transpose(2,1,0); S=S.transpose(2,1,0); nz,ny,nx=p.shape
            if r==0: ax.voxels(p>.25,facecolors=cm.Blues(.25+.75*p),edgecolor="none")
            elif r==1:
                surf=p>0.01; surf=surf & ~binary_erosion(surf,STRUCT)
                ax.voxels(surf,facecolors=cm.YlOrRd(colors.Normalize(-10,0)(T)),edgecolor="none")
            else:
                surf=p>0.01; surf=surf & ~binary_erosion(surf,STRUCT)
                ax.voxels(surf,facecolors=cm.Greens(colors.Normalize(0,0.035)(S)),edgecolor="none")
            axes3(ax,nx,ny,nz,L)
            if c==0: ax.text2D(-.18,.5,"phi/T/S"[0] if False else ["phi","T surface","S_B shell"][r],transform=ax.transAxes,rotation=90,va="center",fontsize=11)
            if r==2 and c==0: ax.set_ylabel("y [m]")
            if r==2: ax.set_xlabel("x [m]")
            if c==0: ax.set_zlabel("z [m]")
            ax.set_title(f"day {int(round(t/86400))}  {100*m/m0:.1f}%",fontsize=8)
    for r,(cmap,lab,norm) in enumerate([("Blues","phi",colors.Normalize(0,1)),("YlOrRd","T [C]",colors.Normalize(-10,0)),("Greens","S_B",colors.Normalize(0,.035))]):
        cax=fig.add_axes([.92,.70-.29*r,.012,.20]); fig.colorbar(cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax).set_label(lab)
    fig.suptitle(f"{tag}: whole-cube snapshots",fontsize=13); fig.subplots_adjust(left=.10,right=.88,top=.90,bottom=.05)
    fig.savefig(out,dpi=180,bbox_inches="tight"); check_png(out); check_text(fig,out); plt.close(fig)
    print(out)

def profiles(tag,root,out):
    fs=snaps(root); days=(0,30,90,180,270,350); cols=plt.cm.viridis(np.linspace(.05,.95,len(days)))
    fig,ax=plt.subplots(1,3,figsize=(15,4.8))
    for c,d in zip(cols,days):
        p,T,S,x,y,z,m,t=load(nearest(fs,d)); sol=p>0.01
        tz=np.array([np.nanmean(T[k][sol[k]]) if sol[k].any() else np.nan for k in range(p.shape[0])])
        pz=np.where(p.sum((1,2))>0,p.mean((1,2)),np.nan)
        psum=p.sum((1,2)); k=int(np.argmax(psum))
        tx=(T[k]*p[k]).sum(0)/np.maximum(p[k].sum(0),1e-6); tx[p[k].sum(0)<=1e-8]=np.nan
        ax[0].plot(tz,z,color=c,label=f"{int(round(t/86400))} d"); ax[1].plot(pz,z,color=c); ax[2].plot(x,tx,color=c)
        kappa=K_ICE/(RHO_ICE*C_ICE); tt=max(t,1.0)
        ax[2].plot(x, -1.8 + (-10.0+1.8)*erf(x/(2*np.sqrt(kappa*tt))), color=c, ls="--", lw=.7)
    ax[0].set(title="T(z), ice mean",xlabel="T [C]",ylabel="z [m]"); ax[1].set(title="phi(z)",xlabel="phi",ylabel="z [m]")
    ax[0].set_ylim(0,50); ax[1].set_ylim(0,50)
    ax[0].set_xticks([-20,-10,0]); ax[0].set_yticks([0,25,50])
    ax[1].set_xticks([0,0.5,1]); ax[1].set_yticks([0,25,50])
    ax[2].set(title="T(x); dashed: erf, no moving boundary",xlabel="x [m]",ylabel="T [C]")
    ax[2].set_xticks([0,10,20,30,40,50]); ax[2].set_yticks([-10,-5,0])
    for a in ax:
        a.grid(alpha=.25); a.legend(fontsize=7)
        a.tick_params(axis="x", pad=10, labelsize=7); a.tick_params(axis="y", pad=10, labelsize=7)
    fig.suptitle(tag); fig.subplots_adjust(left=.08,right=.92,bottom=.18,top=.82)
    fig.savefig(out,dpi=180); check_png(out); check_text(fig,out); plt.close(fig); print(out)

def series(tag,root,out):
    with xr.open_dataset(Path(root)/"run.nc") as ds:
        t=np.asarray(ds.time.values,float)/86400.; day=np.floor(t+1e-9).astype(int)
        last=np.r_[np.where(np.diff(day))[0],len(day)-1]
        d={"day":t[last],"mass":ds.mass.values[last],"draft":ds.draft.values[last],"freeboard":ds.freeboard.values[last],
           "grounded":ds.grounded.values[last],"T_w":ds.ocean_T_draft.values[last],"S_w":ds.ocean_S_draft.values[last],
           "basal":ds.voxel_mass_loss_basal.values[last],"lateral":ds.voxel_mass_loss_lateral.values[last],
           "surface":ds.voxel_mass_loss_surface.values[last],"flush":ds.voxel_mass_loss_flush.values[last],
           "calved":ds.calved_mass.values[last]}
    df=pd.DataFrame(d); m0=float(df.mass.iloc[0]); df["melt"]=df.basal+df.lateral+df.surface
    df["resid"]=m0-df.mass-(df["melt"]+df["flush"]+df.calved)
    fig,ax=plt.subplots(2,2,figsize=(13,8))
    ax[0,0].plot(df.day,100*(m0-df.mass)/m0,"k-"); ax[0,0].set(title="Mass loss",ylabel="% m0")
    ax[0,1].plot(df.day,df.draft,label="draft"); ax[0,1].plot(df.day,df.freeboard,label="freeboard")
    ax[0,1].set(title="Geometry",ylabel="m"); ax[0,1].legend(fontsize=7)
    ax[1,0].plot(df.day,100*df["melt"]/m0,label="basal+lateral+surface")
    ax[1,0].plot(df.day,100*df["flush"]/m0,label="flush")
    ax[1,0].plot(df.day,100*df.calved/m0,label="calved")
    ax[1,0].plot(df.day,100*(m0-df.mass)/m0,"k--",label="total")
    ax[1,0].plot(df.day,100*df.resid/m0,"r-",label="residual")
    ax[1,0].set(title="Mass-loss components",ylabel="% m0"); ax[1,0].legend(fontsize=6)
    calf=Path(root)/"run.nc_calved.csv"
    if calf.exists():
        cd=pd.read_csv(calf)
        for _,r in cd.iterrows():
            for a in (ax[0,0],ax[1,0]): a.axvline(r.time_s/86400,color="k",ls=":",lw=.7)
    ax[1,1].plot(df.day,df.T_w,color="C3",label="T"); ax[1,1].set(ylabel="T [C]",title="Water at draft")
    ax2=ax[1,1].twinx(); ax2.plot(df.day,1000*df.S_w,color="C0",label="S"); ax2.set_ylabel("S [g/kg]")
    for a in ax.ravel():
        a.grid(alpha=.2); a.set_xlabel("day")
        g=df.grounded.values.astype(int); st=np.where((g==1)&np.r_[True,g[:-1]==0])[0]; en=np.where((g==1)&np.r_[g[1:]==0,True])[0]
        for i,j in zip(st,en): a.axvspan(df.day.iloc[i],df.day.iloc[j],color="0.6",alpha=.12,lw=0)
    fig.suptitle(tag)
    for aa in fig.axes:
        aa.tick_params(labelsize=6)
        aa.set_xlim(0, float(df.day.iloc[-1]))
        aa.set_xticks([0,100,200,300])
    ax[1,1].tick_params(axis="x", pad=5)
    fig.subplots_adjust(left=.12,right=.92,bottom=.18,top=.80,wspace=.45,hspace=.50)
    fig.savefig(out,dpi=180); check_png(out); check_text(fig,out); plt.close(fig); print(out)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--run",required=True); p.add_argument("--out-dir",type=Path,required=True); p.add_argument("--target",type=int,default=32); a=p.parse_args()
    root=RUNS[a.run][2]; a.out_dir.mkdir(parents=True,exist_ok=True)
    snapshot_matrix(a.run,root,a.out_dir/"snapshots_3d.png",a.target)
    profiles(a.run,root,a.out_dir/"profiles.png")
    series(a.run,root,a.out_dir/"time_series.png")

if __name__=="__main__": main()

# ---- GIF / track / overview (Stage 12.20 final layout) ----
def check_gif(path):
    im=Image.open(path); sizes=set(); n=getattr(im,"n_frames",1)
    for i in range(n):
        im.seek(i); sizes.add(im.size)
    if len(sizes)!=1: raise RuntimeError(f"GIF frame size varies: {path}")
    return n

def make_gif(tag,root,out_prefix,target=24):
    fs=snaps(root); tmp=Path("/tmp/opencode/stage12.20_gif"); tmp.mkdir(parents=True,exist_ok=True)
    year=int(RUNS[tag][1]); start=datetime(year,1,1); frames={"phi":[],"T":[]}
    with xr.open_dataset(Path(root)/"run.nc") as ds: m0=float(ds.mass.values[0])
    for f in fs:
        p,T,S,x,y,z,m,t=load(f,target=target); pt=p.transpose(2,1,0); tt=T.transpose(2,1,0); nz,ny,nx=pt.shape
        d=start+timedelta(days=int(round(t/86400))); pct=100*m/m0
        for key,arr,norm,cmap in (("phi",pt,colors.Normalize(0,1),"Blues"),("T",tt,colors.Normalize(-10,0),"YlOrRd")):
            fig=plt.figure(figsize=(5.2,4.8)); ax=fig.add_subplot(111,projection="3d")
            if key=="phi": ax.voxels(arr>.25,facecolors=cm.Blues(.25+.75*arr),edgecolor="none")
            else:
                solid=arr>0.01; surf=solid&~binary_erosion(solid,STRUCT)
                ax.voxels(surf,facecolors=cm.YlOrRd(norm(arr)),edgecolor="none")
            axes3(ax,nx,ny,nz,100.0)
            ax.set_title(f"{d:%Y-%m-%d}  day {int(round(t/86400))}  {pct:.1f}%",fontsize=8)
            cax=fig.add_axes([.90,.16,.018,.68]); fig.colorbar(cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax)
            fig.subplots_adjust(left=.03,right=.88,bottom=.04,top=.90)
            fn=tmp/f"{tag}_{key}_{int(round(t/86400)):03d}.png"; fig.savefig(fn,dpi=100); plt.close(fig)
            check_png(fn); frames[key].append(Image.open(fn).convert("P",palette=Image.ADAPTIVE))
    for key,fr in frames.items():
        if fr:
            fr[0].save(str(out_prefix)+f"_{key}.gif",save_all=True,append_images=fr[1:],duration=[400]*(len(fr)-1)+[1500],loop=0,optimize=True)
            check_gif(str(out_prefix)+f"_{key}.gif"); print(str(out_prefix)+f"_{key}.gif")

def make_track(tag,root,out,static):
    with xr.open_dataset(Path(root)/"run.nc") as ds:
        t=np.asarray(ds.time.values,float)/86400.; day=np.floor(t+1e-9).astype(int)
        last=np.r_[np.where(np.diff(day))[0],len(day)-1]
        lat=ds.latitude.values[last]; lon=ds.longitude.values[last]; g=ds.grounded.values[last]
    fig=plt.figure(figsize=(8,7)); ax=fig.add_axes([.16,.10,.72,.80])
    for i in range(1,len(lat)):
        ax.plot(lon[i-1:i+1],lat[i-1:i+1],color="C3" if (g[i] or g[i-1]) else "k",
                ls="--" if (g[i] or g[i-1]) else "-",lw=.8)
    ax.scatter(lon[0],lat[0],marker="o",c="C2",s=50,label="start",zorder=4)
    ax.scatter(lon[-1],lat[-1],marker="X",c="k",s=60,label="end",zorder=4)
    ax.set_xlim(lon.min()-.15,lon.max()+.15); ax.set_ylim(lat.min()-.08,lat.max()+.08)
    ax.set_yticks([lat.min()+.1, (lat.min()+lat.max())/2, lat.max()-.1])
    ax.set_xticks([lon.min()+.1, (lon.min()+lon.max())/2, lon.max()-.1])
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude"); ax.set_title(f"{tag} track"); ax.legend(fontsize=8)
    ax.grid(alpha=.2); ax.set_aspect(1/np.cos(np.deg2rad(np.mean(lat))))
    ax.tick_params(axis="y", pad=14, labelsize=7); ax.tick_params(axis="x", pad=12, labelsize=7)
    ins=fig.add_axes([.60,.60,.30,.28]); ins.plot(lon,lat,"k-",lw=.4); ins.scatter(lon[0],lat[0],c="C2",s=12); ins.scatter(lon[-1],lat[-1],c="k",marker="X",s=15)
    ins.set_axis_off()
    fig.savefig(out,dpi=180); check_png(out); check_text(fig,out); plt.close(fig); print(out)

def main_all():
    p=argparse.ArgumentParser(); p.add_argument("--fig-dir",type=Path,default=Path("docs/wiki/stages/stage12/figures/stage12.20/final")); p.add_argument("--smoke",action="store_true"); a=p.parse_args()
    for tag in RUNS:
        root=RUNS[tag][2]
        if not snaps(root): continue
        d=a.fig_dir/tag; d.mkdir(parents=True,exist_ok=True)
        L=50.0 if "CTRL" in tag else 100.0
        snapshot_matrix(tag,root,d/"snapshots_3d.png",32,L)
        profiles(tag,root,d/"profiles.png")
        series(tag,root,d/"time_series.png")
        make_gif(tag,root,d/"evolution")
        make_track(tag,root,d/"track.png","data/input/static/glorys_static_barents.nc")
    overview(a.fig_dir,"data/input/static/glorys_static_barents.nc")

def run_stats(root, tag):
    p=Path(root)/"run.nc"
    if not p.exists(): return None
    with xr.open_dataset(p) as ds:
        t=np.asarray(ds.time.values,float)/86400.; day=np.floor(t+1e-9).astype(int)
        last=np.r_[np.where(np.diff(day))[0],len(day)-1]; t=t[last]; m=ds.mass.values[last]
        lat=ds.latitude.values[last]; lon=ds.longitude.values[last]; g=ds.grounded.values[last]
        cal=float(ds.calved_mass.values[-1]) if "calved_mass" in ds else 0.0
    def cr(f):
        for i in range(1,len(m)):
            if m[i]<=f*m[0]: return float(t[i-1]+(m[i-1]-f*m[0])/(m[i-1]-m[i])*(t[i]-t[i-1]))
        return np.nan
    path=float(np.sum(np.hypot(np.deg2rad(np.diff(lat))*6371000,np.deg2rad(np.diff(lon))*6371000*np.cos(np.deg2rad((lat[1:]+lat[:-1])/2)))))
    st=Path(root)/"status.log"; status=st.read_text().strip() if st.exists() else "END"
    return {"tag":tag,"days":float(t[-1]),"mass_pct":float(100*m[-1]/m[0]),"t50":cr(.5),"t90":cr(.1),"t99":cr(.01),
            "calved_kg":cal,"path_km":path/1000,"status":status,"lat":lat,"lon":lon,"mass":m,"time":t}

def overview(figdir,static):
    rows=[r for tag in RUNS if (r:=run_stats(RUNS[tag][2],tag))]
    if not rows: return
    df=pd.DataFrame([{k:v for k,v in r.items() if k not in ("lat","lon","mass","time")} for r in rows])
    df.to_csv(figdir/"summary.csv",index=False)
    with xr.open_dataset(static) as st: dep=st.deptho.values; glat=st.latitude.values; glon=st.longitude.values
    fig,axs=plt.subplots(1,2,figsize=(14,6)); colors=plt.cm.tab10(np.linspace(0,1,len(rows)))
    for ax,year in zip(axs,(2020,2024)):
        ax.pcolormesh(glon,glat,np.ma.masked_invalid(dep),shading="auto",cmap="Blues_r",alpha=.5)
        for r,c in zip(rows,colors):
            if RUNS[r["tag"]][1]!=str(year): continue
            ax.plot(r["lon"],r["lat"],color=c,lw=.8,label=r["tag"])
            ax.scatter(r["lon"][0],r["lat"][0],marker="o",s=25,color=c,edgecolor="k")
            ax.scatter(r["lon"][-1],r["lat"][-1],marker="X",s=35,color=c,edgecolor="k")
        ax.set(xlim=(5,80),ylim=(63,86),xlabel="longitude",title=f"{year}: free-drift tracks")
        ax.set_yticks([65,70,75,80,85]); ax.set_xticks([10,20,30,40,50,60,70,80])
        ax.set_aspect(1/np.cos(np.deg2rad(78))); ax.grid(alpha=.15); ax.legend(fontsize=6,loc="lower left")
    axs[0].set_ylabel("latitude"); fig.subplots_adjust(left=.08,right=.98,bottom=.10,top=.90,wspace=.10)
    fig.savefig(figdir/"map_2020_2024.png",dpi=180); check_png(figdir/"map_2020_2024.png"); check_text(fig,figdir/"map_2020_2024.png"); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5))
    for r in rows: ax.plot(r["time"],100*r["mass"]/r["mass"][0],label=r["tag"])
    ax.set(xlabel="day",ylabel="remaining mass [%]",title="Mass curves"); ax.grid(alpha=.2); ax.legend(fontsize=7)
    ax.set_xlim(0, 365); ax.set_xticks([0,100,200,300])
    fig.subplots_adjust(left=.12,right=.90,bottom=.15,top=.88); fig.savefig(figdir/"mass_curves.png",dpi=180); check_png(figdir/"mass_curves.png"); check_text(fig,figdir/"mass_curves.png"); plt.close(fig)
    print(figdir/"map_2020_2024.png"); print(figdir/"summary.csv")
