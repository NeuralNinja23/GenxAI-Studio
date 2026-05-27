# app/failure_memory/repulsion_engine.py
"""
V4 Bounded Cognition — Stage 6: Minimal Cognition
Implements the RepulsionEngine, calculating vector cosine similarity to steer
cognitive exploration away from past failure pathways.
"""

import numpy as np
from typing import Optional
from app.failure_memory.failure_geometry import FailureGeometry

class RepulsionEngine:
    """
    Computes candidate similarity to historical failure states.
    Deforms search probability space using repulsion penalties.
    """

    def __init__(self, failure_db: Optional[FailureGeometry] = None):
        self.db = failure_db or FailureGeometry()

    def get_repulsion_score(self, candidate_vector: np.ndarray) -> float:
        """
        Compute the maximum cosine similarity score against all stored failures.
        Since vectors are pre-normalized to unit length, cosine similarity is simply the dot product.
        """
        failures = self.db.get_all_failures()
        if not failures:
            return 0.0

        max_similarity = 0.0
        for _, stored_vector, _, _, _ in failures:
            # Ensure shape match
            if stored_vector.shape == candidate_vector.shape:
                # Cosine Similarity = dot product for unit vectors
                similarity = float(np.dot(candidate_vector, stored_vector))
                max_similarity = max(max_similarity, similarity)

        return max_similarity

    def check_repulsion_breach(self, candidate_vector: np.ndarray, threshold: float = 0.85) -> bool:
        """
        Returns True if the repulsion similarity score violates safety limits.
        """
        score = self.get_repulsion_score(candidate_vector)
        return score >= threshold
