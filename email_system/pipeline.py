from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from .cleaning import deduplicate, filter_emails
from .cluster import cluster_embeddings
from .embedding import build_embedder
from .eval import average_intra_cluster_similarity, dunn_index
from .intent import IntentClassifier
from .io import load_emails
from .models import Conversation, TaxonomyLabel
from .taxonomy import assign_taxonomy
from .threading import build_conversations


def _conversation_payload(convo: Conversation, label: TaxonomyLabel) -> Dict[str, Any]:
    return {
        "conversation_id": convo.conversation_id,
        "subject": convo.merged_subject,
        "labels": {
            "level1": label.level1,
            "level2": label.level2,
            "level3": label.level3,
        },
        "confidence": label.confidence,
        "needs_review": label.needs_review,
        "metadata": convo.metadata,
    }


def run_pipeline(input_path: str) -> Dict[str, Any]:
    emails = load_emails(input_path)
    filtered, removed = filter_emails(emails)
    deduped = deduplicate(filtered)
    conversations = build_conversations(deduped)

    texts = [convo.embedding_text() for convo in conversations]
    embedder = build_embedder()
    embeddings = embedder.embed(texts)
    if embeddings.ndim == 1:
        embeddings = np.expand_dims(embeddings, axis=0)

    cluster_result = cluster_embeddings(texts, embeddings)
    intent_classifier = IntentClassifier(embedder=embedder)
    intents = []
    for text in texts:
        intent = intent_classifier.classify(text)
        intents.append((intent.level3, intent.confidence))
    labels = assign_taxonomy(cluster_result, intents)

    avg_sim = average_intra_cluster_similarity(embeddings, cluster_result.labels)
    dunn = dunn_index(embeddings, cluster_result.labels)

    return {
        "summary": {
            "input_emails": len(emails),
            "filtered_out": len(removed),
            "deduped": len(deduped),
            "conversations": len(conversations),
            "avg_intra_cluster_similarity": round(avg_sim, 3),
            "dunn_index": round(dunn, 3),
        },
        "conversations": [
            _conversation_payload(convo, label)
            for convo, label in zip(conversations, labels)
        ],
    }
