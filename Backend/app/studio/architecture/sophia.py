# app/studio/architecture/sophia.py
"""
V4 GenxAI Studio — Phase GS-3: Sophia Design Faculty

Cognitive design reasoning engine. Analyzes the ApplicationGraph and InformationGraph
against Sentinel product schemas to synthesize a DesignIntentGraph carrying visual temperature,
semantic color intent, interaction models, and attention maps.
Fails loudly and logs to sentinel_memory.db on structural or cognitive contradictions.
"""

import json
from typing import Dict, Any, Optional, List
from app.sentinel.cognition.ontology_graph import OntologyGraph
from app.studio.architecture.application_graph import ApplicationGraph
from app.studio.architecture.information_graph import InformationGraph
from app.studio.architecture.design_intent import (
    DesignIntentGraph,
    STUDIO_DESIGN_INTENT_NODE,
    STUDIO_GLOBAL_INTENT_NODE,
    STUDIO_PAGE_INTERACTION_NODE,
    STUDIO_ATTENTION_MAP_NODE
)
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.topology_validator import TopologyValidator
from app.llm.adapter import call_llm
from app.core.logging import log
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity
from app.llm.prompts.sophia import SOPHIA_PROMPT

class Sophia:
    """
    Cognitive design reasoning faculty.
    Validates structural and design constraints, failing loudly on contradictions.
    """

    @classmethod
    async def synthesize(
        cls,
        project_id: str,
        ontology_graph: OntologyGraph,
        application_graph: ApplicationGraph,
        information_graph: InformationGraph
    ) -> DesignIntentGraph:
        """
        Synthesizes a DesignIntentGraph and performs strict design contradiction checks.
        Fails loudly and records failures to SQLite failure memory on contradiction or mismatch.
        """
        log("Sophia", f"Starting Design Intent synthesis for project {project_id}")

        app_dump = application_graph.serialize()
        ont_dump = ontology_graph.serialize()
        info_dump = information_graph.serialize()

        prompt = SOPHIA_PROMPT.format(
            app_graph_json=json.dumps(app_dump, indent=2),
            ontology_graph_json=json.dumps(ont_dump, indent=2),
            info_graph_json=json.dumps(info_dump, indent=2)
        )

        try:
            response = await call_llm(
                prompt=prompt,
                system_prompt="You are Sophia, a strict Cognitive UX Architect mapping layouts into cognitive intents.",
                temperature=0.1,
                max_tokens=16384
            )

            # Clean markdown JSON wrapping if present
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())
            intent_graph = DesignIntentGraph(project_id=project_id)
            
            cls._populate_design_intent(
                intent_graph,
                data,
                application_graph,
                information_graph
            )

            # Perform Step 4: Cognitive Contradiction Check
            cls._assert_no_contradictions(intent_graph, information_graph)

            # Validate structural legality using TopologyValidator
            validation_res = TopologyValidator.validate_graph(intent_graph)
            if not validation_res.passed:
                err_reasons = "; ".join(v.reason for v in validation_res.violations)
                raise ValueError(f"Topology Validation Failures: {err_reasons}")

            log("Sophia", f"Successfully synthesized DesignIntentGraph with {len(intent_graph.nodes)} nodes")
            return intent_graph

        except Exception as err:
            err_msg = f"LOUD FAILURE in Sophia for project {project_id}: {err}"
            log("Sophia", f"⚠️ {err_msg}")
            
            # Record cognitive failure in failure_memory.db
            try:
                record_failure(
                    failure_type=FailureType.COMPILATION_FAILURE,
                    severity=Severity.ERROR,
                    reason=err_msg,
                    project_id=project_id,
                    component="Sophia"
                )
            except Exception as rec_err:
                log("Sophia", f"Failed to record failure: {rec_err}")
                
            raise ValueError(err_msg) from err

    @classmethod
    def _populate_design_intent(
        cls,
        graph: DesignIntentGraph,
        data: Dict[str, Any],
        application_graph: ApplicationGraph,
        information_graph: InformationGraph
    ) -> None:
        """Parses Sophia's JSON response and populates the DesignIntentGraph."""
        intent_data = data.get("design_intent", {})
        
        # 1. Pull pages and content blocks from parent graphs to allow edge links
        for node_id, node in application_graph.nodes.items():
            if node.node_type == NodeType.PAGE_NODE:
                graph.add_node(node_id, node.node_type, node.properties)
        for node_id, node in information_graph.nodes.items():
            if str(node.node_type) in ("CONTENT_BLOCK_NODE", "DATA_FIELD_NODE"):
                graph.add_node(node_id, node.node_type, node.properties)

        # Find workspace ID from application_graph
        workspace_id = next(
            (nid for nid, node in application_graph.nodes.items() if node.node_type == NodeType.WORKSPACE_NODE),
            "workspace_root"
        )
        if workspace_id not in graph.nodes and workspace_id != "workspace_root":
            workspace_node = application_graph.nodes[workspace_id]
            graph.add_node(workspace_id, workspace_node.node_type, workspace_node.properties)

        # 2. Add DESIGN_INTENT_NODE root node for causal traceability
        root_id = f"design_intent_{graph.project_id}"
        graph.add_design_node(
            root_id,
            STUDIO_DESIGN_INTENT_NODE,
            {
                "reasoning_rationale": intent_data.get("reasoning_rationale", "Cognitive layout reasoner"),
                "design_metaphor": intent_data.get("design_metaphor", "Abstract design intent")
            }
        )
        if workspace_id in graph.nodes:
            graph.add_edge(workspace_id, root_id, "workspace_uses_design_intent")

        # 3. Add GLOBAL_INTENT_NODE
        global_data = intent_data.get("global", {})
        global_id = f"global_intent_{graph.project_id}"
        graph.add_design_node(
            global_id,
            STUDIO_GLOBAL_INTENT_NODE,
            {
                "visual_temperature": global_data.get("visual_temperature"),
                "color_intent": global_data.get("color_intent"),
                "complexity_preference": global_data.get("complexity_preference"),
                "collaboration_mode": global_data.get("collaboration_mode")
            }
        )
        graph.add_edge(root_id, global_id, "intent_defines_global")

        # 4. Add Page and Attention Nodes
        for page in intent_data.get("pages", []):
            page_id = page.get("page_id")
            if page_id not in graph.nodes:
                continue

            # Add PAGE_INTERACTION_NODE
            interaction_id = f"interaction_{page_id}"
            graph.add_design_node(
                interaction_id,
                STUDIO_PAGE_INTERACTION_NODE,
                {
                    "interaction_model": page.get("interaction_model"),
                    "focus_mode": page.get("focus_mode"),
                    "attention_ranking": page.get("attention_ranking", [])
                }
            )
            graph.add_edge(global_id, interaction_id, "global_defines_page_interaction")
            graph.add_edge(page_id, interaction_id, "page_uses_interaction")

            # Add ATTENTION_MAP_NODEs for Content Blocks
            for block in page.get("content_blocks", []):
                block_id = block.get("id")
                if block_id not in graph.nodes:
                    continue

                # Enforce Step 4: Strict focus anchor ID checks (must reference valid InformationGraph node ID)
                focus_anchors = block.get("focus_anchors", [])
                for fa_id in focus_anchors:
                    if fa_id not in information_graph.nodes:
                        raise ValueError(
                            f"Focus anchor ID Mismatch: Anchor '{fa_id}' in block '{block_id}' "
                            f"does not exist in the InformationGraph."
                        )

                attention_id = f"attention_{block_id}"
                graph.add_design_node(
                    attention_id,
                    STUDIO_ATTENTION_MAP_NODE,
                    {
                        "importance_score": block.get("importance_score"),
                        "attention_rank": block.get("attention_rank"),
                        "information_density": block.get("information_density"),
                        "focus_anchors": focus_anchors,
                        "visual_groups": block.get("visual_groups", [])
                    }
                )
                graph.add_edge(interaction_id, attention_id, "page_defines_attention_map")
                graph.add_edge(block_id, attention_id, "content_uses_attention_map")

    @classmethod
    def _assert_no_contradictions(cls, intent_graph: DesignIntentGraph, information_graph: InformationGraph) -> None:
        """
        Enforce Step 4: Design Contradiction Detection.
        Blocks layouts that are structurally legal but cognitively nonsensical.
        """
        # Find global intent properties
        global_node = next(
            (node for node in intent_graph.nodes.values() if str(node.node_type) == "GLOBAL_INTENT_NODE"),
            None
        )
        visual_temp = global_node.properties.get("visual_temperature") if global_node else None

        # Check contradictions for each page and content block
        for interaction_node in intent_graph.nodes.values():
            if str(interaction_node.node_type) == "PAGE_INTERACTION_NODE":
                interaction_model = interaction_node.properties.get("interaction_model")
                focus_mode = interaction_node.properties.get("focus_mode")
                attention_ranking = interaction_node.properties.get("attention_ranking", [])

                # ⚠️ Contradiction 1: Spacious Content Overflow
                # Spacious layouts or low complexity preferences cannot hold an excessive number of content blocks on a page.
                if visual_temp == "Conversational" or focus_mode == "Single Focal Object":
                    if len(attention_ranking) > 8:
                        raise ValueError(
                            f"DESIGN_CONTRADICTION_FAILURE: Spacious focus mode ('Single Focal Object' / 'Conversational') "
                            f"contains {len(attention_ranking)} blocks, exceeding the maximum allowed threshold of 8 blocks."
                        )

                # ⚠️ Contradiction 2: Operational Focus Mismatch
                # An Operational workspace is multi-modal, highly parallel, and maximizes utility.
                # Restricting it to a "Single Focal Object" is highly contradictory.
                if interaction_model == "Operational" and focus_mode == "Single Focal Object":
                    raise ValueError(
                        f"DESIGN_CONTRADICTION_FAILURE: Page specifies an 'Operational' interaction model "
                        f"but restricts focus to a 'Single Focal Object' instead of 'Multi-Modal Overview'."
                    )

        # ⚠️ Contradiction 3: Dense Focus Mismatch
        # A block containing dense analytical data cannot be placed inside a page with a laser-focused single focal object layout.
        for attention_node in intent_graph.nodes.values():
            if str(attention_node.node_type) == "ATTENTION_MAP_NODE":
                density = attention_node.properties.get("information_density")
                block_id = attention_node.node_id.replace("attention_", "")
                
                # Find the page containing this block to verify its focus mode
                for edge in intent_graph.edges:
                    if edge.relation == "page_defines_attention_map" and edge.target_id == attention_node.node_id:
                        interaction_node = intent_graph.nodes[edge.source_id]
                        focus_mode = interaction_node.properties.get("focus_mode")
                        
                        if density == "High" and focus_mode == "Single Focal Object":
                            raise ValueError(
                                f"DESIGN_CONTRADICTION_FAILURE: Content block '{block_id}' specifies 'High' "
                                f"information density, which contradicts the page's 'Single Focal Object' focus mode."
                            )
