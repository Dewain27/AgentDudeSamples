# Methodology

**Author:** Dewain Robinson

How this estimator arrives at a number, and why it is built the way it is.

---

## The premise: measure, don't assume

The obvious way to estimate an agentic build is to reason about it — how big is
the feature, how many files, how hard does it feel — and produce a figure. That
approach fails badly, and it fails in a specific, repeatable direction.

It fails because the intuitive cost drivers are the wrong ones. People reason
about **lines of code** and **feature complexity**. The actual drivers are
**how many turns the agent takes** and **how large the context is on each
turn**. Those correlate only loosely with how big the feature looks.

So the estimator does not reason about the work. It **measures what similar work
actually cost on this machine**, then scales.

## Where the money goes

Agentic coding is input-dominated. Every turn resends the whole conversation, so
the same tokens are re-read on every request. A representative cost breakdown
looks like this:

| Component | Share of spend | Share of tokens |
| --- | ---: | ---: |
| Cache read | ~68% | ~98% |
| Cache write | ~24% | ~2% |
| Output | ~8% | ~0.2% |
| Fresh input | ~0% | ~0% |

**Cost is context re-reading.** Output is a rounding error. That single fact
determines the model: don't carefully account for output tokens, account for
turns and context size.

The workable approximation is:

```
cost_per_turn ≈ context_size_in_thousands × (input_rate × cache_read_multiplier / 1000)
```

which for an Opus-tier model at 0.1× cache read comes out near
`context_k × $0.0005`, plus a smaller output term. In practice the estimator
does not use this formula at all — it uses the **measured** `cost_per_turn` from
real history, which absorbs the model mix, cache behaviour, and subagent
overhead automatically.

## The model

```
turns_i     = bucket_median_turns(size_i) × brownfield_factor × correction_factor
cost_i      = turns_i × cost_per_main_turn × subagent_multiplier
base        = Σ cost_i

low         = Σ ( cost_i × bucket_min_i / bucket_median_i )
high        = Σ ( cost_i × bucket_max_i / bucket_median_i × (1 + 0.25 × unknowns_i) )

reserve     = base × reserve_percent / 100
budget_ask  = base + reserve
```

Ranges are summed per item, not multiplied as ratios against the total — a
common mistake that makes multi-item estimates wrong in a way that is hard to
see.

## Buckets

Work is classified by **distinct files touched**, because that is something both
the estimator and the historical record can count consistently:

| Bucket | Files touched |
| --- | --- |
| `exploration` | 0 — research, reading, no edits |
| `trivial` | 1 |
| `small` | 2–5 |
| `medium` | 6–15 |
| `large` | 16–50 |
| `subsystem` | 51+ |

Calibration derives a median turn count and a cost range for each bucket from
real sessions. The number of sessions behind each bucket (`n`) travels with the
figure everywhere it is shown, because a median over three sessions and a median
over thirty are not the same kind of claim.

## Why the range matters more than the point

Within a single bucket, observed cost routinely spans **more than 100×**. A
medium-sized change can come in at a few dollars or several hundred, depending
on how many debug loops it needs, how much context accumulates, and whether the
session stays warm.

This has a direct consequence: **the point estimate is nearly meaningless on its
own.** The estimator always reports a range, and treats the point figure as the
midpoint of a guess rather than a prediction.

It also means the **contingency reserve is the important number**, which is why
it is a required input rather than an optional one.

## Reserve adequacy

Most estimating tools take a contingency percentage and add it. This one adds
it *and then checks whether it was enough*:

```
if budget_ask < high:
    required_pct = (high - base) / base × 100
```

If a 25% reserve covers to $636 while comparable work has reached $2,989, the
report says so and states that 488% would be required for full coverage.

That is usually the most useful line in the report. The common failure is not a
wrong point estimate — it is a reserve too thin for how wide the real spread is,
carried into a budget conversation without anyone noticing.

## Corrections from actuals

Recording what a build actually cost produces a per-bucket ratio of actual to
estimated turns. Applying that ratio raw would be a mistake: with one recorded
actual, it is a sample of size one.

So observed ratios are **shrunk toward 1.0** in proportion to sample size:

```
shrunk_ratio = 1 + (median_ratio − 1) × n / (n + 3)
applied      = n ≥ 2
```

One actual moves a future estimate 25% of the way toward the observed ratio.
Five move it 63%. Twenty move it 87%. A single surprising build cannot swing
everything that follows, which is the same over-confidence this estimator exists
to prevent.

## Which model builds it

`cost_per_main_turn` is one blended number measured from real sessions, and
that blend was produced by a specific mix of models. Build the same scope on a
pricier or cheaper model and the price of every token changes, but a measured
number cannot know that on its own.

So the build model is an explicit input. It is validated against the platform
that will run it -- **Claude Code runs Anthropic models, GitHub Copilot runs
its own published catalogue** -- because pricing a model the platform cannot
run would produce a confident number for a build that cannot happen.

Then one of two things happens, and the report always says which:

**Repriced.** The measured cost is scaled by a share-weighted ratio of
published per-model rates:

```
ratio = share_cache_read  x cache_read_rate(target)  / cache_read_rate(calibration)
      + share_cache_write x cache_write_rate(target) / cache_write_rate(calibration)
      + share_output      x output_rate(target)      / output_rate(calibration)
```

Every term is a **measured dollar share** times a ratio of **published rates**.
The shares already encode volume x rate reality, so nothing is reconstructed
from token counts and there is no free parameter. At `target == calibration`
the ratio is exactly 1.0 and the measured cost is returned untouched, so the
formula cannot drift away from the number it is anchored to.

The decomposition by component is not decoration. Claude Fable 5.1 reads cache
at 0.025x rather than 0.10x, and cache reads are about two thirds of the bill.
Scaling by the headline input rate alone would overstate that model by roughly
**98%**.

**Disclosed.** If no model was declared, or the profile lacks the measured
shares or the mix that produced it, nothing is rescaled. The calibration mix is
stated as an assumption and the report says plainly that it was not repriced.
Disclosure is the floor; repricing is the addition taken only when the data
supports it.

### What the rescale does not capture

It prices **tokens, not capability**. It does not model that a cheaper or
weaker model may need **more turns** to finish the same work -- a real effect
that is not derivable from published rates. The report states that limit every
time rather than folding it silently into the figure. The rescale also holds
the measured token profile -- context size, output length, cache behaviour --
constant.

## What is deliberately not modelled

- **Runtime cost of what gets built.** Different drivers entirely.
- **Human labour, licences, infrastructure.** Not agent inference.
- **Wall-clock time.** Turns are not minutes; a long session and a fast one can
  cost the same.
- **Quality.** A cheaper build is not a better one, and this says nothing about
  whether the output is any good.

## The weakest input, and what would fix it

Everything above is arithmetic on measured values except one thing: the work
breakdown itself. The turn medians are measured; what they get **applied to**
is a judgment someone made when they wrote `size: medium, files: 11`.

Nothing in the estimator checks whether that breakdown is complete, whether an
item is plausibly sized, or whether the specification is detailed enough to
size from at all.

[The Build Work Researcher design spec](https://github.com/Dewain27/AgentDudeSamples/blob/main/samples/Build%20Work%20Estimator/docs/2026-09-03-build-work-researcher-design.md)
specifies a companion skill that attacks exactly that gap — and, critically,
produces **structure and questions, never numbers**, so nothing it finds
enters the arithmetic without a human sizing it first.

## The honest limits

1. **Turn counts per bucket are the weakest input.** Everything else is
   arithmetic on measured values; the turn medians carry the uncertainty.
2. **List pricing.** Contracted rates change the answer materially.
3. **One machine.** Other devices and claude.ai sessions are invisible.
4. **Self-selection in the community baseline.** It reflects who contributed,
   not a representative population.
5. **It is a sample.** The point is the method, not the constants.
