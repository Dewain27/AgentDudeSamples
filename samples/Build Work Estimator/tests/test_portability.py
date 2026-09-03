#!/usr/bin/env python3
"""Runs on all four hosts: Claude Code, Claude Cowork, GitHub Copilot, Copilot Cowork.

Author: Dewain Robinson

Sandboxed hosts have no package installation and no browser. These tests prove
the estimator still produces a correct estimate there, rather than failing on an
import.
"""

__author__ = "Dewain Robinson"

import os
import shutil
import sys
import tempfile
import unittest

import _fixtures  # noqa: F401
import environment  # noqa: E402
import estimate  # noqa: E402
import miniyaml  # noqa: E402
import render_report as rr  # noqa: E402
from test_estimate import PROFILE, manifest  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "..", "examples")


class _BlockImport(object):
    """Context manager that makes named modules unimportable."""

    def __init__(self, *names):
        self.names = names
        self.saved = {}

    def __enter__(self):
        for name in self.names:
            self.saved[name] = sys.modules.get(name, None)
            sys.modules[name] = None  # import raises ImportError
        return self

    def __exit__(self, *exc):
        for name, value in self.saved.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
        return False


class TestManifestParsingWithoutPyYAML(unittest.TestCase):
    """A sandbox cannot pip install PyYAML. The manifest must still parse."""

    def _parity(self, path):
        with open(path) as fh:
            text = fh.read()
        import yaml
        self.assertEqual(yaml.safe_load(text), miniyaml.parse(text),
                         "bundled parser diverges from PyYAML on %s" % path)

    def test_parity_on_every_shipped_manifest(self):
        found = 0
        for name in sorted(os.listdir(EXAMPLES)):
            if name.endswith((".yaml", ".yml")):
                self._parity(os.path.join(EXAMPLES, name))
                found += 1
        self.assertGreaterEqual(found, 2, "expected both scenario manifests")

    def test_estimate_runs_with_pyyaml_blocked(self):
        path = os.path.join(EXAMPLES, "harbor-line-manifest.yaml")
        with _BlockImport("yaml"):
            data = estimate.load_manifest(path)
        self.assertEqual(data["build_platform"], "claude-code")
        self.assertEqual(data["target_platform"], "copilot-studio")
        self.assertEqual(data["reserve_percent"], 25)
        self.assertEqual(data["licensing"]["seat_monthly_cost"], 200)
        self.assertEqual(len(data["items"]), 4)
        self.assertTrue(data["items"][0]["brownfield"])

    def test_full_estimate_produced_with_pyyaml_blocked(self):
        path = os.path.join(EXAMPLES, "harbor-line-manifest.yaml")
        with _BlockImport("yaml"):
            data = estimate.load_manifest(path)
            result = estimate.compute_plan(data, PROFILE)
        self.assertGreater(result["build"]["base"], 0)
        self.assertEqual(result["build_platform"], "claude-code")


class TestMiniYaml(unittest.TestCase):
    def test_scalars(self):
        out = miniyaml.parse(
            "s: hello\nq: 'quoted'\ni: 42\nf: 1.5\nt: true\nfa: false\nn: null\n")
        self.assertEqual(out, {"s": "hello", "q": "quoted", "i": 42,
                               "f": 1.5, "t": True, "fa": False, "n": None})

    def test_comments_and_blank_lines_ignored(self):
        out = miniyaml.parse("# lead\n\na: 1   # trailing\n\n# tail\n")
        self.assertEqual(out, {"a": 1})

    def test_hash_inside_quotes_is_not_a_comment(self):
        self.assertEqual(miniyaml.parse('a: "x # y"'), {"a": "x # y"})

    def test_nested_mappings(self):
        out = miniyaml.parse("a:\n  b:\n    c: 1\n  d: 2\ne: 3\n")
        self.assertEqual(out, {"a": {"b": {"c": 1}, "d": 2}, "e": 3})

    def test_list_of_mappings(self):
        out = miniyaml.parse(
            "items:\n  - name: a\n    n: 1\n  - name: b\n    n: 2\n")
        self.assertEqual(out, {"items": [{"name": "a", "n": 1},
                                         {"name": "b", "n": 2}]})

    def test_scalar_list(self):
        self.assertEqual(miniyaml.parse("xs:\n  - one\n  - two\n"),
                         {"xs": ["one", "two"]})

    def test_empty_document(self):
        self.assertIsNone(miniyaml.parse("# only a comment\n"))

    def test_tab_indent_rejected(self):
        with self.assertRaises(miniyaml.ManifestParseError):
            miniyaml.parse("a:\n\tb: 1\n")

    def test_flow_collection_rejected_rather_than_guessed(self):
        with self.assertRaises(miniyaml.ManifestParseError):
            miniyaml.parse("a: [1, 2]\n")

    def test_non_pair_line_rejected(self):
        with self.assertRaises(miniyaml.ManifestParseError):
            miniyaml.parse("just some text\n")

    def test_load_prefers_pyyaml_when_present(self):
        self.assertEqual(miniyaml.load("a: 1"), {"a": 1})

    def test_load_falls_back_when_pyyaml_absent(self):
        with _BlockImport("yaml"):
            self.assertEqual(miniyaml.load("a: 1"), {"a": 1})


class TestEnvironmentProbe(unittest.TestCase):
    def test_probe_reports_every_capability(self):
        caps = environment.probe()
        for key in ("session_history", "pyyaml", "manifest_parsing",
                    "markdown", "playwright", "chromium", "pdf_locally"):
            self.assertIn(key, caps)
            self.assertIsInstance(caps[key], bool)

    def test_manifest_parsing_is_always_available(self):
        # The bundled parser has no dependencies, so this can never be false.
        self.assertTrue(environment.probe()["manifest_parsing"])

    def test_no_history_means_published_baseline_and_says_so(self):
        empty = tempfile.mkdtemp()
        try:
            caps = environment.probe(empty)
            self.assertFalse(caps["session_history"])
            self.assertEqual(environment.calibration_mode(caps),
                             "published-baseline")
            notes = " ".join(environment.guidance(caps))
            self.assertIn("published baselines", notes)
            self.assertIn("materially less reliable", notes)
            self.assertIn("Copilot Cowork", notes)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_history_present_means_measured(self):
        root = tempfile.mkdtemp()
        try:
            _fixtures.simple_history(root)
            caps = environment.probe(root)
            self.assertTrue(caps["session_history"])
            self.assertEqual(environment.calibration_mode(caps), "measured")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_guidance_points_sandboxes_at_native_pdf(self):
        caps = dict(environment.probe())
        caps.update({"markdown": False, "chromium": False, "pdf_locally": False})
        notes = " ".join(environment.guidance(caps))
        self.assertIn("creates documents natively", notes)
        self.assertIn("rather than installing a browser", notes)

    def test_missing_pyyaml_is_a_note_not_a_failure(self):
        caps = dict(environment.probe())
        caps["pyyaml"] = False
        notes = " ".join(environment.guidance(caps))
        self.assertIn("bundled manifest parser", notes)
        self.assertIn("no action needed", notes)


class TestReportWithoutBrowser(unittest.TestCase):
    def test_markdown_is_complete_and_names_the_native_pdf_route(self):
        directory = tempfile.mkdtemp()
        try:
            import json
            result = estimate.compute_plan(manifest(), PROFILE)
            payload = os.path.join(directory, "e.json")
            with open(payload, "w") as fh:
                json.dump(result, fh)
            out = os.path.join(directory, "report")
            original = rr.write_pdf
            rr.write_pdf = lambda *a, **kw: "no browser in this sandbox"
            try:
                code = rr.main([payload, "-o", out, "--format", "both"])
            finally:
                rr.write_pdf = original
            self.assertEqual(code, 0)
            with open(out + ".md") as fh:
                body = fh.read()
            self.assertIn("SAMPLE", body)
            self.assertIn("Budget ask", body)
        finally:
            shutil.rmtree(directory, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
