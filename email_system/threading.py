from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List

from .models import Conversation, EmailRecord
from .utils import sender_domain


def build_conversations(emails: Iterable[EmailRecord]) -> List[Conversation]:
    buckets: Dict[str, List[EmailRecord]] = defaultdict(list)
    for email in emails:
        key = email.conversation_id or email.normalized_subject()
        buckets[key].append(email)

    conversations: List[Conversation] = []
    for convo_id, items in buckets.items():
        items_sorted = sorted(items, key=lambda e: e.date or datetime.min)
        merged_subject = items_sorted[0].normalized_subject() if items_sorted else ""
        merged_body = "\n\n".join(email.body for email in items_sorted if email.body)
        attachment_names = []
        for email in items_sorted:
            attachment_names.extend(email.attachments)
        metadata = {
            "sender_domain": sender_domain(items_sorted[0].sender if items_sorted else ""),
            "thread_length": len(items_sorted),
            "has_attachments": bool(attachment_names),
        }
        conversations.append(
            Conversation(
                conversation_id=convo_id,
                emails=items_sorted,
                merged_subject=merged_subject,
                merged_body=merged_body,
                attachment_names=sorted(set(attachment_names)),
                metadata=metadata,
            )
        )
    return conversations

