#!/usr/bin/env python3
"""Environments, and what building four of them actually costs.

Author: Dewain Robinson

A solution is not built once. It is built into dev, then QA, then test, then
production -- and each of those needs its infrastructure provisioned, its
pipelines wired, its configuration and secrets set, its data seeded, and its
agent deployed. An estimate that prices one environment is pricing a demo.

Two costs multiply, and they multiply differently:

  Work        Infrastructure-as-code, pipeline definitions and configuration
              are AUTHORED once and PARAMETERISED per environment. The second
              environment is not a second build -- but it is not free either.
              Items marked `per_environment: true` are scaled by
              1 + (n - 1) x provisioning_share.

  Consumption Azure resources run in every environment simultaneously
              throughout the build, so their cost is genuinely per-environment
              and does not decay. Four environments is four bills.

  Credits     A Copilot Studio agent deployed to a non-production environment
              consumes credits when it is exercised there. Production is
              excluded -- that is runtime, which this estimator does not cover.
"""

__author__ = "Dewain Robinson"

#: Each environment after the first costs this share of the original authoring
#: work: parameterisation, environment-specific config, pipeline stages,
#: secrets, seed data, and the drift that follows.
DEFAULT_PROVISIONING_SHARE = 0.25

#: Environments that never carry build-time agent testing.
PRODUCTION_NAMES = ("prod", "production", "live")


class EnvironmentError_(Exception):
    """Raised for environment input the user must fix."""


def normalise(config):
    """Validate the manifest's `environments:` block.

    Absent is allowed and means a single unnamed environment -- but the report
    says so, because a four-environment programme priced as one is the most
    expensive omission this tool can make.
    """
    if config is None:
        return {
            "declared": False,
            "environments": [{"name": "unspecified", "azure_usd": 0.0,
                              "agent_deployed": False, "production": False}],
            "count": 1,
            "provisioning_share": DEFAULT_PROVISIONING_SHARE,
            "work_multiplier": 1.0,
            "azure_usd": 0.0,
            "agent_environments": 0,
        }

    if isinstance(config, dict):
        entries = config.get("list") or config.get("environments") or []
        share = config.get("provisioning_share", DEFAULT_PROVISIONING_SHARE)
    else:
        entries, share = config, DEFAULT_PROVISIONING_SHARE

    if not isinstance(entries, list) or not entries:
        raise EnvironmentError_(
            "environments must be a non-empty list.\n\n"
            "  environments:\n"
            "    - name: dev\n"
            "      azure_usd: 4200\n"
            "      agent_deployed: true\n"
            "    - name: prod\n"
            "      azure_usd: 6100\n")

    try:
        share = float(share)
    except (TypeError, ValueError):
        raise EnvironmentError_(
            "environments.provisioning_share must be a number between 0 and 1.")
    if not (0.0 <= share <= 1.0):
        raise EnvironmentError_(
            "environments.provisioning_share must be between 0 and 1, got %s"
            % share)

    out = []
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise EnvironmentError_(
                "environments[%d] must be a mapping with at least a `name`."
                % index)
        name = str(entry.get("name") or "").strip()
        if not name:
            raise EnvironmentError_(
                "environments[%d] has no name." % index)
        try:
            azure = float(entry.get("azure_usd") or 0.0)
        except (TypeError, ValueError):
            raise EnvironmentError_(
                "environments[%s].azure_usd must be a number." % name)
        production = bool(entry.get("production",
                                    name.lower() in PRODUCTION_NAMES))
        deployed = bool(entry.get("agent_deployed", False))
        if production and deployed:
            # Exercising the agent in production is runtime, not build.
            deployed = False
        out.append({"name": name, "azure_usd": azure,
                    "agent_deployed": deployed, "production": production})

    count = len(out)
    return {
        "declared": True,
        "environments": out,
        "count": count,
        "provisioning_share": share,
        "work_multiplier": round(1.0 + (count - 1) * share, 4),
        "azure_usd": round(sum(e["azure_usd"] for e in out), 2),
        "agent_environments": sum(1 for e in out if e["agent_deployed"]),
    }


def render_markdown(env):
    """Report section explaining the environment multiplication."""
    out = ["## Environments", ""]

    if not env["declared"]:
        out.append("> **No environments were declared.** This estimate prices "
                   "the solution as if it\n> were built once, into one place. "
                   "A real delivery provisions dev, QA, test and\n> production "
                   "— each needing infrastructure applied, pipelines wired, "
                   "configuration\n> and secrets set, data seeded, and the "
                   "agent deployed.")
        out.append("")
        out.append("Declaring them is the single largest correction available "
                   "to this estimate.")
        out.append("")
        return "\n".join(out)

    out.append("Four things multiply across environments, and they multiply "
               "differently.")
    out.append("")
    out.append("| Environment | Azure during build | Agent deployed | Notes |")
    out.append("| --- | ---: | --- | --- |")
    for entry in env["environments"]:
        out.append("| %s | $%s | %s | %s |"
                   % (entry["name"],
                      format(entry["azure_usd"], ",.2f"),
                      "yes" if entry["agent_deployed"] else "no",
                      "production — runtime is out of scope"
                      if entry["production"] else ""))
    out.append("| **%d environments** | **$%s** | %d exercised |  |"
               % (env["count"], format(env["azure_usd"], ",.2f"),
                  env["agent_environments"]))
    out.append("")

    out.append("### How each cost multiplies")
    out.append("")
    out.append("| Cost | Multiplication | Why |")
    out.append("| --- | --- | --- |")
    out.append("| Infrastructure and pipeline **work** | **x%.2f** | Authored "
               "once, parameterised per environment. Each additional "
               "environment costs %.0f%% of the original: config, secrets, "
               "pipeline stages, seed data, drift |"
               % (env["work_multiplier"], env["provisioning_share"] * 100))
    out.append("| Azure **consumption** | **x%d** | Resources run in every "
               "environment at once throughout the build. This does not decay "
               "— four environments is four bills |" % env["count"])
    out.append("| Copilot Studio **credits** | x%d exercised | Only "
               "environments where the agent is deployed and tested consume "
               "build-time credits. Production is excluded, because "
               "exercising it there is runtime |"
               % env["agent_environments"])
    out.append("")
    out.append("Work marked `per_environment: true` in the breakdown carries "
               "the **x%.2f**\nmultiplier. Everything else is authored once."
               % env["work_multiplier"])
    out.append("")
    return "\n".join(out)
