# app/sentinel/experience/similarity_engine.py
"""
Similarity engine for comparing active failures and intents against logged historical transitions (S-0.10).
"""

from typing import List, Dict, Any, Optional

class SimilarityEngine:
    """
    Computes structural similarity scores between active workspace failure contexts
    and past transitions stored in the ledger.
    """

    @staticmethod
    def compute_jaccard_similarity(set_a: set, set_b: set) -> float:
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    @classmethod
    def compute_similarity(
        cls,
        active_failures: List[Dict[str, Any]],
        active_target_file: Optional[str],
        active_scope: Optional[str],
        historical_transition: Dict[str, Any]
    ) -> float:
        """
        Calculates a structural similarity score in [0.0, 1.0] based on:
        - Overlap of failure types (Jaccard similarity, weight = 0.5)
        - Matches in targeted files (weight = 0.3)
        - Matches in repair scope (weight = 0.2)
        """
        # 1. Failure type overlap
        active_types = {f.get("failure_type", "UNKNOWN") for f in active_failures}
        
        hist_states = historical_transition.get("states") or {}
        hist_failures = hist_states.get("before_failures") or []
        hist_types = {f.get("failure_type", "UNKNOWN") for f in hist_failures}
        
        type_similarity = cls.compute_jaccard_similarity(active_types, hist_types)

        # 2. Target file match
        hist_intent = historical_transition.get("intent") or {}
        hist_target = hist_intent.get("target_file")
        
        file_similarity = 0.0
        if active_target_file and hist_target:
            if str(active_target_file).strip().lower() == str(hist_target).strip().lower():
                file_similarity = 1.0
            elif str(active_target_file).strip().lower() in str(hist_target).strip().lower() or str(hist_target).strip().lower() in str(active_target_file).strip().lower():
                file_similarity = 0.5
        elif not active_target_file and not hist_target:
            file_similarity = 1.0

        # 3. Repair scope match
        hist_scope = hist_intent.get("scope")
        scope_similarity = 0.0
        if active_scope and hist_scope:
            if str(active_scope).strip().upper() == str(hist_scope).strip().upper():
                scope_similarity = 1.0
            else:
                scope_similarity = 0.5
        elif not active_scope and not hist_scope:
            scope_similarity = 1.0

        # Weighted combination
        score = (0.5 * type_similarity) + (0.3 * file_similarity) + (0.2 * scope_similarity)
        return round(score, 4)
