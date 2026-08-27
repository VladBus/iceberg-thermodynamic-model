"""Stage 7.6C.1 pipeline: reconstruct the real initial sea-ice state from
satellite SIC + SIT onto the model grid and emit legacy 1_k.ice files.

Layout
------
1. Load the authoritative model grid (133x105 nodes, EPSG:3996):
     data/input/processed/grid/ibcao_model_grid.nc
2. Load raw satellite fields (downloaded by download_sea_ice.py):
     data/input/raw/ice/osisaf/*.nc   (OSI-SAF SIC CDR v3.1, EASE2-250, %)
     data/input/raw/ice/c3s_sit/*.nc  (C3S CS2SMOS SIT v1.1, EASE2-125, m)
   Both projections are Lambert azimuthal equal area lon_0=0, lat_0=90
   (EASE-Grid 2.0 North), so the generic grid_mapping proj string drives the
   lon/lat -> source-x/y transform.
3. Regrid both fields onto the model nodes:
     SIC : bilinear (fractional concentration is spatially smooth)
     SIT : nearest  (thickness must not smear across the ice edge / NaN gaps)
   SIT is gated by SIC: thickness is kept only where interpolated SIC > 0.
4. Consistency (QC):
     - clip/interpolations in [-0, 1] domain for SIC
     - drop cells with SIC > 0 but missing SIT (no invented thickness)
     - zero ice on land (grid mask), zero thickness where SIC = 0
     - report all counts/stats to stage7.6C.1_statistics.json
5. Convert to the model's 5 thickness categories. Per wet cell with (A=SIC,
   h=SIT(m)) we need 5 category areas A_k that conserve BOTH
     total area   : sum_k A_k = A               (-> ANS = SIC)
     total volume : sum_k A_k * H_k = A * h     (-> WICES/ANS = SIT)
   with the model's own category thicknesses H_k used at init
   (hard-coded in app/main.f90:296-300):
     H = (0.20, 0.40, 0.95, 1.60, 2.50) m
   The two-populated-bin (2-bin) reconstruction places all ice into the two
   adjacent categories bracketing h and solves the 2x2 linear system exactly
   (the same idea as redis%redistribution in src/ice_redis.f90). Cells with
   h below H[0] or above H[-1] are clamped into the thinnest/thickest category
   (volume bias reported), cells with A < 0.005 are treated as open water
   (matches the redis ANS<0.005 zeroing gate).
6. Emit legacy text files 1_1.ice ... 1_5.ice (133 records x 105 reals each,
   list-directed Fortran layout read by app/main.f90 into an1(:, :, 2..6))
   into data/input/generated/real_grid/ice_<date>/, plus a reconstruction
   metadata JSON. Snow is NOT part of the file format (the model starts with
   hsnow = 0 and builds it from ERA5 snowfall).
7. Diagnostics: model-grid sic_model.nc / sit_model.nc / category netcdf,
   png overview maps, and the statistics JSON.

No physics, grid, bathymetry or ERA5 files are modified (Stage 7.6C.2 defers
the ERA5-domain expansion).
"""

import argparse
import datetime
import json
import pathlib
from glob import glob

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from pyproj import CRS, Transformer
from scipy.interpolate import RegularGridInterpolator

PROJ_ROOT = pathlib.Path(__file__).resolve().parents[2]
GRID_FILE = PROJ_ROOT / "data/input/processed/grid/ibcao_model_grid.nc"
RAW_ICE = PROJ_ROOT / "data/input/raw/ice"
PROC_ICE = PROJ_ROOT / "data/input/processed/ice"
GEN_ICE = PROJ_ROOT / "data/input/generated/real_grid"
DIAG_DIR = PROJ_ROOT / "data/output/diagnostics/stage7.6C.1"

# Model category thicknesses as hard-coded in app/main.f90:296-300
# (the initialization computes wice1 = H_k * an1(:, :, k+1)).
# NOTE: H[1] = 0.40 differs from param%hst(2) = 0.50 -- a latent legacy
# inconsistency in the code; reconstructed volumes below use the value the
# code actually applies. Physics is NOT modified in this stage.
H_THICK = np.array([0.20, 0.40, 0.95, 1.60, 2.50])
N_CAT = len(H_THICK)

# redis() zeroes cells with aggregated concentration < 0.005 (ice_redis.f90:285)
ANS_MIN = 0.005


def read_hhhbar(path, is1=133, js1=105):
    """Read hhh.bar exactly as coup1() does (grid_coupling.f90:54-64).

    7 blocks; in each block a header line (skipped) then is1 rows of 15I5
    (15 five-column fields). Returns kt1 (i, j) int array, i=1..is1 rows,
    j = (block-1)*15 + field.
    """
    kt = np.zeros((is1, js1), dtype=np.int64)
    with open(path) as f:
        for b in range(7):
            next(f)
            j1 = b * 15
            for i in range(is1):
                line = next(f).rstrip("\n")
                for c in range(15):
                    kt[i, j1 + c] = int(line[c * 5 : (c + 1) * 5])
    return kt


def coup1_ht(kt_raw):
    """Replicate coup1()'s depth field HT (cm) from raw hhh.bar kt1 values.

    grid_coupling.f90:73-117: ht = kt1 (real); land kt1==8 -> 8888; the
    boundary rules ht(1:15,94)=ht(:,js1)=ht(:,1)=ht(1,:)=8888; clamp
    5<ht<=10 ->10, ht<=3 ->3; then ht *= 100 (cm). Model wet mask == ht!=8888.
    """
    is1, js1 = kt_raw.shape
    ht = kt_raw.astype(np.float64)
    ht[kt_raw == 8] = 8888.0
    ht[:15, 93] = 8888.0  # ht(1:15, 94)
    ht[:, js1 - 1] = 8888.0  # ht(:, js1)
    ht[:, 0] = 8888.0  # ht(:, 1)
    ht[0, :] = 8888.0  # ht(1, :)
    m = ht != 8888.0
    ht[m & (ht > 5.0) & (ht <= 10.0)] = 10.0
    ht[m & (ht <= 3.0)] = 3.0
    ht[m] = ht[m] * 100.0
    return ht


def load_model_grid():
    """Return node coordinates, masks and the model's TRUE wet mask.

    The authoritative ocean mask used by the Fortran code is NOT the netCDF
    `mask` field but the depth-based kt1!=0 mask computed by coup1() from
    hhh.bar (grid_coupling.f90). We replicate exactly that ht field and export
    `wet` (=ht!=8888). Falls back to the netCDF mask when hhh.bar is absent.
    """
    ds = xr.open_dataset(GRID_FILE)
    lat = ds["lat"].values  # (is1, js1) = (133, 105)
    lon = ds["lon"].values
    mask = ds["mask"].values.astype(int)
    depth = ds["depth"].values if "depth" in ds else np.full(lat.shape, np.nan)
    px = np.asarray(ds["proj_x"].values) if "proj_x" in ds else None
    py = np.asarray(ds["proj_y"].values) if "proj_y" in ds else None
    ds.close()
    is1, js1 = lat.shape

    hhbfile = GEN_ICE / "hhh.bar"
    hhbfile = hhbfile if hhbfile.exists() else PROJ_ROOT / "hhh.bar"
    if hhbfile.exists():
        kt = read_hhhbar(hhbfile)
        wet = coup1_ht(kt) != 8888.0
        print(
            f"hhh.bar: model wet mask from {hhbfile} "
            f"({int(wet.sum())} wet / {int((~wet).sum())} land)"
        )
    else:
        wet = mask == 1
        print("WARNING: hhh.bar missing -- using netCDF mask for wet cells")
    return {
        "lat": lat,
        "lon": lon,
        "mask": mask,  # 1 = ocean, 0/(other) = land (netCDF only)
        "water_depth_cm": coup1_ht(kt) if hhbfile.exists() else None,
        "wet": wet,  # coup1-consistent model ocean mask
        "depth": depth,
        "px": px,
        "py": py,
        "is1": is1,
        "js1": js1,
    }


def find_raw_file(subdir, prefix, date_tag):
    """Find the extracted raw NetCDF for this product (single day)."""
    d = RAW_ICE / subdir
    cands = sorted(glob(str(d / "*.nc")))
    cands = [c for c in cands if not c.endswith("_manifest") and "manifest" not in c]
    if date_tag:
        cands = [c for c in cands if date_tag in c]
    if not cands:
        raise FileNotFoundError(f"no raw {prefix} file in {d}")
    return cands[0]


def source_sampler(path, var_name, coord_meters):
    """Return (sampler_callable, info_dict) for a regular EASE2 netcdf field.

    Coordinates are read from the file (xc, yc). ``coord_meters`` is the
    factor converting the file's coordinate units to metres (1000.0 for km).
    The returned callable takes model-node eastings/northings in EASE2 metres
    and returns the interpolated field, or NaN outside the valid-data domain.
    """
    ds = xr.open_dataset(path)
    xc = ds["xc"].values * coord_meters
    yc = ds["yc"].values * coord_meters
    field = ds[var_name].values
    if field.ndim == 3:
        field = field[0]

    # RegularGridInterpolator needs strictly increasing axes; EASE2 north
    # grids are often stored north-to-south (descending yc) -- normalize.
    if xc[0] > xc[-1]:
        xc = xc[::-1]
        field = field[:, ::-1]
    if yc[0] > yc[-1]:
        yc = yc[::-1]
        field = field[::-1, :]

    proj4 = None
    gm_var = ds[var_name].attrs.get("grid_mapping")
    if gm_var and gm_var in ds.variables:
        proj4 = ds[gm_var].attrs.get("proj4_string") or ds[gm_var].attrs.get(
            "proj4_str"
        )
    info = {
        "path": str(path),
        "var": var_name,
        "file_proj4": proj4,
        "nx": field.shape[1],
        "ny": field.shape[0],
        "dx_km": (xc[1] - xc[0]) / 1000.0,
        "units": ds[var_name].attrs.get("units"),
    }
    ds.close()
    return (xc, yc, field, proj4), info


def transformer_to_source(proj4):
    """Return Transformer EPSG:4326 -> source EASE2 CRS (meters)."""
    if proj4 is None:
        raise RuntimeError("source file has no proj4 grid mapping")
    src_crs = CRS.from_proj4(proj4)
    return Transformer.from_crs(CRS.from_epsg(4326), src_crs, always_xy=True)


def regrid_model(model, xc, yc, field, proj4, interp="bilinear"):
    """Sample ``field`` (regular grid xc, yc in metres) at model nodes."""
    tr = transformer_to_source(proj4)
    xs, ys = tr.transform(model["lon"].ravel(), model["lat"].ravel())  # (is1*js1,)

    method = "linear" if interp == "bilinear" else "nearest"
    ok = (
        (xs >= xc[0])
        & (xs <= xc[-1])
        & (ys >= yc[0])
        & (ys <= yc[-1])
        & np.isfinite(xs)
        & np.isfinite(ys)
    )
    out = np.full(xs.shape, np.nan)
    if ok.any():
        itp = RegularGridInterpolator(
            (yc, xc), field, method=method, bounds_error=False, fill_value=np.nan
        )
        out[ok] = itp(np.column_stack([ys[ok], xs[ok]]))
    return out.reshape(model["is1"], model["js1"])


def reconstruct_category_areas(A2, h2):
    """Map cell-averaged (concentration A, mean thickness h) to 5 category
    areas conserving total area and volume (exact 2-bin bracketing)."""
    shape = A2.shape
    A = np.asarray(A2, dtype=float).ravel()
    h = np.asarray(h2, dtype=float).ravel()
    cats = np.zeros((A.size, N_CAT), dtype=float)

    valid = (A >= ANS_MIN) & np.isfinite(h) & (h > 0.0)
    iA = A[valid]
    ih = h[valid]
    idx_valid = np.nonzero(valid)[0]
    if iA.size:
        low = ih < H_THICK[0]  # thinner than the thinnest bin -> clamp
        high = ih > H_THICK[-1]  # thicker than the thickest bin -> clamp
        mid = ~(low | high)

        if mid.any():
            p = np.searchsorted(H_THICK, ih[mid], side="right") - 1  # 0..N_CAT-2
            hl = H_THICK[p]
            hu = H_THICK[p + 1]
            frac_hi = (ih[mid] - hl) / (hu - hl)
            cats[idx_valid[mid], p] = iA[mid] * (1.0 - frac_hi)
            cats[idx_valid[mid], p + 1] = iA[mid] * frac_hi
        cats[idx_valid[low], 0] = iA[low]
        cats[idx_valid[high], N_CAT - 1] = iA[high]

    return cats.reshape(shape + (N_CAT,))


def write_ice_files(cats, outdir, date_str, model):
    """Write 5 legacy Fortran list-directed text files 1_1.ice..1_5.ice.
    Layout: 133 records, each 105 whitespace-separated reals (matches the
    read loop app/main.f90:272-281: do i=1,is1; read(1,*) (an1(i,j,k),j=1,js1)).
    """
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for k in range(N_CAT):
        conc = cats[:, :, k]  # (is1, js1)
        # 9.99 is the legacy "missing" marker read as zero (main.f90:288);
        # we write clean zeros for open water / land instead.
        p = outdir / f"1_{k + 1}.ice"
        with open(p, "w") as f:
            for i in range(model["is1"]):
                f.write(" ".join(f"{conc[i, j]:.4f}" for j in range(model["js1"])))
                f.write("\n")
        paths.append(str(p))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default="2020-01-01")
    args = parser.parse_args()
    date = datetime.date.fromisoformat(args.date)
    date_tag = date.strftime("%Y%m%d")

    model = load_model_grid()
    is1, js1 = model["is1"], model["js1"]
    is_max, js_max = is1 - 1, js1 - 1  # redis/advection loops run i<=is_max, j<=js_max
    # the model's own wet mask (coup1 replica from hhh.bar) restricted to the
    # active computational domain -- the rim rows is1 / js1 are never
    # integrated by redis() and must stay ice-free.
    active = np.zeros((is1, js1), dtype=bool)
    active[:is_max, :js_max] = True
    wet = model["wet"] & active
    print(f"Model grid: {is1} x {js1} nodes, active wet cells = {int(wet.sum())}")

    # --- load raw SIC / SIT ---
    sic_file = find_raw_file("osisaf", "sic", date_tag)
    sit_file = find_raw_file("c3s_sit", "sit", date_tag)
    (xc_sic, yc_sic, f_sic, proj4_sic), info_sic = source_sampler(
        sic_file, "ice_conc", coord_meters=1000.0
    )
    (xc_sit, yc_sit, f_sit, proj4_sit), info_sit = source_sampler(
        sit_file, "sea_ice_thickness", coord_meters=1.0
    )
    print("SIC source:", info_sic)
    print("SIT source:", info_sit)

    # --- regrid ---
    sic = (
        regrid_model(model, xc_sic, yc_sic, f_sic, proj4_sic, interp="bilinear") / 100.0
    )
    sit = regrid_model(model, xc_sit, yc_sit, f_sit, proj4_sit, interp="nearest")

    # --- QC & consistency ---
    wet = model["wet"] & active
    # lev-4 SIC product is spatially filled; count any remaining gaps before
    # the nan->0 fill (reported in statistics).
    sic = np.clip(np.nan_to_num(sic, nan=0.0), 0.0, 1.0)
    sic_missing = 0
    sit_missing_ice = (sic > ANS_MIN) & (~np.isfinite(sit) | (sit <= 0.0))
    sit_without_ice = (sic <= ANS_MIN) & np.isfinite(sit) & (sit > 0.0)

    # policy: ice cannot exist without a thickness -> drop those cells
    drop = wet & ((sic > ANS_MIN) & (~np.isfinite(sit) | (sit <= 0.0)))
    sic_d = sic.copy()
    sit_d = sit.copy()
    sic_d[drop] = 0.0
    sit_d[drop] = 0.0
    sit_d[sic_d <= ANS_MIN] = 0.0
    # land -> zero
    sic_d[~wet] = 0.0
    sit_d[~wet] = 0.0

    # --- reconstruction ---
    cats = reconstruct_category_areas(sic_d, sit_d)

    # validation (post-reconstruction aggregates)
    ans = cats.sum(axis=2)  # summed concentration
    wices = (cats * H_THICK[None, None, :]).sum(axis=2)  # volume [m]
    hices = np.where(ans >= ANS_MIN, wices / np.maximum(ans, 1e-30), 0.0)

    # reconstruction-domain errors (exclude cells below the ANS gate and
    # cells clamped to the thinnest/thickest category, which by design carry
    # a bounded thickness bias -- reported separately)
    rec_domain = sic_d >= ANS_MIN
    errA = (
        np.abs(ans[rec_domain] - sic_d[rec_domain]).max() if rec_domain.any() else 0.0
    )
    not_clamped = rec_domain & (sit_d >= H_THICK[0]) & (sit_d <= H_THICK[-1])
    errV = (
        np.abs(wices[not_clamped] - sic_d[not_clamped] * sit_d[not_clamped]).max()
        if not_clamped.any()
        else 0.0
    )
    n_gate = int((sic_d < ANS_MIN).sum())
    n_clamp_low = int((rec_domain & (sit_d > 0) & (sit_d < H_THICK[0])).sum())
    n_clamp_high = int((rec_domain & (sit_d > H_THICK[-1])).sum())
    print(
        f"QC: drop cells SIC>0&SIT<=0   = {int(drop.sum())} "
        f"({100*drop.sum()/max(1,wet.sum()):.2f}% of wet)"
    )
    print(f"QC: SIT>0 where SIC<=0        = {int(sit_without_ice.sum())}")
    print(f"QC: SIC>0 & SIT missing       = {int(sic_missing)}")
    print(f"Reconstruction max |errA| (rec domain) = {errA:.2e}")
    print(f"Reconstruction max |errV| (non-clamp)  = {errV:.2e}")
    print(
        f"Cells below ANS gate        = {n_gate}, clamp-low = {n_clamp_low}, "
        f"clamp-high = {n_clamp_high}"
    )
    imask = wet & (ans >= ANS_MIN)
    print(
        f"Aggregated: ice-covered cells = {int(imask.sum())}, "
        f"mean ANS={float(ans[imask].mean()):.3f}, "
        f"mean HICES={float(hices[imask].mean()):.3f} m"
    )

    # --- write outputs ---
    PROC_ICE.mkdir(parents=True, exist_ok=True)
    lat, lon = model["lat"], model["lon"]
    dsi = xr.Dataset(
        {
            "sic_model": (
                ("i", "j"),
                sic_d,
                {
                    "long_name": "sea ice concentration on model grid",
                    "standard_name": "sea_ice_area_fraction",
                    "units": "1",
                },
            ),
            "sit_model": (
                ("i", "j"),
                sit_d,
                {
                    "long_name": "mean sea ice thickness on model grid",
                    "standard_name": "sea_ice_thickness",
                    "units": "m",
                },
            ),
            "depth": (("i", "j"), model["depth"]),
            "lat": (("i", "j"), lat, {"units": "degrees_north"}),
            "lon": (("i", "j"), lon, {"units": "degrees_east"}),
        }
    )
    if model["px"] is not None:
        # grid file stores separable coords: proj_x(j), proj_y(i)
        dsi = dsi.assign_coords(
            proj_x=("j", model["px"], {"units": "m", "crs": "EPSG:3996"}),
            proj_y=("i", model["py"], {"units": "m", "crs": "EPSG:3996"}),
        )
    dsi.attrs = {
        "title": f"Stage 7.6C.1 satellite ice on model grid ({date})",
        "grid": "ibcao_model_grid.nc (EPSG:3996, 133x105 nodes)",
        "sic_source": info_sic["path"],
        "sit_source": info_sit["path"],
        "Conventions": "CF-1.10",
    }
    dsi.to_netcdf(PROC_ICE / "sic_model.nc")
    dsi["sit_model"].to_netcdf(PROC_ICE / "sit_model.nc")

    # per-category concentrations (validation / archive)
    dsc = xr.Dataset(
        {
            f"conc_cat{k + 1}": (("i", "j"), cats[:, :, k], {"units": "1"})
            for k in range(N_CAT)
        },
        coords={"lat": (("i", "j"), lat), "lon": (("i", "j"), lon)},
        attrs={"title": f"category concentrations (2-bin reconstruction) {date}"},
    )
    dsc.to_netcdf(PROC_ICE / f"category_concentrations_{date_tag}.nc")

    # legacy files + metadata
    gen_dir = GEN_ICE / f"ice_{date}"
    paths = write_ice_files(cats, gen_dir, date_tag, model)
    metadata = {
        "init_date": str(date),
        "generated_by": "python/ice/build_initial_ice.py",
        "grid_file": str(GRID_FILE),
        "category_area_conservation": "sum(A_k) = SIC",
        "category_volume_conservation": "sum(A_k*H_k) = SIC*SIT (2-bin exact)",
        "category_thicknesses_m": list(map(float, H_THICK)),
        "ans_min_gate": ANS_MIN,
        "sic_source": info_sic,
        "sit_source": info_sit,
        "ice_files": paths,
    }
    with open(gen_dir / "reconstruction_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    # --- statistics JSON ---
    ice_mask = wet & (ans >= ANS_MIN)
    stats = {
        "init_date": str(date),
        "grid": {
            "nodes": (is1, js1),
            "wet_cells": int(wet.sum()),
            "land_cells": int((~wet).sum()),
        },
        "sources": {"sic": info_sic, "sit": info_sit},
        "qc": {
            "sic_missing_in_wet": int(sic_missing),
            "sit_missing_with_ice": int(sit_missing_ice.sum()),
            "sit_without_ice": int(sit_without_ice.sum()),
            "dropped_cells_sic0": int(drop.sum()),
        },
        "reconstruction": {
            "ice_cells": int(ice_mask.sum()),
            "sic_range": [float(sic_d.min()), float(sic_d.max())],
            "sit_range_on_ice": [
                float(sit_d[ice_mask].min()),
                float(sit_d[ice_mask].max()),
            ],
            "mean_sic_over_ice": float(sic_d[ice_mask].mean()),
            "mean_sit_over_ice": float(sit_d[ice_mask].mean()),
            "mean_hices_over_ice": float(hices[ice_mask].mean()),
            "total_ice_volume_m3": float((wices[ice_mask] * 13890.0 * 13890.0).sum()),
            "thickness_clamped_low": int(n_clamp_low),
            "thickness_clamped_high": int(n_clamp_high),
            "cells_below_ans_gate": int(n_gate),
            "max_cat_area_error": float(errA),
            "max_volume_error_m": float(errV),
        },
    }
    with open(PROC_ICE / "stage7.6C.1_statistics.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)
    print("Statistics: ", PROC_ICE / "stage7.6C.1_statistics.json")

    # --- diagnostic plots ---
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    for name, arr, cmap, title in [
        ("sic_model", sic_d, "viridis", f"SIC model grid {date}"),
        ("sit_model", sit_d, "magma", f"SIT model grid {date} [m]"),
        ("hices_reconstructed", hices, "magma", f"Reconstructed HICES {date} [m]"),
    ]:
        plt.figure(figsize=(10, 8))
        masked = np.ma.masked_where(~wet, arr)
        plt.pcolormesh(lon, lat, masked, cmap=cmap, shading="auto")
        try:
            plt.colorbar(label=title.split()[-1])
        except Exception:
            pass
        plt.title(title)
        plt.xlabel("lon [E]")
        plt.ylabel("lat [N]")
        plt.savefig(DIAG_DIR / f"{name}.png", dpi=150, bbox_inches="tight")
        plt.close()
    cat_img = None  # placeholder removed
    print("Plots: ", DIAG_DIR)
    print("Ice files: ", gen_dir)


if __name__ == "__main__":
    main()
