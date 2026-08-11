# Deploying the `rfp-response` skill to Microsoft agent surfaces

The skill runs unchanged on **Copilot Studio** (GitHub Copilot harness, GA
August 3, 2026) and on **Microsoft 365 Copilot Cowork**. Both use the
**Agent Skills open standard** — the same `SKILL.md` + YAML front matter format
the skill is already written in. Microsoft's own compatibility table lists Claude
Code as *"Full — same `SKILL.md` format."* So this is packaging, not porting.

## Build

```bash
python tools/build_ms_agent_packages.py
```

Produces two artifacts in `dist/`:

| Artifact | Layout | Use it for |
| --- | --- | --- |
| `rfp-response.zip` | `SKILL.md` at the ZIP root + companions | Copilot Studio **Upload a skill**, and Cowork **Upload skill** |
| `rfp-response-cowork-plugin.zip` | `manifest.json` + icons + `skills/rfp-response/` | Cowork **Upload plugin**, admin deployment, App Store submission |

Build one at a time with `--target skill` or `--target cowork-plugin`; add
`--keep-tree` to inspect the staged folders. The script applies the adaptation
below, validates against the documented packaging limits, and fails loudly rather
than shipping an invalid package.

If you changed the catalog, regenerate the skill's bundled references and the
knowledge base first — both derive from it:

```bash
python tools/build_skill_references.py    # skill's offering index + answer library
python tools/export_knowledge_data.py && node tools/build_knowledge_base.js
```

## Install it

### Copilot Studio

The agent must be created with the **GitHub Copilot harness** — skills aren't
available on the standard or Copilot chat harnesses.

**Build** tab → **Skills** → **Add skill → Upload a skill** → `rfp-response.zip`.
Test from **Preview**; run test sets from **Evaluate**.

### Cowork — as a skill (simplest, just for you)

**Customize** → **Skills** tab → **Add ▾** → **Upload skill** → `rfp-response.zip`.

Cowork validates it and saves it to your OneDrive; it appears under **Your
skills** once syncing finishes. Skill uploads here have their own, looser limits:
10 MB compressed, 50 MB uncompressed, up to 100 files. Ours is 55 KB / 16 files.

### Cowork — as a plugin (shareable, deployable)

**Customize** → **Plugins** tab → **Upload plugin** → `rfp-response-cowork-plugin.zip`,
then pick **Only you** in the Share dialog while testing.

For a personal sideload via CLI instead:

```bash
npm install -g @microsoft/m365agentstoolkit-cli
atk auth login
atk install --file-path "dist/rfp-response-cowork-plugin.zip" --scope Personal
```

To roll it out: **M365 admin center → Manage apps → Upload custom app**, then
choose specific users, groups, or the whole tenant. Tenant-distributed packages
skip App Store validation, so that's the path for internal use. Public
distribution goes through Partner Center.

## Nothing else to set up

The skill is **self-contained**. Offering detail, case studies, certifications,
and pricing all ship inside the package, so there is no knowledge source to
configure, no connector to register, and no service to stand up. Upload the ZIP
and it works.

That is a deliberate choice for a catalog this size — 15 offerings comes to 15
companion files and 129 KB, well inside the 20-file / 10 MB limits — and it buys
two things a knowledge source can't: the agent reads approved commitment language
*verbatim* rather than a retrieved paraphrase, and there is no "knowledge base
unreachable" failure mode.

If the content later outgrows the package (hundreds of past proposals, security
questionnaires, a live rate card), the Word and PDF documents under
`knowledge-base/` are generated from the same catalog and can be attached as a
knowledge source instead — Copilot Studio and Cowork both accept direct file
upload, so even that needs no external service. That's a build choice, not a
redesign.

## What differs from the in-repo skill, and why

The authored skill lives at `.claude/skills/rfp-response/`. One thing changes on
the way into a package:

**PDF rendering is environment-aware.** The bundled `md_to_pdf.py` drives
headless Chromium, which neither sandbox has and neither can install. Both hosts
create PDF and Office files natively, so the packaged instructions use that and
keep the script as the shell-environment option. One `SKILL.md` serves all three
environments.

Everything else ships verbatim.

## Limits enforced by the build

| Limit | Value | This package |
| --- | --- | ---: |
| Companion files (excluding `SKILL.md`) | 20 | 15 |
| Size per companion file | 5 MB | 11 KB |
| Total companion size | 10 MB | 129 KB |
| `name` — kebab-case, must match folder | ≤ 64 chars | `rfp-response` |
| `description` | ≤ 1024 chars | 751 |
| `SKILL.md` body | < 5,000 tokens | ~1,720 words |
| Hidden files, `..`, backslashes, reserved names | not allowed | none |
| Skills per plugin package (ASKILL-M002) | 20 | 1 |

The plugin build additionally checks the package-level rules Microsoft codes as
ASKILL-P001–P008 (manifest folder exists, contains `SKILL.md`, valid front
matter, `name` present, `description` present, `name` matches folder, kebab-case,
no duplicate folders).

> The v1.28 manifest schema sets `additionalProperties: false` at the root, so
> any field it doesn't define fails the upload. The generated manifest includes
> only documented fields.

## Things worth knowing before you roll it out

- **Information Barriers block this.** In tenants with Microsoft Purview
  Information Barriers enabled, embedded knowledge file uploads are blocked at
  the tenant level, which prevents plugins and skills from being uploaded or
  published. Check this first — it's the most likely hard blocker.
- **The icons are placeholders.** Generated by the build so the package
  validates and sideloads. Replace `color.png` (192×192) and `outline.png`
  (32×32) before any store submission.
- **Aventra is fictional.** The manifest's developer name, URLs, and the skill's
  content all describe a made-up vendor. Repoint them before this represents a
  real company.
- **Plugin skills can't override built-in skills** of the same name, and
  Microsoft advises against duplicating built-ins — worth checking Cowork's
  built-in skill list if triggering behaves oddly.
- **Billing differs.** Copilot Studio's GitHub Copilot harness bills usage-based
  **Copilot Credits**, and that covers building, testing, and evaluating — not
  just production. Proposal drafting is long and file-producing, so watch cost in
  the Power Platform admin center.

## After uploading — worth verifying

Developed and tested in a shell environment, so re-check these in the host:

- **Triggering.** Paste an RFP and ask for a proposal without naming the skill.
  The orchestrator decides from the `description` alone; if it doesn't fire,
  that's the field to tune.
- **PDF output.** Confirm the host produces the PDF natively and that the cover
  block, numbered sections, and tables survive.
- **Reference loading.** Confirm the agent opens
  `references/offerings-<product-line>.md` and `references/past-performance.md`
  rather than answering from the index alone. If section 8 comes back generic
  with no named engagement, it skipped the past-performance file.
- **Gap flagging.** Give it an RFP demanding a certification Aventra doesn't hold
  (`evals/files/hitrust-analytics-rfp.md` is built for exactly this) and confirm
  it flags rather than fabricates. This is the behaviour most worth protecting.

## Sources

- [Skills overview for agents (Copilot Studio)](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/skills-overview)
- [Add an existing skill to an agent](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/skills-add-existing)
- [Choose a harness](https://learn.microsoft.com/microsoft-copilot-studio/harnesses-overview)
- [Build plugins for Copilot Cowork](https://learn.microsoft.com/microsoft-365/copilot/cowork/cowork-plugin-development)
- [Customize Copilot Cowork — upload a skill / plugin](https://learn.microsoft.com/microsoft-365/copilot/cowork/cowork-customize)
- [Manage plugins for Copilot Cowork](https://learn.microsoft.com/microsoft-365/copilot/cowork/cowork-manage-plugins)
- [Billing for agents powered by the GitHub Copilot harness](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/billing-credit-overview)
