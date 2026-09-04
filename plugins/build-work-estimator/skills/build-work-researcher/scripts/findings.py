#!/usr/bin/env python3
"""The boundary, enforced mechanically rather than trusted.

Author: Dewain Robinson

The researcher exists to improve a work breakdown's COMPLETENESS. It surfaces
components the specification requires but the breakdown does not own, questions
a size without proposing one, and names unknowns nobody declared.

It must never produce a number that could enter the estimate. That is not a
style preference: the estimator's whole value is that every figure traces to
something measured, published, or declared by a human who knew the answer. A
model-supplied size would be a guess wearing the same clothes as a measurement,
and it would enter the arithmetic through a field nobody thought to guard.

So the boundary is defended twice:

  SCHEMA      A finding has a fixed set of keys and none of them can hold a
              size, a turn count, or a cost. Unknown keys are rejected, so
              `suggested_size: large` cannot be smuggled in as an extra field.
              A boundary the format cannot express cannot be crossed by
              accident.

  TEXT SCAN   The schema stops structured assertions but not prose. "This will
              take about 400 turns" fits perfectly well in a rationale field,
              so the prose is scanned for effort and cost assertions too.

Defence in depth, because the schema and the scan fail in different ways.

A NOTE ON QUANTITIES THAT ARE NOT ASSERTIONS
--------------------------------------------
A finding may legitimately need to point at a requirement that contains a
number -- "the 900-concurrent-session target has no load-testing item". The
scan is therefore aimed narrowly at EFFORT and COST assertions (turns, hours,
days, dollars, bare percentages, bare sizes), not at digits in general, and
`spec_reference` is exempt because a citation like "§9 S7" is not a claim.

Where a requirement's magnitude still trips the scan, the fix is to cite it by
identifier rather than restate it -- "N4's availability target" instead of
"99.9%". That reads better anyway, and it keeps the researcher pointing at the
specification rather than paraphrasing numbers out of it.
"""

__author__ = "Dewain Robinson"

import argparse
import os
import re
import sys

#: Every key a finding may carry. There is deliberately nowhere to put a size,
#: a turn count, an hour figure, or a cost. Adding one here is a decision to
#: weaken the boundary and should be argued for on its own terms.
FINDING_KEYS = {
    "id",
    "type",
    "severity",
    "title",
    "rationale",
    "spec_reference",
    "breakdown_impact",
    "source",
    "retrieved",
    "status",
}

REQUIRED_FINDING_KEYS = {"id", "type", "severity", "title", "rationale"}

#: Prose fields the text scan applies to. `spec_reference` is excluded: it is
#: a citation, not a claim, and "§9 S7" should never be read as an assertion.
SCANNED_FIELDS = ("title", "rationale", "breakdown_impact")

FINDING_TYPES = {
    "missing-component",
    "thin-specification",
    "unstated-unknown",
    "sizing-rationale",
    "scope-question",
    "approach-consideration",
}

SEVERITIES = {"high", "medium", "low"}
STATUSES = {"open", "addressed", "accepted-as-is"}
MODES = {"offline", "web-assisted"}

DOCUMENT_KEYS = {
    "schema", "reviewed", "specification", "manifest", "mode", "findings",
}
REQUIRED_DOCUMENT_KEYS = {"schema", "reviewed", "mode", "findings"}

#: Effort and cost assertions. Each carries the reason it is banned, which is
#: printed with the rejection -- a validator that says only "invalid" teaches
#: nobody why the boundary exists.
BANNED_PATTERNS = (
    (re.compile(r"\d+(?:\.\d+)?\s*(?:turns?|hours?|days?|weeks?|sprints?)",
                re.I),
     "asserts an effort figure; effort is the estimator's to compute from "
     "measured medians, never the researcher's to guess"),
    (re.compile(r"\$\s*\d"),
     "asserts a cost; the researcher never produces money"),
    (re.compile(r"\d+(?:\.\d+)?\s*%"),
     "quantifies an impact; say WHAT would change, never by how much"),
    (re.compile(r"\bsize\b\s*[:=]?\s*"
                r"(?:exploration|trivial|small|medium|large)\b", re.I),
     "proposes a size; a suggested size is an anchor and people accept "
     "defaults, so the human sizes it"),
    # `~` is not a word character, so it cannot sit behind \b -- an earlier
    # version grouped it with the words and the tilde branch could never fire.
    (re.compile(r"(?:\b(?:roughly|approximately|around|about|circa)|~)\s*\d",
                re.I),
     "hedged quantity; hedging a fabricated number does not make it measured"),
    (re.compile(r"\b(?:files?|unknowns?|eval_cases)\b\s*[:=]\s*\d", re.I),
     "assigns an estimator input directly"),
)


class InputError(Exception):
    """Raised for a missing or unusable input the user must fix.

    A stack trace tells someone the interpreter was surprised. It does not
    tell them what to do. Every other module in this codebase answers a bad
    input with an explanation, and these scripts are no exception.
    """


def read_text(path, what, guidance=""):
    """Read a required input, or explain precisely what is wrong with it."""
    if not os.path.exists(path):
        raise InputError(
            "%s was not found:\n  %s\n%s" % (what, path, guidance))
    if os.path.isdir(path):
        raise InputError(
            "%s is a directory, not a file:\n  %s" % (what, path))
    try:
        with open(path) as fh:
            text = fh.read()
    except OSError as exc:
        raise InputError("%s could not be read:\n  %s\n  %s"
                         % (what, path, exc))
    if not text.strip():
        raise InputError("%s is empty:\n  %s" % (what, path))
    return text


class FindingsError(Exception):
    """Raised for a findings document that breaches the boundary."""


def scan_text(text):
    """Return the reasons a piece of prose breaches the boundary."""
    if not text:
        return []
    return [reason for pattern, reason in BANNED_PATTERNS
            if pattern.search(str(text))]


def validate_findings(doc):
    """Check a findings document against the schema and the boundary.

    Returns a list of problems. Empty means the document carries no number
    that could enter an estimate -- structurally or in prose.
    """
    problems = []

    if not isinstance(doc, dict):
        return ["findings document must be a mapping"]

    unknown = set(doc) - DOCUMENT_KEYS
    for key in sorted(unknown):
        problems.append(
            "unknown top-level key %r. The schema is closed on purpose: an "
            "unknown key is where a number would enter unnoticed" % key)
    for key in sorted(REQUIRED_DOCUMENT_KEYS - set(doc)):
        problems.append("missing required key %r" % key)

    mode = doc.get("mode")
    if mode is not None and mode not in MODES:
        problems.append("mode must be one of: %s (got %r)"
                        % (", ".join(sorted(MODES)), mode))

    findings = doc.get("findings")
    if findings is None:
        findings = []
    if not isinstance(findings, list):
        return problems + ["findings must be a list"]

    seen_ids = set()
    for index, finding in enumerate(findings, 1):
        problems.extend(_validate_one(finding, index, mode, seen_ids))

    return problems


def _validate_one(finding, index, mode, seen_ids):
    problems = []
    where = "finding %d" % index

    if not isinstance(finding, dict):
        return ["%s must be a mapping" % where]

    ident = finding.get("id")
    if ident:
        where = "finding %s" % ident
        if ident in seen_ids:
            problems.append("%s: duplicate id" % where)
        seen_ids.add(ident)

    # The schema gate. An unknown key is the whole attack surface for a
    # structured number, so it is refused rather than ignored.
    for key in sorted(set(finding) - FINDING_KEYS):
        problems.append(
            "%s: unknown key %r. There is no field for a size, a turn count, "
            "or a cost, and adding one is how the boundary would be lost"
            % (where, key))
    for key in sorted(REQUIRED_FINDING_KEYS - set(finding)):
        problems.append("%s: missing required key %r" % (where, key))

    kind = finding.get("type")
    if kind is not None and kind not in FINDING_TYPES:
        problems.append("%s: type must be one of: %s (got %r)"
                        % (where, ", ".join(sorted(FINDING_TYPES)), kind))

    severity = finding.get("severity")
    if severity is not None and severity not in SEVERITIES:
        problems.append("%s: severity must be one of: %s (got %r)"
                        % (where, ", ".join(sorted(SEVERITIES)), severity))

    status = finding.get("status")
    if status is not None and status not in STATUSES:
        problems.append("%s: status must be one of: %s (got %r)"
                        % (where, ", ".join(sorted(STATUSES)), status))

    # The prose gate.
    for field in SCANNED_FIELDS:
        for reason in scan_text(finding.get(field)):
            problems.append("%s: %s %s" % (where, field, reason))

    # An external claim without a citation is indistinguishable from an
    # invention, so web-assisted findings must say where the claim came from.
    if mode == "web-assisted" and kind == "approach-consideration":
        if not finding.get("source"):
            problems.append(
                "%s: web-assisted approach-consideration has no `source`. An "
                "uncited external claim cannot be told apart from a made-up "
                "one" % where)
        if not finding.get("retrieved"):
            problems.append(
                "%s: web-assisted approach-consideration has no `retrieved` "
                "date. Pages change, and a claim with no retrieval date "
                "cannot be re-checked" % where)

    return problems


def summarise(doc):
    """Counts a reviewer needs to triage, and nothing that looks like effort."""
    findings = doc.get("findings") or []
    by_type, by_severity, by_status = {}, {}, {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        by_type[finding.get("type")] = by_type.get(finding.get("type"), 0) + 1
        by_severity[finding.get("severity")] = (
            by_severity.get(finding.get("severity"), 0) + 1)
        by_status[finding.get("status", "open")] = (
            by_status.get(finding.get("status", "open"), 0) + 1)
    return {
        "total": len(findings),
        "by_type": by_type,
        "by_severity": by_severity,
        "by_status": by_status,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("findings", help="path to a findings.yaml")
    args = ap.parse_args(argv)

    sys.path.insert(0, _estimator_scripts())
    import miniyaml

    try:
        doc = miniyaml.load(read_text(
            args.findings, "The findings file",
            "\nWrite findings first, or see references/findings-schema.md "
            "for the shape."))
    except InputError as exc:
        print("%s" % exc, file=sys.stderr)
        return 2

    problems = validate_findings(doc)
    if problems:
        print("FINDINGS REJECTED:\n", file=sys.stderr)
        for problem in problems:
            print("  - %s" % problem, file=sys.stderr)
        print("\nThe researcher produces structure and questions, never "
              "numbers.", file=sys.stderr)
        return 1

    stats = summarise(doc)
    print("findings valid: %d finding(s), no effort or cost assertion"
          % stats["total"])
    return 0


def _estimator_scripts():
    """The estimator's scripts, for the shared YAML reader."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(
        here, "..", "..", "build-work-estimator", "scripts"))


if __name__ == "__main__":
    sys.exit(main())
