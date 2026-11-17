"""Stage 12.21 layout/label checks (unittest, conda env)."""
from __future__ import annotations
import importlib.util, tempfile, unittest
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("s1221", ROOT / "python/analysis/stage12.21_forcing_figures.py")
S = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(S)


class Stage1221(unittest.TestCase):
    def test_english_labels(self):
        S.set_lang("en")
        self.assertEqual(S.L("days"), "days")
        self.assertEqual(S.L("grounding"), "grounding")
        self.assertEqual(S.L("melt"), "melt-out")
        S.set_lang("ru")
        self.assertEqual(S.L("days"), "сутки")
        S.set_lang("en")

    def test_white_border(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "w.png"; Image.new("RGB", (40, 30), "white").save(p); S.check_png(p)
            Image.new("RGB", (40, 30), "black").save(p)
            with self.assertRaises(RuntimeError): S.check_png(p)

    def test_regions(self):
        self.assertIn("BARENTS", S.REGIONS)
        self.assertEqual(len(S.RUNS), 6)


if __name__ == "__main__": unittest.main()
