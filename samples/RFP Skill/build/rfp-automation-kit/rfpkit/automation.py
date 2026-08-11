"""Starter automation layer for RFP responses.

This is the seed of the automation you want to build: given an RFP question (or
a whole list of them), match each to the best answer block in the reusable
response library and assemble a draft. It is intentionally simple and
dependency-free — keyword scoring over the library — so it is easy to read and
to replace later with embeddings / an LLM while keeping the same interface.

Interface worth keeping stable:
    match_question(question) -> Match
    answer_question(question, offering=None) -> str
    draft_response(offering, questions) -> list[Match]
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from .catalog_data import RESPONSE_LIBRARY
from . import models

_WORD = re.compile(r"[a-z0-9]+")


@dataclass
class Match:
    question: str
    topic: Optional[str]
    title: Optional[str]
    answer: Optional[str]
    score: float

    @property
    def matched(self) -> bool:
        return self.topic is not None


def _tokens(text: str):
    return set(_WORD.findall(text.lower()))


def _score(question_tokens, keywords) -> float:
    """Fraction-weighted overlap between the question and a topic's keywords.

    Multi-word keywords that appear as a phrase count strongest; single-word
    keyword hits add incremental score.
    """
    score = 0.0
    q = " ".join(sorted(question_tokens))
    for kw in keywords:
        kw_l = kw.lower()
        if " " in kw_l:
            # Phrase match: check the raw keyword words are all present.
            kw_tokens = set(_WORD.findall(kw_l))
            if kw_tokens and kw_tokens <= question_tokens:
                score += 2.0
        elif kw_l in question_tokens:
            score += 1.0
    return score


def match_question(question: str, min_score: float = 1.0) -> Match:
    """Return the best-matching library block for a single RFP question."""
    q_tokens = _tokens(question)
    best_topic = None
    best_score = 0.0
    for topic, block in RESPONSE_LIBRARY.items():
        s = _score(q_tokens, block.get("keywords", []))
        if s > best_score:
            best_score, best_topic = s, topic

    if best_topic is None or best_score < min_score:
        return Match(question=question, topic=None, title=None, answer=None, score=best_score)

    block = RESPONSE_LIBRARY[best_topic]
    return Match(
        question=question,
        topic=best_topic,
        title=block["title"],
        answer=block["answer"],
        score=best_score,
    )


def answer_question(question: str, offering: Optional[dict] = None) -> str:
    """Answer one question as text.

    If an offering is given and it overrides the matched topic in its own
    `snippets`, the offering-specific text wins.
    """
    m = match_question(question)
    if not m.matched:
        return (
            "[No library match — route to a subject-matter expert.] "
            f"Question: {question}"
        )
    if offering and m.topic in offering.get("snippets", {}):
        return offering["snippets"][m.topic]
    return m.answer


def draft_response(offering: dict, questions: List[str]) -> List[Match]:
    """Match every question in an RFP to a library block.

    Returns one Match per question, in order. Unmatched questions are flagged
    (topic is None) so a human can fill the gap — exactly the queue an
    automation would surface for review.
    """
    return [match_question(q) for q in questions]


def coverage(questions: List[str]) -> dict:
    """Report how many questions the library can auto-answer."""
    matches = [match_question(q) for q in questions]
    answered = sum(1 for m in matches if m.matched)
    return {
        "total": len(questions),
        "answered": answered,
        "unmatched": len(questions) - answered,
        "coverage_pct": round(100.0 * answered / len(questions), 1) if questions else 0.0,
    }
