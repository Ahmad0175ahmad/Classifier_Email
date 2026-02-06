from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List

import numpy as np
import requests


class Embedder:
    def embed(self, texts: Iterable[str]) -> np.ndarray:
        raise NotImplementedError


@dataclass
class AzureOpenAIEmbedder(Embedder):
    endpoint: str
    api_key: str
    deployment: str
    api_version: str = "2024-02-15-preview"

    def embed(self, texts: Iterable[str]) -> np.ndarray:
        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/"
            f"{self.deployment}/embeddings?api-version={self.api_version}"
        )
        vectors: List[List[float]] = []
        for text in texts:
            response = requests.post(
                url,
                headers={"api-key": self.api_key},
                json={"input": text},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            vectors.append(payload["data"][0]["embedding"])
        return np.array(vectors, dtype=np.float32)


@dataclass
class MockEmbedder(Embedder):
    dim: int = 32

    def embed(self, texts: Iterable[str]) -> np.ndarray:
        rows = []
        for text in texts:
            seed = abs(hash(text)) % (10**8)
            rng = np.random.default_rng(seed)
            vec = rng.random(self.dim)
            rows.append(vec / np.linalg.norm(vec))
        return np.array(rows, dtype=np.float32)


def build_embedder() -> Embedder:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")
    if endpoint and api_key and deployment:
        return AzureOpenAIEmbedder(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
        )
    return MockEmbedder()
