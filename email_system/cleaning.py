from __future__ import annotations

import re
from typing import Iterable, List, Tuple

from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

from .models import EmailRecord
from .utils import normalize_text

DetectorFactory.seed = 0

SPAM_KEYWORDS_EN = {
    "casino",
    "betting",
    "lottery",
    "free money",
    "urgent transfer",
    "crypto giveaway",
    "click here",
}
SPAM_KEYWORDS_ES = {
    "casino",
    "apuesta",
    "loteria",
    "dinero gratis",
    "transferencia urgente",
    "regalo cripto",
    "haga clic",
}

SIGNATURE_PATTERNS = [
    re.compile(r"^--\s*$", re.MULTILINE),
    re.compile(r"^sent from my .*", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^best regards,.*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^saludos,.*$", re.IGNORECASE | re.MULTILINE),
]

QUOTE_PATTERNS = [
    re.compile(r"^on .* wrote:\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^from: .*", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^sent: .*", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^to: .*", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^subject: .*", re.IGNORECASE | re.MULTILINE),
]


def detect_language(text: str) -> str | None:
    if not text.strip():
        return None
    try:
        lang = detect(text)
    except LangDetectException:
        lang = None
    if lang not in {"en", "es"}:
        lang = None
    if lang is None:
        # Heuristic fallback for short/ambiguous text
        ascii_ratio = sum(1 for ch in text if ord(ch) < 128) / max(1, len(text))
        if ascii_ratio > 0.9:
            return "en"
    return lang


def strip_boilerplate(text: str) -> str:
    cleaned = text
    for pattern in SIGNATURE_PATTERNS:
        cleaned = pattern.split(cleaned)[0]
    for pattern in QUOTE_PATTERNS:
        cleaned = pattern.split(cleaned)[0]
    return cleaned.strip()


def is_spam(text: str, lang: str | None) -> bool:
    lowered = text.lower()
    keywords = SPAM_KEYWORDS_EN | SPAM_KEYWORDS_ES
    if lang == "en":
        keywords = SPAM_KEYWORDS_EN
    elif lang == "es":
        keywords = SPAM_KEYWORDS_ES
    return any(keyword in lowered for keyword in keywords)


def deduplicate(emails: Iterable[EmailRecord]) -> List[EmailRecord]:
    seen = set()
    deduped = []
    for email in emails:
        attachments = ",".join(sorted(email.attachments))
        key = normalize_text(f"{email.subject}\n{email.body}\n{attachments}")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(email)
    return deduped


def filter_emails(emails: Iterable[EmailRecord]) -> Tuple[List[EmailRecord], List[EmailRecord]]:
    kept = []
    removed = []
    for email in emails:
        subject = (email.subject or "").strip()
        body = (email.body or "").strip()
        if not subject or not body:
            removed.append(email)
            continue
        cleaned = strip_boilerplate(body)
        if not cleaned:
            removed.append(email)
            continue
        lang = detect_language(cleaned)
        if lang is None:
            removed.append(email)
            continue
        if is_spam(cleaned, lang):
            removed.append(email)
            continue
        email.body = cleaned
        email.raw["language"] = lang
        kept.append(email)
    return kept, removed
