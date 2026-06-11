# app/studio/faculties/reggie.py
from typing import Any, List
import uuid

from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.cognition.branch import BranchState
from app.models.runtime_models import MutationTier
from app.core.logging import log


class ReggieWorkflowFaculty:
    """
    Reggie: Workflow Faculty (Adaptive Fallback)
    Suggests transitions and logical state workflow diagrams.
    """

    @staticmethod
    async def propose_mutations(
        branch: BranchState,
        description: str,
        intent: Any = None,
    ) -> List[PatchIR]:
        from app.sentinel.skills.skill_retriever import SkillRetriever
        retrieved_skills_data = SkillRetriever.retrieve(description, "Reggie")
        log("COGNITION", f"[REGGIE] (Deterministic) Logic retrieved {len(retrieved_skills_data)} skills but bypasses LLM.")

        # Fallback to simple topology additions for stages
        workflow_id = f"workflow_{uuid.uuid4().hex[:6]}"
        return [
            PatchIR(
                patch_id=f"reggie-wf-{uuid.uuid4().hex[:6]}",
                target_node_id=workflow_id,
                mutation_tier=MutationTier.TOPOLOGY,
                action="ADD_NODE",
                node_data={
                    "node_type": "WORKFLOW_NODE",
                    "properties": {
                        "workflow_name": "EmergencyFallbackWorkflow",
                        "states": ["IDLE", "RUNNING", "COMPLETED"],
                        "description": description,
                    }
                },
            )
        ]
