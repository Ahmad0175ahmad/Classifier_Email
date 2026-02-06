from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import hdbscan
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class ClusterResult:
    labels: List[int]
    level1_map: Dict[int, str]
    level2_map: Dict[int, str]
    outlier_label: str = "needs_review"


def _extract_keywords(texts: List[str], top_k: int = 4) -> List[str]:
    vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
    tfidf = vectorizer.fit_transform(texts)
    scores = tfidf.mean(axis=0).A1
    indices = np.argsort(scores)[::-1][:top_k]
    terms = vectorizer.get_feature_names_out()
    return [terms[i] for i in indices if scores[i] > 0]


def _cluster_level1(centroids: np.ndarray) -> List[int]:
    if len(centroids) <= 2:
        return [0 for _ in range(len(centroids))]
    n_level1 = max(2, int(round(len(centroids) ** 0.5)))
    model = AgglomerativeClustering(n_clusters=n_level1)
    return model.fit_predict(centroids).tolist()


def cluster_embeddings(texts: List[str], embeddings: np.ndarray) -> ClusterResult:
    if len(embeddings) < 5:
        labels = [0 for _ in range(len(embeddings))]
        level2_map = {0: "small-batch"}
        level1_map = {0: "process-0:small-batch"}
        return ClusterResult(labels=labels, level1_map=level1_map, level2_map=level2_map)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=5, prediction_data=True)
    labels = clusterer.fit_predict(embeddings).tolist()

    level2_map: Dict[int, str] = {}
    level1_map: Dict[int, str] = {}

    clusters = sorted(set(label for label in labels if label != -1))
    if clusters:
        centroid_texts: List[str] = []
        centroids: List[np.ndarray] = []
        for cluster_id in clusters:
            members = [texts[i] for i, label in enumerate(labels) if label == cluster_id]
            keywords = _extract_keywords(members)
            level2_map[cluster_id] = "-".join(keywords) if keywords else f"cluster-{cluster_id}"
            centroid = embeddings[[i for i, label in enumerate(labels) if label == cluster_id]].mean(axis=0)
            centroids.append(centroid)
            centroid_texts.append(" ".join(keywords) if keywords else "general")

        level1_ids = _cluster_level1(np.vstack(centroids))
        for cluster_id, level1_id, keywords in zip(clusters, level1_ids, centroid_texts):
            level1_map[cluster_id] = f"process-{level1_id}:{keywords}"

    return ClusterResult(labels=labels, level1_map=level1_map, level2_map=level2_map)
