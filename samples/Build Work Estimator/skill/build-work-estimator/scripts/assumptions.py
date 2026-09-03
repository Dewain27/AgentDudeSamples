#!/usr/bin/env python3
"""Which parts of the number are measured, and which are judgment.

Author: Dewain Robinson

An estimate mixes two kinds of input and they are not equally trustworthy:

  MEASURED    Cost per turn, bucket turn medians, cache behaviour -- derived
              from real session history. Published rates with a source URL and
              a verification date.

  JUDGED      Multipliers and shares that shape the result but were never
              measured against anything. A brownfield factor of 1.5 is a
              guess. So is 25% remediation per cycle.

Presenting both without distinction makes the judged parts look derived, which
is the exact failure this estimator exists to prevent. So every judgment factor
is registered here with its value and what it does, and the report lists them.

A reader can then see which parts of the figure would move if someone measured
them, and which would not.
"""

__author__ = "Dewain Robinson"

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def registry():
    """Every unmeasured factor that shapes an estimate."""
    import estimate
    import environments
    import target_platform

    return [
        {
            "name": "Brownfield factor",
            "value": estimate.BROWNFIELD_FACTOR,
            "display": "%.2fx" % estimate.BROWNFIELD_FACTOR,
            "effect": "Multiplies turns for work in an existing codebase.",
            "basis": "Judgment. Never measured against paired greenfield and "
                     "brownfield work.",
        },
        {
            "name": "Remediation share per cycle",
            "value": estimate.REMEDIATION_SHARE,
            "display": "%.0f%%" % (estimate.REMEDIATION_SHARE * 100),
            "effect": "Each evaluation cycle after the first adds this share "
                      "of the build back as rework.",
            "basis": "Judgment. Real remediation depends on what the "
                     "evaluations actually find.",
        },
        {
            "name": "Unknowns range widening",
            "value": estimate.UNKNOWNS_RANGE_STEP,
            "display": "+%.0f%% per unknown" % (
                estimate.UNKNOWNS_RANGE_STEP * 100),
            "effect": "Widens the upper bound of an item per declared unknown.",
            "basis": "Judgment. The declared unknown count is itself a "
                     "subjective input.",
        },
        {
            "name": "Environment provisioning share",
            "value": environments.DEFAULT_PROVISIONING_SHARE,
            "display": "%.0f%% per extra environment" % (
                environments.DEFAULT_PROVISIONING_SHARE * 100),
            "effect": "Cost of applying infrastructure and pipeline work into "
                      "each environment beyond the first.",
            "basis": "Judgment. Override it with "
                     "`environments.provisioning_share` if you have a real "
                     "figure.",
        },
        {
            "name": "Evaluation cycle range",
            "value": (target_platform.CYCLES_LOW_DELTA,
                      target_platform.CYCLES_HIGH_DELTA),
            "display": "%+d / %+d cycles" % (target_platform.CYCLES_LOW_DELTA,
                                             target_platform.CYCLES_HIGH_DELTA),
            "effect": "Produces the low and high bounds on the target side.",
            "basis": "Judgment. Nobody knows how many cycles a build will "
                     "need until it runs.",
        },
        {
            "name": "Correction shrinkage k",
            "value": estimate.CORRECTION_SHRINKAGE_K,
            "display": "k = %d" % estimate.CORRECTION_SHRINKAGE_K,
            "effect": "Pulls recorded actuals toward 1.0 so one data point "
                      "cannot swing later estimates.",
            "basis": "Judgment, but a deliberately conservative one: it only "
                     "ever reduces the influence of thin data.",
        },
    ]


def render_markdown(result):
    """Report section separating what was measured from what was judged."""
    profile = result.get("profile") or {}
    out = ["## What is measured, and what is judgment", ""]
    out.append("This estimate mixes two kinds of input. They are not equally "
               "trustworthy, and\nthe difference is not visible in the "
               "figures themselves.")
    out.append("")

    out.append("### Measured or sourced")
    out.append("")
    out.append("| Input | Basis |")
    out.append("| --- | --- |")
    if profile.get("source") == "measured":
        out.append("| Cost per agent turn, bucket turn medians, cache "
                   "behaviour | Derived from %d real local session%s |"
                   % (profile.get("sessions", 0),
                      "" if profile.get("sessions") == 1 else "s"))
    else:
        out.append("| Cost per agent turn, bucket turn medians | **Published "
                   "baselines, not measured here** — materially less reliable |")
    out.append("| Every provider rate | Published, each carrying a source URL "
               "and a verification date |")
    out.append("| Evaluation volume | Arithmetic on declared test cases, "
               "repeats and cycles |")
    out.append("| Azure consumption | Figures supplied by you; nothing is "
               "bundled or inferred |")
    out.append("")

    out.append("### Judgment, not measurement")
    out.append("")
    out.append("These shape the result and **were never measured against "
               "anything**. They are\nstated here so a reader can see which "
               "parts of the number would move if someone\nmeasured them.")
    out.append("")
    out.append("| Factor | Value | What it does |")
    out.append("| --- | --- | --- |")
    for entry in registry():
        out.append("| %s | **%s** | %s %s |"
                   % (entry["name"], entry["display"], entry["effect"],
                      entry["basis"]))
    out.append("")
    out.append("> **Nothing here is invented at report time.** Every figure "
               "above is either\n> measured, supplied by you, or one of the "
               "listed factors applied to those. Where\n> the estimator "
               "cannot attribute a cost honestly — target credits with no "
               "declared\n> evaluation cases, for instance — it says so "
               "rather than distributing the total\n> to make the table look "
               "complete.")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Provenance: no number in a report unless its derivation is recorded
# --------------------------------------------------------------------------
#
# The rule this enforces: a figure may appear in a report only if the
# estimator can say where it came from. Not "it looks about right" -- an
# actual derivation, traceable to measured history, a published rate with a
# source URL, a value the user declared, or arithmetic on those.
#
# Enforcement is mechanical rather than aspirational. The ledger is built from
# the computed result, and the rendered report is checked against it. A money
# figure with no matching derivation fails validation, which fails the build.

import re as _re

#: Money and large grouped numbers are the substantive claims in a report.
#: Small bare integers are counts, percentages and section numbers whose
#: provenance is the manifest itself, so they are not policed here.
_MONEY = _re.compile(r"\$([\d,]+\.\d{2})")
_GROUPED = _re.compile(r"(?<![\d.$])(\d{1,3}(?:,\d{3})+)(?![\d.])")


def _walk(node, path, ledger):
    """Record every numeric leaf in the computed result, with its path."""
    if isinstance(node, dict):
        for key, value in node.items():
            _walk(value, "%s.%s" % (path, key) if path else str(key), ledger)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk(value, "%s[%d]" % (path, index), ledger)
    elif isinstance(node, bool):
        return
    elif isinstance(node, (int, float)):
        ledger.setdefault(round(float(node), 2), []).append(path)


def ledger(result):
    """Every number the estimator computed, keyed by value, with its origin.

    Values are recorded to two decimal places because that is the precision a
    report renders at. A figure that survives rounding into the report must
    exist here, or it came from somewhere nobody recorded.
    """
    import rates

    found = {}
    _walk(result, "", found)

    # Published rates and the judgment factors are legitimate origins too.
    for name, value in (("rates.DOLLARS_PER_CREDIT", rates.DOLLARS_PER_CREDIT),
                        ("rates.DOLLARS_PER_GITHUB_AI_CREDIT",
                         rates.DOLLARS_PER_GITHUB_AI_CREDIT)):
        found.setdefault(round(float(value), 2), []).append(name)
    for model, (rin, rout) in rates.ANTHROPIC_RATES.items():
        found.setdefault(round(rin, 2), []).append("rates.%s.input" % model)
        found.setdefault(round(rout, 2), []).append("rates.%s.output" % model)
    for entry in registry():
        value = entry["value"]
        if isinstance(value, (int, float)):
            found.setdefault(round(float(value), 2), []).append(
                "assumption:%s" % entry["name"])
    return found


def _cited(value, book, places):
    """Is this rendered figure exactly some recorded value, at its precision?

    The report formats to a fixed number of decimal places, so a recorded
    44311.96 renders as "44,312" at zero places. Matching therefore compares
    the ROUNDED forms rather than opening a tolerance window.

    An earlier version allowed +/- 1.0 on grouped numbers, which let a figure
    one away from a recorded value pass -- exactly the off-by-a-bit computed
    value the check exists to catch. There is no window now.
    """
    target = round(value, places)
    return any(round(known, places) == target for known in book)


def validate(markdown, result):
    """Check every substantive figure in a report traces to a derivation.

    Returns a list of problems. Empty means every money figure and every
    grouped number in the report came from somewhere the estimator can name.
    """
    book = ledger(result)
    problems = []

    for raw in set(_MONEY.findall(markdown)):
        value = float(raw.replace(",", ""))
        if not _cited(value, book, places=2):
            problems.append(
                "$%s appears in the report but the estimator cannot say where "
                "it came from" % raw)

    for raw in set(_GROUPED.findall(markdown)):
        value = float(raw.replace(",", ""))
        if not _cited(value, book, places=0):
            problems.append(
                "%s appears in the report but the estimator cannot say where "
                "it came from" % raw)

    return sorted(problems)


def coverage(markdown, result):
    """What the check actually verifies, measured rather than asserted.

    Honesty about the limit matters as much as the check: this validates
    VALUE provenance -- every figure equals something the estimator recorded
    -- not FIELD provenance. It cannot detect a renderer that displays a real
    value from the wrong field. That is a different defect needing a different
    check, and claiming otherwise would be the kind of overstatement this
    module exists to prevent.
    """
    book = ledger(result)
    money = set(_MONEY.findall(markdown))
    grouped = set(_GROUPED.findall(markdown))
    shared = sum(1 for paths in book.values() if len(paths) > 1)
    return {
        "recorded_values": len(book),
        "values_with_multiple_origins": shared,
        "money_figures_checked": len(money),
        "grouped_figures_checked": len(grouped),
        "problems": len(validate(markdown, result)),
        "verifies": "value provenance",
        "does_not_verify": "field provenance -- a real value shown in the "
                           "wrong place still passes",
    }


def render_provenance(result, problems):
    """State the guarantee, and never claim it when it does not hold."""
    out = ["### Provenance of every figure", ""]
    if problems:
        out.append("> **VALIDATION FAILED.** %d figure%s in this report could "
                   "not be traced to a\n> recorded derivation. This report "
                   "should not be used until that is fixed:"
                   % (len(problems), "" if len(problems) == 1 else "s"))
        out.append(">")
        for problem in problems[:10]:
            out.append("> - %s" % problem)
        out.append("")
        return "\n".join(out)

    out.append("Every money figure and every grouped number above has been "
               "checked against the\nestimator's own derivation ledger. Each "
               "one is either measured from session\nhistory, a published "
               "rate carrying a source URL and verification date, a value "
               "you\ndeclared in the manifest, or arithmetic on those.")
    out.append("")
    out.append("**Nothing in this report is asserted without a derivation.** "
               "The check is\nmechanical and runs on every build; a figure "
               "the estimator cannot account for\nfails validation rather "
               "than being printed.")
    out.append("")
    out.append("Matching is exact at the precision each figure is rendered "
               "to.\nThere is **no tolerance window**, so a value one away "
               "from a recorded one fails.")
    out.append("")
    out.append("What it does **not** verify: that a recorded value appears in "
               "the right place. A\nrenderer showing a real figure under the "
               "wrong label would pass. That is a\ndifferent defect needing a "
               "different check, and claiming otherwise would be the\n"
               "overstatement this section exists to avoid.")
    out.append("")
    return "\n".join(out)
