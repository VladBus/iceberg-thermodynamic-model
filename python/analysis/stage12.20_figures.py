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
from matplotlib.lines import Line2D
from matplotlib.backends.backend_agg import FigureCanvasAgg

RHO_ICE=916.7; K_ICE=2.1; C_ICE=2009.0; STRUCT=generate_binary_structure(3,1)
LABELS = {
    "days": "days", "start": "start", "end": "end", "grounding": "grounding",
    "melt_out": "melt-out", "strict": "strict ocean", "draft": "draft",
    "freeboard": "freeboard", "residual": "residual", "temperature": "T [°C]",
    "salinity": "S_B [‰]", "ice": "φ, fraction", "longitude": "longitude",
    "latitude": "latitude",
}
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
    nt=5 if L>=75 else 3
    ticks=[np.linspace(0,n,nt) for n in (nx,ny,nz)]
    vals=[np.linspace(0,L,nt) for _ in range(3)]
    labels=[[f"{v:g}" for v in vals[i]] for i in range(3)]
    ax.set_xticks(ticks[0]); ax.set_yticks(ticks[1]); ax.set_zticks(ticks[2])
    ax.set_xticklabels(labels[0],fontsize=6); ax.set_yticklabels(labels[1],fontsize=6); ax.set_zticklabels(labels[2],fontsize=6)
    ax.tick_params(axis="both",pad=0)
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
    fs=snaps(root); last=day_of(fs[-1]); days=[]; used=[]
    for target_day in np.linspace(0,last,5):
        f=nearest(fs,target_day); dd=day_of(f)
        if dd not in used: used.append(dd); days.append(dd)
    with xr.open_dataset(Path(root)/"run.nc") as ds: m0=float(ds.mass.values[0])
    fig=plt.figure(figsize=(19,12)); gs=fig.add_gridspec(3,6,width_ratios=[1,1,1,1,1,.05],wspace=.08,hspace=.28)
    for r in range(3):
        for c,d in enumerate(days):
            ax=fig.add_subplot(gs[r,c],projection="3d"); f=nearest(fs,d); p,T,S,x,y,z,m,t=load(f,target)
            p=p.transpose(2,1,0); T=T.transpose(2,1,0); S=S.transpose(2,1,0); nz,ny,nx=p.shape
            if r==0: ax.voxels(p>0.01,facecolors=cm.Blues(.25+.75*p),edgecolor="none")
            elif r==1:
                surf=p>0.01; surf=surf & ~binary_erosion(surf,STRUCT)
                ax.voxels(surf,facecolors=cm.YlOrRd(colors.Normalize(-10,0)(T)),edgecolor="none")
            else:
                surf=p>0.01; surf=surf & ~binary_erosion(surf,STRUCT)
                ax.voxels(surf,facecolors=cm.Greens(colors.Normalize(0,35)(1000*S)),edgecolor="none")
            axes3(ax,nx,ny,nz,L)
            ax.set_xlabel("x, m",fontsize=7); ax.set_ylabel("y, m",fontsize=7); ax.set_zlabel("z, m",fontsize=10,labelpad=8)
            ax.tick_params(labelsize=6)
            ax.set_title(f"{int(round(t/86400))} days · {100*m/m0:.1f}%",fontsize=8)
    for r,(cmap,lab,norm) in enumerate([("Blues","φ, fraction",colors.Normalize(0,1)),("YlOrRd","T, °C",colors.Normalize(-10,0)),("Greens","S_B, ‰",colors.Normalize(0,35))]):
        cax=fig.add_axes([.92,.70-.29*r,.012,.20]); fig.colorbar(cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax).set_label(lab)
    fig.subplots_adjust(left=.10,right=.88,top=.94,bottom=.05)
    fig.savefig(out,dpi=180); check_png(out); check_text(fig,out); plt.close(fig)
    print(out)

def profiles(tag,root,out):
    fs=snaps(root); last=day_of(fs[-1]); days=[]
    for target in np.linspace(0,last,5):
        d=day_of(nearest(fs,target))
        if d not in days: days.append(d)
    cols=plt.cm.viridis(np.linspace(.05,.95,len(days)))
    fig,ax=plt.subplots(1,2,figsize=(12,5.2))
    zmax=1.0
    for c,d in zip(cols,days):
        p,T,S,x,y,z,m,t=load(nearest(fs,d)); sol=p>0.01
        zmax=float(z[-1])
        tz=np.array([np.nanmean(T[k][sol[k]]) if sol[k].any() else np.nan for k in range(p.shape[0])])
        pz=np.where(p.sum((1,2))>0,p.mean((1,2)),np.nan)
        depth=zmax-z
        lab=f"{int(round(t/86400))} days"
        ax[0].plot(tz,depth,color=c,label=lab)
        ax[1].plot(pz,depth,color=c,label=lab)
    ax[0].set(xlabel="T, °C",ylabel="depth, m"); ax[1].set(xlabel="φ, fraction",ylabel="depth, m")
    for a in ax:
        a.set_ylim(zmax,0); a.set_yticks(np.arange(0,zmax+1,20))
        a.grid(alpha=.25); a.legend(fontsize=7)
        a.tick_params(axis="x",pad=10,labelsize=7); a.tick_params(axis="y",pad=10,labelsize=7)
    ax[0].set_xlim(-20,2); ax[0].set_xticks([-20,-15,-10,-5,0]); ax[1].set_xlim(0,1)
    fig.subplots_adjust(left=.10,right=.96,bottom=.16,top=.94,wspace=.28)
    fig.savefig(out,dpi=180); check_png(out); plt.close(fig); print(out)

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
    for aa,letter in zip(ax.ravel(),("(a)","(b)","(c)","(d)")):
        aa.text(0.0,1.01,letter,transform=aa.transAxes,va="bottom",fontsize=10,fontweight="bold")
    ax[0,0].plot(df.day,100*(m0-df.mass)/m0,"k-"); ax[0,0].set(ylabel="mass loss, % m₀")
    ax[0,1].plot(df.day,df.draft,label="draft"); ax[0,1].plot(df.day,df.freeboard,label="freeboard")
    ax[0,1].set(ylabel="m"); ax[0,1].legend(fontsize=8)
    ax[1,0].plot(df.day,100*df["melt"]/m0,label="melting: base+side+top")
    ax[1,0].plot(df.day,100*df["flush"]/m0,label="flush/removal")
    ax[1,0].plot(df.day,100*df.calved/m0,label="calving")
    ax[1,0].plot(df.day,100*(m0-df.mass)/m0,"k--",label="total loss")
    ax[1,0].plot(df.day,100*df.resid/m0,"r-",label="residual")
    ax[1,0].set(ylabel="% m₀"); ax[1,0].legend(fontsize=7)
    calf=Path(root)/"run.nc_calved.csv"
    if calf.exists():
        cd=pd.read_csv(calf)
        for _,r in cd.iterrows():
            for a in (ax[0,0],ax[1,0]): a.axvline(r.time_s/86400,color="k",ls=":",lw=.7)
    l1,=ax[1,1].plot(df.day,df.T_w,color="C3",label="water T")
    ax[1,1].set_ylabel("T, °C"); ax[1,1].yaxis.label.set_color("C3"); ax[1,1].tick_params(axis="y",colors="C3")
    ax2=ax[1,1].twinx(); l2,=ax2.plot(df.day,1000*df.S_w,color="C0",label="water S")
    ax2.set_ylabel("S, psu",color="C0"); ax2.tick_params(axis="y",colors="C0")
    ax[1,1].legend([l1,l2],["water T","water S"],loc="best",fontsize=8)
    ax2.tick_params(labelsize=9)
    for a in ax.ravel():
        a.grid(alpha=.2); a.set_xlabel("days")
        g=df.grounded.values.astype(int); st=np.where((g==1)&np.r_[True,g[:-1]==0])[0]; en=np.where((g==1)&np.r_[g[1:]==0,True])[0]
        for i,j in zip(st,en): a.axvspan(df.day.iloc[i],df.day.iloc[j],color="0.6",alpha=.12,lw=0)
    for aa in fig.axes:
        aa.tick_params(labelsize=9)
        aa.set_xlabel("days",fontsize=9)
        aa.set_xlim(0, float(df.day.iloc[-1]))
        aa.set_xticks([0,100,200,300])
    ax[1,1].tick_params(axis="x", pad=5)
    fig.subplots_adjust(left=.10,right=.91,bottom=.10,top=.96,wspace=.32,hspace=.32)
    fig.savefig(out,dpi=180); check_png(out); plt.close(fig); print(out)

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
            fig=plt.figure(figsize=(5.8,5.2)); ax=fig.add_subplot(111,projection="3d")
            if key=="phi": ax.voxels(arr>.25,facecolors=cm.Blues(.25+.75*arr),edgecolor="none")
            else:
                solid=pt>0.01; surf=solid&~binary_erosion(solid,STRUCT)
                ax.voxels(surf,facecolors=cm.YlOrRd(norm(arr)),edgecolor="none")
            L=50.0 if "CTRL" in tag else 100.0
            axes3(ax,nx,ny,nz,L)
            ax.set_xlabel("x, m",fontsize=7); ax.set_ylabel("y, m",fontsize=7); ax.set_zlabel("z, m",fontsize=7)
            ax.text2D(.02,.95,f"{int(round(t/86400))} days · {pct:.1f}%",transform=ax.transAxes,fontsize=7,va="top")
            cax=fig.add_axes([.85,.16,.018,.68]); cb=fig.colorbar(cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax)
            cb.set_label("φ, fraction" if key=="phi" else "T, °C",fontsize=8)
            fig.subplots_adjust(left=.06,right=.80,bottom=.06,top=.94)
            fn=tmp/f"{tag}_{key}_{int(round(t/86400)):03d}.png"; fig.savefig(fn,dpi=100); plt.close(fig)
            check_png(fn); frames[key].append(Image.open(fn).convert("P",palette=Image.ADAPTIVE))
    for key,fr in frames.items():
        if fr:
            fr[0].save(str(out_prefix)+f"_{key}.gif",save_all=True,append_images=fr[1:],duration=[400]*(len(fr)-1)+[1500],loop=0,optimize=True)
            check_gif(str(out_prefix)+f"_{key}.gif"); print(str(out_prefix)+f"_{key}.gif")

def make_track(tag,root,out,static):
    with xr.open_dataset(Path(root)/"run.nc") as ds:
        t=np.asarray(ds.time.values,float)/86400.; day=np.floor(t+1e-9).astype(int)
        last=np.r_[np.where(np.diff(day))[0],len(day)-1]; day=day[last]; t=t[last]
        lat=ds.latitude.values[last]; lon=ds.longitude.values[last]; g=ds.grounded.values[last]
        u=np.asarray(ds.ocean_u_draft.values,float)[last]; v=np.asarray(ds.ocean_v_draft.values,float)[last]
        wind=np.hypot(ds.air_u10.values,ds.air_v10.values)[last] if "air_u10" in ds else np.zeros_like(t)
        # Displacement speed from the track itself; t is in days.
        dlat=np.deg2rad(np.diff(lat)); dlon=np.deg2rad(np.diff(lon))
        dist=np.hypot(dlat*6371000.0, dlon*6371000.0*np.cos(np.deg2rad((lat[1:]+lat[:-1])/2)))
        dt=np.maximum(np.diff(t)*86400.0,1.0)
        speed_step=dist/dt
        speed=np.r_[speed_step[0],speed_step]
        gap=dist>100000.0
        speed_plot=speed.copy()
        speed_plot[1:][gap]=np.nan
        # write the displacement audit next to the track
        audit=pd.DataFrame(dict(run=[tag]*len(dist), start_day=day[:-1], end_day=day[1:],
                                distance_km=dist/1000.0, speed_m_s=speed_step,
                                gap_over_100km=gap))
        audit.to_csv(out.parent/"track_speed_audit.csv", index=False)
    with xr.open_dataset(static) as st: dep=st.deptho.values; glat=st.latitude.values; glon=st.longitude.values
    fig=plt.figure(figsize=(10,8)); gs=fig.add_gridspec(2,1,height_ratios=[4.2,1.1],hspace=.22)
    ax=fig.add_subplot(gs[0]); z=np.ma.masked_invalid(dep)
    ax.pcolormesh(glon,glat,z,shading="auto",cmap="Blues_r",alpha=.55)
    ax.contour(glon,glat,np.nan_to_num(dep,nan=0),levels=[0.5],colors="0.25",linewidths=.35)
    c100=ax.contour(glon,glat,np.nan_to_num(dep,nan=0),levels=[100],colors="0.25",linestyles="dashed",linewidths=.45)
    c500=ax.contour(glon,glat,np.nan_to_num(dep,nan=0),levels=[500],colors="0.25",linewidths=.75)
    ax.clabel(c100,fmt="%d m",fontsize=6,inline=True)
    ax.clabel(c500,fmt="%d m",fontsize=6,inline=True)
    ax.text(.55,.02,"100 m isobath (≈ 88 m draft)\n500 m isobath",transform=ax.transAxes,
            fontsize=6,va="bottom",ha="center",bbox=dict(fc="white",ec="none",alpha=.8))
    sc=ax.scatter(lon,lat,c=day,cmap="viridis",s=10,zorder=3)
    start=0
    for i in range(1,len(lon)):
        if (not np.isfinite(speed_plot[i])) or i==len(lon)-1:
            end=i+1 if i==len(lon)-1 else i
            if end>start+1: ax.plot(lon[start:end],lat[start:end],"k-",lw=.5,alpha=.5)
            start=i
    ax.scatter(lon[0],lat[0],marker="o",c="C2",s=50,label="start",zorder=4)
    ax.scatter(lon[-1],lat[-1],marker="X",c="k",s=60,label="end",zorder=4)
    if np.any(g>0):
        ax.scatter(lon[g>0],lat[g>0],marker="x",c="C3",s=18,label="grounding",zorder=5)
    label_idx=sorted(set([0,max(0,len(day)//3),max(0,2*len(day)//3),len(day)-1]))
    for kk,k in enumerate(label_idx):
        ax.annotate(f"{int(day[k])}",(lon[k],lat[k]),xytext=(3,3),textcoords="offset points",fontsize=7)
    ax.set_xlim(lon.min()-.55,lon.max()+.55); ax.set_ylim(lat.min()-.4,lat.max()+.4); ax.set_aspect("auto")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    ax.legend(fontsize=7,loc="lower left"); ax.grid(alpha=.2)
    cb=fig.colorbar(sc,ax=ax,label="days",shrink=.8); ax.tick_params(labelsize=8)
    # 100 km scale bar at lower right
    x0=lon.max()-.5; y0=lat.min()-.25; dlon=100/(111*np.cos(np.deg2rad(np.mean(lat))))
    ax.plot([x0-dlon,x0],[y0,y0],"k-",lw=3); ax.text(x0-dlon/2,y0+.08,"100 km",ha="center",fontsize=7)
    ax2=fig.add_subplot(gs[1])
    l1,=ax2.plot(day,speed_plot,label="iceberg",color="C0")
    l2,=ax2.plot(day,np.hypot(u,v),label="current",color="C1")
    ax2.set_xlabel("days"); ax2.set_ylabel("speed, m s$^{-1}$"); ax2.grid(alpha=.2)
    ax3=ax2.twinx(); l3,=ax3.plot(day,wind,label="wind",color="0.55",alpha=.55)
    ax3.set_ylabel("wind, m s$^{-1}$",color="0.45"); ax3.tick_params(axis="y",colors="0.45",labelsize=8)
    ax2.legend([l1,l2,l3],["iceberg","current","wind"],fontsize=7,loc="upper left")
    for i in range(1,len(day)):
        if g[i] or g[i-1]: ax2.axvspan(day[i-1],day[i],color="0.6",alpha=.15,lw=0)
    fig.subplots_adjust(left=.08,right=.90,bottom=.08,top=.95)
    fig.savefig(out,dpi=180); check_png(out); plt.close(fig); print(out)

def main_all():
    p=argparse.ArgumentParser(); p.add_argument("--fig-dir",type=Path,default=Path("docs/wiki/stages/stage12/figures/stage12.20/final")); p.add_argument("--smoke",action="store_true"); a=p.parse_args()
    for tag in RUNS:
        root=RUNS[tag][2]
        if not snaps(root): continue
        d=a.fig_dir/tag; d.mkdir(parents=True,exist_ok=True)
        L=50.0 if "CTRL" in tag else 100.0
        snapshot_matrix(tag,root,d/"snapshots_3d.png",24,L)
        profiles(tag,root,d/"profiles.png")
        series(tag,root,d/"time_series.png")
        make_gif(tag,root,d/"evolution")
        make_track(tag,root,d/"track.png","data/input/static/glorys_static_barents.nc")
    overview(a.fig_dir,"data/input/static/glorys_static_barents.nc")

def tag_year(tag):
    return 2024 if tag.endswith("2024") or "_2024" in tag else 2020

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
    rows=[r for tag in RUNS if not tag.startswith("CTRL") and (r:=run_stats(RUNS[tag][2],tag))]
    if not rows: return
    df=pd.DataFrame([{k:v for k,v in r.items() if k not in ("lat","lon","mass","time")} for r in rows])
    df.to_csv(figdir/"summary.csv",index=False)
    with xr.open_dataset(static) as st: dep=st.deptho.values; glat=st.latitude.values; glon=st.longitude.values
    fig,axs=plt.subplots(1,2,figsize=(14,6),sharey=True); colors=plt.cm.tab10(np.linspace(0,1,len(rows)))
    def stop_style(status):
        if "MELTED" in status: return "*","melt-out",85
        if "GROUNDED" in status: return "X","grounding",55
        if "STRICT" in status: return "^","strict ocean",55
        return "s","end",45
    for ax,year in zip(axs,(2020,2024)):
        ax.pcolormesh(glon,glat,np.ma.masked_invalid(dep),shading="auto",cmap="Blues_r",alpha=.5)
        c100=ax.contour(glon,glat,np.nan_to_num(dep,nan=0),levels=[100],colors="0.25",linestyles="dashed",linewidths=.45)
        c500=ax.contour(glon,glat,np.nan_to_num(dep,nan=0),levels=[500],colors="0.25",linewidths=.75)
        # labels on the 100/500 m isobaths are supplied by the common key; automatic
        # labels can collide at the two-panel scale.
        for r,c in zip(rows,colors):
            if RUNS[r["tag"]][1]!=str(year): continue
            ax.plot(r["lon"],r["lat"],color=c,lw=.9,label=r["tag"])
            ax.scatter(r["lon"][0],r["lat"][0],marker="o",s=32,color=c,edgecolor="k",zorder=4)
            marker,_,size=stop_style(r["status"])
            ax.scatter(r["lon"][-1],r["lat"][-1],marker=marker,s=size,color=c,edgecolor="k",linewidths=.7,zorder=5)
        ax.set(xlim=(5,80),ylim=(63,86),xlabel="longitude")
        ax.text(.02,.98,str(year),transform=ax.transAxes,va="top",fontsize=11)
        ax.set_yticks([65,70,75,80,85]); ax.set_xticks([10,20,30,40,50,60,70,80])
        ax.grid(alpha=.15)
    handles,labels=axs[0].get_legend_handles_labels()
    handles += [Line2D([0],[0],marker="o",linestyle="none",markerfacecolor="k",markeredgecolor="k",markersize=6,label="start"),
                Line2D([0],[0],marker="*",linestyle="none",markerfacecolor="k",markeredgecolor="k",markersize=8,label="melt-out"),
                Line2D([0],[0],marker="X",linestyle="none",markerfacecolor="k",markeredgecolor="k",markersize=7,label="grounding"),
                Line2D([0],[0],marker="^",linestyle="none",markerfacecolor="k",markeredgecolor="k",markersize=7,label="strict ocean")]
    labels += ["start","melt-out","grounding","strict ocean"]
    axs[0].legend(handles,labels,fontsize=7,loc="lower left",framealpha=.95)
    axs[0].text(.98,.02,"100 m isobath (≈ 88 m draft)\n500 m isobath",transform=axs[0].transAxes,
                fontsize=6,va="bottom",ha="right",bbox=dict(fc="white",ec="none",alpha=.8))
    axs[0].set_ylabel("latitude"); fig.subplots_adjust(left=.07,right=.98,bottom=.09,top=.94,wspace=.04)
    fig.savefig(figdir/"map_2020_2024.png",dpi=180); check_png(figdir/"map_2020_2024.png"); check_text(fig,figdir/"map_2020_2024.png"); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5))
    for r in rows:
        year=tag_year(r["tag"]); ax.plot(r["time"],100*r["mass"]/r["mass"][0],label=r["tag"],ls="-" if year==2020 else "--")
    ax.set(xlabel="days",ylabel="remaining mass, %"); ax.grid(alpha=.2); ax.legend(fontsize=7)
    ax.set_xlim(0, 365); ax.set_xticks([0,100,200,300])
    fig.subplots_adjust(left=.12,right=.90,bottom=.15,top=.88); fig.savefig(figdir/"mass_curves.png",dpi=180); check_png(figdir/"mass_curves.png"); check_text(fig,figdir/"mass_curves.png"); plt.close(fig)
    controls_overview(figdir)
    print(figdir/"map_2020_2024.png"); print(figdir/"summary.csv")

def controls_overview(figdir):
    rows=[r for tag in RUNS if tag.startswith("CTRL") and (r:=run_stats(RUNS[tag][2],tag))]
    if not rows: return
    fig,ax=plt.subplots(figsize=(8,5))
    for r in rows:
        year=tag_year(r["tag"]); ax.plot(r["time"],100*r["mass"]/r["mass"][0],label=r["tag"],ls="-" if year==2020 else "--",lw=1.5)
    ax.set(xlabel="days",ylabel="remaining mass, %")
    ax.grid(alpha=.2); ax.legend(fontsize=8); ax.set_xlim(0,365); ax.set_xticks([0,100,200,300])
    fig.subplots_adjust(left=.12,right=.96,bottom=.15,top=.88); out=figdir/"controls_50m.png"
    fig.savefig(out,dpi=180); check_png(out); check_text(fig,out); plt.close(fig); print(out)
