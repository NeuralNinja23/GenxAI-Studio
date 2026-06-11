# app/studio/faculties/derek.py
from typing import Any, List

from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.cognition.branch import BranchState
from app.llm.prompts import DEREK_PROMPT
from app.studio.mutation.mutation_engine import MutationEngine
from app.studio.faculties.utils import serialize_graph_for_llm
from app.core.logging import log


class DerekAPIFaculty:
    """
    Derek: API Faculty
    Suggests API route paths, REST methods, and service wiring layers.
    """

    @staticmethod
    async def propose_mutations(
        branch: BranchState,
        description: str,
        intent: Any = None,
    ) -> List[PatchIR]:
        log("COGNITION", "Derek API Faculty analyzing routing requirements...")
        graph = branch.topology_graph

        from app.sentinel.skills.skill_retriever import SkillRetriever
        retrieved_skills_data = SkillRetriever.retrieve(description, "Derek")
        skill_context = "\n\n".join([item['content'] for item in retrieved_skills_data])

        user_prompt = f"""
USER INTENT / REQUEST:
{description}

RELEVANT ENGINEERING SKILLS:
{skill_context}

{serialize_graph_for_llm(graph)}
"""
        log("COGNITION", f"[DEREK] Prompt augmented with {len(retrieved_skills_data)} skills")
        return await MutationEngine.critique_and_stabilize(
            prompt=user_prompt,
            system_prompt=DEREK_PROMPT,
            branch=branch,
            intent=intent
        )
