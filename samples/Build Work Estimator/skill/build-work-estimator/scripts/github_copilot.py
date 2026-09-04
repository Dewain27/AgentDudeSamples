#!/usr/bin/env python3
"""Build-time cost when the build stack is GitHub Copilot.

Author: Dewain Robinson

GitHub AI Credits are NOT Copilot Studio Copilot Credits. Both happen to be
$0.01 per credit, and they are different meters on different products with
separate allowances. This module never mixes them.

GitHub runs two billing models in parallel:

  ai-credits        Interactions consume input, output, and cached tokens.
                    GitHub prices those at the model's published rates and
                    converts to AI Credits at $0.01 each. Business and
                    Enterprise pool credits at the billing-entity level.

  premium-requests  Legacy. Each interaction costs one premium request times
                    the model's multiplier, drawn from a monthly allowance.
                    Eligible Pro and Pro+ annual subscribers stay on this
                    until their plan expires.

Per-model rates and multipliers are NOT hardcoded. GitHub publishes them and
changes them; a stale table here would silently misprice every estimate. The
user supplies the rate for the model they actually use.
"""

__author__ = "Dewain Robinson"

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rates  # noqa: E402

DEFAULTS = {
    "build_model": None,
    "billing_mode": "ai-credits",
    "interactions": 0,
    "tokens_per_interaction": 6000,
    "output_share": 0.15,
    "dollars_per_1m_input": None,
    "dollars_per_1m_output": None,
    "auto_discount": 0.0,
    # premium-requests mode
    "model_multiplier": 1.0,
    "monthly_allowance": None,
}


class GitHubCopilotError(Exception):
    """Raised for input the user must fix."""


def compute(config, reserve_percent):
    cfg = dict(DEFAULTS)
    cfg.update(config or {})

    mode = str(cfg["billing_mode"]).strip().lower()
    if mode not in rates.GITHUB_BILLING_MODES:
        raise GitHubCopilotError(
            "billing_mode must be one of: %s (got %r).\n\n"
            "Check which applies at %s"
            % (", ".join(sorted(rates.GITHUB_BILLING_MODES)),
               cfg["billing_mode"], rates.GITHUB_PLANS_SOURCE))

    interactions = int(cfg["interactions"] or 0)
    mode_info = rates.GITHUB_BILLING_MODES[mode]

    # Which model builds it. GitHub runs a multi-provider catalogue, so the
    # model is validated against what GitHub Copilot can actually run -- not
    # against a global list, and never against Claude Code's Anthropic-only
    # catalogue.
    build_model = cfg.get("build_model")
    model_rates = None
    if build_model:
        try:
            build_model = rates.validate_model_for_platform(
                "github-copilot", build_model)
        except ValueError as exc:
            raise GitHubCopilotError(str(exc))
        model_rates = rates.GITHUB_MODEL_RATES[build_model]

    result = {
        "stack": "github-copilot",
        "billing_mode": mode,
        "billing_mode_label": mode_info["label"],
        "billing_mode_note": mode_info["note"],
        "interactions": interactions,
        "build_model": build_model or None,
        "unmetered": list(rates.GITHUB_UNMETERED),
        "reserve_percent": float(reserve_percent),
        "verified": rates.GITHUB_VERIFIED,
        "sources": {
            "models_and_pricing": rates.GITHUB_SOURCE,
            "legacy_premium_requests": rates.GITHUB_LEGACY_SOURCE,
            "plans": rates.GITHUB_PLANS_SOURCE,
        },
        "lines": [],
    }

    if mode == "premium-requests":
        # Legacy. GitHub's current pricing page publishes per-model TOKEN
        # rates, not request multipliers, so there is no sourced multiplier to
        # look up. The model is disclosed as a label and the multiplier stays
        # the user's declaration -- inventing one to fill the gap would be a
        # fabricated rate wearing a source's clothes.
        result["model_rate_source"] = "user-declared multiplier (legacy mode)"
        multiplier = float(cfg["model_multiplier"] or 1.0)
        used = interactions * multiplier
        result.update({
            "unit": "premium request",
            "model_multiplier": multiplier,
            "total_units": round(used, 1),
            "reserve_units": round(used * float(reserve_percent) / 100.0, 1),
        })
        result["budget_units"] = round(
            result["total_units"] + result["reserve_units"], 1)
        allowance = cfg["monthly_allowance"]
        if allowance:
            allowance = float(allowance)
            result["monthly_allowance"] = allowance
            result["allowance_share"] = round(
                result["budget_units"] / allowance, 4)
            result["exceeds_allowance"] = result["budget_units"] > allowance
        result["lines"].append({
            "label": "Premium requests",
            "units": round(used, 1),
            "detail": "%s interactions x %.2f model multiplier"
                      % (format(interactions, ","), multiplier),
        })
        return result

    # ai-credits
    rin = cfg["dollars_per_1m_input"]
    rout = cfg["dollars_per_1m_output"]

    # A declared model supplies its published rates, so the common case needs
    # no hand-copied numbers. An explicit rate still wins -- GitHub's
    # catalogue moves, and someone with a current figure should not be
    # overridden by this table -- and the report says which applied.
    if model_rates is not None and (rin is None or rout is None):
        rin, rout = model_rates
        result["model_rate_source"] = "published GitHub rate for %s" % build_model
        result["model_rates_verified"] = rates.GITHUB_MODEL_RATES_VERIFIED
    elif model_rates is not None:
        result["model_rate_source"] = (
            "explicitly supplied, overriding the published rate for %s"
            % build_model)
    else:
        result["model_rate_source"] = "explicitly supplied"

    if rin is None or rout is None:
        raise GitHubCopilotError(
            "dollars_per_1m_input and dollars_per_1m_output are required for "
            "AI Credits billing.\n\n"
            "GitHub prices token consumption at the selected model's published "
            "rates, then\nconverts to AI Credits at $%.2f each. Those rates "
            "are not hardcoded here --\nthey change, and a stale table would "
            "misprice every estimate.\n\n"
            "Either declare the model and let its published rate apply:\n"
            "  build_model: %s\n\n"
            "or supply the rates directly. Known models:\n  %s\n\n"
            "Full catalogue: %s"
            % (rates.DOLLARS_PER_GITHUB_AI_CREDIT,
               sorted(rates.GITHUB_MODEL_RATES)[0],
               ", ".join(sorted(rates.GITHUB_MODEL_RATES)),
               rates.GITHUB_SOURCE))

    rin, rout = float(rin), float(rout)
    total_tokens = interactions * int(cfg["tokens_per_interaction"] or 0)
    out_share = float(cfg["output_share"] or 0.0)
    if not (0.0 <= out_share <= 1.0):
        raise GitHubCopilotError("output_share must be between 0 and 1.")

    output_tokens = total_tokens * out_share
    input_tokens = total_tokens - output_tokens
    dollars = (input_tokens * rin + output_tokens * rout) / 1e6

    discount = float(cfg["auto_discount"] or 0.0)
    if not (0.0 <= discount < 1.0):
        raise GitHubCopilotError("auto_discount must be between 0 and 1.")
    discounted = dollars * (1.0 - discount)
    credits = discounted / rates.DOLLARS_PER_GITHUB_AI_CREDIT

    result.update({
        "total_tokens": int(total_tokens),
        "unit": "GitHub AI Credit",
        "dollars_per_credit": rates.DOLLARS_PER_GITHUB_AI_CREDIT,
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "auto_discount": discount,
        "total_units": round(credits, 1),
        "total_dollars": round(discounted, 2),
    })
    result["reserve_units"] = round(credits * float(reserve_percent) / 100.0, 1)
    result["budget_units"] = round(credits + result["reserve_units"], 1)
    result["budget_dollars"] = round(
        result["budget_units"] * rates.DOLLARS_PER_GITHUB_AI_CREDIT, 2)

    result["lines"].append({
        "label": "Chat and agent interactions",
        "units": round(credits, 1),
        "detail": "%s interactions, %s tokens (%.0f%% output) at $%.2f/$%.2f "
                  "per 1M%s"
                  % (format(interactions, ","), format(total_tokens, ","),
                     out_share * 100, rin, rout,
                     ", less %.0f%% Auto discount" % (discount * 100)
                     if discount else ""),
    })
    return result


def render_markdown(result):
    out = ["## Build cost — GitHub Copilot", ""]
    out.append("> Metered in **%ss**. This is a different meter from Copilot "
               "Studio Copilot\n> Credits, even though both are $0.01 per "
               "credit." % result["unit"])
    out.append("")
    out.append("**Billing model:** %s — %s"
               % (result["billing_mode_label"], result["billing_mode_note"]))
    out.append("")
    if result.get("build_model"):
        out.append("**Build model:** `%s` — rates %s."
                   % (result["build_model"],
                      result.get("model_rate_source", "as supplied")))
        if result.get("model_rates_verified"):
            out.append("")
            out.append("GitHub prices AI Credits from token consumption at the "
                       "selected model's published\nrate, so which model builds "
                       "is a cost input rather than a preference. Rate "
                       "verified\n%s against [models and pricing](%s)."
                       % (result["model_rates_verified"],
                          result["sources"]["models_and_pricing"]))
    else:
        out.append("> **No build model declared.** GitHub prices AI Credits "
                   "from the selected model's\n> published token rate, so the "
                   "model is a cost input. Declaring it lets the "
                   "published\n> rate apply instead of a hand-copied one.")
    out.append("")

    if not result["interactions"]:
        out.append("No metered interactions declared, so no build-time "
                   "consumption is modelled.")
        out.append("")
        return "\n".join(out)

    out.append("| Build activity | %ss | Basis |" % result["unit"].title())
    out.append("| --- | ---: | --- |")
    for line in result["lines"]:
        out.append("| %s | %s | %s |"
                   % (line["label"], format(line["units"], ",.0f"),
                      line["detail"]))
    out.append("| **Total** | **%s** | |"
               % format(result["total_units"], ",.0f"))
    out.append("| Reserve (%.0f%%) | %s | required contingency |"
               % (result["reserve_percent"],
                  format(result["reserve_units"], ",.0f")))
    out.append("| **Budget ask** | **%s** | |"
               % format(result["budget_units"], ",.0f"))
    out.append("")

    if result["billing_mode"] == "ai-credits":
        out.append("At $%.2f per credit that is **$%s** total, **$%s** with "
                   "reserve."
                   % (result["dollars_per_credit"],
                      format(result["total_dollars"], ",.2f"),
                      format(result["budget_dollars"], ",.2f")))
        out.append("")
    elif result.get("monthly_allowance"):
        share = result["allowance_share"] * 100
        out.append("Against a monthly allowance of %s premium requests, this "
                   "build consumes **%.0f%%**."
                   % (format(result["monthly_allowance"], ",.0f"), share))
        if result.get("exceeds_allowance"):
            out.append("")
            out.append("**This exceeds the monthly allowance.** Work will fall "
                       "back to a base model\nor require additional premium "
                       "requests to be purchased.")
        out.append("")

    out.append("### Not metered")
    out.append("")
    out.append("These consume no credits and are unlimited on paid plans, so "
               "they contribute\nnothing to this estimate however heavily they "
               "are used:")
    out.append("")
    for item in result["unmetered"]:
        out.append("- %s" % item)
    out.append("")
    out.append("Rates verified %s. Sources: [models and pricing](%s) · "
               "[legacy premium requests](%s) · [plans](%s)"
               % (result["verified"], result["sources"]["models_and_pricing"],
                  result["sources"]["legacy_premium_requests"],
                  result["sources"]["plans"]))
    out.append("")
    return "\n".join(out)
