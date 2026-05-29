# app/sentinel/failure_memory/repulsion_engine.py
import numpy as np
from .failure_geometry import FailureGeometry

class RepulsionEngine:
    def __init__(self, failure_geometry: FailureGeometry):
        self.failure_geometry = failure_geometry

    def get_repulsion_score(self, candidate_vec: np.ndarray) -> float:
        failures = self.failure_geometry.get_all_failures()
        if not failures:
            return 0.0
        max_sim = 0.0
        for f_id, vec, err_class, cyc_id, details in failures:
            sim = float(np.dot(candidate_vec, vec))
            if sim > max_sim:
                max_sim = sim
        return max_sim

    def check_repulsion_breach(self, candidate_vec: np.ndarray, threshold: float = 0.85) -> bool:
        score = self.get_repulsion_score(candidate_vec)
        return score >= threshold
