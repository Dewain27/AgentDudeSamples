# Scenarios

**Author:** Dewain Robinson

Full worked scenarios, as opposed to the minimal illustrations in
[`../examples/`](../examples/). A scenario carries a real specification and
exercises the estimator at programme scale.

| Scenario | Organization | What it exercises |
| --- | --- | --- |
| [`kestrel-financial/`](kestrel-financial/) | Kestrel Financial Group (fictional) | A regulated wealth-management agent plus web application, targeting Copilot Studio and Azure, estimated twice — once built with Claude Code, once with GitHub Copilot |

Every scenario is generated from committed inputs and checked by
[`../build/regenerate_examples.py --check`](../build/regenerate_examples.py) in
CI, exactly like the examples. Stale scenario output fails the build.

## These are separate runs, not a comparison

Where a scenario is estimated more than once, each run produces a **standalone
document**. Neither references the other, and there is no side-by-side mode.

Platform choice is not a cost decision. Capability, existing team skills,
governance, integration surface, and support all weigh more than a build-time
figure, and presenting two estimates side by side would invite exactly the
reasoning this tool is built to avoid.
