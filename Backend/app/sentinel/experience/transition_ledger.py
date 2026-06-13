# app/sentinel/experience/transition_ledger.py
"""
Transition Ledger coordinator coordinating writing, reading, and querying of raw transitions (S-0.10).
"""

from typing import List, Dict, Any, Optional
from app.sentinel.experience.memory_access_layer import ExperienceMemoryAccessLayer
from app.sentinel.experience.experience_repository import ExperienceRepository

class TransitionLedger:
    """
    Central coordinator to record, look up, and retrieve transitions from the immutable ledger.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.mal = ExperienceMemoryAccessLayer(db_path=db_path)
        self.repo = ExperienceRepository(db_path=db_path)

    def record_transition(
        self,
        transition_id: str,
        parent_transition_id: Optional[str],
        cycle_id: str,
        workspace_id: str,
        attempt_number: int,
        workspace_hash: str,
        before_oracle: float,
        after_oracle: float,
        # States
        before_failures: List[Dict[str, Any]],
        after_failures: List[Dict[str, Any]],
        before_verification_summary: Dict[str, Any],
        after_verification_summary: Dict[str, Any],
        # Intents
        target_file: Optional[str],
        scope: Optional[str],
        repair_mode: Optional[str],
        instruction: Optional[str],
        prompt: Optional[str],
        context_metadata: Dict[str, Any],
        # Artifacts
        before_source: Optional[str],
        after_source: Optional[str],
        diff: Optional[str],
        compiler_output: Optional[str],
        bundler_output: Optional[str],
        runtime_output: Optional[str],
        render_output: Optional[str]
    ) -> bool:
        """Atomically appends a complete observed transition to the ledger."""
        return self.mal.insert_transition(
            transition_id=transition_id,
            parent_transition_id=parent_transition_id,
            cycle_id=cycle_id,
            workspace_id=workspace_id,
            attempt_number=attempt_number,
            workspace_hash=workspace_hash,
            before_oracle=before_oracle,
            after_oracle=after_oracle,
            before_failures=before_failures,
            after_failures=after_failures,
            before_verification_summary=before_verification_summary,
            after_verification_summary=after_verification_summary,
            target_file=target_file,
            scope=scope,
            repair_mode=repair_mode,
            instruction=instruction,
            prompt=prompt,
            context_metadata=context_metadata,
            before_source=before_source,
            after_source=after_source,
            diff=diff,
            compiler_output=compiler_output,
            bundler_output=bundler_output,
            runtime_output=runtime_output,
            render_output=render_output
        )

    def get_transition(self, transition_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single transition object."""
        return self.mal.get_transition(transition_id)

    def get_cycle_transitions(self, cycle_id: str) -> List[Dict[str, Any]]:
        """Retrieves all transitions registered under a specific cycle_id."""
        return self.mal.get_cycle_transitions(cycle_id)

    def find_similar_evidence(
        self,
        active_failures: List[Dict[str, Any]],
        target_file: Optional[str],
        scope: Optional[str],
        limit: int = 3,
        similarity_threshold: float = 0.3,
        only_successful: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieves similar transitions as evidence candidates."""
        return self.repo.retrieve_similar_experiences(
            active_failures=active_failures,
            target_file=target_file,
            scope=scope,
            limit=limit,
            similarity_threshold=similarity_threshold,
            only_successful=only_successful
        )

    def get_evidence_context(self, active_failures: List[Dict[str, Any]], target_file: Optional[str], scope: Optional[str]) -> str:
        """Retrieves and formats evidence block for prompt injection."""
        experiences = self.find_similar_evidence(active_failures, target_file, scope)
        return self.repo.format_experiences_for_prompt(experiences)
