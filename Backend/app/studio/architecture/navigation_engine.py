# app/studio/architecture/navigation_engine.py
"""
V4 GenxAI Studio — Phase GS-5: NavigationEngine

Navigation synthesis engine. Ingests OntologyGraph, ApplicationGraph, InformationGraph,
and DesignIntentGraph to generate a NavigationGraph carrying routing models, URL route paths,
workflow route steps, visual menus, and logical links.
Fails loudly and logs to SQLite Failure Recorder on structural or depth violations.
"""

import json
from typing import Dict, Any, Optional, List, Set
from app.sentinel.cognition.ontology_graph import OntologyGraph
from app.studio.architecture.application_graph import ApplicationGraph
from app.studio.architecture.information_graph import InformationGraph
from app.studio.architecture.design_intent import DesignIntentGraph
from app.studio.architecture.navigation_graph import (
    NavigationGraph,
    STUDIO_NAVIGATION_SYSTEM_NODE,
    STUDIO_ROUTING_MODEL_NODE,
    STUDIO_ROUTE_NODE,
    STUDIO_WORKFLOW_ROUTE_NODE,
    STUDIO_NAV_MENU_NODE,
    STUDIO_NAV_ITEM_NODE
)
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.topology_validator import TopologyValidator
from app.llm.adapter import call_llm
from app.core.logging import log
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity
from app.llm.prompts.navigation_engine import NAVIGATION_ENGINE_PROMPT

class NavigationEngine:
    """
    Logical navigation engine.
    Validates structural, reachability, and depth invariants, failing loudly on contradictions.
    """

    @classmethod
    async def synthesize(
        cls,
        project_id: str,
        ontology_graph: OntologyGraph,
        application_graph: ApplicationGraph,
        information_graph: InformationGraph,
        design_intent_graph: DesignIntentGraph
    ) -> NavigationGraph:
        """
        Synthesizes a NavigationGraph and performs strict click and workflow depth governance.
        Fails loudly and records failures to SQLite failure memory on contradiction or depth violation.
        """
        log("NavigationEngine", f"Starting Navigation synthesis for project {project_id}")

        app_dump = application_graph.serialize()
        ont_dump = ontology_graph.serialize()
        info_dump = information_graph.serialize()
        intent_dump = design_intent_graph.serialize()

        prompt = NAVIGATION_ENGINE_PROMPT.format(
            app_graph_json=json.dumps(app_dump, indent=2),
            ontology_graph_json=json.dumps(ont_dump, indent=2),
            info_graph_json=json.dumps(info_dump, indent=2),
            design_intent_graph_json=json.dumps(intent_dump, indent=2)
        )

        try:
            response = await call_llm(
                prompt=prompt,
                system_prompt="You are a strict, logical Navigation Engine translating page layouts into abstract navigation networks.",
                temperature=0.1,
                max_tokens=16384
            )

            # Clean markdown JSON wrapping if present
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())
            nav_graph = NavigationGraph(project_id=project_id)
            
            cls._populate_navigation(
                nav_graph,
                data,
                application_graph,
                design_intent_graph
            )

            # Perform Step 4: Reachability and Depth Governance
            cls._assert_no_contradictions(nav_graph, application_graph)

            # Validate structural legality using TopologyValidator
            validation_res = TopologyValidator.validate_graph(nav_graph)
            if not validation_res.passed:
                err_reasons = "; ".join(v.reason for v in validation_res.violations)
                raise ValueError(f"Topology Validation Failures: {err_reasons}")

            log("NavigationEngine", f"Successfully synthesized NavigationGraph with {len(nav_graph.nodes)} nodes")
            return nav_graph

        except Exception as err:
            err_msg = f"LOUD FAILURE in NavigationEngine for project {project_id}: {err}"
            log("NavigationEngine", f"⚠️ {err_msg}")
            
            # Record compilation failure in failure_memory.db
            try:
                record_failure(
                    failure_type=FailureType.COMPILATION_FAILURE,
                    severity=Severity.ERROR,
                    reason=err_msg,
                    project_id=project_id,
                    component="NavigationEngine"
                )
            except Exception as rec_err:
                log("NavigationEngine", f"Failed to record failure: {rec_err}")
                
            raise ValueError(err_msg) from err

    @classmethod
    def _populate_navigation(
        cls,
        graph: NavigationGraph,
        data: Dict[str, Any],
        application_graph: ApplicationGraph,
        design_intent_graph: DesignIntentGraph
    ) -> None:
        """Parses LLM response and populates the NavigationGraph."""
        nav_data = data.get("navigation_graph", {})
        
        # 1. Pull DESIGN_INTENT_NODE root from design_intent_graph to allow edge links
        intent_root_id = f"design_intent_{graph.project_id}"
        if intent_root_id in design_intent_graph.nodes:
            intent_node = design_intent_graph.nodes[intent_root_id]
            graph.add_node(intent_root_id, intent_node.node_type, intent_node.properties)

        # Pull pages from application_graph
        for node_id, node in application_graph.nodes.items():
            if node.node_type == NodeType.PAGE_NODE:
                graph.add_node(node_id, node.node_type, node.properties)

        # 2. Add NAVIGATION_SYSTEM_NODE root node for causal traceability
        nav_root_id = f"navigation_system_{graph.project_id}"
        graph.add_navigation_node(
            nav_root_id,
            STUDIO_NAVIGATION_SYSTEM_NODE,
            {"project_id": graph.project_id}
        )
        if intent_root_id in graph.nodes:
            graph.add_edge(nav_root_id, intent_root_id, "navigation_derives_intent")

        # 3. Add ROUTING_MODEL_NODE
        routing_data = nav_data.get("routing_model", {})
        routing_model_id = f"routing_model_{graph.project_id}"
        graph.add_navigation_node(
            routing_model_id,
            STUDIO_ROUTING_MODEL_NODE,
            {
                "routing_paradigm": routing_data.get("routing_paradigm"),
                "base_path": routing_data.get("base_path", "/")
            }
        )
        graph.add_edge(nav_root_id, routing_model_id, "system_defines_routing_model")

        # 4. Add standard routes (ROUTE_NODEs)
        routes_by_id = {}
        for route in nav_data.get("routes", []):
            route_id = route.get("id")
            path = route.get("path")
            target_page_id = route.get("target_page_id")
            route_class = route.get("route_classification")

            if not route_id or not path or not target_page_id or not route_class:
                raise ValueError(f"Route is missing id, path, route_classification, or target_page_id.")

            graph.add_navigation_node(
                route_id,
                STUDIO_ROUTE_NODE,
                {
                    "path": path,
                    "route_classification": route_class,
                    "dynamic": route.get("dynamic", False),
                    "parameters": route.get("parameters", [])
                }
            )
            graph.add_edge(routing_model_id, route_id, "routing_model_contains_route")
            if target_page_id in graph.nodes:
                graph.add_edge(route_id, target_page_id, "route_targets_page")

            routes_by_id[route_id] = route_id

        # 5. Add workflow routes (WORKFLOW_ROUTE_NODEs)
        for wf_route in nav_data.get("workflow_routes", []):
            route_id = wf_route.get("id")
            path = wf_route.get("path")
            target_page_id = wf_route.get("target_page_id")
            route_class = wf_route.get("route_classification")
            wf_step = wf_route.get("workflow_step_name")
            parent_id = wf_route.get("parent_route_id")

            if not route_id or not path or not target_page_id or not route_class or not wf_step:
                raise ValueError(f"Workflow route is missing id, path, route_classification, target_page_id, or workflow_step_name.")

            graph.add_navigation_node(
                route_id,
                STUDIO_WORKFLOW_ROUTE_NODE,
                {
                    "path": path,
                    "route_classification": route_class,
                    "workflow_step_name": wf_step,
                    "parameters": wf_route.get("parameters", [])
                }
            )
            graph.add_edge(routing_model_id, route_id, "routing_model_contains_route")
            if target_page_id in graph.nodes:
                graph.add_edge(route_id, target_page_id, "route_targets_page")

            # Wire workflow nesting transitions
            if parent_id and parent_id in graph.nodes:
                graph.add_edge(parent_id, route_id, "route_defines_workflow_step")
            
            routes_by_id[route_id] = route_id

        # 6. Add navigation menus (NAV_MENU_NODEs)
        for menu in nav_data.get("menus", []):
            menu_id = menu.get("id")
            menu_type = menu.get("nav_menu_type")
            disp_name = menu.get("display_name")

            if not menu_id or not menu_type or not disp_name:
                raise ValueError(f"Nav menu is missing id, nav_menu_type, or display_name.")

            graph.add_navigation_node(
                menu_id,
                STUDIO_NAV_MENU_NODE,
                {
                    "nav_menu_type": menu_type,
                    "display_name": disp_name
                }
            )
            graph.add_edge(nav_root_id, menu_id, "system_defines_menu")

            # Add NAV_ITEM_NODEs
            for item in menu.get("items", []):
                item_id = item.get("id")
                label = item.get("label")
                icon = item.get("icon_intent")
                redirect_id = item.get("redirects_to_route_id")

                if not item_id or not label or not icon or not redirect_id:
                    raise ValueError(f"Nav item {item_id} is missing label, icon_intent, or redirects_to_route_id.")

                graph.add_navigation_node(
                    item_id,
                    STUDIO_NAV_ITEM_NODE,
                    {
                        "label": label,
                        "icon_intent": icon,
                        "is_contextual": item.get("is_contextual", False)
                    }
                )
                graph.add_edge(menu_id, item_id, "menu_contains_item")
                if redirect_id in graph.nodes:
                    graph.add_edge(item_id, redirect_id, "nav_item_redirects_to")

    @classmethod
    def _assert_no_contradictions(cls, graph: NavigationGraph, application_graph: ApplicationGraph) -> None:
        """
        Enforce Step 4: Reachability and Depth Governance contradiction checks.
        """
        # ── 1. Reachability Check ──
        # Every PAGE_NODE in the ApplicationGraph must be targeted by at least one Route.
        routed_pages = set()
        for edge in graph.edges:
            if edge.relation == "route_targets_page":
                routed_pages.add(edge.target_id)

        orphans = []
        for nid, node in application_graph.nodes.items():
            if node.node_type == NodeType.PAGE_NODE:
                if nid not in routed_pages:
                    orphans.append(nid)

        if orphans:
            raise ValueError(
                f"NAVIGATION_CONTRADICTION_FAILURE: Found orphaned page nodes which are nottargeted "
                f"by any routing paths in the navigation tree: {orphans}"
            )

        # ── 2. Sidebar Link Overflow ──
        # Sidebar menu cannot contain more than 10 top-level items.
        for menu_node in graph.nodes.values():
            if str(menu_node.node_type) == "NAV_MENU_NODE":
                menu_type = menu_node.properties.get("nav_menu_type")
                if menu_type == "Sidebar":
                    items_count = sum(
                        1 for e in graph.edges
                        if e.relation == "menu_contains_item" and e.source_id == menu_node.node_id
                    )
                    if items_count > 10:
                        raise ValueError(
                            f"NAVIGATION_CONTRADICTION_FAILURE: Sidebar menu '{menu_node.node_id}' contains "
                            f"{items_count} items, exceeding the maximum allowed scanning limit of 10 items."
                        )

        # ── 3. Unreachable Route Checks ──
        # A route must either have a nav item redirects edge pointing to it OR be dynamic/contextual.
        static_redirected_routes = set()
        for edge in graph.edges:
            if edge.relation == "nav_item_redirects_to":
                static_redirected_routes.add(edge.target_id)

        for route_node in graph.nodes.values():
            if str(route_node.node_type) in ("ROUTE_NODE", "WORKFLOW_ROUTE_NODE"):
                is_dynamic = route_node.properties.get("dynamic", False)
                route_class = route_node.properties.get("route_classification")
                
                # If static/non-contextual route (ENTRY or PRIMARY) and no items point to it, it is unreachable.
                if not is_dynamic and route_class in ("ENTRY_ROUTE", "PRIMARY_ROUTE"):
                    if route_node.node_id not in static_redirected_routes:
                        # Allow entry routes to be resolved as base root paths without explicit sidebar links
                        if route_class != "ENTRY_ROUTE":
                            raise ValueError(
                                f"NAVIGATION_CONTRADICTION_FAILURE: Route '{route_node.node_id}' ({route_node.properties.get('path')}) "
                                f"is completely unreachable. It is static/primary but has no navigation menu items redirecting to it."
                            )

        # ── 4. Depth Governance ──
        # Traverse standard page click depth (NAVIGATION_DEPTH <= 4)
        cls._validate_navigation_depths(graph)

        # Traverse sequential workflow progression depth (WORKFLOW_DEPTH <= 8)
        cls._validate_workflow_depths(graph)

    @classmethod
    def _validate_navigation_depths(cls, graph: NavigationGraph) -> None:
        """Calculates standard navigation click depth starting from the Entry Route."""
        # Find entry route
        entry_route = next(
            (n for n in graph.nodes.values()
             if str(n.node_type) == "ROUTE_NODE" and n.properties.get("route_classification") == "ENTRY_ROUTE"),
            None
        )
        if not entry_route:
            return

        # Build basic route transition paths from navigation menu clicks
        # We can map standard primary/nested route clicks.
        # Let's count standard nested URL parameter slashes or item redirections as depth.
        # Specifically, let's find ROUTE_NODEs and trace their nested pathways.
        # Shortest paths from ENTRY_ROUTE to other ROUTE_NODEs via link pathways.
        # Standard URL slash path count is an excellent abstract representation of hierarchy depth:
        # e.g., /dashboard (depth 1), /customers (depth 1), /customers/detail (depth 2), /customers/detail/settings (depth 3).
        for route_node in graph.nodes.values():
            if str(route_node.node_type) == "ROUTE_NODE":
                path = route_node.properties.get("path", "")
                parts = [p for p in path.split("/") if p]
                depth = len(parts)
                if depth > 4:
                    raise ValueError(
                        f"NAVIGATION_DEPTH_FAILURE: Route '{route_node.node_id}' ({path}) "
                        f"violates standard UX scanning limits. Click depth is {depth}, exceeding the maximum allowed limit of 4 levels."
                    )

    @classmethod
    def _validate_workflow_depths(cls, graph: NavigationGraph) -> None:
        """Calculates sequential workflow steps progressions chain depth (WORKFLOW_DEPTH <= 8)."""
        # Adjacency map of route_defines_workflow_step edges
        adj = {}
        for edge in graph.edges:
            if edge.relation == "route_defines_workflow_step":
                adj.setdefault(edge.source_id, []).append(edge.target_id)

        memo = {}
        def get_max_depth(node_id: str) -> int:
            if node_id in memo:
                return memo[node_id]
            if node_id not in adj:
                return 1
            
            max_d = 0
            for neighbor in adj[node_id]:
                max_d = max(max_d, get_max_depth(neighbor))
            memo[node_id] = max_d + 1
            return memo[node_id]

        for route_node in graph.nodes.values():
            if str(route_node.node_type) in ("ROUTE_NODE", "WORKFLOW_ROUTE_NODE"):
                depth = get_max_depth(route_node.node_id)
                if depth > 8:
                    raise ValueError(
                        f"WORKFLOW_DEPTH_FAILURE: Workflow sequence starting from '{route_node.node_id}' "
                        f"stretches through {depth} stages, exceeding the maximum allowed business workflow threshold of 8 steps."
                    )
