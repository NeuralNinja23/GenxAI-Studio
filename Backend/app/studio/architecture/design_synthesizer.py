# app/studio/architecture/design_synthesizer.py
"""
V4 GenxAI Studio — Phase GS-4: DesignSynthesizer

Design Token synthesis engine. Ingests OntologyGraph and DesignIntentGraph to generate
a DesignSystemGraph carrying abstract HSL palette characteristics, typographic scales,
spacing scales, motion timings, and component rules.
Fails loudly and logs to SQLite Failure Recorder on structural or token contradictions.
"""

import json
from typing import Dict, Any, Optional
from app.sentinel.cognition.ontology_graph import OntologyGraph
from app.studio.architecture.design_intent import DesignIntentGraph
from app.studio.architecture.design_system import (
    DesignSystemGraph,
    STUDIO_DESIGN_SYSTEM_NODE,
    STUDIO_COLOR_CHARACTERISTICS_NODE,
    STUDIO_TYPOGRAPHY_TOKEN_NODE,
    STUDIO_SPACING_TOKEN_NODE,
    STUDIO_MOTION_TOKEN_NODE,
    STUDIO_COMPONENT_RULES_NODE
)
from app.sentinel.topology.node_types import NodeType
from app.sentinel.topology.topology_validator import TopologyValidator
from app.llm.adapter import call_llm
from app.core.logging import log
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity
from app.llm.prompts.design_synthesizer import DESIGN_SYNTHESIZER_PROMPT

class DesignSynthesizer:
    """
    Design system synthesis engine.
    Validates structural and token invariants, failing loudly on contradictions.
    """

    @classmethod
    async def synthesize(
        cls,
        project_id: str,
        ontology_graph: OntologyGraph,
        design_intent_graph: DesignIntentGraph
    ) -> DesignSystemGraph:
        """
        Synthesizes a DesignSystemGraph and performs strict design system contradiction checks.
        Fails loudly and records failures to SQLite failure memory on contradiction or mismatch.
        """
        log("DesignSynthesizer", f"Starting Design System synthesis for project {project_id}")

        ont_dump = ontology_graph.serialize()
        intent_dump = design_intent_graph.serialize()

        prompt = DESIGN_SYNTHESIZER_PROMPT.format(
            ontology_graph_json=json.dumps(ont_dump, indent=2),
            design_intent_graph_json=json.dumps(intent_dump, indent=2)
        )

        try:
            response = await call_llm(
                prompt=prompt,
                system_prompt="You are a strict, logical Design System Synthesizer translating UX intents into design tokens.",
                temperature=0.1,
                max_tokens=16384
            )

            # Clean markdown JSON wrapping if present
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())
            system_graph = DesignSystemGraph(project_id=project_id)
            
            cls._populate_design_system(
                system_graph,
                data,
                design_intent_graph
            )

            # Perform Step 4: Cognitive Contradiction Check
            cls._assert_no_contradictions(system_graph, design_intent_graph)

            # Validate structural legality using TopologyValidator
            validation_res = TopologyValidator.validate_graph(system_graph)
            if not validation_res.passed:
                err_reasons = "; ".join(v.reason for v in validation_res.violations)
                raise ValueError(f"Topology Validation Failures: {err_reasons}")

            log("DesignSynthesizer", f"Successfully synthesized DesignSystemGraph with {len(system_graph.nodes)} nodes")
            return system_graph

        except Exception as err:
            err_msg = f"LOUD FAILURE in DesignSynthesizer for project {project_id}: {err}"
            log("DesignSynthesizer", f"⚠️ {err_msg}")
            
            # Record structural failure in failure_memory.db
            try:
                record_failure(
                    failure_type=FailureType.COMPILATION_FAILURE,
                    severity=Severity.ERROR,
                    reason=err_msg,
                    project_id=project_id,
                    component="DesignSynthesizer"
                )
            except Exception as rec_err:
                log("DesignSynthesizer", f"Failed to record failure: {rec_err}")
                
            raise ValueError(err_msg) from err

    @classmethod
    def _populate_design_system(
        cls,
        graph: DesignSystemGraph,
        data: Dict[str, Any],
        design_intent_graph: DesignIntentGraph
    ) -> None:
        """Parses LLM response and populates the DesignSystemGraph."""
        system_data = data.get("design_system", {})
        
        # 1. Pull DESIGN_INTENT_NODE root from design_intent_graph to allow edge links
        intent_root_id = f"design_intent_{graph.project_id}"
        if intent_root_id in design_intent_graph.nodes:
            intent_node = design_intent_graph.nodes[intent_root_id]
            graph.add_node(intent_root_id, intent_node.node_type, intent_node.properties)

        # 2. Add DESIGN_SYSTEM_NODE root node for causal traceability
        system_root_id = f"design_system_{graph.project_id}"
        graph.add_system_node(
            system_root_id,
            STUDIO_DESIGN_SYSTEM_NODE,
            {
                "theme_name": system_data.get("theme_name", "Default Abstract Theme"),
                "base_ratio": system_data.get("base_ratio", 1.2)
            }
        )
        if intent_root_id in graph.nodes:
            graph.add_edge(system_root_id, intent_root_id, "design_system_derives_intent")

        # 3. Add COLOR_CHARACTERISTICS_NODE
        color_data = system_data.get("color_characteristics", {})
        color_id = f"color_char_{graph.project_id}"
        graph.add_system_node(
            color_id,
            STUDIO_COLOR_CHARACTERISTICS_NODE,
            {
                "stability": color_data.get("stability"),
                "saturation_variance": color_data.get("saturation_variance"),
                "readability_demands": color_data.get("readability_demands"),
                "temperature_profile": color_data.get("temperature_profile")
            }
        )
        graph.add_edge(system_root_id, color_id, "system_defines_color_char")

        # 4. Add TYPOGRAPHY_TOKEN_NODE
        typo_data = system_data.get("typography", {})
        typo_id = f"typography_tokens_{graph.project_id}"
        graph.add_system_node(
            typo_id,
            STUDIO_TYPOGRAPHY_TOKEN_NODE,
            {
                "font_family_sans": typo_data.get("font_family_sans"),
                "font_family_mono": typo_data.get("font_family_mono"),
                "font_scale": typo_data.get("font_scale", [])
            }
        )
        graph.add_edge(system_root_id, typo_id, "system_defines_typography")

        # 5. Add SPACING_TOKEN_NODE
        spacing_data = system_data.get("spacing", {})
        spacing_id = f"spacing_tokens_{graph.project_id}"
        graph.add_system_node(
            spacing_id,
            STUDIO_SPACING_TOKEN_NODE,
            {
                "spacing_scale_type": spacing_data.get("spacing_scale_type"),
                "border_radius_type": spacing_data.get("border_radius_type"),
                "shadow_density": spacing_data.get("shadow_density")
            }
        )
        graph.add_edge(system_root_id, spacing_id, "system_defines_spacing")

        # 6. Add MOTION_TOKEN_NODE
        motion_data = system_data.get("motion", {})
        motion_id = f"motion_tokens_{graph.project_id}"
        graph.add_system_node(
            motion_id,
            STUDIO_MOTION_TOKEN_NODE,
            {
                "duration_speed": motion_data.get("duration_speed"),
                "easing_type": motion_data.get("easing_type")
            }
        )
        graph.add_edge(system_root_id, motion_id, "system_defines_motion")

        # 7. Add COMPONENT_RULES_NODE
        rules_data = system_data.get("component_rules", {})
        rules_id = f"component_rules_{graph.project_id}"
        graph.add_system_node(
            rules_id,
            STUDIO_COMPONENT_RULES_NODE,
            {
                "focus_outline_style": rules_data.get("focus_outline_style"),
                "border_width_profile": rules_data.get("border_width_profile")
            }
        )
        graph.add_edge(system_root_id, rules_id, "system_defines_rules")

    @classmethod
    def _assert_no_contradictions(cls, system_graph: DesignSystemGraph, design_intent_graph: DesignIntentGraph) -> None:
        """
        Enforce Step 4: Design System Contradiction Checks.
        Prevents aesthetically broken or cognitively conflicting design tokens.
        """
        # Find local token node definitions
        color_char_node = next(
            (n for n in system_graph.nodes.values() if str(n.node_type) == "COLOR_CHARACTERISTICS_NODE"),
            None
        )
        spacing_node = next(
            (n for n in system_graph.nodes.values() if str(n.node_type) == "SPACING_TOKEN_NODE"),
            None
        )
        motion_node = next(
            (n for n in system_graph.nodes.values() if str(n.node_type) == "MOTION_TOKEN_NODE"),
            None
        )

        # Pull parent design intents to verify logical compatibility
        global_intent_node = next(
            (n for n in design_intent_graph.nodes.values() if str(n.node_type) == "GLOBAL_INTENT_NODE"),
            None
        )

        if not global_intent_node:
            return

        complexity = global_intent_node.properties.get("complexity_preference")
        color_intent = global_intent_node.properties.get("color_intent")

        # ⚠️ Contradiction 1: Utility Spacing Contradiction
        # If Sophia requested Maximize Utility, we cannot use visual Spacious spacing.
        if spacing_node:
            spacing_scale = spacing_node.properties.get("spacing_scale_type")
            if complexity == "Maximize Utility" and spacing_scale == "Spacious Focus":
                raise ValueError(
                    f"DESIGN_SYSTEM_CONTRADICTION_FAILURE: Sophia requested 'Maximize Utility' complexity, "
                    f"which directly contradicts the synthesized 'Spacious Focus' spacing scale."
                )

        # ⚠️ Contradiction 2: Operational Motion Mismatch
        # If Sophia specifies a fast-paced Operational visual temperature, slow transitions are illegal.
        if motion_node:
            speed = motion_node.properties.get("duration_speed")
            if global_intent_node.properties.get("visual_temperature") == "Operational" and speed == "Fluid":
                raise ValueError(
                    f"DESIGN_SYSTEM_CONTRADICTION_FAILURE: Operational workspace demands snappy/instant feedback, "
                    f"which contradicts the sluggish 'Fluid' transition speed."
                )

        # ⚠️ Contradiction 3: Contrast-Precision Mismatch
        # High contrast precision color demands cannot use high saturation variance or normal/low readability tokens.
        if color_char_node:
            stability = color_char_node.properties.get("stability")
            sat_var = color_char_node.properties.get("saturation_variance")
            readability = color_char_node.properties.get("readability_demands")
            
            if color_intent == "Precision":
                if sat_var == "High saturation variance" or readability != "High readability":
                    raise ValueError(
                        f"DESIGN_SYSTEM_CONTRADICTION_FAILURE: Precision semantic color intent contradicts "
                        f"high saturation variance ({sat_var}) or low readability demands ({readability})."
                    )
