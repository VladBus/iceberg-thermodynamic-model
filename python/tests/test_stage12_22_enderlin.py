"""Stage 12.22 metric, provenance, and layout checks (no model runs)."""
from __future__ import annotations
import importlib.util
import json
import re
import zipfile
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "s1222", ROOT / "python/analysis/stage12.22_enderlin_validation.py")
S = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(S)
FIG = ROOT / "docs/wiki/stages/stage12/figures/stage12.22"
EVID = ROOT / "docs/wiki/stages/stage12/evidence/stage12.22"


class Stage1222Metrics(unittest.TestCase):
    def test_density_matches_fortran(self):
        src = (ROOT / "src/iceberg_types.f90").read_text()
        m = re.search(r"RHO_ICE\s*=\s*([0-9.]+)", src)
        self.assertIsNotNone(m)
        self.assertEqual(float(m.group(1)), 910.0)
        self.assertEqual(S.RHO_ICE, 910.0)
        future = (ROOT / "python/validation/enderlin23_hindcast.py").read_text()
        self.assertRegex(future, r"RHO_ICE\s*=\s*910\.0")

    def test_model_rate_from_components(self):
        # 910 * 100 m2 * 86400 s of ice loss → exactly 1 m/day.
        rate = S.submarine_rate(910.0 * 100.0, 0.0, 0.0, 100.0, 86400.0)
        self.assertAlmostEqual(float(rate), 1.0)
        old = 910.0 * 100.0 / (916.7 * 100.0 * 86400.0) * 86400.0
        corrected = 910.0 * 100.0 / (910.0 * 100.0 * 86400.0) * 86400.0
        self.assertLess(old, corrected)

    def test_bias_ratio_and_centered_error(self):
        obs = np.array([1.0, 2.0, 4.0, 8.0])
        mod = np.array([.5, 1.0, 4.0, 16.0])
        s, _, _, _ = S.base_stats(obs, mod, np.full(4, .1))
        self.assertEqual(s["n"], 4)
        self.assertAlmostEqual(s["bias"], np.mean(mod - obs))
        self.assertAlmostEqual(s["median_ratio"], .75)
        self.assertAlmostEqual(s["sigma_model_over_obs"],
                               np.std(mod, ddof=1) / np.std(obs, ddof=1))
        self.assertAlmostEqual(s["crmse_over_sigma_obs"],
                               np.sqrt(np.mean(((mod - mod.mean()) - (obs - obs.mean())) ** 2))
                               / np.std(obs, ddof=1))

    def test_linear_and_log_metrics(self):
        obs = np.array([1.0, 2.0, 4.0, 8.0])
        mod = np.array([.5, 1.0, 4.0, 16.0])
        s, _, _, _ = S.base_stats(obs, mod, np.full(4, .1))
        self.assertAlmostEqual(s["pearson_log10"], np.corrcoef(np.log10(mod), np.log10(obs))[0, 1])
        self.assertAlmostEqual(s["mean_log10_ratio"], np.mean(np.log10(mod / obs)))

    def test_cluster_bootstrap(self):
        o = np.array([1., 2., 3., 4., 5., 6.])
        m = np.array([.5, 1., 2., 3., 4., 5.])
        groups = ["a", "a", "b", "b", "c", "c"]
        r = S.bootstrap_stats(o, m, np.full(6, .1), groups, seed=1, nboot=50)
        self.assertEqual(r["n_groups"], 3)
        self.assertEqual(r["ci_status"], "ok")
        self.assertIn("ci_low_median_ratio", r)

    def test_single_group_has_no_fake_ci(self):
        o = np.array([1., 2., 3.]); m = np.array([.5, 1., 2.]); s = np.array([.1, .1, .1])
        r = S.bootstrap_stats(o, m, s, ["one", "one", "one"], seed=1, nboot=10)
        self.assertEqual(r["ci_status"], "single_cluster")
        self.assertNotIn("ci_low_bias", r)

    def test_reliability_formula(self):
        obs = np.array([1., 2., 4., 8.])
        sig = np.array([.1, .2, .4, .8])
        expected = np.sqrt(max(0., 1. - np.mean(sig ** 2) / np.var(obs, ddof=1)))
        self.assertAlmostEqual(S.noise_ceiling(obs, sig, False), expected)
        sig_log = sig / (obs * np.log(10.0))
        expected_log = np.sqrt(max(0., 1. - np.mean(sig_log ** 2)
                                     / np.var(np.log10(obs), ddof=1)))
        self.assertAlmostEqual(S.noise_ceiling(obs, sig, True), expected_log)
        self.assertEqual(S.noise_ceiling(obs, np.zeros(4), False), 1.0)

    def test_negative_taylor_coordinates(self):
        x, y = S.taylor_xy(-.5, .8)
        self.assertLess(float(x), 0.0)
        self.assertGreater(float(y), 0.0)
        obs = np.array([1., 2., 4., 8.])
        s, _, _, _ = S.base_stats(obs, obs[::-1], np.full(4, .1))
        self.assertLess(s["pearson_log10"], 0.0)

    def test_no_titles_in_script(self):
        src = (ROOT / "python/analysis/stage12.22_enderlin_validation.py").read_text()
        self.assertNotIn(".set_title", src)


class Stage1222Artifacts(unittest.TestCase):
    def test_matched_table_and_metric_consistency(self):
        d = pd.read_csv(EVID / "matched_cases.csv")
        self.assertEqual(len(d), 190)
        self.assertTrue(np.allclose(d.model_rate, S.submarine_rate(
            d.mass_loss_basal_voxel, d.mass_loss_lateral_voxel,
            d.mass_loss_wave_voxel, d.mean_a_wet_voxel, d.seconds_voxel)))
        self.assertAlmostEqual(float(np.median(d.model_rate / d.obs_rate)), .5437118, places=5)
        m = pd.read_csv(EVID / "metrics.csv")
        q = m[(m.stratum == "All") & (m.metric == "median_ratio")].iloc[0]
        self.assertAlmostEqual(float(q.value), .5437118, places=5)
        self.assertFalse(np.isnan(float(q.ci_low)))

    def test_manifest_and_all_pngs(self):
        man = pd.read_csv(FIG / "figures_manifest.csv")
        self.assertEqual(len(man), 6)
        self.assertEqual(set(man.figure), {"T1", "T2", "B1", "B2", "B3", "B4"})
        for _, r in man.iterrows():
            self.assertTrue((ROOT / r.png).is_file())
            self.assertTrue((ROOT / r.png).stat().st_size > 1000)
            self.assertIn("journal_pdf_vectors.zip::", r.pdf)

    def test_pdf_zip(self):
        p = ROOT / "data/validation/stage12.22/journal_pdf_vectors.zip"
        self.assertTrue(p.is_file())
        with zipfile.ZipFile(p) as z:
            names = set(z.namelist())
        self.assertEqual(names, {"T1_taylor_log10.pdf", "T2_taylor_linear.pdf",
                                 "B1_scatter_loglog.pdf", "B2_ratio_distribution.pdf",
                                 "B3_bias_diagnostics.pdf", "B4_group_means.pdf"})

    def test_stage0_and_region_ci_status(self):
        j = json.loads((EVID / "stage0_recon.json").read_text())
        self.assertEqual(j["hindcast_cases"], 190)
        self.assertEqual(j["independent_groups"], 7)
        self.assertEqual(j["early_stop_cases"], 0)
        self.assertEqual(j["observations_independent_true"], 743)
        r = pd.read_csv(EVID / "metrics_by_region.csv")
        wais = r[(r.stratum == "WAIS") & (r.metric == "bias")].iloc[0]
        self.assertEqual(wais.ci_status, "single_cluster")
        self.assertTrue(np.isnan(float(wais.ci_low)))

    def test_report_reflects_density_and_reliability(self):
        text = (ROOT / "docs/wiki/stages/stage12/stage12.22_enderlin_taylor_bias.md").read_text()
        self.assertIn("0.5437", text)
        self.assertIn("−0.02177", text)
        self.assertIn("0.8843", text)
        self.assertNotIn("916.7 kg", text)


if __name__ == "__main__":
    unittest.main()
