"""Keyword-based safety screening.

This is a transparent, limited heuristic layer that runs independently of the
language model. It never blocks a question; it adds clearly worded notices so
that urgent situations are signposted even if generation fails. Escalation
wording follows NHS patient guidance (links included) and is phrased as general
information, not as an assessment of the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

SafetyLevel = Literal["none", "advisory", "urgent"]

NHS_HEAVY = "https://www.nhs.uk/conditions/heavy-periods/"
NHS_PAIN = "https://www.nhs.uk/symptoms/period-pain/"
NHS_PREG_BLEED = "https://www.nhs.uk/pregnancy/common-symptoms/vaginal-bleeding/"
NHS_ECTOPIC = "https://www.nhs.uk/conditions/ectopic-pregnancy/"


@dataclass
class SafetyNotice:
    level: SafetyLevel
    title: str
    message: str
    source_url: str | None = None
    source_label: str | None = None


@dataclass
class SafetyAssessment:
    level: SafetyLevel = "none"
    flags: list[str] = field(default_factory=list)
    notices: list[SafetyNotice] = field(default_factory=list)


def _rx(*patterns: str) -> re.Pattern[str]:
    return re.compile("|".join(patterns), re.IGNORECASE)


# Each rule: (flag, pattern, notice). Patterns cover English, Hinglish and Hindi phrasings.
_URGENT_RULES: list[tuple[str, re.Pattern[str], SafetyNotice]] = [
    (
        "very_heavy_bleeding",
        _rx(
            r"soak(ing|ed)?\s+(a|through|one)?\s*(pad|tampon)s?\s+(every|each|within)\s+(hour|1|one|2|two)",
            r"pad (every|each) (hour|1|one) hour",
            r"(har|every)\s+(ghante|ghanta|hour)\s+pad",
            r"(bleeding|khoon|खून)\s+(ruk|band)\s*(nahi|नहीं)",
            r"blood clots? (bigger|larger) than",
            r"बहुत (ज़्यादा|ज्यादा) (खून|रक्तस्राव)",
        ),
        SafetyNotice(
            level="urgent",
            title="Very heavy bleeding needs prompt medical attention",
            message=(
                "NHS advises getting urgent help if you feel faint, very short of breath, or are bleeding very heavily "
                "(for example soaking a pad every hour). Please contact a doctor, emergency service, or nearest hospital now."
            ),
            source_url=NHS_HEAVY,
            source_label="NHS - Heavy periods",
        ),
    ),
    (
        "faint_or_collapse",
        _rx(r"\bfaint(ed|ing)?\b", r"passed out", r"unconscious", r"behosh", r"chakkar (aa|aate|aata)", r"बेहोश", r"चक्कर"),
        SafetyNotice(
            level="urgent",
            title="Fainting or dizziness with bleeding or pain",
            message=(
                "Fainting, severe dizziness or collapse alongside bleeding or abdominal pain are signs NHS lists for "
                "immediate care. Please seek emergency help now rather than waiting for an online answer."
            ),
            source_url=NHS_PAIN,
            source_label="NHS - Period pain",
        ),
    ),
    (
        "pregnancy_bleeding_or_pain",
        _rx(
            r"pregnan\w*.*(bleed|blood|spotting|shoulder|severe pain|sharp pain)",
            r"(bleed|blood|spotting|shoulder|severe pain|sharp pain).*pregnan\w*",
            r"(garbh|garbhavastha|pregnant).*(khoon|bleeding|dard)",
            r"(khoon|bleeding|dard).*(garbh|garbhavastha|pregnant)",
            r"गर्भ\w*.*(खून|रक्त|दर्द)",
            r"(खून|रक्त|दर्द).*गर्भ\w*",
            r"ectopic",
        ),
        SafetyNotice(
            level="urgent",
            title="Bleeding or severe pain in pregnancy",
            message=(
                "NHS advises anyone who is pregnant and bleeding to contact their maternity unit, GP or emergency line "
                "promptly, and to call emergency services if there is severe abdominal pain, shoulder-tip pain, "
                "fainting, or heavy bleeding. Please get medical help now."
            ),
            source_url=NHS_PREG_BLEED,
            source_label="NHS - Vaginal bleeding in pregnancy",
        ),
    ),
    (
        "severe_pain",
        _rx(
            r"(severe|unbearable|worst|excruciating|sharp sudden)\s+(pain|cramp)",
            r"pain(killers?)? (not|don't|doesn't|isn't) (help|work)",
            r"(bahut|bohot|itna)\s+(tez|zyada|jyada)\s+dard",
            r"asahniya dard",
            r"असहनीय दर्द",
            r"बहुत (तेज़|तेज|ज़्यादा|ज्यादा) दर्द",
        ),
        SafetyNotice(
            level="urgent",
            title="Severe pain that painkillers do not ease",
            message=(
                "NHS says to ask for an urgent GP appointment or call the urgent helpline if pelvic or period pain is "
                "severe or worse than usual and painkillers have not helped. Please contact a clinician today."
            ),
            source_url=NHS_PAIN,
            source_label="NHS - Period pain",
        ),
    ),
    (
        "self_harm",
        _rx(r"suicid", r"kill myself", r"end my life", r"self[- ]harm", r"(khud ko|apne aap ko) (maar|khatam)", r"आत्महत्या", r"मरना चाहती"),
        SafetyNotice(
            level="urgent",
            title="You deserve immediate support",
            message=(
                "If you are thinking about harming yourself, please reach out right now to someone you trust or a "
                "crisis helpline in your country (in India, Tele-MANAS 14416 is a government mental-health helpline). "
                "You are not alone, and help is available."
            ),
        ),
    ),
]

_ADVISORY_RULES: list[tuple[str, re.Pattern[str], SafetyNotice]] = [
    (
        "diagnosis_request",
        _rx(
            r"\bdo i have\b", r"\bdiagnos", r"\bis it (pcos|endometriosis|cancer|pregnan|fibroid)",
            r"kya mujhe .* (hai|ho gaya|ho gayi)", r"kya (ye|yeh) .* hai", r"क्या मुझे", r"क्या (ये|यह)",
        ),
        SafetyNotice(
            level="advisory",
            title="SakhiSahay cannot diagnose",
            message=(
                "This assistant explains general, source-backed information only. Whether a symptom points to a "
                "particular condition can only be assessed by a qualified clinician who can examine you and order tests."
            ),
        ),
    ),
    (
        "medication_request",
        _rx(
            r"\b(which|what|best)\s+(medicine|tablet|pill|painkiller|drug|dose|dosage)",
            r"\bshould i take\b", r"\bcan i take\b", r"\bhow (much|many)\s+(mg|tablets?|pills?)",
            r"(kaun ?si|konsi|kya)\s+(dawai|dawa|tablet|goli|medicine)", r"(dawai|dawa|goli|tablet)\s+(lu|loon|le sakti|khau)",
            r"कौन ?सी (दवा|गोली)", r"(दवा|गोली) (लूँ|लूं|ले सकती)",
        ),
        SafetyNotice(
            level="advisory",
            title="Medicine choices need a clinician or pharmacist",
            message=(
                "SakhiSahay does not recommend specific medicines or doses. Pain relief and other treatments can be "
                "discussed with a doctor or pharmacist who knows your health history."
            ),
        ),
    ),
]


def screen_question(text: str) -> SafetyAssessment:
    assessment = SafetyAssessment()
    for flag, pattern, notice in _URGENT_RULES:
        if pattern.search(text):
            assessment.flags.append(flag)
            assessment.notices.append(notice)
    for flag, pattern, notice in _ADVISORY_RULES:
        if pattern.search(text):
            assessment.flags.append(flag)
            assessment.notices.append(notice)
    if any(n.level == "urgent" for n in assessment.notices):
        assessment.level = "urgent"
    elif assessment.notices:
        assessment.level = "advisory"
    return assessment


EDUCATIONAL_DISCLAIMER = (
    "SakhiSahay shares general health education from cited public sources. It is not a medical diagnosis, "
    "treatment plan, or a substitute for a consultation with a qualified clinician."
)
