from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from openai import AzureOpenAI

from .embedding import Embedder, build_embedder


INTENT_KEYWORDS = {
    "urgent_escalation": ["urgent", "asap", "immediate", "urgente", "inmediato"],
    "status_inquiry": ["status", "update", "avance", "estado", "seguimiento"],
    "complaint": ["complaint", "issue", "problem", "reclamo", "queja"],
    "additional_info": ["attached", "adjunto", "additional info", "informacion adicional"],
    "service_request": ["request", "quote", "cotizacion", "need", "solicito"],
}

INTENT_DESCRIPTIONS = {
    "urgent_escalation": "Urgent request requiring immediate action or escalation.",
    "status_inquiry": "Request asking for status update or progress.",
    "complaint": "Complaint, issue report, or service problem.",
    "additional_info": "Providing additional information or documents.",
    "service_request": "New service request or quote request.",
    "requires_review": "Unclear intent; requires human review.",
}


@dataclass
class IntentResult:
    level3: str
    confidence: float


class IntentClassifier:
    def __init__(self, embedder: Optional[Embedder] = None) -> None:
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_INTENT_DEPLOYMENT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.embedder = embedder or build_embedder()
        self._intent_embeddings = None

    def _client(self) -> AzureOpenAI:
        return AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )

    def _rule_based(self, text: str) -> IntentResult:
        lowered = text.lower()
        matched: List[str] = []
        for label, keywords in INTENT_KEYWORDS.items():
            if any(word in lowered for word in keywords):
                matched.append(label)
        if not matched:
            return IntentResult(level3="requires_review", confidence=0.4)
        if "urgent_escalation" in matched:
            return IntentResult(level3="urgent_escalation", confidence=0.85)
        if "complaint" in matched:
            return IntentResult(level3="complaint", confidence=0.8)
        if "status_inquiry" in matched:
            return IntentResult(level3="status_inquiry", confidence=0.75)
        if "service_request" in matched:
            return IntentResult(level3="service_request", confidence=0.7)
        if "additional_info" in matched:
            return IntentResult(level3="additional_info", confidence=0.65)
        return IntentResult(level3=matched[0], confidence=0.6)

    def _llm(self, text: str) -> IntentResult | None:
        if not (self.endpoint and self.api_key and self.deployment):
            return None
        client = self._client()
        prompt = (
            "Classify the intent of this email thread. "
            "Return JSON only with keys: level3, confidence. "
            "Valid level3 values: service_request, urgent_escalation, "
            "status_inquiry, complaint, additional_info, requires_review."
        )
        response = client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:6000]},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        level3 = data.get("level3", "requires_review")
        confidence = float(data.get("confidence", 0.5))
        return IntentResult(level3=level3, confidence=confidence)

    def _ensure_intent_embeddings(self) -> None:
        if self._intent_embeddings is not None:
            return
        texts = [f"{label}: {desc}" for label, desc in INTENT_DESCRIPTIONS.items()]
        vectors = self.embedder.embed(texts)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8
        self._intent_embeddings = vectors / norms

    def _embedding_based(self, text: str) -> IntentResult:
        self._ensure_intent_embeddings()
        vector = self.embedder.embed([text])[0]
        vector = vector / (np.linalg.norm(vector) + 1e-8)
        sims = self._intent_embeddings @ vector
        best_idx = int(np.argmax(sims))
        best_label = list(INTENT_DESCRIPTIONS.keys())[best_idx]
        confidence = float(max(0.5, sims[best_idx]))
        if best_label == "requires_review":
            confidence = min(confidence, 0.6)
        return IntentResult(level3=best_label, confidence=confidence)

    def classify(self, text: str) -> IntentResult:
        rule_result = self._rule_based(text)
        llm_result = self._llm(text)
        if llm_result is None:
            embedding_result = self._embedding_based(text)
            if embedding_result.confidence >= rule_result.confidence:
                return embedding_result
            return rule_result
        if llm_result.confidence >= rule_result.confidence:
            return llm_result
        return rule_result
