from email_system.intent import IntentClassifier


def test_intent_rules():
    classifier = IntentClassifier()
    result = classifier.classify("We need an urgent update on the service request.")
    assert result.level3 in {"urgent_escalation", "status_inquiry", "service_request"}
