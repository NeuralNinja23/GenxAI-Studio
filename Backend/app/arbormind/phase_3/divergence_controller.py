# app/arbormind/phase_3/divergence_controller.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

from app.arbormind.phase_2.cognitive_directive import CognitiveDirective


@dataclass(frozen=True)
class CognitiveBranch:
    branch_id: str
    hypothesis: str
    reasoning_trace: str
    metadata: Dict[str, Any]


class DivergenceController:
    """
    Generates competing branches of thought under strict constraints.

    This component:
    - imagines
    - does NOT judge
    - does NOT execute
    """

    def __init__(self, llm):
        self._llm = llm  # injected, never owned

    def generate(
        self,
        problem_statement: str,
        directive: CognitiveDirective,
        max_branches: int = 5,
    ) -> List[CognitiveBranch]:
        """
        Generate competing hypotheses.

        Each branch must:
        - respect forbidden mutations
        - follow attention biases implicitly
        """
        
        # If no LLM, return a single pass-through branch
        if self._llm is None:
            return [
                CognitiveBranch(
                    branch_id="branch_0",
                    hypothesis=f"Execute: {problem_statement[:100]}",
                    reasoning_trace=problem_statement,
                    metadata={"passthrough": True},
                )
            ]

        prompt = self._build_prompt(problem_statement, directive, max_branches)

        raw = self._llm.generate(prompt)

        return self._parse_branches(raw)


    def _build_prompt(
        self,
        problem: str,
        directive: CognitiveDirective,
        max_branches: int,
    ) -> str:
        return f"""
You are generating alternative reasoning approaches.

Problem:
{problem}

Constraints:
- Forbidden mutation dimensions: {directive.forbidden_mutations}
- Allowed mutation dimensions: {directive.allowed_mutations}
- Avoid patterns: {directive.avoid_patterns}
- Prefer patterns: {directive.prefer_patterns}

Instruction:
Generate {max_branches} distinct approaches.
Each approach must be structurally different.
Do not select a best approach.
Do not repeat previous logic.
"""

    def _parse_branches(self, raw_output: str) -> List[CognitiveBranch]:
        """
        Deterministic parsing logic (no heuristics).
        """
        branches = []
        for idx, chunk in enumerate(raw_output.split("\n\n")):
            branches.append(
                CognitiveBranch(
                    branch_id=f"branch_{idx}",
                    hypothesis=chunk.splitlines()[0],
                    reasoning_trace=chunk,
                    metadata={},
                )
            )
        return branches
