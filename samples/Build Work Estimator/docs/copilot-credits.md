# Build-time Copilot Credits

**Author:** Dewain Robinson
**Rates verified:** 2026-09-03 (re-verified against source; no changes)

How this estimator translates a build into Copilot Credits, and — just as
importantly — what it refuses to translate.

---

## Scope: building, not running

> This models the credits consumed **while building an agent**: authoring it,
> iterating on it, testing it, and generating its evaluations.
>
> It does **not** model what the agent consumes once it is live.

For runtime consumption, use Microsoft's own tools:

- [Copilot Studio agent usage estimator](https://microsoft.github.io/copilot-studio-estimator/)
- [Copilot Credits estimator for the GitHub Copilot harness](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/billing-credit-overview)

Build credits and run credits draw on the same tenant pool, so both matter for
budgeting — but they are different calculations and this tool only does one.

## The harness decides almost everything

This is the single most important question to ask, and it is easy to miss.

| Harness | When billing starts | Build-time credits |
| --- | --- | --- |
| **Standard** | **After publish.** Embedded test chat messages are *not billed* | **Near zero** |
| **GitHub Copilot** | **The moment you start building** | **Substantial** |

On the GitHub Copilot harness, creating a solution with natural language,
previewing, testing, and generating or creating agent evaluations all consume
credits. Credits cover LLM tokens, tools (including knowledge and MCPs), and the
harness itself.

**A near-zero build estimate on the standard harness is a correct answer**, not
a broken one. Some billable side-effects can still occur during a standard-
harness build — agent flow runs and content-processing calls against a published
agent — and those are counted.

Source: [Overview of billing for agents and workflows powered by the GitHub Copilot harness](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/billing-credit-overview)

## Rates

Source: [Billing rates and management](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#copilot-credits-billing-rates)

| Feature | Rate | Reachable during build? |
| --- | ---: | --- |
| Classic answer | 1 CC | Yes — test iterations |
| Generative answer | 2 CC | Yes — test iterations |
| Agent action | 5 CC | Yes — test iterations |
| Tenant graph grounding for messages | 10 CC | Yes — if exercised in test |
| Agent flow actions (per 100 actions) | 13 CC | Yes — flow runs during build |
| Text/generative AI tools — basic | 0.1 CC per 1K tokens | Yes |
| Text/generative AI tools — standard | 1.5 CC per 1K tokens | Yes |
| Text/generative AI tools — premium | 10 CC per 1K tokens | Yes |
| Content processing tools | 8 CC per page | Yes — if exercised in test |
| Voice — classic 10 / GenAI 35 / premium GenAI 75 CC per minute | — | **No — runtime only** |

All of the above are **no charge** for Microsoft 365 Copilot–licensed users.
That offset is a *runtime* consideration — it concerns who is using the finished
agent — so it is **not** applied to build estimates.

**Pay-as-you-go: $0.01 per Copilot Credit.**
Sources: [Pay-as-you-go meters](https://learn.microsoft.com/power-platform/admin/pay-as-you-go-meters#how-do-meters-work) ·
[Meters for Microsoft Copilot pay-as-you-go](https://learn.microsoft.com/microsoft-365/copilot/pay-as-you-go/meters)

## The tier is the whole ballgame

Converting tokens to credits spans a **100× range** depending on tool tier:

| Tier | CC per 1K tokens | $ per 1M tokens |
| --- | ---: | ---: |
| basic | 0.1 | **$1.00** |
| standard | 1.5 | **$15.00** |
| premium | 10 | **$100.00** |

For comparison, Claude Opus 5 list pricing is $5.00 per 1M input tokens and
$25.00 per 1M output. The **premium tier is 20× Opus input pricing and 4× its
output pricing.**

Tier selection therefore moves a Microsoft build estimate more than almost any
scope decision. The report shows the comparison table every time.

## Reasoning models always land in premium

A reasoning model bills the **feature rate plus the premium token tier**:

```
total = feature_rate_for_the_operation + premium_tier × tokens/1000
```

So selecting `standard` and then using a reasoning model does not get standard
pricing — the effective tier becomes `premium` regardless. The estimator models
this explicitly and reports the surcharge as its own line, because it is easy to
select a reasoning model without realising it multiplies the token cost by
6.7× against standard.

In the bundled worked example, the reasoning surcharge is **$140.68 of a
$170.48 total** — 82% of the build's credit cost.

Source: [Reasoning model billing rates](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#reasoning-model-billing-rates)

## Deliberately excluded

These are all real and all matter for budgeting — they are simply not build
costs, and answering them here would produce a number that is wrong for both
questions:

| Excluded | Why |
| --- | --- |
| Monthly production credit burn | Driven by end-user traffic |
| Capacity pack sizing (25,000 CC/pack, no carryover) | Runtime capacity planning |
| Overage enforcement at 125% of tenant consumption | Runtime |
| Voice minutes | Runtime |
| End-user M365 Copilot licence offsets | Concerns who uses the finished agent |
| Bring-your-own-model, including Azure Foundry | Billed separately; these rates do not apply |

Capacity packs are worth knowing about even so: they provide 25,000 credits per
pack per month, prepaid, **unused credits do not carry over**, and usage resets
on the 1st. Build credits draw from the same pool as runtime credits, so a
build-heavy month reduces the headroom available to production traffic.

Source: [Capacity packs](https://learn.microsoft.com/microsoft-365/copilot/pay-as-you-go/copilot-capacity-packs)

## Terminology

The billing currency changed from **messages** to **Copilot Credits** on
2025-09-01. Older documentation referring to "messages" describes the same
meter; quantities per prepaid pack and the pay-as-you-go rate did not change.

Source: [Licensing for agents powered by the standard harness](https://learn.microsoft.com/microsoft-copilot-studio/billing-licensing)

## Staleness

Microsoft changes these rates without notice. Every rate in `rates.py` carries a
`VERIFIED` date, and the estimator warns when a table is more than 90 days past
it. **That warning is a prompt to re-verify against the source links above — not
a guarantee that anything younger is current.**
