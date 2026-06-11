# app/studio/faculties/victoria.py
from typing import Any, List

from app.sentinel.cognition.patch_ir import PatchIR
from app.sentinel.cognition.branch import BranchState
from app.llm.prompts import VICTORIA_PROMPT
from app.studio.mutation.mutation_engine import MutationEngine
from app.studio.faculties.utils import serialize_graph_for_llm
from app.core.logging import log


class VictoriaUIFaculty:
    """
    Victoria: UI Faculty
    Suggests component layouts, navigation routes, and state bindings.
    """

    @staticmethod
    async def propose_mutations(
        branch: BranchState,
        description: str,
        intent: Any = None,
    ) -> List[PatchIR]:
        log("COGNITION", "Victoria UI Faculty analyzing intentions...")
        graph = branch.topology_graph

        from app.sentinel.skills.skill_retriever import SkillRetriever
        retrieved_skills_data = SkillRetriever.retrieve(description, "Victoria")
        skill_context = "\n\n".join([item['content'] for item in retrieved_skills_data])

        user_prompt = f"""
USER INTENT / REQUEST:
{description}

RELEVANT ENGINEERING SKILLS:
{skill_context}

{serialize_graph_for_llm(graph)}
"""
        log("COGNITION", f"[VICTORIA] Prompt augmented with {len(retrieved_skills_data)} skills")
        patches = await MutationEngine.critique_and_stabilize(
            prompt=user_prompt,
            system_prompt=VICTORIA_PROMPT,
            branch=branch,
            intent=intent
        )
        # [INSTRUMENT-A] Measure Victoria's output immediately after stabilization
        ui_patches = [p for p in patches if p.node_data and p.node_data.get("node_type") == "UI_NODE"]
        log("COGNITION", f"[VICTORIA-INSTRUMENT] raw_patches={len(patches)} | ui_node_patches={len(ui_patches)} | patch_ids={[p.patch_id for p in patches[:5]]}")
        return patches
