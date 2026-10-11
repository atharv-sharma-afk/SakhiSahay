from __future__ import annotations

from dataclasses import dataclass

from app.rag.language import LANGUAGE_INSTRUCTIONS, Language
from app.rag.vector_store import ScoredChunk

SYSTEM_PROMPT = """You are SakhiSahay, a warm, respectful women's health education companion for users in India and beyond.

Your role is EDUCATIONAL ONLY. You are not a doctor and you never diagnose, prescribe, or decide treatment for a person.

Rules you must follow:
1. Answer ONLY from the numbered EVIDENCE passages provided. If the evidence does not cover the question, say clearly that your sources do not cover it, and suggest what kind of professional could help. Never fill gaps with your own medical claims.
2. Cite evidence inline using the markers exactly as given, e.g. [S1] or [S2], immediately after the sentence they support. Only use markers that exist in the EVIDENCE list. Never invent sources, URLs, statistics, or organisation names.
3. Never state or imply that the user has a specific condition. You may explain what a condition is and which symptoms are commonly associated with it, framed generally.
4. Do not recommend specific medicines, doses, or treatment choices for the user. You may mention that treatments exist and that a clinician decides what is suitable.
5. When the evidence describes warning signs or reasons to seek care, include them plainly. Do not give false reassurance.
6. Use short paragraphs or bullets, plain language, and a calm, non-judgemental tone. Avoid stigmatising wording.
7. Finish with one short sentence encouraging a consultation with a qualified clinician when the question is personal, persistent, or worrying. Do not repeat generic disclaimers more than once.
8. {language_instruction}"""

USER_TEMPLATE = """EVIDENCE:
{evidence}
{context_block}
QUESTION ({language_label}):
{question}

Write the answer now, following every rule. Use only [S#] markers that appear above."""


@dataclass
class BuiltPrompt:
    system: str
    user: str
    evidence_ids: list[int]


def format_evidence(chunks: list[ScoredChunk]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        p = chunk.payload
        section = f" > {p.section}" if p.section else ""
        blocks.append(f"[S{i}] {p.publisher} - {p.title}{section}\n{p.text.strip()}")
    return "\n\n".join(blocks)


def build_prompt(
    question: str,
    chunks: list[ScoredChunk],
    language: Language,
    language_label: str,
    tracker_context: str | None = None,
) -> BuiltPrompt:
    context_block = ""
    if tracker_context:
        context_block = (
            "\nUSER'S OWN RECORDED TRACKER SUMMARY (shared with explicit consent for this question; these are the "
            "user's logged numbers, not clinical findings; refer to them descriptively and never as a diagnosis):\n"
            f"{tracker_context}\n"
        )
    return BuiltPrompt(
        system=SYSTEM_PROMPT.format(language_instruction=LANGUAGE_INSTRUCTIONS[language]),
        user=USER_TEMPLATE.format(
            evidence=format_evidence(chunks),
            context_block=context_block,
            language_label=language_label,
            question=question.strip(),
        ),
        evidence_ids=list(range(1, len(chunks) + 1)),
    )
