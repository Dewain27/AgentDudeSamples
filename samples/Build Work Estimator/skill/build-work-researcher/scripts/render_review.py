#!/usr/bin/env python3
"""Render a validated findings document as a review a human can act on.

Author: Dewain Robinson

Rendering happens only after `validate_findings` passes, so nothing reaches the
page that the boundary would have rejected. The renderer adds no analysis of
its own: it orders findings by severity and prints what the reviewer wrote.

The review states how many of its findings would actually change the breakdown,
because a review raising fourteen items costs human time to triage and the
noise should be visible rather than flattering.
"""

__author__ = "Dewain Robinson"

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import findings as F  # noqa: E402

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

TYPE_LABELS = {
    "missing-component": "Missing component",
    "thin-specification": "Specification too thin to size",
    "unstated-unknown": "Unstated unknown",
    "sizing-rationale": "Sizing rationale",
    "scope-question": "Scope question",
    "approach-consideration": "Approach consideration",
}

#: Types that argue for a change to the breakdown itself. An
#: approach-consideration may be interesting without changing anything.
CHANGES_BREAKDOWN = {
    "missing-component", "thin-specification", "unstated-unknown",
    "sizing-rationale", "scope-question",
}


def render(doc):
    stats = F.summarise(doc)
    items = [f for f in (doc.get("findings") or []) if isinstance(f, dict)]
    items.sort(key=lambda f: (SEVERITY_ORDER.get(f.get("severity"), 9),
                              str(f.get("id"))))

    actionable = sum(1 for f in items if f.get("type") in CHANGES_BREAKDOWN)

    out = ["# Research review", ""]
    out.append("**Author:** Dewain Robinson")
    out.append("")
    out.append("| | |")
    out.append("| --- | --- |")
    out.append("| Reviewed | %s |" % (doc.get("reviewed") or "not stated"))
    out.append("| Specification | `%s` |"
               % (doc.get("specification") or "not stated"))
    out.append("| Breakdown | `%s` |" % (doc.get("manifest") or "not stated"))
    out.append("| Mode | %s |" % (doc.get("mode") or "not stated"))
    out.append("")

    out.append("## What this review is, and is not")
    out.append("")
    out.append("It reports **structure and questions, never numbers.** It "
               "names work the breakdown\nappears to be missing, questions a "
               "size without proposing one, and points at\nunknowns nobody "
               "declared. Every size stays a human's to set.")
    out.append("")
    out.append("It does **not** validate the specification against reality. It "
               "checks the breakdown\nagainst the specification. Whether that "
               "specification describes a system which\nwill work is a "
               "different question, asked elsewhere.")
    out.append("")

    out.append("## Summary")
    out.append("")
    out.append("**%d finding%s, of which %d would change the breakdown.**"
               % (stats["total"], "" if stats["total"] == 1 else "s",
                  actionable))
    out.append("")
    if stats["total"]:
        out.append("| Severity | Findings |")
        out.append("| --- | ---: |")
        for level in ("high", "medium", "low"):
            if stats["by_severity"].get(level):
                out.append("| %s | %d |"
                           % (level.title(), stats["by_severity"][level]))
        out.append("")

    if not items:
        out.append("Nothing was found that would change the breakdown. That is "
                   "a real result, not\na formality -- but it is bounded by "
                   "what a review of documents can see.")
        out.append("")
        return "\n".join(out)

    out.append("## Findings")
    out.append("")
    for finding in items:
        out.append("### %s — %s" % (finding.get("id"), finding.get("title")))
        out.append("")
        out.append("*%s · %s severity*"
                   % (TYPE_LABELS.get(finding.get("type"),
                                      finding.get("type")),
                      finding.get("severity")))
        out.append("")
        out.append(str(finding.get("rationale", "")).strip())
        out.append("")
        if finding.get("spec_reference"):
            out.append("**Where:** %s" % finding["spec_reference"])
            out.append("")
        if finding.get("breakdown_impact"):
            out.append("**What it would change:** %s"
                       % str(finding["breakdown_impact"]).strip())
            out.append("")
        if finding.get("source"):
            cited = finding["source"]
            if finding.get("retrieved"):
                cited += " (retrieved %s)" % finding["retrieved"]
            out.append("**Source:** %s" % cited)
            out.append("")
        if finding.get("status") and finding["status"] != "open":
            out.append("**Status:** %s" % finding["status"])
            out.append("")

    out.append("## What to do with this")
    out.append("")
    out.append("Each finding is a question for a human, not an instruction. "
               "Decide whether it\nchanges the breakdown, then record the "
               "outcome in the manifest so the estimate\nsays the breakdown "
               "was challenged:")
    out.append("")
    out.append("```yaml")
    out.append("research_review:")
    # Quoted: PyYAML reads a bare date as a date object while the bundled
    # reader gives a string, and the two disagreeing is a portability trap.
    out.append('  reviewed: "%s"' % (doc.get("reviewed") or "YYYY-MM-DD"))
    out.append("  findings_total: %d" % stats["total"])
    out.append("  findings_addressed: <how many changed the breakdown>")
    out.append("  findings_accepted_as_is: <how many you knowingly accepted>")
    out.append("```")
    out.append("")
    out.append("The estimator records that block as **declared**. It does not "
               "verify the review's\nquality, only that one happened — because "
               "\"reviewed, three findings knowingly\naccepted\" is a "
               "materially different signal from \"never reviewed\".")
    out.append("")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("findings", help="path to a validated findings.yaml")
    ap.add_argument("--out", help="write the review here")
    args = ap.parse_args(argv)

    sys.path.insert(0, F._estimator_scripts())
    import miniyaml

    with open(args.findings) as fh:
        doc = miniyaml.load(fh.read())

    # Rendering a document that breaches the boundary would put the very
    # numbers the validator exists to stop onto a page someone then trusts.
    problems = F.validate_findings(doc)
    if problems:
        print("REFUSING TO RENDER: the findings breach the boundary.\n",
              file=sys.stderr)
        for problem in problems:
            print("  - %s" % problem, file=sys.stderr)
        return 1

    text = render(doc)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        print("wrote %s" % args.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
