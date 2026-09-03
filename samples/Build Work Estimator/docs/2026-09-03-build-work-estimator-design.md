# Build Work Estimator — Design Spec

**Author:** Dewain Robinson
**Status:** Implemented. Revised 2026-09-03 for build-stack and licensing.
**Date:** 2026-09-03
**Sample:** `samples/Build Work Estimator/` → `plugins/build-work-estimator/`

---

## 1. Purpose

An installable Agent Skill that estimates **the work of building something with
an AI coding agent** — how many turns it will take, how many tokens that
consumes, and what that costs — then renders the estimate as Markdown and PDF.

> ### Build, not run
>
> This estimates **the cost of doing the build**. It does **not** estimate the
> cost of operating whatever gets built.
>
> If you are building a Copilot Studio agent, this tells you what it costs to
> *author, iterate on, and test that agent*. It tells you nothing about what the
> agent will cost once real users start talking to it. Those are different
> questions with different drivers, and conflating them produces a number that
> is wrong for both.

The estimator exists because the naive way to answer the build question is to
guess, and guessing is reliably wrong. Its core idea is that **build cost is
driven by turns and context size, not lines of code**, and that the constants
should be *measured from the estimator's own usage history* rather than assumed.

The estimate is reported in **the currency of the stack the build is done with**
— tokens and dollars for Claude Code, Copilot Credits for Copilot Studio, GitHub
AI Credits for GitHub Copilot — and **how that stack is licensed** decides what
the number means. Both are covered in `platforms-and-licensing.md`.

> **Revision, 2026-09-03.** The first implementation keyed the currency off
> `microsoft: true`, meaning *the target workload is Microsoft*. That was wrong:
> the currency follows what you build **with**, not what you build **for**, and
> using Claude Code to build a Copilot Studio agent bills in tokens. The key was
> removed rather than kept working, and `estimate.py` rejects it with guidance.
> The same revision added the licensing model — a seat is not free, so seat-based
> builds carry an attributable share of the seat cost rather than reporting $0.

### 1.1 What this does NOT estimate

Stated here, in the report, in `SKILL.md`, and in the sample README. This
boundary is the single most important thing about the tool.

| Out of scope | Why, and where to go instead |
|---|---|
| **Runtime / operational cost** of the built service | Driven by end-user traffic, not build effort. For Copilot Studio agents use Microsoft's [agent usage estimator](https://microsoft.github.io/copilot-studio-estimator/) |
| End-user seat licences (M365 Copilot, Power Platform) | Procurement question, unrelated to build effort |
| Infrastructure, hosting, storage, egress | Not agent inference |
| Human labour, PM, design, QA time | This meters agent turns, not people |
| Ongoing maintenance and support after delivery | A run cost, not a build cost |
| Model training or fine-tuning | Different cost structure entirely |

### 1.2 Non-goals

- **Not a quote engine.** No commercial terms or margin.
- **Not a replacement for Microsoft's first-party estimators.** Link, don't
  reimplement.
- **Not a runtime meter.** It estimates before the work; it does not monitor
  spend during it.
- **Not multi-tenant.** Single user, local machine, local history.

---

## 2. Repository layout

Follows the existing repo convention: a sample owns its content; `plugins/` and
`.github/plugin/marketplace.json` are repo-level.

```
samples/Build Work Estimator/
├── README.md                      What it is, install per host, worked example, known limits
├── docs/
│   ├── 2026-09-03-build-work-estimator-design.md   This spec
│   ├── methodology.md             The cost model and its derivation
│   └── copilot-credits.md         Build-time Microsoft credit analysis, dated and sourced
├── examples/
│   ├── harbor-line-manifest.yaml  Fictional worked example input
│   ├── harbor-line-estimate.md    Expected output (Markdown)
│   └── harbor-line-estimate.pdf   Expected output (PDF)
├── calibration/
│   ├── baseline.json              Aggregated community baseline, shipped in the plugin
│   ├── community/*.yaml           Contributed anonymized actuals, one file per record
│   └── aggregate.py               Rebuilds baseline.json from community/
├── tests/
│   ├── fixtures/                  Synthetic session JSONL
│   └── test_*.py
└── build/
    └── build_plugin.py            Generates plugins/build-work-estimator/

plugins/build-work-estimator/      Generated — edit the sample, not this
├── plugin.json
├── README.md
└── skills/build-work-estimator/
    ├── SKILL.md
    ├── scripts/{version_check,calibrate,estimate,copilot_credits,
    │             record_actual,contribute,render_report}.py
    ├── references/{rates-anthropic,rates-copilot-credits,methodology}.md
    └── assets/{harbor-line-estimate.md, baseline.json}
```

**Fictional company:** *Harbor Line Logistics*. Distinct from the RFP sample's
*Aventra Software Group*. All example figures are invented.

### 2.1 Marketplace registration

The plugin ships through the **existing marketplace already in this repo** — no
new marketplace, no second registration path. A second entry is added to
`.github/plugin/marketplace.json` alongside `rfp-response`:

```json
{
  "name": "build-work-estimator",
  "source": "plugins/build-work-estimator",
  "description": "Estimates the work of building something with an AI coding agent — turns, tokens, and cost — with a required budget reserve and optional Copilot Credits translation. Estimates the build, not the run.",
  "version": "1.0.0"
}
```

Marketplace `metadata.version` is bumped. Installation therefore uses the same
two commands users already know for this repo:

```
copilot plugin marketplace add Dewain27/AgentDudeSamples
copilot plugin install build-work-estimator@agentdude-samples
```

A row is added to the root `README.md` inventory table. The plugin id in
`marketplace.json`, `plugin.json`, and the skill directory must match exactly —
`version_check.py` (§3.1) resolves itself out of this file by `name`.

### 2.2 Authorship

**`Dewain Robinson` is the author on every item this sample produces**, in front
matter where the format has front matter, and in the equivalent metadata field
everywhere else. Applied consistently — a reader should find the same
attribution regardless of which artifact they open first.

| Item | Where the attribution goes |
|---|---|
| `plugin.json` | `"author": {"name": "Dewain Robinson", "url": "https://github.com/Dewain27"}` |
| `SKILL.md` | YAML front matter key `author: Dewain Robinson` |
| Spec, `methodology.md`, `copilot-credits.md` | `**Author:** Dewain Robinson` in the document front matter block |
| Sample `README.md`, plugin `README.md` | `**Author:** Dewain Robinson` under the title |
| `marketplace.json` entry | `"author": "Dewain Robinson"` on the plugin object |
| Python scripts | `__author__ = "Dewain Robinson"` module attribute + docstring line |
| Manifest schema (`estimate.yaml`) | Optional `author:` field, defaulting to `Dewain Robinson` in the shipped example |
| **Generated reports (`.md` and `.pdf`)** | `Author: Dewain Robinson` in the metadata block on the cover page and in the Markdown front matter; carried into PDF document properties |
| `examples/harbor-line-*.md` | Front matter `author: Dewain Robinson` |

`build_plugin.py` asserts the attribution is present in every generated artifact
and fails the build if any is missing, so it cannot drift as files are added.

> The existing `rfp-response` plugin currently carries
> `"author": {"name": "AgentDudeSamples"}`. It is **out of scope for this
> change** and is left as-is unless separately requested.

---

## 3. Component design

Seven scripts, each independently runnable and testable. Python 3.9-compatible
syntax (no `match`, no PEP 604 unions in annotations).

### 3.1 `version_check.py`

Runs **first**, on every skill invocation, before any other work.

| Aspect | Behaviour |
|---|---|
| Source | `https://raw.githubusercontent.com/Dewain27/AgentDudeSamples/main/.github/plugin/marketplace.json` |
| Compare | Remote `plugins[name=="build-work-estimator"].version` vs local `plugin.json` version, semver |
| Remote newer | Print local, remote, and the update command. **Exit non-zero. The skill must stop and instruct the user not to continue until updated.** |
| Equal or local newer | Silent, exit 0 |
| Network failure / timeout (5s) | Print `⚠ Could not verify plugin version (offline?). Proceeding with local version X.Y.Z.` Exit 0 — fail-open |
| Malformed remote JSON, or name absent | Same as network failure |

Fail-open on *inability to check* is deliberate: a public sample must not brick
itself offline. Fail-closed on a *confirmed* stale version is also deliberate —
that is the explicit requirement.

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
6. Bucket sessions by distinct files touched (`Edit`/`Write`/`NotebookEdit`
   `file_path` values) to derive per-bucket turn and cost medians.
7. Emit a profile.

**Output** `~/.claude/build-work-estimator/profile.json`:

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
> machine and stay there (Privacy, below).

**Fallback when no history exists.** `source: "published-baseline"`, using
Anthropic's published figures — $13/developer/active-day, $150–250/month, 90%
below $30/active day — and list rate card. The profile **must** carry `source`,
and every downstream report **must** state which was used. A published-baseline
estimate is materially less reliable than a measured one and the report says so.

**Privacy:** the profile contains aggregates only. No file paths, no project
names, no prompt or response content. It is written to the user's home directory
and never transmitted.

### 3.3 `estimate.py`

**Input:** either an interactive interview or a manifest.

Manifest schema (`estimate.yaml`):

```yaml
project: Harbor Line dispatch rewrite
reserve_percent: 25            # REQUIRED — no default
build_stack: claude-code       # claude-code | copilot-studio | github-copilot

licensing:                     # REQUIRED
  model: seat                  # seat | consumption
  plan: Claude Max
  seat_monthly_cost: 200       # REQUIRED for seat — a seat is not free
  seats: 1
  other_workload_share: 0.45   # REQUIRED for seat — already committed elsewhere
  concentrated: true           # compressed into a short delivery window

items:                         # claude-code stack only
  - name: Dispatch API
    size: medium               # trivial | small | medium | large | exploration
    files: 9
    unknowns: 2                # 0-5; scales the range, not the point estimate
    brownfield: true

# copilot-studio and github-copilot stacks carry their own activity blocks
# (`copilot_studio:` / `github_copilot:`) instead of `items:`, because the
# Claude-derived turn medians do not describe them.
```

**Required-field enforcement.** `reserve_percent` is required in both paths.
The interview will not proceed past it; a manifest lacking it is rejected with a
clear error. There is no default and no `--skip-reserve` flag. Valid range
0–500; a value of 0 is permitted but the report flags it.

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

Reported prominently, not buried. Given measured spreads exceeding 100× within a
single bucket, an under-covering reserve is the primary failure mode this tool
exists to catch.

### 3.4 `copilot_credits.py` — Copilot Studio, build-time only

Runs when `build_stack: copilot-studio`. Models **credits consumed while
building the agent**: authoring it, iterating on it, testing it, and generating its
evaluations. It does **not** model production traffic.

**Harness determines almost everything**, so the interview asks first:

| Harness | Build-time billing behaviour |
|---|---|
| **Standard harness** | Billing starts **after publish**. Embedded test chat messages are **not billed**. Build-time credits are therefore near zero — the report says so plainly rather than inventing a number. Non-zero only where a build exercises billable side-effects (agent flow runs, AI Builder / content-processing calls) against a published agent |
| **GitHub Copilot harness** | Billing starts **the moment you start building**. Creating a solution with natural language, previewing, testing, and generating/creating evaluations all consume credits. Credits cover LLM tokens, tools (knowledge and MCPs), and the harness itself |

**Build-time model (GitHub Copilot harness):**

```
build_credits = Σ over build activities of
                  ( feature_rate(activity)
                  + tokens(activity) / 1000 × tier_rate )
```

Activities the interview collects:

| Activity | Driver |
|---|---|
| Authoring / natural-language solution creation | Author turns × tokens per turn |
| Preview and test iterations | Test runs × interactions per run × feature rate |
| Evaluation generation and runs | Eval count × tokens |
| Knowledge / MCP tool calls during build | Included in credits; counted with the turn |

`tier_rate` is basic `0.1`, standard `1.5`, or premium `10` Copilot Credits per
1K tokens. **Reasoning models bill at feature rate + premium tier**, shown as its
own line so the surcharge is visible.

**Output:** total build-time credits, a dollar cross-check at $0.01/credit
alongside the Claude-side estimate, and the tier-sensitivity comparison. The
reserve percentage applies to the credit figure as well as the dollar figure.

**Explicitly excluded, and named in the report:** monthly production burn,
capacity-pack sizing, overage enforcement, voice minutes, and end-user M365
Copilot licence offsets. All are runtime concerns. The report points at
Microsoft's own estimator for them.

**Caveat carried into the report:** bring-your-own-model configurations
(including Azure Foundry models) are billed separately and are **not** covered
by these rates.

### 3.4c `github_copilot.py` — GitHub Copilot, build-time only

Runs when `build_stack: github-copilot`. **GitHub AI Credits are not Copilot
Studio Copilot Credits** — both are $0.01, and they are separate meters on
separate products with separate allowances. They never share a code path.

Two billing modes, asked for explicitly: `ai-credits` (tokens priced at the
model's published rates, converted to credits; pooled at billing-entity level on
Business and Enterprise) and `premium-requests` (legacy; one request times a
model multiplier against a monthly allowance). Per-model rates and multipliers
are **not hardcoded** — GitHub changes them, and the user supplies the rate for
the model they use. Code completions and next edit suggestions consume nothing.

### 3.4d `licensing.py` — what the number means

`consumption` billing makes the figure the expected charge. `seat` licensing
does not, and **must not report $0**: the seat was bought with real money, so a
build consuming a share of the allowance carries that share of the seat cost.

```
allowance_share   = build_notional_cost / typical_monthly_cost
attributable_cost = seat_monthly_cost x seats x allowance_share
total_committed   = allowance_share + other_workload_share
```

`typical_monthly_cost` comes from measured history extrapolated to 30 days.
Below 14 days of history the denominator would be guesswork, so the module
**declines to compute a share** rather than inventing one. `seat_monthly_cost`
and `other_workload_share` are required for seat licensing; seat prices are not
hardcoded because they change and vary by contract.

Overrun beyond the allowance is reported with its overage exposure. Shorter
5-hour and weekly windows are flagged separately, since a build that fits in a
month can still stall inside one.

### 3.5 Feedback loop — actuals in, better estimates out

Every estimate is a prediction. Without recording what actually happened, the
estimator cannot get better, and this whole sample would repeat the mistake it
exists to demonstrate. Two scripts close the loop: one local, one community.

```
estimate ──► ledger.json ──► build happens ──► record_actual ──► correction factors
                                                     │
                                                     └──► contribute ──► PR ──► baseline.json
                                                          (anonymized, opt-in)
```

`estimate.py` therefore assigns each estimate an **`estimate_id`** (ULID-style,
sortable) and appends it to `~/.claude/build-work-estimator/ledger.json` with the
manifest, profile snapshot, and predicted figures. The id is printed and appears
in the report metadata.

### 3.6 `record_actual.py`

Records what a build actually cost, after it is done.

**Invocation:** `record_actual.py <estimate_id> [--since DATE] [--sessions ID...]`

**Measuring the actual.** The estimator already knows how to measure — §3.2 is
the same machinery. Given an `estimate_id`, it re-scans session history from the
estimate's creation date forward, and attributes sessions to the build either by
explicit session ids or, by default, by asking the user to confirm the candidate
list. **It never guesses silently which sessions belong to the build**; an
unconfirmed attribution is the fastest way to poison the correction factors.

**Recorded per item:** `estimated_turns`, `actual_turns`, `estimated_cost`,
`actual_cost`, `ratio = actual/estimated`, plus the size class, files touched,
`unknowns`, and brownfield flag that were predicted from.

**Correction factors.** After recording, the local profile gains a
`corrections` block — per bucket, the median observed ratio:

```json
"corrections": {
  "medium": {"n": 0, "median_ratio": 1.0, "applied": false, "shrunk_ratio": 1.0}
}
```

Applied to future estimates as `turns × shrunk_ratio`, where:

```
shrunk_ratio = 1 + (median_ratio - 1) × n / (n + k)      # k = 3
applied      = n >= 2
```

Shrinkage toward 1.0 is not optional. With one actual, `median_ratio` is a
sample of size one and applying it raw would be exactly the over-confidence this
tool is meant to prevent. `k = 3` means a single actual moves the estimate 25% of
the way toward the observed ratio; five actuals move it 63%. The report always
states `n` behind any applied correction, and shows the pre-correction figure
alongside.

### 3.7 `contribute.py`

Offers to contribute an **anonymized** actual back to the repo so the shipped
baseline improves for everyone — particularly for new installs that have no local
history and currently fall back to published averages.

**Allowlist construction, not redaction.** The contribution record is built by
*copying named fields into a fresh object*. Nothing is copied unless it appears
in this list, so a field added later cannot leak by being forgotten:

```yaml
schema: 1
contributed: 2026-09            # month precision only — never a full date
size: medium                    # bucket label
files: 9
unknowns: 2
brownfield: true
estimated_turns: 431
actual_turns: 604
ratio: 1.40
model_tier: opus                # opus | sonnet | haiku | mixed
cache_hit_rate_band: "95-100"   # banded, not exact
harness: none                   # none | standard | github-copilot
```

**Never included, by construction:** project names, file paths, session ids,
prompt or response content, dollar amounts, contracted rates, org identifiers,
usernames, exact dates. Dollar figures are excluded deliberately — they can
expose negotiated pricing. Turn ratios carry the useful signal without it.

**Consent flow, in order:**

1. Print the **complete** record above, rendered, with nothing elided.
2. State plainly: this opens a public pull request to a public repository.
3. Require an explicit typed confirmation. **No default-yes, no `--yes` flag, no
   remembered consent.** Every contribution is confirmed separately.
4. On confirmation, use `gh` to fork (if needed), branch, commit one file to
   `calibration/community/`, and open a PR.
5. Without `gh` or auth: write the file locally, print the path and the manual
   steps. Never block.

**Nothing is ever transmitted without a fresh, explicit yes.** There is no
telemetry, no background upload, and no opt-out-by-default path. Contribution is
strictly a user-initiated action.

**Aggregation.** `calibration/aggregate.py` rebuilds `baseline.json` from
`community/`, publishing per-bucket median ratios with `n` and interquartile
range. Buckets with `n < 5` are published but flagged low-confidence; the plugin
will not apply a community correction below that threshold. Maintainer reviews
each PR — the dataset is small, human-readable, and one file per record
specifically so review is practical.

### 3.8 `render_report.py`

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

Multipliers: cache read **0.10×** input · cache write 5m **1.25×** · cache write
1h **2.00×**.

> Contracted rates differ from list. The report states that it prices at list and
> that organizations on negotiated rates must substitute their own.

### 4.2 Copilot Credits

`VERIFIED: 2026-09-03`
Source: [Billing rates and management](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#copilot-credits-billing-rates)

Rates below are the published table. The **Build-time** column records whether
each row can be incurred while building, which is the only part this tool models.

| Feature | Rate | Build-time? |
|---|---|---|
| Classic answer | 1 CC | Yes — test iterations |
| Generative answer | 2 CC | Yes — test iterations |
| Agent action | 5 CC | Yes — test iterations |
| Tenant graph grounding for messages | 10 CC | Yes — if exercised in test |
| Agent flow actions (per 100 actions) | 13 CC | Yes — flow runs during build |
| Text/generative AI tools — basic | 0.1 CC per 1K tokens | Yes |
| Text/generative AI tools — standard | 1.5 CC per 1K tokens | Yes |
| Text/generative AI tools — premium | 10 CC per 1K tokens | Yes |
| Content processing tools | 8 CC per page | Yes — if exercised in test |
| Voice (classic 10 / GenAI 35 / premium GenAI 75 CC per minute) | — | **No — runtime only** |

All rows are **no charge** for Microsoft 365 Copilot–licensed users. That offset
is a *runtime* consideration and is **not** applied to build estimates.

Reasoning models: **feature rate + premium tier (10 CC per 1K tokens)**.
Source: [Reasoning model billing rates](https://learn.microsoft.com/microsoft-copilot-studio/requirements-messages-management#reasoning-model-billing-rates)

**Pay-as-you-go: $0.01 per Copilot Credit.**
Source: [Pay-as-you-go meters](https://learn.microsoft.com/power-platform/admin/pay-as-you-go-meters#how-do-meters-work)
and [Meters for Microsoft Copilot pay-as-you-go](https://learn.microsoft.com/microsoft-365/copilot/pay-as-you-go/meters)

Capacity packs (25,000 credits/month, no carryover, enforcement at 125%) are
**runtime capacity planning** and are out of scope. Documented in
`copilot-credits.md` only as context for why build credits and run credits draw
on the same pool.

**Derived, for the report's headline comparison:**

| Tier | CC per 1K tokens | $ per 1M tokens |
|---|---|---|
| basic | 0.1 | $1.00 |
| standard | 1.5 | $15.00 |
| premium / reasoning | 10 | **$100.00** |

The premium tier is ~20× Claude Opus 5 input pricing and 4× its output pricing.
Tier selection is the highest-leverage variable in any Microsoft-side build
estimate, and the report says so explicitly.

**Terminology note:** the billing currency changed from *messages* to *Copilot
Credits* on 2025-09-01. Older material referring to "messages" describes the same
meter.

**First-party estimators to link, not duplicate:**
[Copilot Studio agent usage estimator](https://microsoft.github.io/copilot-studio-estimator/) ·
[Copilot Credits estimator for the GitHub Copilot harness](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/billing-credit-overview)

---

## 5. Report format

Sections, in order:

1. Title + generation metadata, including **`estimate_id`** and **author**
2. **Disclaimer block** (§5.1) — mandatory, first content
3. **Scope banner** — "This estimates the build, not the run", with the §1.1 table
4. Estimate summary: base, reserve, budget ask, range
5. **Reserve adequacy** finding
6. Per-item breakdown with turns, cost, range
7. Calibration basis — measured vs published-baseline, date, session count; and
   **any correction factor applied**, with its `n`, its shrunk value, and the
   pre-correction figure beside it (§3.6)
8. Build-time Copilot Credits analysis (when applicable)
9. Assumptions and dominant sensitivities
10. Known limits
11. **How to record actuals** — the `record_actual.py` command for this
    `estimate_id`, so the loop is closable from the report itself

### 5.1 Disclaimer

Appears at **five** points: PDF cover page (boxed), PDF running footer (one
line), top of the `.md`, terminal output, and as a stated limit in `SKILL.md` and
the sample README.

> **⚠ SAMPLE — BUILD ESTIMATE ONLY, NOT A QUOTE**
>
> This document is generated by a **sample estimator** published as a
> demonstration of *how* an organization could build one. It is not a quote, a
> bid, a budget authority, or a commitment of any kind.
>
> **It estimates the work of building only — never the cost of running what
> gets built.** Runtime, end-user licences, infrastructure, and human labour are
> all outside its scope and are not represented in any figure below.
>
> **The figures are estimates and will be wrong.** They are derived from
> historical token consumption patterns that may not resemble the work being
> estimated. Observed cost for comparable work in the calibration data spans more
> than 100× between the cheapest and most expensive instances. Treat the range as
> the estimate; treat the point figure as the midpoint of a guess.
>
> **Before any real budgeting use, this estimator must be modified for your
> organization** — recalibrated against your own usage history, repriced against
> your contracted rates rather than list price, and adjusted for your own
> delivery patterns, model choices, and review overhead.
>
> Rates shown were verified on `{RATE_VERIFIED_DATE}` and change without notice.
> Calibration source: `{CALIBRATION_SOURCE}` · Generated `{TIMESTAMP}`

Footer line: `SAMPLE — build estimate only, not a quote. Excludes runtime cost. Modify for your organization before budgeting use.`

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
| User asks for runtime cost | Decline, explain the boundary, link Microsoft's estimator |
| `record_actual` with unknown `estimate_id` | Reject; list recent ids from the ledger |
| `record_actual` cannot attribute sessions | **Ask.** Never guess which sessions belong to the build |
| Correction factor with `n < 2` | Compute but do not apply; show it as provisional |
| `contribute` without `gh` or auth | Write the record locally, print path + manual steps, exit 0 |
| `contribute` consent not given | Abort, transmit nothing, leave no file |
| Community bucket with `n < 5` | Publish flagged low-confidence; do not apply as a correction |

No failure silently produces a wrong number. Where the estimator cannot compute
something, it says so rather than substituting a guess.

---

## 7. Testing

- `test_calibrate.py` — fixture JSONL: dedup by `requestId`, cache-tier pricing,
  subagent attribution, corrupt-line tolerance, unknown-model skip,
  empty-history fallback, file-bucket assignment.
- `test_estimate.py` — reserve required (both paths), reserve maths, adequacy
  flag fires when `budget_ask < high`, range monotonic in `unknowns`.
- `test_copilot_credits.py` — each build-time rate row, standard harness yields
  near-zero build credits, GitHub Copilot harness bills from build start,
  reasoning surcharge = feature + premium, dollar cross-check, runtime rows
  (voice, packs, licence offset) are **not** reachable from a build estimate.
- `test_version_check.py` — newer/equal/older remote, network failure, malformed
  JSON, plugin name absent from marketplace.
- `test_render_report.py` — disclaimer present at every required point; scope
  banner present; author attribution present; `.md` still written when PDF
  generation fails.
- `test_record_actual.py` — ledger round-trip, ratio computation, shrinkage
  formula at n=1/2/5/20, correction not applied below n=2, unknown
  `estimate_id` rejected, ambiguous session attribution prompts rather than
  guesses.
- `test_contribute.py` — **the security-critical suite.** Given a ledger entry
  seeded with project names, absolute file paths, dollar amounts, session ids,
  and an exact date, assert the generated record contains **none** of them;
  assert the field set is exactly the §3.7 allowlist and that an unexpected
  input field is dropped rather than passed through; assert nothing is written
  or transmitted without confirmation; assert date precision is month-only.
- `test_aggregate.py` — median and IQR per bucket, `n < 5` flagged
  low-confidence, malformed community file skipped without failing the build.

Fixtures are synthetic and committed. No test reads real user history, and no
test performs a network call — `gh` and HTTP are stubbed.

---

## 8. Known limits

Stated in the sample README and the generated report:

1. **Build only.** Says nothing about what the built thing costs to run. This is
   a deliberate boundary, not a gap to be filled later without redesign.
2. **Turn counts per work bucket are the weakest input.** They come from whatever
   history the estimator can see. With few sessions in a bucket the median is
   close to meaningless — the report shows `n` per bucket.
3. **List pricing only.** Organizations on contracted rates must substitute their
   own.
4. **Single machine.** Sessions from other devices or from claude.ai are not
   visible and are excluded.
5. **Rates go stale.** Both providers change pricing without notice. The 90-day
   warning is a prompt to re-verify, not a guarantee of currency.
6. **Copilot Credits scope.** Rates cover Copilot Studio–provided models.
   Bring-your-own-model, including Azure Foundry, is billed separately and not
   modelled.
7. **Standard-harness builds are largely unbilled**, so a Microsoft estimate on
   that harness will be near zero. That is a correct answer, not a broken one.
8. **Correction factors are weak until they aren't.** Shrinkage keeps a single
   actual from swinging future estimates, but it also means the loop takes
   several completed builds to pay off. Early corrections are provisional and
   labelled as such.
9. **Community baseline reflects who contributed.** It is self-selected, not a
   representative sample of anyone's work. Useful as a fallback for installs
   with no local history; never better than the user's own measured profile.
10. **Contribution is one-way and public.** A merged record cannot be recalled
    from a public repository's history. The consent flow is deliberately
    unskippable for that reason.

---

## 9. Implementation sequence

1. Rate tables + `version_check.py` (+ tests)
2. `calibrate.py` (+ fixtures, tests)
3. `estimate.py` including reserve enforcement and adequacy check (+ tests)
4. `copilot_credits.py` and `github_copilot.py`, build-time models, plus
   `licensing.py` for seat attribution and overrun (+ tests)
5. `render_report.py` with disclaimer and scope banner (+ tests)
6. `record_actual.py` + ledger + shrinkage-corrected profile (+ tests)
7. `contribute.py` + `calibration/aggregate.py` + `baseline.json`
   (+ tests, allowlist suite first)
8. `SKILL.md` tying the flow together, leading with the build/run boundary
9. Fictional worked example, generated by the real pipeline
10. `build_plugin.py`, generate `plugins/build-work-estimator/`, assert
    authorship on every artifact
11. **Register in the existing `.github/plugin/marketplace.json`** (§2.1) + root
    README inventory row
12. Sample README + `methodology.md` + `copilot-credits.md` +
    `CONTRIBUTING-CALIBRATION.md` (what a contribution contains, what it never
    contains, how it is reviewed)

Within step 7, `test_contribute.py` is written and passing **before**
`contribute.py` is wired to `gh`. No contribution path ships ahead of the test
proving it cannot leak.
