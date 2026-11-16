"""Layout checks used by Stage 12.20 figures (unittest, conda env)."""
from __future__ import annotations
import importlib.util, tempfile, unittest
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("s1220", ROOT / "python/analysis/stage12.20_figures.py")
S = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(S)


class Stage1220Layout(unittest.TestCase):
    def test_white_border(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "w.png"; Image.new("RGB", (40, 30), "white").save(p); S.check_png(p)
            Image.new("RGB", (40, 30), "black").save(p)
            with self.assertRaises(RuntimeError): S.check_png(p)

    def test_gif_frames(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.gif"; a = Image.new("RGB", (32, 32), "white"); b = Image.new("RGB", (32, 32), "black")
            a.save(p, save_all=True, append_images=[b], duration=100, loop=0, optimize=False); self.assertEqual(S.check_gif(p), 2)
            self.assertTrue(S.check_gif(p) >= 2)

    def test_axes3_ticks(self):
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig = plt.figure(); ax = fig.add_subplot(111, projection="3d")
        S.axes3(ax, 24, 24, 24, 100.0)
        self.assertEqual(len(ax.get_xticks()), 5)
        ax.clear(); S.axes3(ax, 24, 24, 24, 50.0)
        self.assertEqual(len(ax.get_xticks()), 3)
        plt.close(fig)

    def test_simple_text_figure(self):
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        with tempfile.TemporaryDirectory() as d:
            fig, ax = plt.subplots(figsize=(3, 2)); ax.set_title("ok"); ax.plot([0, 1], [0, 1]); ax.set_axis_off()
            out = Path(d) / "simple.png"; fig.subplots_adjust(left=.25, right=.75, top=.75, bottom=.25)
            fig.savefig(out); S.check_png(out); S.check_text(fig, out); plt.close(fig)


if __name__ == "__main__": unittest.main()
