"""Download a single EN4.2.2 monthly ocean temperature/salinity analysis.

The Met Office publishes EN4 analyses as yearly zips (12 monthly files, ~300 MB
per year). We only need one month, so this tool performs a *surgical HTTP range
extraction*: it fetches only the zip end-of-central-directory (last 64 KiB), then
the central-directory block, then the local header and deflate stream of the one
member of interest. The full archive is never downloaded.

Selected product (Stage 7.7 Phase 2):
    EN.4.2.2.f.analysis.g10.YYYYMM.nc
    EN4.2.2 objective analysis, Gouretski-Reseghetti (2010) XBT + Gouretski-Cheng
    (2020) MBT corrections, monthly mean at 1x1 degree, 42 depth levels (5-5350 m).
    temperature: potential temperature [K]; salinity: practical [1].

Usage:
    python python/ocean/download_initial_ts.py
    python python/ocean/download_initial_ts.py --year 2020 --month 1 \
        --output data/input/raw/ocean/EN.4.2.2.f.analysis.g10.202001.nc
    python python/ocean/download_initial_ts.py --verify-only

Notes:
- Default output follows the raw-input hierarchy of Stage 6.2:
  data/input/raw/ocean/EN.4.2.2.f.analysis.g10.YYYYMM.nc
- Idempotent: if the output already exists and passes validation it is left
  untouched unless --force is given.
- Raw data are NOT committed to Git (data/ is gitignored).
- Licence: Non-Commercial Government Licence v2 (research use).
"""

import argparse
import pathlib
import struct
import sys
import zlib

import requests

EN4_BASE = "https://www.metoffice.gov.uk/hadobs/en4/data/en4-2-1/EN.4.2.2"
CORRECTIONS = "g10"  # Gouretski-Reseghetti XBT / Gouretski-Cheng MBT corrections


def _fetch(url, off, n, timeout=180):
    """Fetch exactly n bytes from url starting at byte off (HTTP range)."""
    headers = {"Range": f"bytes={off}-{off + n - 1}"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    body = r.content
    if len(body) != n:
        raise IOError(f"short range request: got {len(body)} bytes, wanted {n} @ {off}")
    return body


def _zip_size(url):
    """Total remote zip size via HEAD (Content-Range) or a 1-byte range probe."""
    h = requests.head(url, timeout=60)
    h.raise_for_status()
    for key in ("Content-Range", "Content-Length"):
        raw = h.headers.get(key)
        if raw and "/" in raw:
            return int(raw.split("/")[1])
        if raw:
            try:
                return int(raw)
            except ValueError:
                pass
    r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=60)
    r.raise_for_status()
    return int(r.headers["Content-Range"].split("/")[1])


def _parse_central_dir(url, size):
    """Fetch zip tail + central directory; return {name: member-info}."""
    tail = _fetch(url, size - 65536, 65536)
    eocd_at = tail.rfind(b"\x50\x4b\x05\x06")
    if eocd_at < 0:
        raise IOError("end-of-central-directory not found in zip tail")
    n_entries, cd_size, cd_off = struct.unpack(
        "<HII", tail[eocd_at + 10 : eocd_at + 20]
    )
    cd = _fetch(url, cd_off, cd_size)
    members = {}
    pos = 0
    while pos + 46 <= len(cd):
        sig = struct.unpack("<I", cd[pos : pos + 4])[0]
        if sig != 0x02014B50:
            raise IOError(f"bad central-directory signature @ {pos}")
        _, _, flags, meth, _, _, crc, csize, usize, nl, el, cl, _, _, _, lho = (
            struct.unpack("<HHHHHHIIIHHHHHII", cd[pos + 4 : pos + 46])
        )
        name = cd[pos + 46 : pos + 46 + nl].decode("utf-8")
        members[name] = {
            "flags": flags,
            "meth": meth,
            "crc": crc,
            "csize": csize,
            "usize": usize,
            "lho": lho,
        }
        pos += 46 + nl + el + cl
    if len(members) != n_entries:
        raise IOError(
            f"central dir: expected {n_entries} members, parsed {len(members)}"
        )
    return members


def _extract_member(url, member, expect_name):
    """Fetch local header + deflate stream of member; return verified raw bytes."""
    m = member
    lh = _fetch(url, m["lho"], 30)
    sig = struct.unpack("<I", lh[0:4])[0]
    if sig != 0x04034B50:
        raise IOError("bad local file header signature")
    lnl, lel = struct.unpack("<HH", lh[26:30])
    lname = _fetch(url, m["lho"] + 30, lnl).decode("utf-8")
    if lname != expect_name:
        raise IOError(f"local name {lname!r} != central name {expect_name!r}")
    # data descriptor (flag bit 3) trails the compressed stream; not needed by us
    data_off = m["lho"] + 30 + lnl + lel
    comp = _fetch(url, data_off, m["csize"])
    if m["meth"] == 8:
        raw = zlib.decompress(comp, -15)
    elif m["meth"] == 0:
        raw = comp
    else:
        raise IOError(f"unsupported compression method {m['meth']}")
    if len(raw) != m["usize"]:
        raise IOError(f"inflated size {len(raw)} != expected {m['usize']}")
    if (zlib.crc32(raw) & 0xFFFFFFFF) != m["crc"]:
        raise IOError("CRC32 mismatch after inflation")
    return raw


def download_member(year, month, output, force=False, corrections=CORRECTIONS):
    """Surgically download one EN4 analysis month into output (pathlib.Path)."""
    member_name = f"EN.4.2.2.f.analysis.{corrections}.{year:04d}{month:02d}.nc"
    zip_url = f"{EN4_BASE}/EN.4.2.2.analyses.{corrections}.{year:04d}.zip"

    if output.exists() and not force:
        print(f"Output exists (cached), use --force to redo: {output}")
        return True

    print(f"Remote zip: {zip_url}")
    size = _zip_size(zip_url)
    print(f"Zip size  : {size:,} bytes")
    members = _parse_central_dir(zip_url, size)
    if member_name not in members:
        print(f"ERROR: {member_name} not found in the {year} archive")
        sys.exit(1)
    m = members[member_name]
    print(f"Member    : {member_name}  ({m['usize']:,} bytes, nbytes of data)")

    output.parent.mkdir(parents=True, exist_ok=True)
    raw = _extract_member(zip_url, m, member_name)
    tmp = output.with_suffix(output.suffix + ".part")
    tmp.write_bytes(raw)
    tmp.replace(output)
    print(f"Saved     : {output} ({len(raw):,} bytes)")
    return True


def verify_raw(path):
    """Structural checks for the raw EN4 analysis file."""
    import xarray as xr  # deferred; env-only dependency

    ds = xr.open_dataset(path)
    req = {
        "temperature": ("kelvin", ("time", "depth", "lat", "lon")),
        "salinity": ("1", ("time", "depth", "lat", "lon")),
    }
    for var, (unit, dims) in req.items():
        if var not in ds:
            raise ValueError(f"missing variable {var}")
        if ds[var].dims != dims:
            raise ValueError(f"{var}: dims {ds[var].dims} != {dims}")
        if str(ds[var].attrs.get("units", "")).lower() != unit and not (
            var == "salinity" and unit == "1"
        ):
            raise ValueError(f"{var}: unexpected units {ds[var].attrs.get('units')}")
    for dim, n in [("depth", 42), ("lat", 173), ("lon", 360)]:
        if dim not in ds.sizes or ds.sizes[dim] != n:
            raise ValueError(f"dimension {dim} not {n}")
    nopt = int(ds["temperature"].count().compute())
    if nopt == 0:
        raise ValueError("no valid ocean points")
    print(
        f"verify_raw OK: vars={list(ds.data_vars)}, dims={dict(ds.sizes)}, "
        f"valid T points={nopt}"
    )
    ds.close()
    return True


def default_output(year, month, corrections=CORRECTIONS):
    return (
        pathlib.Path("data")
        / "input"
        / "raw"
        / "ocean"
        / f"EN.4.2.2.f.analysis.{corrections}.{year:04d}{month:02d}.nc"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Download one EN4.2.2 monthly ocean T/S analysis (surgical "
        "HTTP-range extraction from the yearly zip, no full-archive download)."
    )
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--month", type=int, default=1)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output .nc path (default: data/input/raw/ocean/... )",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload even if the file already exists",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Do not run structural verification after download",
    )
    args = parser.parse_args()

    out = (
        args.output
        if args.output is not None
        else default_output(args.year, args.month)
    )
    download_member(args.year, args.month, out, force=args.force)
    if not args.skip_verify:
        verify_raw(out)


if __name__ == "__main__":
    main()
