#!/usr/bin/env python3
"""Calibration correctness: dedup, cache pricing, bucketing, resilience.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import json
import os
import shutil
import sys
import tempfile
import unittest

import _fixtures  # noqa: F401  (sets sys.path to the scripts dir)
import calibrate  # noqa: E402
import rates  # noqa: E402


class TestPricing(unittest.TestCase):
    def test_cache_tiers_priced_distinctly(self):
        # 1M tokens of each kind on Opus 5 ($5 in / $25 out).
        self.assertAlmostEqual(
            rates.price_response("claude-opus-5", 1000000, 0, 0, 0, 0), 5.00, 6)
        self.assertAlmostEqual(
            rates.price_response("claude-opus-5", 0, 1000000, 0, 0, 0), 0.50, 6)
        self.assertAlmostEqual(
            rates.price_response("claude-opus-5", 0, 0, 1000000, 0, 0), 6.25, 6)
        self.assertAlmostEqual(
            rates.price_response("claude-opus-5", 0, 0, 0, 1000000, 0), 10.00, 6)
        self.assertAlmostEqual(
            rates.price_response("claude-opus-5", 0, 0, 0, 0, 1000000), 25.00, 6)

    def test_unknown_model_returns_none_rather_than_guessing(self):
        self.assertIsNone(rates.price_response("gpt-9", 1000, 0, 0, 0, 10))
        self.assertIsNone(rates.rate_for("some-unknown-model"))

    def test_prefix_match_handles_dated_ids(self):
        self.assertEqual(rates.rate_for("claude-haiku-4-5-20251001"), (1.0, 5.0))


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        _fixtures.simple_history(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_finds_all_sessions_including_subagents(self):
        sessions = calibrate.collect(self.root)
        self.assertEqual(len(sessions), 3)
        medium = sessions["11111111-1111-1111-1111-111111111111"]
        self.assertEqual(medium["turns"], 40)
        self.assertEqual(medium["sub_turns"], 12)
        self.assertGreater(medium["sub_cost"], 0)

    def test_deduplicates_by_request_id(self):
        path = os.path.join(self.root, "-proj-b",
                            "33333333-3333-3333-3333-333333333333.jsonl")
        with open(path, "a") as fh:
            # Same requestId twice -- one API response, two transcript records.
            fh.write(json.dumps(_fixtures.assistant("e0")) + "\n")
        sessions = calibrate.collect(self.root)
        self.assertEqual(
            sessions["33333333-3333-3333-3333-333333333333"]["turns"], 8)

    def test_corrupt_line_is_skipped_not_fatal(self):
        path = os.path.join(self.root, "-proj-b",
                            "33333333-3333-3333-3333-333333333333.jsonl")
        with open(path, "a") as fh:
            fh.write("{not json at all\n")
            fh.write("\n")
        sessions = calibrate.collect(self.root)
        self.assertEqual(
            sessions["33333333-3333-3333-3333-333333333333"]["turns"], 8)

    def test_unknown_model_counted_not_priced(self):
        _fixtures.write_session(
            self.root, "-proj-c", "44444444-4444-4444-4444-444444444444",
            [_fixtures.assistant("z1", model="mystery-model-9")])
        sessions = calibrate.collect(self.root)
        entry = sessions.get("44444444-4444-4444-4444-444444444444")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["unpriced"], 1)
        self.assertEqual(entry["turns"], 0)


class TestProfile(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        _fixtures.simple_history(self.root)
        self.profile = calibrate.build_profile(calibrate.collect(self.root))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_is_measured_with_sane_shape(self):
        self.assertEqual(self.profile["source"], "measured")
        self.assertEqual(self.profile["sessions"], 3)
        self.assertGreater(self.profile["cost_per_main_turn"], 0)
        self.assertGreaterEqual(self.profile["subagent_multiplier"], 1.0)
        self.assertTrue(0 < self.profile["cache_hit_rate"] <= 1.0)

    def test_buckets_assigned_by_files_touched(self):
        labels = dict((b["label"], b) for b in self.profile["buckets"])
        self.assertIn("medium", labels)       # 9 distinct files
        self.assertIn("small", labels)        # 3 distinct files
        self.assertIn("exploration", labels)  # no edits
        self.assertEqual(labels["exploration"]["n"], 1)

    def test_bucket_boundaries(self):
        self.assertEqual(calibrate.bucket_for(0), "exploration")
        self.assertEqual(calibrate.bucket_for(1), "trivial")
        self.assertEqual(calibrate.bucket_for(5), "small")
        self.assertEqual(calibrate.bucket_for(6), "medium")
        self.assertEqual(calibrate.bucket_for(15), "medium")
        self.assertEqual(calibrate.bucket_for(16), "large")
        self.assertEqual(calibrate.bucket_for(500), "subsystem")

    def test_no_paths_or_project_names_in_profile(self):
        blob = json.dumps(self.profile)
        self.assertNotIn("/f/", blob)
        self.assertNotIn("proj-a", blob)
        self.assertNotIn("11111111", blob)


class TestFallback(unittest.TestCase):
    def test_empty_history_yields_published_baseline(self):
        root = tempfile.mkdtemp()
        try:
            profile = calibrate.build_profile(calibrate.collect(root))
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(profile["source"], "published-baseline")
        self.assertEqual(profile["sessions"], 0)
        self.assertTrue(profile["buckets"])
        self.assertIn("baseline_source", profile)

    def test_corrections_survive_recalibration(self):
        directory = tempfile.mkdtemp()
        try:
            path = os.path.join(directory, "profile.json")
            first = calibrate.fallback_profile()
            first["corrections"] = {"medium": {"n": 4, "median_ratio": 1.3}}
            calibrate.save_profile(first, path)

            fresh = calibrate.fallback_profile()
            self.assertEqual(fresh["corrections"], {})
            calibrate.save_profile(fresh, path)

            reloaded = calibrate.load_profile(path)
            self.assertEqual(reloaded["corrections"]["medium"]["n"], 4)
        finally:
            shutil.rmtree(directory, ignore_errors=True)


class TestStaleness(unittest.TestCase):
    def test_warns_only_when_past_the_window(self):
        self.assertEqual(rates.staleness_warnings("2026-09-03"), [])
        warnings = rates.staleness_warnings("2027-09-03")
        self.assertTrue(warnings)
        self.assertTrue(any("Copilot Credits" in w for w in warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
