# RFP Automation Kit

A self-contained, dependency-free project that models a fictional software
vendor's **full product catalog** and produces a **sample RFP request and RFP
response for every product offering** — plus a starter **automation layer** that
assembles responses from a reusable answer library.

Every sample ships as both **Markdown and a formatted PDF**.

It is built to be the seed for a real RFP-response automation: the catalog and
answer library are the knowledge base, and `rfpkit/automation.py` is a working
(if simple) matcher you can later swap for embeddings or an LLM without changing
the interface.

> Everything here — the vendor **Aventra Software Group**, every buyer, price,
> name, and date — is invented for demonstration. Nothing represents a real
> company, price, or agreement.

---

## The catalog

**6 product lines · 15 offerings.** Each offering ships with a sample RFP
request, a sample RFP response, and a machine-readable `offering.json`.

| Product line | Offerings |
| --- | --- |
| **Custom Application Development** | Custom Web Application Platform · Mobile Application Suite · Legacy Application Modernization |
| **Data & Analytics** | Enterprise Data Warehouse · Business Intelligence & Dashboards · Data Integration & Pipelines |
| **Cloud & Platform Engineering** | Cloud Migration · DevOps & Platform Automation |
| **Integration & APIs** | API Development & Management · Enterprise Systems Integration |
| **Industry Solutions** | Patient Engagement Portal · Constituent Services & Permitting Portal · Loan Origination & Member Servicing Platform |
| **Managed Services & Security** | Application Managed Services · Security & Compliance Services |

Run `python generate.py list` for the full listing with target industries.

---

## Quick start

Requires **Python 3.9+**. No packages to install.

```bash
cd rfp-automation-kit

# See the catalog
python generate.py list

# Generate a request + response + offering.json for EVERY offering
python generate.py build

# Generate samples for just one offering
python generate.py build --offering patient-portal

# Render every sample as a formatted PDF (see "PDF output" below)
python generate.py pdf

# Export the whole catalog as machine-readable JSON (for your automation)
python generate.py export            # -> data/catalog.json
```

Samples land under `samples/<product-line>/<offering>/`:

```
samples/industry-solutions/patient-portal/
├── rfp-request.md      # what a buyer sends
├── rfp-request.pdf     #   ... as a formatted PDF
├── rfp-response.md     # Aventra's matching proposal
├── rfp-response.pdf    #   ... as a formatted PDF
└── offering.json       # structured metadata for this offering
```

Requests and responses are **deterministic** — the same offering always renders
the same buyer, RFP number, dates, and pricing — so committed samples stay
stable and diffs are meaningful.

---

## PDF output

All 30 sample documents (15 offerings × request + response) are committed as
PDFs alongside the Markdown, so you can hand them to someone without running
anything.

Each PDF is laid out as a real business document:

- A **cover page** with a document-type badge, title, the issuing/submitting
  organization, and the key metadata table (RFP number, dates, budget or fee).
- A **sample-document notice** so the fictional content is never mistaken for
  a real solicitation.
- Numbered body sections with styled tables, running **page numbers**, and a
  footer carrying the RFP number and offering name.
- Colour-coded by document type — **slate blue** for buyer requests, **teal**
  for Aventra's responses.

Requests run 4 pages; responses run 6.

**Regenerating PDFs** needs two optional packages (the rest of the kit stays
dependency-free):

```bash
pip install -r requirements-pdf.txt
python generate.py pdf                        # all offerings
python generate.py pdf --offering data-warehouse
```

Rendering goes Markdown → styled HTML → headless Chromium, so the PDFs stay in
lockstep with the Markdown; the `pdf` command re-renders from the catalog rather
than reading stale files. If the extras are missing, the command explains how to
install them and exits without touching anything.

---

## The automation layer

This is what makes the kit a starting point for automating responses, not just a
pile of samples.

**The knowledge base** is two things:
1. **`RESPONSE_LIBRARY`** in `rfpkit/catalog_data.py` — reusable answer blocks
   for the questions that recur in almost every RFP (security, pricing,
   accessibility, SSO, support SLAs, hosting, integration, …), each tagged with
   matching keywords.
2. **Per-offering `snippets`** — offering-specific overrides (understanding,
   proposed solution) that win over the generic library block.

**The matcher** (`rfpkit/automation.py`) scores an incoming RFP question against
the library keywords and returns the best answer — or flags it as unmatched so a
human can fill the gap.

```bash
# Auto-answer a single RFP question
python generate.py answer "How is data encrypted and how do you test security?"

# Assemble an automated draft from an offering's requirements,
# and report how much the library could auto-answer
python generate.py draft --offering data-warehouse
```

```
Coverage: 4/6 auto-answered (66.7%)

• Enforce role-based access to sensitive data
    [sso] We integrate with your existing identity provider using SAML 2.0 ...
• Consolidate data from many disconnected systems
    [UNMATCHED — needs a human answer]
...
```

The `answer` / `draft` / `coverage` functions are the interface to build on. To
grow coverage, add answer blocks (or keywords) to `RESPONSE_LIBRARY`. To upgrade
matching, replace the keyword scorer in `automation.py` with embeddings or an
LLM call — the callers stay the same.

---

## Project structure

```
rfp-automation-kit/
├── generate.py                 # CLI: list / build / pdf / export / answer / draft
├── requirements-pdf.txt        # optional extras, only for `generate.py pdf`
├── rfpkit/
│   ├── catalog_data.py         # SOURCE OF TRUTH: vendor, lines, offerings, response library
│   ├── models.py               # catalog access + deterministic buyer/date derivation
│   ├── automation.py           # question -> answer matcher (the automation seed)
│   ├── render_request.py       # offering -> sample RFP request (Markdown)
│   ├── render_response.py      # offering -> sample RFP response (Markdown)
│   └── render_pdf.py           # Markdown -> styled HTML -> PDF
├── data/
│   └── catalog.json            # machine-readable catalog (via `generate.py export`)
└── samples/                    # generated request+response (md + pdf) + json per offering
```

---

## Extending it

- **Add an offering:** append a dict to `OFFERINGS` in `rfpkit/catalog_data.py`
  (copy an existing one as a template), then `python generate.py build`.
- **Add a product line:** add an entry to `PRODUCT_LINES` and point offerings at
  it with their `line` key.
- **Improve automation coverage:** add blocks/keywords to `RESPONSE_LIBRARY`, or
  swap the matcher in `automation.py`.
- **Feed a real system:** consume `data/catalog.json` — it contains the vendor,
  product lines, every offering, and the full response library.

All content is fictional and for demonstration only.
