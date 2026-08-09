"""Shared Markdown building blocks used by both renderers."""

from typing import Iterable


def bullet_list(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered_list(items: Iterable[str], start: int = 1) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, start=start))


def money(value: int) -> str:
    return f"${value:,}"


def money_range(low: int, high: int) -> str:
    return f"{money(low)} – {money(high)}"


def date(d) -> str:
    return d.strftime("%B %d, %Y")


DISCLAIMER = (
    "> **Sample document.** This RFP is fictional and was generated for "
    "demonstration purposes. All organizations, names, figures, and details "
    "are invented and do not represent any real entity, price, or agreement."
)
