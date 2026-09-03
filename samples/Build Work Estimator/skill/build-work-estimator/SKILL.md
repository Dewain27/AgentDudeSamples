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

### 1b. Establish the build stack and licensing — ask, do not assume

Two questions, and both change the answer.

**What are you building WITH?** This decides the currency, and it is independent
of what is being built FOR. Using Claude Code to build a Copilot Studio agent is
`claude-code` and bills in **tokens**. Never infer the stack from the target
workload.

| `build_stack` | Metered in |
| --- | --- |
| `claude-code` | USD (tokens) |
| `copilot-studio` | Copilot Credits |
| `github-copilot` | GitHub AI Credits |

**GitHub AI Credits are not Copilot Studio Copilot Credits.** Both are $0.01 per
credit; they are separate meters on separate products with separate allowances.
Never report one as the other.

**How is it licensed?** This decides what the number means.

| `licensing.model` | What to report |
| --- | --- |
| `consumption` | The dollar/credit figure is the expected charge |
| `seat` | Allowance share, attributable seat cost, and overrun risk |

For `seat`, `seat_monthly_cost` and `other_workload_share` are **required**. A
seat is not free — reporting $0 for seat-based work is the same class of error
this tool exists to prevent. If the user does not know their seat cost, ask;
do not guess, and do not skip it.

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
reserve_percent: 25            # REQUIRED
build_stack: claude-code       # claude-code | copilot-studio | github-copilot

licensing:
  model: seat                  # seat | consumption
  plan: Claude Max
  seat_monthly_cost: 200       # REQUIRED for seat -- a seat is not free
  seats: 1
  other_workload_share: 0.45   # REQUIRED for seat -- already committed
  concentrated: true           # compressed into a short window

# For build_stack: claude-code
items:
  - name: Dispatch API
    size: medium               # exploration|trivial|small|medium|large|subsystem
    files: 11
    unknowns: 2                # 0-5, widens the upper bound
    brownfield: true

# For build_stack: copilot-studio  (instead of items:)
# copilot_studio:
#   harness: github-copilot      # none | standard | github-copilot
#   tier: standard               # basic | standard | premium
#   reasoning_model: true        # forces the premium tier
#   authoring_turns: 160
#   test_runs: 45
#   eval_runs: 30

# For build_stack: github-copilot  (instead of items:)
# github_copilot:
#   billing_mode: ai-credits     # ai-credits | premium-requests
#   interactions: 400
#   dollars_per_1m_input: 5.0    # from GitHub's models-and-pricing page
#   dollars_per_1m_output: 25.0
```

### 3. Stack-specific pricing

Only the `claude-code` stack uses the turn-and-context model, because that is
what local calibration measures. Microsoft stacks are driven by their own
activity blocks — pricing them from Claude-derived turn medians would be
inventing a number.

**Copilot Studio** — ask which harness, it changes everything:

| Harness | Build-time billing |
| --- | --- |
| `standard` | Bills *after publish*; test chat is not billed → build credits near zero |
| `github-copilot` | Bills *from the moment building starts* — authoring, preview, test, evals |

A near-zero result on the standard harness is correct, not broken. Say so.

**GitHub Copilot** — ask which billing model:

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
- **Never denominate a Microsoft build in tokens.** Copilot Studio work is
  reported in Copilot Credits, GitHub Copilot work in GitHub AI Credits. Tokens
  appear only in a basis column tracing back to Microsoft's published per-1K-token
  rate.
- **Never present this as a stack comparison.** It reports one stack at a time.
  Stack decisions are not made on cost alone — capability, skills, governance,
  and integration matter more — and steering a stack choice with this report
  would be misusing it.

## Bundled files

| Path | What it is |
| --- | --- |
| `scripts/rates.py` | Anthropic and Copilot Credit rate tables, each with source URL and verification date |
| `scripts/version_check.py` | Version gate |
| `scripts/calibrate.py` | Measures local history into a profile |
| `scripts/estimate.py` | The estimate model and reserve enforcement |
| `scripts/licensing.py` | Seat vs consumption, allowance attribution, overrun |
| `scripts/copilot_credits.py` | Build-time Copilot Credits (Copilot Studio) |
| `scripts/github_copilot.py` | Build-time GitHub AI Credits / premium requests |
| `scripts/record_actual.py` | Records actuals, derives corrections |
| `scripts/contribute.py` | Anonymized community contribution |
| `scripts/render_report.py` | Markdown and PDF output |
| `references/methodology.md` | Why turns and context, not lines of code |
| `references/rates-copilot-credits.md` | The Microsoft rate detail |
| `assets/harbor-line-estimate.md` | Worked example: Claude Code stack, seat licensing |
| `assets/granite-peak-estimate.md` | Worked example: Copilot Studio stack, consumption |
| `references/licensing-and-stacks.md` | Why the stack decides the currency |

## Known limits

1. **Build only.** Not the run. Not licences, infrastructure, or labour.
2. **Turn counts are the weakest input.** Thin buckets are flagged; treat them
   as indicative.
3. **List pricing.** Contracted rates must be substituted.
4. **This machine only.** Other devices and claude.ai are not visible.
5. **Rates go stale.** A warning fires past 90 days; re-verify against source.
6. **This is a sample.** It demonstrates how to build an estimator. Modify it
   for the organization before any real budgeting use.
