# Cost Estimator — Design Spec

**Status:** Approved for implementation
**Date:** 2026-09-03
**Sample:** `samples/Cost Estimator/` → `plugins/cost-estimator/`

---

## 1. Purpose

An installable Agent Skill that produces a **baseline cost estimate for an
agentic build** — the cost of having an AI coding agent do the work — and
renders it as Markdown and PDF.

It exists because the naive way to estimate this is to guess, and guessing is
reliably wrong. The estimator's core idea is that **cost is driven by turns and
context size, not lines of code**, and that the constants should be *measured
from the estimator's own usage history* rather than assumed.

Where the work involves Microsoft technology, the estimate is additionally
translated into **Copilot Credits**, because that is the currency the budget
conversation actually happens in for Power Platform, Copilot Studio, and M365
Copilot work.

### 1.1 Non-goals

- **Not a quote engine.** No commercial terms, margin, labour, or licence cost.
- **Not a replacement for Microsoft's own estimators.** Where Microsoft
  publishes a first-party estimator, link to it; do not reimplement it.
- **Not a runtime meter.** It estimates before the work; it does not monitor
  spend during it.
- **Not multi-tenant.** Single user, local machine, local history.

---

## 2. Repository layout

Follows the existing repo convention: a sample owns its content; `plugins/` and
`.github/plugin/marketplace.json` are repo-level.

```
samples/Cost Estimator/
├── README.md                      What it is, install per host, worked example, known limits
├── docs/
│   ├── 2026-09-03-cost-estimator-design.md   This spec
│   ├── methodology.md             The cost model and its derivation
│   └── copilot-credits.md         Full Microsoft credit analysis, dated and sourced
├── examples/
│   ├── harbor-line-manifest.yaml  Fictional worked example input
│   ├── harbor-line-estimate.md    Expected output (Markdown)
│   └── harbor-line-estimate.pdf   Expected output (PDF)
├── tests/
│   ├── fixtures/                  Synthetic session JSONL
│   └── test_*.py
└── build/
    └── build_plugin.py            Generates plugins/cost-estimator/

plugins/cost-estimator/            Generated — edit the sample, not this
├── plugin.json
├── README.md
└── skills/cost-estimator/
    ├── SKILL.md
    ├── scripts/{version_check,calibrate,estimate,copilot_credits,render_report}.py
    ├── references/{rates-anthropic,rates-copilot-credits,methodology}.md
    └── assets/harbor-line-estimate.md
```

**Fictional company:** *Harbor Line Logistics*. Distinct from the RFP sample's
*Aventra Software Group*. All example figures are invented.

---

## 3. Component design

Five scripts, each independently runnable and testable. Python 3.9-compatible
syntax (no `match`, no PEP 604 unions in annotations).

### 3.1 `version_check.py`

Runs **first**, on every skill invocation, before any other work.

| Aspect | Behaviour |
|---|---|
| Source | `https://raw.githubusercontent.com/Dewain27/AgentDudeSamples/main/.github/plugin/marketplace.json` |
| Compare | Remote `plugins[name=="cost-estimator"].version` vs local `plugin.json` version, semver |
| Remote newer | Print local, remote, and update command. **Exit non-zero. The skill must stop and instruct the user not to continue until updated.** |
| Equal or local newer | Silent, exit 0 |
| Network failure / timeout (5s) | Print `⚠ Could not verify plugin version (offline?). Proceeding with local version X.Y.Z.` Exit 0 — fail-open |
| Malformed remote JSON | Same as network failure |

Fail-open on *inability to check* is deliberate: a public sample must not brick
itself offline. Fail-closed on a *confirmed* stale version is also deliberate —
that is the user's explicit requirement.

### 3.2 `calibrate.py`

Derives real cost constants from the local machine's own session history.

**Input:** `~/.claude/projects/*/*.jsonl` (main loop) and
`~/.claude/projects/*/*/subagents/*.jsonl` (subagents).

**Algorithm:**

1. Parse each line as JSON; skip unparseable lines silently (transcripts can be
   truncated mid-write).
2. Keep records where `type == "assistant"` and `message.usage` exists.
3. **Deduplicate by `requestId`** (falling back to `uuid`), per file. One API
   response can appear as multiple records.
4. Price each response:

   ```
   cost = ( input_tokens              * in_rate
          + cache_read_input_tokens   * in_rate * 0.10
          + cache_creation.ephemeral_5m_input_tokens * in_rate * 1.25
          + cache_creation.ephemeral_1h_input_tokens * in_rate * 2.00
          + output_tokens             * out_rate ) / 1e6
   ```

   If `cache_creation` is absent, fall back to `cache_creation_input_tokens`
   treated as 5m.
5. Attribute to `main` or `subagent` by file location.
6. Emit a profile.

**Output** `~/.claude/cost-estimator/profile.json`:

```json
{
  "schema": 1,
  "generated": "2026-01-01T00:00:00Z",
  "source": "measured",
  "sessions": 0,
  "date_range": ["2026-01-01", "2026-01-01"],
  "cost_per_main_turn": 0.00,
  "median_context_tokens": 0,
  "mean_output_tokens_per_turn": 0,
  "cache_hit_rate": 0.0,
  "subagent_multiplier": 1.0,
  "model_mix": {"<model-id>": 0.0},
  "component_shares": {"cache_read": 0.0, "cache_write": 0.0, "output": 0.0},
  "buckets": [{"label": "6-15 files", "n": 0, "median_turns": 0, "median_cost": 0.00,
               "min_cost": 0.00, "max_cost": 0.00}]
}
```

> Shape only — all values zeroed. This spec ships in a public repository, so it
> carries no real usage figures. Actual values are produced on the user's own
> machine and stay there (§3.2, Privacy).

**Fallback when no history exists.** `source: "published-baseline"`, using
Anthropic's published figures — $13/developer/active-day, $150–250/month, 90%
below $30/active day — and list rate card. The profile **must** carry
`source`, and every downstream report **must** state which was used. A
published-baseline estimate is materially less reliable than a measured one and
the report says so.

**Privacy:** the profile contains aggregates only. No file paths, no project
names, no prompt or response content. It is written to the user's home
directory and never transmitted.

### 3.3 `estimate.py`

**Input:** either an interactive interview or a manifest.

Manifest schema (`estimate.yaml`):

```yaml
project: Harbor Line dispatch rewrite
reserve_percent: 25          # REQUIRED — no default
microsoft: true              # triggers Copilot Credits analysis
items:
  - name: Dispatch API
    size: medium             # trivial | small | medium | large | exploration
    files: 9
    unknowns: 2              # 0-5; scales the range, not the point estimate
    brownfield: true
```

**Required-field enforcement.** `reserve_percent` is required in both paths.
The interview will not proceed past it; a manifest lacking it is rejected with
a clear error. There is no default and no `--skip-reserve` flag.
Valid range 0–500; a value of 0 is permitted but the report flags it.

**Cost model:**

```
turns_i     = bucket_median_turns(size_i) × brownfield_factor_i
cost_i      = turns_i × profile.cost_per_main_turn × profile.subagent_multiplier
base        = Σ cost_i

low         = Σ ( cost_i × bucket_min_i / bucket_median_i )
high        = Σ ( cost_i × bucket_max_i / bucket_median_i × (1 + 0.25 × unknowns_i) )

reserve     = base × reserve_percent / 100
budget_ask  = base + reserve
```

**Reserve adequacy check** — the distinguishing feature:

```
if budget_ask < high:
    required_pct = (high - base) / base × 100
    flag: "Reserve of {reserve_percent}% covers to ${budget_ask}.
           Observed high for comparable work is ${high}.
           Full coverage requires {required_pct}%."
```

This is reported prominently, not buried. Given measured spreads exceeding
100× within a single bucket, an under-covering reserve is the primary failure
mode this tool exists to catch.

### 3.4 `copilot_credits.py`

Runs only when `microsoft: true`. Produces a full credit analysis, not a single
converted number.

**All rates are dated and carry a source URL.** See §4.

**Modelled layers:**

1. **Build-time credits.** The GitHub Copilot harness bills from the moment
   building starts — creating, previewing, testing, and generating evaluations
   all consume credits, unlike the standard harness which bills after publish.
   This is its own line item; it is not folded into runtime.
2. **Token→credit conversion**, at the tier the user selects:
   `basic 0.1` / `standard 1.5` / `premium 10` Copilot Credits per 1K tokens.
3. **Feature-rate events** — per-interaction costs (classic answer, generative
   answer, agent action, graph grounding, agent flow actions).
4. **Reasoning-model surcharge.** Total = feature rate **+** premium tier per
   1K tokens. Modelled as a separate line so its impact is visible.
5. **Voice**, when applicable, per minute by tier.
6. **Capacity planning.** Packs of 25,000 credits/month. Unused credits **do
   not carry over**; usage resets on the 1st. Computes packs required, headroom,
   and overage exposure. Notes enforcement at 125% of tenant consumption.
7. **Licence offset.** Core agent features are **no charge** for
   Microsoft 365 Copilot–licensed users. The interview asks what share of users
   are licensed and shows billable vs non-billable split.
8. **Dollar cross-check.** At $0.01/credit, present the credit estimate in
   dollars alongside the Claude-side estimate, so both currencies for the same
   build are visible together.

**Explicit caveat carried into the report:** bring-your-own-model
configurations (including Azure Foundry models) are billed separately and are
**not** covered by these rates.

### 3.5 `render_report.py`

Markdown → PDF, reusing the approach already proven in this repo
(`skills/rfp-response/scripts/md_to_pdf.py`): `markdown` for HTML, Playwright
Chromium for PDF, CSS-styled cover page plus flowing body with running footer.

- `--format md` / `--format pdf` / `--format both` (default `both`)
- PDF failure (Playwright or Chromium missing) must **not** lose the estimate:
  write the `.md`, report the PDF failure with the remediation command, exit 0.

---

## 4. Rate tables

Rates live in one module per provider. **Every rate carries `SOURCE` (URL) and
`VERIFIED` (ISO date).** The skill warns when any table is more than 90 days
past its `VERIFIED` date.

### 4.1 Anthropic (list price, per 1M tokens)

`VERIFIED: 2026-06-24` · source: Claude Platform pricing docs

| Model | Input | Output |
|---|---|---|
| `claude-fable-5` | $10.00 | $50.00 |
| `claude-opus-5` | $5.00 | $25.00 |
| `claude-opus-4-8` / `4-7` / `4-6` | $5.00 | $25.00 |
| `claude-sonnet-5` | $2.00 | $10.00 |
| `claude-sonnet-4-6` | $3.00 | $15.00 |
| `claude-haiku-4-5` | $1.00 | $5.00 |

Multipliers: cache read **0.10×** input · cache write 5m **1.25×** · cache
write 1h **2.00×**.

> Contracted rates differ from list. The report states that it prices at list
> and that organizations on negotiated rates must substitute their own.

### 4.2 Copilot Credits

`VERIFIED: 2026-09-03`
Source: [Billing rates and management](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#copilot-credits-billing-rates)

| Agent feature | Rate | M365 Copilot–licensed user |
|---|---|---|
| Classic answer | 1 CC | No charge |
| Generative answer | 2 CC | No charge |
| Agent action | 5 CC | No charge |
| Tenant graph grounding for messages | 10 CC | No charge |
| Agent flow actions (per 100 actions) | 13 CC | No charge |
| Text/generative AI tools — basic | 0.1 CC per 1K tokens | No charge |
| Text/generative AI tools — standard | 1.5 CC per 1K tokens | No charge |
| Text/generative AI tools — premium | 10 CC per 1K tokens | No charge |
| Content processing tools | 8 CC per page | No charge |

Voice, per minute: classic **10 CC** · GenAI **35 CC** · premium GenAI
**75 CC** (core agent activity included).

Reasoning models: **feature rate + premium tier (10 CC per 1K tokens)**.
Source: [Reasoning model billing rates](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#reasoning-model-billing-rates)

**Pay-as-you-go: $0.01 per Copilot Credit.**
Source: [Pay-as-you-go meters](https://learn.microsoft.com/power-platform/admin/pay-as-you-go-meters#how-do-meters-work)
and [Meters for Microsoft Copilot pay-as-you-go](https://learn.microsoft.com/microsoft-365/copilot/pay-as-you-go/meters)

**Capacity packs:** 25,000 credits per pack per month, prepaid; **no
carryover**; resets on the 1st. Overage enforcement at 125% of tenant
consumption. Pre-purchase plans offer tiered discounts on 1-year terms;
discounts are contract-specific and are **not** hardcoded.
Source: [Capacity packs](https://learn.microsoft.com/microsoft-365/copilot/pay-as-you-go/copilot-capacity-packs)

**Derived, for the report's headline comparison:**

| Tier | CC per 1K tokens | $ per 1M tokens |
|---|---|---|
| basic | 0.1 | $1.00 |
| standard | 1.5 | $15.00 |
| premium / reasoning | 10 | **$100.00** |

The premium tier is ~20× Claude Opus 5 input pricing and 4× its output pricing.
Tier selection is therefore the highest-leverage variable in any Microsoft-side
estimate, and the report says so explicitly.

**Terminology note:** the billing currency changed from *messages* to *Copilot
Credits* on 2025-09-01. Older material referring to "messages" describes the
same meter.

**First-party estimators to link, not duplicate:**
[Copilot Studio agent usage estimator](https://microsoft.github.io/copilot-studio-estimator/)
and the [Copilot Credits estimator](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/billing-credit-overview) for the GitHub Copilot harness.

---

## 5. Report format

Sections, in order:

1. Title + generation metadata
2. **Disclaimer block** (§5.1) — mandatory, first content
3. Estimate summary: base, reserve, budget ask, range
4. **Reserve adequacy** finding
5. Per-item breakdown with turns, cost, range
6. Calibration basis — measured vs published-baseline, date, session count
7. Copilot Credits analysis (when applicable)
8. Assumptions and dominant sensitivities
9. Known limits

### 5.1 Disclaimer

Appears at **five** points: PDF cover page (boxed), PDF running footer (one
line), top of the `.md`, terminal output, and as a stated limit in `SKILL.md`
and the sample README.

> **⚠ SAMPLE — ESTIMATE ONLY, NOT A QUOTE**
>
> This document is generated by a **sample cost estimator** published as a
> demonstration of *how* an organization could build one. It is not a quote, a
> bid, a budget authority, or a commitment of any kind.
>
> **The figures are estimates and will be wrong.** They are derived from
> historical token consumption patterns that may not resemble the work being
> estimated. Observed cost for comparable work in the calibration data spans
> more than 100× between the cheapest and most expensive instances. Treat the
> range as the estimate; treat the point figure as the midpoint of a guess.
>
> **Before any real budgeting use, this estimator must be modified for your
> organization** — recalibrated against your own usage history, repriced
> against your contracted rates rather than list price, and adjusted for your
> own delivery patterns, model choices, and review overhead.
>
> Rates shown were verified on `{RATE_VERIFIED_DATE}` and change without
> notice. Calibration source: `{CALIBRATION_SOURCE}` · Generated
> `{TIMESTAMP}`

Footer line: `SAMPLE — estimate only, not a quote. Modify for your organization before budgeting use.`

Every dollar figure in the body is rendered with its range and dominant
sensitivity inline, so the caveat travels with the number.

---

## 6. Error handling

| Condition | Behaviour |
|---|---|
| Stale plugin version | **Stop.** Instruct update. Non-zero exit |
| Version check unreachable | Warn, continue |
| No session history | Published-baseline profile; state it in the report |
| Corrupt JSONL line | Skip silently; count and report total skipped |
| Unknown model id in history | Skip the record; report count as `unpriced_records` |
| `reserve_percent` missing | **Reject.** Clear error naming the field |
| Playwright/Chromium missing | Write `.md`, report PDF failure + remediation, exit 0 |
| Rate table >90 days past `VERIFIED` | Warn in terminal and in the report |

No failure silently produces a wrong number. Where the estimator cannot compute
something, it says so rather than substituting a guess.

---

## 7. Testing

- `test_calibrate.py` — fixture JSONL: dedup by `requestId`, cache-tier
  pricing, subagent attribution, corrupt-line tolerance, unknown-model skip,
  empty-history fallback.
- `test_estimate.py` — reserve required (both paths), reserve maths, adequacy
  flag fires when `budget_ask < high`, range monotonic in `unknowns`.
- `test_copilot_credits.py` — each rate row, reasoning surcharge = feature +
  premium, pack count and overage, licence offset, dollar cross-check.
- `test_version_check.py` — newer/equal/older remote, network failure, malformed
  JSON.
- `test_render_report.py` — disclaimer present at every required point;
  `.md` still written when PDF generation fails.

Fixtures are synthetic and committed. No test reads real user history.

---

## 8. Known limits

Stated in the sample README and the generated report:

1. **Turn counts per work bucket are the weakest input.** They come from
   whatever history the estimator can see. With few sessions in a bucket, the
   median is close to meaningless — the report shows `n` per bucket.
2. **List pricing only.** Organizations on contracted rates must substitute
   their own.
3. **Single machine.** Sessions from other devices or from claude.ai are not
   visible and are excluded.
4. **Rates go stale.** Both providers change pricing without notice. The 90-day
   warning is a prompt to re-verify, not a guarantee of currency.
5. **Copilot Credits scope.** Rates cover Copilot Studio–provided models.
   Bring-your-own-model, including Azure Foundry, is billed separately and not
   modelled.
6. **No labour, licence, or infrastructure cost.** Agent inference only.

---

## 9. Implementation sequence

1. Rate tables + `version_check.py` (+ tests)
2. `calibrate.py` (+ fixtures, tests)
3. `estimate.py` including reserve enforcement and adequacy check (+ tests)
4. `copilot_credits.py` (+ tests)
5. `render_report.py` with disclaimer (+ tests)
6. `SKILL.md` tying the flow together
7. Fictional worked example, generated by the real pipeline
8. `build_plugin.py`, generate `plugins/cost-estimator/`
9. `marketplace.json` entry + root README inventory row
10. Sample README + `methodology.md` + `copilot-credits.md`
