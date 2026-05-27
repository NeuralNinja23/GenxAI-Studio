# app/topology/topology_compiler.py
"""
V4 Topology Compiler — Stage 2: Canonical Topology Engine

Converts compiled IntentField boundaries, UX ontologies, domain schemas,
routes, workflows, and semantic constraints into a canonical
ProjectTopologyGraph.

IMPORTANT:
- This compiler NEVER writes files.
- This compiler NEVER mutates AST directly.
- This compiler ONLY defines canonical structural reality.
"""

from typing import Dict, List, Any, Optional

from app.models.directive import IntentField, DomainEntity
from app.topology.node_types import NodeType
from app.topology.project_graph import ProjectTopologyGraph


class TopologyCompiler:
    """
    Topology Birth Mechanism.

    Compiles semantic intention boundaries into canonical graph structures.
    """

    @staticmethod
    def compile_intent(
        project_id: str,
        intent: IntentField
    ) -> ProjectTopologyGraph:
        """
        Synthesize a ProjectTopologyGraph from IntentField semantic boundaries.

        No files are written.
        No AST is generated here.
        Pure topology only.
        """

        graph = ProjectTopologyGraph(
            project_id=project_id,
            version=1
        )

        # ────────────────────────────────────────────────────────
        # 1. Contract Boundary
        # ────────────────────────────────────────────────────────

        contract_props = {
            "expected_contracts": intent.expected_contracts,
            "invariants": intent.invariants,
            "deployment_target": intent.deployment_target,
        }

        graph.add_node(
            node_id="sys_contract_boundary",
            node_type=NodeType.CONTRACT_NODE,
            properties=contract_props,
        )

        # ────────────────────────────────────────────────────────
        # 2. Schema Nodes
        # ────────────────────────────────────────────────────────

        for entity in intent.domain_entities:

            node_id = f"schema_{entity.name.lower()}"

            fields_def = [
                {
                    "name": f.name,
                    "type": f.type,
                    "required": f.required,
                }
                for f in entity.fields
            ]

            schema_props = {
                "entity_name": entity.name,
                "description": entity.description,
                "fields": fields_def,
            }

            graph.add_node(
                node_id=node_id,
                node_type=NodeType.SCHEMA_NODE,
                properties=schema_props,
            )

            graph.add_edge(
                source_id="sys_contract_boundary",
                target_id=node_id,
                relation="governs",
            )

        # ────────────────────────────────────────────────────────
        # 3. Services + APIs
        # ────────────────────────────────────────────────────────

        for entity in intent.domain_entities:

            schema_id = f"schema_{entity.name.lower()}"
            service_id = f"service_{entity.name.lower()}"
            api_id = f"api_{entity.name.lower()}"
            route_id = f"route_{entity.name.lower()}"

            # Service Node
            graph.add_node(
                node_id=service_id,
                node_type=NodeType.SERVICE_NODE,
                properties={
                    "service_name": f"{entity.name}Service",
                    "methods": [
                        "create",
                        "read",
                        "update",
                        "delete",
                        "list",
                    ],
                },
            )

            graph.add_edge(
                source_id=service_id,
                target_id=schema_id,
                relation="binds_schema",
            )

            # API Node
            graph.add_node(
                node_id=api_id,
                node_type=NodeType.API_NODE,
                properties={
                    "router_name": f"{entity.name.lower()}s",
                    "endpoints": [
                        {
                            "path": f"/{entity.name.lower()}s",
                            "method": "POST",
                        },
                        {
                            "path": f"/{entity.name.lower()}s/{{id}}",
                            "method": "GET",
                        },
                        {
                            "path": f"/{entity.name.lower()}s/{{id}}",
                            "method": "PUT",
                        },
                        {
                            "path": f"/{entity.name.lower()}s/{{id}}",
                            "method": "DELETE",
                        },
                        {
                            "path": f"/{entity.name.lower()}s",
                            "method": "GET",
                        },
                    ],
                },
            )

            graph.add_edge(
                source_id=api_id,
                target_id=service_id,
                relation="depends_on",
            )

            # Route Node
            graph.add_node(
                node_id=route_id,
                node_type=NodeType.ROUTE_NODE,
                properties={
                    "base_path": f"/api/v1/{entity.name.lower()}s"
                },
            )

            graph.add_edge(
                source_id=route_id,
                target_id=api_id,
                relation="routes_to",
            )

        # ────────────────────────────────────────────────────────
        # 4. UI Layout
        # ────────────────────────────────────────────────────────

        archetype = intent.ux_intent.get(
            "archetype",
            "dashboard"
        )

        ui_layout_id = "ui_layout_root"

        graph.add_node(
            node_id=ui_layout_id,
            node_type=NodeType.UI_NODE,
            properties={
                "component_name": "AppLayout",
                "archetype": archetype,
                "panels": [
                    "Sidebar",
                    "Header",
                    "MainViewport",
                ],
            },
        )

        # Domain UI Components
        for entity in intent.domain_entities:

            ui_comp_id = f"ui_component_{entity.name.lower()}"

            graph.add_node(
                node_id=ui_comp_id,
                node_type=NodeType.UI_NODE,
                properties={
                    "component_name": f"{entity.name}Manager",
                    "features": [
                        "Table",
                        "Form",
                        "Pagination",
                    ],
                },
            )

            graph.add_edge(
                source_id=ui_layout_id,
                target_id=ui_comp_id,
                relation="renders_component",
            )

            # API Relationship
            api_id = f"api_{entity.name.lower()}"

            graph.add_edge(
                source_id=ui_comp_id,
                target_id=api_id,
                relation="consumes_api",
            )

        # ────────────────────────────────────────────────────────
        # 5. Workflows
        # ────────────────────────────────────────────────────────

        for legality_rule in intent.workflow_legality:

            wf_id = f"workflow_{legality_rule.workflow_id}"

            graph.add_node(
                node_id=wf_id,
                node_type=NodeType.WORKFLOW_NODE,
                properties={
                    "workflow_id": legality_rule.workflow_id,
                    "allowed_transitions": legality_rule.allowed_transitions,
                    "forbidden_states": legality_rule.forbidden_states,
                },
            )

            graph.add_edge(
                source_id=wf_id,
                target_id=ui_layout_id,
                relation="coordinates",
            )

        # ────────────────────────────────────────────────────────
        # 6. Grounding Invariant Pass
        # ────────────────────────────────────────────────────────

        TopologyCompiler._ensure_renderable_grounding(graph)

        # ────────────────────────────────────────────────────────
        # Finalize Graph Integrity
        # ────────────────────────────────────────────────────────

        graph.update_graph_hash()

        return graph

    # ────────────────────────────────────────────────────────────
    # Grounding Invariant System
    # ────────────────────────────────────────────────────────────

    @staticmethod
    def _ensure_renderable_grounding(
        graph: ProjectTopologyGraph
    ) -> None:
        """
        Every renderable UI node must be causally grounded.

        Renderable nodes cannot exist independently.

        This invariant guarantees:
        - UI nodes participate in reactive state flow
        - behavioral_oracle coherence rules pass
        - no structurally orphaned UI components exist
        """

        RENDERABLE_NODE_TYPES = {
            NodeType.UI_NODE,
        }

        VALID_BINDING_RELATIONS = {
            "binds_state",
            "binds_query",
            "binds_context",
            "binds_collection",
            "binds_form",
            "binds_signal",
            "binds_prop",
        }

        for node in list(graph.nodes.values()):

            # Skip non-renderable nodes
            if node.node_type not in RENDERABLE_NODE_TYPES:
                continue

            # Check existing grounding
            already_grounded = any(
                edge.source_id == node.node_id
                and edge.relation in VALID_BINDING_RELATIONS
                for edge in graph.edges
            )

            if already_grounded:
                continue

            # Deterministic state grounding
            state_node_id = f"{node.node_id}_state"

            # Create state node if absent
            if state_node_id not in graph.nodes:

                graph.add_node(
                    node_id=state_node_id,
                    node_type=NodeType.STATE_NODE,
                    properties={
                        "generated": True,
                        "scope": node.node_id,
                        "store_type": "zustand",
                    },
                )

            # Bind renderable node to state
            graph.add_edge(
                source_id=node.node_id,
                target_id=state_node_id,
                relation="binds_state",
            )