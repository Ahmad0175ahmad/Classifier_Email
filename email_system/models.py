from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class EmailRecord:
    message_id: str
    conversation_id: str
    subject: str
    body: str
    sender: str
    to: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    date: Optional[datetime] = None
    attachments: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def normalized_subject(self) -> str:
        subject = self.subject or ""
        prefixes = ("re:", "fw:", "fwd:", "rv:")
        lowered = subject.lower().strip()
        changed = True
        while changed:
            changed = False
            for p in prefixes:
                if lowered.startswith(p):
                    lowered = lowered[len(p) :].strip()
                    changed = True
        return lowered


@dataclass
class Conversation:
    conversation_id: str
    emails: List[EmailRecord]
    merged_subject: str
    merged_body: str
    attachment_names: List[str]
    metadata: Dict[str, Any]

    def embedding_text(self) -> str:
        attachment_part = ""
        if self.attachment_names:
            attachment_part = "\nAttachments: " + ", ".join(self.attachment_names)
        meta_tokens = []
        for key, value in self.metadata.items():
            if value is None:
                continue
            meta_tokens.append(f"{key}:{value}")
        meta_part = ""
        if meta_tokens:
            meta_part = "\nMetadata: " + " ".join(meta_tokens)
        return f"{self.merged_subject}\n{self.merged_body}{attachment_part}{meta_part}".strip()


@dataclass
class TaxonomyLabel:
    level1: str
    level2: str
    level3: str
    confidence: float
    needs_review: bool = False

