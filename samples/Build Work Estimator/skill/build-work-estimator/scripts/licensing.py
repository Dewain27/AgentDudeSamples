#!/usr/bin/env python3
"""How the build is licensed -- which decides what the number even means.

Author: Dewain Robinson

Two licensing shapes, and they ask different questions:

  consumption   Every unit bills. The question is "what will this cost?"
                Claude API/Console, Bedrock, Vertex, Foundry, Copilot Studio
                pay-as-you-go, GitHub Copilot usage-based AI Credits.

  seat          Usage draws from an allowance already paid for. The question
                is "will this fit, and what share of the seat does it consume?"
                Claude Pro/Max/Team/Enterprise, GitHub Copilot Business/
                Enterprise pooled credits, Copilot Studio prepaid packs.

A SEAT IS NOT FREE. Marginal spend inside an allowance is zero, but the seat
was bought with real money, so a build consuming 40% of a month's allowance
carries 40% of that month's seat cost. That attributable figure is what this
module computes -- reporting "$0" for seat-based work would repeat exactly the
error this estimator exists to prevent.

Seat prices are NOT hardcoded. They change, they vary by contract and region,
and a stale table would silently produce wrong attribution. The user supplies
their actual seat cost.
"""

__author__ = "Dewain Robinson"

SEAT = "seat"
CONSUMPTION = "consumption"

#: Windows that can be exhausted before a monthly total is. A build that is
#: cheap over a month can still stall repeatedly inside a short window.
CLAUDE_WINDOWS = ("5-hour rolling", "weekly")

PRICING_POINTERS = {
    "claude": "https://claude.com/pricing",
    "github-copilot": "https://docs.github.com/en/copilot/get-started/plans",
    "copilot-studio": "https://learn.microsoft.com/microsoft-copilot-studio/billing-licensing",
}


class LicensingError(Exception):
    """Raised for licensing input the user must fix."""


def normalise(config):
    """Validate and fill a manifest `licensing:` block."""
    cfg = dict(config or {})
    model = str(cfg.get("model", "")).strip().lower()
    if model not in (SEAT, CONSUMPTION):
        raise LicensingError(
            "licensing.model is required and must be %r or %r.\n\n"
            "  %r  every unit bills (Claude API/Console, Bedrock, Vertex, "
            "Foundry,\n            Copilot Studio pay-as-you-go, GitHub "
            "Copilot usage-based)\n"
            "  %r        usage draws on an allowance already paid for "
            "(Claude Pro/Max/\n            Team/Enterprise, GitHub Copilot "
            "Business/Enterprise, prepaid packs)\n\n"
            "This changes what the estimate means, not just its size."
            % (SEAT, CONSUMPTION, CONSUMPTION, SEAT)
        )

    out = {"model": model, "plan": str(cfg.get("plan", "") or "").strip()}


    if model == CONSUMPTION:
        return out

    seat_cost = cfg.get("seat_monthly_cost")
    if seat_cost is None:
        raise LicensingError(
            "licensing.seat_monthly_cost is required for seat-based "
            "licensing.\n\n"
            "A seat is not free. Without its cost this tool cannot attribute "
            "a share of\nit to the build, and would have to report $0 -- "
            "which is misleading.\n\n"
            "Enter what one seat actually costs you per month. Seat prices "
            "are not\nhardcoded here because they change and vary by "
            "contract. Current pricing:\n  %s"
            % "\n  ".join(sorted(set(PRICING_POINTERS.values())))
        )
    try:
        out["seat_monthly_cost"] = float(seat_cost)
    except (TypeError, ValueError):
        raise LicensingError(
            "licensing.seat_monthly_cost must be a number, got %r" % seat_cost)
    if out["seat_monthly_cost"] < 0:
        raise LicensingError("licensing.seat_monthly_cost cannot be negative.")

    out["seats"] = int(cfg.get("seats", 1) or 1)
    if out["seats"] < 1:
        raise LicensingError("licensing.seats must be at least 1.")

    # A team build spends across many developer-months. Without duration the
    # allowance denominator is one developer's single month, which makes any
    # team-scale programme look like a catastrophic overrun.
    raw_months = cfg.get("duration_months", 1)
    if raw_months is None:
        raw_months = 1
    try:
        out["duration_months"] = float(raw_months)
    except (TypeError, ValueError):
        raise LicensingError(
            "licensing.duration_months must be a number, got %r" % raw_months)
    if out["duration_months"] <= 0:
        raise LicensingError(
            "licensing.duration_months must be greater than zero.")

    # What fraction of the allowance period is already committed to other
    # work. Without this the overrun check is blind to everything else the
    # user does with the same seat.
    other = cfg.get("other_workload_share")
    if other is None:
        raise LicensingError(
            "licensing.other_workload_share is required for seat-based "
            "licensing.\n\n"
            "How much of the allowance period is already spoken for by other "
            "work?\nExpressed as a fraction: 0.0 means this build is the only "
            "thing using the\nseat; 0.7 means 70%% of it is already committed "
            "elsewhere.\n\n"
            "Without it the estimate cannot tell you whether this build will "
            "overrun the\nallowance, which is the failure that actually stops "
            "work."
        )
    try:
        out["other_workload_share"] = float(other)
    except (TypeError, ValueError):
        raise LicensingError(
            "licensing.other_workload_share must be a number between 0 and 1, "
            "got %r" % other)
    if not (0.0 <= out["other_workload_share"] <= 1.0):
        raise LicensingError(
            "licensing.other_workload_share must be between 0 and 1, got %s"
            % out["other_workload_share"])

    out["concentrated"] = bool(cfg.get("concentrated", False))
    # Recorded rather than recomputed at render time: a figure the renderer
    # invents is a figure nobody can account for.
    out["seat_rate_monthly"] = out["seat_monthly_cost"]
    out["seat_total_over_build"] = round(
        out["seat_monthly_cost"] * out["seats"] * out["duration_months"], 2)
    return out


def monthly_reference(profile):
    """Typical monthly consumption from measured history, in notional dollars.

    Returns None when history is too thin to say. Attribution then cannot be
    computed and the report says so rather than inventing a denominator.
    """
    if profile.get("source") != "measured":
        return None
    span = profile.get("date_range")
    total = profile.get("total_cost")
    if not span or not total:
        return None
    try:
        import datetime
        start = datetime.date.fromisoformat(span[0])
        end = datetime.date.fromisoformat(span[1])
    except (ValueError, TypeError, IndexError):
        return None
    days = max((end - start).days, 1)
    if days < 14:
        return None  # too short a window to extrapolate a month from
    return float(total) / days * 30.0


def attribute(notional_cost, licensing, profile):
    """Work out what a seat-based build actually costs its owner.

    `notional_cost` is the build priced at list rates -- what it would cost on
    consumption billing. For seat licensing that is not the bill, but it is a
    sound proxy for the *share of allowance* the build consumes.
    """
    if licensing["model"] == CONSUMPTION:
        return {
            "model": CONSUMPTION,
            "billed": True,
            "cost": round(float(notional_cost), 2),
            "notional_cost": round(float(notional_cost), 2),
        }

    seats = licensing["seats"]
    months = licensing["duration_months"]
    # Total seat spend over the whole build, not one seat for one month.
    seat_cost = licensing["seat_monthly_cost"] * seats * months
    per_seat_month = monthly_reference(profile)
    # Available allowance is one developer-month times the number of
    # developer-months the build actually runs for.
    monthly = per_seat_month * seats * months if per_seat_month else None

    result = {
        "model": SEAT,
        "billed": False,
        "plan": licensing.get("plan") or "unspecified",
        "seat_monthly_cost": round(seat_cost, 2),
        "seat_rate_monthly": licensing["seat_monthly_cost"],
        "seats": seats,
        "duration_months": months,
        "developer_months": round(seats * months, 2),
        "per_seat_month_reference": round(per_seat_month, 2)
        if per_seat_month else None,
        "notional_cost": round(float(notional_cost), 2),
        "monthly_reference": round(monthly, 2) if monthly else None,
        "other_workload_share": licensing["other_workload_share"],
        "concentrated": licensing["concentrated"],
        "windows": list(CLAUDE_WINDOWS),
    }

    if not monthly:
        result["allowance_share"] = None
        result["attributable_cost"] = None
        result["note"] = (
            "Allowance share could not be computed: at least 14 days of "
            "measured history is needed to establish a monthly reference. "
            "Run more work through the tool, or switch to consumption "
            "licensing to get a direct dollar figure."
        )
        return result

    share = float(notional_cost) / monthly
    total_share = share + licensing["other_workload_share"]

    result["allowance_share"] = round(share, 4)
    result["total_committed_share"] = round(total_share, 4)
    result["attributable_cost"] = round(seat_cost * share, 2)
    result["overruns"] = total_share > 1.0
    result["headroom_share"] = round(max(0.0, 1.0 - total_share), 4)
    if total_share > 1.0:
        result["overrun_by"] = round(total_share - 1.0, 4)
        result["overrun_cost"] = round(seat_cost * (total_share - 1.0), 2)
    return result


def render_markdown(attribution):
    """Report section describing what licensing means for this estimate."""
    out = ["## Licensing", ""]

    if attribution["model"] == CONSUMPTION:
        out.append("**Consumption billing.** Every unit consumed is billed, so "
                   "the figures above\nare the expected charge.")
        out.append("")
        return "\n".join(out)

    out.append("**Seat-based licensing (%s).** Usage draws on an allowance "
               "already paid for,\nso no additional money changes hands for "
               "this build -- but the seat is not free."
               % attribution["plan"])
    out.append("")

    if attribution.get("allowance_share") is None:
        out.append("> %s" % attribution["note"])
        out.append("")
        out.append("Notional value at list rates: **$%s** — what this build "
                   "would cost on\nconsumption billing. Shown for scale only; "
                   "it is not a charge."
                   % format(attribution["notional_cost"], ",.2f"))
        out.append("")
        return "\n".join(out)

    share = attribution["allowance_share"] * 100
    out.append("| | |")
    out.append("| --- | ---: |")
    out.append("| Developer-months of allowance available | %s (%d seat%s x %s month%s) |"
               % (format(attribution["developer_months"], ",g"),
                  attribution["seats"], "" if attribution["seats"] == 1 else "s",
                  format(attribution["duration_months"], ",g"),
                  "" if attribution["duration_months"] == 1 else "s"))
    out.append("| Share of that allowance | **%.0f%%** |" % share)
    out.append("| Seat spend over the build | $%s |"
               % format(attribution["seat_monthly_cost"], ",.2f"))
    out.append("| **Attributable cost of this build** | **$%s** |"
               % format(attribution["attributable_cost"], ",.2f"))
    out.append("| Already committed to other work | %.0f%% |"
               % (attribution["other_workload_share"] * 100))
    out.append("| **Total committed** | **%.0f%%** |"
               % (attribution["total_committed_share"] * 100))
    out.append("")
    out.append("The attributable cost is the seat's monthly price apportioned "
               "by the share of\nthe allowance this build consumes. Nothing "
               "extra is invoiced, but this is the\nreal cost of the capacity "
               "the build uses up.")
    out.append("")

    if attribution["overruns"]:
        out.append("### Allowance overrun")
        out.append("")
        out.append("**This build plus existing workload exceeds the allowance "
                   "by %.0f%%.**"
                   % (attribution["overrun_by"] * 100))
        out.append("")
        out.append("Work will stall at the limit unless overage is enabled, "
                   "at which point it\nbills on top of the seat. Overage "
                   "exposure at the same rate: **$%s**."
                   % format(attribution["overrun_cost"], ",.2f"))
        out.append("")
        out.append("Options: spread the build across allowance periods, move "
                   "part of it to\nconsumption billing, add seats, or reduce "
                   "the other committed work.")
    else:
        out.append("Headroom after this build and existing work: **%.0f%%** of "
                   "the allowance."
                   % (attribution["headroom_share"] * 100))
    out.append("")

    out.append("### Window risk")
    out.append("")
    out.append("Seat allowances refill on **%s** windows, not only monthly. A "
               "build that fits\ncomfortably in a month can still exhaust a "
               "short window and stall."
               % " and ".join(attribution["windows"]))
    if attribution["concentrated"]:
        out.append("")
        out.append("**This build is marked as concentrated** — compressed into "
                   "a short period.\nMonthly headroom will not protect it; "
                   "expect to hit shorter windows and plan\nfor pauses.")
    out.append("")
    out.append("Notional value at list rates: **$%s** — what this build would "
               "cost on\nconsumption billing. Shown for scale; it is not a "
               "charge."
               % format(attribution["notional_cost"], ",.2f"))
    out.append("")
    return "\n".join(out)
