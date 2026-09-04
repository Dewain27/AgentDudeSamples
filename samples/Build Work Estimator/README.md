# Build Work Estimator

**Author:** Dewain Robinson

An Agent Skill that estimates **the work of building something with an AI coding
agent** — how many turns it takes, how many tokens that consumes, and what it
costs — then renders the estimate as Markdown and PDF.

It calibrates itself against your own session history rather than shipping
assumed constants, requires a contingency reserve and checks whether that
reserve is actually big enough, reports in **the currency of the stack you build
with**, understands how that stack is licensed, and learns from what builds
actually cost.

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

## Two skills: review the breakdown, then estimate it

This plugin installs **two** skills, because they are different disciplines
with different failure modes.

| Skill | What it does |
| --- | --- |
| **Build Work Researcher** | Reviews a work breakdown against the specification it was sized from, *before* estimating. Surfaces components the specification requires but the breakdown does not own. |
| **Build Work Estimator** | Turns a reviewed breakdown into an estimate. |

The researcher exists because the breakdown is the estimator's weakest input.
Turn medians are measured; what they get *applied to* is a judgment someone
made when they wrote `size: medium, files: 11`, and nothing else checks whether
that list is complete.

Critically, **the researcher produces structure and questions, never numbers.**
It can say a component is missing or that a size is unsupported; it cannot say
what the size should be. That boundary is enforced mechanically — the findings
schema has no field a size could occupy, and the prose is scanned for effort
and cost assertions — so a review can never inject a guess into arithmetic
built from measured values.

Reviewing the Kestrel specification found four components the 39-item breakdown
did not own: disaster recovery, load testing, customer-managed keys, and
region-pinned inference. All four are now items, and the review ships as a
worked example in [`examples/kestrel-research-findings.yaml`](examples/kestrel-research-findings.yaml)
([rendered](examples/kestrel-research-review.md)).

## It always asks what the estimate was sized from

Before anything else, the estimator asks for a **functional** and a **technical**
specification. `none` is an acceptable answer — early estimates are legitimate —
but the question cannot go unanswered, because silence looks identical in the
output to a build that rested on agreed scope.

| Status | Confidence in sizing |
| --- | --- |
| `approved` | high — sizes rest on agreed scope |
| `in-review` | medium — scope may still move |
| `draft` | low — sizes will move as it settles |
| `none` | **very low** — sizes are informed guesses |

Without a specification the report opens with a prominent warning: the turn
medians behind the numbers are measured, but what they are applied to is not.
Writing the specification and re-running is named as the single
highest-value improvement available.

## Two platforms, two meters

The estimator asks two questions up front, because they are different questions
with different answers:

| Question | Field | Values |
| --- | --- | --- |
| What are you building **with**? | `build_platform` | `claude-code` · `github-copilot` |
| What are you building **on**? | `target_platform` | `copilot-studio` · `azure` · `both` · `ai-recommend` |

**Copilot Studio is not a build platform.** An AI-assisted build happens in a
coding agent authoring the agent definition; Copilot Studio is where the result
is deployed, previewed, evaluated, and validated. Microsoft's own VS Code
extension docs name GitHub Copilot and Claude Code as the harnesses used for
exactly that, under a heading called *Agent-driven development*.

Both meters are spent on the same project at the same time — they **add
together**, they are not alternatives.

### The target harness decides whether the target side bills at all

| Harness | Build, preview, test, evaluate |
| --- | --- |
| `standard` | **Not billed** — billing starts after publish, test chat does not count |
| `github-copilot` | **Billed from the moment building starts** |

Required whenever the target is Copilot Studio, and never guessed. A
standard-harness target legitimately returns near-zero target cost; the report
says so and shows the counterfactual for the other harness.

### Evaluations, remediation, and retesting are always planned

An agent build is a loop, not a pass. Each cycle adds remediation back onto the
build platform and re-runs evaluations on the target. **Evaluations are capped at
20 per agent node per day**, so a large test set sets a minimum elapsed time no
budget shortens — the report states that alongside cost.

Human validation in the Copilot Studio interface is named as a **dependency, not
a cost line**: planned hours size the interactive test volume, and are never
priced as labour.

**GitHub AI Credits are not Copilot Studio Copilot Credits.** Both are $0.01 per
credit, separate meters on separate products with separate allowances. They never
share a code path here.

## Licensing decides what the number means

| Licensing | The real question |
| --- | --- |
| **Consumption** — API/Console, Bedrock, Vertex, Foundry, pay-as-you-go | What will this cost? |
| **Seat** — Claude Pro/Max/Team/Enterprise, GitHub Business/Enterprise, prepaid packs | Will it fit, and what share of the seat does it burn? |

**A seat is not free.** Marginal spend inside an allowance is zero, but the seat
was bought with real money — so a build consuming 40% of a month's allowance
carries 40% of that month's seat cost. Reporting `$0` would be the same class of
error this tool exists to prevent.

The estimator also checks whether the build plus your *other* committed work
overruns the allowance, and warns that 5-hour and weekly windows can stall a
build that fits comfortably in a month.

Full detail: [`docs/platforms-and-licensing.md`](docs/platforms-and-licensing.md).

## Not a platform comparison tool

Each report covers one chosen build platform and one chosen target, and says so.
Platform decisions are not made on cost alone — capability, team skills,
governance, and integration matter more than a build-time figure — so the
shipped examples each show a single scenario and there is no side-by-side mode
in them.

When `target_platform` is `ai-recommend`, the skill interviews for requirements,
states a recommendation **with its reasoning**, and estimates the agreed target.
It refuses to run while the value is unresolved — the choice changes the
architecture, not just the number.

## Install

Runs in four hosts. Three artifacts cover them, all built from one source.

| Host | Install | Artifact |
| --- | --- | --- |
| **GitHub Copilot** (CLI / VS Code) | `copilot plugin marketplace add Dewain27/AgentDudeSamples`<br>`copilot plugin install build-work-estimator@agentdude-samples` | [`plugins/build-work-estimator/`](../../plugins/build-work-estimator/) |
| **Claude Code** | Point a skill directory at [`skill/build-work-estimator/`](skill/build-work-estimator/), or install the plugin folder above | same |
| **Microsoft Copilot Cowork** | Upload [`packages/build-work-estimator-cowork-plugin.zip`](packages/build-work-estimator-cowork-plugin.zip) | Teams manifest + icons + `skills/` |
| **Claude Cowork** · **Copilot Studio** | Upload [`packages/build-work-estimator.zip`](packages/build-work-estimator.zip) | Agent Skills standard package |

Both zips are **prebuilt and committed** — no toolchain needed to try them, per
this repo's conventions. Rebuild with:

```bash
python build/build_plugin.py          # canonical generator
python build/build_host_packages.py   # zips for the sandboxed hosts
```

### What changes per host

The estimator degrades honestly rather than failing. Run
`python scripts/environment.py` in any host for a capability report.

| Capability | Claude Code | GitHub Copilot | Copilot Cowork | Claude Cowork |
| --- | --- | --- | --- | --- |
| Measured calibration (`~/.claude/projects`) | **yes** | no | no | no |
| Manifest parsing | yes | yes | yes | yes |
| PDF rendered by the bundled script | yes | usually | no | no |
| Estimate still produced | yes | yes | **yes** | **yes** |

Two consequences, both handled and both stated in the output:

- **Only Claude Code can calibrate from measured history.** Everywhere else the
  estimate falls back to published baselines, and every report says which was
  used — a prior and a measurement are not the same claim.
- **Sandboxed hosts have no package installation and no browser.** PyYAML is not
  required: manifests are read by a bundled parser whose output is asserted
  identical to PyYAML's on every shipped manifest. For PDF, the packaged
  instructions tell the host to create the document natively from the Markdown
  rather than attempting to install a browser.

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

Two worked examples ship, deliberately different companies and projects rather
than a comparison:

| Scenario | Built with → built on | Licensing | Demonstrates |
| --- | --- | --- | --- |
| [Harbor Line Logistics](examples/harbor-line-estimate.md) ([pdf](examples/harbor-line-estimate.pdf)) | **Claude Code** → Copilot Studio, GitHub Copilot harness | Seat (Claude Max) | Both meters billing at once; 4 eval cycles; the 20-evals-per-day velocity cap forcing 24 days minimum; a **model blend that reprices** the measured per-turn cost by x0.71 |
| [Granite Peak Utilities](examples/granite-peak-estimate.md) ([pdf](examples/granite-peak-estimate.pdf)) | **GitHub Copilot** → Copilot Studio, standard harness | Seat (Copilot Business) | Standard harness billing nothing for build or test, with the counterfactual shown; side-effects still billing |
| [Copper Basin Utilities](examples/copper-basin-estimate.md) ([pdf](examples/copper-basin-estimate.pdf)) | **GitHub Copilot** → Copilot Studio, standard harness | Seat (Copilot Business) | A **blend of GPT models** — gpt-5.5 for hard reasoning, gpt-5.4 for the everyday work, gpt-5-mini for routine edits — priced from GitHub's published per-model table and weighted by share |

## A full worked scenario

The examples above are minimal illustrations. For a programme-scale case, see
[`scenarios/kestrel-financial/`](scenarios/kestrel-financial/): a regulated
wealth-management agent plus web application on Copilot Studio and Azure, with
a complete [product and technical specification](scenarios/kestrel-financial/specification.md)
— nine agent capabilities, eighteen tools, twelve integrations, 568 evaluation
cases across 6 cycles, 43 work items, 6 engineers, 5 months.

It is estimated **twice**, once built with Claude Code and once with GitHub
Copilot, sharing one work breakdown and one target. **Each report is
standalone** — neither references the other, because platform choice is not a
cost decision.

That scenario is also what forced three gaps out of the estimator: a GitHub
Copilot build could not accept a work breakdown at all, an Azure target could
not be itemised, and seat attribution had no notion of team size or duration.

## What good output looks like

Every report opens with an executive summary — the inputs that were given, then
four numbers — before any of the detail:

```
### What was estimated
  Built with (development tool)    Claude Code — metered in USD (tokens)
  Built on  (target environment)   Microsoft Copilot Studio — Copilot Credits
  Target harness                   github-copilot — bills for build, test, eval
  Licensing                        Seat — Claude Max, $200.00/month x 1 seat
  Evaluation cycles planned        4
  Contingency reserve              25%
  Calibration                      Measured, 24 local sessions

### Totals
                          Build (USD)   Target (Credits)   Combined (USD)
  Low                         $230.67             28,418         $514.85
  Likely                      $890.21             32,290       $1,213.11
  High                      $5,230.98             40,035       $5,631.33
  Likely + 25% reserve      $1,112.76             40,362       $1,516.38

  Plan for $1,213.11. Hold $1,516.38 including the 25% reserve.
```

The build range comes from observed spread in comparable work; the target range
from running 3 to 6 evaluation cycles instead of 4. Credits are converted at
$0.01 purely so both meters fit one column — they remain separate budgets on
different accounts, and the report says so.

Everything after the summary explains how each figure was reached.

### Reserve adequacy — the section that earns its keep

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

### Seat attribution — because a seat is not free

From the Harbor Line scenario, on a Claude Max seat:

```
Share of a typical month's allowance     107%
Seat cost per month                   $200.00
Attributable cost of this build       $214.94
Already committed to other work           45%
Total committed                          152%

Allowance overrun: exceeds by 52%.
Overage exposure: $104.94.
Build is concentrated — expect to hit 5-hour windows.
```

No extra money is invoiced, and the build still has a real cost: it consumes
more than a month of a seat that was bought with real money, and it will stall
against shorter windows before the month runs out.

### Credits, never tokens — from the Granite Peak scenario

A Copilot Studio build reports **19,617 Copilot Credits ($196.17)**, rising to
**25,502 ($255.02)** with a 30% reserve. Of that total, **16,116 credits
($161.16) is the reasoning-model surcharge alone** — 82% of the build's cost,
from a single setting.

Reasoning models bill the feature rate *plus* the premium tier, so selecting
`standard` and then using a reasoning model does not get standard pricing. The
premium tier is $100 per 1M tokens; Claude Opus 5 list input is $5. That 20×
gap is why tier selection moves a Microsoft build estimate more than almost any
scope decision.

Every heading, total, and row label in that report is denominated in Copilot
Credits. Tokens appear only in the Basis column, tracing back to Microsoft's
published "10 CC per 1K tokens" rate so the figure stays verifiable.

## How it works

| Stage | Script | What it does |
| --- | --- | --- |
| 0 | `version_check.py` | Stops the run if the install is behind the marketplace |
| 1 | `calibrate.py` | Measures your local sessions into a cost profile |
| 2 | `estimate.py` | Prices a work breakdown; **requires** a reserve % |
| 2b | `licensing.py` | Seat vs consumption; allowance share, attribution, overrun |
| 3 | `copilot_credits.py` / `github_copilot.py` | Build-time credits, per Microsoft stack |
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

## Build governance

Generated artifacts must never lag the code that produced them. Committed
sample output that is quietly wrong reads as authoritative, which is worse than
shipping no sample at all — so this is enforced rather than remembered.

**After any change to this sample, run the chain in order:**

```bash
cd "samples/Build Work Estimator"

python build/regenerate_examples.py     # rewrite the worked examples
python build/build_plugin.py            # regenerate plugins/build-work-estimator
python build/build_host_packages.py     # rebuild the host zips
python build/check_docs.py              # documentation still describes reality
cd tests && python -m unittest discover -p 'test_*.py'
```

**Documentation is part of the change, not a follow-up.** `check_docs.py`
settles every claim that can be settled mechanically — test counts cited in
prose, the script inventory in both directions, companion-file counts, rate
verification dates, and local links. It runs as its own CI step, so a PR that
adds a module without documenting it fails.

Then commit everything the chain touched.

### What CI enforces

[`.github/workflows/build-work-estimator.yml`](../../.github/workflows/build-work-estimator.yml)
runs on every push and pull request that touches **this sample or its generated
plugin** — it is path-scoped, so other samples in the repo neither trigger it
nor are affected by it.

| Check | Fails when |
| --- | --- |
| Test suite | Any test fails |
| **Documentation matches the repository** | A cited count, the script inventory, a rate date, or a local link has drifted |
| Runs without optional dependencies | The estimator breaks with PyYAML uninstalled |
| **Worked examples are current** | The committed examples drift from the code, or a PDF is left behind at old numbers |
| **Generated plugin is current** | `plugins/build-work-estimator` was not rebuilt after a source change |
| Host packages rebuild and validate | A package breaks a documented limit or the packaged example is stale |
| Rate staleness | Reported as a warning when a rate table is past its 90-day window |

### Why the examples are reproducible at all

The worked examples are generated from **committed inputs only**: the scenario
manifests and [`examples/calibration-profile.json`](examples/calibration-profile.json).
Estimate ids and timestamps are pinned per scenario, so two runs produce
byte-identical Markdown and the drift check can be a plain comparison rather
than a fuzzy one.

Before this existed the examples were built from a calibration profile that
lived only on one machine — nobody else could reproduce them, and nothing would
have noticed if they went stale.

PDFs are **not** byte-reproducible: the renderer embeds a creation date and the
compressor is not stable. They are regenerated every time and verified by
content instead — every headline figure in the Markdown must appear in the PDF
text, which catches the failure that actually matters, a PDF left behind at old
numbers.

## Tests

```bash
cd "samples/Build Work Estimator/tests" && python3 -m unittest discover -p 'test_*.py'
```

379 tests. Fixtures are synthetic and committed; no test reads real history and
no test makes a network call.

The most important suite is `test_contribute.py`. It seeds a ledger entry with
project names, absolute paths, dollar amounts, session ids, an exact date, and
an unanticipated extra field, then asserts none of them survive into the
contribution payload. It was written and passing **before** the submission path
was wired to `gh`.

## Requirements

**Python 3.9+ and nothing else.** Every dependency is optional:

| Package | Used for | If absent |
| --- | --- | --- |
| `PyYAML` | Manifest parsing | Bundled parser takes over, asserted identical on the supported subset |
| `pypdf` | Verifying PDF currency at build time | Skipped with a warning |
| `markdown` + `playwright` | PDF rendering | Markdown still written; host creates the PDF natively |
| `Pillow` | Icon generation at **build** time only | Not needed to run the skill |

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
9. **Host packaging is built to the documented formats, not verified in every
   host.** The Copilot Cowork package follows the Teams manifest v1.28 shape and
   the Agent Skills package follows the open standard — the same shapes the RFP
   sample in this repo ships. The packaged skill is tested end to end by
   extracting the zip and running it, and its limits are asserted against the
   documented ceilings, but no automated test installs it into Copilot Cowork,
   Claude Cowork, or Copilot Studio. Treat first-run in those hosts as
   unverified.
