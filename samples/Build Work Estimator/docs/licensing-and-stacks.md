# Build stacks and licensing

**Author:** Dewain Robinson

Two questions decide what a build estimate says. Getting either wrong produces
a number that looks reasonable and is wrong.

1. **What are you building WITH?** — decides the *currency*.
2. **How is that licensed?** — decides what the number *means*.

---

## 1. The stack decides the currency

The tool you build with determines how the build is metered. **The workload you
build for does not.**

| You build with | You build for | Metered in |
| --- | --- | --- |
| Claude Code | A Copilot Studio agent | **Tokens → USD** |
| Copilot Studio | A Copilot Studio agent | **Copilot Credits** |
| GitHub Copilot | A .NET service | **GitHub AI Credits** |
| Claude Code | A .NET service | **Tokens → USD** |

Using Claude Code to build a Microsoft workload is extremely common, and it
bills in tokens. An earlier version of this estimator keyed off `microsoft: true`
— meaning *the target is Microsoft* — and priced those builds in Copilot Credits.
That was wrong, and the manifest key was removed rather than kept working.

Set `build_stack:` to one of `claude-code`, `copilot-studio`, `github-copilot`.

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
