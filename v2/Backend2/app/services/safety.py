"""
Medical safety layer — deterministic guardrails independent of the LLM.

This runs BEFORE retrieval and generation.  If a message triggers a safety
rule, a pre-defined response is returned immediately.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

# ── Urgent symptom patterns ───────────────────────────────────────────────────
# These are clearly defined, reviewable rules — not LLM-dependent.

_EMERGENCY_PATTERNS = [
    # Severe bleeding
    r"\b(soaking|drench|flood|haemorrhag|hemorrhag)\b.*\b(pad|tampon|blood)\b",
    r"\b(heavy|uncontroll|massive)\b.*\bblee",
    r"\bbleed(ing)?\b.*\b(won't|wont|can't|cant|not|stop)\b",
    # Severe pain
    r"\b(unbearable|excruciating|worst|severe|sudden|sharp|stabbing)\b.*\b(pain|cramp|ache)\b",
    r"\b(cannot|can't|cant)\b.*(move|stand|walk|straighten)",
    # Fainting / consciousness
    r"\b(faint|fainted|pass(ed)? out|los(t|e|ing) consciousness)\b",
    # Fever with pelvic symptoms
    r"\b(fever|temperature)\b.*(pelvi|abdomen|stomach|uterus)",
    # Pregnancy emergencies
    r"\b(pregnan|pregnant)\b.*(bleed|pain|cramp|contraction|emergency|hospital)",
    r"\b(miscarriage|ectopic)\b",
    # Self-harm signals
    r"\b(want to die|end (my|it) all|hurt myself|self.harm|suicid)\b",
    # Chest / breathing
    r"\b(chest pain|can't breathe|cannot breathe|difficulty breathing)\b",
]

_EMERGENCY_REGEXES = [
    re.compile(p, re.IGNORECASE) for p in _EMERGENCY_PATTERNS
]

_EMERGENCY_RESPONSE = (
    "⚠️ **Please seek immediate medical attention.**\n\n"
    "The symptoms you've described may require urgent care. Please:\n"
    "• Call emergency services **(112 in India, 999 in UK, 911 in USA)**\n"
    "• Go to your nearest emergency room or hospital immediately\n"
    "• Contact the **National Women's Health Helpline: 1091** (India)\n\n"
    "Do not delay seeking professional help.\n\n"
    "---\n"
    "Once you are safe, Sakhi can provide general educational information. "
    "For now, please prioritise getting emergency care."
)

# ── Out-of-scope patterns ─────────────────────────────────────────────────────
# Questions clearly outside women's health education

_OUT_OF_SCOPE_PATTERNS = [
    r"\b(hack|crack|exploit|malware|virus|phishing)\b",
    r"\b(stock|crypto|bitcoin|investment|trading)\b",
    r"\b(recipe|cook|bake|food prep)\b",
    r"\b(travel|hotel|flight|itinerary)\b",
    r"\b(tax|income tax|gst|vat|finance|loan)\b",
]

_OUT_OF_SCOPE_REGEXES = [
    re.compile(p, re.IGNORECASE) for p in _OUT_OF_SCOPE_PATTERNS
]

_OUT_OF_SCOPE_RESPONSE = (
    "I'm Sakhi, your women's health companion, and I'm specifically designed "
    "to help with questions about menstrual health, reproductive wellness, "
    "hormones, menopause, and related topics.\n\n"
    "Your question seems to be about a different topic. Please feel free to "
    "ask me anything related to women's health!"
)


@dataclass
class SafetyResult:
    is_safe: bool
    triggered_rule: Optional[str]
    pre_set_response: Optional[str]


def check_safety(message: str) -> SafetyResult:
    """
    Run deterministic safety checks on the user message.

    Returns:
        SafetyResult with is_safe=False and a pre_set_response if a rule fires.
    """
    # 1. Emergency check — highest priority
    for pattern in _EMERGENCY_REGEXES:
        if pattern.search(message):
            return SafetyResult(
                is_safe=False,
                triggered_rule="emergency_symptoms",
                pre_set_response=_EMERGENCY_RESPONSE,
            )

    # 2. Out-of-scope check
    for pattern in _OUT_OF_SCOPE_REGEXES:
        if pattern.search(message):
            return SafetyResult(
                is_safe=False,
                triggered_rule="out_of_scope",
                pre_set_response=_OUT_OF_SCOPE_RESPONSE,
            )

    return SafetyResult(is_safe=True, triggered_rule=None, pre_set_response=None)
