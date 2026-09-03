#!/usr/bin/env python3
"""Documentation must describe what actually exists.

Author: Dewain Robinson

Docs drift silently. Nothing breaks when a README claims 228 tests and the
suite runs 292, or when four modules are added and the bundled-files table
never learns about them -- so it goes unnoticed until someone trusts the wrong
number.

Only claims that can be settled mechanically are checked. Claims needing
judgment are not, because a check that pretends to verify them would be worse
than no check.
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
sys.path.insert(0, BUILD)

import re  # noqa: E402
import check_docs  # noqa: E402
check_docs.re = re


class TestDocumentationMatchesReality(unittest.TestCase):
    """The drift check itself runs as its own CI step, not from in here.

    It shells out to the test suite to count tests, so calling it from inside
    the suite recurses. CI runs `check_docs.py --check` separately; this suite
    proves the checker works and can fail.
    """

    def test_the_checks_that_do_not_need_the_suite_pass(self):
        problems = []
        for label, check in check_docs.CHECKS:
            if label == "test counts":
                continue    # needs a suite run; CI covers it
            check(problems)
        self.assertEqual(
            problems, [],
            "documentation has drifted:\n  " + "\n  ".join(problems))


class TestTheCheckerCanActuallyFail(unittest.TestCase):
    """A documentation check that always passes is decoration."""

    def _with_doc(self, body, check, **kwargs):
        """Run one check against a throwaway document.

        The file goes to a unique temp directory: an earlier version wrote a
        fixed name under tests/, and a nested suite run deleted it underneath
        the outer test.
        """
        import shutil
        import tempfile
        directory = tempfile.mkdtemp()
        fake = os.path.join(directory, "drift.md")
        with open(fake, "w") as fh:
            fh.write(body)
        original = check_docs._markdown_files
        check_docs._markdown_files = lambda: [fake]
        problems = []
        try:
            check(problems, **kwargs)
        finally:
            check_docs._markdown_files = original
            shutil.rmtree(directory, ignore_errors=True)
        return problems

    def test_a_wrong_test_count_is_caught(self):
        # The count is injected, so this never triggers a nested suite run.
        problems = self._with_doc("This sample has 9999 tests.\n",
                                  check_docs.check_test_counts, actual=292)
        self.assertTrue(problems, "a wrong test count must be reported")
        self.assertIn("9999", problems[0])

    def test_a_correct_test_count_passes(self):
        self.assertEqual(
            self._with_doc("This sample has 292 tests.\n",
                           check_docs.check_test_counts, actual=292), [])

    def test_an_undocumented_module_is_caught(self):
        problems = []
        scripts = check_docs.SCRIPTS
        planted = os.path.join(scripts, "_undocumented_probe.py")
        with open(planted, "w") as fh:
            fh.write("# planted by a test\n")
        try:
            check_docs.check_script_inventory(problems)
        finally:
            os.remove(planted)
        self.assertTrue(
            any("_undocumented_probe.py" in p for p in problems),
            "a module absent from SKILL.md must be reported")

    def test_a_broken_local_link_is_caught(self):
        problems = self._with_doc("See [the thing](does-not-exist.md).\n",
                                  check_docs.check_links)
        self.assertTrue(problems)
        self.assertIn("does-not-exist.md", problems[0])

    def test_a_stale_rate_date_is_caught(self):
        problems = self._with_doc("**Rates verified:** 1999-01-01\n",
                                  check_docs.check_rate_dates)
        self.assertTrue(problems)
        self.assertIn("1999-01-01", problems[0])


class TestScopeIsHonest(unittest.TestCase):
    def test_only_mechanical_claims_are_checked(self):
        with open(os.path.join(BUILD, "check_docs.py")) as fh:
            source = fh.read()
        self.assertIn("settled mechanically", source)
        self.assertIn("Claims that need judgment are not checked", source)

    def test_every_check_is_registered(self):
        names = [label for label, _ in check_docs.CHECKS]
        for expected in ("test counts", "script inventory", "local links",
                         "rate verification dates"):
            self.assertIn(expected, names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
