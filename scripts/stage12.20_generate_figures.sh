#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
python3 - <<'PY'
import importlib.util
spec=importlib.util.spec_from_file_location('f','python/analysis/stage12.20_figures.py')
f=importlib.util.module_from_spec(spec); spec.loader.exec_module(f)
f.main_all()
PY
