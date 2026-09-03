#!/usr/bin/env python3
"""What the target platform costs during the build.

Author: Dewain Robinson

The build happens in a coding agent (Claude Code or GitHub Copilot) against
the agent definition. The target platform is where the result is deployed,
previewed, evaluated, and validated by a human -- and that work consumes the
target's own meter, on the same project, at the same time.

    build platform          target platform
    ---------------         ----------------
    author definition  -->  deploy
                            preview / interactive test   <- human, in the UI
                            run evaluations
    remediate       <--     evaluations fail
    (repeat)

THE TARGET HARNESS DECIDES WHETHER ANY OF THIS IS BILLED:

  standard        Billing starts AFTER publish, and embedded test chat is not
                  billed. Build, preview, test, and evaluation in the
                  interface cost nothing. Only billable side-effects exercised
                  during the build (agent flow runs, content processing) count.

  github-copilot  Billing applies to using, BUILDING, TESTING, and EVALUATING.
                  Every preview turn and every evaluation run consumes credits
                  from the moment building starts.

Getting the harness wrong therefore changes the target-side figure between
"effectively zero" and the largest line in the estimate.
"""

__author__ = "Dewain Robinson"

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rates  # noqa: E402

RUNTIME_ESTIMATOR_URL = "https://microsoft.github.io/copilot-studio-estimator/"

DEFAULTS = {
    "harness": None,                  # REQUIRED -- decides whether any of it bills
    "tier": "standard",
    "reasoning_model": False,
    "tokens_per_interaction": 4000,
    # Interactive validation by a human, in the Copilot Studio interface.
    "interactive_test_hours": 0,
    "interactions_per_hour": 25,
    # Evaluations. Always planned -- an agent build without them is not done.
    "eval_test_cases": 0,
    "eval_repeats": 3,                # docs: run the same set multiple times
    "eval_cycles": 1,                 # build -> deploy -> evaluate -> fix rounds
    "eval_tokens_per_case": 3000,
    # Billable side-effects that can occur on any harness.
    "agent_flow_actions": 0,
    "content_processing_pages": 0,
    # Azure targets: the user supplies their own figure; nothing is bundled.
    "azure_build_usd": 0.0,
    "azure_note": "",
}


class TargetPlatformError(Exception):
    """Raised for input the user must fix."""


def _line(label, credits, detail, billed=True):
    return {
        "label": label,
        "credits": round(credits, 2) if billed else 0.0,
        "dollars": round(credits * rates.DOLLARS_PER_CREDIT, 2) if billed else 0.0,
        "unbilled_credits": 0.0 if billed else round(credits, 2),
        "billed": billed,
        "detail": detail,
    }


def validate_harness(value):
    if value is None or str(value).strip() == "":
        raise TargetPlatformError(
            "target harness is required when the target platform is Copilot "
            "Studio.\n\n"
            "  standard        billing starts after publish; build, preview, "
            "test chat and\n                  evaluation in the interface are "
            "NOT billed\n"
            "  github-copilot  billing applies to using, building, testing and "
            "evaluating --\n                  every preview turn and "
            "evaluation run consumes credits\n\n"
            "This single answer moves the target-side figure between "
            "effectively zero and\nthe largest line in the estimate, so it is "
            "not guessed."
        )
    key = str(value).strip().lower()
    if key not in rates.HARNESS_BUILD_BILLING:
        raise TargetPlatformError(
            "harness must be one of: %s (got %r)"
            % (", ".join(sorted(rates.HARNESS_BUILD_BILLING)), value))
    return key


def compute(config, reserve_percent, target="copilot-studio"):
    """Target-platform consumption during the build."""
    cfg = dict(DEFAULTS)
    cfg.update(config or {})

    result = {
        "target": target,
        "reserve_percent": float(reserve_percent),
        "lines": [],
        "verified": rates.COPILOT_VERIFIED,
        "runtime_estimator": RUNTIME_ESTIMATOR_URL,
        "sources": {
            "billing_rates": rates.COPILOT_SOURCE,
            "harness": rates.COPILOT_HARNESS_SOURCE,
            "eval_limits": rates.EVAL_LIMITS_SOURCE,
            "eval_guidance": rates.EVAL_GUIDANCE_SOURCE,
        },
    }

    if target == "azure":
        usd = float(cfg["azure_build_usd"] or 0.0)
        result.update({
            "harness": None,
            "currency": "USD",
            "azure_build_usd": round(usd, 2),
            "azure_note": cfg["azure_note"],
            "total_credits": 0.0,
            "total_dollars": round(usd, 2),
            "reserve_dollars": round(usd * float(reserve_percent) / 100.0, 2),
        })
        result["budget_dollars"] = round(
            result["total_dollars"] + result["reserve_dollars"], 2)
        result["lines"].append({
            "label": "Azure consumption during build and test",
            "credits": 0.0, "dollars": round(usd, 2), "billed": True,
            "unbilled_credits": 0.0,
            "detail": cfg["azure_note"] or "user-supplied figure; Azure rates "
                                           "are not bundled here",
        })
        return result

    harness = validate_harness(cfg["harness"])
    info = rates.HARNESS_BUILD_BILLING[harness]
    billed = info["bills_during_build"]

    tier = str(cfg["tier"]).strip().lower()
    if tier not in rates.CC_TOKEN_TIERS:
        raise TargetPlatformError(
            "tier must be one of: %s (got %r)"
            % (", ".join(sorted(rates.CC_TOKEN_TIERS)), cfg["tier"]))
    reasoning = bool(cfg["reasoning_model"])
    effective_tier = rates.CC_REASONING_TIER if reasoning else tier

    cycles = max(1, int(cfg["eval_cycles"] or 1))
    surcharge = 0.0

    # --- interactive validation in the interface, by a human --------------
    hours = float(cfg["interactive_test_hours"] or 0)
    interactions = int(round(hours * float(cfg["interactions_per_hour"] or 0)))
    if interactions:
        feature = interactions * rates.feature_credits("generative_answer")
        tokens = interactions * int(cfg["tokens_per_interaction"] or 0)
        token_cc = rates.credits_for_tokens(tokens, effective_tier)
        if reasoning:
            surcharge += token_cc - rates.credits_for_tokens(tokens, tier)
        result["lines"].append(_line(
            "Interactive validation in the Copilot Studio interface",
            feature + token_cc,
            "%.1f human hours x %s interactions/hour = %s interactions"
            % (hours, cfg["interactions_per_hour"], format(interactions, ",")),
            billed))

    # --- evaluation runs, across every cycle ------------------------------
    cases = int(cfg["eval_test_cases"] or 0)
    repeats = max(1, int(cfg["eval_repeats"] or 1))
    eval_runs = cases * repeats * cycles
    if eval_runs:
        feature = eval_runs * rates.feature_credits("generative_answer")
        tokens = eval_runs * int(cfg["eval_tokens_per_case"] or 0)
        token_cc = rates.credits_for_tokens(tokens, effective_tier)
        if reasoning:
            surcharge += token_cc - rates.credits_for_tokens(tokens, tier)
        result["lines"].append(_line(
            "Evaluation runs", feature + token_cc,
            "%s cases x %s repeats x %s cycle%s = %s runs"
            % (format(cases, ","), repeats, cycles, "" if cycles == 1 else "s",
               format(eval_runs, ",")),
            billed))

    # --- billable side-effects, on any harness ----------------------------
    if cfg["agent_flow_actions"]:
        actions = int(cfg["agent_flow_actions"]) * cycles
        cc = actions / 100.0 * rates.feature_credits("agent_flow_per_100")
        result["lines"].append(_line(
            "Agent flow runs during build and test", cc,
            "%s actions across %s cycle%s at %s CC per 100"
            % (format(actions, ","), cycles, "" if cycles == 1 else "s",
               rates.feature_credits("agent_flow_per_100")),
            True))  # side-effects bill on every harness

    if cfg["content_processing_pages"]:
        pages = int(cfg["content_processing_pages"]) * cycles
        cc = pages * rates.feature_credits("content_processing_per_page")
        result["lines"].append(_line(
            "Content processing during build and test", cc,
            "%s pages across %s cycle%s at %s CC per page"
            % (format(pages, ","), cycles, "" if cycles == 1 else "s",
               rates.feature_credits("content_processing_per_page")),
            True))

    total = sum(item["credits"] for item in result["lines"])
    unbilled = sum(item["unbilled_credits"] for item in result["lines"])
    reserve = total * float(reserve_percent) / 100.0

    # Velocity: evaluations are capped per agent node per day.
    min_days = None
    if eval_runs:
        min_days = int(math.ceil(
            float(cases * repeats) / rates.MAX_EVALUATIONS_PER_NODE_PER_DAY)) \
            * cycles

    result.update({
        "harness": harness,
        "harness_note": info["note"],
        "bills_during_build": billed,
        "currency": "Copilot Credits",
        "tier": tier,
        "effective_tier": effective_tier,
        "reasoning_model": reasoning,
        "reasoning_surcharge_credits": round(surcharge, 2) if billed else 0.0,
        "eval_cycles": cycles,
        "eval_runs": eval_runs,
        "interactive_hours": hours,
        "interactive_interactions": interactions,
        "total_credits": round(total, 2),
        "total_dollars": round(total * rates.DOLLARS_PER_CREDIT, 2),
        "unbilled_credits": round(unbilled, 2),
        "reserve_credits": round(reserve, 2),
        "budget_credits": round(total + reserve, 2),
        "budget_dollars": round((total + reserve) * rates.DOLLARS_PER_CREDIT, 2),
        "dollars_per_credit": rates.DOLLARS_PER_CREDIT,
        "min_elapsed_days": min_days,
        "eval_cap_per_day": rates.MAX_EVALUATIONS_PER_NODE_PER_DAY,
        "excluded": [
            "Production runtime once the agent is live",
            "Capacity pack sizing and overage enforcement",
            "End-user Microsoft 365 Copilot licence offsets",
            "Human hours for validation (collected to size test volume only)",
        ],
    })
    return result


def render_markdown(result):
    out = ["## Target platform — %s"
           % rates.TARGET_PLATFORMS.get(result["target"], {}).get(
               "label", result["target"]), ""]

    if result["target"] == "azure":
        out.append("Azure consumption during build and test, as supplied. "
                   "Azure rates are not\nbundled here — they depend entirely "
                   "on the services chosen.")
        out.append("")
        out.append("| Item | USD |")
        out.append("| --- | ---: |")
        for line in result["lines"]:
            out.append("| %s | $%s |" % (line["label"],
                                         format(line["dollars"], ",.2f")))
        out.append("| Reserve (%.0f%%) | $%s |"
                   % (result["reserve_percent"],
                      format(result["reserve_dollars"], ",.2f")))
        out.append("| **Budget ask** | **$%s** |"
                   % format(result["budget_dollars"], ",.2f"))
        out.append("")
        return "\n".join(out)

    out.append("**Target harness:** `%s` — %s"
               % (result["harness"], result["harness_note"]))
    out.append("")

    if not result["bills_during_build"]:
        out.append("> **On the standard harness, build and test in the "
                   "interface are not billed.**\n> Billing starts after "
                   "publish and embedded test chat does not count, so the "
                   "work\n> below consumes no credits. That is a correct "
                   "result, not a missing one.")
        out.append("")
        if result["unbilled_credits"]:
            out.append("Had this been the GitHub Copilot harness, the same "
                       "volume of preview and\nevaluation work would have cost "
                       "roughly **%s credits ($%s)** — worth knowing\nbefore "
                       "choosing a harness."
                       % (format(result["unbilled_credits"], ",.0f"),
                          format(result["unbilled_credits"]
                                 * result["dollars_per_credit"], ",.2f")))
            out.append("")

    billable = [l for l in result["lines"] if l["credits"] > 0]
    if billable:
        out.append("| Build-and-test activity | Credits | At $%.2f/CC | Basis |"
                   % result["dollars_per_credit"])
        out.append("| --- | ---: | ---: | --- |")
        for line in billable:
            out.append("| %s | %s | $%s | %s |"
                       % (line["label"], format(line["credits"], ",.0f"),
                          format(line["dollars"], ",.2f"), line["detail"]))
        out.append("| **Total** | **%s** | **$%s** | |"
                   % (format(result["total_credits"], ",.0f"),
                      format(result["total_dollars"], ",.2f")))
        out.append("| Reserve (%.0f%%) | %s | $%s | required contingency |"
                   % (result["reserve_percent"],
                      format(result["reserve_credits"], ",.0f"),
                      format(result["reserve_credits"]
                             * result["dollars_per_credit"], ",.2f")))
        out.append("| **Budget ask** | **%s** | **$%s** | |"
                   % (format(result["budget_credits"], ",.0f"),
                      format(result["budget_dollars"], ",.2f")))
        out.append("")

    if result["reasoning_model"] and result["reasoning_surcharge_credits"]:
        out.append("**Reasoning-model surcharge: %s credits ($%s).** Reasoning "
                   "models bill the feature\nrate *plus* the premium token "
                   "tier, so the effective tier is `premium` whatever\nthe "
                   "`%s` tier selected."
                   % (format(result["reasoning_surcharge_credits"], ",.0f"),
                      format(result["reasoning_surcharge_credits"]
                             * result["dollars_per_credit"], ",.2f"),
                      result["tier"]))
        out.append("")

    out.append("### The evaluation loop")
    out.append("")
    out.append("Evaluation is not a one-off gate. Microsoft's guidance is an "
               "explicit cycle —\ndefine tests, run evaluations, analyse "
               "results, improve the agent, repeat — with a\ntarget pass rate "
               "of %d–%d%% and near 100%% on core tests."
               % (rates.TARGET_PASS_RATE_LOW * 100,
                  rates.TARGET_PASS_RATE_HIGH * 100))
    out.append("")
    out.append("This estimate plans **%d cycle%s**: %s evaluation runs in "
               "total, plus the\nremediation each failed cycle sends back to "
               "the build platform."
               % (result["eval_cycles"],
                  "" if result["eval_cycles"] == 1 else "s",
                  format(result["eval_runs"], ",")))
    out.append("")
    if result.get("min_elapsed_days"):
        out.append("> **Velocity, not just cost.** Evaluations are capped at "
                   "**%d per agent node per\n> day**, so this volume needs a "
                   "minimum of **%d day%s** of elapsed time however much\n> "
                   "budget is available."
                   % (result["eval_cap_per_day"], result["min_elapsed_days"],
                      "" if result["min_elapsed_days"] == 1 else "s"))
        out.append("")

    out.append("### Human validation — a dependency, not a cost line")
    out.append("")
    if result["interactive_hours"]:
        out.append("**%.1f hours** of interactive validation are planned in "
                   "the Copilot Studio\ninterface. Those hours are collected "
                   "to size the test volume above — they are\n**not** "
                   "estimated as labour cost, consistent with this tool "
                   "metering agent\nconsumption rather than people."
                   % result["interactive_hours"])
    else:
        out.append("No interactive validation hours were declared. A Copilot "
                   "Studio build normally\nrequires someone to work in the "
                   "interface to validate behaviour and adjust\n"
                   "configuration; a plan without it is probably incomplete.")
    out.append("")
    out.append("Someone must go into the interface, confirm behaviour, and "
               "make configuration\nchanges between cycles. That step gates "
               "the loop, and no amount of build budget\nremoves it.")
    out.append("")
    out.append("### Not included")
    out.append("")
    for item in result["excluded"]:
        out.append("- %s" % item)
    out.append("")
    out.append("For production runtime consumption use Microsoft's "
               "[agent usage estimator](%s)." % result["runtime_estimator"])
    out.append("")
    out.append("Rates verified %s. Sources: [billing rates](%s) · "
               "[harness billing](%s) · [evaluation limits](%s) · "
               "[iteration guidance](%s)"
               % (result["verified"], result["sources"]["billing_rates"],
                  result["sources"]["harness"],
                  result["sources"]["eval_limits"],
                  result["sources"]["eval_guidance"]))
    out.append("")
    return "\n".join(out)
