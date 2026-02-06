import json

from email_system.pipeline import run_pipeline


def test_pipeline_runs(tmp_path):
    payload = [
        {
            "id": "1",
            "conversationId": "c1",
            "subject": "Request for quote",
            "body": "Hello, I need a quote for cleaning services.",
            "from": "client@example.com",
            "sentDateTime": "2024-01-01T10:00:00",
            "attachments": [{"name": "requirements.pdf"}],
        },
        {
            "id": "2",
            "conversationId": "c1",
            "subject": "Re: Request for quote",
            "body": "Thanks, please proceed.",
            "from": "agent@example.com",
            "sentDateTime": "2024-01-01T11:00:00",
        },
    ]
    path = tmp_path / "emails.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    output = run_pipeline(str(path))
    assert output["summary"]["conversations"] == 1
    assert output["conversations"][0]["labels"]["level3"]
