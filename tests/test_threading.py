from datetime import datetime

from email_system.models import EmailRecord
from email_system.threading import build_conversations


def test_build_conversations():
    emails = [
        EmailRecord(
            message_id="1",
            conversation_id="thread-a",
            subject="Re: Service request",
            body="First message",
            sender="client@example.com",
            date=datetime(2024, 1, 1, 10, 0, 0),
        ),
        EmailRecord(
            message_id="2",
            conversation_id="thread-a",
            subject="Re: Service request",
            body="Second message",
            sender="agent@example.com",
            date=datetime(2024, 1, 1, 11, 0, 0),
        ),
    ]
    conversations = build_conversations(emails)
    assert len(conversations) == 1
    assert conversations[0].metadata["thread_length"] == 2
