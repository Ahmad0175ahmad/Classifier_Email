from email_system.cleaning import deduplicate, filter_emails
from email_system.models import EmailRecord


def test_filter_and_deduplicate():
    emails = [
        EmailRecord(
            message_id="1",
            conversation_id="c1",
            subject="Quote request",
            body="Hello, I need a quote for maintenance service.",
            sender="client@example.com",
        ),
        EmailRecord(
            message_id="2",
            conversation_id="c1",
            subject="Quote request",
            body="Hello, I need a quote for maintenance service.",
            sender="client@example.com",
        ),
    ]
    kept, removed = filter_emails(emails)
    assert len(removed) == 0
    deduped = deduplicate(kept)
    assert len(deduped) == 1
