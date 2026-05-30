# app/studio/architecture/ux_reasoner.py
"""
V4 GenxAI Studio — Phase GS-6: UXReasoner

UX synthesis reasoner. Ingests OntologyGraph, ApplicationGraph, InformationGraph,
DesignIntentGraph, and NavigationGraph to synthesize a UXBlueprint.
Performs strict role capability checks, cognitive focus overload checks, unreachable pages validation,
journey completion outcome validations, and decision complexity checks, failing loudly
and logging to SQLite Failure Recorder on violations.
"""

import json
from typing import Dict, Any, Optional, List, Set
from app.sentinel.cognition.ontology_graph import OntologyGraph
from app.studio.architecture.application_graph import ApplicationGraph
from app.studio.architecture.information_graph import InformationGraph
from app.studio.architecture.design_intent import DesignIntentGraph
from app.studio.architecture.navigation_graph import NavigationGraph
from app.studio.architecture.ux_blueprint import (
    UXBlueprint,
    STUDIO_UX_SYSTEM_NODE,
    STUDIO_UX_INTENT_NODE,
    STUDIO_USER_JOURNEY_NODE,
    STUDIO_TASK_FLOW_NODE,
    STUDIO_ATTENTION_FLOW_NODE,
    STUDIO_DECISION_POINT_NODE,
    STUDIO_OUTCOME_NODE
)
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.topology_validator import TopologyValidator
from app.llm.adapter import call_llm
from app.core.logging import log
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity
from app.llm.prompts.ux_reasoner import UX_REASONER_PROMPT

class UXReasoner:
    """
    UX reasoning synthesizer.
    Enforces deep cognitive contradiction checks and fails loudly.
    """

    @classmethod
    async def synthesize(
        cls,
        project_id: str,
        ontology_graph: OntologyGraph,
        application_graph: ApplicationGraph,
        information_graph: InformationGraph,
        design_intent_graph: DesignIntentGraph,
        navigation_graph: NavigationGraph
    ) -> UXBlueprint:
        """
        Synthesizes a UXBlueprint and enforces role, focus overload, outcome completion, and decision complexity constraints.
        Logs violations as COMPILATION_FAILURE to sentinel_memory.db and fails loudly.
        """
        log("UXReasoner", f"Starting UX Reasoning synthesis for project {project_id}")

        app_dump = application_graph.serialize()
        ont_dump = ontology_graph.serialize()
        info_dump = information_graph.serialize()
        intent_dump = design_intent_graph.serialize()
        nav_dump = navigation_graph.serialize()

        prompt = UX_REASONER_PROMPT.format(
            app_graph_json=json.dumps(app_dump, indent=2),
            ontology_graph_json=json.dumps(ont_dump, indent=2),
            info_graph_json=json.dumps(info_dump, indent=2),
            design_intent_graph_json=json.dumps(intent_dump, indent=2),
            navigation_graph_json=json.dumps(nav_dump, indent=2)
        )

        try:
            response = await call_llm(
                prompt=prompt,
                system_prompt="You are a strict, logical UX Reasoning Engine translating data structures into cognitive interaction blueprints.",
                temperature=0.1,
                max_tokens=16384
            )

            # Clean markdown JSON wrapping if present
            if response.strip().startswith("```json"):
                response = response.strip()[7:]
            if response.strip().endswith("```"):
                response = response.strip()[:-3]

            data = json.loads(response.strip())
            ux_blueprint = UXBlueprint(project_id=project_id)

            cls._populate_ux_blueprint(
                ux_blueprint,
                data,
                application_graph,
                information_graph,
                design_intent_graph
            )

            # Perform Step 4 contradiction and focus checks
            cls._assert_no_contradictions(
                ux_blueprint,
                ontology_graph,
                application_graph,
                information_graph,
                design_intent_graph,
                navigation_graph
            )

            # Validate structural legality using TopologyValidator
            validation_res = TopologyValidator.validate_graph(ux_blueprint)
            if not validation_res.passed:
                err_reasons = "; ".join(v.reason for v in validation_res.violations)
                raise ValueError(f"Topology Validation Failures: {err_reasons}")

            log("UXReasoner", f"Successfully synthesized UXBlueprint with {len(ux_blueprint.nodes)} nodes")
            return ux_blueprint

        except Exception as err:
            err_msg = f"LOUD FAILURE in UXReasoner for project {project_id}: {err}"
            log("UXReasoner", f"⚠️ {err_msg}")

            # Record compilation failure in failure_memory.db
            try:
                record_failure(
                    failure_type=FailureType.COMPILATION_FAILURE,
                    severity=Severity.ERROR,
                    reason=err_msg,
                    project_id=project_id,
                    component="UXReasoner"
                )
            except Exception as rec_err:
                log("UXReasoner", f"Failed to record failure: {rec_err}")

            raise ValueError(err_msg) from err

    @classmethod
    def _populate_ux_blueprint(
        cls,
        graph: UXBlueprint,
        data: Dict[str, Any],
        application_graph: ApplicationGraph,
        information_graph: InformationGraph,
        design_intent_graph: DesignIntentGraph
    ) -> None:
        """Parses LLM response and populates the UXBlueprint."""
        ux_data = data.get("ux_blueprint", {})

        # Pull DESIGN_INTENT_NODE root from design_intent_graph
        intent_root_id = f"design_intent_{graph.project_id}"
        if intent_root_id in design_intent_graph.nodes:
            intent_node = design_intent_graph.nodes[intent_root_id]
            graph.add_node(intent_root_id, intent_node.node_type, intent_node.properties)

        # Pull pages from application_graph
        for node_id, node in application_graph.nodes.items():
            if node.node_type == NodeType.PAGE_NODE:
                graph.add_node(node_id, node.node_type, node.properties)

        # Pull blocks from information_graph
        for node_id, node in information_graph.nodes.items():
            if str(node.node_type) == "CONTENT_BLOCK_NODE":
                graph.add_node(node_id, node.node_type, node.properties)

        # Pull page_contains_content edges from information_graph to preserve block containment
        for edge in information_graph.edges:
            if edge.relation == "page_contains_content":
                if edge.source_id in graph.nodes and edge.target_id in graph.nodes:
                    graph.add_edge(edge.source_id, edge.target_id, edge.relation)

        # Add UX_SYSTEM_NODE root node for causal traceability
        ux_root_id = f"ux_system_{graph.project_id}"
        graph.add_ux_node(
            ux_root_id,
            STUDIO_UX_SYSTEM_NODE,
            {"project_id": graph.project_id}
        )
        if intent_root_id in graph.nodes:
            graph.add_edge(ux_root_id, intent_root_id, "ux_system_derives_intent")

        # 1. Add UX Intents (UX_INTENT_NODE)
        intents_by_id = {}
        for intent in ux_data.get("intents", []):
            i_id = intent.get("id")
            name = intent.get("intent_name")
            if not i_id or not name:
                raise ValueError("UX Intent node is missing id or intent_name.")

            graph.add_ux_node(i_id, STUDIO_UX_INTENT_NODE, {"intent_name": name})
            graph.add_edge(ux_root_id, i_id, "ux_system_defines_intent")
            intents_by_id[i_id] = i_id

        # 2. Add User Journeys (USER_JOURNEY_NODE)
        for journey in ux_data.get("journeys", []):
            j_id = journey.get("id")
            parent_intent_id = journey.get("parent_intent_id")
            name = journey.get("journey_name")
            role = journey.get("target_role")
            objective = journey.get("objective")

            if not j_id or not parent_intent_id or not name or not role or not objective:
                raise ValueError("User Journey is missing id, parent_intent_id, journey_name, target_role, or objective.")

            graph.add_ux_node(
                j_id,
                STUDIO_USER_JOURNEY_NODE,
                {
                    "journey_name": name,
                    "target_role": role,
                    "objective": objective
                }
            )
            if parent_intent_id in graph.nodes:
                graph.add_edge(parent_intent_id, j_id, "ux_intent_defines_journey")

            # Add Task Flows
            for flow in journey.get("task_flows", []):
                f_id = flow.get("id")
                flow_name = flow.get("flow_name")
                action_type = flow.get("action_type")
                complexity = flow.get("complexity_level")
                page_id = flow.get("target_page_id")
                block_ids = flow.get("references_block_ids", [])
                parent_flow_id = flow.get("parent_flow_id")

                if not f_id or not flow_name or not action_type or not complexity or not page_id:
                    raise ValueError(f"Task flow {f_id} is missing flow_name, action_type, complexity_level, or target_page_id.")

                graph.add_ux_node(
                    f_id,
                    STUDIO_TASK_FLOW_NODE,
                    {
                        "flow_name": flow_name,
                        "action_type": action_type,
                        "complexity_level": complexity
                    }
                )
                graph.add_edge(j_id, f_id, "journey_contains_task_flow")

                if parent_flow_id and parent_flow_id in graph.nodes:
                    graph.add_edge(parent_flow_id, f_id, "task_flow_defines_step")

                if page_id in graph.nodes:
                    graph.add_edge(f_id, page_id, "task_flow_references_page")

                for bid in block_ids:
                    if bid in graph.nodes:
                        graph.add_edge(f_id, bid, "task_flow_references_block")

            # Add Decision Points
            for dp in journey.get("decision_points", []):
                dp_id = dp.get("id")
                title = dp.get("decision_title")
                expr = dp.get("condition_expression")
                parent_flow_id = dp.get("parent_flow_id")
                branches = dp.get("branches_to_flow_ids", [])

                if not dp_id or not title or not expr or not parent_flow_id:
                    raise ValueError("Decision Point is missing id, decision_title, condition_expression, or parent_flow_id.")

                graph.add_ux_node(
                    dp_id,
                    STUDIO_DECISION_POINT_NODE,
                    {
                        "decision_title": title,
                        "condition_expression": expr
                    }
                )
                if parent_flow_id in graph.nodes:
                    graph.add_edge(parent_flow_id, dp_id, "task_flow_contains_decision")

                for branch_id in branches:
                    if branch_id in graph.nodes:
                        graph.add_edge(dp_id, branch_id, "decision_point_branches_to")

            # Add Outcomes (OUTCOME_NODE)
            for out in journey.get("outcomes", []):
                out_id = out.get("id")
                out_name = out.get("outcome_name")
                classification = out.get("outcome_classification")
                parent_flow_id = out.get("parent_flow_id")

                if not out_id or not out_name or not classification or not parent_flow_id:
                    raise ValueError("Outcome is missing id, outcome_name, outcome_classification, or parent_flow_id.")

                graph.add_ux_node(
                    out_id,
                    STUDIO_OUTCOME_NODE,
                    {
                        "outcome_name": out_name,
                        "outcome_classification": classification
                    }
                )
                if parent_flow_id in graph.nodes:
                    graph.add_edge(parent_flow_id, out_id, "task_flow_leads_to_outcome")

        # 3. Add Attention Flows (ATTENTION_FLOW_NODE)
        attention_by_page = {}
        for att in ux_data.get("attention_flows", []):
            att_id = att.get("id")
            page_id = att.get("page_id")
            intensity = att.get("focus_intensity")
            trigger = att.get("interaction_trigger")
            block_id = att.get("content_block_id")
            parent_att_id = att.get("parent_attention_id")

            if not att_id or not page_id or not intensity or not trigger or not block_id:
                raise ValueError("Attention flow node is missing id, page_id, focus_intensity, interaction_trigger, or content_block_id.")

            graph.add_ux_node(
                att_id,
                STUDIO_ATTENTION_FLOW_NODE,
                {
                    "focus_intensity": intensity,
                    "interaction_trigger": trigger
                }
            )
            graph.add_edge(ux_root_id, att_id, "ux_system_defines_attention_flow")

            if block_id in graph.nodes:
                graph.add_edge(att_id, block_id, "attention_flow_references_block")

            if parent_att_id and parent_att_id in graph.nodes:
                graph.add_edge(parent_att_id, att_id, "attention_flow_links_blocks")

            attention_by_page.setdefault(page_id, []).append(att_id)

    @classmethod
    def _assert_no_contradictions(
        cls,
        graph: UXBlueprint,
        ontology_graph: OntologyGraph,
        application_graph: ApplicationGraph,
        information_graph: InformationGraph,
        design_intent_graph: DesignIntentGraph,
        navigation_graph: NavigationGraph
    ) -> None:
        """Enforces GS-6 contradiction checks and fails loudly."""
        # ── 1. Journey-Capability Role Alignment ──
        cls._validate_journey_role_alignments(graph, ontology_graph, information_graph)

        # ── 2. Cognitive Focus Overload ──
        cls._validate_cognitive_focus_overload(graph, design_intent_graph)

        # ── 3. Unreachable Page Invariant ──
        cls._validate_unreachable_journey_pages(graph, navigation_graph)

        # ── 4. Journey Completion Outcome Governance ──
        cls._validate_journey_completion(graph)

        # ── 5. Decision Point Fanout Governance ──
        cls._validate_decision_fanout(graph)

    @classmethod
    def _validate_journey_role_alignments(
        cls,
        graph: UXBlueprint,
        ontology_graph: OntologyGraph,
        information_graph: InformationGraph
    ) -> None:
        """Validates that a journey's target role has authorization for all capabilities referenced in its task flows."""
        # Build roles-to-capabilities map from ontology_graph
        # Map edge relations from ROLE_NODE to CAPABILITY_NODE
        role_caps = {}
        for edge in ontology_graph.edges:
            # Check edge between role and capability, typically role_has_capability or capability_supports_role
            if edge.relation in ("role_has_capability", "role_supports_capability"):
                role_caps.setdefault(edge.source_id, set()).add(edge.target_id)
            elif edge.relation == "capability_supports_role":
                role_caps.setdefault(edge.target_id, set()).add(edge.source_id)

        # Map block content to capability nodes
        block_caps = {}
        for edge in information_graph.edges:
            if edge.relation == "content_supports_capability":
                block_caps.setdefault(edge.source_id, set()).add(edge.target_id)

        for j_node in graph.nodes.values():
            if str(j_node.node_type) == "USER_JOURNEY_NODE":
                role_name = j_node.properties.get("target_role", "")
                
                # Retrieve flows in this journey
                flows = [
                    e.target_id for e in graph.edges
                    if e.relation == "journey_contains_task_flow" and e.source_id == j_node.node_id
                ]

                # Extract capabilities from blocks referenced in these flows
                for flow_id in flows:
                    referenced_blocks = [
                        e.target_id for e in graph.edges
                        if e.relation == "task_flow_references_block" and e.source_id == flow_id
                    ]

                    for bid in referenced_blocks:
                        caps = block_caps.get(bid, set())
                        
                        # Match role in ontology to check capabilities
                        # Simple name check matching role node names
                        matching_role_node = next(
                            (nid for nid, n in ontology_graph.nodes.items()
                             if n.node_type == NodeType.ROLE_NODE and n.properties.get("name") == role_name),
                            None
                        )
                        if matching_role_node:
                            allowed_caps = role_caps.get(matching_role_node, set())
                            for cap_id in caps:
                                if cap_id not in allowed_caps:
                                    cap_node = ontology_graph.nodes.get(cap_id)
                                    cap_name = cap_node.properties.get("name", cap_id) if cap_node else cap_id
                                    raise ValueError(
                                        f"JOURNEY_ROLE_ALIGNMENT_FAILURE: Journey '{j_node.properties.get('journey_name')}' "
                                        f"targets role '{role_name}', but flow step utilizes capability '{cap_name}' "
                                        f"which is not authorized for this role in the ontology graph."
                                    )

    @classmethod
    def _validate_cognitive_focus_overload(cls, graph: UXBlueprint, design_intent_graph: DesignIntentGraph) -> None:
        """Traverses attention flows for Single Focal Object pages, asserting sequence length <= 2 focus blocks."""
        # Find pages marked as Single Focal Object focus mode
        single_focal_pages = set()
        for node in design_intent_graph.nodes.values():
            if str(node.node_type) == "ATTENTION_MAP_NODE":
                if node.properties.get("focus_mode") == "Single Focal Object":
                    # Retrieve the page ID connected to this attention map
                    # Tracing GLOBAL_INTENT_NODE / PAGE_INTERACTION_NODE to find page_id
                    # Simple heuristic: attention maps reference page in node properties or parent structure
                    page_id = node.properties.get("page_id")
                    if page_id:
                        single_focal_pages.add(page_id)

        # Adjacency of attention link blocks
        att_links = {}
        for edge in graph.edges:
            if edge.relation == "attention_flow_links_blocks":
                att_links.setdefault(edge.source_id, []).append(edge.target_id)

        # Group attention flow nodes by page_id
        page_att_roots = {}
        for att_node in graph.nodes.values():
            if str(att_node.node_type) == "ATTENTION_FLOW_NODE":
                # Find content block connection to verify page containment
                block_ref = next(
                    (e.target_id for e in graph.edges
                     if e.relation == "attention_flow_references_block" and e.source_id == att_node.node_id),
                    None
                )
                if block_ref:
                    # Content block properties holds page_id or page edge
                    block_node = graph.nodes.get(block_ref)
                    if block_node:
                        page_id = next(
                            (e.source_id for e in graph.edges
                             if e.relation == "page_contains_content" and e.target_id == block_ref),
                            None
                        )
                        if page_id:
                            # Verify if it has parent link, otherwise it's a root of attention shifts
                            has_parent = any(
                                e.relation == "attention_flow_links_blocks" and e.target_id == att_node.node_id
                                for e in graph.edges
                            )
                            if not has_parent:
                                page_att_roots[page_id] = att_node.node_id

        # Validate path length for each single focal page
        for page_id in single_focal_pages:
            root_att = page_att_roots.get(page_id)
            if root_att:
                # Traverse path length
                def get_max_path_length(node_id: str) -> int:
                    if node_id not in att_links:
                        return 1
                    max_l = 0
                    for child in att_links[node_id]:
                        max_l = max(max_l, get_max_path_length(child))
                    return max_l + 1

                length = get_max_path_length(root_att)
                # Max 2 shifts (total path length <= 2 nodes)
                if length > 2:
                    raise ValueError(
                        f"COGNITIVE_OVERLOAD_FAILURE: Page '{page_id}' is configured with Sophia's 'Single Focal Object' "
                        f"focus limits, but has {length} attention focus block shifts, violating cognitive scanning bounds."
                    )

    @classmethod
    def _validate_unreachable_journey_pages(cls, graph: UXBlueprint, navigation_graph: NavigationGraph) -> None:
        """Asserts that every page referenced by task flows is reachable in the NavigationGraph."""
        # Find all reachable page IDs in navigation_graph
        reachable_pages = set()
        for edge in navigation_graph.edges:
            if edge.relation == "route_targets_page":
                reachable_pages.add(edge.target_id)

        for flow_node in graph.nodes.values():
            if str(flow_node.node_type) == "TASK_FLOW_NODE":
                page_ref = next(
                    (e.target_id for e in graph.edges
                     if e.relation == "task_flow_references_page" and e.source_id == flow_node.node_id),
                    None
                )
                if page_ref and page_ref not in reachable_pages:
                    raise ValueError(
                        f"UNREACHABLE_JOURNEY_STEP_FAILURE: Task flow step '{flow_node.properties.get('flow_name')}' "
                        f"references page '{page_ref}' which is orphaned or completely unreachable in the navigation graph."
                    )

    @classmethod
    def _validate_journey_completion(cls, graph: UXBlueprint) -> None:
        """Asserts that every USER_JOURNEY_NODE terminates in at least one dedicated OUTCOME_NODE."""
        for j_node in graph.nodes.values():
            if str(j_node.node_type) == "USER_JOURNEY_NODE":
                # Find task flows inside this journey
                journey_flows = [
                    e.target_id for e in graph.edges
                    if e.relation == "journey_contains_task_flow" and e.source_id == j_node.node_id
                ]

                # Check if at least one flow leads to an outcome node
                has_terminal_outcome = False
                for flow_id in journey_flows:
                    outcome_links = [
                        e.target_id for e in graph.edges
                        if e.relation == "task_flow_leads_to_outcome" and e.source_id == flow_id
                    ]
                    for oid in outcome_links:
                        out_node = graph.nodes.get(oid)
                        if out_node and str(out_node.node_type) == "OUTCOME_NODE":
                            classification = out_node.properties.get("outcome_classification")
                            if classification in ("Success", "Failure", "Abandonment", "Escalation", "Retry"):
                                has_terminal_outcome = True
                                break

                if not has_terminal_outcome:
                    raise ValueError(
                        f"JOURNEY_COMPLETION_FAILURE: User journey '{j_node.properties.get('journey_name')}' "
                        f"does not terminate in any defined success, failure, or abandonment OUTCOME_NODE."
                    )

    @classmethod
    def _validate_decision_fanout(cls, graph: UXBlueprint) -> None:
        """Asserts that each DECISION_POINT_NODE has outbound branches <= 5."""
        for dp_node in graph.nodes.values():
            if str(dp_node.node_type) == "DECISION_POINT_NODE":
                fanout = sum(
                    1 for e in graph.edges
                    if e.relation == "decision_point_branches_to" and e.source_id == dp_node.node_id
                )
                if fanout > 5:
                    raise ValueError(
                        f"DECISION_COMPLEXITY_FAILURE: Decision point '{dp_node.properties.get('decision_title')}' "
                        f"branches out to {fanout} task flow directions, exceeding the maximum allowed scanning limit of 5 options."
                    )
