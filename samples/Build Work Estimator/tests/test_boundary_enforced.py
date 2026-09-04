#!/usr/bin/env python3
"""The researcher cannot produce a number that enters an estimate.

Author: Dewain Robinson

This is the security-critical suite, and it is written to run before the
researcher is wired to a model at all -- the same rule that governed
contribute.py: no path ships ahead of the test proving it cannot leak.

The threat is specific. The estimator's value rests on every figure tracing to
something measured, published, or declared by a human who knew the answer. A
model-supplied size would be a guess wearing a measurement's clothes, and it
would reach the arithmetic through whatever field nobody thought to guard.

So both gates are tested for FAILURE, not just success. A validator that
cannot reject is not a validator.
"""

__author__ = "Dewain Robinson"

import os
import sys
import unittest

import _fixtures  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(
    SAMPLE, "skill", "build-work-researcher", "scripts"))

import findings as F  # noqa: E402


def finding(**overrides):
    base = {
        "id": "F-001",
        "type": "missing-component",
        "severity": "high",
        "title": "No work item covers the supervisory archive retention policy",
        "rationale": "Control S7 requires an immutable archive; the breakdown "
                     "covers the integration but nothing owns the policy.",
        "spec_reference": "§9 S7",
        "breakdown_impact": "A new item is needed, or I9's scope must say it "
                            "is included.",
        "status": "open",
    }
    base.update(overrides)
    return base


def document(*items, **overrides):
    doc = {
        "schema": 1,
        "reviewed": "2026-09-04",
        "mode": "offline",
        "findings": list(items) or [finding()],
    }
    doc.update(overrides)
    return doc


class TestACleanFindingPasses(unittest.TestCase):
    """If nothing legitimate passes, the gate is useless rather than safe."""

    def test_a_well_formed_review_validates(self):
        self.assertEqual(F.validate_findings(document()), [])

    def test_a_finding_may_cite_a_requirement_by_identifier(self):
        ok = finding(rationale="N6 sets a concurrency target that no item "
                               "covers with load testing.")
        self.assertEqual(F.validate_findings(document(ok)), [])

    def test_spec_reference_may_contain_numbers(self):
        """A citation is not a claim."""
        ok = finding(spec_reference="§9 S7, §7 archive_batch, N5")
        self.assertEqual(F.validate_findings(document(ok)), [])


class TestTheSchemaGate(unittest.TestCase):
    """A boundary the format cannot express cannot be crossed by accident."""

    def test_there_is_no_field_for_a_size(self):
        self.assertNotIn("suggested_size", F.FINDING_KEYS)
        self.assertNotIn("size", F.FINDING_KEYS)
        self.assertNotIn("estimated_turns", F.FINDING_KEYS)
        self.assertNotIn("files", F.FINDING_KEYS)
        self.assertNotIn("unknowns", F.FINDING_KEYS)
        self.assertNotIn("impact_percent", F.FINDING_KEYS)

    def test_a_smuggled_size_field_is_rejected(self):
        problems = F.validate_findings(
            document(finding(suggested_size="large")))
        self.assertTrue(problems)
        self.assertIn("suggested_size", problems[0])

    def test_any_unknown_key_is_rejected(self):
        problems = F.validate_findings(document(finding(effort_days=12)))
        self.assertTrue(problems, "an unknown key is the whole attack surface")

    def test_unknown_top_level_keys_are_rejected(self):
        problems = F.validate_findings(document(total_turns=4000))
        self.assertTrue(problems)


class TestTheProseGate(unittest.TestCase):
    """The schema stops structured numbers; prose needs its own gate."""

    def assertRejected(self, text, field="rationale"):
        problems = F.validate_findings(document(finding(**{field: text})))
        self.assertTrue(
            problems,
            "prose asserting effort or cost must be rejected: %r" % text)
        return problems

    def test_turn_assertions_are_rejected(self):
        self.assertRejected("This component will take about 400 turns.")

    def test_hour_and_day_assertions_are_rejected(self):
        self.assertRejected("Roughly 40 hours of work is missing here.")
        self.assertRejected("This adds 3 days to the build.")
        self.assertRejected("Expect 2 weeks for the integration.")

    def test_cost_assertions_are_rejected(self):
        self.assertRejected("This would add $4,000 to the estimate.")

    def test_quantified_impact_is_rejected(self):
        self.assertRejected("This likely adds 30% to the breakdown.")

    def test_a_proposed_size_is_rejected(self):
        self.assertRejected("This should be size: large given the scope.")
        self.assertRejected("The item is plainly size medium.")

    def test_hedged_quantities_are_rejected(self):
        """Hedging a fabricated number does not make it measured."""
        self.assertRejected("Approximately 12 additional items are needed.")
        self.assertRejected("Roughly 200 more turns.")
        self.assertRejected("~15 files would change.")

    def test_assigning_estimator_inputs_is_rejected(self):
        self.assertRejected("Set unknowns: 4 for this item.")
        self.assertRejected("files: 11 would be touched.")

    def test_the_gate_applies_to_the_title(self):
        self.assertRejected("Missing item worth 200 turns", field="title")

    def test_the_gate_applies_to_breakdown_impact(self):
        self.assertRejected("Add an item of size large.",
                            field="breakdown_impact")

    def test_the_rejection_explains_why(self):
        problems = self.assertRejected("This will take 400 turns.")
        self.assertIn("effort", problems[0].lower())


class TestEnumeratedValues(unittest.TestCase):
    def test_an_invented_finding_type_is_rejected(self):
        self.assertTrue(F.validate_findings(
            document(finding(type="cost-estimate"))))

    def test_an_invented_severity_is_rejected(self):
        self.assertTrue(F.validate_findings(
            document(finding(severity="catastrophic"))))

    def test_duplicate_ids_are_rejected(self):
        problems = F.validate_findings(document(finding(), finding()))
        self.assertTrue(any("duplicate" in p for p in problems))


class TestCitations(unittest.TestCase):
    """An uncited external claim cannot be told from an invented one."""

    def _external(self, **kw):
        base = finding(id="F-010", type="approach-consideration",
                       severity="low",
                       title="Agent definitions are commonly version "
                             "controlled via the CLI",
                       rationale="A published pattern exists for ALM of agent "
                                 "definitions; the breakdown has no item for "
                                 "that path.")
        base.update(kw)
        return base

    def test_web_assisted_claim_without_a_source_is_rejected(self):
        problems = F.validate_findings(
            document(self._external(retrieved="2026-09-04"),
                     mode="web-assisted"))
        self.assertTrue(any("source" in p for p in problems))

    def test_web_assisted_claim_without_a_retrieval_date_is_rejected(self):
        problems = F.validate_findings(
            document(self._external(source="https://example.invalid/doc"),
                     mode="web-assisted"))
        self.assertTrue(any("retrieved" in p for p in problems))

    def test_a_cited_claim_passes(self):
        problems = F.validate_findings(
            document(self._external(source="https://example.invalid/doc",
                                    retrieved="2026-09-04"),
                     mode="web-assisted"))
        self.assertEqual(problems, [])

    def test_offline_mode_does_not_demand_a_citation(self):
        """Offline findings reason only about what they were given."""
        problems = F.validate_findings(document(self._external()))
        self.assertEqual(problems, [])


class TestBadInputExplainsItself(unittest.TestCase):
    """A stack trace says the interpreter was surprised, not what to fix.

    The researcher's own rule is to say so and stop when an input is missing.
    A raw FileNotFoundError is not saying so -- it is crashing, and it was
    what these scripts actually did until this suite existed.
    """

    SCRIPTS = os.path.join(SAMPLE, "skill", "build-work-researcher", "scripts")

    def _run(self, script, *args):
        import subprocess
        return subprocess.run(
            [sys.executable, os.path.join(self.SCRIPTS, script)] + list(args),
            capture_output=True, text=True, cwd=SAMPLE)

    def test_a_missing_specification_is_explained_not_traced(self):
        out = self._run("extract.py",
                        "--specification", "does/not/exist.md",
                        "--manifest", "examples/harbor-line-manifest.yaml")
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("Traceback", out.stderr)
        self.assertIn("was not found", out.stderr)

    def test_a_missing_specification_says_the_absence_is_the_finding(self):
        """The useful thing to tell someone with no specification."""
        out = self._run("extract.py",
                        "--specification", "does/not/exist.md",
                        "--manifest", "examples/harbor-line-manifest.yaml")
        self.assertIn("thin-specification", out.stderr)

    def test_a_missing_breakdown_is_explained(self):
        out = self._run("extract.py",
                        "--specification",
                        "scenarios/kestrel-financial/specification.md",
                        "--manifest", "does/not/exist.yaml")
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("Traceback", out.stderr)

    def test_a_missing_findings_file_is_explained(self):
        out = self._run("findings.py", "does/not/exist.yaml")
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("Traceback", out.stderr)
        self.assertIn("was not found", out.stderr)

    def test_render_explains_a_missing_findings_file(self):
        out = self._run("render_review.py", "does/not/exist.yaml")
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("Traceback", out.stderr)

    def test_an_empty_input_is_not_treated_as_valid(self):
        import tempfile
        empty = os.path.join(tempfile.mkdtemp(), "empty.yaml")
        open(empty, "w").close()
        out = self._run("findings.py", empty)
        self.assertEqual(out.returncode, 2)
        self.assertIn("empty", out.stderr)


class TestNoManifestWrites(unittest.TestCase):
    """A human decides what a finding means for the breakdown."""

    def _sources(self):
        root = os.path.join(SAMPLE, "skill", "build-work-researcher",
                            "scripts")
        for name in sorted(os.listdir(root)):
            if name.endswith(".py"):
                with open(os.path.join(root, name)) as fh:
                    yield name, fh.read()

    def test_no_researcher_module_opens_a_manifest_for_writing(self):
        for name, source in self._sources():
            lowered = source.lower()
            for marker in ('"w"', "'w'", '"a"', "'a'"):
                if marker in lowered and "manifest" in lowered:
                    # Only fail if a write mode and a manifest appear on one
                    # line -- the pairing is what would matter.
                    for line in source.splitlines():
                        low = line.lower()
                        self.assertFalse(
                            marker in low and "manifest" in low,
                            "%s appears to write a manifest: %s"
                            % (name, line.strip()))

    def test_no_researcher_module_imports_the_estimator_writer(self):
        for name, source in self._sources():
            self.assertNotIn("import estimate", source,
                             "%s must not drive the estimator" % name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
