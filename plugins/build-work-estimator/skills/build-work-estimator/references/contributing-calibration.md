# Contributing calibration data

**Author:** Dewain Robinson

The estimator gets better when people record what builds actually cost and share
the result. This explains exactly what a contribution contains, what it can
never contain, and how it is reviewed.

---

## Read this before contributing

**A contribution opens a pull request to a public repository. Once merged it
cannot be recalled from that repository's git history.** Contribution is
entirely optional and nothing is ever sent automatically.

## What is sent

The complete payload. There are no other fields:

```yaml
schema: 1
contributed: 2026-09            # month precision only
size: medium                    # bucket label
files: 9
unknowns: 2
brownfield: true
estimated_turns: 431
actual_turns: 604
ratio: 1.40
model_tier: opus                # family only: opus | sonnet | haiku | mixed
cache_hit_rate_band: "95-100"   # banded, not exact
harness: none                   # none | standard | github-copilot
```

## What is never sent

| Never included | Why |
| --- | --- |
| Project or client names | Identifies the work and the customer |
| File paths | Leak project structure and often client names |
| Session ids | Correlatable back to a specific machine and person |
| Prompt or response content | Obvious |
| **Dollar amounts** | Can expose contracted or negotiated rates |
| Exact dates | Narrow the field of who a record could belong to |
| Org identifiers, usernames | Identifying |
| **Your name** | The record is anonymous *by design* — unlike every other artifact in this sample, a contribution carries no author attribution |

Turn **ratios** carry all the useful signal without any of that. A ratio of
1.40 is exactly as useful for calibration as "$1,234 estimated, $1,729 actual",
and reveals nothing.

## How the guarantee is enforced

**Allowlist, not redaction.** The payload is built by copying named fields into
a fresh object. Nothing is included unless it appears in `contribute.ALLOWLIST`.

This matters more than it sounds. Redaction — building the payload from the
source object and then stripping sensitive fields — **fails open**: a field
added to the ledger later leaks until someone remembers to strip it. An
allowlist **fails closed**: a new field is invisible unless deliberately added.

`tests/test_contribute.py` proves it. It seeds a ledger entry with project
names, absolute paths, dollar amounts, session ids, an exact date, and an
unanticipated extra field, then asserts none of them survive into the payload.
That test was written and passing **before** the submission path was wired to
`gh`.

## Consent

1. The **complete** payload is printed, rendered, with nothing elided.
2. You are told plainly that this opens a public pull request.
3. You must type the word `contribute`. **`y` and `yes` are deliberately not
   accepted**, there is no `--yes` flag, and consent is never remembered — every
   contribution is confirmed separately.

If `gh` is unavailable or unauthenticated, the record is written to a local file
and the manual steps are printed. Nothing is blocked and nothing is sent.

## How records are used

`calibration/aggregate.py` rolls `community/` into `baseline.json`, publishing a
median ratio, interquartile range, and `n` per bucket.

**Buckets with fewer than 5 records are published but flagged low-confidence,
and the plugin will not apply a community correction below that threshold.**

A community baseline is **never** better than a user's own measured profile. It
exists to give installs with no local history something better than a published
population average. It is self-selected — it reflects whoever chose to
contribute, not a representative sample of anyone's work — and the baseline file
says so.

## Review

One file per record, human-readable, small. Every PR is reviewed by hand. A
malformed record is skipped by the aggregator rather than breaking the build, so
a bad contribution degrades the dataset slightly instead of breaking the tool.

## Submitting manually

You do not need the script:

1. Fork [Dewain27/AgentDudeSamples](https://github.com/Dewain27/AgentDudeSamples)
2. Add one `.yaml` file matching the shape above under
   `samples/Build Work Estimator/calibration/community/`
3. Open a pull request

Include only the fields listed. Anything else will be asked to be removed before
merge.
