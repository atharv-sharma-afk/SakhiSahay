"""Lightweight language handling for English, Hindi (Devanagari) and Hinglish.

Deliberately heuristic: no extra model, no translation API. The user's explicit
choice always wins; detection only fills in "auto". Accuracy limits are
documented in docs/evaluation.
"""

from __future__ import annotations

import re
from typing import Literal

Language = Literal["en", "hi", "hinglish"]
LanguageChoice = Literal["auto", "en", "hi", "hinglish"]

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_TOKEN = re.compile(r"[a-zA-Z]+")

# Romanised Hindi function words and health vocabulary that rarely occur in English text.
_HINGLISH_MARKERS = {
    "kya", "kyu", "kyun", "kyon", "hai", "hain", "ho", "hoon", "hu", "hota", "hoti", "hote",
    "mujhe", "mera", "meri", "mere", "humko", "hamko", "mujhko", "aap", "aapko", "tum",
    "ka", "ki", "ke", "ko", "se", "mein", "nahi", "nahin", "bahut", "bohot", "zyada", "jyada",
    "dard", "kaise", "kaisa", "kaisi", "kab", "kitna", "kitne", "kitni", "din", "dino", "baar",
    "mahine", "mahina", "mahiney", "peeth", "pet", "khoon", "batao", "bataiye", "bata",
    "raha", "rahi", "rahe", "tha", "thi", "the", "aur", "lekin", "kar", "karna", "karu", "karun",
    "chahiye", "sakti", "sakta", "sakte", "wala", "wali", "bhi", "toh", "abhi", "pehle", "baad",
    "mahwari", "masik", "dharm", "garbh", "garbhavastha", "pregnant", "pareshani", "takleef",
    "theek", "thik", "normal", "hona", "hone", "hogi", "hoga", "ilaj", "dawai", "dawa", "doctor",
    "jana", "jaana", "dikhana", "samajh", "matlab", "wajah", "kyuki", "kyunki", "agar", "phir",
}
# English words that also appear in the marker set are excluded above on purpose
# (e.g. "the" is kept out of scoring by the ratio threshold and "to"/"me" are not markers).
_HINGLISH_MARKERS.discard("the")


def detect_language(text: str) -> Language:
    if _DEVANAGARI.search(text):
        return "hi"
    tokens = [t.lower() for t in _TOKEN.findall(text)]
    if not tokens:
        return "en"
    hits = sum(1 for t in tokens if t in _HINGLISH_MARKERS)
    if hits >= 2 and hits / len(tokens) >= 0.2:
        return "hinglish"
    return "en"


def resolve_language(text: str, choice: LanguageChoice) -> tuple[Language, Language]:
    """Return (detected, to_use)."""
    detected = detect_language(text)
    return detected, (detected if choice == "auto" else choice)


LANGUAGE_INSTRUCTIONS: dict[Language, str] = {
    "en": "Respond in clear, simple English.",
    "hi": (
        "Respond in Hindi written in Devanagari script. Keep sentences short. For medical terms, give the "
        "common Hindi word and the English term in brackets where helpful, e.g. माहवारी (periods)."
    ),
    "hinglish": (
        "Respond in Hinglish: Hindi written in the Latin alphabet, naturally mixing common English health "
        "words, the way a friendly Indian health worker would text. Example tone: 'Periods ke dauran halka "
        "dard common hai.' Do not use Devanagari script."
    ),
}

LANGUAGE_LABELS: dict[Language, str] = {"en": "English", "hi": "Hindi", "hinglish": "Hinglish"}
