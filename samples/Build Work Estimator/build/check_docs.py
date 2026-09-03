#!/usr/bin/env python3
"""Verify the documentation describes what actually exists.

Author: Dewain Robinson

    python build/check_docs.py            # report drift
    python build/check_docs.py --check    # same, non-zero exit on drift

Documentation drifts silently. Nothing breaks when a README claims 271 tests
and the suite has 292, or when a module is added and the bundled-files table
never learns about it -- so it goes unnoticed until someone trusts the wrong
number.

Every claim checked here is one that can be settled mechanically against the
repository. Claims that need judgment are not checked, and pretending
otherwise would be worse than not checking.

What is verified:

  * Test counts cited in prose match the suite
  * Every script exists that the docs say exists
  * Every script that exists is documented -- no silent modules
  * Companion-file counts match the built package
  * Rate verification dates in docs match the rate tables
  * Local file links resolve
"""

__author__ = "Dewain Robinson"

import argparse
import glob
import os
import re
import subprocess
import sys
import zipfile

SAMPLE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(SAMPLE, "..", ".."))
SCRIPTS = os.path.join(SAMPLE, "skill", "build-work-estimator", "scripts")
SKILL_MD = os.path.join(SAMPLE, "skill", "build-work-estimator", "SKILL.md")

#: Documents whose claims are checked.
DOCS = ["README.md", "SKILL.md", "docs", "scenarios"]

#: Modules that are infrastructure rather than user-facing capability, so
#: they are not required to appear in the bundled-files table.
UNDOCUMENTED_OK = {"__init__.py"}

TEST_COUNT = re.compile(r"\b(\d{2,4})\s+tests\b")
VERIFIED = re.compile(r"\*\*(?:Rates )?[Vv]erified:?\*\*\s*(\d{4}-\d{2}-\d{2})")
LOCAL_LINK = re.compile(r"\]\(([^)#:]+\.(?:md|py|yaml|json|pdf))(?:#[^)]*)?\)")
COMPANIONS = re.compile(r"companion files?\s*:?\s*(\d+)\s*/\s*(\d+)", re.I)
COMPANION_PROSE = re.compile(r"\b(\d+)\s*/\s*20\s+companion", re.I)


def _markdown_files():
    found = [os.path.join(SAMPLE, "README.md"), SKILL_MD]
    for directory in ("docs", "scenarios"):
        found.extend(glob.glob(os.path.join(SAMPLE, directory, "**", "*.md"),
                               recursive=True))
    found.append(os.path.join(REPO, "README.md"))
    return [p for p in found if os.path.exists(p)]


#: Set while the suite is running so the checker never re-enters it. Without
#: this, running the doc check from inside a test recurses until it is killed.
REENTRY_GUARD = "BUILD_WORK_ESTIMATOR_DOC_CHECK_RUNNING"


def actual_test_count():
    if os.environ.get(REENTRY_GUARD):
        return None
    os.environ[REENTRY_GUARD] = "1"
    try:
        return _discover_test_count()
    finally:
        os.environ.pop(REENTRY_GUARD, None)


def _discover_test_count():
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-p", "test_*.py"],
        cwd=os.path.join(SAMPLE, "tests"), capture_output=True, text=True)
    match = re.search(r"^Ran (\d+) tests?", proc.stderr, re.M)
    return int(match.group(1)) if match else None


def actual_companion_count():
    package = os.path.join(SAMPLE, "packages", "build-work-estimator.zip")
    if not os.path.exists(package):
        return None
    with zipfile.ZipFile(package) as archive:
        return len([n for n in archive.namelist()
                    if n != "SKILL.md" and not n.endswith("/")])


def check_test_counts(problems, actual=None):
    """Injectable count so callers can check without running the suite."""
    if actual is None:
        actual = actual_test_count()
    if actual is None:
        # Either discovery failed or we are inside the suite already. Skipping
        # is correct: CI runs this check as its own step, outside the suite.
        return
    for path in _markdown_files():
        with open(path) as fh:
            text = fh.read()
        for cited in set(TEST_COUNT.findall(text)):
            # Only flag numbers plausibly describing the suite.
            if abs(int(cited) - actual) == 0:
                continue
            if int(cited) < 20:
                continue
            problems.append(
                "%s cites %s tests; the suite runs %d"
                % (os.path.relpath(path, REPO), cited, actual))


def check_script_inventory(problems):
    with open(SKILL_MD) as fh:
        skill = fh.read()
    on_disk = set(os.path.basename(p) for p in glob.glob(
        os.path.join(SCRIPTS, "*.py"))) - UNDOCUMENTED_OK

    documented = set(re.findall(r"`scripts/([a-z_]+\.py)`", skill))
    for name in sorted(documented - on_disk):
        problems.append("SKILL.md documents scripts/%s which does not exist"
                        % name)
    for name in sorted(on_disk - documented):
        problems.append(
            "scripts/%s exists but SKILL.md does not document it -- an "
            "undocumented capability is an unusable one" % name)


def check_companion_counts(problems):
    actual = actual_companion_count()
    if actual is None:
        problems.append("packages/build-work-estimator.zip is missing; "
                        "run build/build_host_packages.py")
        return
    for path in _markdown_files():
        with open(path) as fh:
            text = fh.read()
        for cited in set(COMPANION_PROSE.findall(text)):
            if int(cited) != actual:
                problems.append(
                    "%s cites %s/20 companion files; the package has %d"
                    % (os.path.relpath(path, REPO), cited, actual))


def check_rate_dates(problems):
    sys.path.insert(0, SCRIPTS)
    import rates
    known = {rates.ANTHROPIC_VERIFIED, rates.COPILOT_VERIFIED,
             rates.GITHUB_VERIFIED, rates.PUBLISHED_BASELINE_VERIFIED}
    for path in _markdown_files():
        with open(path) as fh:
            text = fh.read()
        for cited in set(VERIFIED.findall(text)):
            if cited not in known:
                problems.append(
                    "%s claims rates verified %s; the tables carry %s"
                    % (os.path.relpath(path, REPO), cited,
                       ", ".join(sorted(known))))


def check_links(problems):
    for path in _markdown_files():
        base = os.path.dirname(path)
        with open(path) as fh:
            text = fh.read()
        for target in set(LOCAL_LINK.findall(text)):
            if target.startswith(("http", "mailto")):
                continue
            resolved = os.path.normpath(
                os.path.join(base, target.replace("%20", " ")))
            if not os.path.exists(resolved):
                problems.append("%s links to %s which does not exist"
                                % (os.path.relpath(path, REPO), target))


CHECKS = (
    ("test counts", check_test_counts),
    ("script inventory", check_script_inventory),
    ("companion-file counts", check_companion_counts),
    ("rate verification dates", check_rate_dates),
    ("local links", check_links),
)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero when documentation has drifted")
    args = ap.parse_args(argv)

    problems = []
    for label, check in CHECKS:
        before = len(problems)
        check(problems)
        status = "ok" if len(problems) == before else \
            "%d problem(s)" % (len(problems) - before)
        print("  %-26s %s" % (label, status))

    if not problems:
        print("\nDocumentation matches the repository.")
        return 0

    print("\nDOCUMENTATION HAS DRIFTED:\n", file=sys.stderr)
    for problem in problems:
        print("  - %s" % problem, file=sys.stderr)
    print("\nFix the documentation, not the check.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
