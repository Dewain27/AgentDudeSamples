#!/usr/bin/env python3
"""Estimate model: required reserve, adequacy flag, ranges, corrections.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import copy
import os
import shutil
import sys
import tempfile
import unittest

import _fixtures  # noqa: F401
import calibrate  # noqa: E402
import estimate  # noqa: E402

PROFILE = {
    "source": "measured",
    "sessions": 12,
    "generated": "2026-02-20T00:00:00Z",
    "date_range": ["2026-02-01", "2026-02-20"],
    "cost_per_main_turn": 0.40,
    "subagent_multiplier": 1.2,
    "corrections": {},
    "buckets": [
        {"label": "exploration", "n": 5, "median_turns": 34,
         "median_cost": 3.50, "min_cost": 0.75, "max_cost": 190.0},
        {"label": "small", "n": 4, "median_turns": 190,
         "median_cost": 42.0, "min_cost": 27.0, "max_cost": 153.0},
        {"label": "medium", "n": 6, "median_turns": 430,
         "median_cost": 140.0, "min_cost": 4.0, "max_cost": 466.0},
        {"label": "large", "n": 2, "median_turns": 990,
         "median_cost": 450.0, "min_cost": 146.0, "max_cost": 1506.0},
    ],
}

MANIFEST = {
    "project": "Harbor Line dispatch",
    "reserve_percent": 25,
    "specification": {"functional": "fixture spec",
                      "technical": "fixture spec",
                      "status": "approved"},
    "build_platform": "claude-code",
    "target_platform": "copilot-studio",
    "licensing": {"model": "consumption", "plan": "Claude Console"},
    "target": {"harness": "github-copilot", "eval_test_cases": 10,
               "eval_cycles": 1, "interactive_test_hours": 2},
    "items": [{"name": "Dispatch API", "size": "medium", "files": 9,
               "unknowns": 2, "brownfield": False}],
}


def manifest(**overrides):
    m = copy.deepcopy(MANIFEST)
    m.update(overrides)
    return m


class TestReserveRequired(unittest.TestCase):
    def test_missing_reserve_is_rejected(self):
        m = manifest()
        del m["reserve_percent"]
        with self.assertRaises(estimate.EstimateError) as ctx:
            estimate.compute(m, PROFILE)
        self.assertIn("reserve_percent is required", str(ctx.exception))

    def test_none_reserve_is_rejected(self):
        with self.assertRaises(estimate.EstimateError):
            estimate.compute(manifest(reserve_percent=None), PROFILE)

    def test_zero_reserve_is_allowed(self):
        result = estimate.compute(manifest(reserve_percent=0), PROFILE)
        self.assertEqual(result["reserve"], 0.0)
        self.assertEqual(result["budget_ask"], result["base"])

    def test_out_of_range_rejected(self):
        for bad in (-1, 501):
            with self.assertRaises(estimate.EstimateError):
                estimate.compute(manifest(reserve_percent=bad), PROFILE)

    def test_non_numeric_rejected(self):
        with self.assertRaises(estimate.EstimateError):
            estimate.compute(manifest(reserve_percent="lots"), PROFILE)

    def test_there_is_no_skip_flag(self):
        import argparse
        parser_actions = []

        real = argparse.ArgumentParser.add_argument

        def spy(self, *a, **kw):
            parser_actions.append(a[0] if a else "")
            return real(self, *a, **kw)

        argparse.ArgumentParser.add_argument = spy
        try:
            try:
                estimate.main(["--manifest", "/nonexistent.yaml"])
            except SystemExit:
                pass
        finally:
            argparse.ArgumentParser.add_argument = real
        for flag in parser_actions:
            self.assertNotIn("skip", str(flag))


class TestModel(unittest.TestCase):
    def test_base_uses_turns_rate_and_subagent_multiplier(self):
        result = estimate.compute(manifest(), PROFILE)
        # 430 turns x $0.40 x 1.2
        self.assertAlmostEqual(result["base"], 430 * 0.40 * 1.2, places=2)

    def test_brownfield_scales_turns(self):
        plain = estimate.compute(manifest(), PROFILE)
        brown = manifest()
        brown["items"][0]["brownfield"] = True
        scaled = estimate.compute(brown, PROFILE)
        self.assertAlmostEqual(
            scaled["base"] / plain["base"], estimate.BROWNFIELD_FACTOR, places=3)

    def test_range_is_monotonic_in_unknowns(self):
        highs = []
        for unknowns in range(0, 4):
            m = manifest()
            m["items"][0]["unknowns"] = unknowns
            highs.append(estimate.compute(m, PROFILE)["high"])
        self.assertEqual(highs, sorted(highs))
        self.assertGreater(highs[-1], highs[0])

    def test_multi_item_range_sums_rather_than_multiplying_ratios(self):
        m = manifest()
        m["items"] = [
            {"name": "a", "size": "small", "files": 3, "unknowns": 0},
            {"name": "b", "size": "small", "files": 3, "unknowns": 0},
        ]
        one = manifest()
        one["items"] = [{"name": "a", "size": "small", "files": 3,
                         "unknowns": 0}]
        single = estimate.compute(one, PROFILE)
        double = estimate.compute(m, PROFILE)
        self.assertAlmostEqual(double["high"], single["high"] * 2, places=2)
        self.assertAlmostEqual(double["low"], single["low"] * 2, places=2)

    def test_thin_buckets_flagged(self):
        m = manifest()
        m["items"] = [{"name": "big", "size": "large", "files": 30,
                       "unknowns": 0}]
        result = estimate.compute(m, PROFILE)
        self.assertIn("large", result["thin_buckets"])

    def test_unknown_size_rejected(self):
        m = manifest()
        m["items"][0]["size"] = "enormous"
        with self.assertRaises(estimate.EstimateError):
            estimate.compute(m, PROFILE)

    def test_estimate_id_is_unique_and_sortable(self):
        a = estimate.new_estimate_id()
        b = estimate.new_estimate_id()
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("est_"))


class TestAdequacy(unittest.TestCase):
    def test_flags_when_reserve_does_not_cover_high(self):
        result = estimate.compute(manifest(reserve_percent=25), PROFILE)
        adequacy = result["adequacy"]
        self.assertFalse(adequacy["covers_high"])
        self.assertGreater(adequacy["required_percent"],
                           adequacy["reserve_percent"])

    def test_satisfied_when_reserve_is_large_enough(self):
        result = estimate.compute(manifest(reserve_percent=400), PROFILE)
        self.assertTrue(result["adequacy"]["covers_high"])

    def test_required_percent_would_actually_cover(self):
        result = estimate.compute(manifest(reserve_percent=25), PROFILE)
        needed = result["adequacy"]["required_percent"]
        retried = estimate.compute(manifest(reserve_percent=needed), PROFILE)
        self.assertTrue(retried["adequacy"]["covers_high"])


class TestCorrections(unittest.TestCase):
    def test_shrinkage_curve(self):
        self.assertAlmostEqual(estimate.shrunk_ratio(2.0, 0), 1.0, 4)
        self.assertAlmostEqual(estimate.shrunk_ratio(2.0, 1), 1.25, 4)
        self.assertAlmostEqual(estimate.shrunk_ratio(2.0, 3), 1.5, 4)
        self.assertAlmostEqual(estimate.shrunk_ratio(2.0, 9), 1.75, 4)
        self.assertGreater(estimate.shrunk_ratio(2.0, 100), 1.9)

    def test_single_actual_is_not_applied(self):
        profile = copy.deepcopy(PROFILE)
        profile["corrections"] = {"medium": {"n": 1, "median_ratio": 2.0}}
        plain = estimate.compute(manifest(), PROFILE)
        with_one = estimate.compute(manifest(), profile)
        self.assertAlmostEqual(with_one["base"], plain["base"], places=2)
        self.assertFalse(with_one["corrections"][0]["applied"])

    def test_two_actuals_apply_shrunk_not_raw(self):
        profile = copy.deepcopy(PROFILE)
        profile["corrections"] = {"medium": {"n": 2, "median_ratio": 2.0}}
        plain = estimate.compute(manifest(), PROFILE)
        corrected = estimate.compute(manifest(), profile)
        ratio = corrected["base"] / plain["base"]
        self.assertAlmostEqual(ratio, estimate.shrunk_ratio(2.0, 2), places=3)
        self.assertLess(ratio, 2.0, "raw ratio must not be applied undiluted")


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "ledger.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_estimate_is_appended(self):
        result = estimate.compute(manifest(), PROFILE)
        estimate.append_ledger(result, manifest(), self.path)
        import json
        with open(self.path) as fh:
            ledger = json.load(fh)
        self.assertEqual(len(ledger["estimates"]), 1)
        entry = ledger["estimates"][0]
        self.assertEqual(entry["estimate_id"], result["estimate_id"])
        self.assertIsNone(entry["actual"])


class TestFallbackProfileWorks(unittest.TestCase):
    def test_estimate_runs_on_published_baseline(self):
        profile = calibrate.fallback_profile()
        result = estimate.compute(manifest(), profile)
        self.assertGreater(result["base"], 0)
        self.assertEqual(result["profile"]["source"], "published-baseline")


if __name__ == "__main__":
    unittest.main(verbosity=2)
