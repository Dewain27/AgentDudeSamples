#!/usr/bin/env python3
"""Security-critical suite: the contribution payload must not leak.

Author: Dewain Robinson

`contribute.py` sends data to a PUBLIC repository, permanently. A merged
record cannot be recalled from git history. These tests exist to prove that
the payload is built by allowlist -- copying named fields into a fresh object
-- rather than by redaction, so a field added to the ledger later cannot leak
by someone forgetting to strip it.

Written and passing before contribute.py was wired to `gh`, per the design
spec's implementation sequence.
"""

__author__ = "Dewain Robinson"

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skill", "build-work-estimator", "scripts"))

import contribute  # noqa: E402


#: A ledger entry deliberately stuffed with things that must never escape.
POISONED_ENTRY = {
    "estimate_id": "est_20260903T101500_a1b2c3",
    "generated": "2026-09-03T10:15:00Z",
    "project": "Contoso Confidential Merger Platform",
    "manifest": {
        "project": "Contoso Confidential Merger Platform",
        "reserve_percent": 25,
        "client_contact": "jane.doe@contoso.example",
        "internal_rate_card": {"opus": 3.10},
        "items": [{"name": "Secret dispatch API", "size": "medium",
                   "files": 9, "unknowns": 2, "brownfield": True}],
    },
    "predicted": {
        "base": 1234.56,
        "low": 400.00,
        "high": 4567.89,
        "budget_ask": 1543.20,
        "items": [{"name": "Secret dispatch API", "size": "medium",
                   "bucket": "medium", "files": 9, "unknowns": 2,
                   "brownfield": True, "turns": 431, "cost": 1234.56}],
    },
    "profile_source": "measured",
    "actual": {
        "sessions": ["9f8e7d6c-5b4a-3210-fedc-ba9876543210"],
        "actual_turns": 604,
        "actual_cost": 1728.99,
        "actual_files": 11,
        "estimated_turns": 431,
        "estimated_cost": 1234.56,
        "turn_ratio": 1.4014,
        "cost_ratio": 1.4004,
    },
    # A field nobody anticipated, added by a later version.
    "future_field_nobody_stripped": "/home/example-user/clients/acme/secret.md",
}

PROFILE = {
    "source": "measured",
    "cache_hit_rate": 0.983,
    "model_mix": {"claude-opus-5": 0.61, "claude-sonnet-5": 0.39},
}

#: Substrings that must never appear anywhere in a serialized contribution.
FORBIDDEN = [
    "Contoso", "contoso", "Confidential", "Merger",
    "jane.doe", "example",
    "Secret dispatch", "secret.md",
    "/home/example-user", "example-user",
    "9f8e7d6c", "5b4a-3210",
    "est_20260903T101500", "a1b2c3",
    "1234.56", "1728.99", "4567.89", "1543.20", "3.10", "400.0",
    "future_field_nobody_stripped",
    "2026-09-03", "10:15",
]


class TestAllowlist(unittest.TestCase):
    def setUp(self):
        self.record = contribute.build_record(POISONED_ENTRY, PROFILE)
        self.text = contribute.render_record(self.record)

    def test_field_set_is_exactly_the_allowlist(self):
        self.assertEqual(sorted(self.record), sorted(contribute.ALLOWLIST))

    def test_no_forbidden_substring_survives(self):
        for needle in FORBIDDEN:
            self.assertNotIn(
                needle, self.text,
                "%r leaked into the contribution payload:\n%s"
                % (needle, self.text))

    def test_unexpected_input_field_is_dropped(self):
        self.assertNotIn("future_field_nobody_stripped", self.record)
        for value in self.record.values():
            self.assertNotIn("secret.md", str(value))

    def test_no_dollar_amounts(self):
        # Costs can expose negotiated rates; ratios carry the signal instead.
        for key, value in self.record.items():
            self.assertNotIn("cost", key)
            self.assertNotIn("dollar", key)
            if isinstance(value, float):
                self.assertLess(
                    value, 100.0,
                    "%s=%r looks like a currency amount" % (key, value))

    def test_date_is_month_precision_only(self):
        self.assertRegex(str(self.record["contributed"]), r"^\d{4}-\d{2}$")

    def test_carries_the_useful_signal(self):
        self.assertEqual(self.record["size"], "medium")
        self.assertEqual(self.record["estimated_turns"], 431)
        self.assertEqual(self.record["actual_turns"], 604)
        self.assertAlmostEqual(self.record["ratio"], 1.4014, places=3)
        self.assertTrue(self.record["brownfield"])

    def test_cache_hit_rate_is_banded_not_exact(self):
        self.assertEqual(self.record["cache_hit_rate_band"], "95-100")
        self.assertNotIn("98.3", self.text)

    def test_model_tier_is_a_family_not_a_model_id(self):
        self.assertIn(self.record["model_tier"],
                      ("opus", "sonnet", "haiku", "mixed", "unknown"))
        self.assertNotIn("claude-opus-5", self.text)


class TestConsent(unittest.TestCase):
    def test_declined_consent_writes_nothing_and_submits_nothing(self):
        calls = []
        result = contribute.submit(
            POISONED_ENTRY, PROFILE,
            confirm=lambda text: False,
            runner=lambda argv: calls.append(argv),
            out_dir=None,
        )
        self.assertEqual(result["status"], "declined")
        self.assertEqual(calls, [], "nothing may be executed without consent")
        self.assertIsNone(result.get("path"))

    def test_consent_prompt_shows_the_complete_payload(self):
        shown = {}

        def confirm(text):
            shown["text"] = text
            return False

        contribute.submit(POISONED_ENTRY, PROFILE, confirm=confirm,
                          runner=lambda argv: None, out_dir=None)
        for key in contribute.ALLOWLIST:
            self.assertIn(key, shown["text"],
                          "consent prompt must show every field, missing %r" % key)

    def test_no_default_yes(self):
        # An empty answer is not consent.
        self.assertFalse(contribute.interpret_consent(""))
        self.assertFalse(contribute.interpret_consent("\n"))
        self.assertFalse(contribute.interpret_consent("y"))
        self.assertFalse(contribute.interpret_consent("yes"))
        self.assertTrue(contribute.interpret_consent(contribute.CONSENT_PHRASE))

    def test_missing_actual_is_refused(self):
        entry = dict(POISONED_ENTRY)
        entry["actual"] = None
        with self.assertRaises(contribute.ContributeError):
            contribute.build_record(entry, PROFILE)


class TestBanding(unittest.TestCase):
    def test_bands(self):
        cases = [(0.0, "0-50"), (0.49, "0-50"), (0.62, "50-75"),
                 (0.80, "75-90"), (0.93, "90-95"), (0.983, "95-100"),
                 (1.0, "95-100")]
        for value, expected in cases:
            self.assertEqual(contribute.band_cache_hit_rate(value), expected)

    def test_model_tier_from_mix(self):
        self.assertEqual(contribute.model_tier({"claude-opus-5": 0.9}), "opus")
        self.assertEqual(contribute.model_tier({"claude-sonnet-5": 0.8}), "sonnet")
        self.assertEqual(
            contribute.model_tier({"claude-opus-5": 0.5,
                                   "claude-sonnet-5": 0.5}), "mixed")
        self.assertEqual(contribute.model_tier({}), "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
