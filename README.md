# RFP Sample Generator

A small, dependency-free Python tool that generates realistic **sample RFP
requests** and **matching RFP responses** for a fictional enterprise software
vendor, **Aventra Software Group**.

Use it to produce demo content, populate a sales-enablement library, test a
document pipeline, train an AI model, or rehearse a proposal review — without
touching real customer data.

> Every name, number, logo, and client in the output is invented. Nothing here
> represents a real company, price, or contract.

---

## What it produces

- **RFP requests** — the document a client *organization* sends out asking
  vendors to bid (background, scope, functional/technical/security
  requirements, timeline, budget range, evaluation criteria, submission
  instructions).
- **RFP responses** — Aventra's *reply* to that request (cover letter,
  executive summary, understanding of needs, proposed solution, technical
  approach, project plan, team, pricing, past performance).
- **Matched pairs** — a request and the response written *to that exact
  request*, so the two documents line up.

Output is clean Markdown, easy to convert to PDF/DOCX or paste anywhere.

---

## Quick start

Requires **Python 3.9+**. No packages to install.

```bash
# Generate a matched request + response pair into ./output
python generate.py pair

# Just a request, printed to the terminal
python generate.py request --stdout

# Just a response
python generate.py response

# A batch of 5 matched pairs (great for building a sample library)
python generate.py batch --count 5

# Reproducible output — same seed, same documents
python generate.py pair --seed 42
```

Generated files land in `./output/` by default (override with `--out DIR`).
Filenames encode the scenario, e.g.
`rfp-request_riverside-health_patient-portal_a1b2.md`.

See ready-made examples in [`samples/`](samples/).

---

## Commands

| Command                 | What it does                                                        |
| ----------------------- | ------------------------------------------------------------------ |
| `request`               | Generate one RFP request.                                          |
| `response`              | Generate one RFP response (invents a request scenario to reply to).|
| `pair`                  | Generate one request **and** its matching response.                |
| `batch --count N`       | Generate N matched pairs.                                          |

### Common options

| Option            | Description                                                     |
| ----------------- | --------------------------------------------------------------- |
| `--seed N`        | Seed the RNG for reproducible output.                           |
| `--out DIR`       | Output directory (default `output`).                            |
| `--stdout`        | Print to the terminal instead of writing files.                 |
| `--industry NAME` | Force a client industry (e.g. `healthcare`, `government`).       |
| `--project NAME`  | Force a project type (e.g. `patient-portal`, `erp`).            |
| `--list`          | List available industries and project types, then exit.         |

Run `python generate.py --help` for the full list.

---

## How it works

A single **scenario** (client org + project + requirements + budget + dates) is
generated once, then rendered two ways — as the request and as the response —
so a matched pair is always internally consistent. Randomized data pools
(`rfpgen/data.py`) give variety; templates (`rfpgen/templates.py`) control tone
and structure.

```
rfp-generator/
├── generate.py            # CLI entry point
├── rfpgen/
│   ├── company.py         # The fictional vendor: Aventra Software Group
│   ├── data.py            # Randomized pools: industries, projects, requirements
│   ├── scenario.py        # Builds one coherent RFP scenario
│   ├── render_request.py  # Scenario -> RFP request (Markdown)
│   ├── render_response.py # Scenario -> RFP response (Markdown)
│   └── templates.py       # Shared Markdown building blocks
├── samples/               # Pre-generated example documents
└── README.md
```

To customize, edit the data pools in `rfpgen/data.py` (add industries,
requirements, project types) or the vendor profile in `rfpgen/company.py`.

---

## Notes

- Everything is fictional and for demonstration only.
- Budget figures and timelines are plausible-but-invented ranges, not quotes.
- No external services are called; generation is fully offline.
