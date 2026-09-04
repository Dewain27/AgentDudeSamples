#!/usr/bin/env python3
"""Which model does the building, and what that does to the cost.

Author: Dewain Robinson

The estimator's Claude Code build cost is `turns x cost_per_main_turn`, and
`cost_per_main_turn` is a single blended figure measured from real session
history. That blend was produced by a specific mix of models. Build the same
scope entirely on Opus, or entirely on a cheaper model, and the per-token
price of every turn changes -- but the measured number does not know that.

Before this module the mix was recorded in the calibration profile and read by
nothing. The assumption was invisible: a reader could not tell which models
underpinned the figure they were being asked to budget.

So the model becomes an explicit input, and one of two things happens:

  REPRICED    The declared model differs from the calibration mix, and the
              profile carries the measured dollar shares needed to rescale.
              The measured cost is scaled by a share-weighted ratio of
              published per-model rates.

  DISCLOSED   No model was declared, or the profile lacks the measured shares.
              Nothing is rescaled. The calibration mix is stated as an
              assumption and the report says plainly that it was not repriced.

Disclosure is the floor; repricing is the addition on top of it, taken only
when the data supports it.

WHY THE RESCALE IS GROUNDED RATHER THAN GUESSED

Each term is a MEASURED dollar share times a ratio of PUBLISHED rates:

    ratio = share_cache_read  x cr(target) / cr(calibration)
          + share_cache_write x cw(target) / cw(calibration)
          + share_output      x out(target) / out(calibration)

The shares already encode volume x rate reality, so no token-volume
reconstruction is needed and there is no free parameter to tune. At
target == calibration the ratio is exactly 1.0 and the measured cost is
returned untouched -- the formula cannot drift away from the number it is
anchored to.

WHAT IT DOES NOT CAPTURE

A rescale prices tokens, not capability. It does not model that a cheaper or
weaker model may need MORE TURNS to finish the same work, which is a real
effect and is not derivable from published rates. That limit is stated in the
report every time rather than quietly folded into the number.
"""

__author__ = "Dewain Robinson"

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rates  # noqa: E402

#: Cost components the rescale weighs, in the order the report shows them.
COMPONENTS = ("cache_read", "cache_write", "output")


class BuildModelError(Exception):
    """Raised for build-model input the user must fix."""


def _normalise_shares(shares):
    """Measured dollar shares, normalised to sum to 1.

    Returns None when the profile cannot support a rescale, which is a
    disclosure path rather than an error: an older or published-baseline
    profile simply did not record them.
    """
    if not isinstance(shares, dict):
        return None
    try:
        values = {c: float(shares[c]) for c in COMPONENTS}
    except (KeyError, TypeError, ValueError):
        return None
    total = sum(values.values())
    if total <= 0:
        return None
    return {c: v / total for c, v in values.items()}


def describe(mix):
    """Human label for a mix: 'claude-opus-5' or 'opus-5 55% / sonnet-5 45%'."""
    if not mix:
        return "not declared"
    if len(mix) == 1:
        return list(mix)[0]
    return " / ".join(
        "%s %.0f%%" % (model, weight * 100)
        for model, weight in sorted(mix.items(), key=lambda kv: -kv[1]))


def resolve(manifest, profile, build_platform):
    """Decide whether to reprice the per-turn cost, and by how much.

    Never raises for a missing input -- only for one that is wrong, such as a
    model the platform cannot run. A missing input is disclosed, not rejected.
    """
    declared_raw = manifest.get("build_model")
    try:
        declared = rates.normalise_model_mix(declared_raw, build_platform)
    except ValueError as exc:
        raise BuildModelError(str(exc))

    calibration = profile.get("model_mix") or {}
    shares = _normalise_shares(profile.get("component_shares"))
    base = float(profile["cost_per_main_turn"])

    info = {
        "platform": build_platform,
        "declared": declared,
        "declared_label": describe(declared),
        "calibration_mix": calibration,
        "calibration_label": describe(calibration),
        "base_cost_per_turn": base,
        "cost_per_turn": base,
        "ratio": 1.0,
        "repriced": False,
        "reason": "",
        "shares": shares or {},
    }

    if not declared:
        info["reason"] = (
            "No build model was declared, so the estimate carries the "
            "calibration mix's blended per-turn cost unchanged.")
        return info

    if not calibration:
        info["reason"] = (
            "The calibration profile does not record which models produced "
            "its measured cost, so there is no baseline to rescale from.")
        return info

    if shares is None:
        info["reason"] = (
            "The calibration profile does not record measured cost shares "
            "(cache read, cache write, output), so a rescale would have no "
            "measured basis.")
        return info

    try:
        target_rates = rates.blended_component_rates(declared)
        calibration_rates = rates.blended_component_rates(
            rates.normalise_model_mix(calibration, "claude-code"))
    except ValueError as exc:
        # A calibration mix naming a model with no published rate cannot be
        # a denominator. Disclose rather than guess one.
        info["reason"] = (
            "The calibration mix could not be priced (%s), so there is no "
            "baseline to rescale from." % exc)
        return info

    ratio = 0.0
    breakdown = []
    for component in COMPONENTS:
        denominator = calibration_rates[component]
        if denominator <= 0:
            info["reason"] = (
                "A calibration component rate was zero, so the ratio is "
                "undefined and nothing was rescaled.")
            return info
        term = shares[component] * target_rates[component] / denominator
        ratio += term
        breakdown.append({
            "component": component,
            "share": shares[component],
            "target_rate": target_rates[component],
            "calibration_rate": denominator,
            "term": term,
        })

    # Rounded so an identical mix yields exactly 1.0 rather than 0.9999999.
    ratio = round(ratio, 6)
    info.update({
        "repriced": True,
        "ratio": ratio,
        "cost_per_turn": round(base * ratio, 6),
        "breakdown": breakdown,
        "target_rates": target_rates,
        "calibration_rates": calibration_rates,
    })
    if ratio == 1.0:
        info["reason"] = (
            "The declared build model matches the calibration mix, so the "
            "measured per-turn cost applies unchanged.")
    return info


def render_markdown(info):
    """Report section: which model builds it, and what that did to the cost."""
    if not info:
        return ""
    out = ["## Which model builds it", ""]

    if info["platform"] != "claude-code":
        out.append("**Build model:** %s" % info["declared_label"])
        out.append("")
        return "\n".join(out)

    out.append("| | Model |")
    out.append("| --- | --- |")
    out.append("| Declared for this build | **%s** |" % info["declared_label"])
    out.append("| Measured in the calibration profile | %s |"
               % info["calibration_label"])
    out.append("")

    if not info["repriced"]:
        out.append("> **Not repriced.** %s" % info["reason"])
        out.append("")
        out.append("The per-turn cost used here is the measured **$%s**, which "
                   "carries whatever\nmodel mix produced it. If you will build "
                   "on a materially different model, this\nestimate does not "
                   "adjust for that."
                   % format(info["base_cost_per_turn"], ",.2f"))
        out.append("")
        return "\n".join(out)

    if info["ratio"] == 1.0:
        out.append("The declared model **matches the calibration mix**, so the "
                   "measured per-turn cost\napplies unchanged at **$%s**. No "
                   "rescale was needed."
                   % format(info["base_cost_per_turn"], ",.2f"))
        out.append("")
    else:
        direction = "more" if info["ratio"] > 1 else "less"
        out.append("Repricing the measured **$%s** per turn by **x%.4f** gives "
                   "**$%s** — this model\ncosts %s per token than the mix the "
                   "measurement was taken on."
                   % (format(info["base_cost_per_turn"], ",.2f"),
                      info["ratio"],
                      format(info["cost_per_turn"], ",.2f"), direction))
        out.append("")

    out.append("### How the ratio was derived")
    out.append("")
    out.append("Each row is a **measured dollar share** of the real per-turn "
               "cost, times a ratio of\n**published per-model rates**. There is "
               "no free parameter.")
    out.append("")
    out.append("| Cost component | Measured share | This model $/1M | "
               "Calibration $/1M | Contribution |")
    out.append("| --- | ---: | ---: | ---: | ---: |")
    labels = {"cache_read": "Cache read", "cache_write": "Cache write",
              "output": "Output"}
    for row in info.get("breakdown", []):
        out.append("| %s | %.0f%% | %.4f | %.4f | %.4f |"
                   % (labels[row["component"]], row["share"] * 100,
                      row["target_rate"], row["calibration_rate"],
                      row["term"]))
    out.append("| **Ratio** | | | | **%.4f** |" % info["ratio"])
    out.append("")

    out.append("> **What this does not capture.** The rescale prices *tokens*, "
               "not capability. It\n> does **not** model that a cheaper or "
               "weaker model may need **more turns** to do\n> the same work. "
               "That effect is real and is not derivable from published rates, "
               "so\n> it is named here rather than folded silently into the "
               "number. The rescale also\n> holds the measured token profile — "
               "context size, output length, cache behaviour —\n> constant.")
    out.append("")
    return "\n".join(out)
