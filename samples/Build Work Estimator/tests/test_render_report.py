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
        self.result = estimate.compute(manifest(), PROFILE)
        self.md = rr.build_markdown(self.result)

    def test_disclaimer_is_present_and_first(self):
        self.assertIn("SAMPLE — BUILD ESTIMATE ONLY, NOT A QUOTE", self.md)
        body = self.md.split("---", 2)[-1]
        disclaimer_at = body.index("SAMPLE — BUILD ESTIMATE ONLY")
        summary_at = body.index("## Summary")
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
        md = rr.build_markdown(estimate.compute(manifest(reserve_percent=400),
                                                PROFILE))
        self.assertIn("covers the observed high", md)

    def test_thin_buckets_are_flagged(self):
        m = manifest()
        m["items"] = [{"name": "big", "size": "large", "files": 30,
                       "unknowns": 0}]
        md = rr.build_markdown(estimate.compute(m, PROFILE))
        self.assertIn("Thin calibration data", md)

    def test_published_baseline_is_disclosed(self):
        import calibrate
        md = rr.build_markdown(estimate.compute(manifest(),
                                                calibrate.fallback_profile()))
        self.assertIn("no local session history was found", md)
        self.assertIn("materially less reliable", md)

    def test_stack_banner_names_the_currency(self):
        self.assertIn("## Build stack — Claude Code", self.md)
        self.assertIn("USD (tokens)", self.md)
        self.assertIn("build with", self.md)

    def test_report_disclaims_being_a_comparison_tool(self):
        self.assertIn("not a stack comparison tool", self.md)
        self.assertIn("not made on cost alone", self.md)

    def test_licensing_section_present(self):
        self.assertIn("## Licensing", self.md)
        self.assertIn("Consumption billing", self.md)

    def test_copilot_studio_stack_reports_credits_not_tokens(self):
        m = manifest(build_stack="copilot-studio")
        m["copilot_studio"] = {"harness": "github-copilot", "tier": "standard",
                               "authoring_turns": 50}
        md = rr.build_markdown(estimate.compute_stack(m, PROFILE))
        self.assertIn("Copilot Credits", md)
        self.assertIn("## Build stack — Microsoft Copilot Studio", md)
        # A Microsoft-tooled build must never be priced in tokens.
        self.assertNotIn("cost per agent turn", md.lower())
        self.assertNotIn("$0.40", md)


class TestFileOutput(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.result = estimate.compute(manifest(), PROFILE)
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
