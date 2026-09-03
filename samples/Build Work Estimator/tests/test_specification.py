#!/usr/bin/env python3
"""The estimator always asks what the estimate was sized from.

Author: Dewain Robinson

An estimate without a specification behind it is sizing from vibes. The
question may be answered `none` -- early estimates are legitimate and useful --
but it may not go unanswered, because an unanswered question is
indistinguishable in the output from a build that rested on agreed scope.
"""

__author__ = "Dewain Robinson"

import os
import sys
import unittest

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(SAMPLE, "build"))

import estimate  # noqa: E402
import miniyaml  # noqa: E402
import regenerate_examples as regen  # noqa: E402
import render_report as rr  # noqa: E402
import specification as spec  # noqa: E402
from test_estimate import PROFILE, manifest  # noqa: E402


class TestAlwaysAsked(unittest.TestCase):
    def test_block_is_required(self):
        m = manifest()
        del m["specification"]
        with self.assertRaises(estimate.EstimateError) as ctx:
            estimate.compute_plan(m, PROFILE)
        message = str(ctx.exception)
        self.assertIn("specification is required", message)
        self.assertIn("sizing from", message)

    def test_both_halves_must_be_answered(self):
        for missing in ("functional", "technical"):
            cfg = {"functional": "a", "technical": "b", "status": "draft"}
            del cfg[missing]
            with self.assertRaises(spec.SpecificationError) as ctx:
                spec.normalise(cfg)
            self.assertIn("specification.%s is required" % missing,
                          str(ctx.exception))

    def test_none_is_an_acceptable_answer(self):
        out = spec.normalise({"functional": "none", "technical": "none"})
        self.assertTrue(out["absent"])
        self.assertEqual(out["status"], "none")

    def test_there_is_no_skip_flag(self):
        with open(os.path.join(SAMPLE, "skill", "build-work-estimator",
                               "scripts", "specification.py")) as fh:
            source = fh.read()
        for flag in ("--skip-spec", "skip_specification", "no_specification"):
            self.assertNotIn(flag, source)

    def test_interview_asks_for_both(self):
        asked = []

        def prompt(text):
            asked.append(text)
            return "none"

        spec.interview(prompt=prompt, echo=lambda *a: None)
        joined = " ".join(asked).lower()
        self.assertIn("functional specification", joined)
        self.assertIn("technical specification", joined)


class TestStatusAndConfidence(unittest.TestCase):
    def test_confidence_ladder(self):
        for status, confidence in (("approved", "high"),
                                   ("in-review", "medium"),
                                   ("draft", "low")):
            out = spec.normalise({"functional": "a", "technical": "b",
                                  "status": status})
            self.assertEqual(out["confidence"], confidence)
        self.assertEqual(
            spec.normalise({"functional": "none",
                            "technical": "none"})["confidence"], "very low")

    def test_status_none_with_a_specification_is_rejected(self):
        with self.assertRaises(spec.SpecificationError):
            spec.normalise({"functional": "a", "technical": "b",
                            "status": "none"})

    def test_status_set_without_a_specification_is_rejected(self):
        with self.assertRaises(spec.SpecificationError):
            spec.normalise({"functional": "none", "technical": "none",
                            "status": "approved"})

    def test_unknown_status_rejected(self):
        with self.assertRaises(spec.SpecificationError):
            spec.normalise({"functional": "a", "technical": "b",
                            "status": "vibes"})

    def test_half_a_specification_is_flagged_incomplete(self):
        out = spec.normalise({"functional": "a", "technical": "none",
                              "status": "draft"})
        self.assertFalse(out["complete"])
        self.assertFalse(out["absent"])


class TestReporting(unittest.TestCase):
    def test_absent_specification_produces_a_prominent_warning(self):
        m = manifest()
        m["specification"] = {"functional": "none", "technical": "none"}
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("NO SPECIFICATION", md)
        self.assertIn("informed guess", md)
        self.assertIn("write the specification", md)

    def test_present_specification_is_recorded_verbatim(self):
        m = manifest()
        m["specification"] = {"functional": "docs/functional-v3.md",
                              "technical": "docs/technical-v3.md",
                              "status": "approved"}
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("docs/functional-v3.md", md)
        self.assertIn("docs/technical-v3.md", md)
        self.assertIn("Confidence in sizing | **high**", md)

    def test_draft_specification_warns_about_movement(self):
        m = manifest()
        m["specification"] = {"functional": "a", "technical": "b",
                              "status": "draft"}
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("specification is a draft", md)

    def test_partial_specification_warns(self):
        m = manifest()
        m["specification"] = {"functional": "a", "technical": "none",
                              "status": "draft"}
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("Only one half was provided", md)

    def test_summary_records_confidence(self):
        md = rr.build_markdown(estimate.compute_plan(manifest(), PROFILE))
        self.assertIn("| Specification |", md)
        self.assertIn("confidence in sizing", md.lower())


class TestShippedManifestsDeclareOne(unittest.TestCase):
    def _manifest_path(self, run):
        return os.path.join(run.get("dir", os.path.join(SAMPLE, "examples")),
                            run["manifest"])

    def test_every_shipped_manifest_declares_a_specification(self):
        checked = 0
        for run in list(regen.SCENARIOS) + list(regen.SCENARIO_RUNS):
            data = miniyaml.load_path(self._manifest_path(run))
            self.assertIn("specification", data,
                          "%s does not say what it was sized from"
                          % run["manifest"])
            spec.normalise(data["specification"])
            checked += 1
        self.assertGreaterEqual(checked, 4)

    def test_the_kestrel_scenario_cites_its_own_specification(self):
        for run in regen.SCENARIO_RUNS:
            block = miniyaml.load_path(
                self._manifest_path(run))["specification"]
            self.assertIn("specification.md", block["functional"])
            self.assertIn("specification.md", block["technical"])
            self.assertEqual(block["status"], "approved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
