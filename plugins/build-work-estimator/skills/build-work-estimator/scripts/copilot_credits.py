#!/usr/bin/env python3
"""Translate a BUILD estimate into Copilot Credits.

Author: Dewain Robinson

Build-time only. This models the credits consumed while AUTHORING, ITERATING
ON, TESTING, and EVALUATING an agent -- not the credits its users will consume
once it is live. Runtime capacity planning (monthly burn, capacity packs,
overage enforcement, voice minutes, end-user M365 licence offsets) is
deliberately out of scope; see Microsoft's own agent usage estimator for that.

The harness decides almost everything:

  standard        bills AFTER publish, and embedded test chat is not billed,
                  so build-time credits are near zero
  github-copilot  bills FROM THE MOMENT YOU START BUILDING -- authoring,
                  preview, test, and evaluation generation all consume credits
"""

__author__ = "Dewain Robinson"

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rates  # noqa: E402

RUNTIME_ESTIMATOR_URL = "https://microsoft.github.io/copilot-studio-estimator/"

DEFAULTS = {
    "harness": "github-copilot",
    "tier": "standard",
    "reasoning_model": False,
    "authoring_turns": 0,
    "tokens_per_turn": 4000,
    "test_runs": 0,
    "interactions_per_test_run": 5,
    "interaction_type": "generative_answer",
    "eval_runs": 0,
    "eval_tokens_per_run": 3000,
    "agent_flow_actions": 0,
    "content_processing_pages": 0,
}


class CreditError(Exception):
    """Raised for input the user must fix."""


def _line(label, credits, detail):
    return {
        "label": label,
        "credits": round(credits, 2),
        "dollars": round(credits * rates.DOLLARS_PER_CREDIT, 2),
        "detail": detail,
    }


def compute(config, reserve_percent):
    """Return a build-time Copilot Credits breakdown.

    `config` is the manifest's `copilot:` block. `reserve_percent` is the same
    required reserve applied to the dollar estimate -- contingency applies to
    both currencies or to neither.
    """
    cfg = dict(DEFAULTS)
    cfg.update(config or {})

    harness = str(cfg["harness"]).strip().lower()
    if harness not in rates.HARNESS_BUILD_BILLING:
        raise CreditError(
            "harness must be one of: %s (got %r)"
            % (", ".join(sorted(rates.HARNESS_BUILD_BILLING)), cfg["harness"])
        )
    tier = str(cfg["tier"]).strip().lower()
    if tier not in rates.CC_TOKEN_TIERS:
        raise CreditError(
            "tier must be one of: %s (got %r)"
            % (", ".join(sorted(rates.CC_TOKEN_TIERS)), cfg["tier"])
        )

    harness_info = rates.HARNESS_BUILD_BILLING[harness]
    reasoning = bool(cfg["reasoning_model"])
    # Reasoning models bill the feature rate PLUS the premium token tier, so
    # the effective token tier is premium regardless of what was selected.
    effective_tier = rates.CC_REASONING_TIER if reasoning else tier

    lines = []
    surcharge = 0.0

    if harness_info["bills_during_build"]:
        authoring_tokens = cfg["authoring_turns"] * cfg["tokens_per_turn"]
        if authoring_tokens:
            cc = rates.credits_for_tokens(authoring_tokens, effective_tier)
            lines.append(_line(
                "Authoring / natural-language solution creation", cc,
                "%s turns x %s tokens at %s tier"
                % (format(cfg["authoring_turns"], ","),
                   format(cfg["tokens_per_turn"], ","), effective_tier)))
            if reasoning:
                surcharge += cc - rates.credits_for_tokens(authoring_tokens, tier)

        interactions = cfg["test_runs"] * cfg["interactions_per_test_run"]
        if interactions:
            per = rates.feature_credits(cfg["interaction_type"])
            lines.append(_line(
                "Preview and test iterations", interactions * per,
                "%s runs x %s interactions x %s CC (%s)"
                % (format(cfg["test_runs"], ","),
                   cfg["interactions_per_test_run"], per,
                   rates.CC_FEATURES[cfg["interaction_type"]]["label"])))
            test_tokens = interactions * cfg["tokens_per_turn"]
            cc = rates.credits_for_tokens(test_tokens, effective_tier)
            lines.append(_line(
                "Preview and test model consumption", cc,
                "%s tokens at %s tier" % (format(test_tokens, ","), effective_tier)))
            if reasoning:
                surcharge += cc - rates.credits_for_tokens(test_tokens, tier)

        eval_tokens = cfg["eval_runs"] * cfg["eval_tokens_per_run"]
        if eval_tokens:
            cc = rates.credits_for_tokens(eval_tokens, effective_tier)
            lines.append(_line(
                "Evaluation generation and runs", cc,
                "%s evals x %s tokens at %s tier"
                % (format(cfg["eval_runs"], ","),
                   format(cfg["eval_tokens_per_run"], ","), effective_tier)))
            if reasoning:
                surcharge += cc - rates.credits_for_tokens(eval_tokens, tier)

    # Billable side-effects can occur on ANY harness, including standard, when
    # a build exercises them against a published agent.
    if cfg["agent_flow_actions"]:
        cc = cfg["agent_flow_actions"] / 100.0 * \
            rates.feature_credits("agent_flow_per_100")
        lines.append(_line(
            "Agent flow actions during build", cc,
            "%s actions at %s CC per 100"
            % (format(cfg["agent_flow_actions"], ","),
               rates.feature_credits("agent_flow_per_100"))))

    if cfg["content_processing_pages"]:
        cc = cfg["content_processing_pages"] * \
            rates.feature_credits("content_processing_per_page")
        lines.append(_line(
            "Content processing during build", cc,
            "%s pages at %s CC per page"
            % (format(cfg["content_processing_pages"], ","),
               rates.feature_credits("content_processing_per_page"))))

    total = sum(item["credits"] for item in lines)
    reserve = total * float(reserve_percent) / 100.0

    return {
        "harness": harness,
        "harness_note": harness_info["note"],
        "bills_during_build": harness_info["bills_during_build"],
        "tier": tier,
        "effective_tier": effective_tier,
        "reasoning_model": reasoning,
        "reasoning_surcharge_credits": round(surcharge, 2),
        "reasoning_surcharge_dollars": round(
            surcharge * rates.DOLLARS_PER_CREDIT, 2),
        "lines": lines,
        "total_credits": round(total, 2),
        "total_dollars": round(total * rates.DOLLARS_PER_CREDIT, 2),
        "reserve_percent": float(reserve_percent),
        "reserve_credits": round(reserve, 2),
        "budget_credits": round(total + reserve, 2),
        "budget_dollars": round(
            (total + reserve) * rates.DOLLARS_PER_CREDIT, 2),
        "dollars_per_credit": rates.DOLLARS_PER_CREDIT,
        "tier_comparison": [
            {"tier": name,
             "cc_per_1k_tokens": rates.CC_TOKEN_TIERS[name],
             "dollars_per_1m_tokens": rates.dollars_per_million_tokens(name)}
            for name in ("basic", "standard", "premium")
        ],
        "excluded": [
            "Monthly production credit burn from end users",
            "Capacity pack sizing and overage enforcement",
            "Voice minutes",
            "End-user Microsoft 365 Copilot licence offsets",
            "Bring-your-own-model (including Azure Foundry), billed separately",
        ],
        "runtime_estimator": RUNTIME_ESTIMATOR_URL,
        "sources": {
            "billing_rates": rates.COPILOT_SOURCE,
            "pay_as_you_go": rates.COPILOT_PAYG_SOURCE,
            "reasoning": rates.COPILOT_REASONING_SOURCE,
            "harness": rates.COPILOT_HARNESS_SOURCE,
        },
        "verified": rates.COPILOT_VERIFIED,
    }


def render_markdown(result):
    """Report section for a build-time credits result."""
    out = []
    out.append("## Build-time Copilot Credits")
    out.append("")
    out.append("> These are the credits consumed **building** the agent. They "
               "say nothing about\n> what it will cost once users start "
               "talking to it. For that, use Microsoft's\n> [agent usage "
               "estimator](%s)." % RUNTIME_ESTIMATOR_URL)
    out.append("")
    out.append("**Harness:** `%s` — %s" % (result["harness"], result["harness_note"]))
    out.append("")

    if not result["lines"]:
        out.append("**No build-time credit consumption modelled.** On this "
                   "harness the build itself is not billed, and no billable "
                   "side-effects were declared. That is a correct result, not "
                   "a missing one.")
        out.append("")
        return "\n".join(out)

    out.append("| Build activity | Credits | At $%.2f/CC | Basis |"
               % result["dollars_per_credit"])
    out.append("| --- | ---: | ---: | --- |")
    for line in result["lines"]:
        out.append("| %s | %s | $%s | %s |"
                   % (line["label"], format(line["credits"], ",.0f"),
                      format(line["dollars"], ",.2f"), line["detail"]))
    out.append("| **Total build credits** | **%s** | **$%s** | |"
               % (format(result["total_credits"], ",.0f"),
                  format(result["total_dollars"], ",.2f")))
    out.append("| Reserve (%.0f%%) | %s | $%s | required contingency |"
               % (result["reserve_percent"],
                  format(result["reserve_credits"], ",.0f"),
                  format(result["reserve_credits"] * result["dollars_per_credit"], ",.2f")))
    out.append("| **Budget ask** | **%s** | **$%s** | |"
               % (format(result["budget_credits"], ",.0f"),
                  format(result["budget_dollars"], ",.2f")))
    out.append("")

    if result["reasoning_model"]:
        out.append("**Reasoning-model surcharge: %s credits ($%s).** Reasoning "
                   "models bill the feature rate *plus* the premium token tier, "
                   "so the effective tier is `premium` regardless of the `%s` "
                   "tier selected."
                   % (format(result["reasoning_surcharge_credits"], ",.0f"),
                      format(result["reasoning_surcharge_dollars"], ",.2f"),
                      result["tier"]))
        out.append("")

    out.append("### Tier sensitivity")
    out.append("")
    out.append("Tier selection is the highest-leverage variable in a "
               "Microsoft-side build estimate:")
    out.append("")
    out.append("| Tier | CC per 1K tokens | $ per 1M tokens |")
    out.append("| --- | ---: | ---: |")
    for row in result["tier_comparison"]:
        mark = " ← in use" if row["tier"] == result["effective_tier"] else ""
        out.append("| %s%s | %s | $%s |"
                   % (row["tier"], mark, row["cc_per_1k_tokens"],
                      format(row["dollars_per_1m_tokens"], ",.2f")))
    out.append("")
    out.append("### Not included")
    out.append("")
    for item in result["excluded"]:
        out.append("- %s" % item)
    out.append("")
    out.append("Rates verified %s. Sources: [billing rates](%s) · "
               "[pay-as-you-go](%s) · [reasoning](%s) · [harness](%s)"
               % (result["verified"], result["sources"]["billing_rates"],
                  result["sources"]["pay_as_you_go"],
                  result["sources"]["reasoning"], result["sources"]["harness"]))
    out.append("")
    return "\n".join(out)
