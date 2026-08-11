# Catalog and document generator

The content behind the RFP Skill, plus the generators that produce sample RFP
documents from it.

Everything the skill knows about Aventra Software Group — the 15 offerings, the
pre-approved answer library, the case studies, the certifications — lives in one
file:

**`rfpkit/catalog_data.py` is the single source of truth.**

Edit it, then regenerate the skill's bundled references:

```bash
python ../tools/build_skill_references.py    # -> skill/rfp-response/references/
python ../tools/build_ms_agent_packages.py   # -> packages/*.zip
```

To repoint the skill at a real vendor, replace the contents of `catalog_data.py`
and regenerate. Nothing in `SKILL.md` needs to change — the method is separate
from the content, which is the whole point of the split.

## What's in the catalog

| Structure | Holds |
| --- | --- |
| `VENDOR` | Company profile, contact details, the **exhaustive** certification list, technology stack, and past-performance case studies by industry |
| `PRODUCT_LINES` | The 6 lines offerings are grouped under |
| `OFFERINGS` | All 15 offerings: scope, capabilities, integrations, compliance, pricing bands, differentiators, success measures, and approved positioning language |
| `RESPONSE_LIBRARY` | 15 pre-approved answers to the questions that recur in almost every RFP, each tagged with matching keywords |

The certification list being exhaustive matters: the skill treats anything not
named there as something Aventra does not hold, and says so rather than implying
equivalence.

## The CLI

```bash
python generate.py list                    # every product line and offering
python generate.py build                   # sample RFP request + response per offering
python generate.py pdf                     # render those as formatted PDFs
python generate.py export                  # catalog as JSON
python generate.py answer "How is data encrypted?"
python generate.py draft --offering data-warehouse
```

`build` and `pdf` write into `samples/`, which is **generated on demand and not
committed** — it runs to about 3.6 MB, and the two documents the skill actually
uses are already checked in as `skill/rfp-response/assets/example-rfp-*.md`.

PDF rendering needs `pip install -r requirements-pdf.txt` (markdown + playwright).

## The automation matcher

`rfpkit/automation.py` is a small keyword matcher that maps an RFP question to an
answer-library block and reports coverage:

```bash
python generate.py draft --offering patient-portal
# Coverage: 3/6 auto-answered (50.0%)
```

It exists to make the idea concrete — that a response library plus a matcher gets
you part of the way, and the interesting problem is what to do with the questions
it *can't* answer. The skill's answer to that is to flag them rather than guess.
Swap the keyword scorer for embeddings or an LLM call and the callers don't
change.

## Note

Aventra Software Group is fictional, as is every client, figure, and outcome in
the catalog. Generated documents carry a sample notice saying so.
