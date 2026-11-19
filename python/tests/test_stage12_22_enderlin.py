"""Stage 12.22 metric-definition checks (no model runs)."""
from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "s1222", ROOT / "python/analysis/stage12.22_enderlin_validation.py")
S = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(S)


class Stage1222Metrics(unittest.TestCase):
    def test_bias_ratio_and_centered_error(self):
        obs = np.array([1.0, 2.0, 4.0, 8.0])
        mod = np.array([.5, 1.0, 4.0, 16.0])
        sig = np.full(4, .1)
        s, o, m, g = S.base_stats(obs, mod, sig)
        self.assertEqual(s["n"], 4)
        self.assertAlmostEqual(s["bias"], np.mean(mod - obs))
        self.assertAlmostEqual(s["median_ratio"], 0.75)
        self.assertAlmostEqual(s["sigma_model_over_obs"],
                               np.std(mod, ddof=1) / np.std(obs, ddof=1))
        self.assertAlmostEqual(s["crmse_over_sigma_obs"],
                               np.sqrt(np.mean(((mod - mod.mean()) - (obs - obs.mean())) ** 2))
                               / np.std(obs, ddof=1))

    def test_log_metrics_are_space_specific(self):
        obs = np.array([1.0, 2.0, 4.0, 8.0])
        mod = np.array([.5, 1.0, 4.0, 16.0])
        s, _, _, _ = S.base_stats(obs, mod, np.full(4, .1))
        self.assertAlmostEqual(s["pearson_log10"], np.corrcoef(np.log10(mod), np.log10(obs))[0, 1])
        self.assertAlmostEqual(s["mean_log10_ratio"], np.mean(np.log10(mod / obs)))

    def test_single_cluster_has_no_bootstrap_ci(self):
        o = np.array([1., 2., 3.]); m = np.array([.5, 1., 2.]); s = np.array([.1, .1, .1])
        r = S.bootstrap_stats(o, m, s, ["one", "one", "one"], seed=1, nboot=10)
        self.assertEqual(r["ci_status"], "single_cluster")
        self.assertEqual(r["n_groups"], 1)
        self.assertNotIn("ci_low_bias", r)


if __name__ == "__main__":
    unittest.main()
