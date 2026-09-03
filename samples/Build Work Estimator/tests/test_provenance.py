#!/usr/bin/env python3
"""No number ships unless the estimator can say where it came from.

Author: Dewain Robinson

The rule: a figure may appear in a report only if its derivation is recorded.
Not "it looks about right" -- an actual derivation, traceable to measured
session history, a published rate carrying a source URL, a value declared in
the manifest, or arithmetic on those.

Enforcement is mechanical. The ledger is built from the computed result and the
rendered report is checked against it. This suite proves the check works, and
proves it can fail -- a validator that always passes is not a validator.
"""

__author__ = "Dewain Robinson"

import json
import os
import subprocess
import sys
import tempfile
import unittest

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(SAMPLE, "skill", "build-work-estimator", "scripts")
sys.path.insert(0, os.path.join(SAMPLE, "build"))

import assumptions  # noqa: E402
import estimate  # noqa: E402
import regenerate_examples as regen  # noqa: E402
import render_report as rr  # noqa: E402
from test_estimate import PROFILE, manifest  # noqa: E402


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.result = estimate.compute_plan(manifest(), PROFILE)
        self.book = assumptions.ledger(self.result)

    def test_every_computed_figure_is_recorded(self):
        totals = self.result["totals"]
        for section in ("build", "target", "combined"):
            for value in totals[section].values():
                if isinstance(value, (int, float)) \
                        and not isinstance(value, bool):
                    self.assertIn(round(float(value), 2), self.book,
                                  "%s figure %r is not in the ledger"
                                  % (section, value))

    def test_published_rates_are_recorded_as_origins(self):
        import rates
        self.assertIn(round(rates.DOLLARS_PER_CREDIT, 2), self.book)
        self.assertIn(round(rates.ANTHROPIC_RATES["claude-opus-5"][0], 2),
                      self.book)

    def test_judgment_factors_are_recorded_as_origins(self):
        self.assertIn(round(estimate.BROWNFIELD_FACTOR, 2), self.book)
        self.assertIn(round(estimate.REMEDIATION_SHARE, 2), self.book)

    def test_ledger_names_where_each_value_came_from(self):
        for paths in self.book.values():
            self.assertTrue(paths, "a ledger entry with no origin is useless")


class TestValidatorCatchesUntraceableFigures(unittest.TestCase):
    """A validator that cannot fail is not a validator."""

    def setUp(self):
        self.result = estimate.compute_plan(manifest(), PROFILE)
        self.md = rr.build_markdown(self.result)

    def test_a_clean_report_validates(self):
        self.assertEqual(assumptions.validate(self.md, self.result), [])

    def test_an_invented_money_figure_is_caught(self):
        tampered = self.md + "\n\nTotal: $987,654.32\n"
        problems = assumptions.validate(tampered, self.result)
        self.assertTrue(problems, "an invented figure must be rejected")
        self.assertIn("987,654.32", problems[0])

    def test_an_invented_grouped_number_is_caught(self):
        tampered = self.md + "\n\nCredits: 8,675,309\n"
        problems = assumptions.validate(tampered, self.result)
        self.assertTrue(problems)
        self.assertIn("8,675,309", problems[0])

    def test_a_figure_one_away_from_a_recorded_value_is_caught(self):
        """The defect this replaced: a +/- 1.0 window on grouped numbers.

        An off-by-a-bit computed figure is exactly what the check exists to
        catch, and a tolerance window let it through. Matching is now exact at
        the precision each figure renders to.
        """
        # Use the money path: the grouped regex requires a thousands
        # separator, which the small fixture's totals do not have.
        value = self.result["totals"]["combined"]["likely"]
        nudged = self.md + "\n\n$%s\n" % format(value + 1.0, ",.2f")
        problems = assumptions.validate(nudged, self.result)
        self.assertTrue(problems,
                        "a figure one away from a recorded value must fail")
        self.assertIn(format(value + 1.0, ",.2f"), problems[0])

    def test_a_figure_one_cent_away_is_caught(self):
        value = self.result["totals"]["combined"]["likely"]
        nudged = self.md + "\n\n$%s\n" % format(value + 0.01, ",.2f")
        self.assertTrue(assumptions.validate(nudged, self.result),
                        "money matching is exact at two places")

    def test_a_figure_matching_at_render_precision_passes(self):
        # 44311.96 renders as "44,312" at zero places; that IS the figure.
        value = self.result["totals"]["combined"]["likely"]
        rendered = self.md + "\n\n$%s\n" % format(value, ",.2f")
        self.assertEqual(assumptions.validate(rendered, self.result), [])

    def test_there_is_no_tolerance_window(self):
        source = open(os.path.join(SCRIPTS, "assumptions.py")).read()
        self.assertNotIn("tolerance=1.0", source)
        self.assertNotIn("abs(value - known)", source,
                         "a window comparison is what let near-misses pass")


class TestCoverageIsStatedNotAsserted(unittest.TestCase):
    """The limit of the check is reported, not glossed over."""

    def setUp(self):
        self.result = estimate.compute_plan(manifest(), PROFILE)
        self.md = rr.build_markdown(self.result)

    def test_coverage_reports_what_was_checked(self):
        cov = assumptions.coverage(self.md, self.result)
        self.assertGreater(cov["money_figures_checked"], 0)
        self.assertEqual(cov["problems"], 0)

    def test_coverage_names_what_it_cannot_verify(self):
        cov = assumptions.coverage(self.md, self.result)
        self.assertEqual(cov["verifies"], "value provenance")
        self.assertIn("field provenance", cov["does_not_verify"])

    def test_the_report_states_the_limit(self):
        self.assertIn("does **not** verify", self.md)
        self.assertIn("wrong label would pass", self.md)
        self.assertIn("different defect", self.md)

    def test_the_report_states_there_is_no_tolerance(self):
        self.assertIn("no tolerance window", self.md)
        self.assertIn("exact at the precision", self.md)


class TestEveryShippedReportValidates(unittest.TestCase):
    """The guarantee has to hold on what actually ships, not just fixtures."""

    def _run(self, scenario):
        out = tempfile.mkdtemp()
        payload = os.path.join(out, "e.json")
        home = scenario.get("dir", os.path.join(SAMPLE, "examples"))
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "estimate.py"),
             "--manifest", os.path.join(home, scenario["manifest"]),
             "--profile", regen.PROFILE, "--no-ledger", "--out", payload],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(payload) as fh:
            return json.load(fh)

    def test_all_shipped_runs_have_fully_traceable_figures(self):
        for scenario in list(regen.SCENARIOS) + list(regen.SCENARIO_RUNS):
            result = self._run(scenario)
            problems = assumptions.validate(
                rr.build_markdown(result), result)
            self.assertEqual(
                problems, [],
                "%s contains figures the estimator cannot account for:\n  %s"
                % (scenario["name"], "\n  ".join(problems)))

    def test_reports_state_the_guarantee(self):
        result = estimate.compute_plan(manifest(), PROFILE)
        md = rr.build_markdown(result)
        self.assertIn("Provenance of every figure", md)
        self.assertIn("Nothing in this report is asserted without a "
                      "derivation", md)

    def test_a_failed_validation_is_stated_not_hidden(self):
        problems = ["$1.00 appears in the report but the estimator cannot "
                    "say where it came from"]
        rendered = assumptions.render_provenance({}, problems)
        self.assertIn("VALIDATION FAILED", rendered)
        self.assertNotIn("Nothing in this report is asserted without",
                         rendered)


class TestRendererDoesNotCompute(unittest.TestCase):
    """The renderer displays recorded values; the estimator computes them."""

    def test_totals_are_recorded_on_the_result(self):
        result = estimate.compute_plan(manifest(), PROFILE)
        self.assertIn("totals", result)
        for section in ("build", "target", "combined"):
            self.assertIn(section, result["totals"])

    def test_component_attribution_is_recorded_on_the_result(self):
        result = estimate.compute_plan(manifest(), PROFILE)
        self.assertIn("component_costs", result)
        self.assertIn("components", result["component_costs"])

    def test_credits_are_not_attributed_without_declared_cases(self):
        result = estimate.compute_plan(manifest(), PROFILE)
        data = result["component_costs"]
        if not data["attributable"]:
            for row in data["components"]:
                self.assertEqual(
                    row["target_credits"], 0.0,
                    "credits were distributed without declared eval cases, "
                    "which is invention rather than attribution")


if __name__ == "__main__":
    unittest.main(verbosity=2)
