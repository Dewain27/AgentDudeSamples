#!/usr/bin/env python3
"""Report rendering: disclaimer everywhere, scope banner, PDF-failure safety.

Author: Dewain Robinson
"""

__author__ = "Dewain Robinson"

import os
import shutil
import sys
import tempfile
import unittest

import _fixtures  # noqa: F401
import copilot_credits as cc  # noqa: E402
import estimate  # noqa: E402
import render_report as rr  # noqa: E402
from test_estimate import PROFILE, manifest  # noqa: E402


class TestMarkdown(unittest.TestCase):
    def setUp(self):
        self.result = estimate.compute_plan(manifest(), PROFILE)
        self.md = rr.build_markdown(self.result)

    def test_disclaimer_is_present_and_first(self):
        self.assertIn("SAMPLE — BUILD ESTIMATE ONLY, NOT A QUOTE", self.md)
        body = self.md.split("---", 2)[-1]
        disclaimer_at = body.index("SAMPLE — BUILD ESTIMATE ONLY")
        summary_at = body.index("## Estimate summary")
        self.assertLess(disclaimer_at, summary_at,
                        "disclaimer must precede any figure")

    def test_disclaimer_states_build_not_run(self):
        self.assertIn("never the cost of running what", self.md)
        self.assertIn("will be wrong", self.md)
        self.assertIn("must be modified for your", self.md)

    def test_scope_section_lists_exclusions(self):
        self.assertIn("this estimates the build, not the run", self.md)
        for term in ("Runtime", "licences", "Infrastructure", "labour"):
            self.assertIn(term, self.md)

    def test_footer_present(self):
        self.assertIn(rr.FOOTER, self.md)
        self.assertIn("Excludes runtime cost", self.md)

    def test_author_attribution(self):
        self.assertIn("author: Dewain Robinson", self.md)
        self.assertIn("**Author:** Dewain Robinson", self.md)

    def test_estimate_id_present_for_closing_the_loop(self):
        self.assertIn(self.result["estimate_id"], self.md)
        self.assertIn("record_actual.py", self.md)

    def test_reserve_adequacy_is_reported(self):
        self.assertIn("## Reserve adequacy", self.md)
        self.assertIn("does not cover observed variance", self.md)

    def test_adequate_reserve_reads_differently(self):
        md = rr.build_markdown(estimate.compute_plan(
            manifest(reserve_percent=400), PROFILE))
        self.assertIn("covers the observed high", md)

    def test_thin_buckets_are_flagged(self):
        m = manifest()
        m["items"] = [{"name": "big", "size": "large", "files": 30,
                       "unknowns": 0}]
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("Thin calibration data", md)

    def test_published_baseline_is_disclosed(self):
        import calibrate
        md = rr.build_markdown(estimate.compute_plan(
            manifest(), calibrate.fallback_profile()))
        self.assertIn("no local session history was found", md)
        self.assertIn("materially less reliable", md)

    def test_both_platforms_named_with_their_meters(self):
        self.assertIn("## Platforms", self.md)
        self.assertIn("**Built with** | Claude Code | USD (tokens)", self.md)
        self.assertIn("**Built on** | Microsoft Copilot Studio | Copilot Credits",
                      self.md)

    def test_states_copilot_studio_is_a_destination_not_a_build_tool(self):
        self.assertIn("destination, not a build tool", self.md)

    def test_both_meters_are_additive_not_alternatives(self):
        self.assertIn("Two meters, not two options", self.md)
        self.assertIn("add together", self.md)

    def test_build_loop_and_remediation_are_shown(self):
        self.assertIn("## The build loop", self.md)
        self.assertIn("remediate", self.md)
        self.assertIn("evaluation cycle", self.md)

    def test_human_validation_named_as_dependency_not_costed(self):
        self.assertIn("a dependency, not a cost line", self.md)
        self.assertIn("not** estimated as labour", self.md)

    def test_report_disclaims_being_a_comparison_tool(self):
        self.assertIn("not a platform comparison tool", self.md)
        self.assertIn("not made on cost alone", self.md)

    def test_licensing_section_present(self):
        self.assertIn("## Licensing", self.md)
        self.assertIn("Consumption billing", self.md)

    def test_standard_harness_target_is_unbilled_and_says_so(self):
        m = manifest()
        m["target"] = {"harness": "standard", "eval_test_cases": 10,
                       "eval_cycles": 2, "interactive_test_hours": 4}
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("build and test in the interface are not billed", md)
        self.assertIn("correct result, not a missing one", md)
        self.assertIn("Had this been the GitHub Copilot harness", md)


class TestExecutiveSummary(unittest.TestCase):
    """The section a reader looks at first must stand on its own."""

    def setUp(self):
        self.result = estimate.compute_plan(manifest(), PROFILE)
        self.md = rr.build_markdown(self.result)

    def test_summary_precedes_the_detail(self):
        body = self.md.split("---", 2)[-1]
        self.assertLess(body.index("## Estimate summary"),
                        body.index("## The build loop"),
                        "the summary must come before the detail")

    def test_key_inputs_are_restated(self):
        self.assertIn("### What was estimated", self.md)
        self.assertIn("(development tool)", self.md)
        self.assertIn("(target environment)", self.md)
        self.assertIn("Target harness", self.md)
        self.assertIn("Evaluation cycles planned", self.md)
        self.assertIn("Contingency reserve", self.md)

    def test_four_totals_rows_present(self):
        for row in ("| Low |", "| **Likely** |", "| High |",
                    "reserve** |"):
            self.assertIn(row, self.md, "missing totals row: %s" % row)

    def test_headline_states_plan_and_hold(self):
        self.assertRegex(self.md, r"\*\*Plan for \$[\d,]+\.\d\d\. "
                                  r"Hold \$[\d,]+\.\d\d")

    def test_combined_column_sums_the_two_meters(self):
        build = rr._build_totals(self.result)
        target = rr._target_totals(self.result)
        for key in ("low", "likely", "high", "with_reserve"):
            combined = round(build["usd_" + key] + target["usd_" + key], 2)
            self.assertIn(rr.money(combined), self.md,
                          "combined %s figure missing from the summary" % key)

    def test_ordering_is_low_then_likely_then_high(self):
        build = rr._build_totals(self.result)
        self.assertLessEqual(build["usd_low"], build["usd_likely"])
        self.assertLessEqual(build["usd_likely"], build["usd_high"])

    def test_reserve_row_exceeds_the_likely_row(self):
        build = rr._build_totals(self.result)
        self.assertGreater(build["usd_with_reserve"], build["usd_likely"])

    def test_credit_conversion_is_disclosed(self):
        self.assertIn("converted at $0.01", self.md)
        self.assertIn("separate budgets", self.md)

    def test_seat_build_figure_is_labelled_notional(self):
        m = manifest()
        m["licensing"] = {"model": "seat", "plan": "Claude Max",
                          "seat_monthly_cost": 200, "seats": 1,
                          "other_workload_share": 0.4}
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("notional", md)

    def test_seat_cost_reports_rate_seats_duration_and_total(self):
        m = manifest()
        m["licensing"] = {"model": "seat", "plan": "Team", "seats": 4,
                          "seat_monthly_cost": 25, "duration_months": 5,
                          "other_workload_share": 0.2}
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("$25.00/month x 4 seats x 5 months", md)
        self.assertIn("$500.00** over the build", md)

    def test_seat_total_is_not_mislabelled_as_monthly(self):
        m = manifest()
        m["licensing"] = {"model": "seat", "plan": "Team", "seats": 6,
                          "seat_monthly_cost": 150, "duration_months": 5,
                          "other_workload_share": 0.3}
        md = rr.build_markdown(estimate.compute_plan(m, PROFILE))
        self.assertIn("$150.00/month", md)
        self.assertNotIn("$750.00/month", md,
                         "rate x duration was being labelled as a monthly rate")

    def test_target_range_comes_from_cycle_variation(self):
        # The default fixture plans a single cycle, so low == likely there.
        # Use a multi-cycle plan to exercise the range properly.
        m = manifest()
        m["target"] = dict(m["target"], eval_cycles=4, eval_test_cases=40)
        result = estimate.compute_plan(m, PROFILE)
        span = result["targets"][0]["range"]
        self.assertLess(span["low_cycles"], span["likely_cycles"])
        self.assertGreater(span["high_cycles"], span["likely_cycles"])
        self.assertLess(span["low_credits"], span["high_credits"])
        self.assertIn("evaluation cycles instead of",
                      rr.build_markdown(result))

    def test_single_cycle_plan_still_produces_a_summary(self):
        span = self.result["targets"][0]["range"]
        self.assertEqual(span["low_cycles"], 1)
        self.assertEqual(span["likely_cycles"], 1)
        self.assertIn("### Totals", self.md)


class TestFileOutput(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.result = estimate.compute_plan(manifest(), PROFILE)
        self.json_path = os.path.join(self.dir, "estimate.json")
        import json
        with open(self.json_path, "w") as fh:
            json.dump(self.result, fh)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_md_only(self):
        out = os.path.join(self.dir, "report")
        rr.main([self.json_path, "-o", out, "--format", "md"])
        self.assertTrue(os.path.exists(out + ".md"))
        self.assertFalse(os.path.exists(out + ".pdf"))

    def test_markdown_survives_pdf_failure(self):
        out = os.path.join(self.dir, "report2")
        original = rr.write_pdf
        rr.write_pdf = lambda *a, **kw: "Chromium is not installed"
        try:
            code = rr.main([self.json_path, "-o", out, "--format", "both"])
        finally:
            rr.write_pdf = original
        self.assertEqual(code, 0, "a PDF failure must not fail the run")
        self.assertTrue(os.path.exists(out + ".md"),
                        "the estimate must survive a PDF toolchain failure")
        with open(out + ".md") as fh:
            self.assertIn("SAMPLE", fh.read())

    def test_pdf_only_still_writes_markdown(self):
        out = os.path.join(self.dir, "report3")
        original = rr.write_pdf
        rr.write_pdf = lambda *a, **kw: "no chromium"
        try:
            rr.main([self.json_path, "-o", out, "--format", "pdf"])
        finally:
            rr.write_pdf = original
        self.assertTrue(os.path.exists(out + ".md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
