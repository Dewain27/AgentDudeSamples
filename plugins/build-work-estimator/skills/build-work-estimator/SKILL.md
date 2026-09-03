---
name: build-work-estimator
author: Dewain Robinson
description: Estimate the work of BUILDING something with an AI coding agent — turns, tokens, and cost — calibrated from the user's own session history, with a required contingency reserve, an optional build-time Copilot Credits translation for Microsoft work, and Markdown plus PDF reports. Use whenever someone asks what a build will cost, how many tokens or turns it will take, how long an agentic build will run, how much budget to request for AI-assisted development, or wants an estimate translated into Copilot Credits. Also use to record what a build actually cost afterwards so future estimates improve. This estimates the BUILD, never the RUN — decline runtime, licensing, infrastructure, and labour questions and point at Microsoft's agent usage estimator instead.
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
reserve_percent: 25          # REQUIRED
microsoft: true              # optional: build-time Copilot Credits
copilot:
  harness: github-copilot    # none | standard | github-copilot
  tier: standard             # basic | standard | premium
  reasoning_model: true
  authoring_turns: 140
  tokens_per_turn: 4500
  test_runs: 35
  interactions_per_test_run: 6
  eval_runs: 25
items:
  - name: Dispatch API
    size: medium             # exploration|trivial|small|medium|large|subsystem
    files: 11
    unknowns: 2              # 0-5, widens the upper bound
    brownfield: true
```

### 3. Copilot Credits, when Microsoft work is in scope

Only build-time consumption. **Ask which harness** — it changes everything:

| Harness | Build-time billing |
| --- | --- |
| `standard` | Bills *after publish*; test chat is not billed → build credits near zero |
| `github-copilot` | Bills *from the moment building starts* — authoring, preview, test, evals |

A near-zero result on the standard harness is correct, not broken. Say so.

### 4. Report

```bash
python scripts/render_report.py estimate.json --credits-json credits.json \
    -o build-estimate --format both
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

## Bundled files

| Path | What it is |
| --- | --- |
| `scripts/rates.py` | Anthropic and Copilot Credit rate tables, each with source URL and verification date |
| `scripts/version_check.py` | Version gate |
| `scripts/calibrate.py` | Measures local history into a profile |
| `scripts/estimate.py` | The estimate model and reserve enforcement |
| `scripts/copilot_credits.py` | Build-time Copilot Credits |
| `scripts/record_actual.py` | Records actuals, derives corrections |
| `scripts/contribute.py` | Anonymized community contribution |
| `scripts/render_report.py` | Markdown and PDF output |
| `references/methodology.md` | Why turns and context, not lines of code |
| `references/rates-copilot-credits.md` | The Microsoft rate detail |
| `assets/harbor-line-estimate.md` | A complete worked example |

## Known limits

1. **Build only.** Not the run. Not licences, infrastructure, or labour.
2. **Turn counts are the weakest input.** Thin buckets are flagged; treat them
   as indicative.
3. **List pricing.** Contracted rates must be substituted.
4. **This machine only.** Other devices and claude.ai are not visible.
5. **Rates go stale.** A warning fires past 90 days; re-verify against source.
6. **This is a sample.** It demonstrates how to build an estimator. Modify it
   for the organization before any real budgeting use.
