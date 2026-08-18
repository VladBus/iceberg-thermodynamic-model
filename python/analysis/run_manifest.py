#!/usr/bin/env python3
"""Run manifest generator and validator for AARI model output isolation (Stage 6.2).

Each model run lives in data/runs/<run_id>/ with:
  manifest.json        <- this file
  output/nc/           <- results_day_XX.nc
  output/csv/          <- daily_diagnostics.csv, analysis CSVs
  output/txt/          <- reports
  output/logs/         <- run logs
  output/figures/      <- plots

Usage:
  python python/analysis/run_manifest.py --run-id 2020_Q1_test_heat_on
  python python/analysis/run_manifest.py --run-id smoke_test --start 2020-01-01 --days 2
  python python/analysis/run_manifest.py --run-id X --validate

The manifest contains run_id, description, ERA5 period/domain, grid mode,
HEAT/snowfall state, git commit, model configuration and per-day files.
"""

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

RUNS_ROOT = pathlib.Path("data/runs")

# ERA5 Barents research-domain defaults (Stage 6.2). Not the model grid.
DOMAINS = {
    "barents": {
        "name": "barents",
        "north": 90.0,
        "west": 10.0,
        "south": 70.0,
        "east": 70.0,
        "description": "Barents Sea / Svalbard / Franz Josef Land iceberg-source domain",
    },
    "arctic": {
        "name": "arctic",
        "north": 90.0,
        "west": -180.0,
        "south": 65.0,
        "east": 180.0,
        "description": "Historical Arctic-wide strip (pre-Stage 6.2 datasets)",
    },
}


class RunManifest:
    """Represents a single model run with its expected output files."""

    def __init__(
        self,
        run_id: str,
        start_date: str,
        end_date: str,
        expected_days: int,
        file_pattern: str = "results_day_{:02d}.nc",
        base_dir: str = "data/runs/<run_id>/output/nc",
        run_root: pathlib.Path = RUNS_ROOT,
    ):
        self.run_id = run_id
        self.run_root = pathlib.Path(run_root)
        self.run_dir = self.run_root / run_id
        if "<run_id>" in base_dir:
            base_dir = base_dir.replace("<run_id>", run_id)
        self.base_dir = pathlib.Path(base_dir)
        self.start_date = datetime.fromisoformat(start_date)
        self.end_date = datetime.fromisoformat(end_date)
        self.expected_days = expected_days
        self.file_pattern = file_pattern
        self.files: List[Dict[str, Any]] = []
        self.generated_at = datetime.now().isoformat()
        self.meta: Dict[str, Any] = {}

    def generate_file_list(self) -> List[Dict[str, Any]]:
        """Generate expected file list from start_date and expected_days.

        Model semantics: integration day d (1-indexed) corresponds to
        calendar date start_date + d days, because day_00 = initial state
        at start_date, day_01 = after 1 day, etc.
        """
        files = []
        for day in range(1, self.expected_days + 1):
            file_name = self.file_pattern.format(day)
            file_path = self.base_dir / file_name
            # Model integration day d = start_date + d days (day_00 = initial at start_date)
            expected_date = self.start_date + timedelta(days=day)
            files.append(
                {
                    "day": day,
                    "date": expected_date.date().isoformat(),
                    "file": str(file_path),
                    "exists": file_path.exists(),
                }
            )
        return files

    def git_commit(self) -> str:
        try:
            out = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return out.stdout.strip()
        except Exception:
            return "unknown"

    def build(self) -> Dict[str, Any]:
        """Build the complete manifest (including Stage 6.2 metadata)."""
        self.files = self.generate_file_list()
        manifest = {
            "run_id": self.run_id,
            "description": self.meta.get("description", ""),
            "start_date": self.start_date.date().isoformat(),
            "end_date": self.end_date.date().isoformat(),
            "expected_days": self.expected_days,
            "file_pattern": self.file_pattern,
            "base_dir": str(self.base_dir),
            "era5_period": self.meta.get("era5_period", ""),
            "era5_domain": self.meta.get("era5_domain", "arctic"),
            "grid_mode": self.meta.get("grid_mode", "TEST"),
            "heat_state": self.meta.get("heat_state", "off"),
            "snowfall_state": self.meta.get("snowfall_state", "climatology"),
            "model_config": self.meta.get("model_config", {}),
            "git_commit": self.git_commit(),
            "generated_at": self.generated_at,
            "status": self.meta.get("status", "unknown"),
            "files": self.files,
        }
        return manifest

    def save(self, path: pathlib.Path):
        """Save manifest to JSON file."""
        if not self.files:
            self.files = self.generate_file_list()
        manifest = self.build()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2))
        print(f"Manifest saved to {path}")

    @classmethod
    def load(cls, path: pathlib.Path) -> "RunManifest":
        """Load manifest from JSON file."""
        data = json.loads(path.read_text())
        manifest = cls(
            run_id=data["run_id"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            expected_days=data["expected_days"],
            file_pattern=data.get("file_pattern", "results_day_{:02d}.nc"),
            base_dir=data.get("base_dir", "data/runs/<run_id>/output/nc"),
        )
        manifest.files = data.get("files", [])
        manifest.generated_at = data.get("generated_at", datetime.now().isoformat())
        manifest.meta = {
            k: v
            for k, v in data.items()
            if k
            not in (
                "run_id",
                "start_date",
                "end_date",
                "expected_days",
                "file_pattern",
                "base_dir",
                "generated_at",
                "files",
            )
        }
        return manifest

    def validate(self) -> Dict[str, Any]:
        """Validate manifest against actual files."""
        results = {
            "run_id": self.run_id,
            "expected_days": self.expected_days,
            "total_files": len(self.files),
            "missing_files": [],
            "unexpected_files": [],
            "duplicate_days": [],
            "date_mismatches": [],
            "file_size_zero": [],
            "checks_passed": True,
        }

        seen_days = set()
        for f in self.files:
            day = f["day"]
            if day in seen_days:
                results["duplicate_days"].append(day)
                results["checks_passed"] = False
            seen_days.add(day)

            # Check expected date
            # Model integration day d = start_date + d days
            expected_date = (
                (self.start_date + timedelta(days=day)).date().isoformat()
            )
            if f["date"] != expected_date:
                results["date_mismatches"].append(
                    {"day": day, "expected": expected_date, "found": f["date"]}
                )
                results["checks_passed"] = False

            # Check file exists
            if not f["exists"]:
                results["missing_files"].append(day)
                results["checks_passed"] = False
            else:
                # Check file size
                file_path = pathlib.Path(f["file"])
                if file_path.stat().st_size == 0:
                    results["file_size_zero"].append(day)
                    results["checks_passed"] = False

        # Check for missing days
        expected_days_set = set(range(1, self.expected_days + 1))
        found_days_set = set(f["day"] for f in self.files)
        missing = expected_days_set - found_days_set
        if missing:
            results["missing_files"] = sorted(list(missing))
            results["checks_passed"] = False

        # Check for unexpected extra files in directory (final/00 excluded)
        all_nc_files = list(self.base_dir.glob("results_day_*.nc"))
        expected_files = {f["file"] for f in self.files}
        for nc_file in all_nc_files:
            if str(nc_file) not in expected_files and nc_file.name not in (
                "results_day_final.nc",
                "results_day_00.nc",
            ):
                results["unexpected_files"].append(str(nc_file))
                results["checks_passed"] = False

        return results

    def print_validation_report(self, results: Dict[str, Any]):
        """Print validation results."""
        print(f"\n=== Manifest Validation: {self.run_id} ===")
        print(f"Expected days: {results['expected_days']}")
        print(f"Files in manifest: {results['total_files']}")
        print(f"Validation: {'PASS' if results['checks_passed'] else 'FAIL'}")
        print()

        if results["missing_files"]:
            print(f"  MISSING days: {results['missing_files']}")
        if results["duplicate_days"]:
            print(f"  DUPLICATE days: {results['duplicate_days']}")
        if results["date_mismatches"]:
            for m in results["date_mismatches"]:
                print(
                    f"  DATE MISMATCH day {m['day']}: expected {m['expected']}, found {m['found']}"
                )
        if results["file_size_zero"]:
            print(f"  ZERO-SIZE files: {results['file_size_zero']}")
        if results["unexpected_files"]:
            print(f"  UNEXPECTED files: {results['unexpected_files']}")

        if results["checks_passed"]:
            print("  All checks PASSED")
        else:
            print("  Some checks FAILED")


def create_q1_2020_heat_on_manifest() -> RunManifest:
    """Create manifest for Stage 5.5 Q1 2020 HEAT ON run (isolated in data/runs/).

    Model semantics: day_00 = initial state at 2020-01-01.
    Integration days 1..90 produce results_day_01.nc .. results_day_90.nc.
    Calendar date for integration day d = 2020-01-01 + d days.
    So day 1 = 2020-01-02, day 90 = 2020-03-31.
    """
    m = RunManifest(
        run_id="2020_Q1_test_heat_on",
        start_date="2020-01-01",
        end_date="2020-03-31",
        expected_days=90,
        file_pattern="results_day_{:02d}.nc",
        base_dir="data/runs/2020_Q1_test_heat_on/output/nc",
    )
    m.meta.update(
        {
            "description": "Q1 2020 ERA5 + HEAT ON on TEST grid (Jan 1 - Mar 31, 90 integration days)",
            "era5_period": "2020-01-01..2020-03-31 (6-hourly, 364 steps)",
            "era5_domain": "arctic (historical dataset, lat 66-82 / lon 30-63 used by file)",
            "grid_mode": "TEST",
            "heat_state": "on",
            "snowfall_state": "era5_snowfall_rate available; sfal climatology retained",
            "status": "completed",
        }
    )
    return m


def main():
    """Create and/or validate a run manifest."""
    parser = argparse.ArgumentParser(
        description="Run manifest generator/validator (Stage 6.2)"
    )
    parser.add_argument(
        "--run-id", default="2020_Q1_test_heat_on", help="Run identifier"
    )
    parser.add_argument(
        "--start", default=None, help="Start date YYYY-MM-DD (default: run default)"
    )
    parser.add_argument("--days", type=int, default=None, help="Number of model days")
    parser.add_argument(
        "--domain",
        default="arctic",
        help="ERA5 domain key: barents or arctic (metadata only)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate an existing manifest instead of generating",
    )
    args = parser.parse_args()

    manifest_path = RUNS_ROOT / args.run_id / "manifest.json"
    if args.validate:
        if not manifest_path.exists():
            print(f"ERROR: manifest {manifest_path} not found")
            return 1
        manifest = RunManifest.load(manifest_path)
        results = manifest.validate()
        manifest.print_validation_report(results)
        return 0 if results["checks_passed"] else 1

    if args.run_id == "2020_Q1_test_heat_on" and args.start is None:
        manifest = create_q1_2020_heat_on_manifest()
    else:
        start = args.start or "2020-01-01"
        days = args.days or 1
        end = (
            (datetime.fromisoformat(start) + timedelta(days=days - 1))
            .date()
            .isoformat()
        )
        manifest = RunManifest(
            run_id=args.run_id,
            start_date=start,
            end_date=end,
            expected_days=days,
            base_dir=f"data/runs/{args.run_id}/output/nc",
        )
        dom = DOMAINS.get(args.domain, DOMAINS["arctic"])
        manifest.meta.update(
            {
                "description": f"ERA5 {args.domain} smoke/test run (TEST grid)",
                "era5_domain": dom["description"],
                "grid_mode": "TEST",
                "heat_state": "off",
                "snowfall_state": "climatology",
                "status": "planned",
            }
        )

    manifest.build()
    manifest.save(manifest_path)

    # Validate immediately
    results = manifest.validate()
    manifest.print_validation_report(results)

    return 0 if results["checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
