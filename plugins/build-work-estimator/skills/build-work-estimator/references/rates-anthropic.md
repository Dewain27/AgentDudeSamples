# Anthropic rates

**Author:** Dewain Robinson
**Verified:** 2026-06-24
**Source:** https://docs.claude.com/en/docs/about-claude/pricing

List price, USD per 1M tokens.

| Model | Input | Output |
| --- | ---: | ---: |
| `claude-fable-5` | $10.00 | $50.00 |
| `claude-mythos-5` | $10.00 | $50.00 |
| `claude-opus-4-5` | $5.00 | $25.00 |
| `claude-opus-4-6` | $5.00 | $25.00 |
| `claude-opus-4-7` | $5.00 | $25.00 |
| `claude-opus-4-8` | $5.00 | $25.00 |
| `claude-opus-5` | $5.00 | $25.00 |
| `claude-sonnet-4-5` | $3.00 | $15.00 |
| `claude-sonnet-4-6` | $3.00 | $15.00 |
| `claude-sonnet-5` | $2.00 | $10.00 |
| `claude-haiku-4-5` | $1.00 | $5.00 |

Multipliers applied to the input rate:

| Token kind | Multiplier |
| --- | ---: |
| Cache read | 0.10x |
| Cache write, 5 minute TTL | 1.25x |
| Cache write, 1 hour TTL | 2.00x |

## Published baselines

Used only when no local session history exists. Source: https://code.claude.com/docs/en/costs

| Figure | Value |
| --- | ---: |
| Cost per developer per active day | $13.00 |
| Cost per developer per month | $150 - $250 |
| 90th percentile per active day | $30.00 |

> These are population averages published by Anthropic. They are a fallback, not a
> measurement of any particular user, and an estimate built on them is materially
> less reliable than one built on measured history.

**Rates change without notice.** Re-verify against the source links above; the
estimator warns when a table is more than 90 days past its verification date.
