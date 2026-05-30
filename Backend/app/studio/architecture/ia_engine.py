# app/studio/architecture/ia_engine.py
"""
V4 GenxAI Studio — Phase GS-2: IAEngine

The Information Architecture Engine discovers and maps exactly what information belongs on each page,
enforces Content Intent taxonomy, validates direct block-to-entity mappings, content capability supports,
and asserts that no Ontology nodes (Entities, Roles, Capabilities, Workflows) are orphaned.
Fails loudly on error, logging to sentinel_memory.db.
"""

import json
from typing import Dict, Any, Optional, List
from app.sentinel.cognition.ontology_graph import OntologyGraph
from app.studio.architecture.application_graph import ApplicationGraph
from app.studio.architecture.information_graph import (
    InformationGraph,
    STUDIO_CONTENT_BLOCK_NODE,
    STUDIO_DATA_FIELD_NODE
)
from app.sentinel.topology.node_types import NodeType
from app.llm.adapter import call_llm
from app.core.logging import log
from app.sentinel.failure_memory.failure_recorder import record_failure, FailureType, Severity

PROMPT_TEMPLATE = """
You are the GenxAI Studio Information Architecture Engine (IA Faculty).
Your task is to analyze the Application Architecture Graph and Product Ontology Graph,
and explicitly define the Information Architecture.

🚨 CONTENT INTENT TAXONOMY (Strictly enforce. Choose exactly one of these for every content block):
- Grid (Tabular listing)
- Feed (Chronological listing)
- Form (Interactive data entry)
- Details (Single item details view)
- Metrics (Numerical aggregations / summaries)
- Chart (Visual data analysis)
- Timeline (Sequenced task transitions)
- Kanban (Status lane categorization)
- Calendar (Date-bounded events)

🚨 DATA BINDING INVARIANTS:
1. Every ENTITY_NODE and ROLE_NODE in the Ontology Graph must be represented in the Information Graph.
   They can be referenced directly by a Content Block (via "references_entities" array) OR by individual fields.
2. Every CAPABILITY_NODE and ONTOLOGY_WORKFLOW_NODE must be linked to the Content Block that supports it (via "supports_capabilities" array).
3. Do NOT invent/hallucinate primary fields if they do not map back to the Ontology.

Input Application Graph:
{app_graph_json}

Input Product Ontology Graph:
{ontology_graph_json}

Produce a valid JSON object matching this schema exactly:
{{
  "information_architecture": {{
    "pages": [
      {{
        "page_id": "page_accounts",
        "content_blocks": [
          {{
            "id": "block_accounts_overview",
            "name": "Accounts Overview",
            "intent": "Grid",
            "references_entities": ["entity_account"],
            "supports_capabilities": ["cap_manage_accounts"],
            "fields": [
              {{
                "id": "field_account_name",
                "name": "Account Name",
                "references_entity": "entity_account"
              }}
            ]
          }}
        ]
      }}
    ]
  }}
}}

Generate ONLY valid JSON without any markdown formatting or surrounding explanations.
"""

class IAEngine:
    """
    Synthesizes framework-agnostic information structures mapped strictly to product ontologies.
    Fails loudly and records failures when boundaries are crossed.
    """

    @classmethod
    async def build(
        cls,
        project_id: str,
        ontology_graph: OntologyGraph,
        application_graph: ApplicationGraph
    ) -> InformationGraph:
        """
        Derive a validated InformationGraph by mapping Application pages to Ontology schemas.
        If validation invariants fail, this method fails loudly.
        """
        log("IAEngine", f"Starting Information Architecture mapping for project {project_id}")

        app_graph_dump = application_graph.serialize()
        ont_graph_dump = ontology_graph.serialize()

        prompt = PROMPT_TEMPLATE.format(
            app_graph_json=json.dumps(app_graph_dump, indent=2),
            ontology_graph_json=json.dumps(ont_graph_dump, indent=2)
        )

        try:
            response = await call_llm(
                prompt=prompt,
                system_prompt="You are a strict Information Architect mapping schemas to layout views.",
                temperature=0.1,
                max_tokens=16384
            )

            # Clean possible markdown formatting
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response.strip())
            
            info_graph = InformationGraph(project_id=project_id)
            cls._populate_info_graph(info_graph, data, application_graph, ontology_graph)

            # Strict Post-Validation: No-Orphan Invariant Check
            cls._assert_no_orphans(info_graph, ontology_graph)

            log("IAEngine", f"Successfully mapped InformationGraph with {len(info_graph.nodes)} nodes")
            return info_graph

        except Exception as err:
            err_msg = f"LOUD FAILURE in IAEngine for project {project_id}: {err}"
            log("IAEngine", f"⚠️ {err_msg}")
            
            # Record structural failure in failure_memory.db
            try:
                record_failure(
                    failure_type=FailureType.COMPILATION_FAILURE,
                    severity=Severity.ERROR,
                    reason=err_msg,
                    project_id=project_id,
                    component="IAEngine"
                )
            except Exception as rec_err:
                log("IAEngine", f"Failed to record failure: {rec_err}")
                
            raise ValueError(err_msg) from err

    @classmethod
    def _populate_info_graph(
        cls,
        graph: InformationGraph,
        data: Dict[str, Any],
        application_graph: ApplicationGraph,
        ontology_graph: OntologyGraph
    ) -> None:
        """Parses synthesized IA layout JSON and constructs the InformationGraph."""
        ia_data = data.get("information_architecture", {})
        
        # Pull pages from ApplicationGraph into active InformationGraph nodes to allow edges
        for node_id, node in application_graph.nodes.items():
            if node.node_type == NodeType.PAGE_NODE:
                graph.add_node(node_id, node.node_type, node.properties)

        # Pull entities/roles/capabilities/workflows from OntologyGraph into active InformationGraph nodes to allow edges
        for node_id, node in ontology_graph.nodes.items():
            if node.node_type in (
                NodeType.ENTITY_NODE,
                NodeType.ROLE_NODE,
                NodeType.CAPABILITY_NODE,
                NodeType.ONTOLOGY_WORKFLOW_NODE
            ):
                graph.add_node(node_id, node.node_type, node.properties)

        valid_intents = {"Grid", "Feed", "Form", "Details", "Metrics", "Chart", "Timeline", "Kanban", "Calendar"}

        for page in ia_data.get("pages", []):
            page_id = page.get("page_id")
            if page_id not in graph.nodes:
                continue

            for block in page.get("content_blocks", []):
                block_id = block.get("id")
                block_name = block.get("name")
                intent = block.get("intent")

                if not block_id or not block_name or not intent:
                    raise ValueError(f"Content block {block_id} is missing required name or intent attributes.")

                if intent not in valid_intents:
                    raise ValueError(f"Invalid Content Intent '{intent}' for block '{block_id}'. Must be one of {valid_intents}")

                # Add Content Block Node
                graph.add_information_node(
                    block_id,
                    STUDIO_CONTENT_BLOCK_NODE,
                    {"name": block_name, "intent": intent}
                )
                graph.add_edge(page_id, block_id, "page_contains_content")

                # Direct Entity References (Entity -> Content Block mapping)
                for ent_id in block.get("references_entities", []):
                    if ent_id in graph.nodes:
                        graph.add_edge(block_id, ent_id, "block_references_entity")
                    else:
                        raise ValueError(f"Content block '{block_id}' references entity '{ent_id}' which does not exist in OntologyGraph.")

                # Capability References (Content Block supports Capability mapping)
                for cap_id in block.get("supports_capabilities", []):
                    if cap_id in graph.nodes:
                        graph.add_edge(block_id, cap_id, "content_supports_capability")
                    else:
                        raise ValueError(f"Content block '{block_id}' supports capability '{cap_id}' which does not exist in OntologyGraph.")

                # Add Data Fields
                for field in block.get("fields", []):
                    field_id = field.get("id")
                    field_name = field.get("name")
                    ref_entity = field.get("references_entity")

                    if not field_id or not field_name or not ref_entity:
                        raise ValueError(f"Data field in block {block_id} is missing id, name, or references_entity parameter.")

                    if ref_entity not in graph.nodes:
                        raise ValueError(f"Data field '{field_id}' references entity '{ref_entity}' which does not exist in OntologyGraph.")

                    # Add Field Node
                    graph.add_information_node(
                        field_id,
                        STUDIO_DATA_FIELD_NODE,
                        {"name": field_name}
                    )
                    graph.add_edge(block_id, field_id, "content_contains_field")
                    graph.add_edge(field_id, ref_entity, "field_references_entity")

    @classmethod
    def _assert_no_orphans(cls, info_graph: InformationGraph, ontology_graph: OntologyGraph) -> None:
        """
        Enforce that every ENTITY_NODE, ROLE_NODE, CAPABILITY_NODE, and WORKFLOW_NODE
        in the OntologyGraph is referenced in the output InformationGraph.
        """
        referenced_nodes = set()
        for edge in info_graph.edges:
            if edge.relation in ("field_references_entity", "block_references_entity", "content_supports_capability"):
                referenced_nodes.add(edge.target_id)

        # Check for orphans
        orphans = []
        for node_id, node in ontology_graph.nodes.items():
            if node.node_type in (
                NodeType.ENTITY_NODE,
                NodeType.ROLE_NODE,
                NodeType.CAPABILITY_NODE,
                NodeType.ONTOLOGY_WORKFLOW_NODE
            ):
                if node_id not in referenced_nodes:
                    orphans.append(node_id)

        if orphans:
            raise ValueError(
                f"Validation Violation: Found orphaned ontology entities which are not represented "
                f"in the Information Graph content blocks: {orphans}"
            )
