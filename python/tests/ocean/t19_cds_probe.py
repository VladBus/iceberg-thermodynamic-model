#!/usr/bin/env python3
"""T-19 probe v2: determine the ERA5 snowfall accumulation period.

The v1 probe used ``step`` ranges and CDS collapsed the multi-step request, so
its 12-hour conclusion was invalid.  ECMWF documents single-level accumulated
fields as "accumulation over the hour ending at the validity time" for hourly
data.  This probe requests one day, 24 hourly validity times, **without** the
``step`` parameter, and compares the 12:00 field with the mean of all 24 fields:

  R = mean(spatial, 12:00) / mean(spatial, all 24 hours)

Expected:
  * hourly accumulation: R in [0.2, 5.0] (synoptic variability);
  * 12-hour accumulation: R ~ 12 (the noon field is 12x an hourly mean).

Writes data/validation/t19_cds_probe_v2.json.  Manual tool; not run in CI.
"""

import json
import os
import signal
import socket
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

PROJECT = Path(__file__).resolve().parents[3]
OUT = PROJECT / "data/validation/t19_cds_probe_v2.json"
AREA = [90.0, 7.0, 63.0, 77.5]
GRID = ["0.25", "0.25"]
DAY = "15"
HOURS = [f"{h:02d}:00" for h in range(24)]


def request(client, tmpdir):
    req = {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": "snowfall",
        "year": "2020",
        "month": "01",
        "day": DAY,
        "time": HOURS,
        "area": AREA,
        "grid": GRID,
        # deliberately no "step": a single hourly validity request
    }
    path = Path(tmpdir) / "t19_v2_hourly.nc"
    print("[cds] requesting 24 hourly snowfall fields:", req)
    client.retrieve("reanalysis-era5-single-levels", req, str(path))
    return path


def load(path):
    with Dataset(path) as d:
        return {
            "sf": np.array(d["sf"][:], dtype=np.float64),
            "valid_time": np.array(d["valid_time"][:], dtype=np.int64),
            "lat": np.array(d["latitude"][:], dtype=np.float64),
            "lon": np.array(d["longitude"][:], dtype=np.float64),
        }


def main():
    out = {
        "test": "t19_cds_probe_v2",
        "status": "UNKNOWN",
        "v1_status": "INVALID — the step-range request used by v1 was collapsed by CDS; its 12-hour conclusion is not evidence.",
        "day": f"2020-01-{DAY}",
        "request": {"time": HOURS, "step": None, "area": AREA, "grid": GRID},
    }
    if not os.path.exists(os.path.expanduser("~/.cdsapirc")):
        out["status"] = "SKIP_NO_CDSAPIRC"
        print("SKIP: ~/.cdsapirc absent")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, indent=2, default=str))
        return 0

    import cdsapi

    socket.setdefaulttimeout(120)

    def alarm(signum, frame):
        raise TimeoutError("CDS request exceeded deadline")

    signal.signal(signal.SIGALRM, alarm)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            signal.alarm(1200)
            path = request(cdsapi.Client(quiet=True, debug=False), tmp)
            signal.alarm(0)
            d = load(path)
    except Exception as exc:  # noqa: BLE001
        signal.alarm(0)
        out["status"] = "PROBE_FAILED"
        out["error"] = str(exc)[:500]
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, indent=2, default=str))
        print(json.dumps(out, indent=2))
        return 0

    sf = d["sf"]
    out["n_fields"] = int(sf.shape[0])
    out["valid_times_utc"] = [
        datetime.fromtimestamp(int(t), tz=timezone.utc).isoformat()
        for t in d["valid_time"]
    ]
    means = [float(np.nanmean(sf[i])) for i in range(sf.shape[0])]
    out["hourly_spatial_means_m"] = means
    out["mean_all_24_m"] = float(np.nanmean(means))
    # 12:00 is index 12 if the requested order was preserved
    idx_12 = 12 if len(means) == 24 else int(np.argmin(np.abs(
        d["valid_time"] - int(datetime(2020, 1, 15, 12, tzinfo=timezone.utc).timestamp())
    )))
    out["mean_12z_m"] = means[idx_12]
    ratio = means[idx_12] / out["mean_all_24_m"] if out["mean_all_24_m"] > 0 else None
    out["ratio_12z_over_all24"] = ratio
    if ratio is None:
        verdict = "INCONCLUSIVE_ZERO_MEAN"
    elif 0.2 <= ratio <= 5.0:
        verdict = "HOURLY_ACCUMULATION"
    elif ratio >= 8.0:
        verdict = "12-HOUR_ACCUMULATION"
    else:
        verdict = "INCONCLUSIVE"
    out["verdict"] = verdict
    out["divisor_recommendation_s"] = 3600.0 if verdict == "HOURLY_ACCUMULATION" else 43200.0
    out["status"] = "PASS"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
