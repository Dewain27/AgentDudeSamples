---
name: build-work-estimator
author: Dewain Robinson
description: Estimate the work of BUILDING something with an AI coding agent, in the currency of the stack it is built with — tokens and dollars for Claude Code, Copilot Credits for Copilot Studio, GitHub AI Credits for GitHub Copilot — calibrated from the user's own session history, with a required contingency reserve, licensing-aware output, and Markdown plus PDF reports. Use whenever someone asks what a build will cost, how many tokens or turns it will take, how long an agentic build will run, how much budget to request for AI-assisted development, or wants an estimate translated into Copilot Credits. Also use to record what a build actually cost afterwards so future estimates improve. This estimates the BUILD, never the RUN — decline runtime, licensing, infrastructure, and labour questions and point at Microsoft's agent usage estimator instead.
---

# Build Work Estimator

**Author:** Dewain Robinson

Estimates the work of **building** something with an AI coding agent, and
renders it as Markdown and PDF.

## The boundary — read this first

> **This estimates the BUILD. It never estimates the RUN.**
>
> If someone is building a Copilot Studio agent, this tells them what it costs
> to *author, iterate on, and test that agent*. It says nothing about what the
> agent costs once real users talk to it.

When asked for runtime cost, per-user licences, infrastructure, hosting, or
human labour: **say plainly that this tool does not estimate those**, and point
at Microsoft's [agent usage estimator](https://microsoft.github.io/copilot-studio-estimator/)
for runtime agent consumption. Do not improvise a runtime figure. Answering the
wrong question with a confident number is worse than declining.

## Run order

### 0. Version gate — always first

```bash
python scripts/version_check.py
```

**Exit code 2 means stop.** A newer version is published; tell the user not to
continue until they update, and show the update commands the script prints.
Do not run the estimate anyway. A warning about being unable to *check* is
different — that is fail-open, and work continues.

### 1. Calibrate

```bash
python scripts/calibrate.py --print
```

Derives real constants from the user's own local sessions: cost per turn,
median context, cache hit rate, subagent multiplier, and per-bucket turn
medians. With no history it falls back to published baselines and says so.

Aggregates only — no paths, project names, or content leave the machine.

### 1b. Ask what this was sized from — ALWAYS

**Before anything else, ask for both specifications.** An estimate without one
behind it is sizing from vibes: the turn medians are measured, but what they get
applied to is not.

| Field | Ask |
| --- | --- |
| `specification.functional` | Path, URL, or short description — what the thing does |
| `specification.technical` | Path, URL, or short description — how it is built |
| `specification.status` | `approved` · `in-review` · `draft` · `none` |

**`none` is an acceptable answer. Silence is not.** Early estimates are
legitimate and useful; an unanswered question is not, because it looks identical
in the output to a build that rested on agreed scope.

When neither exists, say so plainly, produce the estimate, and let the report
carry its low-confidence warning. Offer to help write the specification — it is
the single highest-value thing that would improve the number.

### 1c. Ask the three platform questions — do not assume any of them

**Q1. What are you BUILDING WITH?** — `build_platform`

| Value | Metered in |
| --- | --- |
| `claude-code` | USD (tokens) |
| `github-copilot` | GitHub AI Credits |

Those are the only two. **Copilot Studio is not a build platform** — it is where
the agent is deployed, previewed, evaluated, and validated. Microsoft's own VS
Code extension documentation names GitHub Copilot and Claude Code as the
harnesses used to author Copilot Studio agent components.

**Q2. What are you BUILDING ON?** — `target_platform`

| Value | Meaning |
| --- | --- |
| `copilot-studio` | Deployed to Copilot Studio |
| `azure` | Hosted on Azure services |
| `both` | Agent surface in Copilot Studio, Azure services behind it |
| `ai-recommend` | Run the requirements interview and propose one (below) |

**Q3. Which TARGET HARNESS?** — `target.harness`, required when the target is
Copilot Studio. This single answer moves the target-side figure between
effectively zero and the largest line in the estimate:

| Harness | Build, preview, test, evaluate |
| --- | --- |
| `standard` | **Not billed.** Billing starts after publish; test chat does not count |
| `github-copilot` | **Billed from the moment building starts** |

Never guess it. A standard-harness target legitimately returns near-zero
target-side cost — report that as correct, and show what the same work would
have cost on the other harness so the difference is visible.

**These are additive, not alternatives.** The same project spends on the build
platform and the target platform at the same time. Report both.

**GitHub AI Credits are not Copilot Studio Copilot Credits.** Both are $0.01 per
credit; separate meters, separate products, separate allowances.

### 1d. When `target_platform` is `ai-recommend`

Do not silently pick one. Interview for requirements, then recommend:

- Where must the data live, and what are the residency constraints?
- Is there an existing Power Platform estate, or an existing Azure estate?
- What does it integrate with — M365 surfaces, or line-of-business APIs?
- Who maintains it after delivery — makers, or engineers?
- What governance and ALM process must it fit?

State a recommendation **with its reasoning**, get the user's agreement, then set
`target_platform` to the agreed value and estimate that one. The estimator
refuses to run while the value is still `ai-recommend`.

### 1e. Licensing — what the number means

| `licensing.model` | What to report |
| --- | --- |
| `consumption` | The dollar/credit figure is the expected charge |
| `seat` | Allowance share, attributable seat cost, and overrun risk |

For `seat`, `seat_monthly_cost` and `other_workload_share` are **required**. A
seat is not free — reporting $0 for seat-based work is the same class of error
this tool exists to prevent. If the user does not know their seat cost, ask.

### 2. Estimate

```bash
python scripts/estimate.py --manifest estimate.yaml --out estimate.json
python scripts/estimate.py --interactive          # guided interview
```

**`reserve_percent` is required.** There is no default and no skip flag. If the
user has not given one, ask for it — the contingency percentage added on top of
the estimate for budgeting headroom. A value of 0 is allowed if they genuinely
intend to carry no reserve, and the report will flag it.

Manifest shape:

```yaml
project: Dispatch modernization

specification:                 # REQUIRED -- `none` is an answer, silence is not
  functional: docs/functional-spec.md
  technical: docs/technical-spec.md
  status: approved             # approved | in-review | draft | none

reserve_percent: 25            # REQUIRED
build_platform: claude-code       # claude-code | github-copilot
target_platform: copilot-studio   # copilot-studio | azure | both | ai-recommend

licensing:
  model: seat                     # seat | consumption
  plan: Claude Max
  seat_monthly_cost: 200          # REQUIRED for seat -- a seat is not free
  seats: 1
  other_workload_share: 0.45      # REQUIRED for seat -- already committed
  concentrated: true

target:                           # where it is deployed and evaluated
  harness: github-copilot         # REQUIRED for copilot-studio: standard | github-copilot
  tier: standard                  # basic | standard | premium
  reasoning_model: true           # forces the premium tier
  interactive_test_hours: 16      # human validation in the interface
  interactions_per_hour: 25
  eval_test_cases: 40             # always plan for evaluations
  eval_repeats: 3
  eval_cycles: 4                  # build -> deploy -> evaluate -> fix rounds
  agent_flow_actions: 250
  # azure targets instead:  azure_build_usd: 120.0

items:                            # build_platform: claude-code
  - name: Agent instructions, topics and tools
    size: medium                  # exploration|trivial|small|medium|large|subsystem
    files: 11
    unknowns: 2                   # 0-5, widens the upper bound
    brownfield: true

# build_platform: github-copilot uses this instead of items:
# github_copilot:
#   billing_mode: premium-requests   # ai-credits | premium-requests
#   interactions: 900
#   model_multiplier: 1.0
#   monthly_allowance: 1500
```

### 3. The evaluation loop — always plan for it

An agent build is not one pass. Microsoft's own guidance is an explicit cycle:
define tests, run evaluations, analyse results, improve the agent, repeat —
targeting an 80–90% pass rate, near 100% on core tests.

```
  build platform            target platform
  ---------------           ----------------
  author definition   -->   deploy
                            preview / interactive test   <- human, in the UI
                            run evaluations
  remediate           <--   evaluations fail
  (repeat)
```

**Always collect these**, and never assume a build passes first time:

| Field | What to ask |
| --- | --- |
| `eval_cycles` | How many build → deploy → evaluate → fix rounds to plan for |
| `eval_test_cases` · `eval_repeats` | Test set size; docs advise repeating a set for response variability |
| `interactive_test_hours` | **Hours a human will spend validating in the interface** — collected to size test volume, never priced as labour |

Each cycle after the first adds remediation back onto the build platform.
Evaluations are capped at **20 per agent node per day**, so a large test set
sets a minimum elapsed time whatever the budget — report that.

**Human validation is a dependency, not a cost line.** Someone must go into the
Copilot Studio interface, confirm behaviour, and make configuration changes
between cycles. Name it; do not estimate its hours as cost.

**GitHub Copilot as the build platform** — ask which billing model:

| Mode | What to collect |
| --- | --- |
| `ai-credits` | Interactions, tokens each, and the model's **published rates** from GitHub's models-and-pricing page. Rates are not bundled — ask for them |
| `premium-requests` | Interactions, model multiplier, monthly allowance |

Code completions and next edit suggestions consume nothing and are unlimited on
paid plans — they never enter the estimate.

### 4. Report

```bash
python scripts/render_report.py estimate.json -o build-estimate --format both
```

Writes `.md` and `.pdf`. If the PDF toolchain is missing, the Markdown is still
written and the run succeeds — report the remediation, do not treat it as a
failure.

### 5. Close the loop, after the build

```bash
python scripts/record_actual.py <estimate_id> --sessions <session-id> [...]
```

Records what the build actually cost and derives per-bucket correction factors
for future estimates. **Never guess which sessions belong to a build** — without
`--sessions` the script lists candidates and requires confirmation, because a
wrong attribution poisons every later estimate.

Corrections are shrunk toward 1.0 by sample size and are not applied below
n=2. When reporting one, always state its `n`.

### 6. Contribute, optionally

```bash
python scripts/contribute.py <estimate_id>
```

Offers to open a PR adding an anonymized record to the shared baseline. The
payload is built from a strict allowlist — no project names, paths, session
ids, dollar amounts, or exact dates, and it is not attributed to the
contributor.

**Never run this without the user explicitly asking for it.** It opens a public
pull request that cannot be recalled from git history. The script requires a
typed phrase; do not attempt to bypass or pre-answer that prompt.

## How to talk about the numbers

- **Lead with the sizing confidence.** An estimate with no specification behind
  it should be described that way in the first sentence, not buried.
- **Always give the range**, not just the point figure. Measured spreads within
  a single size class exceed 100×.
- **Lead with the reserve adequacy finding** when the reserve does not cover the
  observed high. That is the most actionable line in the report.
- **State the calibration source.** "Measured from 24 sessions" and "published
  baseline, no local history" are very different claims.
- **Flag thin buckets.** Where `n < 3`, the median is barely better than a guess
  and should be described that way.
- **Never present this as a quote.** It is a sample estimator; the disclaimer in
  every report says so and should not be softened.
- **Never denominate Copilot Studio work in tokens.** It is reported in Copilot
  Credits; GitHub Copilot work in GitHub AI Credits. Tokens appear only in a
  basis column tracing back to Microsoft's published per-1K-token rate.
- **Never treat the two meters as alternatives.** Build-side and target-side are
  spent on the same project at the same time and add together.
- **Never present this as a platform comparison.** Platform decisions are not
  made on cost alone — capability, skills, governance, and integration matter
  more — and steering that choice with this report would be misusing it.

## Bundled files

| Path | What it is |
| --- | --- |
| `scripts/rates.py` | Anthropic and Copilot Credit rate tables, each with source URL and verification date |
| `scripts/version_check.py` | Version gate |
| `scripts/calibrate.py` | Measures local history into a profile |
| `scripts/estimate.py` | The estimate model and reserve enforcement |
| `scripts/specification.py` | What the estimate was sized from, and its confidence |
| `scripts/build_model.py` | Which model builds it, and the repricing that follows |
| `scripts/environments.py` | Dev/QA/test/prod, and how each cost multiplies |
| `scripts/assumptions.py` | Measured vs judgment, and the provenance validator |
| `scripts/miniyaml.py` | Manifest parsing with no PyYAML dependency |
| `scripts/environment.py` | Capability probe for the host it is running on |
| `scripts/licensing.py` | Seat vs consumption, allowance attribution, overrun |
| `scripts/target_platform.py` | Target-side preview, test and evaluation cost |
| `scripts/copilot_credits.py` | Copilot Studio credit rate helpers |
| `scripts/github_copilot.py` | Build-time GitHub AI Credits / premium requests |
| `scripts/record_actual.py` | Records actuals, derives corrections |
| `scripts/contribute.py` | Anonymized community contribution |
| `scripts/render_report.py` | Markdown and PDF output |
| `references/methodology.md` | Why turns and context, not lines of code |
| `references/rates-copilot-credits.md` | The Microsoft rate detail |
| `assets/harbor-line-estimate.md` | Worked example: Claude Code stack, seat licensing |
| `references/platforms-and-licensing.md` | Why the two axes are different questions |

## Known limits

1. **Build only.** Not the run. Not licences, infrastructure, or labour.
2. **Turn counts are the weakest input.** Thin buckets are flagged; treat them
   as indicative.
3. **List pricing.** Contracted rates must be substituted.
4. **This machine only.** Other devices and claude.ai are not visible.
5. **Rates go stale.** A warning fires past 90 days; re-verify against source.
6. **This is a sample.** It demonstrates how to build an estimator. Modify it
   for the organization before any real budgeting use.
