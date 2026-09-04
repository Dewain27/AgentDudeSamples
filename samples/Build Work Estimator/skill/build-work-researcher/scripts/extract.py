#!/usr/bin/env python3
"""Mechanical half of a review: what the specification declares, and what the
breakdown appears to own.

Author: Dewain Robinson

This produces CANDIDATES, never findings. The distinction is the whole point.

A candidate is "identifier N5 appears in the specification and no work item
mentions anything like it". That is a lead, and leads are wrong often enough
that shipping them as findings would make the researcher a noise generator.

The evidence is direct. Running this gate by hand against the Kestrel
specification produced seven candidates, of which four were real missing
components, one was arguable, and one -- N10 -- was a plain false positive: the
specification says "Accessibility" and the work item says "WCAG 2.2 AA", so
keyword matching missed a real match that any reader would catch instantly.

That is why judgment is the product and this file is only its input. The
skill's instructions require every candidate to be triaged and let findings be
raised that this script never surfaced.

Nothing here computes an effort, a size, or a cost. It counts identifiers and
compares vocabularies.
"""

__author__ = "Dewain Robinson"

import argparse
import os
import re
import sys

#: Specification identifiers look like a letter-prefix plus a number: C1, N12,
#: S10, I7. Matched only where they stand alone, so "Section 9" and ordinary
#: prose do not become identifiers.
IDENTIFIER = re.compile(r"\b([A-Z]{1,2})(\d{1,2})\b")

#: Words carrying no discriminating power when comparing a requirement against
#: an item name. Without this, every item "matches" every requirement.
STOPWORDS = frozenset("""
a an and are as at be by for from has have in into is it its of on or that the
to with within must should shall will can may each all any per via using use
used support supports provide provides system service agent solution
""".split())

MIN_TOKEN = 4


def tokens(text):
    """Discriminating lowercase word stems from a piece of text.

    Short ALL-CAPS acronyms survive the length filter. RPO, RTO, SLA, KYC and
    CMK are among the most discriminating words a specification contains, and
    dropping them for being under four characters made a requirement look
    unmatched when an item named the same acronym -- a false positive
    manufactured by the tokeniser rather than found in the breakdown.
    """
    raw = str(text or "")
    acronyms = {a.lower() for a in re.findall(r"\b[A-Z]{2,5}\b", raw)}
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]+", raw.lower())
    out = set()
    for word in words:
        if word in STOPWORDS:
            continue
        if len(word) < MIN_TOKEN and word not in acronyms:
            continue
        out.add(word)
        # A crude singular so "runbooks" matches "runbook".
        if word.endswith("s") and len(word) > MIN_TOKEN:
            out.add(word[:-1])
    return out


def declared_identifiers(specification_text):
    """Identifiers the specification declares, with the line each appears on.

    Keeps the first mention only: a requirement is declared once and then
    referenced, and the declaration carries the description worth matching.
    """
    found = {}
    for number, line in enumerate(specification_text.splitlines(), 1):
        for prefix, digits in IDENTIFIER.findall(line):
            ident = "%s%s" % (prefix, digits)
            if ident not in found:
                found[ident] = {"id": ident, "line": number,
                                "text": line.strip()}
    return found


def item_vocabulary(items):
    """Every discriminating word the work breakdown uses, and per-item sets."""
    per_item, everything = [], set()
    for item in items or []:
        name = item.get("name") if isinstance(item, dict) else str(item)
        words = tokens(name)
        per_item.append({"name": name, "tokens": words})
        everything |= words
    return per_item, everything


def candidates(specification_text, items, min_overlap=1):
    """Identifiers whose description shares no vocabulary with any item.

    `min_overlap` is a matching threshold, not an effort figure: how many
    discriminating words a requirement and an item must share before the
    requirement counts as plausibly owned.
    """
    declared = declared_identifiers(specification_text)
    per_item, _all_tokens = item_vocabulary(items)

    out = []
    for ident, entry in sorted(declared.items()):
        # Strip the identifier itself so it cannot match itself.
        description = entry["text"]
        words = tokens(re.sub(r"\b%s\b" % re.escape(ident), " ", description))
        if not words:
            continue

        best, best_overlap = None, 0
        for item in per_item:
            overlap = len(words & item["tokens"])
            if overlap > best_overlap:
                best, best_overlap = item["name"], overlap

        if best_overlap < min_overlap:
            out.append({
                "id": ident,
                "line": entry["line"],
                "text": description,
                "closest_item": best,
                "shared_words": best_overlap,
            })
    return out


def render(cands, specification, manifest):
    """A triage worksheet, explicitly not a findings list."""
    lines = ["# Review candidates", ""]
    lines.append("Specification: `%s`" % specification)
    lines.append("Breakdown: `%s`" % manifest)
    lines.append("")
    lines.append("**These are candidates, not findings.** Each one is a "
                 "requirement whose wording")
    lines.append("shares no discriminating vocabulary with any work item. That "
                 "is a lead worth")
    lines.append("checking, and nothing more -- matching by words alone "
                 "produces false positives")
    lines.append("(a requirement saying *Accessibility* against an item saying "
                 "*WCAG 2.2 AA* looks")
    lines.append("unmatched and plainly is not). Triage every row before any "
                 "of it becomes a")
    lines.append("finding, and raise findings this list never surfaced.")
    lines.append("")

    if not cands:
        lines.append("No unmatched requirements. That is not the same as a "
                     "complete breakdown --")
        lines.append("it means word matching found nothing, so read for what "
                     "matching cannot see.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Ref | Line | Requirement | Closest item |")
    lines.append("| --- | ---: | --- | --- |")
    for c in cands:
        text = c["text"]
        if len(text) > 90:
            text = text[:87] + "..."
        lines.append("| %s | %d | %s | %s |"
                     % (c["id"], c["line"], text.replace("|", "\\|"),
                        c["closest_item"] or "_nothing similar_"))
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--specification", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--min-overlap", type=int, default=1,
                    help="shared words required before a requirement counts "
                         "as plausibly owned (default: 1)")
    ap.add_argument("--out", help="write the worksheet here")
    args = ap.parse_args(argv)

    sys.path.insert(0, _estimator_scripts())
    import miniyaml
    from findings import InputError, read_text

    try:
        spec_text = read_text(
            args.specification, "The specification",
            "\nA review needs something to review AGAINST. If the project "
            "genuinely has no\nwritten specification, that is not a blocker "
            "to work around -- it IS the finding,\nand the honest one: a "
            "breakdown sized from nothing cannot be checked for\n"
            "completeness. Record it as a `thin-specification` finding and "
            "say so plainly.")
        manifest = miniyaml.load(read_text(
            args.manifest, "The breakdown",
            "\nThis is the manifest whose `items:` are being checked for "
            "completeness."))
    except InputError as exc:
        print("%s" % exc, file=sys.stderr)
        return 2
    except Exception as exc:                      # miniyaml parse failures
        print("The breakdown could not be parsed:\n  %s\n  %s"
              % (args.manifest, exc), file=sys.stderr)
        return 2

    items = (manifest or {}).get("items")
    if not items:
        print("The breakdown declares no `items:`, so there is nothing to "
              "check the\nspecification against:\n  %s" % args.manifest,
              file=sys.stderr)
        return 2

    cands = candidates(spec_text, items, args.min_overlap)
    text = render(cands, args.specification, args.manifest)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        print("wrote %s (%d candidate(s) to triage)" % (args.out, len(cands)))
    else:
        print(text)
    return 0


def _estimator_scripts():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(
        here, "..", "..", "build-work-estimator", "scripts"))


if __name__ == "__main__":
    sys.exit(main())
