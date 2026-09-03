# Platforms and licensing

**Author:** Dewain Robinson

Two questions decide what a build estimate says. Getting either wrong produces
a number that looks reasonable and is wrong.

1. **What are you building WITH?** — the build platform, decides the build-side meter.
2. **What are you building ON?** — the target platform, decides the target-side meter.
3. **How is that licensed?** — decides what the numbers *mean*.

They are additive, not alternatives: the same project spends on both meters at
the same time.

---

## 1. Two platforms, two meters

**Copilot Studio is not a build platform.** An AI-assisted build happens in a
coding agent — Claude Code or GitHub Copilot — authoring the agent definition.
Copilot Studio is where the result is deployed, previewed, evaluated, and
validated by a human. Microsoft's own VS Code extension documentation says so
directly, naming *"GitHub Copilot, Claude Code, or your favorite agent"* as the
harnesses used to create and update Copilot Studio agent components, under a
heading titled **Agent-driven development**.

| | Values | Meter |
| --- | --- | --- |
| `build_platform` | `claude-code` · `github-copilot` | Tokens → USD, or GitHub AI Credits |
| `target_platform` | `copilot-studio` · `azure` · `both` · `ai-recommend` | Copilot Credits, or Azure consumption |

Two earlier versions of this estimator got this wrong. The first keyed off
`microsoft: true` — meaning *the target is Microsoft* — and priced those builds
in Copilot Credits. The second treated `copilot-studio` as a build stack, which
models a workflow nobody performs. Both keys were removed rather than kept
working, and both are rejected with guidance.

### The target harness decides whether any of it bills

Required whenever the target is Copilot Studio:

| Harness | Build, preview, test, evaluate |
| --- | --- |
| `standard` | **Not billed.** Billing starts after publish; embedded test chat does not count |
| `github-copilot` | **Billed from the moment building starts** |

A standard-harness target legitimately returns near-zero target-side cost. The
report says so plainly and shows what the same work would have cost on the other
harness, so the difference is visible rather than hidden. Billable side-effects
— agent flow runs, content processing — still bill on either harness.

### The evaluation loop is the cost driver

```
  build platform            target platform
  ---------------           ----------------
  author definition   -->   deploy
                            preview / interactive test   <- human, in the UI
                            run evaluations
  remediate           <--   evaluations fail
  (repeat)
```

Microsoft's guidance is explicit that evaluation is a continuous cycle, targeting
an 80–90% pass rate with near 100% on core tests, and that a test set should be
run multiple times for response variability. So an estimate must plan for
cycles, not a single pass: each cycle after the first adds remediation back onto
the build platform, and re-runs the evaluations on the target.

**Evaluations are capped at 20 per agent node per day.** A large test set
therefore sets a minimum elapsed time no amount of budget shortens — the report
states that separately from cost.

**Human validation is a dependency, not a cost line.** Someone must work in the
Copilot Studio interface between cycles to confirm behaviour and adjust
configuration. Planned hours are collected to size the interactive test volume;
they are never priced as labour, consistent with this tool metering agent
consumption rather than people.

### Microsoft products do not bill in tokens

A Copilot Studio report is denominated in **Copilot Credits** throughout — every
heading, total, unit, and row label. Tokens appear only in the *Basis* column,
because Microsoft's own published rate is literally "10 Copilot Credits per 1K
tokens" and removing that would make the credit figure unverifiable. A test
enforces this: no heading and no row label may be denominated in tokens.

### GitHub AI Credits are not Copilot Credits

This one is a trap. **Both are $0.01 per credit.** They are different meters, on
different products, with separate allowances:

| | Copilot Studio | GitHub Copilot |
| --- | --- | --- |
| Unit | Copilot Credit | GitHub AI Credit |
| Rate | $0.01 | $0.01 |
| Allowance | Capacity packs, 25,000/month | Pooled at billing-entity level |
| Meter | Power Platform / M365 | GitHub billing |

Reporting one as the other would produce a plausible number drawn against the
wrong budget. They never share a code path here.

GitHub also runs **two billing models in parallel**:

- **AI Credits** (usage-based) — interactions consume input, output, and cached
  tokens; GitHub prices those at the model's published rates and converts to
  credits. Business and Enterprise pool credits at the billing-entity level.
- **Legacy premium requests** — one request per interaction times a model
  multiplier, drawn from a monthly plan allowance. Eligible Pro and Pro+
  subscribers on existing annual plans stay on this until their plan expires.

**Code completions and next edit suggestions consume no credits** and are
unlimited on paid plans, so however heavily they are used they contribute
nothing to a build estimate.

Per-model rates and multipliers are **not hardcoded**. GitHub publishes and
changes them; a stale table here would misprice every estimate. The user
supplies the rate for the model they actually use.

---

## 2. Licensing decides what the number means

| Licensing | The real question |
| --- | --- |
| **Consumption** — Claude API/Console, Bedrock, Vertex, Foundry, Copilot Studio pay-as-you-go, GitHub usage-based | **What will this cost?** |
| **Seat / allowance** — Claude Pro, Max, Team, Enterprise; GitHub Business/Enterprise; prepaid capacity packs | **Will this fit, and what share of the seat does it burn?** |

### A seat is not free

From the Claude Code documentation: *"Usage inside the seat allowance isn't
metered in dollars."* Marginal spend inside an allowance is zero.

Reporting `$0` for a seat-based build would be the same class of error this tool
exists to prevent. The seat was bought with real money. A build consuming 40% of
a month's allowance carries 40% of that month's seat cost:

```
allowance_share    = build_notional_cost / typical_monthly_cost
attributable_cost  = seat_monthly_cost × seats × allowance_share
```

`typical_monthly_cost` comes from measured history — the calibration profile's
total spend over its date range, extrapolated to 30 days. With fewer than 14
days of history the denominator would be guesswork, so the tool **declines to
compute a share** rather than inventing one.

Seat prices are **not hardcoded**. They change, they vary by contract and
region, and a stale table would silently misattribute every estimate. The user
supplies their actual seat cost; `seat_monthly_cost` is required for seat
licensing and there is no default.

### Overrun is the failure that actually stops work

A build fitting inside an allowance in isolation can still overrun once other
work is counted. `other_workload_share` is required for seat licensing — it is
the fraction of the allowance period already committed elsewhere:

```
total_committed = allowance_share + other_workload_share
overruns        = total_committed > 1.0
```

When it overruns, the report states by how much and what the overage would cost
at the same rate, then lists the options: spread the build across periods, move
part of it to consumption billing, add seats, or reduce the other work.

### Short windows stall before monthly totals do

Claude seat allowances refill on **5-hour rolling** and **weekly** windows, not
only monthly. A build comfortably inside a month can still exhaust a short
window and stall repeatedly.

Set `concentrated: true` when the build is compressed into a short delivery
window; the report then warns that monthly headroom will not protect it.

There is a second, subtler effect: **cache lifetime is one hour on a
subscription and five minutes on an API key.** Cache misses reprocess the full
context, and cache writes were roughly a quarter of measured spend — so the same
build can cost materially more on consumption billing purely from cache
behaviour.

---

## What this is not

**This is not a stack comparison tool.** It reports one stack, in that stack's
own currency, and every report says so.

Technology stack decisions are not made on cost alone. Capability, existing
team skills, governance, integration surface, and support all weigh more than a
build-time figure. A tool that made stack choice look like an arithmetic
comparison would be encouraging a bad decision process — so the shipped examples
each show a single stack, and there is no side-by-side mode in them.
