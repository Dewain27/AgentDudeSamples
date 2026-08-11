# Agent Samples

A collection of working samples for building with AI agents — each one
self-contained, documented, and ready to install and try.

Every sample is built around a **fictional company**, so nothing here exposes
real data, pricing, or customers. The point is the pattern, which you repoint at
your own content.

---

## Inventory

| Sample | What it is | Install into |
| --- | --- | --- |
| **[RFP Skill](samples/RFP%20Skill/)** | An Agent Skill that turns an incoming RFP into a submission-ready proposal — matching the request to a product offering, answering from a library of pre-approved answers, flagging what it can't answer, and producing Markdown plus a formatted PDF. Ships with 7 test solicitations. | Claude Code · Copilot Studio · Copilot Cowork |

---

## Sample layout

Each sample lives in `samples/<Sample Name>/` and follows the same shape, so you
can find your way around one you've never opened:

```
samples/<Sample Name>/
├── README.md        What it is, how to install it per scenario, how to test it
├── packages/        Prebuilt artifacts — upload these, no build required
├── test-rfps/       (or similar) Sample inputs for trying it out
├── docs/            Deeper platform-specific detail
└── build/           Source of truth and the tooling that generates the sample
```

Start with the sample's own `README.md`. It carries installation instructions for
each supported host, what good output looks like, and the known limits.

---

## Conventions

A few things hold across every sample here:

- **Self-contained by default.** A sample shouldn't need you to stand up a
  service, database, or external index to try it. Where a sample *can* grow into
  one, that's documented as an option rather than a prerequisite.
- **Prebuilt artifacts are committed.** You can install and run a sample without
  installing a toolchain first. Build tooling is there if you want to change it.
- **Everything fictional is labelled.** Generated documents carry a sample notice
  so they can't be mistaken for real solicitations, proposals, or records.
- **Known limits are stated.** Each sample's README ends with what hasn't been
  tested and what would need to change for production use, rather than leaving
  you to discover it.

---

## Adding a sample

Create `samples/<Sample Name>/` following the layout above, then add a row to the
inventory table. A sample is ready to publish when someone can clone the repo,
read one README, install it, and try it without asking a question.
