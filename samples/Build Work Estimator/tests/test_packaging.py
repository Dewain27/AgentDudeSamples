#!/usr/bin/env python3
"""Host packages: limits respected, sandbox instructions correct, runs standalone.

Author: Dewain Robinson

These run against the committed packages, so a stale artifact fails the suite
rather than shipping quietly.
"""

__author__ = "Dewain Robinson"

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))
PACKAGES = os.path.join(SAMPLE, "packages")
BUILD = os.path.join(SAMPLE, "build")

sys.path.insert(0, BUILD)
import build_host_packages as bhp  # noqa: E402

STANDARD = os.path.join(PACKAGES, "build-work-estimator.zip")
COWORK = os.path.join(PACKAGES, "build-work-estimator-cowork-plugin.zip")


def names(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        return archive.namelist()


class TestPackagesExist(unittest.TestCase):
    def test_both_packages_are_committed(self):
        self.assertTrue(os.path.exists(STANDARD),
                        "Agent Skills package missing; run build_host_packages.py")
        self.assertTrue(os.path.exists(COWORK),
                        "Cowork package missing; run build_host_packages.py")


class TestAgentSkillsPackage(unittest.TestCase):
    """Copilot Studio and Claude Cowork consume the Agent Skills standard."""

    def setUp(self):
        self.entries = names(STANDARD)

    def test_skill_md_at_the_root(self):
        self.assertIn("SKILL.md", self.entries)

    def test_companion_count_within_documented_limit(self):
        companions = [n for n in self.entries
                      if n != "SKILL.md" and not n.endswith("/")]
        self.assertLessEqual(
            len(companions), bhp.MAX_COMPANION_FILES,
            "%d companions exceeds the documented ceiling of %d"
            % (len(companions), bhp.MAX_COMPANION_FILES))

    def test_headroom_remains(self):
        companions = [n for n in self.entries
                      if n != "SKILL.md" and not n.endswith("/")]
        self.assertLess(len(companions), bhp.MAX_COMPANION_FILES,
                        "packaging is at the ceiling with no headroom")

    def test_total_size_within_limit(self):
        self.assertLess(os.path.getsize(STANDARD), bhp.MAX_TOTAL_BYTES)

    def test_every_script_is_present(self):
        for script in ("estimate.py", "calibrate.py", "licensing.py",
                       "miniyaml.py", "environment.py", "render_report.py",
                       "copilot_credits.py", "github_copilot.py"):
            self.assertIn("scripts/%s" % script, self.entries)

    def test_references_are_consolidated(self):
        refs = [n for n in self.entries if n.startswith("references/")]
        self.assertEqual(sorted(refs),
                         ["references/methodology.md", "references/rates.md"])


class TestCoworkPackage(unittest.TestCase):
    """Microsoft Copilot Cowork wants a Teams manifest plus icons."""

    def setUp(self):
        self.entries = names(COWORK)
        with zipfile.ZipFile(COWORK) as archive:
            self.manifest = json.loads(archive.read("manifest.json"))

    def test_required_root_files(self):
        for required in ("manifest.json", "color.png", "outline.png"):
            self.assertIn(required, self.entries)

    def test_manifest_points_at_a_folder_that_exists(self):
        folders = [s["folder"] for s in self.manifest["agentSkills"]]
        self.assertEqual(folders, ["./skills/build-work-estimator"])
        self.assertTrue(
            any(n.startswith("skills/build-work-estimator/")
                for n in self.entries),
            "manifest references a skills folder absent from the package")

    def test_skill_md_inside_the_skills_folder(self):
        self.assertIn("skills/build-work-estimator/SKILL.md", self.entries)

    def test_description_within_limits(self):
        self.assertLessEqual(len(self.manifest["description"]["short"]), 80)
        self.assertLessEqual(len(self.manifest["description"]["full"]),
                             bhp.MAX_DESC_LEN)

    def test_id_is_stable_across_rebuilds(self):
        self.assertEqual(self.manifest["id"], bhp.COWORK_ID)

    def test_developer_attribution(self):
        self.assertEqual(self.manifest["developer"]["name"], "Dewain Robinson")


class TestSandboxInstructions(unittest.TestCase):
    """Packaged SKILL.md must not tell a browserless host to launch a browser."""

    def setUp(self):
        with zipfile.ZipFile(STANDARD) as archive:
            self.skill = archive.read("SKILL.md").decode("utf-8")

    def test_native_pdf_is_the_instruction(self):
        self.assertIn("no browser and no package installation", self.skill)
        self.assertIn("creates documents natively", self.skill)

    def test_does_not_instruct_format_both(self):
        self.assertNotIn("--format both", self.skill)

    def test_host_note_explains_baseline_fallback(self):
        self.assertIn("## Running here", self.skill)
        self.assertIn("falls back to published baselines", self.skill)
        self.assertIn("materially less reliable", self.skill)

    def test_host_note_explains_no_pip(self):
        self.assertIn("PyYAML is not needed", self.skill)

    def test_points_at_the_capability_probe(self):
        self.assertIn("environment.py", self.skill)


class TestPackagedSkillRuns(unittest.TestCase):
    """The extracted package must work with nothing else installed."""

    def test_estimate_runs_from_the_extracted_package(self):
        directory = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(STANDARD) as archive:
                archive.extractall(directory)
            out = os.path.join(directory, "e.json")
            proc = subprocess.run(
                [sys.executable, os.path.join(directory, "scripts",
                                              "estimate.py"),
                 "--manifest", os.path.join(directory, "assets",
                                            "harbor-line-manifest.yaml"),
                 "--out", out],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0,
                             "packaged estimate failed:\n%s" % proc.stderr)
            with open(out) as fh:
                result = json.load(fh)
            self.assertEqual(result["build_stack"], "claude-code")
            self.assertGreater(result["base"], 0)
        finally:
            import shutil
            shutil.rmtree(directory, ignore_errors=True)

    def test_environment_probe_runs_from_the_extracted_package(self):
        directory = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(STANDARD) as archive:
                archive.extractall(directory)
            proc = subprocess.run(
                [sys.executable,
                 os.path.join(directory, "scripts", "environment.py"),
                 "--json"],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertIn("capabilities", payload)
            self.assertTrue(payload["capabilities"]["manifest_parsing"])
        finally:
            import shutil
            shutil.rmtree(directory, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
