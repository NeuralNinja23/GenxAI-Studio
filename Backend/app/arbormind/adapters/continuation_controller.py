# continuation_controller.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from app.arbormind.phase_1.state import ExecutionState, ExecutionStatus
from app.arbormind.phase_1.failure_memory import FailureMemory
from app.arbormind.phase_2.failure_taxonomy import FailureTaxonomy
from app.arbormind.phase_2.mutation_authority import MutationAuthority
from app.arbormind.phase_2.attention_bias import AttentionBiasEngine
from app.arbormind.phase_2.cognitive_directive import CognitiveDirective
from .lineage_tracker import LineageTracker


@dataclass(frozen=True)
class ContinuationDecision:
    continue_system: bool
    reason: str
    new_directive: Optional[CognitiveDirective]
    lineage_id: Optional[str]


class ContinuationController:
    """
    Decides whether and how the system should continue
    AFTER an execution halts.

    This controller:
    - never resumes execution
    - never retries
    - never patches execution state
    """

    def __init__(
        self,
        failure_memory: FailureMemory,
        taxonomy: FailureTaxonomy,
        mutation_authority: MutationAuthority,
        attention_bias_engine: AttentionBiasEngine,
        lineage_tracker: LineageTracker,
    ):
        self._failure_memory = failure_memory
        self._taxonomy = taxonomy
        self._mutation_authority = mutation_authority
        self._attention_bias_engine = attention_bias_engine
        self._lineage_tracker = lineage_tracker

    def decide_next(
        self,
        execution: ExecutionState,
        previous_directive: Optional[CognitiveDirective],
        parent_lineage_id: Optional[str],
    ) -> ContinuationDecision:

        if execution.status not in {
            ExecutionStatus.FAILED,
            ExecutionStatus.HALTED,
        }:
            return ContinuationDecision(
                continue_system=False,
                reason="Execution has not halted; continuation is illegal",
                new_directive=None,
                lineage_id=None,
            )

        if not execution.failures:
            return ContinuationDecision(
                continue_system=False,
                reason="Execution halted without failure signal",
                new_directive=None,
                lineage_id=None,
            )

        # Use the most recent failure
        failure = execution.failures[-1]
        failure_class = self._taxonomy.classify(failure)
        mutation_policy = self._mutation_authority.decide(failure_class)
        attention_bias = self._attention_bias_engine.derive(
            failure=failure_class,
            mutation_policy=mutation_policy,
        )

        # Build successor CognitiveDirective
        new_directive = CognitiveDirective(
            avoid_patterns=[],
            prefer_patterns=[],
            allowed_mutations=list(mutation_policy.allowed),
            forbidden_mutations=list(mutation_policy.forbidden),
            attention_boosts=attention_bias.boosts,
            attention_penalties=attention_bias.penalties,
        )

        lineage = self._lineage_tracker.record(
            execution_id=execution.run_id,
            parent_lineage_id=parent_lineage_id,
            failure_reason=failure.reason,
            directive_delta={
                "allowed_mutations": [d.value for d in new_directive.allowed_mutations],
                "forbidden_mutations": [
                    d.value for d in new_directive.forbidden_mutations
                ],
                "attention_bias": {
                    **attention_bias.boosts,
                    **attention_bias.penalties,
                },
            },
        )

        return ContinuationDecision(
            continue_system=True,
            reason="Execution halted; successor directive generated",
            new_directive=new_directive,
            lineage_id=lineage.lineage_id,
        )
