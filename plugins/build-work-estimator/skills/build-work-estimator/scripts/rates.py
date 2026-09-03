#!/usr/bin/env python3
"""Rate tables for the Build Work Estimator.

Author: Dewain Robinson

Every rate carries a SOURCE url and a VERIFIED date. Rates change without
notice; `staleness_warnings()` surfaces tables that have gone stale so a
report can never quietly present old pricing as current.

This module is data plus lookup helpers. It performs no I/O and has no
dependencies outside the standard library.
"""

__author__ = "Dewain Robinson"

import datetime as _dt

STALE_AFTER_DAYS = 90

# --------------------------------------------------------------------------
# Anthropic — list price, USD per 1M tokens
# --------------------------------------------------------------------------

ANTHROPIC_VERIFIED = "2026-06-24"
ANTHROPIC_SOURCE = "https://docs.claude.com/en/docs/about-claude/pricing"

#: model id -> (input $/1M, output $/1M)
ANTHROPIC_RATES = {
    "claude-fable-5": (10.00, 50.00),
    "claude-mythos-5": (10.00, 50.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Multipliers applied to the model's *input* rate.
CACHE_READ_MULT = 0.10
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00


def rate_for(model):
    """Return (input_rate, output_rate) for a model id, or None if unknown.

    Exact match first, then longest known prefix (model ids sometimes carry a
    date suffix). Returns None rather than guessing a family rate -- an
    unpriced record is reported, never silently mispriced.
    """
    if not model:
        return None
    if model in ANTHROPIC_RATES:
        return ANTHROPIC_RATES[model]
    best = None
    for known in ANTHROPIC_RATES:
        if model.startswith(known) and (best is None or len(known) > len(best)):
            best = known
    return ANTHROPIC_RATES[best] if best else None


def price_response(model, input_tokens, cache_read, cache_write_5m,
                   cache_write_1h, output_tokens):
    """Cost in USD of one API response. Returns None if the model is unknown."""
    rates = rate_for(model)
    if rates is None:
        return None
    rin, rout = rates
    return (
        input_tokens * rin
        + cache_read * rin * CACHE_READ_MULT
        + cache_write_5m * rin * CACHE_WRITE_5M_MULT
        + cache_write_1h * rin * CACHE_WRITE_1H_MULT
        + output_tokens * rout
    ) / 1e6


# --------------------------------------------------------------------------
# Anthropic published baselines -- the fallback when no local history exists
# --------------------------------------------------------------------------

PUBLISHED_BASELINE_VERIFIED = "2026-09-03"
PUBLISHED_BASELINE_SOURCE = "https://code.claude.com/docs/en/costs"

PUBLISHED_BASELINE = {
    "cost_per_developer_active_day": 13.00,
    "cost_per_developer_month_low": 150.00,
    "cost_per_developer_month_high": 250.00,
    "p90_cost_per_active_day": 30.00,
}

# --------------------------------------------------------------------------
# Build stacks -- WHAT YOU BUILD WITH decides the currency
# --------------------------------------------------------------------------
#
# The stack you build WITH determines how the build is metered. The workload
# you build FOR does not. Using Claude Code to build a Copilot Studio agent is
# billed in tokens, not Copilot Credits -- getting this backwards prices the
# work in a currency nobody is charged in.

BUILD_STACKS = {
    "claude-code": {
        "label": "Claude Code",
        "currency": "USD (tokens)",
        "unit": "token",
        "module": "anthropic",
        "note": "Metered in input/output/cache tokens, priced per model.",
    },
    "copilot-studio": {
        "label": "Microsoft Copilot Studio",
        "currency": "Copilot Credits",
        "unit": "Copilot Credit",
        "module": "copilot_studio",
        "note": "Metered in Copilot Credits. Not tokens, and not GitHub AI "
                "Credits -- a separate meter that happens to share a rate.",
    },
    "github-copilot": {
        "label": "GitHub Copilot",
        "currency": "GitHub AI Credits",
        "unit": "GitHub AI Credit",
        "module": "github_copilot",
        "note": "Metered in GitHub AI Credits, or legacy premium requests on "
                "older plans. A separate meter from Copilot Studio credits.",
    },
}


def stack_info(name):
    key = str(name or "").strip().lower()
    if key not in BUILD_STACKS:
        raise ValueError(
            "unknown build_stack %r; expected one of: %s"
            % (name, ", ".join(sorted(BUILD_STACKS))))
    return BUILD_STACKS[key]


# --------------------------------------------------------------------------
# GitHub Copilot -- GitHub AI Credits, and legacy premium requests
# --------------------------------------------------------------------------
#
# DISTINCT from Copilot Studio Copilot Credits. Both happen to be $0.01 per
# credit; they are different meters on different products with separate
# allowances. Conflating them produces a plausible-looking wrong number.

GITHUB_VERIFIED = "2026-09-03"
GITHUB_SOURCE = "https://docs.github.com/copilot/reference/copilot-billing/models-and-pricing"
GITHUB_LEGACY_SOURCE = "https://docs.github.com/copilot/concepts/billing/copilot-requests"
GITHUB_PLANS_SOURCE = "https://docs.github.com/en/copilot/get-started/plans"

#: USD per GitHub AI Credit.
DOLLARS_PER_GITHUB_AI_CREDIT = 0.01

#: Billing modes GitHub currently runs in parallel.
GITHUB_BILLING_MODES = {
    "ai-credits": {
        "label": "Usage-based GitHub AI Credits",
        "note": "Interactions consume input, output, and cached tokens. "
                "GitHub prices those at the model's published rates and "
                "converts the result to AI Credits at $0.01 per credit. On "
                "Business and Enterprise plans credits are pooled at the "
                "billing-entity level.",
    },
    "premium-requests": {
        "label": "Legacy premium requests",
        "note": "Each interaction costs one premium request multiplied by the "
                "model's multiplier, drawn from a monthly plan allowance. "
                "Eligible Copilot Pro and Pro+ subscribers on existing annual "
                "plans remain on this model until their plan expires.",
    },
}

#: Code completions and next edit suggestions do not consume AI Credits and
#: are unlimited on paid plans -- so they contribute nothing to a build
#: estimate, however much they are used.
GITHUB_UNMETERED = (
    "Code completions",
    "Next edit suggestions",
)


# --------------------------------------------------------------------------
# Copilot Studio Credits
# --------------------------------------------------------------------------

COPILOT_VERIFIED = "2026-09-03"
COPILOT_SOURCE = (
    "https://learn.microsoft.com/microsoft-copilot-studio/"
    "requirements-messages-management#copilot-credits-billing-rates"
)
COPILOT_PAYG_SOURCE = (
    "https://learn.microsoft.com/power-platform/admin/"
    "pay-as-you-go-meters#how-do-meters-work"
)
COPILOT_REASONING_SOURCE = (
    "https://learn.microsoft.com/microsoft-copilot-studio/"
    "requirements-messages-management#reasoning-model-billing-rates"
)
COPILOT_HARNESS_SOURCE = (
    "https://learn.microsoft.com/microsoft-copilot-studio/"
    "agents-experience/billing-credit-overview"
)

#: USD per Copilot Credit, pay-as-you-go.
DOLLARS_PER_CREDIT = 0.01

#: Copilot Credits per event. `build_time` marks rows reachable while BUILDING
#: an agent (test iterations, flow runs during development). Rows with
#: build_time=False are runtime-only and are out of scope for this estimator.
CC_FEATURES = {
    "classic_answer": {"cc": 1, "build_time": True,
                       "label": "Classic answer"},
    "generative_answer": {"cc": 2, "build_time": True,
                          "label": "Generative answer"},
    "agent_action": {"cc": 5, "build_time": True,
                     "label": "Agent action"},
    "graph_grounding": {"cc": 10, "build_time": True,
                        "label": "Tenant graph grounding for messages"},
    "agent_flow_per_100": {"cc": 13, "build_time": True,
                           "label": "Agent flow actions (per 100 actions)"},
    "content_processing_per_page": {"cc": 8, "build_time": True,
                                    "label": "Content processing tools (per page)"},
}

#: Copilot Credits per 1000 tokens, by tool tier.
CC_TOKEN_TIERS = {
    "basic": 0.1,
    "standard": 1.5,
    "premium": 10.0,
}

#: Reasoning models bill the feature rate PLUS the premium token tier.
CC_REASONING_TIER = "premium"

#: Runtime-only rates. Held here so documentation can cite them accurately and
#: so tests can assert they are never reachable from a build estimate.
CC_RUNTIME_ONLY = {
    "voice_classic_per_min": 10,
    "voice_genai_per_min": 35,
    "voice_premium_genai_per_min": 75,
    "capacity_pack_credits": 25000,
    "overage_enforcement_pct": 125,
}

#: How each harness bills during the BUILD phase.
HARNESS_BUILD_BILLING = {
    "none": {
        "bills_during_build": False,
        "note": "No Copilot Studio harness in scope.",
    },
    "standard": {
        "bills_during_build": False,
        "note": (
            "Standard harness bills after publish, and embedded test chat "
            "messages are not billed. Build-time credits are therefore near "
            "zero. Non-zero only where the build exercises billable "
            "side-effects (agent flow runs, AI Builder or content-processing "
            "calls) against a published agent."
        ),
    },
    "github-copilot": {
        "bills_during_build": True,
        "note": (
            "GitHub Copilot harness bills from the moment you start building. "
            "Creating a solution with natural language, previewing, testing, "
            "and generating evaluations all consume credits. Credits cover "
            "LLM tokens, tools (knowledge and MCPs), and the harness itself."
        ),
    },
}

#: Derived, for the report's headline comparison: USD per 1M tokens by tier.
def dollars_per_million_tokens(tier):
    """Copilot Credit token tier expressed as USD per 1M tokens."""
    return CC_TOKEN_TIERS[tier] * 1000 * DOLLARS_PER_CREDIT


def credits_for_tokens(tokens, tier):
    """Copilot Credits consumed by `tokens` tokens at the given tool tier."""
    if tier not in CC_TOKEN_TIERS:
        raise ValueError(
            "unknown tier %r; expected one of %s"
            % (tier, ", ".join(sorted(CC_TOKEN_TIERS)))
        )
    return tokens / 1000.0 * CC_TOKEN_TIERS[tier]


def feature_credits(feature):
    """Copilot Credits for one occurrence of a billable feature event."""
    if feature not in CC_FEATURES:
        raise ValueError(
            "unknown feature %r; expected one of %s"
            % (feature, ", ".join(sorted(CC_FEATURES)))
        )
    if not CC_FEATURES[feature]["build_time"]:
        raise ValueError(
            "%r is a runtime-only rate and is out of scope for build "
            "estimation" % feature
        )
    return CC_FEATURES[feature]["cc"]


# --------------------------------------------------------------------------
# Staleness
# --------------------------------------------------------------------------

_TABLES = (
    ("Anthropic pricing", ANTHROPIC_VERIFIED, ANTHROPIC_SOURCE),
    ("Anthropic published baselines", PUBLISHED_BASELINE_VERIFIED,
     PUBLISHED_BASELINE_SOURCE),
    ("Copilot Credits", COPILOT_VERIFIED, COPILOT_SOURCE),
)


def staleness_warnings(today=None):
    """Return a warning string per rate table older than STALE_AFTER_DAYS."""
    if today is None:
        today = _dt.date.today()
    elif isinstance(today, str):
        today = _dt.date.fromisoformat(today)
    out = []
    for label, verified, source in _TABLES:
        age = (today - _dt.date.fromisoformat(verified)).days
        if age > STALE_AFTER_DAYS:
            out.append(
                "%s rates were verified %s (%d days ago) and may be out of "
                "date. Re-verify against %s" % (label, verified, age, source)
            )
    return out
