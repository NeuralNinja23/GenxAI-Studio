# app/sentinel/experience/experience_repository.py
"""
Repository for retrieving and formatting similar historical state transitions as evidence (S-0.10).
"""

import sqlite3
from typing import List, Dict, Any, Optional
from app.sentinel.experience.memory_access_layer import ExperienceMemoryAccessLayer
from app.sentinel.experience.similarity_engine import SimilarityEngine

class ExperienceRepository:
    """
    Orchestrates lookup and extraction of relevant historical experiences to aid LLM-guided repairs.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.mal = ExperienceMemoryAccessLayer(db_path=db_path)

    def retrieve_similar_experiences(
        self,
        active_failures: List[Dict[str, Any]],
        target_file: Optional[str],
        scope: Optional[str],
        limit: int = 3,
        similarity_threshold: float = 0.3,
        only_successful: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Queries the ledger database, scores candidate transitions using the SimilarityEngine,
        and returns the top-N matches above the similarity threshold.
        """
        # Fetch all transitions from database
        all_ids = []
        try:
            with sqlite3.connect(str(self.mal.db_path), timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT transition_id FROM state_transitions")
                all_ids = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[EXPERIENCE_REPOSITORY] Failed to fetch transition list: {e}")
            return []

        scored_matches = []
        for t_id in all_ids:
            transition = self.mal.get_transition(t_id)
            if not transition:
                continue

            # Filtering for successful runs (oracle score improved / after is less than before)
            if only_successful:
                before_oracle = transition.get("before_oracle", 0.0)
                after_oracle = transition.get("after_oracle", 0.0)
                if after_oracle >= before_oracle:
                    # Skip unsuccessful transitions
                    continue

            # Compute similarity
            sim_score = SimilarityEngine.compute_similarity(
                active_failures=active_failures,
                active_target_file=target_file,
                active_scope=scope,
                historical_transition=transition
            )

            if sim_score >= similarity_threshold:
                scored_matches.append((sim_score, transition))

        # Sort by similarity score descending
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        
        # Take the top-K
        selected_matches = []
        for score, transition in scored_matches[:limit]:
            transition["similarity_score"] = score
            selected_matches.append(transition)

        return selected_matches

    def format_experiences_for_prompt(self, experiences: List[Dict[str, Any]]) -> str:
        """
        Formats retrieved transitions into a plain-text context prompt block.
        """
        if not experiences:
            return ""

        output = ["\n=== HISTORICAL REPAIR EVIDENCE ==="]
        for idx, exp in enumerate(experiences, 1):
            intent = exp.get("intent") or {}
            artifacts = exp.get("artifacts") or {}
            states = exp.get("states") or {}
            
            output.append(f"\n[Evidence Sample {idx}] (Similarity: {exp.get('similarity_score', 0.0):.2f})")
            output.append(f"- Targeted File: {intent.get('target_file')}")
            output.append(f"- Scope: {intent.get('scope')}")
            output.append(f"- Mode: {intent.get('repair_mode')}")
            output.append(f"- Instruction: {intent.get('instruction')}")
            
            # Summarize failure change
            before_fails = [f.get("failure_type", "UNKNOWN") for f in states.get("before_failures", [])]
            after_fails = [f.get("failure_type", "UNKNOWN") for f in states.get("after_failures", [])]
            output.append(f"- Before Failures: {', '.join(before_fails) if before_fails else 'None'}")
            output.append(f"- After Failures: {', '.join(after_fails) if after_fails else 'None'}")
            
            # Include code diff
            diff = artifacts.get("diff")
            if diff:
                output.append("- Applied Source Code Diff:")
                output.append("```diff")
                output.append(diff.strip())
                output.append("```")
            else:
                output.append("- No diff generated.")
        
        output.append("\n=== END OF HISTORICAL EVIDENCE ===")
        return "\n".join(output)
