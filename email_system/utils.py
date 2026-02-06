from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def sender_domain(sender: str) -> str:
    if "@" in sender:
        return sender.split("@")[-1].lower()
    return "unknown"

