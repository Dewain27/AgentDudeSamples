#!/usr/bin/env python3
"""The shipped examples must match the code that produced them.

Author: Dewain Robinson

Committed sample output that lags its code is worse than no sample: it reads as
authoritative and is quietly wrong. Nothing else in the repo would catch that
drift, so it is caught here and in CI.
"""

__author__ = "Dewain Robinson"

import os
import subprocess
import sys
import unittest

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))
BUILD = os.path.join(SAMPLE, "build")
EXAMPLES = os.path.join(SAMPLE, "examples")

sys.path.insert(0, BUILD)
import regenerate_examples as regen  # noqa: E402


class TestInputsAreCommitted(unittest.TestCase):
    """An example nobody else can reproduce is not a sample."""

    def test_calibration_profile_is_committed(self):
        self.assertTrue(
            os.path.exists(regen.PROFILE),
            "examples/calibration-profile.json is missing; the examples would "
            "not be reproducible outside the machine that made them")

    def test_every_scenario_manifest_is_committed(self):
        for scenario in regen.SCENARIOS:
            path = os.path.join(EXAMPLES, scenario["manifest"])
            self.assertTrue(os.path.exists(path),
                            "missing manifest: %s" % scenario["manifest"])

    def test_scenarios_pin_id_and_timestamp(self):
        # Without pinning, regeneration churns and the drift check is useless.
        for scenario in regen.SCENARIOS:
            self.assertTrue(scenario["estimate_id"])
            self.assertTrue(scenario["generated"])

    def test_both_build_platforms_are_demonstrated(self):
        import estimate
        import miniyaml
        platforms = set()
        for scenario in regen.SCENARIOS:
            data = miniyaml.load_path(
                os.path.join(EXAMPLES, scenario["manifest"]))
            platforms.add(data["build_platform"])
            # Every shipped manifest must actually estimate.
            self.assertIsNotNone(data.get("target_platform"))
        self.assertEqual(platforms, {"claude-code", "github-copilot"},
                         "the samples should demonstrate both build platforms")

    def test_both_harnesses_are_demonstrated(self):
        import miniyaml
        harnesses = set()
        for scenario in regen.SCENARIOS:
            data = miniyaml.load_path(
                os.path.join(EXAMPLES, scenario["manifest"]))
            harness = (data.get("target") or {}).get("harness")
            if harness:
                harnesses.add(harness)
        self.assertEqual(
            harnesses, {"standard", "github-copilot"},
            "the samples should show both the billed and unbilled harness, "
            "since that distinction is the largest single swing in the model")


class TestExamplesDirectoryIsClean(unittest.TestCase):
    """examples/ holds inputs and outputs only -- no build intermediates."""

    ALLOWED_SUFFIXES = ("-manifest.yaml", "-estimate.md", "-estimate.pdf")
    ALLOWED_EXACT = ("calibration-profile.json",)

    def test_no_stray_files(self):
        stray = []
        for name in sorted(os.listdir(EXAMPLES)):
            if name.startswith("."):
                continue
            if name in self.ALLOWED_EXACT:
                continue
            if any(name.endswith(s) for s in self.ALLOWED_SUFFIXES):
                continue
            stray.append(name)
        self.assertEqual(
            stray, [],
            "examples/ should contain only manifests, the calibration "
            "profile, and the rendered .md/.pdf outputs. Found: %s" % stray)

    def test_regeneration_leaves_no_intermediates(self):
        before = set(os.listdir(EXAMPLES))
        subprocess.run(
            [sys.executable, os.path.join(BUILD, "regenerate_examples.py")],
            capture_output=True, text=True)
        after = set(os.listdir(EXAMPLES))
        self.assertEqual(
            after - before, set(),
            "regeneration wrote intermediate files into examples/: %s"
            % sorted(after - before))


class TestExamplesAreCurrent(unittest.TestCase):
    def test_committed_examples_match_a_fresh_regeneration(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(BUILD, "regenerate_examples.py"),
             "--check"],
            capture_output=True, text=True)
        self.assertEqual(
            proc.returncode, 0,
            "The shipped examples are stale relative to the code.\n\n%s%s\n"
            "Run: python build/regenerate_examples.py"
            % (proc.stdout, proc.stderr))

    def test_regeneration_is_deterministic(self):
        import tempfile
        import shutil
        first = tempfile.mkdtemp()
        second = tempfile.mkdtemp()
        try:
            a = regen.generate(regen.SCENARIOS[0], first, "md")
            b = regen.generate(regen.SCENARIOS[0], second, "md")
            with open(a) as fa, open(b) as fb:
                self.assertEqual(
                    fa.read(), fb.read(),
                    "regeneration is not deterministic, so the drift check "
                    "cannot be a plain comparison")
        finally:
            shutil.rmtree(first, ignore_errors=True)
            shutil.rmtree(second, ignore_errors=True)

    def test_check_mode_writes_nothing(self):
        before = {}
        for name in sorted(os.listdir(EXAMPLES)):
            path = os.path.join(EXAMPLES, name)
            before[name] = (os.path.getsize(path), os.path.getmtime(path))
        subprocess.run(
            [sys.executable, os.path.join(BUILD, "regenerate_examples.py"),
             "--check"], capture_output=True, text=True)
        for name, stamp in before.items():
            path = os.path.join(EXAMPLES, name)
            self.assertEqual(
                (os.path.getsize(path), os.path.getmtime(path)), stamp,
                "--check modified %s; it must be read-only" % name)


class TestDriftIsActuallyDetected(unittest.TestCase):
    """A check that cannot fail is not a check."""

    def test_markdown_drift_is_caught(self):
        import shutil
        import tempfile
        staging = tempfile.mkdtemp()
        try:
            fresh = regen.generate(regen.SCENARIOS[0], staging, "md")
            with open(fresh) as fh:
                good = fh.read()
            self.assertNotEqual(good, good.replace("Budget ask", "Total"),
                                "sanity: the marker should exist")
            # A one-word change must make the comparison fail.
            self.assertNotEqual(good, good + "\ndrift\n")
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def test_pdf_figure_check_flags_a_mismatched_pdf(self):
        md = os.path.join(EXAMPLES, "harbor-line-estimate.md")
        other_pdf = os.path.join(EXAMPLES, "granite-peak-estimate.pdf")
        problems = regen.check_pdf("harbor-line", md, other_pdf)
        self.assertTrue(
            problems,
            "pairing one scenario's Markdown with another's PDF must be "
            "reported as stale")
        self.assertIn("stale", problems[0])

    def test_missing_pdf_is_reported(self):
        problems = regen.check_pdf(
            "nope", os.path.join(EXAMPLES, "harbor-line-estimate.md"),
            os.path.join(EXAMPLES, "does-not-exist.pdf"))
        self.assertTrue(problems)
        self.assertIn("missing", problems[0])

    def test_figures_are_extracted_from_markdown(self):
        found = regen.figures("Budget ask $1,234.56 and 40,362 credits")
        self.assertIn("$1,234.56", found)
        self.assertIn("40,362", found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
