# Build-Model Factor — Design Spec

**Author:** Dewain Robinson
**Status:** Specified, not implemented
**Date:** 2026-09-04

---

## 1. The gap

The estimator never asks which model does the building, and the answer moves
the number more than most inputs it does ask about.

On the Claude Code side, the build cost is `turns × cost_per_main_turn`, and
`cost_per_main_turn` is a single blended figure measured from session history
(`$0.32` in the shipped profile). That blend was produced by a specific model
mix — `{claude-opus-5: 0.55, claude-sonnet-5: 0.45}` — which the calibration
profile records in `model_mix` but which **nothing in the arithmetic reads and
no report section shows**. Build the same scope entirely on Opus, or entirely
on a cheaper model, and the estimate is identical and silent about the
assumption underneath it.

On the GitHub Copilot side the same choice hides in the `dollars_per_1m_input`
/ `dollars_per_1m_output` knobs: those *are* a per-model rate, but nothing
labels them as one or discloses which model they describe.

Cache reads are ~66% of Claude Code per-turn cost, and per-model input rates
differ several-fold (`rates.ANTHROPIC_RATES`: Opus 5 at \$5/1M input, Sonnet 5
at \$2, Haiku 4.5 at \$1). Model choice is plausibly a larger lever than the
reserve percentage. Today it is invisible on both platforms.

This is exactly the class of hidden, materially-significant assumption the
estimator exists to surface. The fix makes it an explicit, disclosed input —
and reprices by it only where that can be done from measured data and
published rates, never by guessing.

## 2. The boundary

The same rule that governs every figure governs this one: **no number unless
it is measured, a published rate, a value you declared, or arithmetic on
those.** A repricing that cannot be grounded that way is not produced; the
estimator discloses the assumption instead and says why it did not reprice.

Two honesty limits are stated in the report every time, never buried:

1. **A rescale captures price-per-token only.** It does *not* capture that a
   cheaper or weaker model may need *more turns* to do the same work. That
   turn-count effect is real and is not derivable from published rates, so it
   is named, not modelled.
2. **The rescale assumes the same token profile.** Holding context size,
   output length and cache behaviour at the calibration profile's measured
   values is an approximation; a different model does not change how many
   tokens the work needs, but it is still an assumption and is disclosed.

## 3. The repricing model (Claude Code)

### 3.1 Inputs, all already present or measured

- `cost_per_main_turn` — measured, the profile's real blended per-turn cost.
- `component_shares = {cache_read, cache_write, output}` — measured dollar
  shares of that cost. These already encode volume × rate reality, which is
  why no token-volume reconstruction is needed.
- `model_mix` — the measured mix that produced the two above.
- `rates.ANTHROPIC_RATES[model] = (input$/1M, output$/1M)` — published,
  sourced, verified.
- `rates.cache_read_mult(model)` and `rates.CACHE_WRITE_5M_MULT = 1.25` —
  published multipliers on the input rate.

### 3.2 The per-model component rates

For a model *m*:

```
cr(m) = input_rate(m) × cache_read_mult(m)     # cost of a cache-read token
cw(m) = input_rate(m) × CACHE_WRITE_5M_MULT    # cost of a cache-write token
out(m) = output_rate(m)                        # cost of an output token
```

For a mix `M = {model_i: weight_i}` (weights sum to 1), each component rate is
the weight-blended value: `cr(M) = Σ weight_i × cr(model_i)`, and likewise for
`cw` and `out`.

### 3.3 The ratio

```
ratio = shares.cache_read × cr(target) / cr(cal)
      + shares.cache_write × cw(target) / cw(cal)
      + shares.output      × out(target) / out(cal)

cost_per_main_turn(target) = cost_per_main_turn(measured) × ratio
```

where `cal` is the calibration profile's `model_mix` and `target` is the
declared `build_model`.

**Why this is grounded, not guessed.** Each term is a measured dollar share
times a ratio of published rates. At `target == cal` every ratio is exactly
1.0, so `ratio = 1.0` and the measured cost is returned unchanged — the
formula cannot drift away from the measured number at the point where it is
anchored. Away from the calibration mix it moves by exactly the published
per-token price differences, weighted by where the money actually went. There
is no free parameter and no tolerance window.

### 3.4 `build_model` as a single model or a mix

A real build uses more than one model — Opus for hard reasoning, a cheaper
model for routine edits. So `build_model` accepts either:

```yaml
build_model: claude-opus-5            # shorthand for {claude-opus-5: 1.0}
```
```yaml
build_model:                          # an explicit mix, weights sum to 1
  claude-opus-5: 0.7
  claude-sonnet-5: 0.3
```

Every model named must exist in `ANTHROPIC_RATES`, or the estimator refuses
the input with the list of known ids — an unknown model is never priced by
guessing a rate.

## 4. Fallback — when repricing is refused

The rescale needs the profile to carry `component_shares` and `model_mix`. A
published-baseline profile (not measured here) or an older actuals profile may
lack them. When either is missing, or when `build_model` is omitted, the
estimator does **not** rescale. It instead:

- reports the calibration mix as a stated assumption, and
- if a differing `build_model` was declared, states plainly that the estimate
  was **not** repriced and why (no measured shares to scale).

Disclosure is the floor. Repricing is the addition on top of it, taken only
when the data supports it.

## 5. GitHub Copilot side

The GitHub Copilot run prices the build from `dollars_per_1m_input/output` in
the `github_copilot:` block. These are per-model rates already; the change is
to make the model explicit and disclosed rather than to invent a second rate
mechanism.

- Add `build_model` to the `github_copilot:` block. It is a disclosed label
  naming which model the supplied `dollars_per_1m_*` rates describe.
- If a **sourced** GitHub per-model rate table can be established from GitHub's
  published pricing during implementation (verified via the docs tools, with a
  SOURCE url and VERIFIED date exactly like every other table in `rates.py`),
  a known `build_model` populates the rates from it and the report cites them.
- If such a table **cannot** be sourced reliably, GitHub Copilot keeps the
  user-supplied `dollars_per_1m_*` (still per-model, still illustrative), and
  the report discloses the model those rates are asserted to describe and warns
  the reader to check them against GitHub's published rate for that model.

Under no circumstance is a GitHub per-model rate fabricated to fill the table.
Sourced or user-declared, never invented.

## 6. Report

A new disclosure appears in both runs, and the "measured vs judgment" section
gains the model row:

- **Build model** stated up front in the executive summary's key-inputs line,
  next to the development tool and target — it is a key input by the same test
  those already pass.
- A short **"Which model builds it"** subsection: the declared build model (or
  mix), the calibration mix it was measured against, the resulting `ratio`
  when a rescale was applied (or the explicit note that none was), and the two
  §2 limits every time.
- The provenance ledger records `ratio` and the repriced `cost_per_main_turn`
  so both trace like every other figure.

## 7. What changes

| File | Change |
| --- | --- |
| `scripts/rates.py` | `build_model_rates()` helper: component rates and mix blending. Optional sourced GitHub per-model table (§5). |
| `scripts/estimate.py` | Accept `build_model`; apply the §3 rescale or the §4 fallback; record `ratio` and repriced per-turn. Interview gains one question. |
| `scripts/assumptions.py` | Ledger records `ratio`; measured-vs-judgment section gains the model row. |
| `scripts/render_report.py` | Key-inputs line and the "Which model builds it" subsection. |
| `scripts/github_copilot.py` | `build_model` label + disclosure (§5). |
| `scenarios/kestrel-*-manifest.yaml` | Declare `build_model` in each run so the two outputs show the feature. |
| `tests/` | Ratio math (including `ratio == 1` at the calibration mix), mix blending, unknown-model refusal, fallback path, provenance of `ratio`, disclosure text present. |
| `docs/methodology.md` | Document the factor and both honesty limits. |

## 8. Open decisions for review

1. **Kestrel `build_model` values.** To show the feature distinctly, set the
   Claude Code run to a realistic mix (e.g. `{opus-5: 0.7, sonnet-5: 0.3}`)
   that differs from the calibration `{0.55, 0.45}`, so a non-trivial `ratio`
   appears. Acceptable, or keep it at the calibration mix (ratio = 1) and let
   the feature show only as disclosure on the sample?
2. **GitHub per-model table.** Attempt to source a real GitHub per-model rate
   table (§5, adds a sourced table to `rates.py`), or ship the
   declare-and-disclose form now and leave the sourced table to a follow-up?
