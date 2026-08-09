# Deploying the `rfp-response` skill to Copilot Studio

The skill runs in Microsoft Copilot Studio on the **GitHub Copilot harness**,
which went generally available on **August 3, 2026**. Skills there use the
**Agent Skills open standard** — the same `SKILL.md` format the skill is already
written in — so this is a packaging exercise, not a rewrite.

## Build the package

```bash
python tools/build_copilot_studio_package.py
# -> dist/rfp-response.zip
```

The script regenerates the reference content from the `rfp-automation-kit`
catalog (still the single source of truth), applies the two adaptations below,
validates against the documented packaging limits, and fails loudly rather than
shipping an invalid package. Add `--keep-tree` to inspect the staged folder.

## Upload it

1. Open your agent in Copilot Studio. It must be an agent created with the
   **GitHub Copilot harness** — skills aren't available on the standard or
   Copilot chat harnesses.
2. Go to the **Build** tab.
3. In the components panel, select **Skills**.
4. Choose **Add skill → Upload a skill**.
5. Drop in `dist/rfp-response.zip`. Copilot Studio validates it and adds it.
6. Test it from the **Preview** tab, and use the **Evaluate** tab to run test
   sets against it.

To update later, rebuild the ZIP and use **replace** on the existing skill rather
than adding a second copy — two skills with overlapping descriptions make the
orchestrator's triggering decision worse, not better.

## What differs from the in-repo skill, and why

The authored skill lives at `.claude/skills/rfp-response/`. Two things change on
the way into the package:

**1. Offering references are consolidated.** The authored skill keeps one file
per offering (15 of them) so a shell agent loads only the ~60 lines it needs.
That puts the package at exactly 20 companion files — the documented ceiling,
with zero headroom for ever adding anything. The package consolidates them into
six files, one per product line, bringing it to **11 companion files**. Slightly
more to read per run, room to grow in exchange.

**2. PDF rendering is environment-aware.** The bundled `md_to_pdf.py` drives
headless Chromium, which the Copilot Studio sandbox doesn't have and can't
install. But the harness **creates PDF files natively**, so the packaged
instructions tell the agent to use that, and keep the script as the option for
shell environments. The same `SKILL.md` therefore works in both places.

## Packaging limits enforced by the build

| Limit | Value | This package |
| --- | --- | ---: |
| Companion files (excluding `SKILL.md`) | 20 | 11 |
| Size per companion file | 5 MB | 11 KB |
| Total companion size | 10 MB | 78 KB |
| `name` — kebab-case, matches folder | ≤ 64 chars | `rfp-response` |
| `description` | ≤ 1024 chars | 751 |
| Hidden files, `..`, backslashes, reserved names | not allowed | none |

> A caveat worth knowing: Copilot Studio's own documentation doesn't publish
> per-package numbers. The figures above come from Microsoft's documentation of
> the same Agent Skills standard for Copilot Cowork plugins, so the build treats
> them as the safe ceiling. If Copilot Studio rejects an upload for a limit not
> listed here, that's the thing to check first.

## After uploading — worth verifying

The skill was developed and tested in a shell environment, so these are the
behaviours most worth re-checking inside Copilot Studio:

- **Triggering.** Paste an RFP and ask for a proposal without naming the skill.
  The orchestrator decides from the `description` alone; if it doesn't fire,
  that's the field to tune.
- **PDF output.** Confirm the harness produces the PDF natively and that the
  cover block, numbered sections, and tables survive.
- **Reference loading.** Confirm the agent actually opens
  `references/offerings-<product-line>.md` after picking an offering, rather than
  answering from the index alone — grounding depends on it.
- **Gap flagging.** Give it an RFP demanding a certification Aventra doesn't hold
  (the `evals/files/hitrust-analytics-rfp.md` case is built for exactly this) and
  confirm it flags rather than fabricates. This is the behaviour most worth
  protecting.

## Billing

Agents on the GitHub Copilot harness bill via **Copilot Credits** on a
usage-based model, and that applies to building, testing, and evaluating — not
just production traffic. Proposal drafting is a long, multi-step, file-producing
task, so runs aren't cheap. Worth watching cost in the Power Platform admin
center during evaluation.

## Sources

- [Skills overview for agents](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/skills-overview)
- [Add an existing skill to an agent](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/skills-add-existing)
- [Agents powered by GitHub Copilot Harness overview](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/overview)
- [Choose a harness](https://learn.microsoft.com/microsoft-copilot-studio/harnesses-overview)
- [Build plugins for Copilot Cowork](https://learn.microsoft.com/microsoft-365/copilot/cowork/cowork-plugin-development) — packaging limits and cross-platform compatibility for the Agent Skills standard
- [Billing for agents powered by the GitHub Copilot harness](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/billing-credit-overview)
