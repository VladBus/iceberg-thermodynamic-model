"""Run-context resolution for Stage 6.2 run-based analysis.

Every analysis/plotting script must accept either a --run-id or --manifest
argument and resolve the run directory. This module centralizes that logic:

    from run_context import resolve_run, RunContext

    ctx = resolve_run(run_id="2020_Q1_test_heat_on")   # or manifest=Path(...)
    ctx.nc_dir    # data/runs/<run_id>/output/nc
    ctx.csv_dir   # data/runs/<run_id>/output/csv
    ctx.txt_dir   # data/runs/<run_id>/output/txt
    ctx.log_dir   # data/runs/<run_id>/output/logs
    ctx.fig_dir   # data/runs/<run_id>/output/figures
    ctx.manifest  # pathlib.Path to manifest.json
    ctx.daily_diagnostics  # pathlib.Path to daily_diagnostics.csv

Rules (AGENTS.md 8b): never glob data/runs/*/output/nc without run
identification. Always resolve through this module.
"""

import json
import pathlib
import sys

RUNS_ROOT = pathlib.Path("data/runs")


class RunContext:
    """Resolved paths for one isolated model run."""

    def __init__(self, run_id: str, run_dir: pathlib.Path, manifest: pathlib.Path,
                 meta: dict = None):
        self.run_id = run_id
        self.run_dir = pathlib.Path(run_dir)
        self.manifest = pathlib.Path(manifest)
        self.nc_dir = self.run_dir / "output" / "nc"
        self.csv_dir = self.run_dir / "output" / "csv"
        self.txt_dir = self.run_dir / "output" / "txt"
        self.log_dir = self.run_dir / "output" / "logs"
        self.fig_dir = self.run_dir / "output" / "figures"
        self.meta = meta or {}
        self.daily_diagnostics = self.csv_dir / "daily_diagnostics.csv"
        self.guard_events = self.csv_dir / "convective_guard_events.csv"

    def __repr__(self):
        return f"RunContext(run_id={self.run_id!r}, dir={self.run_dir})"


def load_manifest_meta(manifest_path: pathlib.Path) -> dict:
    """Load manifest JSON metadata (non-file keys)."""
    if not pathlib.Path(manifest_path).exists():
        return {}
    try:
        data = json.loads(pathlib.Path(manifest_path).read_text())
    except Exception:
        return {}
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k != "files"}
    return {}


def _from_manifest(manifest_path) -> RunContext:
    mpath = pathlib.Path(manifest_path)
    if not mpath.exists():
        raise FileNotFoundError(f"manifest not found: {mpath}")
    meta = load_manifest_meta(mpath)
    run_id = meta.get("run_id") or mpath.parent.name
    run_dir = mpath.parent
    return RunContext(run_id, run_dir, mpath, meta)


def _from_run_id(run_id: str) -> RunContext:
    run_dir = RUNS_ROOT / run_id
    if not run_dir.exists():
        raise FileNotFoundError(
            f"run directory not found: {run_dir}. Create it with "
            f"`python python/analysis/run_manifest.py --run-id {run_id}` "
            f"or run the model with `fpm run -- {run_id}`.")
    mpath = run_dir / "manifest.json"
    meta = load_manifest_meta(mpath)
    return RunContext(run_id, run_dir, mpath, meta)


def resolve_run(run_id=None, manifest=None) -> RunContext:
    """Resolve a RunContext from run_id or manifest path. One is required."""
    if manifest is not None:
        return _from_manifest(manifest)
    if run_id is not None:
        return _from_run_id(run_id)
    # Fallback: newest run by manifest timestamp (explicit, logged).
    runs = sorted(RUNS_ROOT.glob("*/manifest.json"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        raise FileNotFoundError(
            "no runs found in data/runs/. Pass --run-id or --manifest explicitly.")
    print(f"NOTE: no --run-id given; using newest run {runs[0].parent.name}")
    return _from_manifest(runs[0])


def add_run_args(parser, default_run_id=None):
    """Add --run-id and --manifest arguments to an argparse parser."""
    parser.add_argument("--run-id", default=default_run_id,
                        help="Run identifier (data/runs/<run_id>). Default: newest run.")
    parser.add_argument("--manifest", default=None,
                        help="Path to run manifest.json (overrides --run-id).")
    return parser


def main():
    """CLI: print resolved run paths for a given run."""
    parser = __import__("argparse").ArgumentParser(
        description="Resolve a run directory from --run-id or --manifest.")
    add_run_args(parser)
    args = parser.parse_args()
    try:
        ctx = resolve_run(run_id=args.run_id, manifest=args.manifest)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"run_id      : {ctx.run_id}")
    print(f"run_dir     : {ctx.run_dir}")
    print(f"nc_dir      : {ctx.nc_dir}")
    print(f"csv_dir     : {ctx.csv_dir}")
    print(f"txt_dir     : {ctx.txt_dir}")
    print(f"log_dir     : {ctx.log_dir}")
    print(f"fig_dir     : {ctx.fig_dir}")
    print(f"manifest    : {ctx.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())