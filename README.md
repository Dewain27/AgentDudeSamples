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
| **[RFP Skill](samples/RFP%20Skill/)** | An Agent Skill that turns an incoming RFP into a submission-ready proposal — matching the request to a product offering, answering from a library of pre-approved answers, flagging what it can't answer, and producing Markdown plus a formatted PDF. Ships with 7 test solicitations. | GitHub Copilot CLI · Claude Code · Copilot Studio · Copilot Cowork |
| **[Build Work Estimator](samples/Build%20Work%20Estimator/)** | An Agent Skill that estimates the work of **building** something with an AI coding agent — turns, tokens, and cost — calibrated from your own session history rather than assumed constants. Requires a contingency reserve and checks whether it actually covers observed variance, translates Microsoft work into build-time Copilot Credits, and learns from recorded actuals. Estimates the build, never the run. | GitHub Copilot CLI · Claude Code · Copilot Cowork · Claude Cowork · Copilot Studio |

---

## Installing from GitHub Copilot

This repository is a **GitHub Copilot plugin marketplace**. Register it once, then
install any sample that ships a plugin:

```bash
copilot plugin marketplace add Dewain27/AgentDudeSamples
copilot plugin install rfp-response@agentdude-samples
```

The same commands work as `/plugin ...` inside an interactive Copilot session, and
VS Code lists the marketplace's plugins under `@agentPlugins` in the Extensions
search view.

`.github/plugin/marketplace.json` is the manifest Copilot reads. Installable
plugins live under [`plugins/`](plugins/) — one space-free directory per plugin,
because marketplaces reference them by repo-relative path.

---

## Sample layout

Each sample lives in `samples/<Sample Name>/` and follows the same shape, so you
can find your way around one you've never opened:

```
.github/plugin/
└── marketplace.json     Registers this repo as a Copilot plugin marketplace

plugins/
└── <plugin-name>/       Installable Copilot plugin, generated from a sample

samples/<Sample Name>/
├── README.md            What it is, how to install it per scenario, how to test it
├── packages/            Prebuilt artifacts — upload these, no build required
├── test-rfps/           (or similar) Sample inputs for trying it out
├── docs/                Deeper platform-specific detail
└── build/               Source of truth and the tooling that generates the sample
```

A sample owns its content; `plugins/` and `.github/plugin/marketplace.json` are
repo-level because that is where Copilot expects to find them.

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
inventory table. If it ships an installable plugin, generate it into `plugins/`
and add an entry to `.github/plugin/marketplace.json`.

A sample is ready to publish when someone can clone the repo, read one README,
install it, and try it without asking a question.
