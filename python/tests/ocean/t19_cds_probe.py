#!/usr/bin/env python3
"""
T-19 probe: reproduce the CDS snowfall request to settle the accumulation
period of the raw artifacts in data/input/raw/era5/.

Experiment (two small single-day requests, same domain/grid as the artifact):
  R_step12 : time [00:00,12:00], step ["12"]   -> one window per reference
  R_hourly : time [00:00,12:00], step 1..24   -> what download_era5.py requests
Then compare, for a chosen valid time T:
  artifact(T)            vs
  R_step12(T)            (expected = accumulation ref->ref+12h ending at T)
  sum of R_hourly values with valid_time <= T covering (T-12h, T]
If artifact == R_step12 == 12x ~mean hourly -> the 12-hour reading is
CONFIRMED from live CDS metadata; the divisor 43200 is correct.
If artifact values match single hourly fields -> 1-hour reading; divisor must
become 3600 (recorded as a recommendation only; this probe never changes it).

Manual verification tool (needs ~/.cdsapirc; NOT run in CI).
Writes: data/validation/t19_cds_probe.json
"""

import json
import os
import signal
import socket
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
OUT = PROJECT / "data/validation/t19_cds_probe.json"
ARTIFACT = PROJECT / "data/input/raw/era5/2020/2020_01/snowfall_2020_01_fullcoverage.nc"
AREA = [90.0, 7.0, 63.0, 77.5]   # north, west, south, east (artifact bbox)
GRID = ["0.25", "0.25"]
DAY = "15"                        # mid-month: no month-boundary ambiguity

EPOCH = datetime(1970, 1, 1)


def base_request():
    return {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": "snowfall",
        "year": "2020",
        "month": "01",
        "day": DAY,
        "area": AREA,
        "grid": GRID,
    }


def download(client, extra, tag, tmpdir):
    req = dict(base_request())
    req.update(extra)
    path = Path(tmpdir) / f"t19_{tag}.nc"
    print(f"[cds] requesting {tag}: {req}")
    client.retrieve("reanalysis-era5-single-levels", req, str(path))
    return path


def load_sf(path):
    with Dataset(path) as d:
        sf = np.array(d["sf"][:], dtype=np.float64)
        t = np.array(d["valid_time"][:], dtype=np.int64)
        lat = np.array(d["latitude"][:], dtype=np.float64)
        lon = np.array(d["longitude"][:], dtype=np.float64)
    return {"sf": sf, "time": t, "lat": lat, "lon": lon}


def field_at(data, unix_sec):
    idx = int(np.argmin(np.abs(data["time"] - unix_sec)))
    hit = abs(int(data["time"][idx]) - int(unix_sec)) <= 300
    return (np.where(np.isnan(data["sf"][idx]), 0.0, data["sf"][idx])
            if hit else None), int(data["time"][idx])


def main():
    if not os.path.exists(os.path.expanduser("~/.cdsapirc")):
        print("SKIP: ~/.cdsapirc absent; CDS reproduction not possible here.")
        return 0
    import cdsapi  # noqa: E402  (manual tool; env-provided)

    # Hard guards against indefinite hangs (CDS queue / network):
    socket.setdefaulttimeout(60)

    class _CdsTimeout(Exception):
        pass

    def _alarm(signum, frame):
        raise _CdsTimeout("CDS request exceeded per-request deadline")

    signal.signal(signal.SIGALRM, _alarm)
    client = cdsapi.Client(quiet=True, debug=False)
    out = {"test": "t19_cds_probe", "day": f"2020-01-{DAY}",
           "requests": {"step12": {"time": ["00:00", "12:00"], "step": ["12"]},
                        "hourly": {"time": ["00:00", "12:00"],
                                   "step": [str(h) for h in range(1, 25)]}}}
    art = load_sf(ARTIFACT)
    d12 = None
    dh = None
    with tempfile.TemporaryDirectory() as tmp:
        try:
            signal.alarm(600)
            p12 = download(client, out["requests"]["step12"], "step12", tmp)
            signal.alarm(0)
            d12 = load_sf(p12)
            out["step12_downloaded"] = True
        except Exception as exc:  # noqa: BLE001
            signal.alarm(0)
            out["step12_downloaded"] = False
            out["step12_error"] = str(exc)[:300]
        try:
            signal.alarm(900)
            ph = download(client, out["requests"]["hourly"], "hourly", tmp)
            signal.alarm(0)
            dh = load_sf(ph)
            out["hourly_downloaded"] = True
        except Exception as exc:  # noqa: BLE001
            signal.alarm(0)
            out["hourly_downloaded"] = False
            out["hourly_error"] = str(exc)[:300]

        if d12 is None and dh is None:
            out["status"] = "PROBE_FAILED"
            print("CDS probe failed both requests")
            OUT.parent.mkdir(parents=True, exist_ok=True)
            with open(OUT, "w") as f:
                json.dump(out, f, indent=2, default=str)
            return 0

        t_1200 = int((datetime(2020, 1, 15, 12) - EPOCH).total_seconds())
        t_0000 = t_1200 - 12 * 3600
        a_field, a_t = field_at(art, t_1200)
        a_prev, _ = field_at(art, t_0000)
        f12, t12 = (None, None)
        if d12 is not None:
            f12, t12 = field_at(d12, t_1200)
        hsum = np.zeros_like(art["sf"][0]) if (a_field is not None and dh is not None) else None
        n_h = 0
        if dh is not None:
            for tt in dh["time"]:
                if t_1200 - 12 * 3600 < int(tt) <= t_1200:
                    fld, _ = field_at(dh, int(tt))
                    if fld is not None:
                        hsum = hsum + fld
                        n_h += 1

        def stats(f):
            return None if f is None else {
                "mean_m": float(np.nanmean(f)),
                "max_m": float(np.nanmax(f)),
                "sum_m": float(np.nansum(f)),
            }

        out["artifact_12z"] = ({"valid_time_s": a_t, **stats(a_field)}
                               if a_field is not None else None)
        out["request_step12_12z"] = ({"valid_time_s": t12, **stats(f12)}
                                     if f12 is not None else None)
        out["request_hourly_sum_12h"] = ({"n_fields": n_h, **stats(hsum)}
                                         if (hsum is not None and n_h) else None)
        if a_field is not None and f12 is not None:
            out["artifact_vs_step12_maxdiff_m"] = float(np.nanmax(np.abs(a_field - f12)))
            ratio = (np.nansum(np.abs(f12)) + 1e-30) / (np.nansum(np.abs(a_field)) + 1e-30)
            out["step12_over_artifact_sum_ratio"] = float(ratio)
        if a_field is not None and hsum is not None and n_h:
            out["artifact_vs_hourlysum_maxdiff_m"] = float(np.nanmax(np.abs(a_field - hsum)))
        out["artifact_only_field_nonzero"] = bool(a_field is not None and np.nansum(a_field) > 0)

    print(json.dumps(out, indent=2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"wrote {OUT.relative_to(PROJECT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())