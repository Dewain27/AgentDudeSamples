#!/usr/bin/env python3
"""The instructions that stop a session ending in "ready to execute".

Author: Dewain Robinson

A real GitHub Copilot session collected every input across three rounds of
questions and then produced nothing, answering "run it now" with "Estimate run
is ready to execute". Four defects in the instructions caused it, and this
suite pins each one so it cannot quietly return.

These check SKILL.md text rather than behaviour, which is a real limit: they
prove the instruction is present, not that a model followed it. That is worth
having anyway -- every one of these failures traced to an instruction that was
absent or wrong, not to an instruction that was ignored.
"""

__author__ = "Dewain Robinson"

import os
import unittest

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))
SKILL = os.path.join(SAMPLE, "skill", "build-work-estimator", "SKILL.md")


def skill_text():
    with open(SKILL) as fh:
        return fh.read()


class TestDoneMeansTheReportExists(unittest.TestCase):
    """The failure that wasted the whole session."""

    def test_the_skill_says_announcing_is_not_running(self):
        t = skill_text()
        self.assertIn("Announcing that you are ready to run the estimate is "
                      "not running it", t)

    def test_the_failure_phrases_are_named_explicitly(self):
        """Naming the exact phrases beats describing the failure abstractly."""
        t = skill_text()
        for phrase in ("Ready to execute", "settings locked"):
            self.assertIn(phrase, t)

    def test_completion_is_defined_as_files_produced(self):
        t = skill_text()
        self.assertIn("Done means the report exists", t)
        self.assertIn("an estimate is a file", t)

    def test_it_says_run_in_the_same_turn(self):
        t = skill_text()
        self.assertIn("same turn you finish collecting them", t)

    def test_a_collecting_conversation_with_no_file_is_called_a_failure(self):
        t = skill_text()
        self.assertIn("produces no file has failed", t)


class TestTheBreakdownIsNotOptional(unittest.TestCase):
    """The false comment that hid the most important input."""

    def test_github_copilot_is_not_told_to_skip_items(self):
        t = skill_text()
        self.assertNotIn("github-copilot uses this instead of items", t,
                         "this claim is false -- estimate.py derives "
                         "interactions FROM items -- and it is why a real "
                         "session never asked for the work breakdown")

    def test_the_skill_says_both_platforms_use_items(self):
        t = skill_text()
        self.assertIn("ALSO uses items", t)
        self.assertIn("DERIVED from the same breakdown", t)

    def test_interactions_are_documented_as_derived(self):
        """Proving the doc matches the code it describes."""
        import estimate  # noqa: F401
        source = open(os.path.join(
            SAMPLE, "skill", "build-work-estimator", "scripts",
            "estimate.py")).read()
        self.assertIn('gh_cfg["interactions"] = sizing["total_turns"]', source,
                      "if this derivation goes away, the SKILL.md claim that "
                      "items drive a GitHub build stops being true")


class TestItReadsTheSpecification(unittest.TestCase):
    def test_the_skill_says_to_open_the_specification(self):
        t = skill_text()
        self.assertIn("open it before asking them anything", t)

    def test_it_drafts_a_breakdown_from_the_specification(self):
        t = skill_text()
        self.assertIn("draft the **work breakdown**", t)

    def test_the_draft_must_be_confirmed_not_assumed(self):
        t = skill_text()
        self.assertIn("ask the user to correct it", t)
        self.assertIn("not a measurement", t)

    def test_it_is_told_to_include_operating_work(self):
        """The omission class the researcher gate actually found."""
        t = skill_text()
        self.assertIn("recovery, load testing, key management, residency", t)


class TestItAsksOnce(unittest.TestCase):
    def test_the_skill_requires_a_single_round(self):
        t = skill_text()
        self.assertIn("ONE message", t)
        self.assertIn("not one at a time", t)

    def test_defaults_are_offered_for_what_can_be_defaulted(self):
        t = skill_text()
        self.assertIn("Offer a sensible default", t)

    def test_reserve_percent_is_never_defaulted(self):
        t = skill_text()
        self.assertIn("No default. Required, always ask.", t)

    def test_it_must_not_ask_what_the_specification_answers(self):
        t = skill_text()
        self.assertIn("Never ask for something the specification already "
                      "answers", t)


class TestItChallengesAnImplausibleRate(unittest.TestCase):
    def test_the_skill_says_to_sanity_check_a_declared_rate(self):
        t = skill_text()
        self.assertIn("Sanity-check a declared rate before you use it", t)

    def test_it_must_not_invent_a_replacement_figure(self):
        t = skill_text()
        self.assertIn("must not invent a figure to replace", t)

    def test_it_points_at_the_published_source(self):
        t = skill_text()
        self.assertIn("docs.github.com/en/copilot/get-started/plans", t)

    def test_the_stakes_are_stated(self):
        t = skill_text()
        self.assertIn("no reserve covers", t)


class TestDraftedSizesAreDisclosed(unittest.TestCase):
    """A drafted size and an authored one are different claims."""

    def setUp(self):
        import estimate
        import render_report as rr
        from test_estimate import PROFILE, manifest
        self.estimate, self.rr = estimate, rr
        self.PROFILE, self.manifest = PROFILE, manifest

    def test_absent_means_authored(self):
        result = self.estimate.compute_plan(self.manifest(), self.PROFILE)
        self.assertEqual(result["breakdown_source"], "authored")

    def test_a_drafted_breakdown_is_recorded(self):
        m = self.manifest()
        m["breakdown_source"] = "drafted"
        result = self.estimate.compute_plan(m, self.PROFILE)
        self.assertEqual(result["breakdown_source"], "drafted")

    def test_a_drafted_breakdown_is_visible_in_the_report(self):
        m = self.manifest()
        m["breakdown_source"] = "drafted"
        md = self.rr.build_markdown(
            self.estimate.compute_plan(m, self.PROFILE))
        self.assertIn("drafted from the specification", md)
        self.assertIn("weaker than an authored breakdown", md)

    def test_an_authored_breakdown_makes_no_claim(self):
        md = self.rr.build_markdown(
            self.estimate.compute_plan(self.manifest(), self.PROFILE))
        self.assertNotIn("drafted from the specification", md)

    def test_an_unknown_source_is_refused(self):
        import specification as spec_mod
        with self.assertRaises(spec_mod.SpecificationError):
            spec_mod.normalise_breakdown_source("guessed")

    def test_disclosure_changes_no_figure(self):
        m = self.manifest()
        m["breakdown_source"] = "drafted"
        self.assertEqual(
            self.estimate.compute_plan(self.manifest(),
                                       self.PROFILE)["totals"],
            self.estimate.compute_plan(m, self.PROFILE)["totals"],
            "how the breakdown was produced is a confidence signal, not an "
            "input to the arithmetic")


if __name__ == "__main__":
    unittest.main(verbosity=2)
