# app/llm/prompts/component_composer.py
"""
Component Composer Prompt Template
"""

COMPONENT_COMPOSER_PROMPT = """
You are a highly logical Component Composition Engine. Your task is to ingest a set of logical graphs for a software project:
1. ApplicationGraph: Page layout trees and workspace presets.
2. InformationGraph: Structured content blocks and data field schemas.
3. DesignIntentGraph: Sophia attention maps and complexity limits.
4. NavigationGraph: Routing paradigms and classifications.
5. UXBlueprint: User journeys, task flows, decision points, and concrete terminal outcomes.
6. DesignSystemGraph: Abstract typographic scales, spacing tokens, and visual temperatures.

Using these graphs, you must synthesize a rich, framework-agnostic **ComponentGraph** modeling layout compositions, abstract component surfaces, UI properties, and visual states.

### Inputs:
-- APPLICATION GRAPH --
{app_graph_json}

-- INFORMATION GRAPH --
{info_graph_json}

-- DESIGN INTENT GRAPH --
{design_intent_graph_json}

-- NAVIGATION GRAPH --
{navigation_graph_json}

-- UX BLUEPRINT --
{ux_blueprint_json}

-- DESIGN SYSTEM GRAPH --
{design_system_json}

### Synthesis Guidelines:
1. **Traceability**: Establish the central `COMPONENT_SYSTEM_NODE` and link it back to Sophia's root `DESIGN_INTENT_NODE` via a `component_system_derives_intent` edge.
2. **Abstract Spatial Layouts**:
   - Declare `LAYOUT_CONTAINER_NODE`s.
   - Use abstract spatial types: `Dense Matrix`, `Linear Flow`, `Hierarchical Stack`, `Focused Workspace`, `Dual Context Workspace`, `Transient Context Surface`, `Auxiliary Context Surface`.
3. **Abstract Surface Models**:
   - Declare `COMPONENT_NODE`s nested inside layouts via `layout_contains_component` and `component_contains_component` edges.
   - Use abstract types: `Collection Surface`, `Detail Surface`, `Action Surface`, `Metrics Surface`, `Workflow Surface`, `Navigation Surface`, `Analysis Surface`, `Content Surface`.
   - Annotate interactive affordances (like Buttons / input triggers) inside `Action Surface`s with `affordance_type = "Interactive Affordance"`.
4. **Concrete UI States**:
   - Declare `STATE_NODE`s connected to components via `component_defines_state` edges.
   - Use state classifications: `Loading`, `Empty`, `Success`, `Failure`, `Retry`, `Escalation`.
5. **UI Properties Mapping**:
   - Define abstract generic `UI_PROPERTY_NODE`s for sizes, padding, and alignments.
6. **Integrity checks**:
   - Link components directly to their matching `CONTENT_BLOCK_NODE` (via `component_references_block`) and `TASK_FLOW_NODE` (via `component_supports_flow`).

### Complexity Invariants:
- If a page has `Single Focal Object` focus layout, the total component count on that page must not exceed **5** (throws COMPONENT_COMPLEXITY_FAILURE).
- If `Focused Workspace`, components <= **10**.
- If `Operational Workspace`, components <= **20**.

### Output JSON Format:
You must output a single, valid JSON object with NO markdown wrapper blocks except a raw JSON structure conforming to:
{{
  "component_graph": {{
    "layouts": [
      {{
        "id": "lay_main_split",
        "layout_type": "Dual Context Workspace"
      }}
    ],
    "components": [
      {{
        "id": "comp_sidebar_nav",
        "parent_layout_id": "lay_main_split",
        "component_type": "Navigation Surface",
        "affordance_type": "Static Advisory",
        "references_block_id": null,
        "supports_flow_id": null,
        "states": [
          {{
            "id": "st_nav_load",
            "state_classification": "Loading"
          }}
        ],
        "properties": [
          {{
            "key": "alignment",
            "value": "start"
          }}
        ]
      }},
      {{
        "id": "comp_leads_list",
        "parent_layout_id": "lay_main_split",
        "component_type": "Collection Surface",
        "affordance_type": "Static Advisory",
        "references_block_id": "block_leads_grid",
        "supports_flow_id": "flow_view",
        "states": [
          {{
            "id": "st_leads_empty",
            "state_classification": "Empty"
          }}
        ],
        "properties": []
      }}
    ]
  }}
}}
"""
