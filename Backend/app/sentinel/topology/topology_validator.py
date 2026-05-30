# app/topology/topology_validator.py
"""
V4 Structural Physics Engine — Stage 2: Canonical Topology Engine

Provides deterministic graph mathematics, dependency legality checks,
and integrity validation for ProjectTopologyGraph. No cognition allowed here.
"""

from typing import Dict, List, Set, Tuple, Optional
from pydantic import BaseModel, Field
from app.sentinel.topology.node_types import NodeType, NodeOntology
from app.sentinel.topology.project_graph import ProjectTopologyGraph, TopologyNode, TopologyEdge

class ValidationViolation(BaseModel):
    rule: str
    node_id: Optional[str] = None
    target_id: Optional[str] = None
    reason: str


class TopologyValidationResult(BaseModel):
    passed: bool
    violations: List[ValidationViolation] = Field(default_factory=list)


class TopologyValidator:
    """
    Purely deterministic structural physics engine.
    Applies graph mathematical invariants to verify topology sanity.
    """

    @classmethod
    def validate_graph(cls, graph: ProjectTopologyGraph) -> TopologyValidationResult:
        """
        Validate all structural constraints, import legality, and DAG safety.
        Returns a validation result containing any rules broken.
        """
        violations: List[ValidationViolation] = []

        # ── 1. Validate Node Integrity Hashes ─────────────────
        for node_id, node in graph.nodes.items():
            expected_hash = node.calculate_hash()
            if node.integrity_hash != expected_hash:
                violations.append(
                    ValidationViolation(
                        rule="NODE_CORRUPTION_DETECTED",
                        node_id=node_id,
                        reason=f"Node integrity hash mismatch. Graph indicates tampering or corruption."
                    )
                )

        # ── 2. Validate Edge Reference Legality ───────────────
        for edge in graph.edges:
            if edge.source_id not in graph.nodes:
                violations.append(
                    ValidationViolation(
                        rule="DANGLING_EDGE_SOURCE",
                        node_id=edge.source_id,
                        reason="Edge source node does not exist in graph."
                    )
                )
            if edge.target_id not in graph.nodes:
                violations.append(
                    ValidationViolation(
                        rule="DANGLING_EDGE_TARGET",
                        node_id=edge.target_id,
                        reason=f"Edge target node '{edge.target_id}' does not exist in graph."
                    )
                )

        if violations:
            # Return early if basic references are broken to avoid KeyError in deeper checks
            return TopologyValidationResult(passed=False, violations=violations)

        # ── 3. Cycle Detection (DAG enforcement) ─────────────
        # Some relations (depends_on, imports) MUST be acyclic
        acyclic_relations = [
            "depends_on", "imports", "governs",
            "experience_contains_goal",
            "goal_contains_journey",
            "journey_contains_flow",
            "flow_contains_screen",
            "screen_contains_action",
            "workspace_contains_page",
            "page_contains_feature",
            "page_uses_layout",
            "block_references_entity",
            "content_supports_capability",
            "workspace_uses_design_intent",
            "intent_defines_global",
            "global_defines_page_interaction",
            "page_defines_attention_map",
            "design_system_derives_intent",
            "system_defines_color_char",
            "system_defines_typography",
            "system_defines_spacing",
            "system_defines_motion",
            "system_defines_rules",
            "navigation_derives_intent",
            "system_defines_routing_model",
            "routing_model_contains_route",
            "route_targets_page",
            "route_defines_workflow_step",
            "system_defines_menu",
            "menu_contains_item",
            "nav_item_redirects_to",
            "page_uses_nav_menu",
            "ux_system_derives_intent",
            "ux_system_defines_intent",
            "ux_intent_defines_journey",
            "journey_contains_task_flow",
            "task_flow_defines_step",
            "task_flow_contains_decision",
            "decision_point_branches_to",
            "task_flow_leads_to_outcome",
            "task_flow_references_page",
            "task_flow_references_block",
            "ux_system_defines_attention_flow",
            "attention_flow_links_blocks",
            "attention_flow_references_block",
            "component_system_derives_intent",
            "component_system_defines_layout",
            "layout_contains_component",
            "layout_contains_layout",
            "component_contains_component",
            "component_defines_state",
            "component_defines_property",
            "component_references_block",
            "component_supports_flow",
            "interaction_system_derives_intent",
            "interaction_system_defines_intent",
            "interaction_intent_contains_loop",
            "interaction_loop_contains_trigger",
            "interaction_loop_contains_mutation",
            "transition_mutates_state",
            "trigger_references_component",
            "mutation_targets_component",
            "responsive_system_derives_intent",
            "responsive_system_defines_intent",
            "responsive_intent_defines_viewport",
            "viewport_defines_attention",
            "viewport_defines_density",
            "viewport_defines_cost",
            "viewport_defines_priority",
            "viewport_defines_adaptation",
            "viewport_defines_override",
            "override_targets_layout",
            "override_targets_component",
            "priority_targets_component",
            "priority_targets_layout",
            "design_memory_derives_intent",
            "critique_references_record",
            "feedback_references_record",
            "memory_contains_record",
            "memory_defines_learning",
            "learning_derives_record"
        ]
        for rel in acyclic_relations:
            has_cycle, cycle_path = cls._detect_cycle(graph, rel)
            if has_cycle:
                violations.append(
                    ValidationViolation(
                        rule=f"CYCLIC_{rel.upper()}_RELATION",
                        reason=f"Illegal cyclic structure detected in relationship '{rel}': {' -> '.join(cycle_path)}"
                    )
                )

        # ── 4. Edge Legality and Connection Rules ────────────
        # Example rule: UI_NODE cannot directly edge to SCHEMA_NODE (must use STATE_NODE or API_NODE)
        for edge in graph.edges:
            source_node = graph.nodes[edge.source_id]
            target_node = graph.nodes[edge.target_id]

            if source_node.node_type == NodeType.UI_NODE and target_node.node_type == NodeType.SCHEMA_NODE:
                violations.append(
                    ValidationViolation(
                        rule="ILLEGAL_UI_TO_SCHEMA_EDGE",
                        node_id=edge.source_id,
                        target_id=edge.target_id,
                        reason="UI Component cannot directly target a Database Schema. Must bind via a STATE_NODE, UI_STATE_NODE, or DATA_STATE_NODE."
                    )
                )
                
            # Phase 7: Experience Graph Hierarchy Checks
            if edge.relation == "experience_contains_goal" and (source_node.node_type != NodeType.EXPERIENCE_NODE or target_node.node_type != NodeType.GOAL_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_EXPERIENCE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="experience_contains_goal must be from EXPERIENCE_NODE to GOAL_NODE"))
            if edge.relation == "goal_contains_journey" and (source_node.node_type != NodeType.GOAL_NODE or target_node.node_type != NodeType.JOURNEY_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_EXPERIENCE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="goal_contains_journey must be from GOAL_NODE to JOURNEY_NODE"))
            if edge.relation == "journey_contains_flow" and (source_node.node_type != NodeType.JOURNEY_NODE or target_node.node_type != NodeType.FLOW_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_EXPERIENCE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="journey_contains_flow must be from JOURNEY_NODE to FLOW_NODE"))
            if edge.relation == "flow_contains_screen" and (source_node.node_type != NodeType.FLOW_NODE or target_node.node_type != NodeType.SCREEN_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_EXPERIENCE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="flow_contains_screen must be from FLOW_NODE to SCREEN_NODE"))
            if edge.relation == "screen_contains_action" and (source_node.node_type != NodeType.SCREEN_NODE or target_node.node_type != NodeType.ACTION_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_EXPERIENCE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="screen_contains_action must be from SCREEN_NODE to ACTION_NODE"))

            # Phase GS-1: Application Architect Edge Validation
            if edge.relation == "workspace_contains_page" and (source_node.node_type != NodeType.WORKSPACE_NODE or target_node.node_type != NodeType.PAGE_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_APPLICATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="workspace_contains_page must be from WORKSPACE_NODE to PAGE_NODE"))
            if edge.relation == "page_contains_feature" and (source_node.node_type != NodeType.PAGE_NODE or target_node.node_type != NodeType.FEATURE_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_APPLICATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="page_contains_feature must be from PAGE_NODE to FEATURE_NODE"))
            if edge.relation == "page_uses_layout" and (source_node.node_type not in (NodeType.WORKSPACE_NODE, NodeType.PAGE_NODE) or target_node.node_type != NodeType.NAV_LAYOUT_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_APPLICATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="page_uses_layout must be from WORKSPACE_NODE/PAGE_NODE to NAV_LAYOUT_NODE"))
            if edge.relation == "page_relates_to" and (source_node.node_type != NodeType.PAGE_NODE or target_node.node_type != NodeType.PAGE_NODE):
                violations.append(ValidationViolation(rule="ILLEGAL_APPLICATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="page_relates_to must be from PAGE_NODE to PAGE_NODE"))

            # Phase GS-2: Information Architecture Edge Validation
            source_type = source_node.node_type.value if hasattr(source_node.node_type, "value") else str(source_node.node_type)
            target_type = target_node.node_type.value if hasattr(target_node.node_type, "value") else str(target_node.node_type)

            if edge.relation == "page_contains_content" and (source_type != "PAGE_NODE" or target_type != "CONTENT_BLOCK_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INFORMATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="page_contains_content must be from PAGE_NODE to CONTENT_BLOCK_NODE"))
            if edge.relation == "content_contains_field" and (source_type != "CONTENT_BLOCK_NODE" or target_type != "DATA_FIELD_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INFORMATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="content_contains_field must be from CONTENT_BLOCK_NODE to DATA_FIELD_NODE"))
            if edge.relation == "field_references_entity" and (source_type != "DATA_FIELD_NODE" or target_type not in ("ENTITY_NODE", "ROLE_NODE")):
                violations.append(ValidationViolation(rule="ILLEGAL_INFORMATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="field_references_entity must be from DATA_FIELD_NODE to ENTITY_NODE/ROLE_NODE"))
            if edge.relation == "block_references_entity" and (source_type != "CONTENT_BLOCK_NODE" or target_type not in ("ENTITY_NODE", "ROLE_NODE")):
                violations.append(ValidationViolation(rule="ILLEGAL_INFORMATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="block_references_entity must be from CONTENT_BLOCK_NODE to ENTITY_NODE/ROLE_NODE"))
            if edge.relation == "content_supports_capability" and (source_type != "CONTENT_BLOCK_NODE" or target_type not in ("CAPABILITY_NODE", "ONTOLOGY_WORKFLOW_NODE")):
                violations.append(ValidationViolation(rule="ILLEGAL_INFORMATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="content_supports_capability must be from CONTENT_BLOCK_NODE to CAPABILITY_NODE/ONTOLOGY_WORKFLOW_NODE"))

            # Phase GS-3: Design Intent Edge Validation
            if edge.relation == "workspace_uses_design_intent" and (source_type != "WORKSPACE_NODE" or target_type != "DESIGN_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_DESIGN_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="workspace_uses_design_intent must be from WORKSPACE_NODE to DESIGN_INTENT_NODE"))
            if edge.relation == "intent_defines_global" and (source_type != "DESIGN_INTENT_NODE" or target_type != "GLOBAL_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_DESIGN_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="intent_defines_global must be from DESIGN_INTENT_NODE to GLOBAL_INTENT_NODE"))
            if edge.relation == "global_defines_page_interaction" and (source_type != "GLOBAL_INTENT_NODE" or target_type != "PAGE_INTERACTION_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_DESIGN_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="global_defines_page_interaction must be from GLOBAL_INTENT_NODE to PAGE_INTERACTION_NODE"))
            if edge.relation == "page_defines_attention_map" and (source_type != "PAGE_INTERACTION_NODE" or target_type != "ATTENTION_MAP_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_DESIGN_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="page_defines_attention_map must be from PAGE_INTERACTION_NODE to ATTENTION_MAP_NODE"))

            # Phase GS-4: Design System Edge Validation
            if edge.relation == "design_system_derives_intent" and (source_type != "DESIGN_SYSTEM_NODE" or target_type != "DESIGN_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_SYSTEM_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="design_system_derives_intent must be from DESIGN_SYSTEM_NODE to DESIGN_INTENT_NODE"))
            if edge.relation == "system_defines_color_char" and (source_type != "DESIGN_SYSTEM_NODE" or target_type != "COLOR_CHARACTERISTICS_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_SYSTEM_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="system_defines_color_char must be from DESIGN_SYSTEM_NODE to COLOR_CHARACTERISTICS_NODE"))
            if edge.relation == "system_defines_typography" and (source_type != "DESIGN_SYSTEM_NODE" or target_type != "TYPOGRAPHY_TOKEN_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_SYSTEM_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="system_defines_typography must be from DESIGN_SYSTEM_NODE to TYPOGRAPHY_TOKEN_NODE"))
            if edge.relation == "system_defines_spacing" and (source_type != "DESIGN_SYSTEM_NODE" or target_type != "SPACING_TOKEN_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_SYSTEM_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="system_defines_spacing must be from DESIGN_SYSTEM_NODE to SPACING_TOKEN_NODE"))
            if edge.relation == "system_defines_motion" and (source_type != "DESIGN_SYSTEM_NODE" or target_type != "MOTION_TOKEN_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_SYSTEM_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="system_defines_motion must be from DESIGN_SYSTEM_NODE to MOTION_TOKEN_NODE"))
            if edge.relation == "system_defines_rules" and (source_type != "DESIGN_SYSTEM_NODE" or target_type != "COMPONENT_RULES_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_SYSTEM_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="system_defines_rules must be from DESIGN_SYSTEM_NODE to COMPONENT_RULES_NODE"))

            # Phase GS-5: Navigation Edge Validation
            if edge.relation == "navigation_derives_intent" and (source_type != "NAVIGATION_SYSTEM_NODE" or target_type != "DESIGN_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="navigation_derives_intent must be from NAVIGATION_SYSTEM_NODE to DESIGN_INTENT_NODE"))
            if edge.relation == "system_defines_routing_model" and (source_type != "NAVIGATION_SYSTEM_NODE" or target_type != "ROUTING_MODEL_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="system_defines_routing_model must be from NAVIGATION_SYSTEM_NODE to ROUTING_MODEL_NODE"))
            if edge.relation == "routing_model_contains_route" and (source_type != "ROUTING_MODEL_NODE" or target_type not in ("ROUTE_NODE", "WORKFLOW_ROUTE_NODE")):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="routing_model_contains_route must be from ROUTING_MODEL_NODE to ROUTE_NODE/WORKFLOW_ROUTE_NODE"))
            if edge.relation == "route_targets_page" and (source_type not in ("ROUTE_NODE", "WORKFLOW_ROUTE_NODE") or target_type != "PAGE_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="route_targets_page must be from ROUTE_NODE/WORKFLOW_ROUTE_NODE to PAGE_NODE"))
            if edge.relation == "route_defines_workflow_step" and (source_type not in ("ROUTE_NODE", "WORKFLOW_ROUTE_NODE") or target_type != "WORKFLOW_ROUTE_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="route_defines_workflow_step must be from ROUTE_NODE/WORKFLOW_ROUTE_NODE to WORKFLOW_ROUTE_NODE"))
            if edge.relation == "system_defines_menu" and (source_type != "NAVIGATION_SYSTEM_NODE" or target_type != "NAV_MENU_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="system_defines_menu must be from NAVIGATION_SYSTEM_NODE to NAV_MENU_NODE"))
            if edge.relation == "menu_contains_item" and (source_type != "NAV_MENU_NODE" or target_type != "NAV_ITEM_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="menu_contains_item must be from NAV_MENU_NODE to NAV_ITEM_NODE"))
            if edge.relation == "nav_item_redirects_to" and (source_type != "NAV_ITEM_NODE" or target_type not in ("ROUTE_NODE", "WORKFLOW_ROUTE_NODE")):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="nav_item_redirects_to must be from NAV_ITEM_NODE to ROUTE_NODE/WORKFLOW_ROUTE_NODE"))
            if edge.relation == "page_uses_nav_menu" and (source_type != "PAGE_NODE" or target_type != "NAV_MENU_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_NAVIGATION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="page_uses_nav_menu must be from PAGE_NODE to NAV_MENU_NODE"))

            # Phase GS-6: UX Blueprint Edge Validation
            if edge.relation == "ux_system_derives_intent" and (source_type != "UX_SYSTEM_NODE" or target_type != "DESIGN_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="ux_system_derives_intent must be from UX_SYSTEM_NODE to DESIGN_INTENT_NODE"))
            if edge.relation == "ux_system_defines_intent" and (source_type != "UX_SYSTEM_NODE" or target_type != "UX_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="ux_system_defines_intent must be from UX_SYSTEM_NODE to UX_INTENT_NODE"))
            if edge.relation == "ux_intent_defines_journey" and (source_type != "UX_INTENT_NODE" or target_type != "USER_JOURNEY_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="ux_intent_defines_journey must be from UX_INTENT_NODE to USER_JOURNEY_NODE"))
            if edge.relation == "journey_contains_task_flow" and (source_type != "USER_JOURNEY_NODE" or target_type != "TASK_FLOW_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="journey_contains_task_flow must be from USER_JOURNEY_NODE to TASK_FLOW_NODE"))
            if edge.relation == "task_flow_defines_step" and (source_type != "TASK_FLOW_NODE" or target_type != "TASK_FLOW_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="task_flow_defines_step must be from TASK_FLOW_NODE to TASK_FLOW_NODE"))
            if edge.relation == "task_flow_contains_decision" and (source_type != "TASK_FLOW_NODE" or target_type != "DECISION_POINT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="task_flow_contains_decision must be from TASK_FLOW_NODE to DECISION_POINT_NODE"))
            if edge.relation == "decision_point_branches_to" and (source_type != "DECISION_POINT_NODE" or target_type != "TASK_FLOW_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="decision_point_branches_to must be from DECISION_POINT_NODE to TASK_FLOW_NODE"))
            if edge.relation == "task_flow_leads_to_outcome" and (source_type != "TASK_FLOW_NODE" or target_type != "OUTCOME_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="task_flow_leads_to_outcome must be from TASK_FLOW_NODE to OUTCOME_NODE"))
            if edge.relation == "task_flow_references_page" and (source_type != "TASK_FLOW_NODE" or target_type != "PAGE_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="task_flow_references_page must be from TASK_FLOW_NODE to PAGE_NODE"))
            if edge.relation == "task_flow_references_block" and (source_type != "TASK_FLOW_NODE" or target_type != "CONTENT_BLOCK_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="task_flow_references_block must be from TASK_FLOW_NODE to CONTENT_BLOCK_NODE"))
            if edge.relation == "ux_system_defines_attention_flow" and (source_type != "UX_SYSTEM_NODE" or target_type != "ATTENTION_FLOW_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="ux_system_defines_attention_flow must be from UX_SYSTEM_NODE to ATTENTION_FLOW_NODE"))
            if edge.relation == "attention_flow_links_blocks" and (source_type != "ATTENTION_FLOW_NODE" or target_type != "ATTENTION_FLOW_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="attention_flow_links_blocks must be from ATTENTION_FLOW_NODE to ATTENTION_FLOW_NODE"))
            if edge.relation == "attention_flow_references_block" and (source_type != "ATTENTION_FLOW_NODE" or target_type != "CONTENT_BLOCK_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_UX_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="attention_flow_references_block must be from ATTENTION_FLOW_NODE to CONTENT_BLOCK_NODE"))

            # Phase GS-7: Component Composition Edge Validation
            if edge.relation == "component_system_derives_intent" and (source_type != "COMPONENT_SYSTEM_NODE" or target_type != "DESIGN_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="component_system_derives_intent must be from COMPONENT_SYSTEM_NODE to DESIGN_INTENT_NODE"))
            if edge.relation == "component_system_defines_layout" and (source_type != "COMPONENT_SYSTEM_NODE" or target_type != "LAYOUT_CONTAINER_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="component_system_defines_layout must be from COMPONENT_SYSTEM_NODE to LAYOUT_CONTAINER_NODE"))
            if edge.relation == "layout_contains_component" and (source_type != "LAYOUT_CONTAINER_NODE" or target_type != "COMPONENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="layout_contains_component must be from LAYOUT_CONTAINER_NODE to COMPONENT_NODE"))
            if edge.relation == "layout_contains_layout" and (source_type != "LAYOUT_CONTAINER_NODE" or target_type != "LAYOUT_CONTAINER_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="layout_contains_layout must be from LAYOUT_CONTAINER_NODE to LAYOUT_CONTAINER_NODE"))
            if edge.relation == "component_contains_component" and (source_type != "COMPONENT_NODE" or target_type != "COMPONENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="component_contains_component must be from COMPONENT_NODE to COMPONENT_NODE"))
            if edge.relation == "component_defines_state" and (source_type != "COMPONENT_NODE" or target_type != "STATE_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="component_defines_state must be from COMPONENT_NODE to STATE_NODE"))
            if edge.relation == "component_defines_property" and (source_type != "COMPONENT_NODE" or target_type != "UI_PROPERTY_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="component_defines_property must be from COMPONENT_NODE to UI_PROPERTY_NODE"))
            if edge.relation == "component_references_block" and (source_type != "COMPONENT_NODE" or target_type != "CONTENT_BLOCK_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="component_references_block must be from COMPONENT_NODE to CONTENT_BLOCK_NODE"))
            if edge.relation == "component_supports_flow" and (source_type != "COMPONENT_NODE" or target_type != "TASK_FLOW_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_COMPONENT_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="component_supports_flow must be from COMPONENT_NODE to TASK_FLOW_NODE"))

            # Phase GS-8: Interaction Reasoning Edge Validation
            if edge.relation == "interaction_system_derives_intent" and (source_type != "INTERACTION_SYSTEM_NODE" or target_type != "DESIGN_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="interaction_system_derives_intent must be from INTERACTION_SYSTEM_NODE to DESIGN_INTENT_NODE"))
            if edge.relation == "interaction_system_defines_intent" and (source_type != "INTERACTION_SYSTEM_NODE" or target_type != "INTERACTION_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="interaction_system_defines_intent must be from INTERACTION_SYSTEM_NODE to INTERACTION_INTENT_NODE"))
            if edge.relation == "interaction_intent_contains_loop" and (source_type != "INTERACTION_INTENT_NODE" or target_type != "INTERACTION_LOOP_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="interaction_intent_contains_loop must be from INTERACTION_INTENT_NODE to INTERACTION_LOOP_NODE"))
            if edge.relation == "interaction_loop_contains_trigger" and (source_type != "INTERACTION_LOOP_NODE" or target_type != "TRIGGER_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="interaction_loop_contains_trigger must be from INTERACTION_LOOP_NODE to TRIGGER_NODE"))
            if edge.relation == "interaction_loop_contains_transition" and (source_type != "INTERACTION_LOOP_NODE" or target_type != "TRANSITION_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="interaction_loop_contains_transition must be from INTERACTION_LOOP_NODE to TRANSITION_NODE"))
            if edge.relation == "interaction_loop_contains_mutation" and (source_type != "INTERACTION_LOOP_NODE" or target_type != "MUTATION_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="interaction_loop_contains_mutation must be from INTERACTION_LOOP_NODE to MUTATION_NODE"))
            if edge.relation == "transition_mutates_state" and (source_type != "TRANSITION_NODE" or target_type != "MUTATION_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="transition_mutates_state must be from TRANSITION_NODE to MUTATION_NODE"))
            if edge.relation == "trigger_references_component" and (source_type != "TRIGGER_NODE" or target_type != "COMPONENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="trigger_references_component must be from TRIGGER_NODE to COMPONENT_NODE"))
            if edge.relation == "mutation_targets_component" and (source_type != "MUTATION_NODE" or target_type not in ("COMPONENT_NODE", "STATE_NODE")):
                violations.append(ValidationViolation(rule="ILLEGAL_INTERACTION_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="mutation_targets_component must be from MUTATION_NODE to COMPONENT_NODE/STATE_NODE"))

            # Phase GS-9: Responsive Reasoning Edge Validation
            if edge.relation == "responsive_system_derives_intent" and (source_type != "RESPONSIVE_SYSTEM_NODE" or target_type != "DESIGN_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="responsive_system_derives_intent must be from RESPONSIVE_SYSTEM_NODE to DESIGN_INTENT_NODE"))
            if edge.relation == "responsive_system_defines_intent" and (source_type != "RESPONSIVE_SYSTEM_NODE" or target_type != "RESPONSIVE_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="responsive_system_defines_intent must be from RESPONSIVE_SYSTEM_NODE to RESPONSIVE_INTENT_NODE"))
            if edge.relation == "responsive_intent_defines_viewport" and (source_type != "RESPONSIVE_INTENT_NODE" or target_type != "VIEWPORT_CONSTRAINT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="responsive_intent_defines_viewport must be from RESPONSIVE_INTENT_NODE to VIEWPORT_CONSTRAINT_NODE"))
            if edge.relation == "viewport_defines_attention" and (source_type != "VIEWPORT_CONSTRAINT_NODE" or target_type != "ATTENTION_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="viewport_defines_attention must be from VIEWPORT_CONSTRAINT_NODE to ATTENTION_NODE"))
            if edge.relation == "viewport_defines_density" and (source_type != "VIEWPORT_CONSTRAINT_NODE" or target_type != "DENSITY_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="viewport_defines_density must be from VIEWPORT_CONSTRAINT_NODE to DENSITY_NODE"))
            if edge.relation == "viewport_defines_cost" and (source_type != "VIEWPORT_CONSTRAINT_NODE" or target_type != "INTERACTION_COST_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="viewport_defines_cost must be from VIEWPORT_CONSTRAINT_NODE to INTERACTION_COST_NODE"))
            if edge.relation == "viewport_defines_priority" and (source_type != "VIEWPORT_CONSTRAINT_NODE" or target_type != "PRIORITY_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="viewport_defines_priority must be from VIEWPORT_CONSTRAINT_NODE to PRIORITY_NODE"))
            if edge.relation == "viewport_defines_adaptation" and (source_type != "VIEWPORT_CONSTRAINT_NODE" or target_type != "ADAPTATION_RULE_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="viewport_defines_adaptation must be from VIEWPORT_CONSTRAINT_NODE to ADAPTATION_RULE_NODE"))
            if edge.relation == "viewport_defines_override" and (source_type != "VIEWPORT_CONSTRAINT_NODE" or target_type != "LAYOUT_OVERRIDE_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="viewport_defines_override must be from VIEWPORT_CONSTRAINT_NODE to LAYOUT_OVERRIDE_NODE"))
            if edge.relation == "override_targets_layout" and (source_type != "LAYOUT_OVERRIDE_NODE" or target_type != "LAYOUT_CONTAINER_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="override_targets_layout must be from LAYOUT_OVERRIDE_NODE to LAYOUT_CONTAINER_NODE"))
            if edge.relation == "override_targets_component" and (source_type != "LAYOUT_OVERRIDE_NODE" or target_type != "COMPONENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="override_targets_component must be from LAYOUT_OVERRIDE_NODE to COMPONENT_NODE"))
            if edge.relation == "priority_targets_component" and (source_type != "PRIORITY_NODE" or target_type != "COMPONENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="priority_targets_component must be from PRIORITY_NODE to COMPONENT_NODE"))
            if edge.relation == "priority_targets_layout" and (source_type != "PRIORITY_NODE" or target_type != "LAYOUT_CONTAINER_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_RESPONSIVE_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="priority_targets_layout must be from PRIORITY_NODE to LAYOUT_CONTAINER_NODE"))

            # Phase GS-10: Design Memory Edge Validation
            if edge.relation == "design_memory_derives_intent" and (source_type != "DESIGN_MEMORY_NODE" or target_type != "DESIGN_INTENT_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_MEMORY_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="design_memory_derives_intent must be from DESIGN_MEMORY_NODE to DESIGN_INTENT_NODE"))
            if edge.relation == "critique_references_record" and (source_type != "COGNITIVE_CRITIQUE_NODE" or target_type != "COMPILE_RECORD_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_MEMORY_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="critique_references_record must be from COGNITIVE_CRITIQUE_NODE to COMPILE_RECORD_NODE"))
            if edge.relation == "feedback_references_record" and (source_type != "USER_FEEDBACK_NODE" or target_type != "COMPILE_RECORD_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_MEMORY_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="feedback_references_record must be from USER_FEEDBACK_NODE to COMPILE_RECORD_NODE"))
            if edge.relation == "memory_contains_record" and (source_type != "DESIGN_MEMORY_NODE" or target_type != "COMPILE_RECORD_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_MEMORY_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="memory_contains_record must be from DESIGN_MEMORY_NODE to COMPILE_RECORD_NODE"))
            if edge.relation == "memory_defines_learning" and (source_type != "DESIGN_MEMORY_NODE" or target_type != "DESIGN_LEARNING_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_MEMORY_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="memory_defines_learning must be from DESIGN_MEMORY_NODE to DESIGN_LEARNING_NODE"))
            if edge.relation == "learning_derives_record" and (source_type != "DESIGN_LEARNING_NODE" or target_type != "COMPILE_RECORD_NODE"):
                violations.append(ValidationViolation(rule="ILLEGAL_MEMORY_EDGE", node_id=edge.source_id, target_id=edge.target_id, reason="learning_derives_record must be from DESIGN_LEARNING_NODE to COMPILE_RECORD_NODE"))

            # Ensure mutation tier bounds are respected (bypass if local studio nodes)
            is_studio_source = source_type in (
                "CONTENT_BLOCK_NODE", "DATA_FIELD_NODE",
                "DESIGN_INTENT_NODE", "GLOBAL_INTENT_NODE", "PAGE_INTERACTION_NODE", "ATTENTION_MAP_NODE",
                "DESIGN_SYSTEM_NODE", "COLOR_CHARACTERISTICS_NODE", "TYPOGRAPHY_TOKEN_NODE", "SPACING_TOKEN_NODE", "MOTION_TOKEN_NODE", "COMPONENT_RULES_NODE",
                "NAVIGATION_SYSTEM_NODE", "ROUTING_MODEL_NODE", "ROUTE_NODE", "WORKFLOW_ROUTE_NODE", "NAV_MENU_NODE", "NAV_ITEM_NODE",
                "UX_SYSTEM_NODE", "UX_INTENT_NODE", "USER_JOURNEY_NODE", "TASK_FLOW_NODE", "ATTENTION_FLOW_NODE", "DECISION_POINT_NODE", "OUTCOME_NODE",
                "COMPONENT_SYSTEM_NODE", "LAYOUT_CONTAINER_NODE", "COMPONENT_NODE", "STATE_NODE", "UI_PROPERTY_NODE",
                "INTERACTION_SYSTEM_NODE", "INTERACTION_INTENT_NODE", "INTERACTION_LOOP_NODE", "TRIGGER_NODE", "TRANSITION_NODE", "MUTATION_NODE",
                "RESPONSIVE_SYSTEM_NODE", "RESPONSIVE_INTENT_NODE", "VIEWPORT_CONSTRAINT_NODE", "ATTENTION_NODE", "DENSITY_NODE", "INTERACTION_COST_NODE", "PRIORITY_NODE", "ADAPTATION_RULE_NODE", "LAYOUT_OVERRIDE_NODE",
                "DESIGN_MEMORY_NODE", "COMPILE_RECORD_NODE", "COGNITIVE_CRITIQUE_NODE", "USER_FEEDBACK_NODE", "DESIGN_LEARNING_NODE"
            )
            is_studio_target = target_type in (
                "CONTENT_BLOCK_NODE", "DATA_FIELD_NODE",
                "DESIGN_INTENT_NODE", "GLOBAL_INTENT_NODE", "PAGE_INTERACTION_NODE", "ATTENTION_MAP_NODE",
                "DESIGN_SYSTEM_NODE", "COLOR_CHARACTERISTICS_NODE", "TYPOGRAPHY_TOKEN_NODE", "SPACING_TOKEN_NODE", "MOTION_TOKEN_NODE", "COMPONENT_RULES_NODE",
                "NAVIGATION_SYSTEM_NODE", "ROUTING_MODEL_NODE", "ROUTE_NODE", "WORKFLOW_ROUTE_NODE", "NAV_MENU_NODE", "NAV_ITEM_NODE",
                "UX_SYSTEM_NODE", "UX_INTENT_NODE", "USER_JOURNEY_NODE", "TASK_FLOW_NODE", "ATTENTION_FLOW_NODE", "DECISION_POINT_NODE", "OUTCOME_NODE",
                "COMPONENT_SYSTEM_NODE", "LAYOUT_CONTAINER_NODE", "COMPONENT_NODE", "STATE_NODE", "UI_PROPERTY_NODE",
                "INTERACTION_SYSTEM_NODE", "INTERACTION_INTENT_NODE", "INTERACTION_LOOP_NODE", "TRIGGER_NODE", "TRANSITION_NODE", "MUTATION_NODE",
                "RESPONSIVE_SYSTEM_NODE", "RESPONSIVE_INTENT_NODE", "VIEWPORT_CONSTRAINT_NODE", "ATTENTION_NODE", "DENSITY_NODE", "INTERACTION_COST_NODE", "PRIORITY_NODE", "ADAPTATION_RULE_NODE", "LAYOUT_OVERRIDE_NODE",
                "DESIGN_MEMORY_NODE", "COMPILE_RECORD_NODE", "COGNITIVE_CRITIQUE_NODE", "USER_FEEDBACK_NODE", "DESIGN_LEARNING_NODE"
            )
            
            if not (is_studio_source or is_studio_target):
                source_max_tier = NodeOntology.get_max_mutation_tier(source_node.node_type)
                target_max_tier = NodeOntology.get_max_mutation_tier(target_node.node_type)

        # ── 5. Validate Dynamic Entry Route (ENTRY_ROUTE_FAILURE) ───────
        has_ui_nodes = False
        has_entry_route = False
        for node_id, node in graph.nodes.items():
            node_type_str = str(node.node_type)
            if node_type_str == "UI_NODE" or (hasattr(node.node_type, "value") and node.node_type.value == "UI_NODE") or node.node_type == NodeType.UI_NODE:
                has_ui_nodes = True
                if node.properties.get("is_root") is True:
                    has_entry_route = True
                    break

        if has_ui_nodes and not has_entry_route:
            violations.append(
                ValidationViolation(
                    rule="ENTRY_ROUTE_FAILURE",
                    reason="The synthesized application graph is missing an entry point page. At least one UI_NODE must be designated as 'is_root=True'."
                )
            )

        return TopologyValidationResult(passed=len(violations) == 0, violations=violations)

    @classmethod
    def _detect_cycle(cls, graph: ProjectTopologyGraph, relation: str) -> Tuple[bool, List[str]]:
        """DFS-based cycle detection for a specific edge relationship."""
        adj = graph.get_dependencies_dag(relation=relation)
        visited: Set[str] = set()
        rec_stack: List[str] = []

        def dfs(node_id: str) -> Tuple[bool, List[str]]:
            visited.add(node_id)
            rec_stack.append(node_id)

            for neighbor in adj.get(node_id, set()):
                if neighbor not in visited:
                    has_cyc, path = dfs(neighbor)
                    if has_cyc:
                        return True, path
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start_idx = rec_stack.index(neighbor)
                    cycle_path = rec_stack[cycle_start_idx:] + [neighbor]
                    return True, cycle_path

            rec_stack.pop()
            return False, []

        for node_id in graph.nodes:
            if node_id not in visited:
                has_cyc, path = dfs(node_id)
                if has_cyc:
                    return True, path

        return False, []
