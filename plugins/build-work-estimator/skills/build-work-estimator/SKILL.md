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

## Done means the report exists

**Announcing that you are ready to run the estimate is not running it.**

"Ready to execute", "settings locked", "I can run it next" — these are not
outcomes. The user asked for an estimate; an estimate is a file. If you have
the inputs, run the commands in the same turn you finish collecting them. Do
not wait to be told to proceed a second time.

You are done when **all four** of these are true:

1. `scripts/estimate.py --report <name>` ran — one command that computes and
   writes the report, so there is no half-finished sequence to forget
2. The `.md` exists on disk (and the `.pdf` if asked for)
3. You told the user where the files are
4. You gave them the headline: likely, and likely-plus-reserve

If a required input is genuinely missing, ask for it and stop — that is a
legitimate halt. But once nothing is missing, run. A conversation that
collects every input and produces no file has failed, however agreeable it was.

If a command fails, show the error and what you are doing about it. Silence
after "ready to run" is the worst outcome available.

### Never say you ran something you did not run

**A status claim must be backed by output you can point at.** Do not say "I'm
running it now", "yes, it's running", or "that's in progress" unless a command
has actually executed and you can show what it printed. There is no background
execution here — nothing runs between your messages, so anything you have not
already done is not underway.

This happened, verbatim, in a real session:

> **User:** OK, so it is running now?
> **Assistant:** Yes.
> **User:** What is the status of it?
> **Assistant:** It is not running yet — I have not executed the estimate
> commands.

That is worse than being slow. The user waited on a claim that was never true.

If you are asked whether it is running and it is not: say so in one sentence,
then **run it in that same reply** rather than promising again.

## Say that you have started, and keep saying where you are

An estimate involves reading a specification, calibrating against history,
drafting a breakdown and running two scripts. From the outside that is a long
silence, and silence is indistinguishable from nothing happening.

**Say you have started before the first slow step**, in one line:

> Reading the specification and calibrating against your session history — I'll
> come back with a draft breakdown and anything I still need.

Then report as you go. One short line per phase, not a running commentary:

| After | Say |
| --- | --- |
| Calibrating | whether it measured real history or fell back to published baselines, and the sample size |
| Reading the specification | what it covers, and what you could not find in it |
| Drafting the breakdown | how many items, and which parts you are least sure of |
| Running the estimate | that it ran, and the headline figure |
| Rendering | where the files are |

If something is slow, say it is slow. If a step fails, say which one and what
you are doing about it. A user who can see where you are will wait; a user
staring at nothing assumes it is stuck — and in the session that prompted this
rule, they were right.

## Run order

### 0. Find a Python interpreter — before anything else

Every script here is Python. **`python` and `python3` are frequently absent
from a chat host's PATH while a perfectly good interpreter exists**, so a
`command not found` is the start of the problem, not the end of it. In a real
session the assistant declared itself blocked for four turns; the interpreter
was at `/usr/bin/python3` the whole time.

Work through this before concluding anything:

```bash
command -v python3 || command -v python \
  || ls /usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 \
       /usr/bin/python 2>/dev/null
```

Use whatever that finds — an absolute path is fine, and preferable to
reporting failure. Only if every one of them comes back empty is the
environment genuinely without Python; say so then, and say what the user would
need to install. Never present "python: command not found" as the final answer
without having looked in the standard locations.

### 0b. Version gate

```bash
<python> scripts/version_check.py
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

### 1a. If you were given a specification, READ IT

When the user points at a specification — a path, a URL, a pasted document —
**open it before asking them anything.** "Estimate this specification" is the
most common way this skill is invoked, and answering it with a list of
questions about fields they cannot see is the wrong response.

From the specification, draft the **work breakdown**. That is the estimator's
most important input and the one users are least able to produce cold:

1. List the components the specification implies — capabilities, integrations,
   surfaces, platform work, CI/CD, environments.
2. Give each a `size`, `files` and `unknowns`.
3. Include the work of *operating* what is built, not just its features:
   recovery, load testing, key management, residency. Specifications describe
   features; breakdowns forget properties.
4. **Show the draft and ask the user to correct it.** Present it as a table
   they can argue with, not a fait accompli.

Then set `breakdown_source: drafted` in the manifest. The report says the
sizes were drafted from the specification and confirmed by the user, rather
than authored by someone who knew the work. That distinction is real and the
reader is entitled to it.

**A drafted size is a starting point, not a measurement.** Say so when you
present it. The user changing your numbers is the process working.

If no specification is available, say what that costs — the breakdown cannot
be checked for completeness — and ask them to describe the work instead.

### Then ask everything you still need in ONE message

The steps below list what the estimate requires. **Collect them in a
single round, not one at a time.** Three waves of questions before anything
runs is the most common way this skill wastes a user's time.

Offer a sensible default for everything that has one, so the user can say
"those are fine" instead of answering eight questions:

| Input | If they don't say |
| --- | --- |
| `reserve_percent` | No default. Required, always ask. |
| `eval_cycles` | Propose 4, and say why |
| `eval_repeats` | Propose 3 |
| `eval_test_cases` | Propose a count scaled to the breakdown |
| `interactive_test_hours` | Propose a figure and label it an assumption |
| `licensing.seats` | Propose 1 unless they mention a team |

**Never assume a seat's whole allowance is free for this build.** A seat
carries a monthly credit allowance, and most of them are already doing other
work — that is what `other_workload_share` records. Defaulting it to `0.0`
claims the entire seat is available to this project, which is the most
optimistic possible reading and quietly understates what the build draws.

Ask it directly:

> How much of that seat's monthly allowance is already going to other work?
> `0.0` means this build gets the whole seat; `0.45` means 45% is already
> committed elsewhere. If you're not sure, a rough share is far better than
> assuming the seat is idle.
| `other_workload_share` | **No default. Always ask.** See below |
| `tier`, `reasoning_model` | Infer from the specification, and say what you inferred. **Copilot Studio fields** — they do nothing unless the target includes Copilot Studio |

**Never propose a `target.harness`.** It is in the required list below for a
reason: it swings the target figure between near-zero and the largest line in
the estimate, so a proposed default is a guess at the most consequential input.
Ask it, and if the build platform is GitHub Copilot say which pairing is
likely:

> You're building with GitHub Copilot. Authoring Copilot Studio agents that way
> usually means the `github-copilot` harness rather than `standard` — but they
> bill very differently, so I don't want to assume. Which is it?

**Never propose a value copied from the manifest example.** `Claude Max`, `200`
and `0.45` are placeholders in the shape reference below, not defaults. A real
session proposed all three as "drafted from your specification" on a build that
had nothing to do with Claude — they were drafted from an example. Licence
plan, seat cost and workload share come from the user or they are asked for;
they are never filled in from the sample.

These genuinely cannot be defaulted, and **the work breakdown is the first of
them**:

1. **`items:` — the work breakdown.** Draft it from the specification (step
   1a) or get it from the user. Without it there is nothing to estimate. Two
   real sessions listed "required inputs" as six config fields and never
   mentioned the breakdown at all, then could not run.
2. `reserve_percent`
3. `specification`
4. `build_platform`
5. `target_platform` — recommend it rather than asking cold
6. `target.harness`, when the target includes Copilot Studio
7. `seat_monthly_cost`, for seat licensing

Everything else can start from a proposal.

**Never ask for something the specification already answers.** If it names the
platform, the integrations, or the environments, read them out and confirm
rather than asking cold.

### 1b. Ask what this was sized from — ALWAYS

**Record what this was sized from.** If step 1a gave you a specification, you
already have it — note the path and confirm the status rather than asking cold.
If there is none, this is the question to ask.

An estimate with no specification behind it is sizing from vibes: the turn
medians are measured, but what they get applied to is not.

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
| `ai-recommend` | You analyse the requirements and recommend one (below) |

**Do not ask this cold.** Copilot Studio and Azure are both Microsoft, and the
choice between them is an architecture decision that follows from the
requirements — not a preference the user should have to hold in their head
before they can get an estimate.

If you have a specification, **read it and recommend**. Only ask outright when
there is nothing to reason from. If the user already knows, take their answer
and move on; a recommendation nobody wanted is just another question.

**Q3. Which TARGET HARNESS?** — `target.harness`, required when the target is
Copilot Studio. This single answer moves the target-side figure between
effectively zero and the largest line in the estimate:

| Harness | Build, preview, test, evaluate |
| --- | --- |
| `standard` | **Not billed.** Billing starts after publish; test chat does not count |
| `github-copilot` | **Billed from the moment building starts** |

**Ask this one as a preference first** — unlike the target platform, the
harness is usually a decision the team has already made about how they author,
and asking is faster than inferring. But offer the alternative in the same
breath:

> Which Copilot Studio harness — `standard` (the maker experience) or
> `github-copilot` (code-first)? If you'd rather I recommend one from your
> requirements, say so and I'll do that instead.

If they ask for a recommendation, set `harness: ai-recommend`, decide from
these signals, and agree it before estimating. The estimator refuses to price
`ai-recommend`, so it cannot be left undecided:

| Signal in the requirements | Points to |
| --- | --- |
| Makers author in the Copilot Studio interface; no source-control requirement for the agent definition; Power Platform ALM | `standard` |
| Agent definitions belong in source control; code-first authoring; engineers building with GitHub Copilot; a pipeline promoting the definition across environments | `github-copilot` |

**Recommend on fit, never on cost.** This is the input that swings the target
figure the most, which is exactly why a cost-driven recommendation would be
this tool steering an architecture decision with its own number. Decide on how
the team authors, then state the cost consequence as information.

Never guess it. A standard-harness target legitimately returns near-zero
target-side cost — report that as correct, and show what the same work would
have cost on the other harness so the difference is visible.

**These are additive, not alternatives.** The same project spends on the build
platform and the target platform at the same time. Report both.

**GitHub AI Credits are not Copilot Studio Copilot Credits.** Both are $0.01 per
credit; separate meters, separate products, separate allowances.

### 1d. Recommending the target platform

Read the specification for these signals before asking anyone anything. Most
specifications answer most of them.

| Signal in the requirements | Points to |
| --- | --- |
| A conversational surface for M365 users; makers maintain it; M365, Dataverse or Power Platform connectors; Power Platform governance | `copilot-studio` |
| A custom application or API surface rather than a chat one; engineers maintain it; line-of-business APIs, custom models, heavy data processing; network isolation, private endpoints, or residency controls | `azure` |
| An agent surface **with** custom services behind it — the common enterprise shape | `both` |

Where the specification is silent, ask only what is still undecided:

- Where must the data live, and what are the residency constraints?
- Is there an existing Power Platform estate, or an existing Azure estate?
- Who maintains it after delivery — makers, or engineers?
- What governance and ALM process must it fit?

State the recommendation **with the requirements that drove it**, cite where in
the specification, and get agreement before estimating. The estimator refuses
to run while the value is still `ai-recommend`, so a silent pick is impossible.

**Recommend on fit, never on cost.** The target decides which meters apply, so
a cost-driven recommendation would be this tool steering an architecture
decision with its own number. State the cost consequence *after* the
recommendation, as information, not as the reason.

### 1e. Licensing — what the number means

| `licensing.model` | What to report |
| --- | --- |
| `consumption` | The dollar/credit figure is the expected charge |
| `seat` | Allowance share, attributable seat cost, and overrun risk |

For `seat`, `seat_monthly_cost` and `other_workload_share` are **required**. A
seat is not free — reporting $0 for seat-based work is the same class of error
this tool exists to prevent. If the user does not know their seat cost, ask.

**Name the plan and the estimator checks it.** `rates.py` carries published
seat SKUs for both platforms, so a plan name is worth more than a remembered
number:

| Platform | What is published | What gets checked |
| --- | --- | --- |
| GitHub Copilot | Price **and** monthly AI-credit allowance per SKU | Seat cost against the published price, and any declared `monthly_allowance` against what the SKU actually includes |
| Claude | Price only | Seat cost against the published price |

**Never state an allowance for a Claude plan.** Anthropic publishes usage as a
relative multiplier over a rolling five-hour window — "5x or 20x more than
Pro" — not a credit count. There is no number to quote, and inventing one to
fill the gap is precisely the failure this estimator exists to prevent. On a
Claude seat, `other_workload_share` is the user's judgement and nothing can
cross-check it; say so rather than implying a check happened.

### 2. Estimate

```bash
python scripts/estimate.py --manifest estimate.yaml --out estimate.json
python scripts/estimate.py --interactive          # guided interview
```

**Sanity-check a declared rate before you use it.** Seat costs and token
rates are the inputs most often misremembered, and this estimator's whole
value is that its numbers are grounded. If a figure looks far from the
published price, say so and cite the source rather than accepting it:

> You mentioned $100/month for GitHub Copilot Pro. Published Copilot plan
> pricing is materially lower than that — Pro and Pro+ are different tiers with
> different prices. Worth checking against
> https://docs.github.com/en/copilot/get-started/plans before we commit it,
> because seat cost drives the attributed total directly.

You cannot look up live pricing, and you must not invent a figure to replace
theirs. Point at the published source, state the concern, and let them decide.
An estimate built on a 10x-wrong seat price is wrong in a way no reserve covers.

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

breakdown_source: authored     # authored | drafted -- see 1a
                               # `drafted` when YOU proposed the sizes from a
                               # specification and the user confirmed them.
                               # The report says so; a confirmed proposal is
                               # not the same claim as an authored judgement.

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

# build_platform: github-copilot ALSO uses items: above. Interactions are
# DERIVED from the same breakdown, so both platforms size the identical scope.
# github_copilot:
#   billing_mode: ai-credits         # ai-credits | premium-requests
#   build_model: gpt-5.4             # or a blend; validated against GitHub's catalogue
#   # interactions: 900              # omit -- derived from items: unless you override
#   model_multiplier: 1.0            # premium-requests mode only
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

### 4. Report — actually produce it

**Prefer the single command.** Estimating and rendering in one invocation
means "run it" is one action with a file at the end, not a sequence whose
second half keeps not happening:

```bash
python scripts/estimate.py --manifest estimate.yaml \
    --report build-estimate --format both
```

It prints the paths written and the headline figure. The separate form still
exists when you already have the JSON:

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
