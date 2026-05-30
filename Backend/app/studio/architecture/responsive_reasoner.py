# app/studio/architecture/responsive_reasoner.py
"""
V4 GenxAI Studio — Phase GS-9: ResponsiveReasoner

Responsive cognitive reasoning engine. Ingests ApplicationGraph, InformationGraph, DesignIntentGraph,
ComponentGraph, UXBlueprint, and InteractionGraph to generate a ResponsiveGraph.
Fails loudly and logs to SQLite Failure Recorder on structural or complexity violations.
"""

import json
from typing import Dict, Any, Optional, List, Set
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.topology_validator import TopologyValidator
from app.studio.architecture.application_graph import ApplicationGraph
from app.studio.architecture.information_graph import InformationGraph
from app.studio.architecture.design_intent import DesignIntentGraph
from app.studio.architecture.component_graph import ComponentGraph
from app.studio.architecture.ux_blueprint import UXBlueprint
from app.studio.architecture.responsive_graph import (
    ResponsiveGraph,
    STUDIO_RESPONSIVE_SYSTEM_NODE,
    STUDIO_RESPONSIVE_INTENT_NODE,
    STUDIO_VIEWPORT_CONSTRAINT_NODE,
    STUDIO_ATTENTION_NODE,
    STUDIO_DENSITY_NODE,
    STUDIO_INTERACTION_COST_NODE,
    STUDIO_PRIORITY_NODE,
    STUDIO_ADAPTATION_RULE_NODE,
    STUDIO_LAYOUT_OVERRIDE_NODE
)
from app.llm.adapter import call_llm
from app.core.logging import log
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity
from app.llm.prompts.responsive_reasoner import RESPONSIVE_REASONER_PROMPT

class ResponsiveReasoner:
    """
    Responsive reasoning engine.
    Validates viewport ranges, cognitive density, attention fragmentation, interaction costs,
    critical actions, priority mismatches, intent drifts, disruptive mutations, and visibility syncs, failing loudly.
    """

    @classmethod
    async def synthesize(
        cls,
        project_id: str,
        application_graph: ApplicationGraph,
        information_graph: InformationGraph,
        design_intent_graph: DesignIntentGraph,
        component_graph: ComponentGraph,
        ux_blueprint: UXBlueprint
    ) -> ResponsiveGraph:
        """
        Synthesizes a ResponsiveGraph and enforces 9 strict cognitive and priority invariants.
        Logs violations as COMPILATION_FAILURE to sentinel_memory.db and fails loudly.
        """
        log("ResponsiveReasoner", f"Starting Responsive cognitive synthesis for project {project_id}")

        app_dump = application_graph.serialize()
        info_dump = information_graph.serialize()
        intent_dump = design_intent_graph.serialize()
        comp_dump = component_graph.serialize()
        ux_dump = ux_blueprint.serialize()

        prompt = RESPONSIVE_REASONER_PROMPT.format(
            app_graph_json=json.dumps(app_dump, indent=2),
            info_graph_json=json.dumps(info_dump, indent=2),
            design_intent_graph_json=json.dumps(intent_dump, indent=2),
            component_graph_json=json.dumps(comp_dump, indent=2),
            ux_blueprint_json=json.dumps(ux_dump, indent=2)
        )

        try:
            response = await call_llm(
                prompt=prompt,
                system_prompt="You are a strict, logical Responsive Reasoner translating layout compositions into dynamic responsive cognitive systems.",
                temperature=0.1,
                max_tokens=16384
            )

            # Clean markdown JSON wrapping if present
            if response.strip().startswith("```json"):
                response = response.strip()[7:]
            if response.strip().endswith("```"):
                response = response.strip()[:-3]

            data = json.loads(response.strip())
            resp_graph = ResponsiveGraph(project_id=project_id)

            cls._populate_responsive_graph(
                resp_graph,
                data,
                design_intent_graph,
                component_graph
            )

            # Perform Step 4: Contradiction and Alignment checks
            cls._assert_no_contradictions(
                resp_graph,
                design_intent_graph,
                component_graph
            )

            # Validate structural legality using TopologyValidator
            validation_res = TopologyValidator.validate_graph(resp_graph)
            if not validation_res.passed:
                err_reasons = "; ".join(v.reason for v in validation_res.violations)
                raise ValueError(f"Topology Validation Failures: {err_reasons}")

            log("ResponsiveReasoner", f"Successfully synthesized ResponsiveGraph with {len(resp_graph.nodes)} nodes")
            return resp_graph

        except Exception as err:
            err_msg = f"LOUD FAILURE in ResponsiveReasoner for project {project_id}: {err}"
            log("ResponsiveReasoner", f"⚠️ {err_msg}")

            # Record compilation failure in failure_memory.db
            try:
                record_failure(
                    failure_type=FailureType.COMPILATION_FAILURE,
                    severity=Severity.ERROR,
                    reason=err_msg,
                    project_id=project_id,
                    component="ResponsiveReasoner"
                )
            except Exception as rec_err:
                log("ResponsiveReasoner", f"Failed to record failure: {rec_err}")

            raise ValueError(err_msg) from err

    @classmethod
    def _populate_responsive_graph(
        cls,
        graph: ResponsiveGraph,
        data: Dict[str, Any],
        design_intent_graph: DesignIntentGraph,
        component_graph: ComponentGraph
    ) -> None:
        """Parses LLM response and populates the ResponsiveGraph."""
        resp_data = data.get("responsive_graph", {})

        # Pull DESIGN_INTENT_NODE root from design_intent_graph
        intent_root_id = f"design_intent_{graph.project_id}"
        if intent_root_id in design_intent_graph.nodes:
            intent_node = design_intent_graph.nodes[intent_root_id]
            graph.add_node(intent_root_id, intent_node.node_type, intent_node.properties)

        # Pull components from component_graph
        for node_id, node in component_graph.nodes.items():
            if str(node.node_type) == "COMPONENT_NODE":
                graph.add_node(node_id, node.node_type, node.properties)

        # Add RESPONSIVE_SYSTEM_NODE root node for causal traceability
        resp_root_id = f"responsive_system_{graph.project_id}"
        graph.add_responsive_node(
            resp_root_id,
            STUDIO_RESPONSIVE_SYSTEM_NODE,
            {"project_id": graph.project_id}
        )
        if intent_root_id in graph.nodes:
            graph.add_edge(resp_root_id, intent_root_id, "responsive_system_derives_intent")

        # 1. Add Responsive Intents (RESPONSIVE_INTENT_NODE)
        for intent in resp_data.get("intents", []):
            i_id = intent.get("id")
            viewport = intent.get("viewport")
            primary_goal = intent.get("primary_goal")

            if not i_id or not primary_goal:
                raise ValueError("Responsive Intent is missing id or primary_goal.")

            graph.add_responsive_node(
                i_id,
                STUDIO_RESPONSIVE_INTENT_NODE,
                {"viewport": viewport, "primary_goal": primary_goal}
            )
            graph.add_edge(resp_root_id, i_id, "responsive_system_defines_intent")

        # 2. Add Viewport Constraints (VIEWPORT_CONSTRAINT_NODE)
        for vp in resp_data.get("viewports", []):
            vp_id = vp.get("id")
            min_w = vp.get("min_width")
            max_w = vp.get("max_width")
            attention_capacity = vp.get("attention_capacity")
            density_budget = vp.get("density_budget")
            max_cost = vp.get("max_interaction_cost")

            if not vp_id or min_w is None or max_w is None:
                raise ValueError("Viewport Constraint is missing id, min_width, or max_width.")

            graph.add_responsive_node(
                vp_id,
                STUDIO_VIEWPORT_CONSTRAINT_NODE,
                {"min_width": min_w, "max_width": max_w}
            )
            # Link back to matching Responsive Intent if matching viewport label
            for int_node in list(graph.nodes.values()):
                if str(int_node.node_type) == "RESPONSIVE_INTENT_NODE" and int_node.properties.get("viewport") in vp_id:
                    graph.add_edge(int_node.node_id, vp_id, "responsive_intent_defines_viewport")

            # Add Attention Node
            att_id = f"attention_{vp_id}"
            graph.add_responsive_node(att_id, STUDIO_ATTENTION_NODE, {"attention_capacity": attention_capacity})
            graph.add_edge(vp_id, att_id, "viewport_defines_attention")

            # Add Density Node
            dens_id = f"density_{vp_id}"
            graph.add_responsive_node(dens_id, STUDIO_DENSITY_NODE, {"density_budget": density_budget})
            graph.add_edge(vp_id, dens_id, "viewport_defines_density")

            # Add Interaction Cost Node
            cost_id = f"cost_{vp_id}"
            graph.add_responsive_node(cost_id, STUDIO_INTERACTION_COST_NODE, {"max_interaction_cost": max_cost})
            graph.add_edge(vp_id, cost_id, "viewport_defines_cost")

        # 3. Add Component Priorities (PRIORITY_NODE)
        for pri in resp_data.get("priorities", []):
            pri_id = pri.get("id")
            target_comp = pri.get("target_component_id")
            level = pri.get("priority_level")

            if not pri_id or not target_comp or not level:
                raise ValueError("Priority definition is missing id, target_component_id, or priority_level.")

            # Make sure allowed levels
            allowed_levels = {"Critical", "Primary", "Secondary", "Optional"}
            if level not in allowed_levels:
                raise ValueError(f"Unsupported priority level: '{level}'. Must be one of {allowed_levels}.")

            graph.add_responsive_node(
                pri_id,
                STUDIO_PRIORITY_NODE,
                {
                    "target_component_id": target_comp,
                    "priority_level": level
                }
            )

            # Link back to active viewports
            for vp_node in list(graph.nodes.values()):
                if str(vp_node.node_type) == "VIEWPORT_CONSTRAINT_NODE":
                    graph.add_edge(vp_node.node_id, pri_id, "viewport_defines_priority")

            if target_comp in graph.nodes:
                graph.add_edge(pri_id, target_comp, "priority_targets_component")

        # 4. Add Adaptation Rules (ADAPTATION_RULE_NODE)
        for adapt in resp_data.get("adaptations", []):
            a_id = adapt.get("id")
            vp_id = adapt.get("viewport_id")
            pri_id = adapt.get("priority_id")
            action = adapt.get("adaptation_action")

            if not a_id or not vp_id or not pri_id or not action:
                raise ValueError("Adaptation Rule is missing id, viewport_id, priority_id, or adaptation_action.")

            graph.add_responsive_node(
                a_id,
                STUDIO_ADAPTATION_RULE_NODE,
                {
                    "viewport_id": vp_id,
                    "priority_id": pri_id,
                    "adaptation_action": action
                }
            )
            if vp_id in graph.nodes:
                graph.add_edge(vp_id, a_id, "viewport_defines_adaptation")

        # 5. Add Layout Overrides (LAYOUT_OVERRIDE_NODE)
        for over in resp_data.get("overrides", []):
            o_id = over.get("id")
            vp_id = over.get("viewport_id")
            t_layout = over.get("target_layout_id")
            override_type = over.get("override_layout_type")
            steps_count = over.get("workflow_steps_count", 0)
            focus_anchors = over.get("focus_anchors_count", 0)

            if not o_id or not vp_id:
                raise ValueError("Layout Override is missing id or viewport_id.")

            graph.add_responsive_node(
                o_id,
                STUDIO_LAYOUT_OVERRIDE_NODE,
                {
                    "viewport_id": vp_id,
                    "target_layout_id": t_layout,
                    "override_layout_type": override_type,
                    "workflow_steps_count": steps_count,
                    "focus_anchors_count": focus_anchors
                }
            )
            if vp_id in graph.nodes:
                graph.add_edge(vp_id, o_id, "viewport_defines_override")

    @classmethod
    def _assert_no_contradictions(
        cls,
        graph: ResponsiveGraph,
        design_intent_graph: DesignIntentGraph,
        component_graph: ComponentGraph
    ) -> None:
        """Enforces Phase GS-9 strict cognitive and responsive validations, failing loudly."""
        # ── 1. Viewport Overlap Check ──
        cls._validate_viewport_overlap(graph)

        # ── 2. Cognitive Density budget check ──
        cls._validate_density_overload(graph, component_graph)

        # ── 3. Attention Fragmentation check ──
        cls._validate_attention_fragmentation(graph)

        # ── 4. Interaction Cost bounds check ──
        cls._validate_interaction_cost(graph)

        # ── 5. Critical Action component preservation check ──
        cls._validate_critical_action_removal(graph, component_graph)

        # ── 6. Priority adaptation alignment check ──
        cls._validate_priority_adaptation_mismatch(graph)

        # ── 7. Responsive Intent Consistency check ──
        cls._validate_responsive_intent_drift(graph)

        # ── 8. Layout Continuity validation ──
        cls._validate_disruptive_layout_mutations(graph)

        # ── 9. Dynamic Visibility sync check ──
        cls._validate_visibility_out_of_sync(graph)

    @classmethod
    def _validate_viewport_overlap(cls, graph: ResponsiveGraph) -> None:
        """Throws VIEWPORT_OVERLAP_FAILURE if viewport width ranges intersect."""
        viewports = []
        for node in graph.nodes.values():
            if str(node.node_type) == "VIEWPORT_CONSTRAINT_NODE":
                min_w = node.properties.get("min_width", 0)
                max_w = node.properties.get("max_width", 9999)
                viewports.append((node.node_id, min_w, max_w))

        # Check all pairs for overlap
        for i in range(len(viewports)):
            for j in range(i + 1, len(viewports)):
                id1, min1, max1 = viewports[i]
                id2, min2, max2 = viewports[j]
                if not (max1 < min2 or max2 < min1):
                    raise ValueError(
                        f"VIEWPORT_OVERLAP_FAILURE: Viewport limits overlap between '{id1}' ({min1}px-{max1}px) "
                        f"and '{id2}' ({min2}px-{max2}px), violating spatial range laws."
                    )

    @classmethod
    def _validate_density_overload(cls, graph: ResponsiveGraph, component_graph: ComponentGraph) -> None:
        """Throws DENSITY_OVERLOAD_FAILURE if total targeted components exceed density limits."""
        for vp_node in graph.nodes.values():
            if str(vp_node.node_type) == "VIEWPORT_CONSTRAINT_NODE":
                # Find density budget associated
                dens_node_id = f"density_{vp_node.node_id}"
                dens_node = graph.nodes.get(dens_node_id)
                if dens_node:
                    budget = dens_node.properties.get("density_budget")
                    # Count total visible components in this viewport (components that do NOT have a Hide adaptation rule)
                    hidden_components = set()
                    for adapt in graph.nodes.values():
                        if str(adapt.node_type) == "ADAPTATION_RULE_NODE":
                            if adapt.properties.get("viewport_id") == vp_node.node_id:
                                if adapt.properties.get("adaptation_action") == "Hide":
                                    # Find matching priority to target component
                                    pri_id = adapt.properties.get("priority_id")
                                    pri_node = graph.nodes.get(pri_id)
                                    if pri_node:
                                        hidden_components.add(pri_node.properties.get("target_component_id"))

                    total_components = sum(1 for n in component_graph.nodes.values() if str(n.node_type) == "COMPONENT_NODE")
                    visible_count = total_components - len(hidden_components)

                    if budget == "Sparse" and visible_count > 5:
                        raise ValueError(
                            f"DENSITY_OVERLOAD_FAILURE: Viewport budget is '{budget}', but has {visible_count} "
                            f"visible components, violating cognitive budget limit of 5."
                        )
                    elif budget == "Balanced" and visible_count > 10:
                        raise ValueError(
                            f"DENSITY_OVERLOAD_FAILURE: Viewport budget is '{budget}', but has {visible_count} "
                            f"visible components, violating cognitive budget limit of 10."
                        )

    @classmethod
    def _validate_attention_fragmentation(cls, graph: ResponsiveGraph) -> None:
        """Throws ATTENTION_FRAGMENTATION_FAILURE if a mobile layout override has multiple competing focus anchors."""
        for over in graph.nodes.values():
            if str(over.node_type) == "LAYOUT_OVERRIDE_NODE":
                vp_id = over.properties.get("viewport_id")
                # Identify if viewport is mobile/low attention capacity
                att_node = graph.nodes.get(f"attention_{vp_id}")
                if att_node and att_node.properties.get("attention_capacity") == "low":
                    focus_anchors = over.properties.get("focus_anchors_count", 0)
                    if focus_anchors > 1:
                        raise ValueError(
                            f"ATTENTION_FRAGMENTATION_FAILURE: Viewport '{vp_id}' has low attention capacity, "
                            f"but layout override defines {focus_anchors} focus anchors, causing visual fragmentation."
                        )

    @classmethod
    def _validate_interaction_cost(cls, graph: ResponsiveGraph) -> None:
        """Throws INTERACTION_COST_FAILURE if layout override workflow steps exceed the viewport's budget."""
        for over in graph.nodes.values():
            if str(over.node_type) == "LAYOUT_OVERRIDE_NODE":
                vp_id = over.properties.get("viewport_id")
                cost_node = graph.nodes.get(f"cost_{vp_id}")
                if cost_node:
                    max_cost = cost_node.properties.get("max_interaction_cost", 99)
                    steps_count = over.properties.get("workflow_steps_count", 0)
                    if steps_count > max_cost:
                        raise ValueError(
                            f"INTERACTION_COST_FAILURE: Viewport '{vp_id}' has maximum allowed interaction cost of {max_cost}, "
                            f"but layout override workflow steps stretch to {steps_count} interactions, exceeding cognitive budget."
                        )

    @classmethod
    def _validate_critical_action_removal(cls, graph: ResponsiveGraph, component_graph: ComponentGraph) -> None:
        """Throws CRITICAL_ACTION_REMOVAL_FAILURE if any Critical interactive affordance action component is hidden."""
        for node in graph.nodes.values():
            if str(node.node_type) == "PRIORITY_NODE":
                level = node.properties.get("priority_level")
                comp_id = node.properties.get("target_component_id")

                if level == "Critical":
                    comp_node = component_graph.nodes.get(comp_id)
                    if comp_node and comp_node.properties.get("affordance_type") == "Interactive Affordance":
                        # Check adaptation actions for this priority
                        for adapt in graph.nodes.values():
                            if str(adapt.node_type) == "ADAPTATION_RULE_NODE":
                                if adapt.properties.get("priority_id") == node.node_id:
                                    if adapt.properties.get("adaptation_action") == "Hide":
                                        raise ValueError(
                                            f"CRITICAL_ACTION_REMOVAL_FAILURE: Component '{comp_id}' carrying Critical priority "
                                            f"and 'Interactive Affordance' action wrappers was hidden in viewport '{adapt.properties.get('viewport_id')}'."
                                        )

    @classmethod
    def _validate_priority_adaptation_mismatch(cls, graph: ResponsiveGraph) -> None:
        """Throws PRIORITY_ADAPTATION_MISMATCH_FAILURE if any Critical component has a Hide or Collapse adaptation rule."""
        for node in graph.nodes.values():
            if str(node.node_type) == "PRIORITY_NODE":
                level = node.properties.get("priority_level")
                comp_id = node.properties.get("target_component_id")

                if level == "Critical":
                    for adapt in graph.nodes.values():
                        if str(adapt.node_type) == "ADAPTATION_RULE_NODE":
                            if adapt.properties.get("priority_id") == node.node_id:
                                action = adapt.properties.get("adaptation_action")
                                if action in ("Hide", "Collapse"):
                                    raise ValueError(
                                        f"PRIORITY_ADAPTATION_MISMATCH_FAILURE: Component '{comp_id}' marked as 'Critical' priority "
                                        f"carries an illegal '{action}' adaptation action, violating priority-behavior compliance."
                                    )

    @classmethod
    def _validate_responsive_intent_drift(cls, graph: ResponsiveGraph) -> None:
        """Throws RESPONSIVE_INTENT_DRIFT_FAILURE if adaptations violate declared viewport goals."""
        for intent in graph.nodes.values():
            if str(intent.node_type) == "RESPONSIVE_INTENT_NODE":
                goal = intent.properties.get("primary_goal")
                vp = intent.properties.get("viewport")

                if goal == "task_execution":
                    # For task_execution, we must not hide all components, and should promote action items
                    # Scan rules: if all adaptations for this viewport are "Hide", or if we hide core items, drift occurs.
                    # Simple check: did we hide actions but promote optional reports?
                    hidden_criticals = 0
                    for adapt in graph.nodes.values():
                        if str(adapt.node_type) == "ADAPTATION_RULE_NODE":
                            # check if viewport matches
                            if vp in adapt.properties.get("viewport_id", ""):
                                if adapt.properties.get("adaptation_action") == "Hide":
                                    pri_id = adapt.properties.get("priority_id")
                                    pri_node = graph.nodes.get(pri_id)
                                    # If we hide something critical, drift flags
                                    if pri_node and pri_node.properties.get("priority_level") == "Critical":
                                        hidden_criticals += 1
                    if hidden_criticals > 0:
                        raise ValueError(
                            f"RESPONSIVE_INTENT_DRIFT_FAILURE: Viewport goal is '{goal}', but critical task execution "
                            f"actions have been hidden, causing a direct semantic intent drift."
                        )

    @classmethod
    def _validate_disruptive_layout_mutations(cls, graph: ResponsiveGraph) -> None:
        """Throws DISRUPTIVE_LAYOUT_MUTATION_FAILURE if layout overrides perform semantic drift layout transformations."""
        for node in graph.nodes.values():
            if str(node.node_type) == "LAYOUT_OVERRIDE_NODE":
                override_type = node.properties.get("override_layout_type")
                # Transitions from Bento / grid to stack are fine, but unrelated types are disjointed
                disallowed_mutations = {"Chat UI", "Voice Dialog", "Terminal Shell"}
                if override_type in disallowed_mutations:
                    raise ValueError(
                        f"DISRUPTIVE_LAYOUT_MUTATION_FAILURE: Layout mutation override targets disjointed layout format '{override_type}', "
                        f"causing a major cognitive discontinuity in visual scanning layout transition."
                    )

    @classmethod
    def _validate_visibility_out_of_sync(cls, graph: ResponsiveGraph) -> None:
        """Throws VISIBILITY_OUT_OF_SYNC_FAILURE if a component is hidden but still targeted by active events."""
        hidden_components = set()
        for adapt in graph.nodes.values():
            if str(adapt.node_type) == "ADAPTATION_RULE_NODE":
                if adapt.properties.get("adaptation_action") == "Hide":
                    pri_id = adapt.properties.get("priority_id")
                    pri_node = graph.nodes.get(pri_id)
                    if pri_node:
                        hidden_components.add(pri_node.properties.get("target_component_id"))

        # In ResponsiveGraph, if a hidden component targets layout overrides carrying workflow steps, raise error
        for over in graph.nodes.values():
            if str(over.node_type) == "LAYOUT_OVERRIDE_NODE":
                t_layout = over.properties.get("target_layout_id")
                # Simple mock check for hidden component workflow out of sync
                if t_layout in hidden_components and over.properties.get("workflow_steps_count", 0) > 0:
                    raise ValueError(
                        f"VISIBILITY_OUT_OF_SYNC_FAILURE: Target component layout '{t_layout}' is hidden on viewport "
                        f"but remains actively targeted by workflow actions."
                    )
