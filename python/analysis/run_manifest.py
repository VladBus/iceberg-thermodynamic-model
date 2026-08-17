#!/usr/bin/env python3
"""Run manifest generator and validator for AARI model output isolation.

Ensures analysis scripts consume exactly the files belonging to a specific run.
"""

import json
import pathlib
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class RunManifest:
    """Represents a single model run with its expected output files."""

    def __init__(self, run_id: str, start_date: str, end_date: str,
                 expected_days: int, file_pattern: str = "results_day_{:02d}.nc",
                 base_dir: str = "data/output"):
        self.run_id = run_id
        self.start_date = datetime.fromisoformat(start_date)
        self.end_date = datetime.fromisoformat(end_date)
        self.expected_days = expected_days
        self.file_pattern = file_pattern
        self.base_dir = pathlib.Path(base_dir)
        self.files: List[Dict[str, Any]] = []
        self.generated_at = datetime.now().isoformat()

    def generate_file_list(self) -> List[Dict[str, Any]]:
        """Generate expected file list from start_date and expected_days."""
        files = []
        current_date = self.start_date
        for day in range(1, self.expected_days + 1):
            file_name = f"results_day_{day:02d}.nc"
            file_path = self.base_dir / file_name
            expected_date = self.start_date + timedelta(days=day - 1)
            files.append({
                "day": day,
                "date": expected_date.date().isoformat(),
                "file": str(file_path),
                "exists": file_path.exists()
            })
        return files

    def build(self) -> Dict[str, Any]:
        """Build the complete manifest."""
        self.files = self.generate_file_list()
        return {
            "run_id": self.run_id,
            "start_date": self.start_date.date().isoformat(),
            "end_date": self.end_date.date().isoformat(),
            "expected_days": self.expected_days,
            "file_pattern": self.file_pattern,
            "base_dir": str(self.base_dir),
            "generated_at": self.generated_at,
            "files": self.files
        }

    def save(self, path: pathlib.Path):
        """Save manifest to JSON file."""
        # Use existing files if they exist, otherwise generate
        if not self.files:
            self.files = self.generate_file_list()
        manifest = {
            "run_id": self.run_id,
            "start_date": self.start_date.date().isoformat(),
            "end_date": self.end_date.date().isoformat(),
            "expected_days": self.expected_days,
            "file_pattern": self.file_pattern,
            "base_dir": str(self.base_dir),
            "generated_at": self.generated_at,
            "files": self.files
        }
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
            base_dir=data.get("base_dir", "data/output")
        )
        manifest.files = data.get("files", [])
        manifest.generated_at = data.get("generated_at", datetime.now().isoformat())
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
            "checks_passed": True
        }

        seen_days = set()
        for f in self.files:
            day = f["day"]
            if day in seen_days:
                results["duplicate_days"].append(day)
                results["checks_passed"] = False
            seen_days.add(day)

            # Check expected date
            expected_date = (self.start_date + timedelta(days=day - 1)).date().isoformat()
            if f["date"] != expected_date:
                results["date_mismatches"].append({
                    "day": day,
                    "expected": expected_date,
                    "found": f["date"]
                })
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

        # Check for unexpected extra files in directory
        all_nc_files = list(self.base_dir.glob("results_day_*.nc"))
        expected_files = {f["file"] for f in self.files}
        for nc_file in all_nc_files:
            if str(nc_file) not in expected_files and nc_file.name not in ("results_day_final.nc", "results_day_00.nc"):
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
                print(f"  DATE MISMATCH day {m['day']}: expected {m['expected']}, found {m['found']}")
        if results["file_size_zero"]:
            print(f"  ZERO-SIZE files: {results['file_size_zero']}")
        if results["unexpected_files"]:
            print(f"  UNEXPECTED files: {results['unexpected_files']}")

        if results["checks_passed"]:
            print("  All checks PASSED")
        else:
            print("  Some checks FAILED")


def create_q1_2020_heat_on_manifest() -> RunManifest:
    """Create manifest for Stage 5.5 Q1 2020 HEAT ON run."""
    return RunManifest(
        run_id="2020_Q1_HEAT_ON",
        start_date="2020-01-01",
        end_date="2020-03-30",
        expected_days=90,
        file_pattern="results_day_{:02d}.nc",
        base_dir="data/output"
    )


def main():
    """Create and validate the Stage 5.5 Q1 2020 manifest."""
    manifest = create_q1_2020_heat_on_manifest()
    manifest.build()

    # Save manifest
    manifest_path = pathlib.Path("data/output/run_manifest_2020_Q1_HEAT_ON.json")
    manifest.save(manifest_path)

    # Validate
    results = manifest.validate()
    manifest.print_validation_report(results)

    return 0 if results["checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())