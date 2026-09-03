#!/usr/bin/env python3
"""Actuals: ledger round-trip, ratios, shrinkage, attribution safety.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import json
import os
import shutil
import tempfile
import unittest

import _fixtures  # noqa: E402
import calibrate  # noqa: E402
import estimate  # noqa: E402
import record_actual as ra  # noqa: E402

PROFILE = {
    "source": "measured", "sessions": 3, "cost_per_main_turn": 0.40,
    "subagent_multiplier": 1.0, "corrections": {},
    "buckets": [{"label": "medium", "n": 6, "median_turns": 40,
                 "median_cost": 16.0, "min_cost": 4.0, "max_cost": 60.0}],
}

MANIFEST = {
    "project": "Fixture build", "reserve_percent": 20,
    "build_stack": "claude-code",
    "licensing": {"model": "consumption"},
    "items": [{"name": "thing", "size": "medium", "files": 9, "unknowns": 0}],
}


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.root = os.path.join(self.dir, "projects")
        os.makedirs(self.root)
        _fixtures.simple_history(self.root)
        self.ledger = os.path.join(self.dir, "ledger.json")
        self.profile = os.path.join(self.dir, "profile.json")
        calibrate.save_profile(dict(PROFILE), self.profile)

        self.result = estimate.compute(MANIFEST, PROFILE)
        estimate.append_ledger(self.result, MANIFEST, self.ledger)
        self.eid = self.result["estimate_id"]

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestRecording(Base):
    def test_records_actual_and_computes_ratio(self):
        out = ra.record(self.eid, ["11111111-1111-1111-1111-111111111111"],
                        root=self.root, ledger_file=self.ledger,
                        profile_file=self.profile)
        actual = out["entry"]["actual"]
        self.assertEqual(actual["actual_turns"], 40)
        self.assertEqual(actual["estimated_turns"], 40)
        self.assertAlmostEqual(actual["turn_ratio"], 1.0, places=3)
        self.assertGreater(actual["actual_cost"], 0)

    def test_unknown_estimate_id_is_rejected_and_lists_known(self):
        with self.assertRaises(ra.RecordError) as ctx:
            ra.record("est_nope", ["11111111-1111-1111-1111-111111111111"],
                      root=self.root, ledger_file=self.ledger,
                      profile_file=self.profile)
        self.assertIn(self.eid, str(ctx.exception))

    def test_unknown_session_id_is_rejected(self):
        with self.assertRaises(ra.RecordError):
            ra.record(self.eid, ["does-not-exist"], root=self.root,
                      ledger_file=self.ledger, profile_file=self.profile)

    def test_multiple_sessions_are_summed(self):
        out = ra.record(self.eid,
                        ["11111111-1111-1111-1111-111111111111",
                         "22222222-2222-2222-2222-222222222222"],
                        root=self.root, ledger_file=self.ledger,
                        profile_file=self.profile)
        self.assertEqual(out["entry"]["actual"]["actual_turns"], 55)

    def test_corrections_written_to_profile(self):
        ra.record(self.eid, ["11111111-1111-1111-1111-111111111111",
                             "22222222-2222-2222-2222-222222222222"],
                  root=self.root, ledger_file=self.ledger,
                  profile_file=self.profile)
        with open(self.profile) as fh:
            saved = json.load(fh)
        self.assertIn("medium", saved["corrections"])
        self.assertEqual(saved["corrections"]["medium"]["n"], 1)

    def test_single_actual_is_provisional_not_applied(self):
        out = ra.record(self.eid, ["11111111-1111-1111-1111-111111111111"],
                        root=self.root, ledger_file=self.ledger,
                        profile_file=self.profile)
        self.assertFalse(out["corrections"]["medium"]["applied"])
        self.assertIn("Provisional", ra.render(out))

    def test_two_actuals_become_applied(self):
        ra.record(self.eid, ["11111111-1111-1111-1111-111111111111"],
                  root=self.root, ledger_file=self.ledger,
                  profile_file=self.profile)
        second = estimate.compute(MANIFEST, PROFILE)
        estimate.append_ledger(second, MANIFEST, self.ledger)
        out = ra.record(second["estimate_id"],
                        ["22222222-2222-2222-2222-222222222222"],
                        root=self.root, ledger_file=self.ledger,
                        profile_file=self.profile)
        self.assertEqual(out["corrections"]["medium"]["n"], 2)
        self.assertTrue(out["corrections"]["medium"]["applied"])


class TestAttribution(Base):
    def test_candidates_are_offered_not_assumed(self):
        sessions = calibrate.collect(self.root)
        entry = ra.find_estimate(ra.load_ledger(self.ledger), self.eid)
        candidates = ra.candidate_sessions(sessions, entry["generated"])
        # Fixture history predates the estimate, so nothing auto-qualifies.
        self.assertIsInstance(candidates, list)

    def test_cli_refuses_to_guess_without_confirmation(self):
        code = ra.main([self.eid, "--root", self.root, "--ledger", self.ledger,
                        "--profile", self.profile])
        # Either no candidates (error) or candidates listed awaiting --sessions;
        # in neither case does it silently attribute.
        self.assertEqual(code, 1)
        with open(self.ledger) as fh:
            ledger = json.load(fh)
        self.assertIsNone(ledger["estimates"][0]["actual"])


class TestShrinkageIntegration(Base):
    def test_recorded_ratio_feeds_future_estimates_shrunk(self):
        ra.record(self.eid, ["11111111-1111-1111-1111-111111111111",
                             "22222222-2222-2222-2222-222222222222"],
                  root=self.root, ledger_file=self.ledger,
                  profile_file=self.profile)
        second = estimate.compute(MANIFEST, PROFILE)
        estimate.append_ledger(second, MANIFEST, self.ledger)
        ra.record(second["estimate_id"],
                  ["33333333-3333-3333-3333-333333333333"],
                  root=self.root, ledger_file=self.ledger,
                  profile_file=self.profile)

        corrected_profile = calibrate.load_profile(self.profile)
        plain = estimate.compute(MANIFEST, PROFILE)
        corrected = estimate.compute(MANIFEST, corrected_profile)
        entry = corrected_profile["corrections"]["medium"]
        raw = entry["median_ratio"]
        applied = corrected["base"] / plain["base"]
        if abs(raw - 1.0) > 0.01:
            self.assertLess(abs(applied - 1.0), abs(raw - 1.0),
                            "correction must be shrunk toward 1.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
