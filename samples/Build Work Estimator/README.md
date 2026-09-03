# Build Work Estimator

**Author:** Dewain Robinson

An Agent Skill that estimates **the work of building something with an AI coding
agent** — how many turns it takes, how many tokens that consumes, and what it
costs — then renders the estimate as Markdown and PDF.

It calibrates itself against your own session history rather than shipping
assumed constants, requires a contingency reserve and checks whether that
reserve is actually big enough, translates Microsoft work into build-time
Copilot Credits, and can learn from what builds actually cost.

---

## This estimates the build, not the run

> It tells you what it costs to **build** a thing. It says nothing about what
> that thing costs to **operate** afterwards.
>
> If you are building a Copilot Studio agent, this covers authoring, iterating,
> and testing it. It does not cover what the agent consumes once real users
> start talking to it.

| Out of scope | Where to go instead |
| --- | --- |
| Runtime / operational cost | [Copilot Studio agent usage estimator](https://microsoft.github.io/copilot-studio-estimator/) |
| End-user seat licences | Your licensing/procurement process |
| Infrastructure, hosting, egress | Your cloud cost tooling |
| Human labour — PM, design, QA | Your delivery estimation process |
| Maintenance after delivery | A run cost, not a build cost |

Asked for any of those, the skill declines and redirects rather than
improvising a number.

## Install

```
copilot plugin marketplace add Dewain27/AgentDudeSamples
copilot plugin install build-work-estimator@agentdude-samples
```

The same commands work as `/plugin ...` inside an interactive Copilot session.
For Claude Code, point a skill directory at
[`skill/build-work-estimator/`](skill/build-work-estimator/).

## Try it

```bash
cd "samples/Build Work Estimator"

python skill/build-work-estimator/scripts/version_check.py
python skill/build-work-estimator/scripts/calibrate.py --print
python skill/build-work-estimator/scripts/estimate.py \
    --manifest examples/harbor-line-manifest.yaml --out /tmp/e.json
python skill/build-work-estimator/scripts/render_report.py \
    /tmp/e.json -o /tmp/estimate --format both
```

A complete worked example ships in
[`examples/harbor-line-estimate.md`](examples/harbor-line-estimate.md) and
[`.pdf`](examples/harbor-line-estimate.pdf).

## What good output looks like

The worked example produces a five-page report. The section that earns its keep:

```
Base estimate     $508.69
Reserve (25%)     $127.17
Budget ask        $635.86
Observed high   $2,989.13

The reserve does not cover observed variance.
Full coverage would require 488%.
```

Most estimating tools take a contingency percentage and add it. This one adds it
**and then checks whether it was enough**. Within a single size class, observed
build cost routinely spans more than 100× — so the usual failure is not a wrong
point estimate, it is a reserve too thin for the real spread, carried into a
budget conversation unnoticed.

For Microsoft work it also reports the reasoning-model surcharge separately. In
the worked example that surcharge is **$140.68 of a $170.48 total** — 82% of the
build's credit cost, from a setting that is easy to select without noticing.

## How it works

| Stage | Script | What it does |
| --- | --- | --- |
| 0 | `version_check.py` | Stops the run if the install is behind the marketplace |
| 1 | `calibrate.py` | Measures your local sessions into a cost profile |
| 2 | `estimate.py` | Prices a work breakdown; **requires** a reserve % |
| 3 | `copilot_credits.py` | Build-time Copilot Credits for Microsoft work |
| 4 | `render_report.py` | Markdown + PDF |
| 5 | `record_actual.py` | Records what the build really cost |
| 6 | `contribute.py` | Optionally shares an anonymized result |

The cost model, and why it counts turns instead of lines of code, is in
[`docs/methodology.md`](docs/methodology.md). The Microsoft rate detail — with
every rate's source URL and verification date — is in
[`docs/copilot-credits.md`](docs/copilot-credits.md).

### Self-calibrating

`calibrate.py` reads `~/.claude/projects/**`, prices every API response at list
rates with the correct cache tiers, and derives your real cost per turn, median
context, cache hit rate, and per-bucket turn medians. With no history it falls
back to Anthropic's published baselines **and says so in every report** — a
prior and a measurement are not the same claim.

The profile holds aggregates only. No paths, project names, prompts, or
responses. It never leaves the machine.

### Learning from actuals

After a build, `record_actual.py` measures what it really cost and derives
per-bucket correction factors. Observed ratios are **shrunk toward 1.0** by
sample size:

```
shrunk_ratio = 1 + (median_ratio − 1) × n / (n + 3)     applied at n ≥ 2
```

One recorded actual moves a future estimate 25% toward the observed ratio, not
100%. Without that, the first surprising build would swing everything after it —
the same over-confidence the tool exists to prevent.

### Contributing calibration data

`contribute.py` optionally opens a PR adding an **anonymized** record to a shared
baseline, so installs with no local history start from something better than a
population average.

The payload is built from a strict **allowlist** — nothing is included unless
named, so a field added later cannot leak by being forgotten. No project names,
paths, session ids, dollar amounts, exact dates, or contributor attribution.
Consent is required per contribution with a typed phrase; `y` and `yes` are
deliberately not accepted. Full detail, including exactly what is and is not
sent: [`docs/CONTRIBUTING-CALIBRATION.md`](docs/CONTRIBUTING-CALIBRATION.md).

## Tests

```bash
cd "samples/Build Work Estimator/tests" && python3 -m unittest discover -p 'test_*.py'
```

114 tests. Fixtures are synthetic and committed; no test reads real history and
no test makes a network call.

The most important suite is `test_contribute.py`. It seeds a ledger entry with
project names, absolute paths, dollar amounts, session ids, an exact date, and
an unanticipated extra field, then asserts none of them survive into the
contribution payload. It was written and passing **before** the submission path
was wired to `gh`.

## Requirements

Python 3.9+. `PyYAML` for manifests. `markdown` and `playwright` (with Chromium)
for PDF output — if those are missing the Markdown is still written and the run
still succeeds.

## Note

This is a **sample**. The worked example uses **Harbor Line Logistics**, a
fictional company; every figure in it is invented.

It demonstrates *how* to build an estimator. Before any real budgeting use it
must be modified for your organization — recalibrated against your own history,
repriced against your contracted rates rather than list price, and adjusted for
your own delivery patterns. Every report it generates says so.

## Known limits

1. **Build only.** Says nothing about what the built thing costs to run. This is
   a deliberate boundary, not a gap to fill later without redesign.
2. **Turn counts per bucket are the weakest input.** Everything else is
   arithmetic on measured values. Where `n < 3` the report flags the bucket and
   the figure is barely better than a guess.
3. **List pricing only.** Contracted rates change the answer materially.
4. **This machine only.** Sessions from other devices and from claude.ai are
   invisible and excluded.
5. **Rates go stale.** Both providers change pricing without notice. The 90-day
   warning is a prompt to re-verify, not a guarantee of currency.
6. **Standard-harness builds are largely unbilled**, so a Microsoft estimate on
   that harness comes out near zero. That is a correct answer, not a broken one.
7. **The community baseline is self-selected.** It reflects who contributed, not
   a representative sample, and is never better than your own measured profile.
8. **Contribution is one-way and public.** A merged record cannot be recalled
   from a public repository's history.
