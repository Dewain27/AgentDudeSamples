# RFP Skill

An **Agent Skill** that turns an incoming RFP into a submission-ready proposal —
matching the request to the right product offering, answering requirements from a
library of pre-approved answers, flagging what it can't answer, and producing
Markdown plus a formatted PDF.

It writes as **Aventra Software Group**, a fictional enterprise software vendor
with 15 offerings across 6 product lines. Everything about the company is
invented; the point is the *pattern*, which you repoint at a real catalog.

**The skill is self-contained.** No knowledge source, no connector, no database,
no service to stand up. One ZIP, upload it, done.

---

## Quick start

1. Install it — pick your scenario from [Installation](#installation) below.
2. Give the agent a solicitation from [`test-rfps/`](test-rfps/):

   > Draft our proposal for this — the RFP is attached.

3. It should trigger without being named, and return a proposal plus a PDF.

Start with `test-rfps/01-westbrook-permitting-portal.md` for a clean run, or
`test-rfps/06-open-horizons-nothing-fits.md` to watch it correctly *decline* to
bid. See [`test-rfps/README.md`](test-rfps/README.md) for what each one exercises.

---

## What's in this folder

| Path | What it is |
| --- | --- |
| `skill/rfp-response/` | The skill source — this is the actual deliverable |
| `packages/` | Prebuilt ZIPs, ready to upload. No build required. |
| `test-rfps/` | Seven sample solicitations for testing, with a guide to each |
| `docs/microsoft-deployment.md` | Deeper detail on Copilot Studio and Cowork, limits, and caveats |
| `build/` | How it's generated: the catalog source of truth and the packaging tools |

---

## Installation

### Scenario 1 — Claude Code (or any Agent Skills client)

Copy the skill folder into your project's skills directory:

```bash
mkdir -p .claude/skills
cp -r "samples/RFP Skill/skill/rfp-response" .claude/skills/
```

Or install it for every project: `cp -r skill/rfp-response ~/.claude/skills/`.

It loads on the next session. The same folder works in VS Code / GitHub Copilot,
Cursor, Gemini CLI, and other tools that read the Agent Skills standard.

**PDF rendering** here uses the bundled `scripts/md_to_pdf.py`, which needs two
packages:

```bash
pip install markdown playwright
```

Without them the script exits with a clear message and the Markdown is still a
complete deliverable.

### Scenario 2 — Microsoft Copilot Studio

Requires an agent built on the **GitHub Copilot harness**. Skills aren't
available on the standard or Copilot chat harnesses.

1. Open your agent → **Build** tab.
2. In the components panel, select **Skills**.
3. **Add skill → Upload a skill**.
4. Upload `packages/rfp-response.zip`.

Test from the **Preview** tab. The harness creates PDFs natively, so nothing
needs installing.

> Copilot Studio bills usage-based **Copilot Credits**, and that covers building,
> testing, and evaluating — not just production traffic.

### Scenario 3 — Microsoft 365 Copilot Cowork, as a skill

The simplest route, and personal to you:

1. **Customize** → **Skills** tab.
2. **Add ▾** → **Upload skill**.
3. Upload `packages/rfp-response.zip`.

Cowork validates it and saves it to your OneDrive; it appears under **Your
skills** once syncing finishes.

### Scenario 4 — Microsoft 365 Copilot Cowork, as a plugin

Use this when you want to share it with colleagues or have IT deploy it.

1. **Customize** → **Plugins** tab → **Upload plugin**.
2. Upload `packages/rfp-response-cowork-plugin.zip`.
3. Choose **Only you** in the Share dialog while testing.

To roll out more widely: **M365 admin center → Manage apps → Upload custom app**,
then assign to users, groups, or the tenant. Tenant-distributed packages skip App
Store validation, so that's the internal path.

Sideloading via CLI instead:

```bash
npm install -g @microsoft/m365agentstoolkit-cli
atk auth login
atk install --file-path "packages/rfp-response-cowork-plugin.zip" --scope Personal
```

> **Check this first:** in tenants with Microsoft Purview **Information
> Barriers** enabled, skill and plugin upload is blocked at the tenant level.
> That's the most likely hard blocker on either Microsoft surface.

---

## How it works

Two ideas drive the whole skill, and both come from how proposals are actually
judged:

1. **Evaluators score against their own published criteria, in their own
   vocabulary.** They have a scoresheet and a stack of proposals. Anything they
   have to hunt for loses points — so the skill mirrors the buyer's structure and
   words, and abandons its own default layout whenever the buyer mandates one.
2. **Every sentence is a commitment.** A proposal becomes a contract attachment.
   Claiming a certification the company doesn't hold is worse than admitting a
   gap, so the skill flags what it can't answer instead of filling it in.

The workflow is: read the solicitation → match it to an offering → answer each
requirement from the pre-approved library → write in the buyer's structure →
render the PDF → report back with every gap and assumption.

### What's bundled

| File | Holds |
| --- | --- |
| `references/catalog.md` | All 15 offerings, with guidance for telling close matches apart |
| `references/offerings-<line>.md` | Full capabilities, integrations, differentiators, success measures |
| `references/answer-library.md` | Pre-approved answers to recurring questions — security, hosting, SSO, accessibility, SLAs |
| `references/past-performance.md` | Case studies by industry, reference policy, and the **exhaustive** certification list |
| `references/pricing.md` | Ranges, fee build-up, inclusions and exclusions, under-budget guidance |
| `assets/example-*.md` | Two complete worked request→response pairs |
| `scripts/md_to_pdf.py` | Markdown → styled PDF, for environments with a shell |

That's 15 companion files and 129 KB, against packaging limits of 20 files and
10 MB.

### The examples matter

Two worked pairs ship with the skill, covering the two shapes a solicitation
takes: one with no mandated format answered in the default structure, and one
where the buyer mandates Part A–H with a compliance table and a budget cap that
full scope doesn't fit. The skill is told to read whichever matches before
drafting.

Both are **output the skill actually produced** during testing, not hand-written
ideals.

---

## Testing it

Beyond handing it the files in `test-rfps/`, the skill carries its own eval
harness in `skill/rfp-response/evals/`:

```bash
# after collecting run outputs into build/eval-runs/iteration-N/
python skill/rfp-response/evals/grade.py --iteration 3
```

`evals.json` holds the prompts and the assertions. The most recent run scored
**36/36** with the skill in complete isolation — nothing available but the skill
itself and the solicitation.

The behaviours most worth protecting, in order:

1. **It flags rather than fabricates.** Give it `03-northfield-...` and confirm
   it says Aventra does not hold HITRUST rather than implying SOC 2 is equivalent.
2. **It follows the buyer's structure.** `04-cedar-valley-...` should come back
   in Part A–H, not the default 12 sections.
3. **It declines when nothing fits.** `06-open-horizons-...` should not produce a
   confident proposal.

---

## Changing it

The catalog at `build/rfp-automation-kit/rfpkit/catalog_data.py` is the single
source of truth — offerings, pricing, and the answer library all live there.
After editing it:

```bash
python build/tools/build_skill_references.py     # regenerate bundled references
python build/tools/build_ms_agent_packages.py    # rebuild both ZIPs
```

The packaging build validates against the documented limits (file count, sizes,
naming, path rules) and fails loudly rather than shipping something that won't
upload.

To repoint the skill at a real vendor, replace the catalog contents and the
`VENDOR` block, then regenerate. The method in `SKILL.md` doesn't change.

---

## Known limits

- **Not yet tested inside Copilot Studio or Cowork.** All testing ran in a shell
  environment. The instructions are faithful, but triggering behaviour and native
  PDF generation on those surfaces are unverified — check them after upload.
- **The plugin icons are placeholders**, generated so the package validates.
  Replace before any store submission.
- **Aventra is fictional**, including the developer name and URLs in the plugin
  manifest. Repoint them before this represents a real company.
- **Bundling doesn't scale forever.** The catalog fits in 15 companion files
  today. At hundreds of past proposals or a live rate card you'd exceed the
  20-file / 10 MB packaging limits and want an external knowledge source
  instead — both Copilot Studio and Cowork accept direct file upload, so even
  that needs no service standing up.
