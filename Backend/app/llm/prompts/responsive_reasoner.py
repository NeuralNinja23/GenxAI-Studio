# app/llm/prompts/responsive_reasoner.py
"""
Responsive Reasoner Prompt Template
"""

RESPONSIVE_REASONER_PROMPT = """
You are a highly logical Responsive Cognitive Reasoning Engine. Your task is to ingest a set of logical graphs for a software project:
1. ApplicationGraph: Page layout trees and workspace presets.
2. InformationGraph: Structured content blocks and data field schemas.
3. DesignIntentGraph: Sophia attention maps and visual temperatures.
4. ComponentGraph: Framework-agnostic components, abstract spatial layouts, visual states, and UI properties.
5. UXBlueprint: User journeys, task flows, decision points, and concrete terminal outcomes.

Using these graphs, you must synthesize a rich, framework-agnostic **ResponsiveGraph** modeling viewport constraints, responsive intents, attention capacities, cognitive density budgets, interaction cost mappings, priority rules, and layout overrides.

### Inputs:
-- APPLICATION GRAPH --
{app_graph_json}

-- INFORMATION GRAPH --
{info_graph_json}

-- DESIGN INTENT GRAPH --
{design_intent_graph_json}

-- COMPONENT GRAPH --
{component_graph_json}

-- UX BLUEPRINT --
{ux_blueprint_json}

### Synthesis Guidelines:
1. **Traceability**: Establish the central `RESPONSIVE_SYSTEM_NODE` and link it back to Sophia's root `DESIGN_INTENT_NODE` via a `responsive_system_derives_intent` edge.
2. **Responsive Intent Nodes (`RESPONSIVE_INTENT_NODE`)**:
   - Define device-specific responsive intents (Desktop: `analysis`, Tablet: `monitoring`, Mobile: `task_execution`).
3. **Viewport Constraints (`VIEWPORT_CONSTRAINT_NODE`)**:
   - Establish non-overlapping constraint boundaries (Desktop width >= 1024, Tablet width 768 to 1023, Mobile width < 768).
4. **Attention Capacity (`ATTENTION_NODE`)**:
   - Declare viewport-specific attention capacities (Desktop: `high`, Tablet: `medium`, Mobile: `low`).
5. **Density Budget (`DENSITY_NODE`)**:
   - Declare cognitive density budget scales (`Sparse`, `Balanced`, `Dense`) based on device focus.
6. **Interaction Cost (`INTERACTION_COST_NODE`)**:
   - Map maximum allowed interaction costs per workflow (Desktop max cost: 12, Tablet: 8, Mobile: 5).
7. **Component Priority Nodes (`PRIORITY_NODE`)**:
   - Level components as `Critical`, `Primary`, `Secondary`, or `Optional`.
8. **Adaptation Rules (`ADAPTATION_RULE_NODE`)**:
   - Derive reflow behavior strictly from priority:
     - `Critical` -> `Always Visible`
     - `Primary` -> `Promote`
     - `Secondary` -> `Collapse`
     - `Optional` -> `Hide`
9. **Layout Overrides (`LAYOUT_OVERRIDE_NODE`)**:
   - Map spatial viewport-specific overrides (e.g. reflowing a `Dense Matrix` on Desktop to a `Hierarchical Stack` on Mobile).

### Output JSON Format:
You must output a single, valid JSON object with NO markdown wrapper blocks except a raw JSON structure conforming to:
{{
  "responsive_graph": {{
    "intents": [
      {{
        "id": "intent_desktop",
        "viewport": "desktop",
        "primary_goal": "analysis"
      }},
      {{
        "id": "intent_mobile",
        "viewport": "mobile",
        "primary_goal": "task_execution"
      }}
    ],
    "viewports": [
      {{
        "id": "vp_desktop",
        "min_width": 1024,
        "max_width": 9999,
        "attention_capacity": "high",
        "density_budget": "Dense",
        "max_interaction_cost": 12
      }},
      {{
        "id": "vp_mobile",
        "min_width": 0,
        "max_width": 767,
        "attention_capacity": "low",
        "density_budget": "Sparse",
        "max_interaction_cost": 5
      }}
    ],
    "priorities": [
      {{
        "id": "pri_leads_list",
        "target_component_id": "comp_leads_list",
        "priority_level": "Critical"
      }},
      {{
        "id": "pri_analytics_feed",
        "target_component_id": "comp_analytics_feed",
        "priority_level": "Optional"
      }}
    ],
    "adaptations": [
      {{
        "id": "rule_leads_visible",
        "viewport_id": "vp_mobile",
        "priority_id": "pri_leads_list",
        "adaptation_action": "Always Visible"
      }},
      {{
        "id": "rule_analytics_hide",
        "viewport_id": "vp_mobile",
        "priority_id": "pri_analytics_feed",
        "adaptation_action": "Hide"
      }}
    ],
    "overrides": [
      {{
        "id": "over_mobile_stack",
        "viewport_id": "vp_mobile",
        "target_layout_id": "lay_matrix",
        "override_layout_type": "Hierarchical Stack",
        "workflow_steps_count": 4,
        "focus_anchors_count": 1
      }}
    ]
  }}
}}
"""
