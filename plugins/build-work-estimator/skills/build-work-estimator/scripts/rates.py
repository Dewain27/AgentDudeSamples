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

ANTHROPIC_VERIFIED = "2026-09-03"
ANTHROPIC_SOURCE = "https://docs.claude.com/en/docs/about-claude/pricing"

#: model id -> (input $/1M, output $/1M)
ANTHROPIC_RATES = {
    "claude-fable-5-1": (10.00, 50.00),
    "claude-mythos-5-1": (10.00, 50.00),
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
    # Retired models. Kept because historical sessions still calibrate
    # against them; dropping a rate would silently produce unpriced records.
    "claude-opus-4-1": (15.00, 75.00),
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-3-5": (0.80, 4.00),
}

# Multipliers applied to the model's *input* rate.
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00

#: Cache reads are 0.1x base input on every model EXCEPT Fable 5.1 and
#: Mythos 5.1, which read at 0.025x. Cache reads dominate agentic spend, so a
#: single global multiplier misprices those two models by 4x on the largest
#: component of the bill.
CACHE_READ_MULT = 0.10
CACHE_READ_MULT_OVERRIDES = {
    "claude-fable-5-1": 0.025,
    "claude-mythos-5-1": 0.025,
}


def cache_read_mult(model):
    """Cache-read multiplier for a model. Longest-prefix match."""
    if not model:
        return CACHE_READ_MULT
    best = None
    for known in CACHE_READ_MULT_OVERRIDES:
        if model.startswith(known) and (best is None or len(known) > len(best)):
            best = known
    return CACHE_READ_MULT_OVERRIDES[best] if best else CACHE_READ_MULT


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
        + cache_read * rin * cache_read_mult(model)
        + cache_write_5m * rin * CACHE_WRITE_5M_MULT
        + cache_write_1h * rin * CACHE_WRITE_1H_MULT
        + output_tokens * rout
    ) / 1e6


# --------------------------------------------------------------------------
# Anthropic published baselines -- the fallback when no local history exists
# --------------------------------------------------------------------------

#: Sonnet 5's $2/$10 launched as introductory pricing through 2026-08-31 and
#: is now the standard price; the scheduled rise to $3/$15 will not occur.
SONNET_5_PRICING_NOTE = (
    "Claude Sonnet 5 at $2/$10 per MTok was introductory pricing through "
    "2026-08-31 and is now the standard price. The increase to $3/$15 "
    "scheduled for 2026-09-01 will not occur."
)

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

# WHAT DOES THE BUILDING. An AI-assisted build happens in a coding agent --
# Claude Code or GitHub Copilot -- authoring the agent definition. Copilot
# Studio is NOT a build platform: it is where the result is deployed,
# previewed, evaluated, and validated. Microsoft's own VS Code extension
# documentation says as much, naming GitHub Copilot and Claude Code as the
# harnesses used to create and update Copilot Studio agent components.
BUILD_PLATFORMS = {
    "claude-code": {
        "label": "Claude Code",
        "currency": "USD (tokens)",
        "unit": "token",
        "note": "Metered in input/output/cache tokens, priced per model.",
    },
    "github-copilot": {
        "label": "GitHub Copilot",
        "currency": "GitHub AI Credits",
        "unit": "GitHub AI Credit",
        "note": "Metered in GitHub AI Credits, or legacy premium requests on "
                "older plans. A separate meter from Copilot Studio credits.",
    },
}

# WHERE IT RUNS. The target platform is where the agent is deployed and where
# preview, test, and evaluation consumption lands. It is a different meter
# from the build platform, and both are spent on the same project.
TARGET_PLATFORMS = {
    "copilot-studio": {
        "label": "Microsoft Copilot Studio",
        "currency": "Copilot Credits",
        "note": "Deployment, preview, test, and evaluation consumption is "
                "metered in Copilot Credits -- whether that is billed depends "
                "on the harness.",
    },
    "azure": {
        "label": "Azure",
        "currency": "Azure consumption (USD)",
        "note": "Model and service consumption billed to the Azure "
                "subscription. Rates depend on the services chosen and are "
                "supplied by the user, not bundled here.",
    },
    "both": {
        "label": "Copilot Studio and Azure",
        "currency": "Copilot Credits + Azure consumption",
        "note": "Agent surface in Copilot Studio with Azure-hosted services "
                "behind it. Both meters apply.",
    },
    "ai-recommend": {
        "label": "To be recommended",
        "currency": "decided after the requirements interview",
        "note": "The skill asks a short requirements interview, recommends a "
                "target with its reasoning, and estimates the agreed one.",
    },
}


def build_platform_info(name):
    key = str(name or "").strip().lower()
    if key not in BUILD_PLATFORMS:
        raise ValueError(
            "unknown build_platform %r; expected one of: %s"
            % (name, ", ".join(sorted(BUILD_PLATFORMS))))
    return BUILD_PLATFORMS[key]


def target_platform_info(name):
    key = str(name or "").strip().lower()
    if key not in TARGET_PLATFORMS:
        raise ValueError(
            "unknown target_platform %r; expected one of: %s"
            % (name, ", ".join(sorted(TARGET_PLATFORMS))))
    return TARGET_PLATFORMS[key]


# Documented evaluation constraints. These bound velocity, not just cost.
EVAL_LIMITS_SOURCE = (
    "https://learn.microsoft.com/microsoft-copilot-studio/"
    "workflows-experience/agent-node-workflow#test-and-evaluate-an-agent-node"
)
EVAL_GUIDANCE_SOURCE = (
    "https://learn.microsoft.com/microsoft-365/copilot/extensibility/"
    "evaluation-test-categories#iteration-loop"
)
MAX_EVALUATIONS_PER_NODE_PER_DAY = 20
MAX_AI_GENERATED_TEST_METHODS = 5
TARGET_PASS_RATE_LOW = 0.80
TARGET_PASS_RATE_HIGH = 0.90
EVAL_RESULTS_RETENTION_DAYS = 89


# --------------------------------------------------------------------------
# GitHub Copilot -- GitHub AI Credits, and legacy premium requests
# --------------------------------------------------------------------------
#
# DISTINCT from Copilot Studio Copilot Credits. Both happen to be $0.01 per
# credit; they are different meters on different products with separate
# allowances. Conflating them produces a plausible-looking wrong number.

GITHUB_VERIFIED = "2026-09-03"
#: Confirmed against the published models-and-pricing reference: "1 AI credit
#: = $0.01 USD", and code completions and next edit suggestions are not
#: billed in AI credits, remaining unlimited on all paid plans.
GITHUB_RATES_ARE_PUBLISHED = True
GITHUB_SOURCE = "https://docs.github.com/copilot/reference/copilot-billing/models-and-pricing"
GITHUB_LEGACY_SOURCE = "https://docs.github.com/copilot/concepts/billing/copilot-requests"
GITHUB_PLANS_SOURCE = "https://docs.github.com/en/copilot/get-started/plans"

#: USD per GitHub AI Credit.
DOLLARS_PER_GITHUB_AI_CREDIT = 0.01

# --------------------------------------------------------------------------
# GitHub Copilot -- per-model token rates
# --------------------------------------------------------------------------
#
# GitHub meters AI Credits from token consumption priced at the selected
# model's published rate, so which model builds is a cost input, not a
# preference. This table is the published catalogue.
#
# Only rates confirmed verbatim against the source page are listed. Every
# Anthropic row here independently matches ANTHROPIC_RATES above -- Sonnet 5
# at 2/10, Opus 5 at 5/25, Haiku 4.5 at 1/5 -- which is the corroboration
# that made shipping this table defensible rather than a transcription.
#
# The catalogue is larger than this. Models are added here only once their
# rate has been read off the source, because a guessed row would misprice
# every estimate that selected it.

GITHUB_MODEL_RATES_VERIFIED = "2026-09-04"
GITHUB_MODEL_RATES_SOURCE = GITHUB_SOURCE

#: model id -> (input $/1M, output $/1M) at the default (non-long-context) tier
GITHUB_MODEL_RATES = {
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5.3-codex": (1.75, 14.00),
    "gpt-5.4-nano": (0.20, 1.25),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4": (2.50, 15.00),
    "gpt-5.5": (5.00, 30.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

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

#: Agent flow TEST runs are explicitly exempt: "Testing an agent flow in the
#: flow designer or from the agent's test chat doesn't consume capacity for
#: agent flow actions. Test runs aren't blocked by enforcement."
#: Source: requirements-messages-management#agent-flow-enforcement
AGENT_FLOW_TEST_RUNS_EXEMPT = True

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
    ("GitHub per-model token rates", GITHUB_MODEL_RATES_VERIFIED,
     GITHUB_MODEL_RATES_SOURCE),
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


# --------------------------------------------------------------------------
# Which model builds it
# --------------------------------------------------------------------------
#
# The build platform constrains the model catalogue. Claude Code runs
# Anthropic models; GitHub Copilot runs its published multi-provider
# catalogue. Selecting a model the platform cannot run is a manifest error,
# not a rate to look up, so the two catalogues live behind one function and
# cannot drift apart from the validation that uses them.

#: build_platform -> (catalogue, human label for the error message)
_PLATFORM_MODELS = {
    "claude-code": (ANTHROPIC_RATES, "Claude Code runs Anthropic models"),
    "github-copilot": (GITHUB_MODEL_RATES,
                       "GitHub Copilot runs its published model catalogue"),
}


def models_for_platform(build_platform):
    """Model ids the given build platform can actually run."""
    key = str(build_platform or "").strip().lower()
    if key not in _PLATFORM_MODELS:
        raise ValueError(
            "unknown build_platform %r; expected one of: %s"
            % (build_platform, ", ".join(sorted(_PLATFORM_MODELS))))
    return _PLATFORM_MODELS[key][0]


def validate_model_for_platform(build_platform, model):
    """Raise unless `model` is available on `build_platform`.

    Claude Code cannot run a GPT model and GitHub Copilot cannot run a model
    absent from its catalogue. Pricing such a selection would produce a
    confident number for a build that cannot happen.
    """
    catalogue = models_for_platform(build_platform)
    key = str(model or "").strip().lower()
    if key in catalogue:
        return key
    _, why = _PLATFORM_MODELS[str(build_platform).strip().lower()]
    raise ValueError(
        "%r is not available on %s.\n\n%s. Available models:\n  %s"
        % (model, build_platform, why,
           "\n  ".join(sorted(catalogue))))


def normalise_model_mix(mix, build_platform):
    """Accept a single model id or a {model: weight} mix; return a mix.

    Weights are normalised to sum to 1 so a caller may express shares however
    is natural. Every model is validated against the platform first, because a
    mix containing one impossible model is an impossible mix.
    """
    if not mix:
        return {}
    if isinstance(mix, str):
        return {validate_model_for_platform(build_platform, mix): 1.0}
    if not isinstance(mix, dict):
        raise ValueError(
            "build_model must be a model id or a mapping of model to weight, "
            "got %r" % type(mix).__name__)

    out = {}
    for model, weight in mix.items():
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            raise ValueError(
                "build_model weight for %r must be a number, got %r"
                % (model, weight))
        if weight < 0:
            raise ValueError(
                "build_model weight for %r must not be negative." % model)
        out[validate_model_for_platform(build_platform, model)] = weight

    total = sum(out.values())
    if total <= 0:
        raise ValueError("build_model weights must sum to more than zero.")
    return {model: weight / total for model, weight in out.items()}


def describe_mix(mix):
    """Human label for a mix: 'gpt-5.5' or 'gpt-5.5 50% / gpt-5.4 30%'."""
    if not mix:
        return "not declared"
    if len(mix) == 1:
        return list(mix)[0]
    return " / ".join(
        "%s %.0f%%" % (model, weight * 100)
        for model, weight in sorted(mix.items(), key=lambda kv: -kv[1]))


def blended_github_rates(mix):
    """Weight-blend GitHub per-model token rates across a mix.

    A team rarely builds on one model: the cheap one handles routine edits and
    the expensive one handles the hard reasoning. Blending the published rates
    by the declared share prices that reality instead of forcing a single
    model to stand in for all of it.
    """
    if not mix:
        raise ValueError("cannot blend an empty model mix.")
    total = float(sum(mix.values()))
    rin = rout = 0.0
    for model, weight in mix.items():
        if model not in GITHUB_MODEL_RATES:
            raise ValueError(
                "no published GitHub rate for %r; known models: %s"
                % (model, ", ".join(sorted(GITHUB_MODEL_RATES))))
        share = float(weight) / total
        model_in, model_out = GITHUB_MODEL_RATES[model]
        rin += share * model_in
        rout += share * model_out
    return rin, rout


def component_rates(model):
    """Per-token cost of each cost component for one Anthropic model.

    Returned in $/1M tokens so the three are directly comparable:

      cache_read   input rate x the model's cache-read multiplier
      cache_write  input rate x the 5-minute cache-write multiplier
      output       the model's output rate
    """
    if model not in ANTHROPIC_RATES:
        raise ValueError(
            "unknown model %r; known models: %s"
            % (model, ", ".join(sorted(ANTHROPIC_RATES))))
    rin, rout = ANTHROPIC_RATES[model]
    return {
        "cache_read": rin * cache_read_mult(model),
        "cache_write": rin * CACHE_WRITE_5M_MULT,
        "output": rout,
    }


def blended_component_rates(mix):
    """Weight-blend `component_rates` across a {model: weight} mix."""
    if not mix:
        raise ValueError("cannot blend an empty model mix.")
    blended = {"cache_read": 0.0, "cache_write": 0.0, "output": 0.0}
    total = float(sum(mix.values()))
    for model, weight in mix.items():
        share = float(weight) / total
        for component, rate in component_rates(model).items():
            blended[component] += share * rate
    return blended
