#!/usr/bin/env python3
"""A research review is declared by a human, never inferred by the estimator.

Author: Dewain Robinson

The estimator cannot tell whether a breakdown was challenged. It records that
someone says it was, and it says plainly that it is recording a claim rather
than verifying one -- because the alternative is a report that implies
diligence nobody performed.
"""

__author__ = "Dewain Robinson"

import os
import sys
import unittest

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))

import estimate  # noqa: E402
import render_report as rr  # noqa: E402
import specification as spec_mod  # noqa: E402
from test_estimate import PROFILE, manifest  # noqa: E402

REVIEW = {
    "reviewed": "2026-09-04",
    "findings_total": 7,
    "findings_addressed": 4,
    "findings_accepted_as_is": 1,
}


class TestNormalise(unittest.TestCase):
    def test_absent_is_allowed(self):
        self.assertEqual(spec_mod.normalise_review(None),
                         {"declared": False})

    def test_a_declared_review_is_recorded(self):
        out = spec_mod.normalise_review(dict(REVIEW))
        self.assertTrue(out["declared"])
        self.assertEqual(out["findings_total"], 7)
        self.assertEqual(out["findings_addressed"], 4)
        self.assertEqual(out["findings_accepted_as_is"], 1)

    def test_open_findings_are_derived_not_declared(self):
        out = spec_mod.normalise_review(dict(REVIEW))
        self.assertEqual(out["findings_open"], 2)

    def test_addressed_plus_accepted_cannot_exceed_total(self):
        bad = dict(REVIEW, findings_addressed=6, findings_accepted_as_is=6)
        with self.assertRaises(spec_mod.SpecificationError):
            spec_mod.normalise_review(bad)

    def test_negative_counts_are_refused(self):
        with self.assertRaises(spec_mod.SpecificationError):
            spec_mod.normalise_review(dict(REVIEW, findings_total=-1))

    def test_a_non_numeric_count_is_refused(self):
        with self.assertRaises(spec_mod.SpecificationError):
            spec_mod.normalise_review(dict(REVIEW, findings_total="several"))


class TestReporting(unittest.TestCase):
    def test_absence_is_reported_not_silent(self):
        md = spec_mod.render_review_markdown({"declared": False})
        self.assertIn("No research review is recorded", md)
        self.assertIn("available improvement", md)

    def test_a_declared_review_is_labelled_as_declared(self):
        md = spec_mod.render_review_markdown(
            spec_mod.normalise_review(dict(REVIEW)))
        self.assertIn("declared", md.lower())
        self.assertIn("cannot judge how", md)

    def test_open_findings_are_called_out(self):
        md = spec_mod.render_review_markdown(
            spec_mod.normalise_review(dict(REVIEW)))
        self.assertIn("Still open", md)
        self.assertIn("known to be", md)

    def test_the_estimator_never_infers_a_review(self):
        """No review block means no review, however complete the manifest."""
        result = estimate.compute_plan(manifest(), PROFILE)
        self.assertEqual(result["research_review"], {"declared": False})

    def test_a_declared_review_reaches_the_report(self):
        m = manifest()
        m["research_review"] = dict(REVIEW)
        result = estimate.compute_plan(m, PROFILE)
        self.assertTrue(result["research_review"]["declared"])
        md = rr.build_markdown(result)
        self.assertIn("Was the breakdown challenged?", md)

    def test_a_report_without_a_review_still_asks_the_question(self):
        md = rr.build_markdown(estimate.compute_plan(manifest(), PROFILE))
        self.assertIn("Was the breakdown challenged?", md)
        self.assertIn("No research review is recorded", md)


class TestReviewChangesNoArithmetic(unittest.TestCase):
    """Recording a review must not move a single figure."""

    def test_totals_are_identical_with_and_without_a_review(self):
        without = estimate.compute_plan(manifest(), PROFILE)
        m = manifest()
        m["research_review"] = dict(REVIEW)
        with_review = estimate.compute_plan(m, PROFILE)
        self.assertEqual(without["totals"], with_review["totals"],
                         "a declared review is a confidence signal, not an "
                         "input to the arithmetic")


if __name__ == "__main__":
    unittest.main(verbosity=2)
