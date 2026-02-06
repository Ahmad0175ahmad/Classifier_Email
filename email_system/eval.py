from __future__ import annotations

import math
from typing import List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def average_intra_cluster_similarity(embeddings: np.ndarray, labels: List[int]) -> float:
    total = 0.0
    count = 0
    for label in set(labels):
        if label == -1:
            continue
        idx = [i for i, l in enumerate(labels) if l == label]
        if len(idx) < 2:
            continue
        sims = cosine_similarity(embeddings[idx])
        total += (sims.sum() - len(idx)) / (len(idx) * (len(idx) - 1))
        count += 1
    return total / count if count else 0.0


def dunn_index(embeddings: np.ndarray, labels: List[int]) -> float:
    clusters = [label for label in set(labels) if label != -1]
    if len(clusters) < 2:
        return 0.0
    dist_matrix = 1 - cosine_similarity(embeddings)
    intra_max = 0.0
    for label in clusters:
        idx = [i for i, l in enumerate(labels) if l == label]
        if len(idx) < 2:
            continue
        intra_max = max(intra_max, dist_matrix[np.ix_(idx, idx)].max())
    inter_min = math.inf
    for i, label_a in enumerate(clusters):
        idx_a = [i for i, l in enumerate(labels) if l == label_a]
        for label_b in clusters[i + 1 :]:
            idx_b = [i for i, l in enumerate(labels) if l == label_b]
            inter_min = min(inter_min, dist_matrix[np.ix_(idx_a, idx_b)].min())
    if inter_min == math.inf or intra_max == 0.0:
        return 0.0
    return float(inter_min / intra_max)
