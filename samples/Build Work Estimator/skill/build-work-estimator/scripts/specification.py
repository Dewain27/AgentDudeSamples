#!/usr/bin/env python3
"""Specifications behind an estimate -- always asked for, never assumed.

Author: Dewain Robinson

An estimate sized without a specification is sizing from vibes. The work
breakdown asks how big each item is, and the honest answer to that question
depends entirely on whether anyone has written down what the item does.

So the estimator ALWAYS asks for both a functional and a technical
specification, and records the answer. It does not refuse to run without them
-- early estimates are legitimate and useful -- but it refuses to be quiet
about their absence, because a confident figure sized from nothing is exactly
the failure this tool exists to prevent.

Answers are recorded verbatim in the report, so a reader can see what the
number was actually derived from.
"""

__author__ = "Dewain Robinson"

NONE_ANSWERS = ("none", "no", "n/a", "na", "not available", "-", "")

#: Maturity of a specification, and what it means for confidence.
STATUS_CONFIDENCE = {
    "approved": ("high", "Signed off. Sizes rest on agreed scope."),
    "in-review": ("medium", "Under review; scope may still move."),
    "draft": ("low", "Draft only. Sizes will move as it settles."),
    "none": ("very low", "No specification. Sizes are informed guesses."),
}
VALID_STATUS = tuple(STATUS_CONFIDENCE)


class SpecificationError(Exception):
    """Raised when the specification block is missing or malformed."""


def _looks_absent(value):
    return str(value or "").strip().lower() in NONE_ANSWERS


def normalise(config):
    """Validate the manifest's `specification:` block.

    The block is REQUIRED. Its contents may say 'none' -- that is a valid,
    recorded answer -- but the question may not go unanswered, because an
    unanswered question is indistinguishable in the output from a specified
    build.
    """
    if config is None:
        raise SpecificationError(
            "specification is required.\n\n"
            "Every estimate must record what it was sized from. Add:\n\n"
            "  specification:\n"
            "    functional: <path, URL, or short description>\n"
            "    technical:  <path, URL, or short description>\n"
            "    status:     approved | in-review | draft | none\n\n"
            "`none` is an acceptable answer for either. It is not acceptable "
            "to leave the\nquestion unanswered -- an estimate sized without a "
            "specification is sizing from\nvibes, and the report has to say "
            "so rather than look identical to one that\nrested on agreed "
            "scope."
        )
    if not isinstance(config, dict):
        raise SpecificationError(
            "specification must be a mapping with `functional` and "
            "`technical` keys.")

    out = {}
    for key in ("functional", "technical"):
        if key not in config:
            raise SpecificationError(
                "specification.%s is required. Give a path, a URL, a short "
                "description, or\nthe literal `none` -- but answer it." % key)
        raw = config[key]
        out[key] = None if _looks_absent(raw) else str(raw).strip()

    status = str(config.get("status", "") or "").strip().lower()
    if not status:
        # Infer rather than nag, but only when the answer is unambiguous.
        status = "none" if not (out["functional"] or out["technical"]) \
            else "draft"
    if status not in VALID_STATUS:
        raise SpecificationError(
            "specification.status must be one of: %s (got %r)"
            % (", ".join(VALID_STATUS), config.get("status")))
    out["status"] = status

    if (out["functional"] or out["technical"]) and status == "none":
        raise SpecificationError(
            "specification.status is `none` but a specification was given. "
            "Use draft,\nin-review, or approved.")
    if not (out["functional"] or out["technical"]) and status != "none":
        raise SpecificationError(
            "specification.status is %r but neither a functional nor a "
            "technical\nspecification was given. Use status: none." % status)

    confidence, note = STATUS_CONFIDENCE[status]
    out["confidence"] = confidence
    out["confidence_note"] = note
    out["complete"] = bool(out["functional"] and out["technical"])
    out["absent"] = not (out["functional"] or out["technical"])
    return out


def interview(prompt=input, echo=print):
    """Ask for both specifications. Always. There is no skip."""
    echo("")
    echo("=" * 68)
    echo("What was this sized from?")
    echo("")
    echo("An estimate without a specification behind it is sizing from vibes.")
    echo("Answer both. `none` is an acceptable answer; silence is not.")
    echo("")
    functional = prompt(
        "  Functional specification (path, URL, description, or 'none'): ")
    technical = prompt(
        "  Technical specification  (path, URL, description, or 'none'): ")

    if _looks_absent(functional) and _looks_absent(technical):
        echo("")
        echo("  No specification. The estimate will carry a low-confidence")
        echo("  warning, and the sizes in it are informed guesses rather than")
        echo("  measurements of agreed scope.")
        return {"functional": "none", "technical": "none", "status": "none"}

    status = ""
    while status not in VALID_STATUS or status == "none":
        status = prompt(
            "  Status [approved / in-review / draft]: ").strip().lower()
        if status == "none":
            echo("    A specification was given, so `none` does not apply.")
        elif status not in VALID_STATUS:
            echo("    Expected approved, in-review or draft.")
    return {"functional": functional, "technical": technical,
            "status": status}


def normalise_review(config):
    """Validate the manifest's optional `research_review:` block.

    A review is DECLARED, never inferred. The estimator cannot tell whether a
    breakdown was challenged, and it does not pretend to -- it records that
    someone says it was, because "reviewed, three findings knowingly accepted"
    is a materially different confidence signal from "never reviewed".

    Absent is allowed and reported, exactly as a missing specification is.
    """
    if config is None:
        return {"declared": False}

    if not isinstance(config, dict):
        raise SpecificationError(
            "research_review must be a mapping:\n\n"
            "  research_review:\n"
            "    reviewed: 2026-09-04\n"
            "    findings_total: 14\n"
            "    findings_addressed: 11\n"
            "    findings_accepted_as_is: 3\n")

    def _count(key):
        raw = config.get(key, 0) or 0
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise SpecificationError(
                "research_review.%s must be a whole number, got %r"
                % (key, raw))
        if value < 0:
            raise SpecificationError(
                "research_review.%s cannot be negative." % key)
        return value

    total = _count("findings_total")
    addressed = _count("findings_addressed")
    accepted = _count("findings_accepted_as_is")

    if addressed + accepted > total:
        raise SpecificationError(
            "research_review: %d addressed + %d accepted exceeds %d total. "
            "Every finding is one or the other, or still open."
            % (addressed, accepted, total))

    return {
        "declared": True,
        "reviewed": str(config.get("reviewed") or "").strip() or None,
        "findings_total": total,
        "findings_addressed": addressed,
        "findings_accepted_as_is": accepted,
        "findings_open": total - addressed - accepted,
    }


def render_review_markdown(review):
    """Report section: was the breakdown challenged, and what came of it."""
    out = ["### Was the breakdown challenged?", ""]

    if not review or not review.get("declared"):
        out.append("> **No research review is recorded.** This estimate prices "
                   "the breakdown as\n> written. Nothing has checked whether "
                   "it is complete, whether an item is\n> plausibly sized, or "
                   "whether the specification is detailed enough to size\n> "
                   "from at all.")
        out.append("")
        out.append("Reviewing it is an available improvement, and the "
                   "breakdown is the weakest\ninput in the whole estimate.")
        out.append("")
        return "\n".join(out)

    out.append("A review is **declared**, not verified. The estimator records "
               "that someone\nchallenged the breakdown; it cannot judge how "
               "well.")
    out.append("")
    out.append("| | Findings |")
    out.append("| --- | ---: |")
    out.append("| Raised | %d |" % review["findings_total"])
    out.append("| Addressed in the breakdown | %d |"
               % review["findings_addressed"])
    out.append("| Knowingly accepted as-is | %d |"
               % review["findings_accepted_as_is"])
    if review["findings_open"]:
        out.append("| **Still open** | **%d** |" % review["findings_open"])
    out.append("")
    if review.get("reviewed"):
        out.append("Reviewed %s." % review["reviewed"])
        out.append("")
    if review["findings_open"]:
        out.append("> **%d finding%s neither addressed nor accepted.** The "
                   "breakdown this estimate\n> prices is known to be "
                   "incomplete."
                   % (review["findings_open"],
                      "" if review["findings_open"] == 1 else "s"))
        out.append("")
    return "\n".join(out)


def render_markdown(spec):
    """Report section recording what the estimate was sized from."""
    out = ["## What this was sized from", ""]

    if spec["absent"]:
        out.append("> ### ⚠ NO SPECIFICATION")
        out.append(">")
        out.append("> This estimate was produced without a functional or a "
                   "technical specification.")
        out.append(">")
        out.append("> **Every size in the breakdown is an informed guess.** "
                   "The turn medians behind\n> them are measured, but what "
                   "they are applied to is not — nobody has written\n> down "
                   "what these items do. Treat the range as wide and the "
                   "point figure as\n> indicative only.")
        out.append(">")
        out.append("> The single highest-value thing that could be done to "
                   "improve this estimate is\n> to write the specification "
                   "and run it again.")
        out.append("")
        return "\n".join(out)

    out.append("| | Reference |")
    out.append("| --- | --- |")
    out.append("| Functional specification | %s |"
               % (spec["functional"] or "**not provided**"))
    out.append("| Technical specification | %s |"
               % (spec["technical"] or "**not provided**"))
    out.append("| Status | `%s` — %s |"
               % (spec["status"], spec["confidence_note"]))
    out.append("| Confidence in sizing | **%s** |" % spec["confidence"])
    out.append("")

    if not spec["complete"]:
        missing = "technical" if spec["functional"] else "functional"
        out.append("> **Only one half was provided.** Without the %s "
                   "specification, sizes rest on\n> a partial picture. "
                   "Expect the range to be wider than it looks." % missing)
        out.append("")
    if spec["status"] == "draft":
        out.append("> **The specification is a draft.** Sizes will move as it "
                   "settles, and a draft\n> that grows is the most common "
                   "reason a build overruns its estimate.")
        out.append("")
    return "\n".join(out)
