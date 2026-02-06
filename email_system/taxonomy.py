from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .cluster import ClusterResult
from .models import TaxonomyLabel


@dataclass
class TaxonomyAssignment:
    labels: List[TaxonomyLabel]


def assign_taxonomy(
    cluster_result: ClusterResult,
    intents: List[tuple[str, float]],
) -> List[TaxonomyLabel]:
    labels: List[TaxonomyLabel] = []
    for idx, cluster_id in enumerate(cluster_result.labels):
        level1 = cluster_result.level1_map.get(cluster_id, cluster_result.outlier_label)
        level2 = cluster_result.level2_map.get(cluster_id, cluster_result.outlier_label)
        level3, intent_conf = intents[idx]
        needs_review = cluster_id == -1 or level3 == "requires_review"
        confidence = max(0.1, intent_conf)
        labels.append(
            TaxonomyLabel(
                level1=level1,
                level2=level2,
                level3=level3,
                confidence=confidence,
                needs_review=needs_review,
            )
        )
    return labels
