# Kestrel Financial Group — Advisor Intelligence Platform

**Author:** Dewain Robinson

> **Kestrel Financial Group is fictional.** Every entity, volume, policy, and
> service-level target is invented. Nothing here is regulatory advice.

A regulated wealth-management scenario at programme scale, used to exercise the
estimator well beyond what the minimal examples cover.

## The scenario

[`specification.md`](specification.md) — a full product and technical
specification: a nine-capability Copilot Studio agent on the GitHub Copilot
harness, an advisor console and client portal on Azure, twelve system
integrations, and a financial-services evaluation strategy of 568 test cases
across 6 cycles.

Phases 1 and 2 are in scope. 43 work items, 6 engineers, 5 months.

## Two runs

The same programme, estimated twice with a different developer AI. **Identical
work breakdown, identical target** — only the build platform and its licensing
differ.

| Run | Built with | Built on | Output |
| --- | --- | --- | --- |
| A | Claude Code | Copilot Studio + Azure | [`kestrel-claude-code-estimate.md`](kestrel-claude-code-estimate.md) · [pdf](kestrel-claude-code-estimate.pdf) |
| B | GitHub Copilot | Copilot Studio + Azure | [`kestrel-github-copilot-estimate.md`](kestrel-github-copilot-estimate.md) · [pdf](kestrel-github-copilot-estimate.pdf) |

**Each report is standalone.** Neither references the other. This is not a
comparison, and the reports say so — platform choice is not a cost decision.

## What this scenario forced into the estimator

Running a programme-scale specification through the tool exposed three gaps
that the minimal examples never reached:

| Gap | Fix |
| --- | --- |
| A `github-copilot` build accepted only `interactions: N` — no work breakdown, so two runs could not estimate the same scope | `items:` now sizes **both** build platforms. Turn count is treated as a property of the work; only the price per turn differs, and the report states that assumption |
| An Azure target accepted one opaque `azure_build_usd` — useless for a twelve-service architecture | `azure_components:` itemises the target, each line carrying its own note |
| Seat attribution divided by **one** developer-month, so a 6-person 5-month programme reported a 1901% allowance overrun | `duration_months` added; allowance is now `seats x months` of developer-time. The same programme reports 63% |

Two bugs were found while wiring it up: a falsy-zero guard that silently turned
an invalid `duration_months: 0` into `1`, and a seat line that labelled
rate x duration as a monthly rate — reporting a $150 seat as `$750.00/month`.
Both are now covered by tests.

## Reproducing

```bash
cd "samples/Build Work Estimator"
python build/regenerate_examples.py          # regenerates examples and scenarios
python build/regenerate_examples.py --check  # verifies, writes nothing
```

Both runs are byte-reproducible from committed inputs and are checked in CI.
